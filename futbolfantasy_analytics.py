import ast
import os
import re
import copy
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
import csv
import requests
from bs4 import BeautifulSoup
import urllib3

from useful_functions import overwrite_dict_data, read_dict_data, create_driver, find_manual_similar_string

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root


class FutbolFantasyScraper:
    def __init__(self):
        # self.base_url = 'https://www.futbolfantasy.com/analytics/laliga-fantasy/mercado'
        self.base_url = 'https://www.futbolfantasy.com/analytics/biwenger/mercado'
        self.driver = create_driver()
        self.wait = WebDriverWait(self.driver, 15)
        self.small_wait = WebDriverWait(self.driver, 5)
        self.session = requests.Session()
        # Use this custom headers dict when making GET requests
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }

    def fetch_page(self, url):
        self.driver.get(url)

    def fetch_response(self, url):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = self.session.get(url, headers=self.headers, verify=False)
        response.raise_for_status()
        return response.text

    def accept_cookies(self):
        # This function was used to click a cookie accept button with Selenium,
        # but it's not needed when using requests unless the site strictly requires
        # special headers or cookies. We'll leave it here to keep the comment.
        pass

    def get_team_options(self, html):
        # select = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="main_wrapper"]/div/div[1]/main/div[3]/div[2]/div[2]/select')))
        # Instead, parse HTML with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        select = soup.find('select', {'name': 'equipo'})
        team_options = {}
        if select:
            options = select.find_all('option')
            for option in options:
                value = option.get('value', '')
                if value and value != '0':
                    team_options[value] = option.text.strip()
        return team_options


    def get_player_elements(self, html):
        # players_container = self.wait.until(EC.presence_of_element_located((By.XPATH, f'//div[@class="lista_elementos"]')))
        # Instead, parse HTML with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        players_container = soup.find('div', class_='lista_elementos')
        if not players_container:
            return []
        # player_elements = players_container.find_elements(By.XPATH, './div')
        player_elements = players_container.find_all('div', recursive=False)
        return player_elements

    def get_player_data(self, player_element):
        # We gather attributes from the HTML element
        # Because these are stored in data-* attributes, we can access them via get(...)
        name = player_element.get('data-nombre', '').strip().title()
        name = find_manual_similar_string(name)
        price = player_element.get('data-valor', '').strip()
        position = player_element.get('data-posicion', '').strip()
        team_id = player_element.get('data-equipo', '').strip()
        form = player_element.get('data-diferencia-pct1', '').strip()
        price_trend = player_element.get('data-diferencia1', '').strip() or "0"
        return name, price, position, team_id, form, price_trend

    def scrape_teams_probabilities(self):
        # self.fetch_page("https://www.futbolfantasy.com/laliga/clasificacion")
        self.fetch_page("https://www.futbolfantasy.com/mundial-clubes/clasificacion")

        team_elements = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, '//tr[contains(@class, "team")]')))
        team_elements = team_elements[:20]
        team_links = {}
        for team_element in team_elements:
            team_name = team_element.find_element(By.TAG_NAME, 'strong').text.strip()
            team_link = team_element.find_element(By.TAG_NAME, 'a').get_attribute('href').strip()
            team_links[team_name] = team_link

        probabilities_dict = {}
        for team_name, team_link in team_links.items():
            self.fetch_page(team_link)

            try:
                select_probabilidad_element = self.wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//select[option[@value="probabilidad"]]')
                    )
                )
                select_probabilidad_obj = Select(select_probabilidad_element)
                select_probabilidad_obj.select_by_value("probabilidad")
            except:
                pass

            player_elements = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, '//*[contains(@class, "camiseta ")]')))
            team_probabilities = {}
            for player_element in player_elements:
                player_name = None
                probability = "0%"
                try:
                    player_name = player_element.find_element(
                        # By.XPATH, './/ancestor::*[contains(@class, "fotocontainer laliga")]').find_element(By.TAG_NAME, 'img').get_attribute('alt').strip()
                        By.XPATH, './/ancestor::*[contains(@class, "fotocontainer mundial-clubes")]').find_element(By.TAG_NAME, 'img').get_attribute('alt').strip()
                except NoSuchElementException:  # Error while getting player_name
                    try:
                        player_name = player_element.find_element(
                            # By.XPATH, './/*[@class="img   laliga "]').get_attribute('alt').strip()
                            By.XPATH, './/*[@class="img   mundial-clubes "]').get_attribute('alt').strip()
                    except NoSuchElementException:  # Error while getting player_name
                        player_name = player_element.get_attribute('href').split('/')[-1].replace('-', ' ').strip()
                        player_name = player_name.encode('latin1').decode('utf-8')
                        player_name = player_name.title()
                try:
                    probability = player_element.get_attribute('data-probabilidad').strip()
                except AttributeError: # Error while getting probability
                    continue
                player_name = re.sub(r'[\d%]', '', player_name).strip()
                probability = re.sub(r'[^0-9%]', '', probability)
                if player_name and probability:
                    player_name = find_manual_similar_string(player_name)
                    probability = float(probability.replace('%', '')) / 100
                    team_probabilities[player_name] = probability
            probabilities_dict[team_name] = team_probabilities

        return probabilities_dict

    def scrape_matches_probabilities(self, probabilities_dict=None):
        if not probabilities_dict:
            probabilities_dict = {}

        # 1) Fetch the possible lineups page via requests and parse out match URLs
        # html = self.fetch_response("https://www.futbolfantasy.com/laliga/posibles-alineaciones")
        html = self.fetch_response("https://www.futbolfantasy.com/mundial-clubes/posibles-alineaciones")
        soup = BeautifulSoup(html, 'html.parser')
        main = soup.find('main')

        match_links = []
        for a in main.find_all('a', href=True):
            href = a['href']
            if 'www.futbolfantasy.com/partidos/' in href:
                match_links.append(href)
        match_links = sorted(list(set(match_links)))

        for match_url in match_links:
            # print(match_url)
            # 2) Load each match page with Selenium
            self.fetch_page(match_url)

            # 3) Try to select probabilidad to display it
            try:
                select_probabilidad_element = self.wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//select[option[@value="probabilidad"]]')
                    )
                )
                select_probabilidad_obj = Select(select_probabilidad_element)
                select_probabilidad_obj.select_by_value("probabilidad")
            except:
                pass

            try:
                # 4) Extract home & away team names
                local_el = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[starts-with(@class,"equipo local ")]'))
                )
                home_team_name = local_el.find_element(
                    By.XPATH, './/*[starts-with(@class,"nombre ")]'
                ).text.strip()

                visit_el = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, '//*[starts-with(@class,"equipo visitante ")]'))
                )
                away_team_name = visit_el.find_element(
                    By.XPATH, './/*[starts-with(@class,"nombre ")]'
                ).text.strip()

                # 5) Grab the two halves (starters)
                row = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.row.fondo-campo.m-auto'))
                )
                team_divs = row.find_elements(By.XPATH, './div')
                home_start = team_divs[0]
                away_start = team_divs[1]

                # 6) Grab the single suplentes-container, split its two inner divs into home_sup/away_sup
                sup_container = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.suplentes-container'))
                )
                inner = sup_container.find_element(By.TAG_NAME, 'div')
                child_divs = inner.find_elements(By.XPATH, './div')
                home_sup = child_divs[0]
                away_sup = child_divs[1]

                teams_elements = {
                    home_team_name: [home_start, home_sup],
                    away_team_name: [away_start, away_sup],
                }
            except TimeoutException:
                # skip this match if anything timed out
                continue

            # 7) For each team, find all its camiseta elements and extract probabilities
            for team_name, containers in teams_elements.items():
                try:
                    team_probabilities = {}
                    for container in containers:
                        # scoped wait for any camiseta under this container
                        player_elements = self.wait.until(
                            lambda d: container.find_elements(By.XPATH, './/*[contains(@class,"camiseta ")]')
                        )
                        for player_element in player_elements:
                            player_name = None
                            probability = "0%"
                            try:
                                player_name = player_element.find_element(
                                    # By.CSS_SELECTOR, 'div.fotocontainer.laliga'
                                    By.CSS_SELECTOR, 'div.fotocontainer.mundial-clubes'
                                ).find_element(By.TAG_NAME, 'img').get_attribute('alt').strip()
                            except NoSuchElementException:  # Error while getting player_name
                                try:
                                    player_name = player_element.find_element(
                                        # By.XPATH, './/*[contains(@class, "img") and contains(@class, "laliga")]'
                                        By.XPATH, './/*[contains(@class, "img") and contains(@class, "mundial-clubes")]'
                                    ).get_attribute('alt').strip()
                                except NoSuchElementException:  # Error while getting player_name
                                    player_name = player_element.get_attribute('href').split('/')[-1].replace('-', ' ').strip()
                                    player_name = player_name.encode('latin1').decode('utf-8')
                                    player_name = player_name.title()
                            try:
                                probability = player_element.get_attribute('data-probabilidad').strip()
                            except AttributeError: # Error while getting probability
                                continue

                            # Clean up name & percent
                            player_name = re.sub(r'[\d%]', '', player_name).strip()
                            probability = re.sub(r'[^0-9%]', '', probability)
                            if player_name and probability:
                                player_name = find_manual_similar_string(player_name)
                                team_probabilities[player_name] = float(probability.replace('%','')) / 100

                    probabilities_dict[team_name] = team_probabilities
                except TimeoutException:
                    # skip this team if anything timed out
                    continue

        return probabilities_dict

    def scrape(self):
        # self.fetch_page(self.base_url)
        # self.accept_cookies()
        main_html = self.fetch_response(self.base_url)
        team_options = self.get_team_options(main_html)

        positions_normalize = {
            "Portero": "GK",
            "Defensa": "DEF",
            "Mediocampista": "MID",
            "Delantero": "ATT",
        }

        prices_dict = {team_name: {} for team_name in team_options.values()}
        positions_dict = {team_name: {} for team_name in team_options.values()}
        forms_dict = {team_name: {} for team_name in team_options.values()}
        price_trends_dict = {team_name: {} for team_name in team_options.values()}

        player_elements = self.get_player_elements(main_html)
        for player_element in player_elements:
            name, price, position, team_id, form, price_trend = self.get_player_data(player_element)
            team_name = team_options.get(team_id)
            position_name = positions_normalize.get(position)
            if team_name:
                prices_dict[team_name][name] = price
                positions_dict[team_name][name] = position_name
                forms_dict[team_name][name] = form
                price_trends_dict[team_name][name] = price_trend

        teams_probabilities_dict = self.scrape_teams_probabilities()
        matches_probabilities_dict = self.scrape_matches_probabilities(teams_probabilities_dict)
        probabilities_dict = copy.deepcopy(matches_probabilities_dict)

        # We don't have a browser to quit, but we'll keep the comment
        # self.driver.quit()
        return prices_dict, positions_dict, forms_dict, probabilities_dict, price_trends_dict


def get_futbolfantasy_data(
        price_file_name="futbolfantasy_prices",
        positions_file_name="futbolfantasy_positions",
        forms_file_name="futbolfantasy_forms",
        start_probability_file_name="futbolfantasy_start_probabilities",
        price_trends_file_name="futbolfantasy_price_trends",
        force_scrape=False
):
    if not force_scrape:
        prices_data = read_dict_data(price_file_name)
        positions_data = read_dict_data(positions_file_name)
        forms_data = read_dict_data(forms_file_name)
        start_probabilities_data = read_dict_data(start_probability_file_name)
        price_trends_data = read_dict_data(price_trends_file_name)

        if prices_data and positions_data and forms_data and start_probabilities_data and price_trends_data:
            return prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data

    scraper = FutbolFantasyScraper()
    prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data = scraper.scrape()

    overwrite_dict_data(prices_data, price_file_name)
    overwrite_dict_data(positions_data, positions_file_name)
    overwrite_dict_data(forms_data, forms_file_name)
    overwrite_dict_data(start_probabilities_data, start_probability_file_name)
    overwrite_dict_data(price_trends_data, price_trends_file_name)

    return prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data


def get_players_prices_dict(
        file_name="futbolfantasy_prices",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    scraper = FutbolFantasyScraper()
    result, _, _, _, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_positions_dict(
        file_name="futbolfantasy_positions",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    scraper = FutbolFantasyScraper()
    _, result, _, _, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_forms_dict(
        file_name="futbolfantasy_forms",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    scraper = FutbolFantasyScraper()
    _, _, result, _, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_start_probabilities_dict(
        file_name="futbolfantasy_start_probabilities",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    scraper = FutbolFantasyScraper()
    _, _, _, result, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_price_trends_dict(
        file_name="futbolfantasy_price_trends",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    scraper = FutbolFantasyScraper()
    _, _, _, _, result = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


# prices, positions, forms, start_probabilities, price_trends = get_futbolfantasy_data(
#     price_file_name="test_futbolfantasy_mundialito_players_prices",
#     positions_file_name="test_futbolfantasy_mundialito_players_positions",
#     forms_file_name="test_futbolfantasy_mundialito_players_forms",
#     start_probability_file_name="test_futbolfantasy_mundialito_players_start_probabilities",
#     price_trends_file_name="test_futbolfantasy_mundialito_players_price_trends",
#     force_scrape=True
# )
# print("Prices:")
# for team, players in prices.items():
#     print(team, players)
# print("\nPositions:")
# for team, players in positions.items():
#     print(team, players)
# print("\nForms:")
# for team, players in forms.items():
#     print(team, players)
# print("\nStart Probabilities:")
# for team, players in start_probabilities.items():
#     print(team, players)
# print("\nPrice Trends:")
# for team, players in price_trends.items():
#     print(team, players)
