import json
import re
import requests
import tls_requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import threading
import time
import os
import ast

from useful_functions import write_dict_data, read_dict_data, overwrite_dict_data, find_manual_similar_string

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root
JSON_FILES_DIR = os.path.join(ROOT_DIR, 'json_files')
CLUB_METADATA_CACHE_FILE = os.path.join(JSON_FILES_DIR, 'transfermarket_club_metadata_cache.json')
TEAM_COUNTRY_CACHE_FILE = os.path.join(JSON_FILES_DIR, 'transfermarket_team_country_cache.json')


def _load_disk_cache(path):
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding='utf-8') as cache_file:
            data = json.load(cache_file)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Could not read cache {path}: {e!r}")
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): value for key, value in data.items()}


def _save_disk_cache(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as cache_file:
        json.dump(data, cache_file, ensure_ascii=False, indent=2)


class TransfermarktScraper:
    def __init__(self, competition: str = None, max_workers: int = 8, use_disk_cache: bool = True):
        self.base_url = 'https://www.transfermarkt.com'
        self.competition =  (
            competition
            if competition is not None
            else "-/startseite/wettbewerb/ES1"
        )
        self.max_workers = max(1, max_workers)
        self.use_disk_cache = use_disk_cache
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.json_headers = {**self.headers, 'Accept': 'application/json'}
        self.tmapi_base_url = 'https://tmapi-alpha.transfermarkt.technology'
        self._club_cache = {}
        self._team_country_cache = {}
        self._cache_lock = threading.Lock()
        if self.use_disk_cache:
            self._club_cache = _load_disk_cache(CLUB_METADATA_CACHE_FILE)
            self._team_country_cache = _load_disk_cache(TEAM_COUNTRY_CACHE_FILE)
            print(
                f"Disk cache loaded: {len(self._club_cache)} clubs, "
                f"{len(self._team_country_cache)} countries"
            )

    def persist_disk_caches(self):
        if not self.use_disk_cache:
            return
        with self._cache_lock:
            club_snapshot = dict(self._club_cache)
            country_snapshot = dict(self._team_country_cache)
        _save_disk_cache(CLUB_METADATA_CACHE_FILE, club_snapshot)
        _save_disk_cache(TEAM_COUNTRY_CACHE_FILE, country_snapshot)
        print(
            f"Disk cache saved: {len(club_snapshot)} clubs, "
            f"{len(country_snapshot)} countries"
        )

    def fetch_page(self, url, tries: int = 3, pause: float = 20.0):
        """
        Fetch a URL, retrying up to `tries` times if the status is not 200.
        Sleeps `pause` seconds between attempts.
        Returns a BeautifulSoup on success, or None if all attempts fail.
        """
        # response = requests.get(url, headers=self.headers)
        for attempt in range(1, tries + 1):
            try:
                response = tls_requests.get(url, headers=self.headers)
            except Exception as e:
                # network-level error; count it as a failed attempt
                print(f"Attempt {attempt}/{tries} failed with exception: {e!r} ({url})")
            else:
                if response.status_code == 200:
                    return BeautifulSoup(response.content, 'html.parser')
                else:
                    print(f"Attempt {attempt}/{tries} returned status {response.status_code} ({url})")
            if attempt < tries:
                time.sleep(pause)
        # all attempts exhausted
        return None

    def get_team_links(self, url):
        soup = self.fetch_page(url)
        team_links = {}
        if soup:
            idx = 1
            idx_limit = 2 if 'teilnehmer' in self.competition else 20
            while idx < idx_limit:
                block_id = f"yw{idx}"
                selector = f"#{block_id} table tbody tr td a"
                teams = soup.select(selector)
                if not teams:
                    break
                for a in teams:
                    team_name = a.get("title")
                    team_name = find_manual_similar_string(team_name)
                    team_link = a.get("href")
                    if team_name and team_link and "verein" in team_link:
                        team_links[team_name] = team_link
                idx += 1
        return team_links

    def get_player_links(self, url):
        soup = self.fetch_page(url, tries=5, pause=60.0)
        player_links = {}
        if soup:
            players = soup.select("#yw1 table tbody tr td.posrela a")
            if not players:
                players = soup.select("div.responsive-table div.grid-view table.items tbody tr td table.inline-table tr td.hauptlink a")
            for player in players:
                player_name = player.text.strip()
                player_name = find_manual_similar_string(player_name)
                url = player.get('href')
                if player_name and url:
                    player_links[player_name] = f"{self.base_url}{url}"
        return player_links

    def _team_players_url(self, team_suffix, use_country_as_team=False):
        cutoff_month = 5 if use_country_as_team else 7
        year = str(datetime.now().year - int(datetime.now() < datetime(datetime.now().year, cutoff_month, 1)))
        slug = team_suffix.split('/')[1]
        verein_id = team_suffix.split('/')[4]
        return f"{self.base_url}/{slug}/startseite/verein/{verein_id}/plus/0?saison_id={year}"

    def get_team_player_links(self, team_links, use_country_as_team=False):
        team_player_links = {}

        def fetch_one(item):
            team_name, team_suffix = item
            # if team_name not in [
            #     'Inter',
            #     'Ulsan HD FC',
            #     'Juventus FC',
            #     'Al-Ain FC',
            #     'Wydad Casablanca',
            # ]:
            #     continue
            print('Extracting players links from %s ...' % team_name)
            return team_name, self.get_player_links(self._team_players_url(team_suffix, use_country_as_team))

        workers = min(self.max_workers, len(team_links) or 1)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for team_name, player_links in executor.map(fetch_one, team_links.items()):
                team_player_links[team_name] = player_links

        return team_player_links

    def _team_country_cache_key(self, url):
        match = re.search(r'/verein/(\d+)', url)
        return match.group(1) if match else url

    def _keywords_country_from_html(self, html):
        match = re.search(
            r'<meta[^>]+name=["\']keywords["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.I,
        )
        if not match:
            match = re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']keywords["\']',
                html,
                re.I,
            )
        if not match:
            return None
        country = match.group(1).split(',')[-1].strip()
        return find_manual_similar_string(country) if country else None

    def get_team_country(self, url):
        cache_key = self._team_country_cache_key(url)
        with self._cache_lock:
            if cache_key in self._team_country_cache:
                return self._team_country_cache[cache_key]

        country = None
        try:
            response = tls_requests.get(url, headers=self.headers, verify=False)
            if response.status_code == 200:
                country = self._keywords_country_from_html(response.text)
        except Exception as e:
            print(f"get_team_country failed for {url}: {e!r}")

        with self._cache_lock:
            self._team_country_cache[cache_key] = country
        return country

    def _player_id_from_url(self, url):
        match = re.search(r'/spieler/(\d+)', url)
        return match.group(1) if match else None

    def _fetch_player_performance_by_club(self, player_id):
        api_url = f"{self.base_url}/ceapi/performance-game/{player_id}"
        try:
            response = tls_requests.get(api_url, headers=self.json_headers, verify=False)
        except Exception as e:
            print(f"performance-game API failed for player {player_id}: {e!r}")
            return None
        if response.status_code != 200:
            print(f"performance-game API returned {response.status_code} for player {player_id}")
            return None
        payload = response.json()
        if not payload.get('success'):
            return None
        performances = (payload.get('data') or {}).get('performance') or []
        if not performances:
            return None

        by_club = {}
        for game in performances:
            stats = game.get('statistics') or {}
            general = stats.get('generalStatistics') or {}
            if general.get('participationState') != 'played':
                continue
            club_block = (game.get('clubsInformation') or {}).get('club') or {}
            club_id = str(club_block.get('clubId') or '')
            if not club_id:
                continue
            if club_id not in by_club:
                by_club[club_id] = {'appearances': 0, 'goals': 0, 'minutes': 0}
            goals = (stats.get('goalStatistics') or {}).get('goalsScoredTotal') or 0
            minutes = (stats.get('playingTimeStatistics') or {}).get('playedMinutes') or 0
            by_club[club_id]['appearances'] += 1
            by_club[club_id]['goals'] += int(goals)
            by_club[club_id]['minutes'] += int(minutes)
        return by_club if by_club else None

    def _fetch_club_metadata(self, club_id):
        name = None
        team_url = None
        try:
            response = tls_requests.get(
                f"{self.tmapi_base_url}/club/{club_id}",
                headers=self.json_headers,
                verify=False,
            )
            if response.status_code == 200:
                data = (response.json().get('data') or {})
                relative_url = data.get('relativeUrl')
                if relative_url:
                    name = data.get('name')
                    team_url = f"{self.base_url}{relative_url}"
        except Exception as e:
            print(f"tmapi club lookup failed for {club_id}: {e!r}")

        if not team_url:
            lookup_url = f"{self.base_url}/-/startseite/verein/{club_id}"
            try:
                response = tls_requests.get(lookup_url, headers=self.headers, verify=False)
                if response.status_code == 200:
                    html = response.text
                    canonical = re.search(
                        r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
                        html,
                        re.I,
                    )
                    team_url = canonical.group(1) if canonical else lookup_url
                    headline = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.I)
                    if headline:
                        name = headline.group(1).strip()
            except Exception as e:
                print(f"club page lookup failed for {club_id}: {e!r}")
                team_url = lookup_url

        if name:
            name = find_manual_similar_string(name)
        return {
            'name': name or f'Club {club_id}',
            'url': team_url or f"{self.base_url}/-/startseite/verein/{club_id}",
        }

    def _get_club_metadata(self, club_id):
        club_id = str(club_id)
        with self._cache_lock:
            if club_id in self._club_cache:
                return self._club_cache[club_id]

        info = self._fetch_club_metadata(club_id)
        with self._cache_lock:
            if club_id not in self._club_cache:
                self._club_cache[club_id] = info
            return self._club_cache[club_id]

    def _team_history_from_html_table(self, url, use_country_as_team=False):
        transfers_url = url.replace("/profil/", "/leistungsdatenverein/")
        soup = self.fetch_page(transfers_url)
        team_history = []
        if not soup:
            return team_history
        team_entries = soup.select("#yw1 table tbody tr")
        for entry in team_entries:
            team_data = entry.select("td")
            if not team_data:
                continue
            team_name = team_data[1].text.strip()
            team_name = find_manual_similar_string(team_name)
            team_link = team_data[1].find('a')
            if not team_link or not team_link.get('href'):
                continue
            team_url = f"{self.base_url}{team_link['href']}"
            if use_country_as_team:
                team_country = self.get_team_country(team_url)
                if team_country:
                    team_name = team_country
            appearances = team_data[2].text.replace("-", "0").strip()
            goals = team_data[4].text.replace("-", "0").strip()
            minutes = team_data[-1].text.replace("-", "0").replace("'", "").replace(".", "").strip()
            if team_name:# and minutes:
                team_history.append({
                    "name": team_name,
                    "url": team_url,
                    # "country": team_country,
                    "appearances": int(appearances),
                    "goals": int(goals),
                    "minutes": int(minutes),
                })
        return team_history

    # def get_player_team_history(self, url, use_country_as_team=False):
    #     transfers_url = url.replace("/profil/", "/leistungsdatenverein/")
    #     soup = self.fetch_page(transfers_url)
    #     team_history = []
    #     if soup:
    #         team_entries = soup.select("#yw1 table tbody tr")
    #         for entry in team_entries:
    #             team_data = entry.select("td")
    #             if team_data:
    #                 team_name = team_data[1].text.strip()
    #                 team_name = find_manual_similar_string(team_name)
    #                 team_url = f"{self.base_url}{team_data[1].find('a')['href']}"
    #                 if use_country_as_team:
    #                     team_country = self.get_team_country(team_url)
    #                     team_name = team_country
    #                 appearances = team_data[2].text.replace("-", "0").strip()
    #                 goals = team_data[4].text.replace("-", "0").strip()
    #                 minutes = team_data[-1].text.replace("-", "0").replace("'", "").replace(".", "").strip()
    #
    #                 if team_name:# and minutes:
    #                     team_info = {
    #                         "name": team_name,
    #                         "url": team_url,
    #                         # "country": team_country,
    #                         "appearances": int(appearances),
    #                         "goals": int(goals),
    #                         "minutes": int(minutes),
    #                     }
    #                     team_history.append(team_info)
    #     return team_history

    def get_player_team_history(self, url, use_country_as_team=False):
        player_id = self._player_id_from_url(url)
        if not player_id:
            return self._team_history_from_html_table(url, use_country_as_team)

        by_club = self._fetch_player_performance_by_club(player_id)
        if not by_club:
            return self._team_history_from_html_table(url, use_country_as_team)

        team_history = []
        for club_id, stats in sorted(by_club.items(), key=lambda item: item[1]['minutes'], reverse=True):
            club = self._get_club_metadata(club_id)
            team_name = club['name']
            team_url = club['url']
            if use_country_as_team:
                team_country = self.get_team_country(team_url)
                if team_country:
                    team_name = team_country
            if team_name:
                team_history.append({
                    "name": team_name,
                    "url": team_url,
                    # "country": team_country,
                    "appearances": stats['appearances'],
                    "goals": stats['goals'],
                    "minutes": stats['minutes'],
                })
        return team_history

    def _scrape_player_history(self, team_name, player_name, player_link, use_country_as_team):
        player_name = find_manual_similar_string(player_name)
        history = self.get_player_team_history(player_link, use_country_as_team)
        return team_name, player_name, history

    def scrape(self, use_country_as_team=False):
        try:
            # # league_url = f"{self.base_url}/fifa-club-world-cup/startseite/pokalwettbewerb/KLUB"
            # league_url = f"{self.base_url}/laliga/startseite/wettbewerb/ES1"
            # # league_url = "https://www.transfermarkt.com/europameisterschaft-2024/teilnehmer/pokalwettbewerb/EM24"
            # # league_url = f"{self.base_url}/copa-america-2024/teilnehmer/pokalwettbewerb/CAM4"
            league_url = f"{self.base_url}/{self.competition}"
            team_links = self.get_team_links(league_url)
            team_player_links = self.get_team_player_links(team_links, use_country_as_team)
            print()

            tasks = [
                (team_name, player_name, player_link)
                for team_name, player_links in team_player_links.items()
                for player_name, player_link in player_links.items()
            ]
            result = {team_name: {} for team_name in team_player_links}
            total = len(tasks)
            print(f"\nFetching team history for {total} players ({self.max_workers} workers)...\n")

            completed = 0
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [
                    executor.submit(
                        self._scrape_player_history,
                        team_name,
                        player_name,
                        player_link,
                        use_country_as_team,
                    )
                    for team_name, player_name, player_link in tasks
                ]
                # break
                for future in as_completed(futures):
                    team_name, player_name, history = future.result()
                    result[team_name][player_name] = history
                    completed += 1
                    if completed == 1 or completed % 25 == 0 or completed == total:
                        print(f"  {completed}/{total} players done (latest: {player_name})")

            return result
        finally:
            self.persist_disk_caches()


def competition_from_filename(file_name: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', file_name.lower())  # normalize to dashed tokens

    mapping = {
        ("mundialito", "club-world-cup", "clubworldcup", "mundial-clubes", "mundialclubes", ): "-/startseite/pokalwettbewerb/KLUB",
        ("champions", "championsleague", "champions-league"): "-/teilnehmer/pokalwettbewerb/CL",
        ('europaleague', 'europa-league', ): "-/teilnehmer/pokalwettbewerb/EL",
        ('conference', 'conferenceleague', 'conference-league', ): "-/teilnehmer/pokalwettbewerb/UCOL",
        ("eurocopa", "euro", "europa", "europeo", ): "-/teilnehmer/pokalwettbewerb/EURO",
        ("copaamerica", "copa-america", ): "-/teilnehmer/pokalwettbewerb/COPA",
        ("mundial", "worldcup", "world-cup", ): "-/teilnehmer/pokalwettbewerb/FIWC",
        ("laliga", "la-liga", ): "-/startseite/wettbewerb/ES1",
        ('premier', 'premier-league', 'premierleague', ): "-/startseite/wettbewerb/GB1",
        ('seriea', 'serie-a', ): "-/startseite/wettbewerb/IT1",
        ('bundesliga', 'bundes-liga', 'bundes', ): "-/startseite/wettbewerb/L1",
        ('ligueone', 'ligue-one', 'ligue1', 'ligue-1', 'ligue', ): "-/startseite/wettbewerb/FR1",
        ("segunda", "segundadivision", "segunda-division", "laliga2", "la-liga-2", "la-liga-hypermotion", "hypermotion", "laligahypermotion", ): "-/startseite/wettbewerb/ES2",
    }
    for keys, slug in mapping.items():
        for k in sorted(keys, key=len, reverse=True):  # longest first
            if k in s:
                return slug
    return "-/startseite/wettbewerb/ES1"


def get_players_team_history_dict(
        write_file=True,
        file_name="transfermarket_laliga_team_history",
        use_country_as_team=False,
        force_scrape=False,
        max_workers=8,
        use_disk_cache=True,
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = TransfermarktScraper(
        competition=competition,
        max_workers=max_workers,
        use_disk_cache=use_disk_cache,
    )
    team_history_data = scraper.scrape(use_country_as_team)

    filtered_team_history_data = {}
    for team, player_data in team_history_data.items():
        filtered_player_team_history = {}
        for player_name, team_history in player_data.items():
            filtered_team_history = [team["name"] for team in team_history] # if team["minutes"] > 0]
            filtered_player_team_history[player_name] = filtered_team_history
        filtered_team_history_data[team] = filtered_player_team_history

    if write_file:
        # write_dict_data(filtered_team_history_data, file_name):
        overwrite_dict_data(filtered_team_history_data, file_name)

    return filtered_team_history_data


# players_team_history = get_players_team_history_dict(
#     file_name="test_transfermarket_laliga_team_history",
#     use_country_as_team=False,
#     force_scrape=True
# )
#
# print(players_team_history)
# for team, players in players_team_history.items():
#     print()
#     print(team)
#     for player, team_history in players.items():
#         print(player, team_history)
