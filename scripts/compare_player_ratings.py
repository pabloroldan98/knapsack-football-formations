"""
Compara dos JSON de ratings {equipo: {jugador: rating}} y muestra las mayores diferencias.
Solo considera equipos y jugadores presentes en ambos archivos.

Uso:
  python scripts/compare_player_ratings.py
"""
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from useful_functions import ROOT_DIR


# --- Configuración ---
COMPETITION = "mundial"
FILE_A = f"sofascore_{COMPETITION}_players_ratings"
FILE_B = f"sofascore_{COMPETITION}_players_ratings_OLD"
THRESHOLD = 0.1  # |delta| mínimo para mostrar un jugador
# ---------------------


def load_ratings(file_name):
    path = os.path.join(ROOT_DIR, "json_files", file_name + ".json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compare_ratings(data_a, data_b, threshold):
    common_teams = sorted(set(data_a) & set(data_b))
    differences = []
    compared_players = 0

    for team in common_teams:
        players_a = data_a[team]
        players_b = data_b[team]
        if not isinstance(players_a, dict) or not isinstance(players_b, dict):
            continue

        common_players = set(players_a) & set(players_b)
        compared_players += len(common_players)

        for player in sorted(common_players):
            rating_a = players_a[player]
            rating_b = players_b[player]
            if not isinstance(rating_a, (int, float)) or not isinstance(rating_b, (int, float)):
                continue

            delta = rating_a - rating_b
            abs_delta = abs(delta)
            if abs_delta >= threshold:
                differences.append({
                    "team": team,
                    "player": player,
                    "rating_a": rating_a,
                    "rating_b": rating_b,
                    "delta": delta,
                    "abs_delta": abs_delta,
                })

    differences.sort(key=lambda item: item["abs_delta"], reverse=True)
    return common_teams, compared_players, differences


def print_report(file_a, file_b, threshold, common_teams, compared_players, differences):

    print(f"Archivo A: {file_a}.json")
    print(f"Archivo B: {file_b}.json")
    print(f"Umbral: {threshold}")
    print(f"Equipos en común: {len(common_teams)}")
    print(f"Jugadores en común: {compared_players}")
    print(f"Diferencias >= umbral: {len(differences)}")
    print()

    if not differences:
        print("No hay diferencias por encima del umbral.")
        return

    print(f"{'#':>3}  {'Equipo':<22} {'Jugador':<30} {'A':>8} {'B':>8} {'diff':>8}")
    print("-" * 87)
    for index, item in enumerate(differences, start=1):
        print(
            f"{index:>3}  {item['team']:<22} {item['player']:<30} "
            f"{item['rating_a']:>8.4f} {item['rating_b']:>8.4f} "
            f"{item['delta']:>+8.4f}"
        )


def main():
    data_a = load_ratings(FILE_A)
    data_b = load_ratings(FILE_B)
    common_teams, compared_players, differences = compare_ratings(data_a, data_b, THRESHOLD)
    print_report(FILE_A, FILE_B, THRESHOLD, common_teams, compared_players, differences)


if __name__ == "__main__":
    main()
