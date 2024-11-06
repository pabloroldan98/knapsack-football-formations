import itertools

from MCKP import knapsack_multichoice


def best_squads(players_list, formations, budget):
    n = len(players_list)
    player_values = []
    player_prices = []
    player_positions = []
    for player in players_list:
        player_values.append(player.value)
        player_prices.append(player.price)
        player_positions.append(player.get_group())

    for formation in formations:
        max_gk = 1
        max_def = formation[0]
        max_mid = formation[1]
        max_att = formation[2]

        score, result_indexes = group_knapsack(n, budget, player_values, player_prices, max_gk, max_def, max_mid, max_att, player_positions)

        result = []
        for res_index in result_indexes:
            result.append(players_list[res_index])

        print("With formation " + str(formation) + ": " + str(score))
        for best_player in result:
            print(best_player)
        print()
        print()


# Works fine but doesn't have to use 11 players

def group_knapsack(n, weight, values, weights, count_group_a, count_group_b, count_group_c, count_group_d, groups):
    K = [[[[[[0
        for _ in range(count_group_d + 1)]
        for _ in range(count_group_c + 1)]
        for _ in range(count_group_b + 1)]
        for _ in range(count_group_a + 1)]
        for _ in range(weight + 1)]
        for _ in range(n + 1)]
    for d in range(1, count_group_d + 1):
        for c in range(1, count_group_c + 1):
            for b in range(1, count_group_b + 1):
                for a in range(1, count_group_a + 1):
                    for i in range(1, n + 1):
                        for w in range(weight + 1):
                            if groups[i - 1] == 0:
                                added_weight_group = K[i - 1][w - weights[i - 1]][a - 1][b][c][d]
                                count_check = a - 1
                            elif groups[i - 1] == 1:
                                added_weight_group = K[i - 1][w - weights[i - 1]][a][b - 1][c][d]
                                count_check = b - 1
                            elif groups[i - 1] == 2:
                                added_weight_group = K[i - 1][w - weights[i - 1]][a][b][c - 1][d]
                                count_check = c - 1
                            else:
                                added_weight_group = K[i - 1][w - weights[i - 1]][a][b][c][d - 1]
                                count_check = d - 1

                            if i == 0 or w == 0 or (a == 0 and b == 0 and c == 0 and d == 0):
                                K[i][w][a][b][c][d] = 0
                            elif weights[i - 1] <= w and count_check >= 0:
                                K[i][w][a][b][c][d] = max(K[i - 1][w][a][b][c][d],
                                                  added_weight_group + values[i - 1])
                            else:
                                K[i][w][a][b][c][d] = K[i - 1][w][a][b][c][d]

    # stores the result of Knapsack
    res = K[-1][-1][-1][-1][-1][-1]
    # print(res)
    sol=[]

    w = weight
    a = count_group_a
    b = count_group_b
    c = count_group_c
    d = count_group_d
    for i in range(n, 0, -1):
        if res <= 0:
            break
        # either the result comes from the
        # top (K[i-1][w]) or from (val[i-1]
        # + K[i-1] [w-wt[i-1]]) as in Knapsack
        # table. If it comes from the latter
        # one/ it means the item is included.
        if res == K[i - 1][w][a][b][c][d]:
            continue
        else:

            # This item is included.
            sol.append(i - 1)
            # print("Item in pos: " + str(i - 1))

            # Since this weight is included
            # its value is deducted
            res = res - values[i - 1]
            w = w - weights[i - 1]
            if groups[i - 1] == 0:
                a = a - 1
            elif groups[i - 1] == 1:
                b = b - 1
            elif groups[i - 1] == 2:
                c = c - 1
            else:
                d = d - 1

    return K[-1][-1][-1][-1][-1][-1], sol


def best_teams(players_list, formations, budget):
    # players_by_group = sorted(players_list, key=lambda x: x.get_group())

    for formation in formations:
        player_values, player_prices, player_positions, player_comb_indexes = players_preproc(players_list, formation)

        # score, comb_result_indexes = multipleChoiceKnapsack(budget, player_prices, player_values, player_positions)
        score, comb_result_indexes = knapsack_multichoice(budget, player_values, player_prices, player_positions)

        print(comb_result_indexes)

        result_indexes = []
        for comb_index in comb_result_indexes:
            for win_i in player_comb_indexes[comb_index]:
                result_indexes.append(win_i)

        result = []
        for res_index in result_indexes:
            result.append(players_list[res_index])

        print("With formation " + str(formation) + ": " + str(score))
        for best_player in result:
            print(best_player)
        print()
        print()


def players_preproc(players_list, formation):
    max_gk = 1
    max_def = formation[0]
    max_mid = formation[1]
    max_att = formation[2]

    gk_values, gk_weights, gk_indexes = generate_group(players_list, "GK")
    gk_comb_values, gk_comb_weights, gk_comb_groups, gk_comb_indexes = group_preproc(gk_values, gk_weights, 0, gk_indexes, max_gk)

    def_values, def_weights, def_indexes = generate_group(players_list, "DEF")
    def_comb_values, def_comb_weights, def_comb_groups, def_comb_indexes = group_preproc(def_values, def_weights, 1, def_indexes, max_def)

    mid_values, mid_weights, mid_indexes = generate_group(players_list, "MID")
    mid_comb_values, mid_comb_weights, mid_comb_groups, mid_comb_indexes = group_preproc(mid_values, mid_weights, 2, mid_indexes, max_mid)

    att_values, att_weights, att_indexes = generate_group(players_list, "ATT")
    att_comb_values, att_comb_weights, att_comb_groups, att_comb_indexes = group_preproc(att_values, att_weights, 3, att_indexes, max_att)

    result_comb_values = gk_comb_values + def_comb_values + mid_comb_values + att_comb_values
    result_comb_weights = gk_comb_weights + def_comb_weights + mid_comb_weights + att_comb_weights
    result_comb_groups = gk_comb_groups + def_comb_groups + mid_comb_groups + att_comb_groups
    result_comb_indexes = gk_comb_indexes + def_comb_indexes + mid_comb_indexes + att_comb_indexes

    return result_comb_values, result_comb_weights, result_comb_groups, result_comb_indexes


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


def group_preproc(group_values, group_weights, group, initial_indexes, r):
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

    group_array = [group for _ in range(len(group_comb_values))]

    return group_comb_values, group_comb_weights, group_array, comb_indexes
