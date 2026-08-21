"""API knapsack integration: both calculate endpoints share best_full_teams."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


class _P:
    def __init__(self, name, position, price, value, team="Spain"):
        self.name = name
        self.position = position
        self.price = price
        self.value = value
        self.show_value = value
        self.team = team
        self.form = 1.0
        self.fixture = 1.0
        self.start_probability = 0.9
        self.status = "ok"
        self.img_link = ""
        self.opponent = ""


def _pool(n_def=80):
    players = [
        _P("gk-a", "GK", 10, 8),
        _P("gk-b", "GK", 8, 6),
        _P("mid-a", "MID", 12, 14),
        _P("mid-b", "MID", 11, 13),
        _P("mid-c", "MID", 9, 10),
        _P("mid-d", "MID", 8, 9),
        _P("att-a", "ATT", 14, 16),
        _P("att-b", "ATT", 12, 12),
        _P("att-c", "ATT", 7, 8),
        _P("att-d", "ATT", 6, 7),
    ]
    for i in range(n_def):
        # Mix of expensive stars and one uniquely cheap DEF so a [:200]
        # truncation-by-value would drop it if n_def is large.
        price = 4 if i == n_def - 1 else 20 + (i % 15)
        value = 3 if i == n_def - 1 else 40 - (i % 20) * 0.1
        players.append(_P(f"def-{i}", "DEF", price, value))
    return players


_PAYLOAD = {
    "competition": "laliga",
    "app": "biwenger",
    "budget": 300,
    "formations": [[4, 3, 3]],
    "min_prob": 0.0,
    "max_prob": 1.0,
    "use_fixture_filter": False,
    "blinded_names": [],
    "banned_names": [],
}


def _client():
    from api import app

    return TestClient(app)


class ApiKnapsackIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.players = _pool(80)
        self._cache = patch("api._get_cached", return_value=self.players)
        self._purge = patch("api.purge_everything", side_effect=lambda ps, **_k: ps)
        self._log_calc = patch("api.database.log_calculation", return_value=1)
        self._log_res = patch("api.database.log_result_formation")
        self._init = patch("api.database.init")
        for p in (self._cache, self._purge, self._log_calc, self._log_res, self._init):
            p.start()
            self.addCleanup(p.stop)

    def test_api_py_has_no_second_knapsack_or_old_caps(self):
        src = Path("api.py").read_text(encoding="utf-8")
        self.assertNotIn("from MCKP", src)
        self.assertNotIn("players_preproc", src)
        self.assertNotIn("knapsack_multichoice", src)
        self.assertNotIn("working[:200]", src)
        self.assertNotIn("fl[:90]", src)
        self.assertNotIn("fl[:100]", src)
        self.assertNotIn("fl[:150]", src)
        self.assertNotIn("p.price = 0", src)
        self.assertNotIn("speed_up: bool = False", src)
        self.assertNotIn("req.speed_up", src)

    def test_calculate_delegates_to_best_full_teams_with_full_pool(self):
        captured = {}
        import group_knapsack

        real = group_knapsack.best_full_teams

        def wrapped(players, formations, budget, **kwargs):
            captured["n"] = len(players)
            captured["names"] = {p.name for p in players}
            captured["verbose"] = kwargs.get("verbose")
            captured["has_callback"] = kwargs.get("progress_callback") is not None
            return real(players, formations, budget, **kwargs)

        with patch("api.best_full_teams", wrapped):
            resp = _client().post("/api/calculate", json=_PAYLOAD)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(captured["n"], len(self.players))
        self.assertEqual(captured["verbose"], 0)
        self.assertFalse(captured["has_callback"])
        self.assertIn("def-79", captured["names"])
        body = resp.json()
        self.assertTrue(body["formations"])

    def test_calculate_stream_delegates_to_the_same_solver(self):
        captured = {}
        import group_knapsack

        real = group_knapsack.best_full_teams

        def wrapped(players, formations, budget, **kwargs):
            captured["n"] = len(players)
            captured["verbose"] = kwargs.get("verbose")
            captured["has_callback"] = kwargs.get("progress_callback") is not None
            captured["names"] = {p.name for p in players}
            return real(players, formations, budget, **kwargs)

        with patch("api.best_full_teams", wrapped):
            resp = _client().post("/api/calculate-stream", json=_PAYLOAD)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(captured["n"], len(self.players))
        self.assertEqual(captured["verbose"], 0)
        self.assertTrue(captured["has_callback"])
        self.assertIn("def-79", captured["names"])

        percents = []
        result = None
        for line in resp.text.splitlines():
            if not line.startswith("data: "):
                continue
            event = json.loads(line[6:])
            if event.get("type") == "progress":
                percents.append(event["percent"])
            elif event.get("type") == "result":
                result = event["data"]
        self.assertTrue(percents)
        self.assertEqual(percents, sorted(percents))
        self.assertTrue(all(0 <= p <= 100 for p in percents))
        self.assertEqual(percents[-1], 100)
        self.assertTrue(result["formations"])

    def test_api_schema_has_no_speed(self):
        import inspect

        from api import CalculateRequest
        from group_knapsack import best_full_teams

        self.assertNotIn("speed_up", CalculateRequest.model_fields)
        self.assertNotIn("speed", CalculateRequest.model_fields)
        params = inspect.signature(best_full_teams).parameters
        self.assertNotIn("speed_up", params)
        self.assertNotIn("speed", params)

    def test_frontend_streamlit_and_logging_have_no_speed_api(self):
        import inspect

        from db import log_calculation

        js = Path("app/js/app.js").read_text(encoding="utf-8")
        html = Path("app/index.html").read_text(encoding="utf-8")
        streamlit = Path("streamlit_app.py").read_text(encoding="utf-8")
        for blob in (js, html, streamlit):
            self.assertNotIn("speed_up", blob)
            self.assertNotIn("use_slow_calc", blob)
            self.assertNotIn("slow_calc", blob)
        params = inspect.signature(log_calculation).parameters
        self.assertNotIn("speed_up", params)
        self.assertNotIn("speed", params)

    def test_unlimited_budget_does_not_mutate_cached_player_prices(self):
        original = {p.name: p.price for p in self.players}
        names = [p.name for p in self.players]
        payload = {**_PAYLOAD, "selected_player_names": names, "budget": 300}
        resp = _client().post("/api/calculate", json=payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual({p.name: p.price for p in self.players}, original)
        self.assertTrue(all(p != 0 for p in original.values()))

    def test_calculate_and_stream_return_the_same_team(self):
        client = _client()
        calc = client.post("/api/calculate", json=_PAYLOAD).json()["formations"][0]
        stream = client.post("/api/calculate-stream", json=_PAYLOAD)
        result = None
        for line in stream.text.splitlines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                if event.get("type") == "result":
                    result = event["data"]["formations"][0]
        self.assertIsNotNone(result)
        self.assertEqual(calc["formation"], result["formation"])
        self.assertEqual(calc["score"], result["score"])
        self.assertEqual(
            [p["name"] for p in calc["players"]],
            [p["name"] for p in result["players"]],
        )


if __name__ == "__main__":
    unittest.main()
