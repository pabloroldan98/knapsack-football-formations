import copy
import heapq
import itertools
import math
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Tuple

import streamlit as st
from tqdm import tqdm

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

try:
    STREAMLIT_ACTIVE = st.runtime.exists()
except Exception:
    STREAMLIT_ACTIVE = False


def _parse_formation(formation):
    """Extract GK/DEF/MID/ATT counts from a formation list."""
    if len(formation) == 3:
        return 1, formation[0], formation[1], formation[2]
    elif len(formation) == 4:
        return formation[0], formation[1], formation[2], formation[3]
    else:
        return 1, formation[0], sum(formation[1:-1]), formation[-1]


def _formation_coarse_weights(formation) -> Tuple[List[str], List[int]]:
    """Map a tactical formation to (GK, DEF, MID, ATT) labels and slot weights."""
    max_gk, max_def, max_mid, max_att = _parse_formation(formation)
    return ["GK", "DEF", "MID", "ATT"], [max_gk, max_def, max_mid, max_att]


# Max total candidates after formation filter; split inversely to slot count
# (lines with large C(n,r) get fewer extras). Default tier is always "standard".
_SPEED_TOTAL_PLAYER_CAP: Dict[str, int] = {
    "local": 150,
    "fast": 200,
    "standard": 250,
}
_DEFAULT_SPEED_TIER = "standard"


def _resolve_speed_tier(speed_up: bool, speed: Optional[str] = None) -> Optional[str]:
    """Resolve speed tier for the global candidate cap.

    When ``speed`` is omitted (default ``None``), uses ``speed_up``:
    - ``speed_up=False`` → ``standard`` (250)
    - ``speed_up=True`` → ``fast`` (200)

    Explicit ``speed`` overrides ``speed_up``:
    - ``"uncapped"`` / ``"none"`` / ``"off"`` → no global cap
    - ``"local"`` / ``"fast"`` / ``"standard"`` → that tier
    """
    if isinstance(speed, str):
        low = speed.lower()
        if low in ("none", "off", "uncapped"):
            return None
        if speed in _SPEED_TOTAL_PLAYER_CAP:
            return speed
    return "fast" if speed_up else _DEFAULT_SPEED_TIER


def _allocate_integer_shares_from_proportions(total: int, proportions: List[float]) -> List[int]:
    """Largest-remainder split of *total* across non-negative *proportions*."""
    if total <= 0 or not proportions:
        return [0] * len(proportions)
    s = sum(proportions)
    if s <= 0:
        return [0] * len(proportions)
    raw = [total * p / s for p in proportions]
    floors = [int(math.floor(r)) for r in raw]
    rem = total - sum(floors)
    order = sorted(
        range(len(proportions)), key=lambda i: (raw[i] - floors[i]), reverse=True
    )
    for k in range(max(0, rem)):
        floors[order[k % len(order)]] += 1
    return floors


def _speed_cap_proportions_inverse(slot_weights: List[int]) -> List[float]:
    """Speed-cap shares: 0 slots → 0; w>0 → ∝ 1/w (heavy lines get a thinner pool)."""
    return [0.0 if w <= 0 else 1.0 / float(w) for w in slot_weights]


def _ensure_caps_at_least_formation(caps: List[int], weights: List[int]) -> None:
    """Each position keeps at least as many candidates as formation slots (in-place)."""
    for i, w in enumerate(weights):
        if w > 0:
            caps[i] = max(caps[i], w)


def _apply_weighted_player_cap(
    players_list,
    position_caps: Dict[str, int],
) -> list:
    """Keep up to *position_caps[pos]* highest-value players per position."""
    by_pos = defaultdict(list)
    for pl in players_list:
        pos = pl.position
        cap = position_caps.get(pos, 0)
        if cap <= 0:
            continue
        by_pos[pos].append(pl)

    out = []
    for pos, cap in position_caps.items():
        if cap <= 0:
            continue
        lst = sorted(by_pos.get(pos, []), key=lambda pl: pl.value, reverse=True)
        out.extend(lst[:cap])
    out.sort(key=lambda pl: pl.value, reverse=True)
    return out


def _apply_speed_cap(players_list, formation, speed_tier: Optional[str]) -> list:
    """Apply proportional per-position candidate cap for the given speed tier."""
    if not speed_tier:
        return players_list
    total_cap = _SPEED_TOTAL_PLAYER_CAP.get(speed_tier)
    if not total_cap or total_cap <= 0:
        return players_list

    pos_labels, weights = _formation_coarse_weights(formation)
    props = _speed_cap_proportions_inverse(weights)
    caps = _allocate_integer_shares_from_proportions(total_cap, props)
    _ensure_caps_at_least_formation(caps, weights)
    position_caps = dict(zip(pos_labels, caps))
    return _apply_weighted_player_cap(players_list, position_caps)


def filter_players_knapsack(players_list, formation):
    """
    Filters players based on a formation and per-position max counts, keeping highest-value players per price bucket.

    Args:
        players_list: list of player objects with attributes .position, .price, .value
        formation: sequence indicating formation counts
            - If len==3: [DEF, MID, ATT] with GK fixed at 1
            - If len==4: [GK, DEF, MID, ATT]
            - Else: assume [DEF, MID1, ..., MIDk, ATT], GK=1, MID is sum of middle entries

    Returns:
        List of filtered players sorted by descending .value
    """
    max_limits = dict(zip(*_formation_coarse_weights(formation)))
    excluded_positions = {pos for pos, limit in max_limits.items() if limit == 0}

    buckets = defaultdict(lambda: defaultdict(list))
    for p in players_list:
        if p.position in excluded_positions:
            continue
        buckets[p.position][p.price].append(p)

    filtered_players = []
    for position, price_dict in buckets.items():
        limit = max_limits.get(position)
        if limit is None or limit == 0:
            continue
        for group in price_dict.values():
            top_n = heapq.nlargest(limit, group, key=lambda pl: pl.value)
            filtered_players.extend(top_n)

    # Sort all by descending value
    filtered_players.sort(key=lambda pl: pl.value, reverse=True)

    # print(len(players_list))
    # print(len(filtered_players))

    return filtered_players


def best_full_teams(
    players_list,
    formations=possible_formations,
    budget=300,
    speed_up=False,
    speed: Optional[str] = None,
    translator=None,
    verbose=1,
    progress_callback: Optional[Callable[[float], None]] = None,
):
    super_verbose = bool(verbose - 1)
    verbose = bool(verbose)
    speed_tier = _resolve_speed_tier(speed_up, speed)

    unlimited_budget = budget <= 0 or budget >= 100000
    if unlimited_budget:
        budget = 1
        for player in players_list:
            player.price = 0
    else:
        # Players more expensive than the budget can never fit the knapsack
        players_list = [p for p in players_list if (p.price or 0) <= budget]

    # Precompute everything in a single pass (avoid filtering twice per formation)
    total_global_operations = 0
    precomputed = []
    for formation in formations:
        filtered_players_list = filter_players_knapsack(players_list, formation)
        filtered_players_list = _apply_speed_cap(filtered_players_list, formation, speed_tier)
        players_values, players_prices, players_comb_indexes = players_preproc(
            filtered_players_list, formation
        )
        ops = sum(len(group) for group in players_comb_indexes[1:]) if len(players_comb_indexes) > 1 else 0
        total_global_operations += ops
        precomputed.append(
            (formation, filtered_players_list, players_values, players_prices, players_comb_indexes)
        )

    update_master = None
    if total_global_operations:
        progress_text = None
        progress_bar = None
        _label = (
            translator("loader.knapsack_progress")
            if callable(translator)
            else "Calculando mejores combinaciones"
        )
        if STREAMLIT_ACTIVE:
            progress_text = st.empty()
            progress_bar = st.progress(0.0)

        completed_ops = 0
        last_percent = -1

        def update_master(n):
            nonlocal completed_ops, last_percent
            completed_ops += n
            percent = (completed_ops / total_global_operations) * 100
            pct_int = int(percent)
            if pct_int <= last_percent:
                return
            last_percent = pct_int
            if progress_callback:
                progress_callback(percent)
            if STREAMLIT_ACTIVE and progress_bar is not None and progress_text is not None:
                progress_bar.progress(completed_ops / total_global_operations)
                progress_text.text(f"{_label}: {pct_int} %")

    formation_score_players = []
    for formation, filtered_players_list, players_values, players_prices, players_comb_indexes in precomputed:
        if not players_values or not players_prices or not players_comb_indexes:
            continue

        score, comb_result_indexes = knapsack_multichoice_onepick(
            players_prices,
            players_values,
            budget,
            verbose=super_verbose,
            update_master=update_master,
        )

        result_indexes = []
        for comb_index in comb_result_indexes:
            for winning_i in players_comb_indexes[comb_index[0]][comb_index[1]]:
                result_indexes.append(winning_i)

        result_players = [filtered_players_list[i] for i in result_indexes]
        formation_score_players.append((formation, score, result_players))

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
    max_gk, max_def, max_mid, max_att = _parse_formation(formation)
    positions = ["GK", "DEF", "MID", "ATT"]
    requirements = [max_gk, max_def, max_mid, max_att]

    all_values = []
    all_weights = []
    all_indexes = []

    for pos, req in zip(positions, requirements):
        if req <= 0:
            continue
        g_v, g_w, g_i = generate_group(players_list, pos)
        cv, cw, ci = group_preproc(g_v, g_w, g_i, req)
        if not cv or not cw or not ci:
            return [], [], []
        all_values.append(cv)
        all_weights.append(cw)
        all_indexes.append(ci)

    if not all_values:
        return [], [], []

    return all_values, all_weights, all_indexes


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
    if r <= 0 or not initial_indexes:
        return [], [], []
    comb_values = list(itertools.combinations(group_values, r))
    comb_weights = list(itertools.combinations(group_weights, r))
    comb_indexes = list(itertools.combinations(initial_indexes, r))

    return (
        [sum(c) for c in comb_values],
        [sum(c) for c in comb_weights],
        comb_indexes,
    )


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
