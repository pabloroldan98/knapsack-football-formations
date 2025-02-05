import pandas as pd
import datetime
from pprint import pprint

from useful_functions import find_manual_similar_string, read_dict_data, overwrite_dict_data


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
        full_teams_elos_dict = {find_manual_similar_string(key): value for key, value in full_teams_elos.items()}
    else:
        # Get today's date in the format 'YYYY-MM-DD'
        today = datetime.date.today().strftime('%Y-%m-%d')
        url = f"http://api.clubelo.com/{today}"
        teams_elos_df = pd.read_csv(url)

        filtered_teams_elos_df = teams_elos_df[
            (teams_elos_df['Country'] == country) &
            ((teams_elos_df['Level'] == 1) | (teams_elos_df['Level'] == 2))
        ]
        full_teams_elos = dict(zip(filtered_teams_elos_df['Club'], filtered_teams_elos_df['Elo']))
        full_teams_elos_dict = {find_manual_similar_string(key): value for key, value in full_teams_elos.items()}
        # teams_elos_dict = full_teams_elos_dict.copy()

    return full_teams_elos_dict  # , teams_elos_dict


def get_teams_elos_dict(
        is_country=False,
        country="ESP",
        write_file=False,
        file_name="elo_ratings_laliga_data",
        force_scrape=True
):
    data = None
    if force_scrape:
        try:
            data = get_teams_elos(is_country=is_country, country=country)
        except:
            pass
    if not data: # if force_scrape failed or not force_scrape
        if is_country:
            file_name = "elo_ratings_countries_data"
        data = read_dict_data(file_name)
        if data:
            return data

    if write_file:
        # write_dict_data(data, file_name)
        overwrite_dict_data(data, file_name)

    return data


# result = get_teams_elos()
# for team, elo in result.items():
#     print(f"{team}: {elo}")
