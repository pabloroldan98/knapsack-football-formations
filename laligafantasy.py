import requests
import tls_requests
from datetime import datetime
from tqdm import tqdm

from player import Player, get_position, get_status  # assumes existing Player class and get_position utility
from useful_functions import find_similar_string, read_dict_data, overwrite_dict_data

# Base URLs
PLAYERS_URL = "https://api-fantasy.llt-services.com/api/v4/players?x-lang=es"
# PLAYERS_URL = "https://api-fantasy.llt-services.com/api/v3/players?x-lang=es"
MARKET_VALUE_URL = "https://api-fantasy.llt-services.com/api/v3/player/{player_id}/market-value?x-lang=es"

def fetch_json(url):
    """
    Fetch JSON data from URL.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    # resp = requests.get(url, headers=headers)
    resp = tls_requests.get(url, headers=headers, verify=False)
    resp.raise_for_status()
    return resp.json()

def get_all_players():
    """
    Returns the raw list of all players from the LLT Fantasy API.
    """
    return fetch_json(PLAYERS_URL)

def get_player_market_history(player_id):
    """
    Returns the market value history for a given player.
    """
    url = MARKET_VALUE_URL.format(player_id=player_id)
    return fetch_json(url)

def get_price_and_trend(player_id, in_millions=True):
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

    if in_millions:
        return int(latest / 1_000_000), int(trend / 1_000_000)
    return latest, trend

def create_players_list(use_millions=True):
    """
    Build and return a list of Player objects with up-to-date price and trend.
    """
    raw_players = get_all_players()
    players = []

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

        price, trend = get_price_and_trend(pid, in_millions=use_millions)

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
                fitness=[],
                img_link=img_link
            )
            players.append(player)

    players.sort(key=lambda p: p.price, reverse=True)
    return players


# all_players = create_players_list()
# current_players = sorted(
#     all_players,
#     key=lambda x: (-x.value, -x.form, -x.fixture, -x.price, x.team, x.name),
#     reverse=False
# )
# for p in current_players:
#     print(p)
#
# # Extract and display all distinct statuses
# statuses = sorted({p.status for p in all_players})
# print('Statuses found:')
# for status in statuses:
#     print(f'- {status}')
