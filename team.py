import csv
import os

from unidecode import unidecode

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root


class Team:
    def __init__(
            self,
            name: str,
            next_opponent: str,
            elo: float,
            is_home: bool
    ):
        self.name = name
        self.next_opponent = next_opponent
        self.elo = elo
        self.is_home = is_home

    def __str__(self):
        return f"({self.name}, {self.elo})"

    def __eq__(self, other_player):
        if unidecode(self.name).lower() in unidecode(other_player.name).lower() \
                or unidecode(other_player.name).lower() in unidecode(self.name).lower():
            return True
        else:
            return False


def get_old_teams_data(forced_matches=[]):
    with open(f'{ROOT_DIR}/csv_files/OLD_teams_before_jornada_03.csv', newline='') as f:
        reader = csv.reader(f)
        data = list(reader)
    old_teams_data = []
    for d in data:
        new_team = Team(
            d[0],
            d[1],
            float(d[2]),
            bool(d[3])
        )
        old_teams_data.append(new_team)
    if forced_matches:
        for old_team in old_teams_data:
            team_name = old_team.name
            team_name_next_opponent = None
            for new_match in forced_matches:
                home_team = new_match[0]
                away_team = new_match[1]
                if unidecode(team_name).lower() == unidecode(home_team).lower():
                    team_name_next_opponent = away_team
                    is_playing_home = True
                if unidecode(team_name).lower() == unidecode(away_team).lower():
                    team_name_next_opponent = home_team
                    is_playing_home = False
            old_team.next_opponent = team_name_next_opponent
            old_team.is_home = is_playing_home

    return old_teams_data
