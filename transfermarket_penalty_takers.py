import requests
import tls_requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import os
import ast

from useful_functions import write_dict_data, read_dict_data, overwrite_dict_data, find_manual_similar_string

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root


class TransfermarktScraper:
    def __init__(self):
        self.base_url = 'https://www.transfermarkt.com'
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
        soup = self.fetch_page(url)
        team_links = {}
        if soup:
            idx = 1
            while idx < 20:
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

    def get_penalty_takers(self, team_suffix):
        # Dynamically determine the current year and then the two previous years
        current_year = datetime.now().year
        years = [str(current_year - i) for i in range(15)]

        takers = []
        for year in years:
            penalty_url = f"{self.base_url}/{team_suffix.split('/')[1]}/elfmeterschuetzen/verein/{team_suffix.split('/')[4]}/plus/0?saison_id={year}"
            soup = self.fetch_page(penalty_url)
            if soup:
                for tr in soup.select("#yw1 table tbody tr"):
                    name_elem = tr.select_one("td.hauptlink a")
                    minute_elem = tr.select_one("td:nth-of-type(8)")
                    date_elem = tr.select_one("td.zentriert")
                    is_goal_elem = tr.select_one("td:nth-of-type(7)")

                    if name_elem and minute_elem and date_elem and is_goal_elem:
                        minute_text = minute_elem.text.replace("'", "").strip()
                        is_goal_text = is_goal_elem.text.strip()
                        is_goal = True if is_goal_text == "in" else False
                        if minute_text.isdigit():
                            date_obj = datetime.strptime(date_elem.text.strip(), "%b %d, %Y")
                            player_name = name_elem['title']
                            player_name = find_manual_similar_string(player_name)
                            takers.append({
                                'name': player_name,
                                'minute': int(minute_text),
                                'date': date_obj,
                                # 'position': len(takers) + 1,
                                # 'is_goal': is_goal
                            })
        takers.sort(key=lambda x: (x['date'], x['minute']), reverse=True)
        return takers

    def scrape(self):
        result = {}
        # league_url = "https://www.transfermarkt.com/fifa-club-world-cup/startseite/pokalwettbewerb/KLUB"
        league_url = "https://www.transfermarkt.com/laliga/startseite/wettbewerb/ES1"
        # league_url = "https://www.transfermarkt.com/europameisterschaft-2024/teilnehmer/pokalwettbewerb/EM24/saison_id/2023"
        # league_url = "https://www.transfermarkt.com/copa-america-2024/teilnehmer/pokalwettbewerb/CAM4/saison_id/2023"
        team_links = self.get_team_links(league_url)
        for team_name, team_suffix in team_links.items():
            print('Extracting penalty takers data from %s ...' % team_name)
            result[team_name] = self.get_penalty_takers(team_suffix)
        return result


def get_penalty_takers_dict(
        write_file=True,
        file_name="transfermarket_laliga_penalty_takers",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    scraper = TransfermarktScraper()
    penalties_data = scraper.scrape()

    filtered_penalties_data = {}
    for team, penalty_takers in penalties_data.items():
        filtered_penalties = [penalty_taker["name"] for penalty_taker in penalty_takers if penalty_taker["minute"] != 120][:6]
        filtered_penalties += ["UNKNOWN"] * (6 - len(filtered_penalties))
        filtered_penalties_data[team] = filtered_penalties

    if write_file:
        # write_dict_data(filtered_penalties_data, file_name)
        overwrite_dict_data(filtered_penalties_data, file_name)

    return filtered_penalties_data


# penalty_takers = get_penalty_takers_dict(file_name="test_transfermarket_laliga_penalty_takers", force_scrape=True)
#
# print(penalty_takers)
# for team, penalties in penalty_takers.items():
#     print(team, penalties)
