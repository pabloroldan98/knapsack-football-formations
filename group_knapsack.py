import copy
import gc
import itertools
import math

from MCKP import multipleChoiceKnapsack, knapsack_multichoice, \
    knapsack_multichoice_onepick


possible_formations = [
    [3, 4, 3],
    [3, 5, 2],
    [4, 3, 3],
    [4, 4, 2],
    [4, 5, 1],
    [5, 3, 2],
    [5, 4, 1],
]


def best_full_teams(players_list, formations=possible_formations, budget=300, verbose=1):
    super_verbose = bool(verbose-1)
    verbose = bool(verbose)
    # players_by_group = sorted(players_list, key=lambda x: x.get_group())
    if budget <= 0 or budget >= 100000:
        budget = 1
        for player in players_list:
            player.price = 0

    formation_score_players = []

    for formation in formations:
        players_values, players_prices, players_comb_indexes = players_preproc(players_list, formation)

        score, comb_result_indexes = knapsack_multichoice_onepick(players_prices, players_values, budget, verbose=super_verbose)

        result_indexes = []
        for comb_index in comb_result_indexes:
            for winning_i in players_comb_indexes[comb_index[0]][comb_index[1]]:
                result_indexes.append(winning_i)

        result_players = []
        for res_index in result_indexes:
            result_players.append(players_list[res_index])

        formation_score_players.append((formation, score, result_players))

        # print_best_full_teams(formation_score_players)

    formation_score_players_by_score = sorted(formation_score_players, key=lambda tup: tup[1], reverse=True)

    if verbose:
        print_best_full_teams(formation_score_players_by_score)

    return formation_score_players_by_score


def print_best_full_teams(best_results_teams):
    print()
    for best_result in best_results_teams:
        formation, score, result_players = best_result
        total_price = sum(player.price for player in result_players)
        print("With formation " + str(formation) + ": " + str(score) + "  | (price = " + str(total_price) + ")")
        for best_player in result_players:
            print(best_player)
        print()
        print()
    for best_result in best_results_teams:
        print((best_result[0], best_result[1]))


def players_preproc(players_list, formation):
    if len(formation) == 3:
        max_gk = 1
        max_def = formation[0]
        max_mid = formation[1]
        max_att = formation[2]
    elif len(formation) == 4:
        max_gk = formation[0]
        max_def = formation[1]
        max_mid = formation[2]
        max_att = formation[3]
    else:
        max_gk = 1
        max_def = formation[0]
        max_mid = sum(formation[1:-1])
        max_att = formation[-1]

    gk_values, gk_weights, gk_indexes = generate_group(players_list, "GK")
    gk_comb_values, gk_comb_weights, gk_comb_indexes = group_preproc(gk_values, gk_weights, gk_indexes, max_gk)

    def_values, def_weights, def_indexes = generate_group(players_list, "DEF")
    def_comb_values, def_comb_weights, def_comb_indexes = group_preproc(def_values, def_weights, def_indexes, max_def)

    mid_values, mid_weights, mid_indexes = generate_group(players_list, "MID")
    mid_comb_values, mid_comb_weights, mid_comb_indexes = group_preproc(mid_values, mid_weights, mid_indexes, max_mid)

    att_values, att_weights, att_indexes = generate_group(players_list, "ATT")
    att_comb_values, att_comb_weights, att_comb_indexes = group_preproc(att_values, att_weights, att_indexes, max_att)

    result_comb_values = [gk_comb_values, def_comb_values, mid_comb_values, att_comb_values]
    result_comb_weights = [gk_comb_weights, def_comb_weights, mid_comb_weights, att_comb_weights]
    result_comb_indexes = [gk_comb_indexes, def_comb_indexes, mid_comb_indexes, att_comb_indexes]

    result_comb_values, result_comb_weights, result_comb_indexes = remove_zero_combinations(result_comb_values, result_comb_weights, result_comb_indexes)

    return result_comb_values, result_comb_weights, result_comb_indexes


def remove_zero_combinations(values_combinations, weights_combinations, indexes_combinations):
    # Create copies of the lists to avoid modifying the originals
    values_combinations_copy = values_combinations.copy()
    weights_combinations_copy = weights_combinations.copy()
    indexes_combinations_copy = indexes_combinations.copy()

    # Identify indices of sublists in values_combinations that are entirely zeros
    indices_to_delete = [i for i, sublist in enumerate(values_combinations_copy) if sublist and all(x == 0 for x in sublist)]

    # Remove the sublists from the copied lists based on indices
    values_combinations_copy = [sublist for i, sublist in enumerate(values_combinations_copy) if i not in indices_to_delete]
    weights_combinations_copy = [sublist for i, sublist in enumerate(weights_combinations_copy) if i not in indices_to_delete]
    indexes_combinations_copy = [sublist for i, sublist in enumerate(indexes_combinations_copy) if i not in indices_to_delete]

    return values_combinations_copy, weights_combinations_copy, indexes_combinations_copy


def generate_group(full_list, group):
    group_values = []
    group_weights = []
    group_indexes = []
    for i, item in enumerate(full_list):
        if item.position == group:
            group_values.append(item.value)
            group_weights.append(item.price)
            group_indexes.append(i)
    return group_values, group_weights, group_indexes


def group_preproc(group_values, group_weights, initial_indexes, r):
    comb_values = list(itertools.combinations(group_values, r))
    comb_weights = list(itertools.combinations(group_weights, r))
    comb_indexes = list(itertools.combinations(initial_indexes, r))

    group_comb_values = []
    for value_combinations in comb_values:
        values_added = sum(list(value_combinations))
        group_comb_values.append(values_added)

    group_comb_weights = []
    for weight_combinations in comb_weights:
        weights_added = sum(list(weight_combinations))
        group_comb_weights.append(weights_added)

    return group_comb_values, group_comb_weights, comb_indexes


def best_transfers(past_team, players_list, n_transfers, formations=possible_formations, budget=300, n_results=5, verbose=True, by_n_transfers=False):
    players_not_in_list, past_team_indexes = check_team(past_team, players_list)
    if players_not_in_list:
        if verbose:
            print("The following players are NOT in your Database:")
            for missing_player in players_not_in_list:
                print(missing_player)
        return players_not_in_list

    multiple_players_list = players_list_preproc(past_team_indexes, players_list, n_transfers)

    all_possible_transfers = []
    counter = 0
    threshold = 0
    for boosted_players in multiple_players_list:
        players_list_with_boosts = boosted_players[0]
        formation_boostedscore_players_list = best_full_teams(players_list_with_boosts, formations, budget, False)

        best_formation_boostedscore_players = formation_boostedscore_players_list[0]
        best_formation = best_formation_boostedscore_players[0]
        best_score, best_players = get_real_score(best_formation_boostedscore_players, players_list)
        n_non_transferred_players = len(past_team) - boosted_players[1]
        best_formation_score_players = (best_formation, best_score, best_players, n_non_transferred_players)

        all_possible_transfers.append(best_formation_score_players)

        counter = counter + 1
        if verbose:
            percent = counter/len(multiple_players_list)*100
            if percent >= threshold:
                print(str(percent) + " %")
                threshold = threshold + 1

    all_possible_transfers_sorted = sorted(all_possible_transfers, key=lambda tup: (tup[1], tup[3]), reverse=True)

    if by_n_transfers:
        grouped_best_possible_transfers = group_by_n(all_possible_transfers_sorted, n_transfers, len(past_team))
        best_possible_transfers = []
        new_n_results = math.ceil(n_results/n_transfers)
        for group_transfers in grouped_best_possible_transfers:
            best_possible_transfers.append(grouped_best_possible_transfers[0:min(len(group_transfers), new_n_results - 1)])
        if verbose:
            for grouped_results in best_possible_transfers:
                for result in grouped_results:
                    print_transfers(result)
    else:
        best_possible_transfers = all_possible_transfers_sorted[0:n_results - 1]
        if verbose:
            print_transfers(best_possible_transfers)

    return best_possible_transfers


def print_transfers(transfers):
    print()
    for best_result in transfers:
        formation, score, result_players, n_non_changed_players = best_result
        total_price = sum(player.price for player in result_players)
        print("With formation " + str(formation) + ": " + str(score) + "  | (price = " + str(total_price) + ")")
        print("Number of changes = " + str(
            len(result_players) - n_non_changed_players))
        for best_player in result_players:
            print(best_player)
        print()
        print()
    for best_result in transfers:
        print((best_result[0], best_result[1]))


def group_by_n(formation_score_players_stay_list, n, stay):
    results = [[] for _ in range(n + 1)]
    for pos_solution in formation_score_players_stay_list:
        for i in range(stay-n, stay+1):
            staying = pos_solution[3]
            if staying == i:
                results[stay - i].append(pos_solution)
                break
    for grouped_result in results:
        grouped_result.sort(key=lambda tup: (tup[1], tup[3]), reverse=True)
    return results


def check_team(team, players_list):
    missing_players = team.copy()
    team_indexes = []
    for current_player in team:
        for player_index, player in enumerate(players_list):
            if current_player == player:
                missing_players.remove(current_player)
                team_indexes.append(player_index)
                break
    return missing_players, team_indexes


def players_list_preproc(team_indexes, players_list, n_comb):
    multi_players_list = []

    team_indexes_combinations = generate_indexes_combinations(team_indexes, n_comb)

    for boost_comb in team_indexes_combinations:
        new_players_list = copy.deepcopy(players_list)
        n_boosted_players = len(team_indexes) - len(boost_comb)
        for i, player in enumerate(new_players_list):
            if i in boost_comb:
                player.value = 10000
        multi_players_list.append((new_players_list, n_boosted_players))

    return multi_players_list


def generate_indexes_combinations(indexes, max_r):
    full_indexes_combinations = []

    for r in range(len(indexes) - max_r, len(indexes) + 1):
        new_index_comb = list(itertools.combinations(indexes, r))
        full_indexes_combinations = full_indexes_combinations + new_index_comb

    return full_indexes_combinations


def get_real_score(formation_fakescore_players, players_list):
    fakescore_team = formation_fakescore_players[2]
    realscore = 0
    realscore_team = []
    for current_player in fakescore_team:
        for player in players_list:
            if current_player == player:
                realscore = realscore + player.value
                realscore_team.append(player)
                break
    return realscore, realscore_team



