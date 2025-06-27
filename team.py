import csv
import os
import copy

from unidecode import unidecode

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root


class Team:
    def __init__(
            self,
            name: str,
            next_opponent: str,
            elo: float,
            is_home: bool = False,
            num_ok: int = 0,
            num_injured: int = 0,
            num_doubt: int = 0,
            num_sanctioned: int = 0,
            num_warned: int = 0,
            img_link: str = "https://cdn.biwenger.com/i/t/XXXXX.png",
    ):
        self.name = name
        self.next_opponent = next_opponent
        self.elo = elo
        self.is_home = is_home
        self.num_ok = num_ok
        self.num_injured = num_injured
        self.num_doubt = num_doubt
        self.num_sanctioned = num_sanctioned
        self.num_warned = num_warned
        self.img_link = img_link

    def __str__(self):
        return f"({self.name}, {self.elo})"

    def __eq__(self, other_player):
        if unidecode(self.name).lower() in unidecode(other_player.name).lower() \
                or unidecode(other_player.name).lower() in unidecode(self.name).lower():
            return True
        else:
            return False


def get_old_teams_data(forced_matches=[]):
    with open(f'{ROOT_DIR}/csv_files/unused/OLD_teams_before_jornada_03.csv', newline='') as f:
        reader = csv.reader(f)
        data = list(reader)
    old_teams_data = []
    for d in data:
        new_team = Team(
            d[0],
            d[1],
            float(d[2]),
            bool(d[3]),
            int(d[4]),
            int(d[5]),
            int(d[6]),
            int(d[7]),
            int(d[8])
        )
        old_teams_data.append(new_team)
    if forced_matches:
        for old_team in old_teams_data:
            team_name = old_team.name
            team_name_next_opponent = None
            is_playing_home = False
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


def set_team_status_nerf(teams_list, verbose=False):
    result_teams = copy.deepcopy(teams_list)

    for team in result_teams:
        team_nerf = 10 * (team.num_injured + team.num_sanctioned) + 5 * (team.num_doubt)
        prev_elo = team.elo
        team.elo = team.elo - team_nerf
        if verbose:
            print(f"{team.name}: {prev_elo} --> {team.elo} (-{team_nerf})")

    return result_teams
