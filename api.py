"""
FastAPI backend for Calculadora Fantasy.
Replaces Streamlit with a REST API that the HTML/JS frontend calls.
"""
import copy
import hashlib
import os
import time
from typing import Optional, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from main import get_current_players_wrapper
from group_knapsack import best_full_teams
from player import purge_everything
from useful_functions import read_dict_data, percentile_ranks_dict, percentile_rank
from biwenger import get_next_jornada

app = FastAPI(title="Calculadora Fantasy API", version="1.0.0")

# CORS: FRONTEND_URL desde variable de entorno (Render, Docker, etc.)
_cors_origins = [
    "https://www.calculadorafantasy.com",
    "https://calculadorafantasy.com",
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:8080",
    "http://localhost:3000",
]
_frontend_url = os.getenv("FRONTEND_URL", "").strip()
if _frontend_url:
    _cors_origins.append(_frontend_url.rstrip("/"))
    # Si es https://www.dominio.com, añadir también https://dominio.com
    if _frontend_url.startswith("https://www."):
        _cors_origins.append("https://" + _frontend_url[12:].split("/")[0])
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (frontend) from the project root
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Cache ────────────────────────────────────────────────────────────────────
_player_cache: dict = {}
_cache_ts: dict = {}
CACHE_TTL = 300  # seconds


def _cache_key(*args) -> str:
    return hashlib.md5("|".join(str(a) for a in args).encode()).hexdigest()


def _get_cached(key):
    if key in _player_cache and time.time() - _cache_ts.get(key, 0) < CACHE_TTL:
        return _player_cache[key]
    return None


def _set_cached(key, data):
    _player_cache[key] = data
    _cache_ts[key] = time.time()


# ─── Serialisation ────────────────────────────────────────────────────────────
def player_to_dict(player, divide_millions=False):
    show_price = round(player.price / 10, 1) if divide_millions else player.price
    form_val = player.form if isinstance(player.form, (int, float)) else 1.0
    fixture_val = player.fixture if isinstance(player.fixture, (int, float)) else 1.0
    return {
        "name": player.name,
        "position": player.position,
        "price": show_price,
        "raw_price": player.price,
        "value": round(player.value, 3),
        "show_value": player.show_value,
        "team": player.team,
        "opponent": getattr(player, "opponent", ""),
        "form": round(form_val, 4),
        "fixture": round(fixture_val, 4),
        "start_probability": round(player.start_probability, 4),
        "img_link": player.img_link,
        "status": player.status,
    }


# ─── Request models ──────────────────────────────────────────────────────────
class CalculateRequest(BaseModel):
    competition: str = "laliga"
    app: str = "biwenger"
    ignore_form: bool = False
    ignore_fixtures: bool = False
    ignore_penalties: bool = False
    jornada_key: str = ""
    num_jornadas: int = 1

    budget: int = 200
    blinded_names: List[str] = []
    banned_names: List[str] = []
    formations: List[List[int]] = [
        [3, 4, 3], [3, 5, 2], [4, 3, 3],
        [4, 4, 2], [4, 5, 1], [5, 3, 2], [5, 4, 1],
    ]
    min_prob: float = 0.65
    max_prob: float = 1.0
    use_fixture_filter: bool = False
    speed_up: bool = True

    # "My Best 11" mode: only these players are considered, budget = -1
    selected_player_names: Optional[List[str]] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _load_players(competition, is_biwenger, no_form, no_fixtures, nerf_penalty,
                  jornada_key, num_jornadas):
    jornadas_dict = None
    forced_matches = []
    if jornada_key:
        jornadas_dict = read_dict_data(f"forced_matches_{competition}_2025_26")
        if jornadas_dict and jornada_key in jornadas_dict:
            forced_matches = jornadas_dict[jornada_key]

    current_players = get_current_players_wrapper(
        competition=competition,
        is_biwenger=is_biwenger,
        no_form=no_form,
        no_fixtures=no_fixtures,
        nerf_penalty_boost=nerf_penalty,
        forced_matches=forced_matches,
    )

    # Multi-jornada averaging (LaLiga only)
    if competition == "laliga" and num_jornadas > 1 and jornadas_dict and jornada_key:
        jkeys = list(jornadas_dict.keys())
        try:
            idx = jkeys.index(jornada_key)
        except ValueError:
            idx = -1

        if idx >= 0:
            future_players = None
            distant_players = None

            if num_jornadas >= 2 and idx + 1 < len(jkeys):
                future_players = get_current_players_wrapper(
                    competition=competition, is_biwenger=is_biwenger,
                    no_form=True, no_fixtures=no_fixtures,
                    nerf_penalty_boost=nerf_penalty,
                    forced_matches=jornadas_dict[jkeys[idx + 1]],
                )

            if num_jornadas >= 3 and idx + 2 < len(jkeys):
                distant_players = get_current_players_wrapper(
                    competition=competition, is_biwenger=is_biwenger,
                    no_form=True, no_fixtures=no_fixtures,
                    nerf_penalty_boost=nerf_penalty,
                    forced_matches=jornadas_dict[jkeys[idx + 2]],
                )

            if distant_players and future_players:
                for cp in current_players:
                    for fp in future_players:
                        for dp in distant_players:
                            if cp.name == fp.name == dp.name:
                                cp.value = (cp.value + fp.value + dp.value) / 3
                                cp.show_value = cp.calc_show_value()
                                cp.form = (cp.form + fp.form + dp.form) / 3
                                cp.fixture = (cp.fixture + fp.fixture + dp.fixture) / 3
            elif future_players:
                for cp in current_players:
                    for fp in future_players:
                        if cp.name == fp.name:
                            cp.value = (cp.value + fp.value) / 2
                            cp.show_value = cp.calc_show_value()
                            cp.form = (cp.form + fp.form) / 2
                            cp.fixture = (cp.fixture + fp.fixture) / 2

    return current_players


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/competitions")
def get_competitions():
    return {"competitions": [
        {"key": "laliga",    "name_es": "LaLiga",              "name_en": "LaLiga",                  "has_jornadas": True,  "apps": ["biwenger", "laligafantasy"]},
        {"key": "premier",   "name_es": "Premier League",      "name_en": "Premier League",          "has_jornadas": False, "apps": ["biwenger"]},
        {"key": "seriea",    "name_es": "Serie A",             "name_en": "Serie A",                 "has_jornadas": False, "apps": ["biwenger"]},
        {"key": "ligueone",  "name_es": "Ligue 1",            "name_en": "Ligue 1",                 "has_jornadas": False, "apps": ["biwenger"]},
        {"key": "segunda",   "name_es": "Segunda División",   "name_en": "Spanish Second Division", "has_jornadas": False, "apps": ["biwenger"]},
        {"key": "champions", "name_es": "Champions League",    "name_en": "Champions League",        "has_jornadas": False, "apps": ["biwenger"]},
    ]}


@app.get("/api/jornadas")
def get_jornadas(competition: str = "laliga"):
    jornadas_dict = read_dict_data(f"forced_matches_{competition}_2025_26")
    if not jornadas_dict:
        return {"jornadas": [], "next_jornada": None}
    next_j = get_next_jornada(competition)
    jornadas = [{"key": k, "label": k.replace("_", " ").strip().title()} for k in jornadas_dict]
    return {"jornadas": jornadas, "next_jornada": next_j}


@app.get("/api/players")
def get_players(
    competition: str = "laliga",
    app: str = "biwenger",
    ignore_form: bool = False,
    ignore_fixtures: bool = False,
    ignore_penalties: bool = False,
    jornada_key: str = "",
    num_jornadas: int = 1,
):
    is_biwenger = (app == "biwenger")
    is_tournament = competition in [
        "mundialito", "champions", "europaleague", "conference",
        "mundial", "eurocopa", "copaamerica",
    ]
    divide_millions = (not is_tournament) and is_biwenger

    key = _cache_key(competition, is_biwenger, ignore_form, ignore_fixtures,
                     ignore_penalties, jornada_key, num_jornadas)

    players = _get_cached(key)
    if players is None:
        players = _load_players(competition, is_biwenger, ignore_form,
                                ignore_fixtures, ignore_penalties,
                                jornada_key, num_jornadas)
        _set_cached(key, players)

    teams = sorted({p.team for p in players})

    return {
        "players": [player_to_dict(p, divide_millions) for p in players],
        "teams": teams,
        "divide_millions": divide_millions,
        "is_tournament": is_tournament,
        "is_laliga": competition == "laliga",
    }


@app.post("/api/calculate")
def calculate(req: CalculateRequest):
    is_biwenger = (req.app == "biwenger")
    is_tournament = req.competition in [
        "mundialito", "champions", "europaleague", "conference",
        "mundial", "eurocopa", "copaamerica",
    ]
    divide_millions = (not is_tournament) and is_biwenger

    key = _cache_key(req.competition, is_biwenger, req.ignore_form,
                     req.ignore_fixtures, req.ignore_penalties,
                     req.jornada_key, req.num_jornadas)

    all_players = _get_cached(key)
    if all_players is None:
        all_players = _load_players(
            req.competition, is_biwenger, req.ignore_form,
            req.ignore_fixtures, req.ignore_penalties,
            req.jornada_key, req.num_jornadas,
        )
        _set_cached(key, all_players)

    # Subset for "My Best 11"
    if req.selected_player_names is not None:
        working = [copy.deepcopy(p) for p in all_players
                   if p.name in set(req.selected_player_names)]
    else:
        working = copy.deepcopy(all_players)

    # Remove banned
    banned = set(req.banned_names)
    working = [p for p in working if p.name not in banned]

    # Apply prob / fixture filters
    filtered = purge_everything(working, probability_threshold=req.min_prob,
                                fixture_filter=req.use_fixture_filter)
    filtered_names = {p.name for p in filtered}
    blinded = set(req.blinded_names)

    working = [
        p for p in working
        if (p.name in filtered_names
            and req.min_prob <= p.start_probability <= req.max_prob)
        or p.name in blinded
    ]

    # Boost blinded
    for p in working:
        if p.name in blinded:
            p.value = max(1000, p.value * 1000)
            p.start_probability = 10
            p.form = 10
            p.fixture = 10

    if len(working) < 11:
        return {"error": "not_enough_players", "formations": []}

    working.sort(key=lambda x: (-x.value, -x.form, -x.fixture, x.price, x.team))
    needed = working[:200]

    budget = req.budget
    if req.selected_player_names is not None:
        budget = -1

    results = best_full_teams(
        needed, req.formations, budget,
        speed_up=req.speed_up, verbose=0,
    )

    # Build response using original (un-boosted) player data
    orig_map = {p.name: p for p in all_players}
    formations_out = []

    for formation, score, players in results:
        if score == -1:
            continue

        actual = [orig_map.get(p.name, p) for p in players]
        actual_score = sum(p.show_value for p in actual)
        actual_price = sum(p.price for p in actual)
        show_price = round(actual_price / 10, 1) if divide_millions else actual_price

        result_names = {p.name for p in actual}
        missing = [n for n in req.blinded_names if n not in result_names]

        lines = {"GK": [], "DEF": [], "MID": [], "ATT": []}
        for pl in actual:
            d = player_to_dict(pl, divide_millions)
            d["is_blinded"] = pl.name in blinded
            lines[pl.position].append(d)

        formations_out.append({
            "formation": formation,
            "score": actual_score,
            "total_price": show_price,
            "lines": lines,
            "players": [player_to_dict(pl, divide_millions) for pl in actual],
            "missing_blinded": missing,
        })

    return {"formations": formations_out}


# ─── Static files (serve frontend) ───────────────────────────────────────────
# This lets you run the ENTIRE app (frontend + API) from a single server
# during development: python api.py → http://localhost:8000/
app.mount("/", StaticFiles(directory=ROOT_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
