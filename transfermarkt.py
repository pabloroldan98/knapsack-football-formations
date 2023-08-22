import requests
from bs4 import BeautifulSoup
from datetime import datetime

class TransfermarktScraper:
    def __init__(self):
        self.base_url = 'https://www.transfermarkt.com'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def fetch_page(self, url):
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return BeautifulSoup(response.content, 'html.parser')
        else:
            return None

    def get_team_links(self, url):
        soup = self.fetch_page(url)
        team_links = {}
        if soup:
            teams = soup.select("#yw1 table tbody tr td a")
            for team in teams:
                link = team.get('href')
                title = team.get('title')
                if title and link:
                    team_links[title] = link
        return team_links

    def get_penalty_takers(self, team_suffix):
        # Dynamically determine the current year and then the two previous years
        current_year = datetime.now().year
        years = [str(current_year), str(current_year - 1), str(current_year - 2)]

        takers = []
        for year in years:
            penalty_url = f"{self.base_url}/{team_suffix.split('/')[1]}/elfmeterschuetzen/verein/{team_suffix.split('/')[4]}/plus/0?saison_id={year}"
            soup = self.fetch_page(penalty_url)
            if soup:
                for tr in soup.select("#yw1 table tbody tr"):
                    name_elem = tr.select_one("td.hauptlink a")
                    minute_elem = tr.select_one("td:nth-of-type(8)")
                    date_elem = tr.select_one("td.zentriert")

                    if name_elem and minute_elem and date_elem:
                        minute_text = minute_elem.text.replace("'", "").strip()
                        if minute_text.isdigit():
                            date_obj = datetime.strptime(date_elem.text.strip(), "%b %d, %Y")
                            takers.append({
                                'name': name_elem['title'],
                                'minute': int(minute_text)
                                # 'date': date_obj,
                                # 'position': len(takers) + 1
                            })
        return takers

    def scrape(self):
        result = {}
        league_url = "https://www.transfermarkt.com/laliga/startseite/wettbewerb/ES1"
        team_links = self.get_team_links(league_url)
        for team_name, team_suffix in team_links.items():
            print('Extracting data from %s ...' % team_name)
            result[team_name] = self.get_penalty_takers(team_suffix)
        return result


if __name__ == "__main__":
    scraper = TransfermarktScraper()
    penalties_data = scraper.scrape()

    filtered_penalties_data = {}
    for team, penalty_takers in penalties_data.items():
        filtered_penalties = [penalty_taker["name"] for penalty_taker in penalty_takers if penalty_taker["minute"] != 120][:6]
        filtered_penalties_data[team] = filtered_penalties

    print(filtered_penalties_data)
    # for team, penalties in data.items():
    #     print(team, penalties)
