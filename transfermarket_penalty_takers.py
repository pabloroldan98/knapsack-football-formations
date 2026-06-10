import re
import tls_requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import time
import os

from useful_functions import read_dict_data, overwrite_dict_data, find_manual_similar_string

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root


class TransfermarktScraper:
    def __init__(self, competition: str = None, max_workers: int = 8):
        self.base_url = 'https://www.transfermarkt.com'
        self.competition = (
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
                    team_link = a.get("href")
                    if team_name and team_link and "verein" in team_link:
                        team_links[team_name] = team_link
                idx += 1
        return team_links

    def _penalty_season_url(self, team_suffix, year):
        slug = team_suffix.split('/')[1]
        verein_id = team_suffix.split('/')[4]
        return f"{self.base_url}/{slug}/elfmeterschuetzen/verein/{verein_id}/plus/0?saison_id={year}"

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

    def _parse_penalty_taker_row(self, tr):
        name_elem = tr.select_one("td.hauptlink a")
        if not name_elem:
            return None

        tds = tr.select("td")
        if len(tds) >= 11:
            date_elem = tds[0]
            is_goal_elem = tds[9]
            minute_elem = tds[10]
        else:
            date_elem = tr.select_one("td.zentriert")
            is_goal_elem = tr.select_one("td:nth-of-type(7)")
            minute_elem = tr.select_one("td:nth-of-type(8)")

        if not date_elem or not minute_elem or not is_goal_elem:
            return None

        minute_text = minute_elem.text.replace("'", "").strip()
        if not minute_text.isdigit():
            return None

        # date_obj = datetime.strptime(date_elem.text.strip(), "%b %d, %Y")
        # date_obj = datetime.strptime(date_elem.text.strip(), "%d.%m.%Y")
        # date_obj = datetime.strptime(date_elem.text.strip(), "%d/%m/%Y")
        date_str = date_elem.text.strip().replace('.', '/').replace('-', '/')
        try:
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            return None

        player_name = name_elem.get("title") or name_elem.text.strip()
        player_name = find_manual_similar_string(player_name)
        is_goal_text = is_goal_elem.text.strip()
        is_goal = is_goal_text == "in"
        return {
            'name': player_name,
            'minute': int(minute_text),
            'date': date_obj,
            'is_goal': is_goal,
        }

    def _extract_takers_from_page(self, soup):
        if soup.select_one("#yw1 .empty"):
            return []

        takers = []
        for tr in soup.select("#yw1 table.items tbody tr, #yw1 table tbody tr"):
            row = self._parse_penalty_taker_row(tr)
            if row:
                takers.append(row)
        return takers

    # for year in years:
    #     penalty_url = f"{self.base_url}/{team_suffix.split('/')[1]}/elfmeterschuetzen/verein/{team_suffix.split('/')[4]}/plus/0?saison_id={year}"
    #     soup = self.fetch_page(penalty_url)
    #     if soup:
    #         for tr in soup.select("#yw1 table tbody tr"):
    #             name_elem = tr.select_one("td.hauptlink a")
    #             minute_elem = tr.select_one("td:nth-of-type(8)")
    #             date_elem = tr.select_one("td.zentriert")
    #             is_goal_elem = tr.select_one("td:nth-of-type(7)")
    #
    #             if name_elem and minute_elem and date_elem and is_goal_elem:
    #                 minute_text = minute_elem.text.replace("'", "").strip()
    #                 is_goal_text = is_goal_elem.text.strip()
    #                 is_goal = True if is_goal_text == "in" else False
    #                 if minute_text.isdigit():
    #                     # date_obj = datetime.strptime(date_elem.text.strip(), "%b %d, %Y")
    #                     # date_obj = datetime.strptime(date_elem.text.strip(), "%d.%m.%Y")
    #                     # date_obj = datetime.strptime(date_elem.text.strip(), "%d/%m/%Y")
    #                     date_str = date_elem.text.strip().replace('.', '/').replace('-', '/')
    #                     date_obj = datetime.strptime(date_str, "%d/%m/%Y")
    #                     player_name = name_elem['title']
    #                     player_name = find_manual_similar_string(player_name)
    #                     takers.append({
    #                         'name': player_name,
    #                         'minute': int(minute_text),
    #                         'date': date_obj,
    #                         # 'position': len(takers) + 1,
    #                         # 'is_goal': is_goal
    #                     })

    def _fetch_penalty_takers_for_season(self, team_suffix, year):
        first_page_url = self._penalty_season_url(team_suffix, year)
        soup = self.fetch_page(first_page_url)
        if not soup:
            return []

        season_takers = []
        for page_url in self._penalty_page_urls(soup, first_page_url):
            if page_url != first_page_url:
                soup = self.fetch_page(page_url)
                if not soup:
                    continue
            season_takers.extend(self._extract_takers_from_page(soup))
        return season_takers

    def get_penalty_takers(self, team_suffix):
        # Dynamically determine the current year and then the two previous years
        current_year = datetime.now().year
        years = [str(current_year - i) for i in range(15)]

        takers = []
        workers = min(self.max_workers, len(years))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for year_takers in executor.map(
                lambda year: self._fetch_penalty_takers_for_season(team_suffix, year),
                years,
            ):
                takers.extend(year_takers)

        takers.sort(key=lambda x: (x['date'], x['minute']), reverse=True)
        return takers

    def _scrape_team_penalty_takers(self, team_name, team_suffix):
        print('Extracting penalty takers data from %s ...' % team_name)
        return team_name, self.get_penalty_takers(team_suffix)

    def scrape(self):
        result = {}
        # # league_url = f"{self.base_url}/fifa-club-world-cup/startseite/pokalwettbewerb/KLUB"
        # league_url = f"{self.base_url}/laliga/startseite/wettbewerb/ES1"
        # # league_url = "https://www.transfermarkt.com/europameisterschaft-2024/teilnehmer/pokalwettbewerb/EM24"
        # # league_url = f"{self.base_url}/copa-america-2024/teilnehmer/pokalwettbewerb/CAM4"
        league_url = f"{self.base_url}/{self.competition}"
        team_links = self.get_team_links(league_url)
        items = list(team_links.items())
        workers = min(self.max_workers, len(items) or 1)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(self._scrape_team_penalty_takers, team_name, team_suffix)
                for team_name, team_suffix in items
            ]
            for future in as_completed(futures):
                team_name, takers = future.result()
                result[team_name] = takers

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


def get_penalty_takers_dict(
        write_file=True,
        file_name="transfermarket_laliga_penalty_takers",
        force_scrape=False,
        max_workers=8,
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = TransfermarktScraper(competition=competition, max_workers=max_workers)
    penalties_data = scraper.scrape()

    filtered_penalties_data = {}
    for team, penalty_takers in penalties_data.items():
        # Exclude penaltis shot at the same time (because they are penalty shootouts)
        combo_counts = {}
        for p in penalty_takers:
            key = (p["minute"], p["date"])
            combo_counts[key] = combo_counts.get(key, 0) + 1
        filtered_penalties = [
            [p["name"], p["is_goal"]]
            for p in penalty_takers
            if p["minute"] < 90 or combo_counts[(p["minute"], p["date"])] < 3
        ][:6]
        filtered_penalties += [["UNKNOWN", True]] * (6 - len(filtered_penalties))
        filtered_penalties_data[team] = filtered_penalties

    if write_file:
        # write_dict_data(filtered_penalties_data, file_name)
        overwrite_dict_data(filtered_penalties_data, file_name, compact_list_items=True)

    return filtered_penalties_data


# penalty_takers = get_penalty_takers_dict(file_name="test_transfermarket_laliga_penalty_takers", force_scrape=True)
#
# print(penalty_takers)
# for team, penalties in penalty_takers.items():
#     print(team, penalties)
