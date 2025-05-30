import numpy as np
import pandas as pd
import datetime
from pprint import pprint

import requests
import tls_requests
import urllib3
from bs4 import BeautifulSoup
from matplotlib import pyplot as plt

from useful_functions import find_manual_similar_string, read_dict_data, overwrite_dict_data


def get_teams_elos_dict(
        is_country=False,
        country="ESP",
        extra_teams=False,
        write_file=False,
        file_name="elo_ratings_laliga_data",
        force_scrape=False
):
    data = None
    if force_scrape:
        try:
            data = get_teams_elos(is_country=is_country, country=country, extra_teams=extra_teams)
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


def get_teams_elos(is_country=False, country="ESP", extra_teams=False):
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

        if country is not None:
            filtered_teams_elos_df = teams_elos_df[
                (teams_elos_df['Country'] == country) &
                (teams_elos_df['Level'].isin([1, 2, ]))
            ]
        else:
            filtered_teams_elos_df = teams_elos_df[
                teams_elos_df['Level'].isin([1, ])
            ]
        full_teams_elos = dict(zip(filtered_teams_elos_df['Club'], filtered_teams_elos_df['Elo']))
        full_teams_elos_dict = {find_manual_similar_string(key): value for key, value in full_teams_elos.items()}

        if extra_teams:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            # 1. Fetch the page
            url = 'https://es.besoccer.com/competicion/clasificacion/mundial_clubes'
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                )
            }
            # response = requests.get(league_url, headers=headers, verify=False)
            response = tls_requests.get(url, headers=headers, verify=False)
            html = response.text
            soup = BeautifulSoup(html, "html.parser")

            # 2. Extract all <td class="name"> elements,
            #    find their <a data-cy="team"> child, and grab the span.team-name text + href
            besoccer_teams = []
            for td in soup.find_all('td', class_='name'):
                a = td.find('a', attrs={'data-cy': 'team'})
                if not a:
                    continue
                # team name is inside the <span class="team-name">
                name_span = a.find('span', class_='team-name')
                team_name = name_span.get_text(strip=True) if name_span else None
                url = a.get('href')
                besoccer_teams.append({
                    'name': team_name,
                    'url': url
                })

            # 3. For each team, fetch its page and parse the ELO
            for team in besoccer_teams:
                team_url = team['url']
                resp = tls_requests.get(team_url, headers=headers, verify=False)
                team_soup = BeautifulSoup(resp.text, "html.parser")

                # find the ELO container
                elo_div = team_soup.find('div', class_='elo label-text')
                elo = None
                if elo_div:
                    span = elo_div.find('span')
                    if span:
                        # convert the string (e.g. "1234.56") to float
                        try:
                            elo = float(span.get_text(strip=True))
                        except ValueError:
                            elo = None
                team['elo'] = elo

            besoccer_elos_dict = {
                team['name']: team['elo']
                for team in sorted(
                    besoccer_teams,
                    key=lambda t: (t['elo'] is None, t['elo']),  # None’s go last
                    reverse=True
                )
            }

            full_besoccer_teams_elos_dict = {find_manual_similar_string(key): value for key, value in besoccer_elos_dict.items()}

            # ─── Find common team names ──────────────────────────────────────────────────
            common = set(full_teams_elos_dict) & set(full_besoccer_teams_elos_dict)

            # ─── Build x = besoccer, y = full_teams ──────────────────────────────────────
            x = np.array([full_besoccer_teams_elos_dict[t] for t in common])
            y = np.array([full_teams_elos_dict[t] for t in common])

            # ─── Fit polynomials y = f(x) of degree 1, 2, 3 ───────────────────────────────
            coeffs1 = np.polyfit(x, y, 1)  # [m,     b]
            coeffs2 = np.polyfit(x, y, 2)  # [a2,    a1,   a0]
            coeffs3 = np.polyfit(x, y, 3)  # [a3,    a2,   a1,   a0]

            # Wrap each in a callable poly1d
            poly1 = np.poly1d(coeffs1)
            poly2 = np.poly1d(coeffs2)
            poly3 = np.poly1d(coeffs3)

            # ─── Forward functions y = f(x) ──────────────────────────────────────────────
            def y_from_x_deg1(x_val):
                """Linear: y = m*x + b"""
                return poly1(x_val)
            def y_from_x_deg2(x_val):
                """Quadratic: y = a2*x^2 + a1*x + a0"""
                return poly2(x_val)
            def y_from_x_deg3(x_val):
                """Cubic: y = a3*x^3 + a2*x^2 + a1*x + a0"""
                return poly3(x_val)

            # ─── Build your new dicts: predicted full_teams ELO for every besoccer team ───
            full_teams_elos_dict = {
                team: (
                    full_teams_elos_dict[team]  # if it was in common, keep the original
                    if team in common
                    else y_from_x_deg1(x_bes)  # otherwise predict via your linear fit
                )
                for team, x_bes in full_besoccer_teams_elos_dict.items()
            }
            # full_teams_elos_dict = {
            #     team: y_from_x_deg2(x_bes)
            #     for team, x_bes in full_besoccer_teams_elos_dict.items()
            # }
            # full_teams_elos_dict = {
            #     team: y_from_x_deg3(x_bes)
            #     for team, x_bes in full_besoccer_teams_elos_dict.items()
            # }

    full_teams_elos_dict = dict(
        sorted(full_teams_elos_dict.items(), key=lambda kv: kv[1], reverse=True)
    )
    return full_teams_elos_dict


# result = get_teams_elos(country=None, extra_teams=True)
# for team, elo in result.items():
#     print(f"{team}: {elo}")
