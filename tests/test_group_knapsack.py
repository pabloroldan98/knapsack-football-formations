"""Count-DP knapsack: exact, no C(n, r) blow-up, no value-truncation.

Ported from the SoccerSolver tests on ``fix/review-simulator-changes`` and
adapted to this repo's Player duck-type (``.price`` / ``.value`` / coarse
positions) and integer fantasy budgets.
"""
import itertools
import random
import unittest

from pathlib import Path
from unittest.mock import patch

from group_knapsack import (
    _CandidatePool,
    _DECIMAL_PRICE_QUANTUM,
    _INTEGER_PRICE_QUANTUM,
    _knapsack_exact_counts,
    _r_dominance_reduce,
    _to_budget_int,
    _to_weight,
    best_full_teams,
)


class _P:
    def __init__(self, name, position, price, value):
        self.name = name
        self.position = position
        self.price = price
        self.value = value

    def __repr__(self):
        return f"{self.name}({self.position} p={self.price} v={self.value})"


def _squad(*rows):
    """``(name, pos, price, value)`` rows → player list."""
    return [_P(*row) for row in rows]


class ExactCountsCorrectnessTests(unittest.TestCase):
    def test_single_group_pick_two_within_budget(self):
        items = [(1, 5.0, "a"), (2, 8.0, "b"), (3, 10.0, "c")]
        value, picks = _knapsack_exact_counts([(items, 2)], max_weight=4)
        self.assertEqual(value, 15.0)
        self.assertEqual(len(picks), 1)
        self.assertEqual(set(picks[0]), {"a", "c"})

    def test_two_groups_pick_one_each(self):
        g0 = [(1, 5.0, "x"), (2, 8.0, "y")]
        g1 = [(1, 3.0, "p"), (3, 10.0, "q")]
        value, picks = _knapsack_exact_counts([(g0, 1), (g1, 1)], max_weight=4)
        self.assertEqual(value, 15.0)
        self.assertEqual(set(picks[0]), {"x"})
        self.assertEqual(set(picks[1]), {"q"})

    def test_infeasible_when_not_enough_items(self):
        items = [(1, 5.0, "a"), (2, 8.0, "b")]
        value, picks = _knapsack_exact_counts([(items, 3)], max_weight=100)
        self.assertIsNone(value)
        self.assertIsNone(picks)

    def test_infeasible_when_budget_too_tight(self):
        items = [(5, 10.0, "a"), (6, 12.0, "b")]
        value, picks = _knapsack_exact_counts([(items, 1)], max_weight=4)
        self.assertIsNone(value)
        self.assertIsNone(picks)

    def test_zero_weight_items_unlimited_budget_case(self):
        items = [(0, 5.0, "a"), (0, 9.0, "b"), (0, 7.0, "c")]
        value, picks = _knapsack_exact_counts([(items, 2)], max_weight=1)
        self.assertEqual(value, 16.0)
        self.assertEqual(set(picks[0]), {"b", "c"})


class ExactCountsEquivalenceTests(unittest.TestCase):
    """The DP optimum must equal a brute-force optimum (independent oracle)."""

    def _brute_optimum(self, groups, max_weight):
        per_group_choices = []
        for items, r in groups:
            combs = list(itertools.combinations(items, r))
            if not combs:
                return None
            per_group_choices.append(combs)
        best = None
        for selection in itertools.product(*per_group_choices):
            total_w = sum(w for group in selection for w, _v, _ref in group)
            if total_w > max_weight:
                continue
            total_v = sum(v for group in selection for _w, v, _ref in group)
            if best is None or total_v > best:
                best = total_v
        return best

    def test_matches_brute_force_on_random_instances(self):
        rng = random.Random(20260722)
        for trial in range(200):
            n_groups = rng.randint(1, 3)
            groups = []
            for gi in range(n_groups):
                n = rng.randint(2, 8)
                r = rng.randint(1, min(3, n))
                items = [
                    (rng.randint(1, 8), float(rng.randint(1, 20)), f"g{gi}i{j}")
                    for j in range(n)
                ]
                groups.append((items, r))
            max_weight = rng.randint(5, 30)

            new_value, picks = _knapsack_exact_counts(groups, max_weight)
            old_value = self._brute_optimum(groups, max_weight)

            if old_value is None:
                self.assertIsNone(new_value, msg=f"trial {trial}")
                continue

            self.assertIsNotNone(new_value, msg=f"trial {trial}")
            self.assertEqual(new_value, old_value, msg=f"trial {trial}")
            total_w = 0
            for (items, r), chosen in zip(groups, picks, strict=True):
                self.assertEqual(len(chosen), r, msg=f"trial {trial}")
                weight_by_ref = {ref: w for w, _v, ref in items}
                total_w += sum(weight_by_ref[ref] for ref in chosen)
            self.assertLessEqual(total_w, max_weight, msg=f"trial {trial}")


class DominanceReduceTests(unittest.TestCase):
    def test_drops_strictly_dominated_extra_items(self):
        items = [
            (1, 10.0, 0),
            (1, 9.0, 1),
            (2, 8.0, 2),
            (5, 1.0, 3),
        ]
        kept = _r_dominance_reduce(items, r=1)
        refs = {it[2] for it in kept}
        self.assertIn(0, refs)
        self.assertNotIn(3, refs)

    def test_keeps_the_r_cheapest_even_if_low_value(self):
        items = [
            (1, 1.0, "cheap"),
            (10, 100.0, "star"),
            (10, 99.0, "star2"),
        ]
        kept = _r_dominance_reduce(items, r=1)
        refs = {it[2] for it in kept}
        self.assertIn("cheap", refs)
        self.assertIn("star", refs)


class BestFullTeamsTests(unittest.TestCase):
    def _mini_league(self):
        return _squad(
            ("gk-a", "GK", 10, 8),
            ("gk-b", "GK", 5, 4),
            ("def-star", "DEF", 40, 30),
            ("def-ok", "DEF", 8, 12),
            ("def-cheap", "DEF", 4, 6),
            ("mid-star", "MID", 40, 28),
            ("mid-ok", "MID", 8, 11),
            ("att-star", "ATT", 40, 32),
            ("att-ok", "ATT", 8, 13),
        )

    def test_picks_highest_value_when_budget_allows(self):
        results = best_full_teams(
            self._mini_league(), formations=[[1, 1, 1]], budget=300, verbose=0,
        )
        self.assertTrue(results)
        _formation, score, team = results[0]
        names = {p.name for p in team}
        self.assertEqual(names, {"gk-a", "def-star", "mid-star", "att-star"})
        self.assertEqual(score, 8 + 30 + 28 + 32)

    def test_tight_budget_keeps_the_cheap_player_truncation_would_drop(self):
        """The old speed-cap kept the N highest-value players per line.

        With many expensive stars, that dropped the only affordable DEF and
        reported no team. The count-DP must still find the feasible XI.
        """
        players = _squad(
            ("gk", "GK", 5, 5),
            ("mid", "MID", 5, 5),
            ("att", "ATT", 5, 5),
            ("def-cheap", "DEF", 5, 3),
        )
        for i in range(40):
            players.append(_P(f"def-star-{i}", "DEF", 50, 100 - i * 0.01))

        results = best_full_teams(
            players, formations=[[1, 1, 1]], budget=20, verbose=0,
        )
        self.assertTrue(results, "tight budget must still return a feasible team")
        names = {p.name for p in results[0][2]}
        self.assertIn("def-cheap", names)
        self.assertLessEqual(sum(p.price for p in results[0][2]), 20)

    def test_never_exceeds_budget(self):
        results = best_full_teams(
            self._mini_league(), formations=[[1, 1, 1]], budget=30, verbose=0,
        )
        self.assertTrue(results)
        team = results[0][2]
        self.assertLessEqual(sum(p.price for p in team), 30)

    def test_unlimited_budget_does_not_mutate_player_prices(self):
        players = self._mini_league()
        original = {p.name: p.price for p in players}
        results = best_full_teams(
            players, formations=[[1, 1, 1]], budget=-1, verbose=0,
        )
        self.assertTrue(results)
        self.assertEqual({p.name: p.price for p in players}, original)
        names = {p.name for p in results[0][2]}
        self.assertEqual(names, {"gk-a", "def-star", "mid-star", "att-star"})

    def test_infeasible_formation_is_omitted(self):
        players = _squad(
            ("gk", "GK", 5, 5),
            ("def", "DEF", 5, 5),
            ("mid", "MID", 5, 5),
        )
        results = best_full_teams(
            players, formations=[[1, 1, 1]], budget=300, verbose=0,
        )
        self.assertEqual(results, [])

    def test_four_length_formation_honours_gk_count(self):
        players = _squad(
            ("gk", "GK", 5, 5),
            ("def", "DEF", 5, 5),
            ("mid", "MID", 5, 5),
            ("att", "ATT", 5, 5),
        )
        results = best_full_teams(
            players, formations=[[0, 1, 1, 1]], budget=300, verbose=0,
        )
        self.assertTrue(results)
        names = {p.name for p in results[0][2]}
        self.assertNotIn("gk", names)
        self.assertEqual(len(results[0][2]), 3)

    def test_signature_has_no_speed_flags(self):
        import inspect

        params = inspect.signature(best_full_teams).parameters
        self.assertNotIn("speed", params)
        self.assertNotIn("speed_up", params)

    def test_solver_source_has_no_speed_caps(self):
        src = Path("group_knapsack.py").read_text(encoding="utf-8")
        self.assertNotIn("_SPEED_TOTAL_PLAYER_CAP", src)
        self.assertNotIn("_apply_speed_cap", src)
        self.assertNotIn("_apply_weighted_player_cap", src)
        self.assertNotIn("_resolve_speed_tier", src)
        self.assertNotIn("speed_up", src)
        self.assertNotRegex(src, r"\bspeed\s*=")

    def test_uses_the_full_post_filter_pool(self):
        """No global 'keep the best N players' cap: every affordable player
        is visible to the CandidatePool, including a cheap unique DEF that
        a value-truncation of the first 50/90/200 would drop."""
        players = _squad(
            ("gk", "GK", 5, 5),
            ("mid", "MID", 5, 5),
            ("att", "ATT", 5, 5),
            ("def-cheap", "DEF", 5, 1),
        )
        for i in range(250):
            players.append(_P(f"def-star-{i}", "DEF", 40, 200 - i * 0.01))
        results = best_full_teams(
            players, formations=[[1, 1, 1]], budget=20, verbose=0,
        )
        self.assertTrue(results)
        names = {p.name for p in results[0][2]}
        self.assertIn("def-cheap", names)

    def test_fractional_values_are_not_collapsed(self):
        """SoccerSolver had to decouple value scale from price scale. Here values
        stay floats, so 0.6 must beat 0.4 instead of rounding to the same int."""
        players = _squad(
            ("gk", "GK", 1, 1),
            ("def-low", "DEF", 1, 0.4),
            ("def-high", "DEF", 1, 0.6),
            ("mid", "MID", 1, 1),
            ("att", "ATT", 1, 1),
        )
        results = best_full_teams(players, [[1, 1, 1]], 10, verbose=0)
        names = {p.name for p in results[0][2]}
        self.assertIn("def-high", names)
        self.assertNotIn("def-low", names)

    def test_433_returns_eleven_players(self):
        players = []
        for pos, n in (("GK", 3), ("DEF", 12), ("MID", 12), ("ATT", 10)):
            for i in range(n):
                players.append(_P(f"{pos}-{i}", pos, 10 + i, 50 - i))
        results = best_full_teams(players, [[4, 3, 3]], 300, verbose=0)
        self.assertTrue(results)
        team = results[0][2]
        self.assertEqual(len(team), 11)
        counts = {pos: 0 for pos in ("GK", "DEF", "MID", "ATT")}
        for p in team:
            counts[p.position] += 1
        self.assertEqual(counts, {"GK": 1, "DEF": 4, "MID": 3, "ATT": 3})

    def test_large_line_does_not_enumerate_combinations(self):
        """C(50, 4) meta-items used to explode; the count-DP must stay cheap."""
        import time
        players = [
            _P("gk", "GK", 1, 1),
            _P("mid", "MID", 1, 1),
            _P("att", "ATT", 1, 1),
        ]
        for i in range(50):
            players.append(_P(f"def-{i}", "DEF", 1 + (i % 9), 10 + i))
        t0 = time.perf_counter()
        results = best_full_teams(players, [[4, 1, 1]], 40, verbose=0)
        elapsed = time.perf_counter() - t0
        self.assertTrue(results)
        self.assertEqual(sum(1 for p in results[0][2] if p.position == "DEF"), 4)
        self.assertLess(elapsed, 0.5)


class ProgressReportingTests(unittest.TestCase):
    def _mini_league(self):
        return _squad(
            ("gk-a", "GK", 10, 8),
            ("def-ok", "DEF", 8, 12),
            ("mid-ok", "MID", 8, 11),
            ("att-ok", "ATT", 8, 13),
        )

    def test_verbose_zero_is_silent(self):
        from io import StringIO
        from unittest.mock import patch

        out, err = StringIO(), StringIO()
        with patch("sys.stdout", out), patch("sys.stderr", err):
            best_full_teams(
                self._mini_league(), formations=[[1, 1, 1]], budget=300, verbose=0,
            )
        self.assertEqual(out.getvalue().strip(), "")
        self.assertNotIn("Knapsack Progress", err.getvalue())

    def test_verbose_does_not_change_the_optimum(self):
        from io import StringIO
        from unittest.mock import patch

        players = self._mini_league()
        quiet = best_full_teams(players, [[1, 1, 1]], 300, verbose=0)
        with patch("sys.stdout", StringIO()), patch("sys.stderr", StringIO()):
            noisy = best_full_teams(players, [[1, 1, 1]], 300, verbose=1)
        self.assertEqual(quiet[0][1], noisy[0][1])
        self.assertEqual(
            [p.name for p in quiet[0][2]],
            [p.name for p in noisy[0][2]],
        )

    def test_progress_callback_reaches_100(self):
        percents = []
        best_full_teams(
            self._mini_league(),
            formations=[[1, 1, 1], [1, 1, 1], [1, 1, 1]],
            budget=300,
            verbose=0,
            progress_callback=percents.append,
        )
        self.assertTrue(percents)
        self.assertEqual(percents[-1], 100)
        self.assertTrue(all(0 <= p <= 100 for p in percents))
        self.assertEqual(len(percents), 3)

    def test_streamlit_is_not_active_in_unit_tests(self):
        import group_knapsack

        self.assertFalse(group_knapsack.STREAMLIT_ACTIVE)
        results = best_full_teams(
            self._mini_league(), formations=[[1, 1, 1]], budget=300, verbose=0,
        )
        self.assertTrue(results)

    def test_verbose_zero_one_and_two_return_the_same_team(self):
        from io import StringIO
        from unittest.mock import patch

        players = self._mini_league()
        formations = [[1, 1, 1]]
        quiet = best_full_teams(players, formations, 300, verbose=0)

        def _run(verbose):
            with patch("sys.stdout", StringIO()), patch("sys.stderr", StringIO()):
                return best_full_teams(players, formations, 300, verbose=verbose)

        v1 = _run(1)
        v2 = _run(2)
        for other in (v1, v2):
            self.assertEqual(quiet[0][0], other[0][0])
            self.assertEqual(quiet[0][1], other[0][1])
            self.assertEqual(
                [p.name for p in quiet[0][2]],
                [p.name for p in other[0][2]],
            )
            self.assertEqual(
                sum(p.price for p in quiet[0][2]),
                sum(p.price for p in other[0][2]),
            )

    def test_progress_callback_is_monotonic_and_independent_of_verbose(self):
        percents = []
        best_full_teams(
            self._mini_league(),
            formations=[[1, 1, 1], [1, 1, 1], [1, 1, 1]],
            budget=300,
            verbose=0,
            progress_callback=percents.append,
        )
        self.assertEqual(percents, sorted(percents))
        self.assertEqual(percents[-1], 100)
        self.assertTrue(all(0 <= p <= 100 for p in percents))

    def test_tqdm_wraps_formations_once_when_verbose(self):
        from io import StringIO
        from unittest.mock import patch

        calls = []

        def spy_tqdm(iterable, disable=False, desc="", **_kwargs):
            items = list(iterable)
            calls.append({"n": len(items), "disable": disable, "desc": desc})
            return items

        formations = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
        with patch("group_knapsack.tqdm", spy_tqdm), patch(
            "sys.stdout", StringIO()
        ), patch("sys.stderr", StringIO()):
            best_full_teams(
                self._mini_league(), formations=formations, budget=300, verbose=1,
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["n"], 3)
        self.assertFalse(calls[0]["disable"])

        calls.clear()
        with patch("group_knapsack.tqdm", spy_tqdm):
            best_full_teams(
                self._mini_league(), formations=formations, budget=300, verbose=0,
            )
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0]["disable"])

    def test_tqdm_is_not_used_inside_the_dp(self):
        import inspect

        from group_knapsack import _group_count_profile, _knapsack_exact_counts

        dp_src = inspect.getsource(_knapsack_exact_counts) + inspect.getsource(
            _group_count_profile
        )
        self.assertNotIn("tqdm", dp_src)

    def test_streamlit_active_disables_tqdm_but_still_updates_st_progress(self):
        from io import StringIO
        from unittest.mock import MagicMock, patch

        tqdm_calls = []

        def spy_tqdm(iterable, disable=False, desc="", **_kwargs):
            tqdm_calls.append(disable)
            return list(iterable)

        st = MagicMock()
        bar = MagicMock()
        st.progress.return_value = bar
        with patch("group_knapsack.STREAMLIT_ACTIVE", True), patch(
            "group_knapsack.st", st
        ), patch("group_knapsack.tqdm", spy_tqdm), patch(
            "sys.stdout", StringIO()
        ):
            best_full_teams(
                self._mini_league(),
                formations=[[1, 1, 1], [1, 1, 1]],
                budget=300,
                verbose=2,
            )
        self.assertEqual(tqdm_calls, [True])
        st.progress.assert_called()
        bar.progress.assert_called()

    def test_tqdm_off_when_silent_or_streamlit(self):
        from group_knapsack import _tqdm_disabled

        self.assertTrue(_tqdm_disabled(0, streamlit_active=False))
        self.assertFalse(_tqdm_disabled(1, streamlit_active=False))
        self.assertFalse(_tqdm_disabled(2, streamlit_active=False))
        self.assertTrue(_tqdm_disabled(1, streamlit_active=True))
        self.assertTrue(_tqdm_disabled(2, streamlit_active=True))


class DiscretizationTests(unittest.TestCase):
    """ceil(price)+int(budget) used to drop a player priced exactly at a
    decimal budget. Quantum 0.1 plus a real-price rescue closes that hole.
    """

    def test_on_grid_tenths_survive_binary_float_division(self):
        """10.2 / 0.1 is 101.999... in IEEE-754. Without the 1e-9 nudge,
        floor(budget) would be 101 while ceil(price) is 102 → false miss.

        Weight uses ceil(x/q - 1e-9); capacity uses floor(x/q + 1e-9).
        On the 0.1 grid they agree. Off-grid 10.25 does not (103 vs 102);
        that hole is the rescue's job, not a reason to round blindly.
        """
        q = _DECIMAL_PRICE_QUANTUM
        expected = {10.1: 101, 10.2: 102, 10.3: 103}
        for amount, units in expected.items():
            self.assertEqual(_to_weight(amount, q), units, msg=amount)
            self.assertEqual(_to_budget_int(amount, q), units, msg=amount)
            raw = float(amount) / q
            if amount in (10.1, 10.2):
                self.assertLess(raw, units)
                self.assertGreater(raw, units - 1)

        self.assertEqual(_to_weight(10.25, q), 103)
        self.assertEqual(_to_budget_int(10.25, q), 102)

    def test_integer_amounts_stay_on_quantum_one(self):
        self.assertEqual(_to_weight(10, _INTEGER_PRICE_QUANTUM), 10)
        self.assertEqual(_to_budget_int(300, _INTEGER_PRICE_QUANTUM), 300)

    def test_off_grid_tenth_equal_to_budget_is_rescued(self):
        """10.25 is not a production unit; DP weight 103 > capacity 102.
        Rescue must still return the only feasible XI."""
        players = _squad(
            ("gk", "GK", 0, 1),
            ("def", "DEF", 10.25, 5),
            ("mid", "MID", 0, 1),
            ("att", "ATT", 0, 1),
        )
        calls = {"n": 0}
        orig = _CandidatePool.cheapest_real_selection

        def _spy(self, req_by_pos, budget):
            calls["n"] += 1
            return orig(self, req_by_pos, budget)

        with patch.object(_CandidatePool, "cheapest_real_selection", _spy):
            results = best_full_teams(players, [[1, 1, 1]], 10.25, verbose=0)
        self.assertTrue(results)
        self.assertGreaterEqual(calls["n"], 1)
        self.assertLessEqual(sum(p.price for p in results[0][2]), 10.25 + 1e-9)

    def test_integer_production_units_do_not_need_rescue(self):
        """Typical Biwenger/API units are integers. Rescue is a discretization
        safety net, not a second solver: it should stay idle here."""
        players = []
        for pos, n in (("GK", 4), ("DEF", 40), ("MID", 40), ("ATT", 30)):
            for i in range(n):
                players.append(_P(f"{pos}-{i}", pos, 5 + (i % 25), 20 - i * 0.05))
        calls = {"n": 0}
        orig = _CandidatePool.cheapest_real_selection

        def _spy(self, req_by_pos, budget):
            calls["n"] += 1
            return orig(self, req_by_pos, budget)

        with patch.object(_CandidatePool, "cheapest_real_selection", _spy):
            results = best_full_teams(
                players,
                formations=[[3, 4, 3], [4, 3, 3], [4, 4, 2], [5, 3, 2]],
                budget=300,
                verbose=0,
            )
        self.assertTrue(results)
        self.assertEqual(calls["n"], 0)

    def test_decimal_price_equal_to_decimal_budget_is_feasible(self):
        players = _squad(
            ("gk", "GK", 0, 1),
            ("def", "DEF", 10.2, 5),
            ("mid", "MID", 0, 1),
            ("att", "ATT", 0, 1),
        )
        results = best_full_teams(players, [[1, 1, 1]], 10.2, verbose=0)
        self.assertTrue(results)
        names = {p.name for p in results[0][2]}
        self.assertIn("def", names)
        self.assertLessEqual(sum(p.price for p in results[0][2]), 10.2 + 1e-9)

    def test_integer_budget_keeps_unit_quantum(self):
        from group_knapsack import _INTEGER_PRICE_QUANTUM, _price_quantum

        players = _squad(("a", "GK", 10, 1), ("b", "DEF", 20, 1))
        self.assertEqual(_price_quantum(30, players), _INTEGER_PRICE_QUANTUM)

    def test_zero_price_players_are_selectable(self):
        players = _squad(
            ("gk", "GK", 0, 3),
            ("def-paid", "DEF", 8, 1),
            ("def-free", "DEF", 0, 9),
            ("mid", "MID", 0, 1),
            ("att", "ATT", 0, 1),
        )
        results = best_full_teams(players, [[1, 1, 1]], 5, verbose=0)
        names = {p.name for p in results[0][2]}
        self.assertIn("def-free", names)

    def test_no_duplicate_players_and_exact_counts(self):
        players = _squad(
            ("gk", "GK", 1, 1),
            ("d1", "DEF", 1, 3),
            ("d2", "DEF", 1, 2),
            ("d3", "DEF", 1, 1),
            ("m1", "MID", 1, 3),
            ("m2", "MID", 1, 2),
            ("m3", "MID", 1, 1),
            ("a1", "ATT", 1, 3),
            ("a2", "ATT", 1, 2),
        )
        results = best_full_teams(players, [[3, 3, 2]], 20, verbose=0)
        team = results[0][2]
        names = [p.name for p in team]
        self.assertEqual(len(names), len(set(names)))
        counts = {pos: 0 for pos in ("GK", "DEF", "MID", "ATT")}
        for p in team:
            counts[p.position] += 1
        self.assertEqual(counts, {"GK": 1, "DEF": 3, "MID": 3, "ATT": 2})

    def test_matches_real_price_brute_force_on_decimals(self):
        prices = (9.9, 10.0, 10.1, 10.2, 10.5, 10.9, 11.0)
        budgets = (10, 10.1, 10.2, 10.5, 10.9, 11)
        for budget in budgets:
            for def_price in prices:
                players = _squad(
                    ("gk", "GK", 0, 1),
                    ("def", "DEF", def_price, 5),
                    ("mid", "MID", 0, 1),
                    ("att", "ATT", 0, 1),
                )
                results = best_full_teams(players, [[1, 1, 1]], budget, verbose=0)
                real_ok = (0 + def_price + 0 + 0) <= budget + 1e-9
                if real_ok:
                    self.assertTrue(
                        results,
                        msg=f"false infeasible def={def_price} budget={budget}",
                    )
                    self.assertLessEqual(
                        sum(p.price for p in results[0][2]), budget + 1e-9
                    )
                elif results:
                    self.assertLessEqual(
                        sum(p.price for p in results[0][2]), budget + 1e-9
                    )


class CandidatePoolTests(unittest.TestCase):
    def test_keeps_top_r_per_price_bucket(self):
        players = [
            _P("keep", "DEF", 10, 9),
            _P("drop", "DEF", 10, 1),
            _P("other", "DEF", 11, 20),
        ]
        pool = _CandidatePool(players)
        items = pool.group("DEF", 1)
        refs = {it[2] for it in items}
        self.assertIn(0, refs)
        self.assertNotIn(1, refs)
        self.assertIn(2, refs)


if __name__ == "__main__":
    unittest.main()
