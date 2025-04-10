import ast
import copy
import csv
import math
import difflib

import numpy as np
from unidecode import unidecode
import os
from pprint import pprint

from useful_functions import find_similar_string, find_string_positions, write_dict_data, read_dict_data

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
            start_probability:  float = 0
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
        self.start_probability = start_probability

    def __str__(self):
        return f"({self.name}, {self.position}, {self.team}, {self.price}, {self.value:.3f}, {self.status}) - (form: {self.form:.4f}, fixture: {self.fixture:.4f}) --> {self.start_probability*100:.0f} %"
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

    def calc_value(self, no_form=False, no_fixtures=False, no_home_boost=False, alt_fixture_method=False, alt_forms=False):
        if alt_forms:
            # form_coef = (np.log1p(np.abs(self.price_trend * (self.standard_price - self.price_trend) / 1000000000)) * np.sign(self.price_trend)) / 235 + 1
            # form_coef = (np.log1p(np.log1p(np.abs(self.price_trend * (self.standard_price / (self.standard_price - self.price_trend)) / 100000))) * np.sign(self.price_trend)) * 3.5 / 100 + 1
            price_trend_percent = 100 * self.price_trend / (self.standard_price - self.price_trend) if self.standard_price != self.price_trend else 0
            prod_percent_trend = price_trend_percent * self.price_trend
            form_coef = (np.log1p(np.log1p(np.abs(prod_percent_trend / 100000))) * np.sign(self.price_trend)) * 3 / 100 + 1
        else:
            form_coef = ((self.price_trend / np.log1p(self.standard_price)) / 300000) * 1.75 * 0.9 + 1

        if no_form:
            form_coef = 1

        if alt_fixture_method:
            capped_elo_dif = math.log(abs(self.next_match_elo_dif), 10) if self.next_match_elo_dif != 0 else 0
            # if self.position == "GK":
            #     capped_elo_dif = capped_elo_dif * 0.2
            base_coef = capped_elo_dif * 0.0075 + 1 if self.next_match_elo_dif >= 0 else 1 - capped_elo_dif * 0.015
        else:
            # capped_elo_dif = min(250.0, max(-250.0, self.next_match_elo_dif))
            capped_elo_dif = min(400.0, max(-400.0, self.next_match_elo_dif))
            # if self.position == "GK":
            #     capped_elo_dif = capped_elo_dif * 0.2
            # base_coef = capped_elo_dif * 1.5 / 10000 + 1
            # base_coef = capped_elo_dif * 1.15 / 10000 + 1
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

        predicted_value = ((float(self.sofascore_rating) * float(self.form)) + float(self.penalty_boost) + float(self.strategy_boost)) * float(self.fixture)
        return predicted_value

    def set_value(self, no_form=False, no_fixtures=False, no_home_boost=False, alt_fixture_method=False, alt_forms=False):
        predicted_value = self.calc_value(no_form, no_fixtures, no_home_boost, alt_fixture_method=alt_fixture_method, alt_forms=alt_forms)
        self.value = predicted_value


def get_position(group):
    if group == 1:
        position = "GK"
    elif group == 2:
        position = "DEF"
    elif group == 3:
        position = "MID"
    else:
        position = "ATT"
    return position


def purge_everything(players_list, teams_to_purge=[], mega_purge=False, probability_threshold=0.5, fixture_filter=False):
    purged_players = purge_no_team_players(players_list)
    purged_players = purge_negative_values(purged_players)
    if not probability_threshold or mega_purge:
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
    if not all(player.start_probability == 0 for player in players_list):
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
    result_players = [player for player in result_players if not ((player.position == "GK") and (player.fixture < 0.965))]
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


def set_manual_boosts(players_list, manual_boosts):
    result_players = copy.deepcopy(players_list)
    for boosted_player in manual_boosts:
        for player in result_players:
            if boosted_player == player:
                player.penalty_boost = boosted_player.penalty_boost
                player.strategy_boost = boosted_player.strategy_boost
                break
    return result_players


def set_positions(players_list, players_positions_dict, verbose=False):
    result_players = copy.deepcopy(players_list)
    team_position_names_list = list(players_positions_dict.keys())

    for player in result_players:
        closest_player_position_team = find_similar_string(player.team, team_position_names_list, similarity_threshold=0)
        player_position_names_list = list(players_positions_dict[closest_player_position_team].keys())
        closest_player_position_name = find_similar_string(player.name, player_position_names_list)
        if closest_player_position_name:
            new_position = players_positions_dict[closest_player_position_team][closest_player_position_name]
            if verbose:
                if player.position != new_position:
                    print(f"{player.name}: {player.position} --> {new_position}")
            player.position = new_position
        # else:
        #     print(f"{player.name}")

    return result_players


def set_prices(players_list, players_prices_dict, verbose=False):
    result_players = copy.deepcopy(players_list)
    team_price_names_list = list(players_prices_dict.keys())

    for player in result_players:
        closest_player_price_team = find_similar_string(player.team, team_price_names_list, similarity_threshold=0)
        player_price_names_list = list(players_prices_dict[closest_player_price_team].keys())
        closest_player_price_name = find_similar_string(player.name, player_price_names_list)
        if closest_player_price_name:
            new_price = players_prices_dict[closest_player_price_team][closest_player_price_name]
            new_price = round(float(new_price))
        else:
            # print(player.name)
            new_price = round(float(player.standard_price) * 5)
        new_price = round(float(new_price) / 1000000)
        if verbose:
            if player.price != new_price:
                print(f"{player.name}: {player.price} --> {new_price}")
        player.price = new_price

    return result_players


def set_price_trends(players_list, players_price_trends_dict, players_standard_prices_dict=None, verbose=False):
    result_players = copy.deepcopy(players_list)
    team_price_trend_names_list = list(players_price_trends_dict.keys())

    for player in result_players:
        closest_player_price_trend_team = find_similar_string(player.team, team_price_trend_names_list, similarity_threshold=0)
        player_price_trend_names_list = list(players_price_trends_dict[closest_player_price_trend_team].keys())
        closest_player_price_trend_name = find_similar_string(player.name, player_price_trend_names_list)
        if closest_player_price_trend_name:
            new_price_trend = players_price_trends_dict[closest_player_price_trend_team][closest_player_price_trend_name]
            new_price_trend = float(new_price_trend)
            if verbose:
                if player.price_trend != new_price_trend:
                    print(f"{player.name}: {player.price_trend} --> {new_price_trend}")
            player.price_trend = new_price_trend


    if players_standard_prices_dict:
        result_players = copy.deepcopy(result_players)
        team_standard_price_names_list = list(players_standard_prices_dict.keys())

        for player in result_players:
            closest_player_standard_price_team = find_similar_string(player.team, team_standard_price_names_list, similarity_threshold=0)
            player_standard_price_names_list = list(players_standard_prices_dict[closest_player_standard_price_team].keys())
            closest_player_standard_price_name = find_similar_string(player.name, player_standard_price_names_list)
            if closest_player_standard_price_name:
                new_standard_price = players_standard_prices_dict[closest_player_standard_price_team][closest_player_standard_price_name]
                new_standard_price = float(new_standard_price)
                if verbose:
                    if player.standard_price != new_standard_price:
                        print(f"{player.name}: {player.standard_price} --> {new_standard_price}")
                player.standard_price = new_standard_price

    return result_players


def set_start_probabilities(players_list, players_start_probabilities_dict, players_start_probabilities_dict_extra=None, verbose=False):
    result_players = copy.deepcopy(players_list)
    team_start_probability_names_list = list(players_start_probabilities_dict.keys())

    # team_names_list = list(set(player.team for player in result_players))
    # for team_name, start_probability_names_list in players_start_probabilities_dict.items():
    #     closest_team_name = find_similar_string(team_name, team_names_list)
    #     players_names_list = list(set(player.name for player in players_list if player.team == closest_team_name))
    #     for start_probability_name in start_probability_names_list:
    #         closest_player_name = find_similar_string(start_probability_name, players_names_list, verbose=False)
    #         if closest_player_name:
    #             for player in result_players:
    #                 if player.name == closest_player_name:
    #                     new_start_probability = players_start_probabilities_dict[team_name][start_probability_name]
    #                     if verbose:
    #                         if player.start_probability != new_start_probability:
    #                             print(
    #                                 f"{player.name}: {player.start_probability} --> {new_start_probability} ({closest_player_start_probability_name})")
    #                     player.start_probability = new_start_probability
    #         else:
    #             print(f"{start_probability_name}")

    for player in result_players:
        closest_player_start_probability_team = find_similar_string(player.team, team_start_probability_names_list, similarity_threshold=0)
        player_start_probability_names_list = list(players_start_probabilities_dict[closest_player_start_probability_team].keys())
        closest_player_start_probability_name = find_similar_string(player.name, player_start_probability_names_list, verbose=False)
        if closest_player_start_probability_name:
            new_start_probability = players_start_probabilities_dict[closest_player_start_probability_team][closest_player_start_probability_name]
            if verbose:
                if player.start_probability != new_start_probability:
                    print(f"{player.name}: {player.start_probability} --> {new_start_probability} ({closest_player_start_probability_name})")
            player.start_probability = new_start_probability
        # else:
        #     print(f"{player.name} ({player.team})")

    if players_start_probabilities_dict_extra:
        if verbose:
            print()
            print("-----> EXTRA <-----")

        team_start_probability_names_list = list(players_start_probabilities_dict_extra.keys())

        for player in result_players:
            closest_player_start_probability_team = find_similar_string(player.team, team_start_probability_names_list, similarity_threshold=0)
            player_start_probability_names_list = list(players_start_probabilities_dict_extra[closest_player_start_probability_team].keys())
            closest_player_start_probability_name = find_similar_string(player.name, player_start_probability_names_list, verbose=False)
            if closest_player_start_probability_name:
                new_start_probability = round((player.start_probability + players_start_probabilities_dict_extra[closest_player_start_probability_team][closest_player_start_probability_name]) / 2, 4)
                if verbose:
                    if player.start_probability != new_start_probability:
                        print(f"{player.name}: {player.start_probability} --> {new_start_probability} ({closest_player_start_probability_name})")
                player.start_probability = new_start_probability
            # else:
            #     print("#######################")
            #     print(f"{player.name} ({player.team})")

    return result_players


def set_forms(players_list, players_forms_dict, verbose=False):
    result_players = copy.deepcopy(players_list)
    team_form_names_list = list(players_forms_dict.keys())

    for player in result_players:
        closest_player_form_team = find_similar_string(player.team, team_form_names_list, similarity_threshold=0)
        player_form_names_list = list(players_forms_dict[closest_player_form_team].keys())
        closest_player_form_name = find_similar_string(player.name, player_form_names_list)
        if closest_player_form_name:
            new_form = players_forms_dict[closest_player_form_team][closest_player_form_name]
            new_form = 1 + float(new_form)/100
            if verbose:
                if player.form != new_form:
                    print(f"{player.name}: {player.form} --> {new_form}")
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


def get_biwinger_transfermarket_teams_dict(biwenger_team_names_list, transfermarket_team_names_list, file_name="biwinger_transfermarket_teams"):
    if os.path.isfile('./' + file_name + '.csv'):
        return read_dict_data(file_name)
    result_biwinger_transfermarket_teams_dict = dict()

    for biwenger_team_name in biwenger_team_names_list:
        closest_transfermarket_team_name = find_similar_string(biwenger_team_name, transfermarket_team_names_list)
        result_biwinger_transfermarket_teams_dict[biwenger_team_name] = closest_transfermarket_team_name

    return result_biwinger_transfermarket_teams_dict


def set_team_history_boosts(players_list, players_team_history_dict, verbose=False):
    result_players = copy.deepcopy(players_list)

    team_names_list = list(set(player.team for player in result_players))
    penalty_team_names_list = list(players_team_history_dict.keys())
    biwinger_transfermarket_teams_dict = get_biwinger_transfermarket_teams_dict(team_names_list, penalty_team_names_list) #, file_name="biwinger_transfermarket_laliga_teams")

    for team_name, team_players_history in players_team_history_dict.items():
        closest_team_name = find_similar_string(team_name, team_names_list)
        players_names_list = list(set(player.name for player in players_list if player.team == closest_team_name))
        for player_name, player_team_history in team_players_history.items():
            closest_player_name = find_similar_string(player_name, players_names_list, verbose=False)
            for player in result_players:
                if player.name == closest_player_name:
                    player.team_history = player_team_history
                    transfermarket_opponent_name = biwinger_transfermarket_teams_dict[player.opponent]
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
    clean_players = purge_no_opponent_players(clean_players, teams_dict)
    # clean_players = purge_eliminated_players(clean_players, teams_list)

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
        if player.team == "Atlético":
            closest_player_rating_team = "Atl. Madrid"
        else:
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


def set_players_value(players_list, no_form=False, no_fixtures=False, no_home_boost=False, alt_fixture_method=False, alt_forms=False):
    result_players = copy.deepcopy(players_list)
    for player in result_players:
        player.set_value(no_form, no_fixtures, no_home_boost, alt_fixture_method, alt_forms)
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

