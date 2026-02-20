"""
Exporta los datos de jugadores a archivos JSON estáticos en data/.
Útil para:
  - Tener datos pre-generados como backup/cache
  - Servir datos estáticos desde IONOS sin necesidad del backend
  - Debugging y desarrollo local del frontend

Uso:
  python export_players_json.py                    # Exporta LaLiga Biwenger (default)
  python export_players_json.py --competition laliga --app biwenger
  python export_players_json.py --all              # Exporta todas las combinaciones

Los archivos se guardan en data/<competition>_<app>_players.json
"""
import argparse
import json
import os
import sys

from main import get_current_players_wrapper
from useful_functions import read_dict_data
from biwenger import get_next_jornada

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")


def player_to_dict(player, divide_millions=False):
    """Serializa un Player a diccionario JSON-friendly."""
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


COMPETITIONS = [
    {"key": "laliga",    "apps": ["biwenger", "laligafantasy"]},
    {"key": "premier",   "apps": ["biwenger"]},
    {"key": "seriea",    "apps": ["biwenger"]},
    {"key": "ligueone",  "apps": ["biwenger"]},
    {"key": "segunda",   "apps": ["biwenger"]},
    {"key": "champions", "apps": ["biwenger"]},
]


def export_players(competition="laliga", app="biwenger"):
    """Exporta jugadores de una competición+app a JSON."""
    is_biwenger = (app == "biwenger")
    is_tournament = competition in [
        "mundialito", "champions", "europaleague", "conference",
        "mundial", "eurocopa", "copaamerica",
    ]
    divide_millions = (not is_tournament) and is_biwenger

    print(f"  Cargando {competition} ({app})...")
    try:
        players = get_current_players_wrapper(
            competition=competition,
            is_biwenger=is_biwenger,
            no_form=False,
            no_fixtures=False,
            nerf_penalty_boost=False,
            forced_matches=[],
        )
    except Exception as e:
        print(f"  ERROR cargando {competition}/{app}: {e}")
        return None

    players_data = [player_to_dict(p, divide_millions) for p in players]
    teams = sorted({p["team"] for p in players_data})

    result = {
        "competition": competition,
        "app": app,
        "divide_millions": divide_millions,
        "is_tournament": is_tournament,
        "is_laliga": competition == "laliga",
        "teams": teams,
        "players": players_data,
        "total_players": len(players_data),
    }

    # Guardar
    os.makedirs(DATA_DIR, exist_ok=True)
    filename = f"{competition}_{app}_players.json"
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  ✅ Exportados {len(players_data)} jugadores -> {filepath}")
    return filepath


def export_jornadas(competition="laliga"):
    """Exporta las jornadas disponibles a JSON."""
    jornadas_dict = read_dict_data(f"forced_matches_{competition}_2025_26")
    if not jornadas_dict:
        print(f"  No hay jornadas para {competition}")
        return None

    next_j = get_next_jornada(competition)
    result = {
        "competition": competition,
        "next_jornada": next_j,
        "jornadas": [
            {"key": k, "label": k.replace("_", " ").strip().title()}
            for k in jornadas_dict
        ],
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    filename = f"{competition}_jornadas.json"
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  ✅ Exportadas {len(result['jornadas'])} jornadas -> {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Exporta datos de jugadores a JSON")
    parser.add_argument("--competition", "-c", default="laliga",
                        help="Competición a exportar (default: laliga)")
    parser.add_argument("--app", "-a", default="biwenger",
                        help="App fuente de datos (default: biwenger)")
    parser.add_argument("--all", action="store_true",
                        help="Exportar todas las competiciones y apps")
    args = parser.parse_args()

    print("=" * 60)
    print("Exportador de datos - Calculadora Fantasy")
    print("=" * 60)

    if args.all:
        for comp in COMPETITIONS:
            for app in comp["apps"]:
                export_players(comp["key"], app)
            if comp["key"] == "laliga":
                export_jornadas(comp["key"])
    else:
        export_players(args.competition, args.app)
        if args.competition == "laliga":
            export_jornadas(args.competition)

    print("\n✅ Exportación completada.")


if __name__ == "__main__":
    main()
