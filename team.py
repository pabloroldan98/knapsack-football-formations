import csv

from unidecode import unidecode


class Team:
    def __init__(
            self,
            name: str,
            next_opponent: str,
            elo: float
    ):
        self.name = name
        self.next_opponent = next_opponent
        self.elo = elo

    def __str__(self):
        return f"({self.name}, {self.elo})"

    def __eq__(self, other_player):
        if unidecode(self.name).lower() in unidecode(other_player.name).lower() \
                or unidecode(other_player.name).lower() in unidecode(self.name).lower():
            return True
        else:
            return False


def get_old_teams_data(forced_matches=[]):
    with open('OLD_teams_before_jornada_03.csv', newline='') as f:
        reader = csv.reader(f)
        data = list(reader)
    old_teams_data = []
    for d in data:
        new_team = Team(
            d[0],
            d[1],
            float(d[2])
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
                if unidecode(team_name).lower() == unidecode(away_team).lower():
                    team_name_next_opponent = home_team
            old_team.next_opponent = team_name_next_opponent

    return old_teams_data
