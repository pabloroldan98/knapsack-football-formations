import copy
import heapq
import itertools
import math
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Tuple

import streamlit as st
from tqdm import tqdm

# One DP candidate: (weight, value, index into the candidate pool).
_Item = Tuple[int, float, int]


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


def _formation_requirements(formation) -> Dict[str, int]:
    """Per-position exact counts, omitting lines with 0 slots."""
    labels, weights = _formation_coarse_weights(formation)
    return {pos: w for pos, w in zip(labels, weights) if w > 0}


# Finest price step this product actually uses (Biwenger UI is 0.1M). Integer
# prices stay on quantum 1 so a typical budget of 300 keeps W=300. Decimals
# bump to 0.1 so ``price == budget == 10.2`` is feasible (plain ceil/int is not).
_INTEGER_PRICE_QUANTUM = 1.0
_DECIMAL_PRICE_QUANTUM = 0.1
# IEEE-754 only: ``10.2 / 0.1`` is ``101.999...``, not 102. Nudge on-grid
# values onto the integer lattice. Off-grid amounts (e.g. 10.25 at q=0.1)
# stay off-grid; feasibility rescue covers those, not this epsilon.
_IEEE_QUANTUM_EPS = 1e-9


def _is_integral(amount: float) -> bool:
    return abs(float(amount) - round(float(amount))) <= _IEEE_QUANTUM_EPS


def _price_quantum(budget: float, players) -> float:
    """1.0 when every price and the budget are whole numbers, else 0.1."""
    if not _is_integral(budget):
        return _DECIMAL_PRICE_QUANTUM
    for p in players:
        if not _is_integral(p.price or 0):
            return _DECIMAL_PRICE_QUANTUM
    return _INTEGER_PRICE_QUANTUM


def _to_weight(amount: float, quantum: float) -> int:
    """Real price → DP units. Ceil so a selection cannot under-count cost."""
    return max(0, int(math.ceil((float(amount or 0) / quantum) - _IEEE_QUANTUM_EPS)))


def _to_budget_int(budget: float, quantum: float) -> int:
    """Real budget → DP capacity. Floor so a selection cannot overspend."""
    return max(0, int(math.floor((float(budget) / quantum) + _IEEE_QUANTUM_EPS)))


def _player_weight(player, unlimited_budget: bool, quantum: float = _INTEGER_PRICE_QUANTUM) -> int:
    if unlimited_budget:
        return 0
    return _to_weight(player.price or 0, quantum)


def _player_value(player) -> float:
    return float(player.value or 0)


def _real_price(player) -> float:
    return float(player.price or 0)


def _tqdm_disabled(verbose, streamlit_active: Optional[bool] = None) -> bool:
    """CLI progress bar: on for verbose>=1, off when silent or inside Streamlit."""
    if streamlit_active is None:
        streamlit_active = STREAMLIT_ACTIVE
    return (not verbose) or bool(streamlit_active)


def filter_players_knapsack(players_list, formation):
    """
    Filters players based on a formation and per-position max counts, keeping highest-value players per price bucket.

    This reduction is exact: at a given price, a cheaper-or-equal slot can always
    replace a lower-valued player, so only the top ``r`` by value can appear in an
    optimum. The count-DP solver also applies this (plus dominance reduction) per
    ``(position, r)``; the helper remains for callers that want the filtered pool.

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

    filtered_players.sort(key=lambda pl: pl.value, reverse=True)
    return filtered_players


def _r_dominance_reduce(items: List[_Item], r: int) -> List[_Item]:
    """Drop every item that at least ``r`` other items dominate — i.e. cost no
    more AND score at least as much. Exact: never changes the optimum.

    Why ``r`` and not one dominator: with ``r`` slots to fill, a single better
    candidate isn't enough (it may already be in the solution and can't be picked
    twice). With ``r`` dominators, at most ``r - 1`` of them can be in a solution
    that also contains the dominated item, so one is always free to swap in —
    same count, no more weight, no less value.

    Exact for the *discretized* problem (same knapsack weight). Two real prices
    that collapse to one bucket (e.g. 10.1 and 10.9 at quantum 1) are treated as
    equal cost; the ``r`` cheapest *real* prices of that bucket still survive
    because they share the bucket's weight.

    The ``r`` cheapest discretized items always survive, so a request that is
    feasible after quantization cannot become infeasible through this reduction.
    """
    if r <= 0 or len(items) <= r:
        return list(items)
    ordered = sorted(items, key=lambda it: (it[0], -it[1]))
    kept: List[_Item] = []
    top: List[float] = []  # min-heap of the r best values seen so far
    for item in ordered:
        value = item[1]
        if len(top) >= r and top[0] >= value:
            continue
        kept.append(item)
        heapq.heappush(top, value)
        if len(top) > r:
            heapq.heappop(top)
    return kept


class _CandidatePool:
    """Position/price buckets built once per solver call, plus a memo of the
    per-``(position, count)`` DP groups.

    What a position contributes depends only on that position's own requirement:
    the top ``r`` candidates of each distinct *discretized* price, then
    ``_r_dominance_reduce``. Exact for the quantized knapsack, not automatically
    for raw floats that share a bucket. Memoising on ``(position, count)``
    avoids rebuilding the same group for every formation that shares a line count.
    """

    def __init__(
        self,
        players,
        unlimited_budget: bool = False,
        quantum: float = _INTEGER_PRICE_QUANTUM,
    ) -> None:
        self.players = players
        self._by_price: Dict[str, Dict[int, List[int]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._memo: Dict[Tuple[str, int], List[_Item]] = {}
        for idx, pl in enumerate(players):
            pos = pl.position
            if not pos:
                continue
            self._by_price[pos][_player_weight(pl, unlimited_budget, quantum)].append(idx)

    def group(self, pos: str, r: int) -> List[_Item]:
        if r <= 0:
            return []
        cached = self._memo.get((pos, r))
        if cached is not None:
            return cached
        players = self.players
        items: List[_Item] = []
        for price, idxs in self._by_price.get(pos, {}).items():
            if len(idxs) > r:
                idxs = sorted(idxs, key=lambda i: _player_value(players[i]), reverse=True)[:r]
            items.extend((price, _player_value(players[i]), i) for i in idxs)
        items = _r_dominance_reduce(items, r)
        self._memo[(pos, r)] = items
        return items

    def build_groups(self, req_by_pos: Dict[str, int]) -> List[Tuple[List[_Item], int]]:
        groups = []
        for pos, r in req_by_pos.items():
            if r > 0:
                groups.append((self.group(pos, r), r))
        return groups

    def cheapest_real_selection(
        self,
        req_by_pos: Dict[str, int],
        budget: float,
    ) -> Optional[List[int]]:
        """Cheapest XI in *real* prices meeting the exact counts. ``None`` if
        even that exceeds ``budget``. Bypasses top-r / dominance: this is the
        feasibility guarantee, so it must see every candidate the budget filter
        allowed.
        """
        chosen: List[int] = []
        total = 0.0
        for pos, r in req_by_pos.items():
            if r <= 0:
                continue
            idxs = [
                i
                for bucket in self._by_price.get(pos, {}).values()
                for i in bucket
            ]
            if len(idxs) < r:
                return None
            idxs.sort(
                key=lambda i: (
                    _real_price(self.players[i]),
                    -_player_value(self.players[i]),
                )
            )
            for i in idxs[:r]:
                total += _real_price(self.players[i])
                chosen.append(i)
        if total > budget + _IEEE_QUANTUM_EPS:
            return None
        return chosen


def _group_count_profile(
    items: List[Tuple[int, float, object]],
    r: int,
    max_weight: int,
) -> Tuple[List[float], List]:
    """Best value (and chosen refs) picking exactly ``r`` of ``items`` for every
    total weight ``w`` in ``0..max_weight``.

    A ``(count, weight)`` 0/1 knapsack: iterate items outer, count and weight
    descending, so each item is used at most once. ``O(len(items) · r · W)``.
    """
    neg = float("-inf")
    values = [[neg] * (max_weight + 1) for _ in range(r + 1)]
    picks: List[List] = [[None] * (max_weight + 1) for _ in range(r + 1)]
    values[0][0] = 0.0
    picks[0][0] = ()
    for w_j, v_j, ref in items:
        if w_j > max_weight:
            continue
        for k in range(r, 0, -1):
            prev_vals = values[k - 1]
            prev_picks = picks[k - 1]
            cur_vals = values[k]
            cur_picks = picks[k]
            for w in range(max_weight, w_j - 1, -1):
                prev = prev_vals[w - w_j]
                if prev > neg:
                    cand = prev + v_j
                    if cand > cur_vals[w]:
                        cur_vals[w] = cand
                        cur_picks[w] = prev_picks[w - w_j] + (ref,)
    return values[r], picks[r]


def _knapsack_exact_counts(
    groups: List[Tuple],
    max_weight: int,
) -> Tuple[Optional[float], Optional[List]]:
    """Pick exactly ``r`` items from each group so total weight ≤ ``max_weight``,
    maximising total value. Exact optimum, polynomial — no ``C(n, r)`` blow-up.

    ``groups`` is a list of ``(items, r)`` where ``items`` are
    ``(weight:int, value:float, ref)``. Returns ``(best_value, picks)`` with
    ``picks`` aligned to the non-empty groups, or ``(None, None)`` when no
    selection meets every count within budget.

    Each group is reduced to a per-weight value profile and folded into a
    running sparse (max, +) convolution over total weight.
    """
    neg = float("-inf")
    state: List[Tuple[int, float, List]] = [(0, 0.0, [])]
    for group in groups:
        items, r = group[0], group[1]
        if r <= 0:
            continue
        prof_val, prof_pick = _group_count_profile(items, r, max_weight)
        profile = [
            (w, prof_val[w], prof_pick[w])
            for w in range(max_weight + 1)
            if prof_val[w] > neg
        ]
        if not profile:
            return None, None
        best_at: Dict[int, Tuple[float, List]] = {}
        for w1, base, base_pick in state:
            room = max_weight - w1
            for w2, pv, pick in profile:
                if w2 > room:
                    break
                w = w1 + w2
                cand = base + pv
                prev = best_at.get(w)
                if prev is None or cand > prev[0]:
                    best_at[w] = (cand, base_pick + [pick])
        if not best_at:
            return None, None
        state = [(w, v, p) for w, (v, p) in sorted(best_at.items())]

    best_v, best_pick = neg, None
    for _w, v, p in state:
        if v > best_v:
            best_v, best_pick = v, p
    if best_v <= neg or best_pick is None:
        return None, None
    return best_v, best_pick


def best_full_teams(
    players_list,
    formations=possible_formations,
    budget=300,
    translator=None,
    verbose=1,
    progress_callback: Optional[Callable[[float], None]] = None,
):
    """Find the best 11 for each formation within ``budget``.

    Count-constrained DP (exact on the quantized knapsack), always uncapped
    after safe reductions (top-r per discretized price, r-dominance). Formations
    impose exact positive counts, so there is no empty-team / range-solve path.
    """
    disable_tqdm = _tqdm_disabled(verbose)
    verbose = bool(verbose)

    unlimited_budget = budget <= 0 or budget >= 100000
    if unlimited_budget:
        quantum = _INTEGER_PRICE_QUANTUM
        budget_int = 1
        candidates = list(players_list)
    else:
        candidates = [p for p in players_list if (p.price or 0) <= budget]
        quantum = _price_quantum(budget, candidates)
        budget_int = _to_budget_int(budget, quantum)

    pool = _CandidatePool(
        candidates, unlimited_budget=unlimited_budget, quantum=quantum,
    )
    n_formations = len(formations) or 1

    update_ui = None
    if STREAMLIT_ACTIVE:
        _label = (
            translator("loader.knapsack_progress")
            if callable(translator)
            else "Calculando mejores combinaciones"
        )
        progress_text = st.empty()
        progress_bar = st.progress(0.0)

        def update_ui(fraction: float):
            progress_bar.progress(fraction)
            progress_text.text(f"{_label}: {int(fraction * 100)} %")

    formation_score_players = []
    for i, formation in enumerate(
        tqdm(formations, disable=disable_tqdm, desc="Knapsack Progress")
    ):
        req_by_pos = _formation_requirements(formation)
        groups = pool.build_groups(req_by_pos)
        score, picks = _knapsack_exact_counts(groups, budget_int)

        fraction = (i + 1) / n_formations
        if progress_callback:
            progress_callback(fraction * 100)
        if update_ui:
            update_ui(fraction)

        if score is None or not picks:
            if not unlimited_budget:
                rescued = pool.cheapest_real_selection(req_by_pos, budget)
                if rescued:
                    result_players = [candidates[idx] for idx in rescued]
                    score = sum(_player_value(p) for p in result_players)
                    formation_score_players.append((formation, score, result_players))
            continue
        result_players = [candidates[idx] for group_pick in picks for idx in group_pick]
        if not result_players:
            continue
        if not unlimited_budget:
            real_cost = sum(_real_price(p) for p in result_players)
            if real_cost > budget + _IEEE_QUANTUM_EPS:
                continue
        formation_score_players.append((formation, score, result_players))

    formation_score_players_by_score = sorted(
        formation_score_players, key=lambda tup: tup[1], reverse=True
    )

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
        formation_boostedscore_players_list = best_full_teams(
            players_list_with_boosts, formations, budget,
        )
        if not formation_boostedscore_players_list:
            continue

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
