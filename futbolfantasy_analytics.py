import ast
import os
import re
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
import csv

from useful_functions import overwrite_dict_to_csv, read_dict_from_csv, create_driver

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root


class FutbolFantasyScraper:
    def __init__(self):
        self.base_url = 'https://www.futbolfantasy.com/analytics/laliga-fantasy/mercado'
        # chrome_opt = Options()
        # chrome_opt.add_argument("--disable-search-engine-choice-screen")
        # chrome_opt.add_argument("--headless")  # Run Chrome in headless mode
        # chrome_opt.add_argument("--disable-gpu")  # Disable GPU usage (useful for headless mode)
        # chrome_opt.add_argument("--no-sandbox")  # Bypass OS security model
        # chrome_opt.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
        # self.driver = webdriver.Chrome(options=chrome_opt)
        self.driver = create_driver()
        self.wait = WebDriverWait(self.driver, 15)
        self.small_wait = WebDriverWait(self.driver, 5)

    def fetch_page(self, url):
        self.driver.get(url)

    def accept_cookies(self):
        try:
            accept_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@mode="primary"]')))
            accept_button.click()
        except TimeoutException:
            print("No cookie accept button found or clickable.")

    def get_team_options(self):
        select = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="main_wrapper"]/div/div[1]/main/div[3]/div[2]/div[2]/select')))
        options = select.find_elements(By.TAG_NAME, 'option')
        team_options = {option.get_attribute('value'): option.text for option in options if option.get_attribute('value') != '0'}
        return team_options

    def get_player_elements(self):
        players_container = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, f'//div[@class="lista_elementos"]')))
        player_elements = players_container.find_elements(By.XPATH, './div')
        return player_elements

    def get_player_data(self, player_element):
        name = player_element.get_attribute('data-nombre').strip().title()
        if name == "Alfonso Espino":
            name = "Pacha Espino"
        if name == "Peter Gonzales":
            name = "Peter Federico"
        if name == "Abde Ezzalzouli":
            name = "Ez Abde"
        if name == "Jonathan Montiel":
            name = "Joni Montiel"
        if name == "Manuel Fuster":
            name = "Fuster"
        price = player_element.get_attribute('data-valor').strip()
        position = player_element.get_attribute('data-posicion').strip()
        team_id = player_element.get_attribute('data-equipo').strip()
        form = player_element.get_attribute('data-diferencia-pct1').strip()
        price_trend = player_element.get_attribute('data-diferencia1').strip() or "0"
        return name, price, position, team_id, form, price_trend

    def scrape_probabilities(self):
        self.fetch_page("https://www.futbolfantasy.com/laliga/clasificacion")

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
            player_elements = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, '//*[contains(@class, "camiseta ")]')))
            team_probabilities = {}
            for player_element in player_elements:
                player_name = None
                probability = "0%"
                try:
                    player_name = player_element.find_element(
                        By.XPATH, './/ancestor::*[contains(@class, "fotocontainer laliga")]').find_element(By.TAG_NAME, 'img').get_attribute('alt').strip()
                except NoSuchElementException:  # Error while getting player_name
                    try:
                        player_name = player_element.find_element(
                            By.XPATH, './/*[@class="img   laliga "]').get_attribute('alt').strip()
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
                    if player_name == "Alfonso Espino":
                        player_name = "Pacha Espino"
                    if player_name == "Peter González":
                        player_name = "Peter Federico"
                    if player_name == "Abde Ezzalzouli":
                        player_name = "Ez Abde"
                    if player_name == "Jonathan Montiel":
                        player_name = "Joni Montiel"
                    if player_name == "Manu Fuster":
                        player_name = "Fuster"
                    probability = float(probability.replace('%', '')) / 100
                    team_probabilities[player_name] = probability
            probabilities_dict[team_name] = team_probabilities

        return probabilities_dict

    def scrape(self):
        self.fetch_page(self.base_url)
        # self.accept_cookies()
        team_options = self.get_team_options()
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

        player_elements = self.get_player_elements()
        for player_element in player_elements:
            name, price, position, team_id, form, price_trend = self.get_player_data(player_element)
            team_name = team_options.get(team_id)
            position_name = positions_normalize.get(position)
            if team_name:
                prices_dict[team_name][name] = price
                positions_dict[team_name][name] = position_name
                forms_dict[team_name][name] = form
                price_trends_dict[team_name][name] = price_trend

        probabilities_dict = self.scrape_probabilities()

        self.driver.quit()
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
        if (
                os.path.isfile(ROOT_DIR + '/csv_files/' + price_file_name + '.csv') and
                os.path.isfile(ROOT_DIR + '/csv_files/' + positions_file_name + '.csv') and
                os.path.isfile(ROOT_DIR + '/csv_files/' + forms_file_name + '.csv') and
                os.path.isfile(ROOT_DIR + '/csv_files/' + start_probability_file_name + '.csv') and
                os.path.isfile(ROOT_DIR + '/csv_files/' + price_trends_file_name + '.csv')
        ):
            prices_data = read_dict_from_csv(price_file_name)
            positions_data = read_dict_from_csv(positions_file_name)
            forms_data = read_dict_from_csv(forms_file_name)
            start_probabilities_data = read_dict_from_csv(start_probability_file_name)
            price_trends_data = read_dict_from_csv(price_trends_file_name)
            return prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data

    scraper = FutbolFantasyScraper()
    prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data = scraper.scrape()

    overwrite_dict_to_csv(prices_data, price_file_name)
    overwrite_dict_to_csv(positions_data, positions_file_name)
    overwrite_dict_to_csv(forms_data, forms_file_name)
    overwrite_dict_to_csv(start_probabilities_data, start_probability_file_name)
    overwrite_dict_to_csv(price_trends_data, price_trends_file_name)

    return prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data

def get_players_prices_dict(
        file_name="futbolfantasy_prices",
        force_scrape=False
):
    if not force_scrape:
        if os.path.isfile(ROOT_DIR + '/csv_files/' + file_name + '.csv'):
            data = read_dict_from_csv(file_name)
            return data

    scraper = FutbolFantasyScraper()
    result, _, _, _, _ = scraper.scrape()

    overwrite_dict_to_csv(result, file_name)

    return result

def get_players_positions_dict(
        file_name="futbolfantasy_positions",
        force_scrape=False
):
    if not force_scrape:
        if os.path.isfile(ROOT_DIR + '/csv_files/' + file_name + '.csv'):
            data = read_dict_from_csv(file_name)
            return data

    scraper = FutbolFantasyScraper()
    _, result, _, _, _ = scraper.scrape()

    overwrite_dict_to_csv(result, file_name)

    return result

def get_players_forms_dict(
        file_name="futbolfantasy_forms",
        force_scrape=False
):
    if not force_scrape:
        if os.path.isfile(ROOT_DIR + '/csv_files/' + file_name + '.csv'):
            data = read_dict_from_csv(file_name)
            return data

    scraper = FutbolFantasyScraper()
    _, _, result, _, _ = scraper.scrape()

    overwrite_dict_to_csv(result, file_name)

    return result

def get_players_start_probabilities_dict(
        file_name="futbolfantasy_start_probabilities",
        force_scrape=False
):
    if not force_scrape:
        if os.path.isfile(ROOT_DIR + '/csv_files/' + file_name + '.csv'):
            data = read_dict_from_csv(file_name)
            return data

    scraper = FutbolFantasyScraper()
    _, _, _, result, _ = scraper.scrape()

    overwrite_dict_to_csv(result, file_name)

    return result

def get_players_price_trends_dict(
        file_name="futbolfantasy_price_trends",
        force_scrape=False
):
    if not force_scrape:
        if os.path.isfile(ROOT_DIR + '/csv_files/' + file_name + '.csv'):
            data = read_dict_from_csv(file_name)
            return data

    scraper = FutbolFantasyScraper()
    _, _, _, _, result = scraper.scrape()

    overwrite_dict_to_csv(result, file_name)

    return result


# prices, positions, forms, start_probabilities, price_trends = get_futbolfantasy_data(
#     price_file_name="futbolfantasy_laliga_players_prices",
#     positions_file_name="futbolfantasy_laliga_players_positions",
#     forms_file_name="futbolfantasy_laliga_players_forms",
#     start_probability_file_name="futbolfantasy_laliga_players_start_probabilities",
#     price_trends_file_name="futbolfantasy_laliga_players_price_trends",
#     force_scrape=False
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
