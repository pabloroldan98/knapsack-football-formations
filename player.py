import ast
import base64
import copy
import csv
import io
import itertools
import numpy as np
from PIL import Image
from matplotlib import pyplot as plt
from tqdm import tqdm
from unidecode import unidecode
import os
from pprint import pprint

from analiticafantasy import get_players_start_probabilities_dict_analiticafantasy, \
    get_players_price_trends_dict_analiticafantasy, get_players_forms_dict_analiticafantasy, \
    get_players_prices_dict_analiticafantasy, get_players_positions_dict_analiticafantasy
from futbolfantasy_analytics import get_players_start_probabilities_dict_futbolfantasy, \
    get_players_price_trends_dict_futbolfantasy, get_players_forms_dict_futbolfantasy, \
    get_players_prices_dict_futbolfantasy, get_players_positions_dict_futbolfantasy
from futmondo import get_players_positions_dict_futmondo
from jornadaperfecta import get_players_start_probabilities_dict_jornadaperfecta, \
    get_players_positions_dict_jornadaperfecta, get_players_prices_dict_jornadaperfecta, \
    get_players_price_trends_dict_jornadaperfecta, get_players_forms_dict_jornadaperfecta
from pundit import get_players_start_probabilities_dict_pundit
from rotowire import get_players_start_probabilities_dict_rotowire
from scout import get_players_start_probabilities_dict_scout
from sportsgambler import get_players_start_probabilities_dict_sportsgambler
from useful_functions import find_similar_string, find_string_positions, write_dict_data, read_dict_data, \
    overwrite_dict_data

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root


class Player:
    def __init__(
            self,
            name: str,
            position: str = "GK",
            price: int = 100000,
            value: float = 0,
            team: str = "Spain",
            team_elo: float = 0,
            opponent: str = "France",
            opponent_elo: float = 0,
            status: str = "ok",
            standard_price: float = 0,
            fantasy_price: float = 0,
            price_trend: float = 0,
            fitness: list = [None, None, None, None, None],
            penalties: list = [False, False, False, False, False, False],
            penalty_saves: list = [False, False, False, False, False, False, False, False, False, False, False],
            penalty_boost: float = 0,
            strategy_boost: float = 0,
            team_history: list = [],
            team_history_boost: float = 0,
            sofascore_rating: float = 0,
            next_match_elo_dif: float = 0,
            is_playing_home: bool = False,
            form:  float = 0,
            fixture:  float = 0,
            form_arrow: str = "https://www.calculadorafantasy.com/img/arrows/0.png",
            fixture_arrow: str = "https://www.calculadorafantasy.com/img/arrows/0.png",
            start_probability:  float = 0,
            img_link: str = "https://cdn.biwenger.com/i/p/XXXXX.png",
            show_value: float = 0,
    ):
        self.name = name
        self._position = position
        self.price = price
        self.value = value
        self.team = team
        self.team_elo = team_elo
        self.opponent = opponent
        self.opponent_elo = opponent_elo
        self.status = status
        self.standard_price = standard_price
        self.fantasy_price = fantasy_price
        self.price_trend = price_trend
        self.fitness = fitness
        self._penalties = penalties
        self.penalty_saves = penalty_saves
        self.penalty_boost = penalty_boost
        self.strategy_boost = strategy_boost
        self.team_history = team_history
        self.team_history_boost = team_history_boost
        self.sofascore_rating = sofascore_rating
        self.next_match_elo_dif = next_match_elo_dif
        self.is_playing_home = is_playing_home
        self.form = form
        self.fixture = fixture
        self.form_arrow = form_arrow
        self.fixture_arrow = fixture_arrow
        self.start_probability = start_probability
        self.img_link = img_link
        self.show_value = show_value

    def __str__(self):
        return f"({self.name}, {self.position}, {self.team}, {self.price}, {self.value:.3f}, {self.status}) - (form: {self.form:.4f}, fixture: {self.fixture:.4f}) --> {self.start_probability*100:.0f} %"
        # return f"({self.name}, {self.position}, {self.team}, {self.price}, {self.show_value:.1f}, {self.status}) - (form: {self.form:.4f}, fixture: {self.fixture:.4f}) --> {self.start_probability*100:.0f} %"
        # return f"({self.name}, {self.position}, {self.price}, {self.value:.3f}, {self.team}, {self.status}) - (form: {self.form:.4f}, fixture: {self.fixture:.4f})"
        # return f"({self.name}, {self.position}, {self.price}, {self.value}, {self.team})"

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, pos="GK"):
        if pos not in ["GK", "DEF", "MID", "ATT"]:
            raise ValueError("Sorry, that's not a valid position")
        self._position = pos

    @property
    def penalties(self):
        return self._penalties

    @penalties.setter
    def penalties(self, indexes=[]):
        result = [False] * len(self.penalties)  # Initialize a new list of False values
        for idx in indexes:
            if 0 <= idx < len(result):
                result[idx] = True
        self._penalties = result

    def get_group(self):
        if self.position == "GK":
            group = 1
        elif self.position == "DEF":
            group = 2
        elif self.position == "MID":
            group = 3
        else:
            group = 4
        return group

    def has_played_last_match(self):
        if self.fitness[0] is not None:
            return True
        else:
            return False

    def __eq__(self, other_player):
        if unidecode(str(self.name)).lower().replace(" ", "").replace("-", "") in unidecode(str(other_player.name)).lower().replace(" ", "").replace("-", "") \
                or unidecode(str(other_player.name)).lower().replace(" ", "").replace("-", "") in unidecode(str(self.name)).lower().replace(" ", "").replace("-", ""):
            return True
        else:
            return False

    def stricter_equal(self, other_player):
        if unidecode(str(self.name)).lower().replace(" ", "").replace("-", "") == unidecode(str(other_player.name)).lower().replace(" ", "").replace("-", ""):
            return True
        else:
            return False

    def calc_value(self, no_form=False, no_fixtures=False, no_home_boost=False, alt_fixture_method=False, alt_forms=False, ignore_gk_fixture=None, nerf_form=False, skip_arrows=True, arrows_data=None):
        if alt_forms:
            # form_coef = (np.log1p(np.abs(self.price_trend * (self.standard_price - self.price_trend) / 1000000000)) * np.sign(self.price_trend)) / 235 + 1
            # form_coef = (np.log1p(np.log1p(np.abs(self.price_trend * (self.standard_price / (self.standard_price - self.price_trend)) / 100000))) * np.sign(self.price_trend)) * 3.5 / 100 + 1
            price_trend_percent = 100 * self.price_trend / (self.standard_price - self.price_trend) if self.standard_price != self.price_trend else 0
            prod_percent_trend = price_trend_percent * self.price_trend
            form_coef = (np.log1p(np.log1p(np.abs(prod_percent_trend / 100000))) * np.sign(self.price_trend)) * 3 / 100 + 1
        else:
            # # form_coef = ((self.price_trend / np.log1p(self.standard_price)) / 300000) * 1.75 * 0.9 + 1
            # price_trend_percent = 100 * self.price_trend / (self.standard_price - self.price_trend) if self.standard_price != self.price_trend else 0
            # prod_percent_price = price_trend_percent * self.standard_price * 0.5
            # form_coef = (np.log1p(np.log1p(np.abs(prod_percent_price / 1000000))) * np.sign(self.price_trend)) * 3 * 1.1 / 100 + 1
            price_trend_percent = 100 * self.price_trend / (self.standard_price - self.price_trend) if self.standard_price != self.price_trend else 0
            prod_percent_price = self.price_trend * self.standard_price if np.sign(self.price_trend) == 1 else price_trend_percent * self.price_trend * 1000000
            aux_coef = np.log1p(np.log1p(np.abs(prod_percent_price / 100000)))
            aux_coef_extra = max(aux_coef - 2.5, 0)
            form_coef = aux_coef_extra * np.sign(self.price_trend) * 13 / 100 + 1
            if nerf_form:
                form_coef = aux_coef_extra * np.sign(self.price_trend) * 10 / 100 + 1

        if no_form:
            form_coef = 1

        if alt_fixture_method:
            # capped_elo_dif = math.log(abs(self.next_match_elo_dif), 10) if self.next_match_elo_dif != 0 else 0
            # # if self.position == "GK":
            # #     capped_elo_dif = capped_elo_dif * 0.2
            # base_coef = capped_elo_dif * 0.0075 + 1 if self.next_match_elo_dif >= 0 else 1 - capped_elo_dif * 0.015
            capped_elo_dif = self.next_match_elo_dif
            if self.position == "GK" and ignore_gk_fixture != False:
                capped_elo_dif = capped_elo_dif * 0.2

            capped_elo_dif = np.sign(capped_elo_dif) * 0.01 * (np.abs(capped_elo_dif) / 100.0) ** 0.8
            capped_elo_dif *= (
                1.25
                if capped_elo_dif < 0.04
                else (1.25 - (capped_elo_dif - 0.04) * 25)
                if capped_elo_dif < 0.05
                else 1.00
            )
            base_coef = capped_elo_dif + 1
        else:
            # capped_elo_dif = min(250.0, max(-250.0, self.next_match_elo_dif))
            # capped_elo_dif = min(400.0, max(-400.0, self.next_match_elo_dif))
            # capped_elo_dif = min(450.0, max(-450.0, self.next_match_elo_dif))
            capped_elo_dif = self.next_match_elo_dif
            if self.position == "GK" and ignore_gk_fixture == True:
                capped_elo_dif = capped_elo_dif * 0.2

            capped_elo_dif = np.sign(capped_elo_dif) * np.log1p(abs(capped_elo_dif/1000))
            base_coef = capped_elo_dif * 1.25 / 10 + 1
        if no_fixtures:
            fixture_coef = 1
        else:
            fixture_coef = base_coef

        home_bonus = 0.005 if self.is_playing_home else 0
        # fixture_coef = 1 if self.position == "GK" else fixture_coef
        fixture_coef += home_bonus if not no_home_boost else 0
        fixture_coef += self.team_history_boost

        # if not alt_forms or (alt_forms and self.form == 0):
        #     self.form = form_coef
        self.form = form_coef
        self.fixture = fixture_coef

        if not skip_arrows:
            self.form_arrow = get_arrow_image(form_coef, arrows_data, avoid_png=True)
            self.fixture_arrow = get_arrow_image(fixture_coef, arrows_data, avoid_png=True)

        predicted_value = ((float(self.sofascore_rating) * float(self.form)) + float(self.penalty_boost) + float(self.strategy_boost)) * float(self.fixture)
        return predicted_value

    def calc_show_value(self, value=None):
        if not value:
            value = self.value
        round_value = round(value, 1)

        if round_value <= 0.9:
            predicted_show_value = -7
        elif 1.0 <= round_value <= 4.9:
            predicted_show_value = -6
        elif 5.0 <= round_value <= 5.1:
            predicted_show_value = -5
        elif 5.2 <= round_value <= 5.3:
            predicted_show_value = -4
        elif 5.4 <= round_value <= 5.5:
            predicted_show_value = -3
        elif 5.6 <= round_value <= 5.7:
            predicted_show_value = -2
        elif 5.8 <= round_value <= 5.9:
            predicted_show_value = -1
        elif 6.0 <= round_value <= 6.1:
            predicted_show_value = 0
        elif 6.2 <= round_value <= 6.3:
            predicted_show_value = 1
        elif 6.4 <= round_value <= 6.5:
            predicted_show_value = 2
        elif 6.6 <= round_value <= 6.7:
            predicted_show_value = 3
        elif 6.8 <= round_value <= 6.9:
            predicted_show_value = 4
        elif 7.0 <= round_value <= 7.1:
            predicted_show_value = 5
        elif 7.2 <= round_value <= 7.3:
            predicted_show_value = 6
        elif 7.4 <= round_value <= 7.5:
            predicted_show_value = 7
        elif 7.6 <= round_value <= 7.7:
            predicted_show_value = 8
        elif 7.8 <= round_value <= 7.9:
            predicted_show_value = 9
        elif 8.0 <= round_value <= 8.1:
            predicted_show_value = 10
        elif 8.2 <= round_value <= 8.5:
            predicted_show_value = 11
        elif 8.6 <= round_value <= 8.9:
            predicted_show_value = 12
        elif 9.0 <= round_value <= 9.4:
            predicted_show_value = 13
        elif 9.5 <= round_value <= 10.0:
            predicted_show_value = 14
        elif 10.1 <= round_value:
            predicted_show_value = 15
        else:
            predicted_show_value = 0

        return predicted_show_value

    def set_player_value(self, no_form=False, no_fixtures=False, no_home_boost=False, alt_fixture_method=False, alt_forms=False, ignore_gk_fixture=None, nerf_form=False, skip_arrows=True, arrows_data=None):
        predicted_value = self.calc_value(no_form, no_fixtures, no_home_boost, alt_fixture_method=alt_fixture_method, alt_forms=alt_forms, ignore_gk_fixture=ignore_gk_fixture, nerf_form=nerf_form, skip_arrows=skip_arrows, arrows_data=arrows_data)
        self.value = predicted_value
        predicted_show_value = self.calc_show_value(predicted_value)
        self.show_value = predicted_show_value


def get_position(group):
    if group == 1 or group == "1":
        position = "GK"
    elif group == 2 or group == "2":
        position = "DEF"
    elif group == 3 or group == "3":
        position = "MID"
    elif group == 4 or group == "4":
        position = "ATT"
    else:
        position = "ATT"
    return position


def get_status(group):
    if group == "doubt" or group == "doubtful":
        status = "doubt"
    elif group == "injured" or group == "injured":
        status = "injured"
    elif group == "ok" or group == "ok":
        status = "ok"
    elif group == "sanctioned" or group == "suspended":
        status = "sanctioned"
    elif group == "unknown" or group == "out_of_league":
        status = "unknown"
    else:
        status = "unknown"
    return status


def purge_everything(players_list, teams_to_purge=[], mega_purge=False, probability_threshold=0.5, fixture_filter=False):
    purged_players = purge_no_team_players(players_list)
    purged_players = purge_negative_values(purged_players)
    if probability_threshold is None or mega_purge:
        purged_players = purge_injured_players(purged_players)
    purged_players = purge_non_starting_players(purged_players, probability_threshold)
    purged_players = purge_national_teams(purged_players, teams_to_purge)
    if mega_purge:
        purged_players = purge_worse_value_players(purged_players)
    if fixture_filter:
        purged_players = purge_bad_fixture_players_positions(purged_players)
    return purged_players


def purge_injured_players(players_list):
    result_players = [player for player in players_list if
                      (player.status == "ok") or (player.status == "warned") or (player.status == "unknown")]
    return result_players


def purge_no_team_players(players_list):
    result_players = [player for player in players_list if
                      player.team != "None"]
    return result_players


def purge_no_opponent_players(players_list, teams_dict):
    result_players = [player for player in players_list if
                      teams_dict[player.team].next_opponent is not None]
    return result_players


def purge_eliminated_players(players_list, qualified_teams):
    result_players = []
    for player in players_list:
        for team in qualified_teams:
            if player.team == team.name:
                result_players.append(player)
    return result_players


def purge_non_starting_players(players_list, probability_threshold=0.5):
    if probability_threshold and not all(player.start_probability == 0 for player in players_list):
        result_players = [
            player for player in players_list
            if (player.start_probability >= probability_threshold)
        ]
    else:
        result_players = [
            player for player in players_list
            if (len(player.fitness) <= 0) or
                (len(player.fitness) == 1 and isinstance(player.fitness[0], int)) or
                 (len(player.fitness) >= 2 and (isinstance(player.fitness[0], int) or isinstance(player.fitness[1], int)))
        ]
    return result_players


def purge_negative_values(players_list):
    result_players = [player for player in players_list if
                      player.value > 1]
    return result_players


def purge_national_teams(players_list, teams_to_purge):
    result_players = [player for player in players_list if
                      player.team not in teams_to_purge]
    return result_players


def purge_worse_value_players(players_list):
    result_players = copy.deepcopy(players_list)
    for player in result_players:
        for player_to_check in result_players:
            if player_to_check.price >= player.price \
                    and player_to_check.value < player.value \
                    and player_to_check.position == player.position:
                result_players.remove(player_to_check)
    return result_players


def purge_bad_fixture_players_positions(players_list):
    result_players = copy.deepcopy(players_list)
    # result_players = [player for player in result_players if not ((player.position == "GK") and (player.fixture < 0.965))]
    result_players = [player for player in result_players if not ((player.position == "GK") and (player.fixture < 0.9775))]
    result_players = [player for player in result_players if not ((player.position == "DEF") and (player.fixture < 0.985))]
    result_players = [player for player in result_players if not ((player.position == "MID") and (player.fixture < 0.97))]
    result_players = [player for player in result_players if not ((player.position == "ATT") and (player.fixture < 0.96))]
    return result_players


def fill_with_team_players(my_team, players_list):
    result_players = copy.deepcopy(players_list)
    past_players = []
    for p in my_team:
        for c in players_list:
            if p == c:
                past_players.append(c)
                break
    for p in result_players:
        for c in past_players:
            if p == c:
                past_players.remove(c)
                break
    result_players = result_players + past_players
    return result_players

def get_arrow_properties(value, min_value=0.96, max_value=1.05):
    # Compute angle (symmetric around 1)
    if value >= max_value:
        angle = 90
    elif value <= min_value:
        angle = -90
    elif value > 1:
        angle = (value - 1) / (max_value - 1) * 90
    elif value < 1:
        angle = (value - 1) / (1 - min_value) * 90
    else:
        angle = 0

    # Compute color
    if value >= max_value:
        color = (0, 1, 0)
    elif value <= min_value:
        color = (1, 0, 0)
    elif value == 1:
        color = (1, 1, 0)
    elif value < 1:
        ratio = (value - min_value) / (1 - min_value)
        color = (1, ratio, 0)
    else:
        ratio = (value - 1) / (max_value - 1)
        color = (1 - ratio, 1, 0)

    return angle, color

def get_arrow_image(value, arrows_data=None, min_value=0.96, max_value=1.05, size=0.6, avoid_png=False):
    rounded_value = str(round(value, 4))  # reduce number of unique values
    if arrows_data and rounded_value in arrows_data.keys():
        # return io.BytesIO(base64.b64decode(arrows_data[rounded_value]))
        return arrows_data[rounded_value]
    if avoid_png:
        if arrows_data and "1.0" in arrows_data.keys():
            return arrows_data["1.0"]
        else:
            return "./img/arrows/0.png"

    angle, color = get_arrow_properties(value, min_value, max_value)
    radians = np.deg2rad(angle)

    dx = size * np.cos(radians)
    dy = size * np.sin(radians)

    fig, ax = plt.subplots(figsize=(1, 1))
    start_x = -dx / 2
    start_y = -dy / 2

    ax.arrow(
        start_x, start_y, dx, dy,
        width=0.1,
        head_width=0.25,
        head_length=0.2,
        fc=color,
        ec='#1c1f26',
        lw=1.5,
        length_includes_head=True
    )

    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.set_aspect('equal')
    ax.axis('off')

    # Save figure to buffer (without bbox_inches='tight')
    buf = io.BytesIO()
    fig.savefig(buf, format='png', transparent=True, pad_inches=0)
    plt.close(fig)
    buf.seek(0)

    # Load and crop with PIL
    image = Image.open(buf).convert("RGBA")
    bbox = image.getbbox()  # Gets bounding box of non-transparent content
    cropped_image = image.crop(bbox)

    # Make it square by adding padding
    width, height = cropped_image.size
    max_side = max(width, height)

    square_image = Image.new("RGBA", (max_side, max_side), (255, 255, 255, 0))  # transparent background
    paste_x = (max_side - width) // 2
    paste_y = (max_side - height) // 2
    square_image.paste(cropped_image, (paste_x, paste_y))

    # cropped_buf = io.BytesIO()
    # square_image.save(cropped_buf, format='PNG')
    # cropped_buf.seek(0)
    #
    # return cropped_buf

    return square_image

def idx_from_value(v):  # integer name avoids float formatting headaches
    return int(round(v * 10000))

def get_arrows_data(
        write_file=False,
        file_name="arrows_data",
        force_scrape=False
):
    data = None
    if force_scrape:
        try:
            arrows_img_dir = "img/arrows"
            os.makedirs(arrows_img_dir, exist_ok=True)
            data = {}
            for idx in tqdm(range(9000, 11001)):  # 0.900 to 1.100 inclusive
                value = round(idx / 10000, 4)
                # arrow_img = get_arrow_image(value)
                # data[str(value)] = base64.b64encode(arrow_img.getvalue()).decode()
                png = get_arrow_image(value)
                png.save(os.path.join(arrows_img_dir, f"{idx}.png"), format="PNG", optimize=True)
                # data[str(value)] = f"https://www.calculadorafantasy.com/img/arrows/{idx}.png"
                data[str(value)] = f"./img/arrows/{idx}.png"
        except:
            pass
    if not data: # if force_scrape failed or not force_scrape
        data = read_dict_data(file_name)
        if data:
            return data

    if write_file:
        # write_dict_data(data, file_name)
        overwrite_dict_data(data, file_name, ignore_valid_file=True, ignore_old_data=True)

    return data
# get_arrows_data(True, "arrows_data", True)

def set_manual_boosts(players_list, manual_boosts):
    result_players = copy.deepcopy(players_list)
    for boosted_player in manual_boosts:
        for player in result_players:
            if boosted_player == player:
                player.penalty_boost = boosted_player.penalty_boost
                player.strategy_boost = boosted_player.strategy_boost
                break
    return result_players


def get_team_players_dict(players_list, full_players_data_dict, verbose=False): #, flag=False):
    result_players = copy.deepcopy(players_list)

    team_players_dict = {}
    for player in result_players:
        if player.team not in team_players_dict:
            team_players_dict[player.team] = {}
        team_players_dict[player.team][player.name] = []

    num_probability_files = 0
    for source, players_data_dict in full_players_data_dict.items():
        num_probability_files = num_probability_files + 1

        team_data_names_list = list(players_data_dict.keys())

        for player_team_name, players_in_team in team_players_dict.items():
            closest_player_data_team = find_similar_string(player_team_name, team_data_names_list, similarity_threshold=0)
            if closest_player_data_team:
                # if len(players_data_dict[closest_player_data_team]) >= 11:
                team_players_dict[player_team_name]["num_probability_files"] = num_probability_files
                for player_name, player_data in players_in_team.items():
                    player_data_names_list = list(players_data_dict[closest_player_data_team].keys())
                    # if source == "jornadaperfecta" and flag:
                    #     closest_player_data_name = find_similar_string(player_name, player_data_names_list, verbose=True)
                    closest_player_data_name = find_similar_string(player_name, player_data_names_list, verbose=False)
                    if closest_player_data_name:
                        new_data = players_data_dict[closest_player_data_team][closest_player_data_name]
                        old_player_data = player_data.copy()
                        new_data = old_player_data + [new_data]
                        if verbose:
                            if old_player_data != new_data:
                                print(f"{player_name}: {old_player_data} --> {new_data} ({closest_player_data_name})")
                        team_players_dict[player_team_name][player_name] = new_data
    return team_players_dict


def get_players_positions_dict(
        file_names=["futbolfantasy_positions", "analiticafantasy_positions", "jornadaperfecta_positions", ],
        force_scrape=False
):
    players_dict = {}
    for file_name in file_names:
        if "futbolfantasy" in file_name.lower():
            try:
                futbolfantasy_data = get_players_positions_dict_futbolfantasy(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["futbolfantasy"] = futbolfantasy_data
            except:
                pass
        elif "analiticafantasy" in file_name.lower():
            try:
                analiticafantasy_data = get_players_positions_dict_analiticafantasy(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["analiticafantasy"] = analiticafantasy_data
            except:
                pass
        elif "jornadaperfecta" in file_name.lower():
            try:
                jornadaperfecta_data = get_players_positions_dict_jornadaperfecta(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["jornadaperfecta"] = jornadaperfecta_data
            except:
                pass
        elif "futmondo" in file_name.lower():
            try:
                futmondo_data = get_players_positions_dict_futmondo(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["futmondo"] = futmondo_data
            except:
                pass
    return players_dict


def set_players_database(players_list, new_players_list, verbose=False):
    original_players = copy.deepcopy(players_list)
    result_players = copy.deepcopy(new_players_list)

    players_to_remove = set()

    team_names = list(set(p.team for p in original_players))
    # closest_players_names = [p.name for p in original_players]
    # new_players_names = [p.name for p in result_players]
    for player in result_players:
        player_needs_removal = True
        closest_team = find_similar_string(player.team, team_names)

        # Get LaLigaFantasy players in the closest team
        closest_team_players = [p for p in original_players if p.team == closest_team]
        closest_team_players_names = [p.name for p in closest_team_players]

        closest_name = find_similar_string(player.name, closest_team_players_names, fallback_none=True, verbose=False)

        if closest_name:
            # En este caso actualizas con los datos de LaLigaFantasy
            # original_player = next((p for p in closest_team_players if p.name == closest_name), None)
            original_player = next((p for p in original_players if p.name == closest_name), None)
            if original_player:
                player_needs_removal = False
                if verbose:
                    if player.name != closest_name:
                        print(f"{player.name} --> {closest_name}")
                player.name = original_player.name
                player.team = original_player.team
                player.fantasy_price = original_player.fantasy_price
                player.img_link = original_player.img_link

        ## DABA FALLO PORQUE HAY NOMBRES COMO WILLIAM, O NICO, QUE NO LOS PONE CON QUIEN DEBERÍA
        # else:
        #     # Reviso que no vaya a ser que esté en otro equipo
        #     closest_name = find_similar_string(player.name, closest_players_names, similarity_threshold=1, verbose=False)
        #     if closest_name and closest_name not in new_players_names:
        #         player_needs_removal = False
        #         original_player = next((p for p in original_players if p.name == closest_name), None)
        #         if original_player:
        #             if verbose:
        #                 if player.name != closest_name:
        #                     print(f"{player.name} --> {closest_name}")
        #             player.name = original_player.name
        #             player.team = original_player.team
        #             player.fantasy_price = original_player.fantasy_price

        if player_needs_removal:
            # Este es el caso en el que está en LaLigaFantasy y no en Biwenger, o que no lo haya cogido bien
            if verbose:
                print(f"{player.name} --> REMOVED ({player.status})")
            players_to_remove.add((player.name, player.team))
            # result_players.remove(player)
            # if player.status != "unknown":
            #     print(player)

    result_players = [
        player for player in result_players
        if (player.name, player.team) not in players_to_remove
    ]

    return result_players


def set_positions(players_list, full_players_positions_dict, verbose=False):
    result_players = copy.deepcopy(players_list)

    team_players_dict = get_team_players_dict(result_players, full_players_positions_dict, verbose)

    for player in result_players:
        positions = team_players_dict[player.team][player.name].copy()
        valid_positions = [p for p in positions if p is not None]
        new_position = valid_positions[0] if valid_positions else None
        if new_position:
            if verbose:
                if player.position != new_position:
                    print(f"{player.name}: {positions} --> {new_position}")
            player.position = new_position

    return result_players


def get_players_prices_dict(
        file_names=["futbolfantasy_prices", "analiticafantasy_prices", "jornadaperfecta_prices", ],
        force_scrape=False
):
    players_dict = {}
    for file_name in file_names:
        if "futbolfantasy" in file_name.lower():
            try:
                futbolfantasy_data = get_players_prices_dict_futbolfantasy(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["futbolfantasy"] = futbolfantasy_data
            except:
                pass
        elif "analiticafantasy" in file_name.lower():
            try:
                analiticafantasy_data = get_players_prices_dict_analiticafantasy(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["analiticafantasy"] = analiticafantasy_data
            except:
                pass
        elif "jornadaperfecta" in file_name.lower():
            try:
                jornadaperfecta_data = get_players_prices_dict_jornadaperfecta(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["jornadaperfecta"] = jornadaperfecta_data
            except:
                pass
    return players_dict


def set_prices(players_list, full_players_prices_dict, verbose=False):
    result_players = copy.deepcopy(players_list)

    team_players_dict = get_team_players_dict(result_players, full_players_prices_dict, verbose)

    for player in result_players:
        prices = team_players_dict[player.team][player.name].copy()
        valid_prices = [p for p in prices if p is not None]
        new_price = valid_prices[0] if valid_prices else round(float(player.standard_price) * 5)
        new_price = round(float(new_price) / 1000000)
        if new_price:
            if verbose:
                if player.price != new_price:
                    print(f"{player.name}: {prices} --> {new_price}")
            player.price = new_price

    return result_players


def get_players_price_trends_dict(
        file_names=["futbolfantasy_price_trends", "analiticafantasy_price_trends", "jornadaperfecta_price_trends", ],
        force_scrape=False
):
    players_dict = {}
    for file_name in file_names:
        if "futbolfantasy" in file_name.lower():
            try:
                futbolfantasy_data = get_players_price_trends_dict_futbolfantasy(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["futbolfantasy"] = futbolfantasy_data
            except:
                pass
        elif "analiticafantasy" in file_name.lower():
            try:
                analiticafantasy_data = get_players_price_trends_dict_analiticafantasy(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["analiticafantasy"] = analiticafantasy_data
            except:
                pass
        elif "jornadaperfecta" in file_name.lower():
            try:
                jornadaperfecta_data = get_players_price_trends_dict_jornadaperfecta(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["jornadaperfecta"] = jornadaperfecta_data
            except:
                pass
    return players_dict


def set_price_trends(players_list, full_players_price_trends_dict, full_players_standard_prices_dict=None, verbose=False):
    result_players = copy.deepcopy(players_list)

    team_players_dict = get_team_players_dict(result_players, full_players_price_trends_dict, verbose)

    for player in result_players:
        trends = team_players_dict[player.team][player.name].copy()
        valid_trends = [p for p in trends if p is not None]
        new_trend = valid_trends[0] if valid_trends else 0
        if new_trend:
            if verbose:
                if player.price_trend != new_trend:
                    print(f"{player.name}: {trends} --> {new_trend}")
            player.price_trend = new_trend


    if full_players_standard_prices_dict:
        result_players = copy.deepcopy(result_players)

        team_players_dict = get_team_players_dict(result_players, full_players_standard_prices_dict, verbose)

        for player in result_players:
            std_prices = team_players_dict[player.team][player.name].copy()
            valid_std_prices = [p for p in std_prices if p is not None]
            new_std_price = valid_std_prices[0] if valid_std_prices else None
            if new_std_price:
                if verbose:
                    if player.standard_price != new_std_price:
                        print(f"{player.name}: {std_prices} --> {new_std_price}")
                player.standard_price = new_std_price


    return result_players


def get_players_start_probabilities_dict(
        file_names=["futbolfantasy_start_probabilities", "analiticafantasy_start_probabilities", "jornadaperfecta_start_probabilities", "pundit_start_probabilities", "scout_start_probabilities", ],
        force_scrape=False
):
    players_dict = {}
    for file_name in file_names:
        if "futbolfantasy" in file_name.lower():
            try:
                futbolfantasy_data = get_players_start_probabilities_dict_futbolfantasy(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["futbolfantasy"] = futbolfantasy_data
            except:
                pass
        elif "analiticafantasy" in file_name.lower():
            try:
                analiticafantasy_data = get_players_start_probabilities_dict_analiticafantasy(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["analiticafantasy"] = analiticafantasy_data
            except:
                pass
        elif "jornadaperfecta" in file_name.lower():
            try:
                jornadaperfecta_data = get_players_start_probabilities_dict_jornadaperfecta(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["jornadaperfecta"] = jornadaperfecta_data
            except:
                pass
        elif "pundit" in file_name.lower():
            try:
                pundit_data = get_players_start_probabilities_dict_pundit(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["pundit"] = pundit_data
            except:
                pass
        elif "scout" in file_name.lower():
            try:
                scout_data = get_players_start_probabilities_dict_scout(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["scout"] = scout_data
            except:
                pass
        elif "rotowire" in file_name.lower():
            try:
                rotowire_data = get_players_start_probabilities_dict_rotowire(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["rotowire"] = rotowire_data
            except:
                pass
        elif "sportsgambler" in file_name.lower():
            try:
                sportsgambler_data = get_players_start_probabilities_dict_sportsgambler(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["sportsgambler"] = sportsgambler_data
            except:
                pass
    return players_dict


def set_start_probabilities(players_list, full_players_start_probabilities_dict, verbose=False):
    result_players = copy.deepcopy(players_list)

    team_players_dict = get_team_players_dict(result_players, full_players_start_probabilities_dict, verbose) #, True)
    # num_probability_files = len(full_players_start_probabilities_dict)

    for player in result_players:
        start_probabilities = team_players_dict[player.team][player.name].copy()
        valid_probs = [p for p in start_probabilities if p is not None]
        new_start_probability = round(sum(valid_probs) / len(valid_probs), 4) if valid_probs else 0
        num_probability_files = team_players_dict[player.team]["num_probability_files"]
        if 0 < num_probability_files <= 2:
            new_start_probability = round(sum(valid_probs) / num_probability_files, 4) if valid_probs else 0
        # if player.status == "sanctioned":
        #     new_start_probability = 0
        if new_start_probability:
            if verbose:
                if player.start_probability != new_start_probability:
                    print(f"{player.name}: {start_probabilities} --> {new_start_probability}")
            player.start_probability = new_start_probability
        # if len(valid_probs) == 1 and new_start_probability>=0.5:
        #     print(player.name)
        #     print(player.team)
        #     print(start_probabilities)
        #     print(new_start_probability)

    return result_players


def get_players_forms_dict(
        file_names=["futbolfantasy_forms", "analiticafantasy_forms", "jornadaperfecta_forms", ],
        force_scrape=False
):
    players_dict = {}
    for file_name in file_names:
        if "futbolfantasy" in file_name.lower():
            try:
                futbolfantasy_data = get_players_forms_dict_futbolfantasy(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["futbolfantasy"] = futbolfantasy_data
            except:
                pass
        elif "analiticafantasy" in file_name.lower():
            try:
                analiticafantasy_data = get_players_forms_dict_analiticafantasy(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["analiticafantasy"] = analiticafantasy_data
            except:
                pass
        elif "jornadaperfecta" in file_name.lower():
            try:
                jornadaperfecta_data = get_players_forms_dict_jornadaperfecta(
                    file_name=file_name,
                    force_scrape=force_scrape,
                )
                players_dict["jornadaperfecta"] = jornadaperfecta_data
            except:
                pass
    return players_dict


def set_forms(players_list, full_players_forms_dict, verbose=False):
    result_players = copy.deepcopy(players_list)

    team_players_dict = get_team_players_dict(result_players, full_players_forms_dict, verbose)

    for player in result_players:
        forms = team_players_dict[player.team][player.name].copy()
        valid_forms = [p for p in forms if p is not None]
        new_form = valid_forms[0] if valid_forms else None
        if new_form:
            new_form = 1 + float(new_form)/100
            if verbose:
                if player.form != new_form:
                    print(f"{player.name}: {forms} --> {new_form}")
            player.form = new_form

    return result_players


def set_penalty_takers_boosts(players_list, penalty_takers_dict):
    result_players = copy.deepcopy(players_list)

    team_names_list = list(set(player.team for player in result_players))

    for team_name, penalty_takers_names_list in penalty_takers_dict.items():
        closest_team_name = find_similar_string(team_name, team_names_list)
        players_names_list = list(set(player.name for player in players_list if player.team == closest_team_name))
        for penalty_taker_name in penalty_takers_names_list:
            closest_player_name = find_similar_string(penalty_taker_name, players_names_list, verbose=False)
            for player in result_players:
                if player.name == closest_player_name:
                    players_penalties = find_string_positions(penalty_takers_names_list, penalty_taker_name)
                    player.penalties = players_penalties
                    players_penalties_bool_list = [i in players_penalties for i in range(max(players_penalties) + 1)]
                    player.penalty_boost = calc_penalty_boost(players_penalties_bool_list)

        # for player in result_players:
        #     if player.team == closest_team_name:
        #         closest_penalty_taker_name = find_similar_string(player.name, penalty_takers_names_list, verbose=True)
        #         if closest_penalty_taker_name is not None:
        #             players_penalties = find_string_positions(penalty_takers_names_list, closest_penalty_taker_name)
        #             player.penalties = players_penalties
        #             player.penalty_boost = calc_penalty_boost(players_penalties)
    return result_players


def set_penalty_savers_boosts(players_list, penalty_savers_dict):
    result_players = copy.deepcopy(players_list)

    team_names_list = list(set(player.team for player in result_players))

    for team_name, penalty_savers in penalty_savers_dict.items():
        closest_team_name = find_similar_string(team_name, team_names_list)
        players_names_list = list(set(player.name for player in players_list if player.team == closest_team_name))
        for player_name, player_penalty_saves in penalty_savers.items():
            closest_player_name = find_similar_string(player_name, players_names_list, verbose=False)
            for player in result_players:
                if player.name == closest_player_name:
                    player.penalty_saves = player_penalty_saves
                    player.penalty_boost = calc_penalty_boost(player_penalty_saves)

    return result_players

def calc_penalty_boost(players_penalties):
    penalty_coef = 0
    penalty_indexes = [index for index, value in enumerate(players_penalties) if value]
    # Not Goalkeepers
    if len(players_penalties) < 10:
        for penalty_index in penalty_indexes:
            # if penalty_index < 6: # Take only last 6 pens into account
            #     penalty_coef = penalty_coef + 0.175 - (penalty_index * 0.025)
            if penalty_index < 5: # Take only last 5 pens into account
                penalty_coef = penalty_coef + 0.21 - (penalty_index * 0.05)
    # Goalkeepers
    else:
        for penalty_index in penalty_indexes:
            if penalty_index < 11: # Take only last 11 pens into account
                penalty_coef = penalty_coef + 0.015 - (penalty_index * 0.001)
        penalty_coef = penalty_coef * 0.5

    return penalty_coef


def get_biwenger_transfermarket_teams_dict(biwenger_team_names_list, transfermarket_team_names_list, extra_teams_list, file_name="biwenger_transfermarket_teams"):
    if os.path.isfile('./' + file_name + '.csv'):
        return read_dict_data(file_name)
    result_biwenger_transfermarket_teams_dict = dict()

    full_biwenger_team_names_list = biwenger_team_names_list + extra_teams_list
    for biwenger_team_name in full_biwenger_team_names_list:
        closest_transfermarket_team_name = find_similar_string(biwenger_team_name, transfermarket_team_names_list)
        result_biwenger_transfermarket_teams_dict[biwenger_team_name] = closest_transfermarket_team_name

    return result_biwenger_transfermarket_teams_dict


def set_team_history_boosts(players_list, players_team_history_dict, extra_teams, verbose=False):
    result_players = copy.deepcopy(players_list)

    team_names_list = list(set(player.team for player in result_players))
    transfermarket_team_names_list = list(players_team_history_dict.keys())
    extra_teams_list = list(itertools.chain.from_iterable(extra_teams))
    biwenger_transfermarket_teams_dict = get_biwenger_transfermarket_teams_dict(team_names_list, transfermarket_team_names_list, extra_teams_list) #, file_name="biwenger_transfermarket_laliga_teams")

    for team_name, team_players_history in players_team_history_dict.items():
        closest_team_name = find_similar_string(team_name, team_names_list)
        players_names_list = list(set(player.name for player in players_list if player.team == closest_team_name))
        for player_name, player_team_history in team_players_history.items():
            closest_player_name = find_similar_string(player_name, players_names_list, verbose=False)
            for player in result_players:
                if player.name == closest_player_name:
                    player.team_history = player_team_history
                    transfermarket_opponent_name = biwenger_transfermarket_teams_dict[player.opponent]
                    player.team_history_boost = calc_team_history_boost(player_team_history, transfermarket_opponent_name)
                    if verbose:
                        if player.team_history_boost != 0:
                            print(f"{player.name}: {player.team} --> {player.opponent} ({player.team_history_boost:.4f})")

    return result_players


def calc_team_history_boost(team_history, opponent):
    # # closest_opponent_name = find_similar_string(opponent, team_history)
    # # return 0.005 if closest_opponent_name else 0
    # return 0.005 if opponent in team_history else 0
    # We don't pop the current team out of the team_history since it works better for the calculation since it is ordered by matches in a team
    if opponent not in team_history:
        return 0
    position = team_history.index(opponent)
    length = len(team_history)
    # Interpolate between 0.01 (first position) and 0.005 (last position)
    # return 0.01 if position == 0 else 0.005 if position == length - 1 else 0.01 - (position / (length - 1)) * 0.005
    # return 0.0075 if position == 0 else 0.0025 if position == length - 1 else 0.0075 - (position / (length - 1)) * 0.0025
    return 0.005 if position == 0 else 0.0025 if position == length - 1 else 0.005 - (position / (length - 1)) * 0.0025


def set_players_elo_dif(players_list, teams_list):
    teams_dict = {team.name: team for team in teams_list}

    result_players = copy.deepcopy(players_list)
    clean_players = purge_no_team_players(result_players)
    clean_players = purge_eliminated_players(clean_players, teams_list)
    clean_players = purge_no_opponent_players(clean_players, teams_dict)

    # checked_teams = check_teams(clean_players, teams_list)
    # if len(checked_teams) != len(teams_list):
    #     print("The following teams do NOT match your Databases:")
    #     for team in teams_list:
    #         if team.name not in checked_teams:
    #             print(team.name)
    #     print()

    for player in clean_players:
        player_team = teams_dict[player.team]
        opponent_team = teams_dict[player_team.next_opponent]
        elo_dif = player_team.elo - opponent_team.elo
        player.next_match_elo_dif = elo_dif
        player.is_playing_home = player_team.is_home

        player.team_elo = player_team.elo
        player.opponent_elo = opponent_team.elo
        player.opponent = opponent_team.name
    return clean_players


def check_teams(players_list, teams_list):
    count = dict()
    for player in players_list:
        for team in teams_list:
            if player.team == team.name:
                count[player.team] = player.team
    return count


def set_players_sofascore_rating(
        players_list,
        players_ratings_list,
        write_file=True,
        file_name="player_names_biwenger_sofascore"
):
    result_players = copy.deepcopy(players_list)

    team_player_rating_dict = {}
    for player_rating in players_ratings_list:
        if player_rating.team not in team_player_rating_dict:
            team_player_rating_dict[player_rating.team] = {}
        team_player_rating_dict[player_rating.team][player_rating.name] = player_rating.sofascore_rating

    # # Find unassigned teams with players
    # assigned_teams_players = set()

    team_rating_names_list = list(team_player_rating_dict.keys())
    for player in result_players:
        closest_player_rating_team = find_similar_string(player.team, team_rating_names_list, similarity_threshold=0)

        player_rating_names_list = list(team_player_rating_dict[closest_player_rating_team].keys())
        closest_player_rating_name = find_similar_string(player.name, player_rating_names_list, similarity_threshold=0.8, verbose=False)
        if closest_player_rating_name:
            player.sofascore_rating = team_player_rating_dict[closest_player_rating_team][closest_player_rating_name]
            # assigned_teams_players.add((closest_player_rating_team, closest_player_rating_name))

    # # Find unassigned teams with players
    # unassigned_dict = {}
    #
    # for team, players in team_player_rating_dict.items():
    #     unassigned_players = {
    #         player_name: rating
    #         for player_name, rating in players.items()
    #         if (team, player_name) not in assigned_teams_players
    #     }
    #     if unassigned_players:  # Only keep teams with unassigned players
    #         unassigned_dict[team] = unassigned_players
    #
    # # Print unassigned teams and players
    # print("Unassigned teams and players:")
    # pprint(unassigned_dict)

    # has_previous_file = False
    # if os.path.isfile('./' + file_name + '.csv'):
    #     biwenger_sofascore_names = read_dict_from_csv(file_name)
    #     has_previous_file = True
    #     write_file = False
    # players_ratings_dict = {listed_rated_player.name: listed_rated_player for listed_rated_player in players_ratings_list}
    #
    # similar_names_dict = {}  # Initialize an empty dictionary
    #
    # # Create a dictionary with teams as keys and lists of players as values
    # team_players_ratings_dict = {}
    # for player in players_ratings_list:
    #     if player.team not in team_players_ratings_dict:
    #         team_players_ratings_dict[player.team] = []
    #     team_players_ratings_dict[player.team].append(player)
    #
    # team_names_list = list(set(player.team for player in result_players))
    #
    # for team_ratings_name, players_with_ratings_list in team_players_ratings_dict.items():
    #     if team_ratings_name == "Atl. Madrid":
    #         closest_team_name = "Atlético"
    #     else:
    #         closest_team_name = find_similar_string(team_ratings_name, team_names_list)
    #     players_ratings_names_list = list(set(player.name for player in players_with_ratings_list))
    #     for player in result_players:
    #         if player.team == closest_team_name:
    #             if has_previous_file:
    #                 closest_player_ratings_name = biwenger_sofascore_names[player.name]
    #             else:
    #                 closest_player_ratings_name = find_similar_string(player.name, players_ratings_names_list, similarity_threshold=-1)
    #             similar_names_dict[player.name] = closest_player_ratings_name  # Add key-value pair to the dictionary
    #             if closest_player_ratings_name == player.name:
    #                 players_ratings_names_list.remove(closest_player_ratings_name)
    #             if closest_player_ratings_name is not None:
    #                 player.sofascore_rating = players_ratings_dict[closest_player_ratings_name].sofascore_rating
    # if write_file:
    #     write_dict_to_csv(similar_names_dict, file_name)


    # for rated_player_name in players_ratings_names_list:
    #     if has_previous_file:
    #         closest_player_name = sofascore_biwenger_names[rated_player_name]
    #     else:
    #         closest_player_name = find_similar_string(rated_player_name, players_names_list)  # , verbose=True)
    #     similar_names_dict[rated_player_name] = closest_player_name  # Add key-value pair to the dictionary
    #     if closest_player_name == rated_player_name:
    #         players_names_list.remove(closest_player_name)
    #     for player in result_players:
    #         if player.name == closest_player_name:
    #             player.sofascore_rating = players_ratings_dict[rated_player_name].sofascore_rating
    # if write_file:
    #     write_dict_to_csv(similar_names_dict, file_name)

    return result_players


def set_players_value(players_list, no_form=False, no_fixtures=False, no_home_boost=False, alt_fixture_method=False, alt_forms=False, ignore_gk_fixture=None, nerf_form=False, skip_arrows=True, arrows_data=None):
    result_players = copy.deepcopy(players_list)
    for player in result_players:
        player.set_player_value(no_form, no_fixtures, no_home_boost, alt_fixture_method, alt_forms, ignore_gk_fixture, nerf_form, skip_arrows, arrows_data)
    return result_players


def set_players_value_to_last_fitness(players_list):
    purged_list = purge_non_starting_players(players_list)
    for player in purged_list:
        if player.fitnesss[0] is None:
            player.value = float(player.fitness[1])
        else:
            player.value = float(player.fitness[0])
    repurged_list = purge_negative_values(purged_list)
    return repurged_list


def set_players_value_to_last_fitness(players_list):
    purged_list = purge_non_starting_players(players_list)
    for player in purged_list:
        if player.fitnesss[0] is None:
            player.value = float(player.fitness[1])
        else:
            player.value = float(player.fitness[0])
    repurged_list = purge_negative_values(purged_list)
    return repurged_list


def get_old_players_data():
    with open(ROOT_DIR + '/csv_files/OLD_players_before_jornada_03.csv', newline='') as f:
        reader = csv.reader(f)
        data = list(reader)
    old_players_data = []
    for d in data:
        new_player = Player(
            d[0],
            d[1],
            int(d[2]),
            float(0),
            d[4],
            d[5],
            float(d[6]),
            float(d[7]),
            ast.literal_eval(d[8]),
            float(0),
            float(0),
            float(0),
            float(d[12])
        )
        old_players_data.append(new_player)
    return old_players_data

