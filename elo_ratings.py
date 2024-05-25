import pandas as pd
import datetime


def get_teams_elos(is_country=False, country="ESP"):
    if is_country:
        teams_elos_url = "https://www.eloratings.net/World.tsv"
        teams_elos_df = pd.read_table(teams_elos_url, sep="\t", header=None, na_filter=False)[[2, 3]]
        teams_elos_dict = dict(teams_elos_df.values)

        teams_alias_url = "https://www.eloratings.net/en.teams.tsv"
        teams_alias_df = pd.read_table(teams_alias_url, sep="\t", header=None, names=range(10), na_filter=False)[[0, 1]]
        teams_alias_dict = dict(teams_alias_df.values)

        full_teams_elos = dict()
        for team_short, team_elo in teams_elos_dict.items():
            team_name = teams_alias_dict[str(team_short)]
            full_teams_elos[str(team_name)] = team_elo
    else:
        # Get today's date in the format 'YYYY-MM-DD'
        today = datetime.date.today().strftime('%Y-%m-%d')
        url = f"http://api.clubelo.com/{today}"
        teams_elos_df = pd.read_csv(url)

        filtered_teams_elos_df = teams_elos_df[
            (teams_elos_df['Country'] == country) &
            (teams_elos_df['Level'] == 1)
        ]
        full_teams_elos = dict(zip(filtered_teams_elos_df['Club'], filtered_teams_elos_df['Elo']))
        teams_elos_dict = full_teams_elos.copy()

    return full_teams_elos  # , teams_elos_dict


# result = get_teams_elos()
# for team, elo in result.items():
#     print(f"{team}: {elo}")
