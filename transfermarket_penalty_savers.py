import re
import tls_requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import time
import os

from useful_functions import read_dict_data, overwrite_dict_data, find_manual_similar_string

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root

NATIONAL_TEAM_COMPETITION_SLUGS = (
    "/teilnehmer/pokalwettbewerb/EURO",
    "/teilnehmer/pokalwettbewerb/COPA",
    "/teilnehmer/pokalwettbewerb/FIWC",
)


class TransfermarktScraper:
    def __init__(self, competition: str = None, max_workers: int = 8):
        self.base_url = 'https://www.transfermarkt.com'
        self.competition =  (
            competition
            if competition is not None
            else "-/startseite/wettbewerb/ES1"
        )
        self.max_workers = max(1, max_workers)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

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
        soup = self.fetch_page(url, tries=5, pause=60.0)
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
                    # if team_name not in ["CA Osasuna", "Getafe CF", ]:
                    #     continue
                    team_link = a.get("href")
                    if team_name and team_link and "verein" in team_link:
                        team_links[team_name] = team_link
                idx += 1
        return team_links

    def get_goalkeeper_links(self, url):
        soup = self.fetch_page(url)
        player_links = {}
        if soup:
            players = soup.select("#yw1 table tbody tr td.posrela table tbody tr td a")
            if not players:
                players = soup.select("div.responsive-table div.grid-view table.items tbody tr td table.inline-table tr td.hauptlink a")
            positions = soup.select("#yw1 table tbody tr td.posrela table tbody tr td")
            if not positions:
                positions = soup.select("div.responsive-table div.grid-view table.items tbody tr td table.inline-table tr td")
            i = 0
            for player in players:
                player_name = player.text.strip()
                player_name = find_manual_similar_string(player_name)
                position_text = positions[i * 3 + 2].text.strip()
                player_url = player.get('href')
                if player_name and player_url and position_text:
                    if "Goalkeeper" in position_text:
                        player_links[player_name] = f"{self.base_url}{player_url}"
                i = i + 1
        return player_links

    def _uses_may_season_cutoff(self):
        return any(slug in self.competition for slug in NATIONAL_TEAM_COMPETITION_SLUGS)

    def _team_players_url(self, team_suffix):
        cutoff_month = 5 if self._uses_may_season_cutoff() else 7
        year = str(datetime.now().year - int(datetime.now() < datetime(datetime.now().year, cutoff_month, 1)))
        slug = team_suffix.split('/')[1]
        verein_id = team_suffix.split('/')[4]
        return f"{self.base_url}/{slug}/startseite/verein/{verein_id}/plus/0?saison_id={year}"

    def get_team_player_links(self, team_links):
        team_player_links = {}

        def fetch_one(item):
            team_name, team_suffix = item
            # if team_name not in [
            #     "Chelsea FC",
            #     "CR Flamengo",
            #     "CF Monterrey",
            # ]:
            #     continue
            print('Extracting goalkeeper links from %s ...' % team_name)
            # team_players_url = f"{self.base_url}/{team_suffix.split('/')[1]}/kader/verein/{team_suffix.split('/')[4]}/saison_id/{year}/plus/1"
            return team_name, self.get_goalkeeper_links(self._team_players_url(team_suffix))

        workers = min(self.max_workers, len(team_links) or 1)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for team_name, player_links in executor.map(fetch_one, team_links.items()):
                team_player_links[team_name] = player_links

        return team_player_links

    def _penalty_detail_url(self, profile_url):
        # penalty_saves_url = url.replace("/profil/", "/elfmeterstatistik/") + "/saison_id=2022//wettbewerb_id//plus/1#gehalten"
        path = profile_url.replace(self.base_url, "")
        path = path.replace("/profil/", "/elfmeterstatistik/")
        return f"{self.base_url}{path.rstrip('/')}/saison_id//wettbewerb_id//plus/1"

    def _absolute_url(self, href):
        if not href:
            return None
        if href.startswith("http"):
            return href
        return f"{self.base_url}{href}"

    def _penalty_page_urls(self, soup, first_page_url):
        page_urls = [first_page_url]
        seen_paths = {first_page_url}
        for link in soup.select("ul.tm-pagination a.tm-pagination__link[href]"):
            page_url = self._absolute_url(link.get("href"))
            if page_url and page_url not in seen_paths:
                seen_paths.add(page_url)
                page_urls.append(page_url)
        return page_urls

    def _parse_penalty_row(self, tr, is_saved):
        minute_elem = tr.select_one("td:nth-of-type(8)")
        date_elem = tr.select_one("td:nth-of-type(4)")
        if not minute_elem or not date_elem:
            return None
        minute_text = minute_elem.text.replace("'", "").strip()
        if not minute_text.isdigit():
            return None
        # date_obj = datetime.strptime(date_elem.text.strip(), "%b %d, %Y")
        # date_obj = datetime.strptime(date_elem.text.strip(), "%d.%m.%Y")
        date_str = date_elem.text.strip().replace('.', '/').replace('-', '/')
        try:
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            return None
        match_link = tr.select_one("a.ergebnis-link")
        match_id = match_link.get("id") if match_link else None
        return {
            'is_saved': is_saved,
            'date': date_obj,
            'minute': int(minute_text),
            'match_id': match_id,
        }

    def _extract_penalties_from_page(self, soup, seen_match_ids):
        penalties = []
        for grid_id, is_saved in (("yw1", True), ("yw2", False)):
            for tr in soup.select(f"#{grid_id} table.items tbody tr, div.grid-view#{grid_id} table.items tbody tr"):
                row = self._parse_penalty_row(tr, is_saved)
                if not row:
                    continue
                match_id = row.pop('match_id', None)
                if match_id:
                    if match_id in seen_match_ids:
                        continue
                    seen_match_ids.add(match_id)
                penalties.append(row)
        return penalties

    # def get_player_penalty_saves(self, url):
    #     penalty_saves_url = url.replace("/profil/", "/elfmeterstatistik/") + "/saison_id=2022//wettbewerb_id//plus/1#gehalten"
    #     soup = self.fetch_page(penalty_saves_url)
    #     penalty_saves = []
    #     if soup:
    #         for tr in soup.select("#yw1 table tbody tr"):
    #             is_penalty_saved = True
    #             minute_elem = tr.select_one("td:nth-of-type(8)")
    #             date_elem = tr.select_one("td:nth-of-type(4)")
    #
    #             if minute_elem and date_elem:
    #                 minute_text = minute_elem.text.replace("'", "").strip()
    #                 if minute_text.isdigit():
    #                     # date_obj = datetime.strptime(date_elem.text.strip(), "%b %d, %Y")
    #                     # date_obj = datetime.strptime(date_elem.text.strip(), "%d.%m.%Y")
    #                     date_str = date_elem.text.strip().replace('.', '/').replace('-', '/')
    #                     date_obj = datetime.strptime(date_str, "%d/%m/%Y")
    #                     penalty_saves.append({
    #                         'is_saved': is_penalty_saved,
    #                         'date': date_obj,
    #                         'minute': int(minute_text),
    #                     })
    #         for tr in soup.select("#yw2 table tbody tr"):
    #             is_penalty_saved = False
    #             minute_elem = tr.select_one("td:nth-of-type(8)")
    #             date_elem = tr.select_one("td:nth-of-type(4)")
    #
    #             if minute_elem and date_elem:
    #                 minute_text = minute_elem.text.replace("'", "").strip()
    #                 if minute_text.isdigit():
    #                     # date_obj = datetime.strptime(date_elem.text.strip(), "%b %d, %Y")
    #                     # date_obj = datetime.strptime(date_elem.text.strip(), "%d.%m.%Y")
    #                     date_str = date_elem.text.strip().replace('.', '/').replace('-', '/')
    #                     date_obj = datetime.strptime(date_str, "%d/%m/%Y")
    #                     penalty_saves.append({
    #                         'is_saved': is_penalty_saved,
    #                         'date': date_obj,
    #                         'minute': int(minute_text),
    #                     })
    #     penalty_saves.sort(key=lambda x: (x['date'], x['minute']), reverse=True)
    #     return penalty_saves

    def get_player_penalty_saves(self, url):
        first_page_url = self._penalty_detail_url(url)
        soup = self.fetch_page(first_page_url)
        if not soup:
            return []

        seen_match_ids = set()
        penalty_saves = []
        for page_url in self._penalty_page_urls(soup, first_page_url):
            if page_url != first_page_url:
                soup = self.fetch_page(page_url)
                if not soup:
                    continue
            penalty_saves.extend(self._extract_penalties_from_page(soup, seen_match_ids))

        penalty_saves.sort(key=lambda x: (x['date'], x['minute']), reverse=True)
        return penalty_saves

    def _scrape_goalkeeper_penalties(self, team_name, player_name, player_link):
        player_name = find_manual_similar_string(player_name)
        penalties = self.get_player_penalty_saves(player_link)
        return team_name, player_name, penalties

    def scrape(self):
        # # league_url = f"{self.base_url}/fifa-club-world-cup/startseite/pokalwettbewerb/KLUB"
        # league_url = f"{self.base_url}/laliga/startseite/wettbewerb/ES1"
        # # league_url = "https://www.transfermarkt.com/europameisterschaft-2024/teilnehmer/pokalwettbewerb/EM24"
        # # league_url = f"{self.base_url}/copa-america-2024/teilnehmer/pokalwettbewerb/CAM4"
        league_url = f"{self.base_url}/{self.competition}"
        team_links = self.get_team_links(league_url)
        team_player_links = self.get_team_player_links(team_links)
        print()

        tasks = [
            (team_name, player_name, player_link)
            for team_name, player_links in team_player_links.items()
            for player_name, player_link in player_links.items()
        ]
        result = {team_name: {} for team_name in team_player_links}
        total = len(tasks)
        print(f"\nFetching penalty history for {total} goalkeepers ({self.max_workers} workers)...\n")

        completed = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(
                    self._scrape_goalkeeper_penalties,
                    team_name,
                    player_name,
                    player_link,
                )
                for team_name, player_name, player_link in tasks
            ]
            # break
            for future in as_completed(futures):
                team_name, player_name, penalties = future.result()
                result[team_name][player_name] = penalties
                completed += 1
                if completed == 1 or completed % 10 == 0 or completed == total:
                    print(f"  {completed}/{total} goalkeepers done (latest: {player_name})")

        return result


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


def get_penalty_savers_dict(
        write_file=True,
        file_name="transfermarket_laliga_penalty_savers",
        force_scrape=False,
        max_workers=8,
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = TransfermarktScraper(competition=competition, max_workers=max_workers)
    penalty_saves_data = scraper.scrape()

    filtered_penalty_saves_data = {}
    for team, player_data in penalty_saves_data.items():
        filtered_player_penalty_saves = {}
        for player_name, penalty_saves in player_data.items():
            filtered_penalty_saves = [team["is_saved"] for team in penalty_saves][:11]
            filtered_penalty_saves += [False] * (11 - len(filtered_penalty_saves))
            filtered_player_penalty_saves[player_name] = filtered_penalty_saves
        filtered_penalty_saves_data[team] = filtered_player_penalty_saves

    if write_file:
        # write_dict_data(filtered_penalty_saves_data, file_name):
        overwrite_dict_data(filtered_penalty_saves_data, file_name, ignore_valid_file=True)

    return filtered_penalty_saves_data


# goalkeepers_penalty_saves = get_penalty_savers_dict(
#     file_name="test_transfermarket_laliga_penalty_savers",
#     force_scrape=True
# )
#
# print(goalkeepers_penalty_saves)
# for team, goalkeepers_penalties in goalkeepers_penalty_saves.items():
#     print()
#     print(team)
#     for goalkeeper, penalty_saves in goalkeepers_penalties.items():
#         print(goalkeeper, penalty_saves)
