import json
from dataclasses import asdict
from pprint import pprint

import requests
import tls_requests
from datetime import datetime
from tqdm import tqdm
import urllib3
from urllib3.exceptions import ReadTimeoutError

from player import Player, get_position, get_status  # assumes existing Player class and get_position utility
from useful_functions import find_similar_string, read_dict_data, overwrite_dict_data

# Base URLs
PLAYERS_URL = "https://api-fantasy.llt-services.com/api/v4/players?x-lang=es"
PLAYERS_URL_MARKET = "https://api-fantasy.llt-services.com/api/v3/players?x-lang=es"
MARKET_VALUE_URL = "https://api-fantasy.llt-services.com/api/v3/player/{player_id}/market-value?x-lang=es"


def get_laligafantasy_data(
        write_file=False,
        file_name="laligafantasy_laliga_data",
        force_scrape=False
):
    data = None
    json_data = {}
    if force_scrape:
        try:
            data = create_players_list()
            json_data = [
                {k[1:] if k.startswith("_") else k: v for k, v in obj.__dict__.items()}
                for obj in data
            ]
        except:
            pass
    if not data: # if force_scrape failed or not force_scrape
        json_data = read_dict_data(file_name)
        data = [Player(**d) for d in json_data]
        if data:
            for player_data in data:
                player_data.price = int(round(player_data.price / 1_000_000))
            return data

    if write_file:
        # write_dict_data(json_data, file_name)
        overwrite_dict_data(json_data, file_name, ignore_old_data=True)

    for player_data in data:
        player_data.price = int(round(player_data.price / 1_000_000))

    return data

def fetch_json(url):
    """
    Fetch JSON data from URL.
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    # resp = requests.get(url, headers=headers, verify=False)
    resp = tls_requests.get(url, headers=headers, verify=False)
    resp.raise_for_status()
    return resp.json()

def get_all_players(players_url):
    """
    Returns the raw list of all players from the LLT Fantasy API.
    """
    return fetch_json(players_url)

def get_player_market_history(player_id):
    """
    Returns the market value history for a given player.
    """
    url = MARKET_VALUE_URL.format(player_id=player_id)
    return fetch_json(url)

def get_price_and_trend(player_id, market_price=None):
    """
    Fetch the latest market value and compute trend (difference between last two entries).
    Returns (price, price_trend).
    """
    history = get_player_market_history(player_id)
    if len(history) <= 0:
        latest = 0
        trend = 0
    elif 1 <= len(history) < 2:
        latest = history[-1]['marketValue']
        trend = 0
    else:
        sorted_hist = sorted(history, key=lambda e: datetime.fromisoformat(e['date']))
        latest = sorted_hist[-1]['marketValue']
        previous = sorted_hist[-2]['marketValue']
        trend = latest - previous

    if market_price and market_price != latest:
        # Then market_price is the actual latest because PLAYERS_URL_MARKET updates faster than get_player_market_history
        trend = market_price - latest
        latest = market_price

    return latest, trend

def create_players_list():
    """
    Build and return a list of Player objects with up-to-date price and trend.
    """
    raw_players = get_all_players(PLAYERS_URL)
    raw_players_with_market = get_all_players(PLAYERS_URL_MARKET)
    players = []

    market_players_dict = {}
    for raw_market in raw_players_with_market:
        market_players_dict[raw_market.get('id')] = int(raw_market.get('marketValue'))

    for raw in tqdm(raw_players, desc='Procesando jugadores', unit='jugador'):
        pid = raw.get('id')
        name = raw.get('nickname')
        pos_id = raw.get('positionId')
        position = get_position(pos_id)
        team_info = raw.get('team', {})
        team_name = team_info.get('name')
        status_id = raw.get('playerStatus')
        status = get_status(status_id)
        img_link = raw.get('images', {}).get('transparent', {}).get('256x256')

        market_price = market_players_dict.get(pid, None)
        price, trend = get_price_and_trend(pid, market_price)

        if pos_id != "5":
            player = Player(
                name=name,
                position=position,
                price=price,
                value=0,
                team=team_name,
                status=status,
                standard_price=price,
                # fantasy_price=price,
                price_trend=trend,
                form=1+trend/price if price else 1,
                fitness=[],
                img_link=img_link
            )
            players.append(player)

    players.sort(key=lambda p: p.price, reverse=True)
    return players


# data = get_laligafantasy_data(force_scrape=True, file_name="test_laligafantasy_laliga_data", write_file=True)
# for d in data:
#     print(d)

# all_players = get_laligafantasy_data()
# current_players = sorted(
#     all_players,
#     key=lambda x: (-x.value, -x.form, -x.fixture, -x.price, x.team, x.name),
#     reverse=False
# )
# for p in current_players:
#     print(p)
