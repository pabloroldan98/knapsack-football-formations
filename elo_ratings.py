import numpy as np
import pandas as pd
import datetime
from pprint import pprint

import re
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


def get_besoccer_teams_elos():
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

    full_besoccer_teams_elos_dict = {
        find_manual_similar_string(key): value for key, value in besoccer_elos_dict.items()
    }

    return full_besoccer_teams_elos_dict


def get_footballdatabase_teams_elos():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # 1. Fetch the page
    url = 'https://footballdatabase.com/league-scores-tables/fifa-club-world-cup-2025'
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

    # 2. Find all <a> within any <table> whose href starts with '/clubs-ranking/'
    pattern = re.compile(r"^/clubs-ranking/")
    footballdatabase_teams = []
    seen_urls = set()
    for table in soup.find_all('table'):
        for a in table.find_all('a', href=pattern):
            link_text = a.get_text(strip=True)
            href = a['href']
            if href in seen_urls:
                continue
            seen_urls.add(href)
            footballdatabase_teams.append({
                'name': link_text,
                'url': "https://footballdatabase.com" + href
            })

    # 3. For each team, fetch its page and parse the ELO
    for team in footballdatabase_teams:
        team_url = team['url']
        resp = tls_requests.get(team_url, headers=headers, verify=False)
        team_soup = BeautifulSoup(resp.text, "html.parser")

        elo = None
        # Try each table.table-hover until we successfully extract an ELO
        for table in team_soup.find_all('table', class_='table table-hover'):
            active_tr = table.find('tr', class_='active')
            if not active_tr:
                continue

            tds = active_tr.find_all('td')
            if not tds:
                continue

            elo_text = tds[-1].get_text(strip=True)
            try:
                elo = float(elo_text)
            except ValueError:
                # fallback: leave as raw text or None
                elo = None
            break  # stop after first successful parse

        team['elo'] = elo

    footballdatabase_elos_dict = {
        team['name']: team['elo']
        for team in sorted(
            footballdatabase_teams,
            key=lambda t: (t['elo'] is None, t['elo']),  # None’s go last
            reverse=True
        )
    }

    full_besoccer_teams_elos_dict = {
        find_manual_similar_string(key): value for key, value in footballdatabase_elos_dict.items()
    }

    return full_besoccer_teams_elos_dict


def get_model_prediction(teams_elos_dict, besoccer_teams_elos_dict, footballdatabase_teams_elos_dict):
    teams_elo = pd.Series(teams_elos_dict, name="teams_elo")
    besoccer_elo = pd.Series(besoccer_teams_elos_dict, name="besoccer_elo")
    footballdb_elo = pd.Series(footballdatabase_teams_elos_dict, name="footballdb_elo")

    # Combine into a single DataFrame
    df_elo = pd.concat([teams_elo, besoccer_elo, footballdb_elo], axis=1)
    df_elo.columns = ["teams_elo", "besoccer_elo", "footballdb_elo"]

    # ——————————————————————————
    # 1) Fit the three regressions (only if data is available)
    # ——————————————————————————

    def fit_linear_regression(X, y):
        X_b = np.c_[np.ones((X.shape[0], 1)), X]  # Add intercept
        theta = np.linalg.pinv(X_b.T @ X_b) @ X_b.T @ y
        return theta

    def predict(X, theta):
        X_b = np.c_[np.ones((X.shape[0], 1)), X]
        return X_b @ theta

    reg_full = reg_besoccer = reg_footballdb = None

    # a) Full 2-predictor model
    mask_full_train = df_elo[["teams_elo", "besoccer_elo", "footballdb_elo"]].notna().all(axis=1)
    if mask_full_train.sum() > 0:
        X_full = df_elo.loc[mask_full_train, ["besoccer_elo", "footballdb_elo"]].values
        y_full = df_elo.loc[mask_full_train, "teams_elo"].values
        reg_full = fit_linear_regression(X_full, y_full)

    # b) BeSoccer-only model
    mask_besoccer_train = df_elo[["teams_elo", "besoccer_elo"]].notna().all(axis=1)
    if mask_besoccer_train.sum() > 0:
        X_besoccer = df_elo.loc[mask_besoccer_train, ["besoccer_elo"]].values
        y_besoccer = df_elo.loc[mask_besoccer_train, "teams_elo"].values
        reg_besoccer = fit_linear_regression(X_besoccer, y_besoccer)

    # c) FBDB-only model
    mask_footballdb_train = df_elo[["teams_elo", "footballdb_elo"]].notna().all(axis=1)
    if mask_footballdb_train.sum() > 0:
        X_footballdb = df_elo.loc[mask_footballdb_train, ["footballdb_elo"]].values
        y_footballdb = df_elo.loc[mask_footballdb_train, "teams_elo"].values
        reg_footballdb = fit_linear_regression(X_footballdb, y_footballdb)

    # ——————————————————————————
    # 2) Predict into each “missing” scenario
    # ——————————————————————————

    if reg_full is not None:
        mask_full_pred = (
            df_elo["teams_elo"].isna()
            & df_elo[["besoccer_elo", "footballdb_elo"]].notna().all(axis=1)
        )
        if mask_full_pred.any():
            Xp_full = df_elo.loc[mask_full_pred, ["besoccer_elo", "footballdb_elo"]].values
            df_elo.loc[mask_full_pred, "teams_elo"] = predict(Xp_full, reg_full)

    if reg_besoccer is not None:
        mask_besoccer_pred = (
            df_elo["teams_elo"].isna()
            & df_elo["besoccer_elo"].notna()
            & df_elo["footballdb_elo"].isna()
        )
        if mask_besoccer_pred.any():
            Xp_besoccer = df_elo.loc[mask_besoccer_pred, ["besoccer_elo"]].values
            df_elo.loc[mask_besoccer_pred, "teams_elo"] = predict(Xp_besoccer, reg_besoccer)

    if reg_footballdb is not None:
        mask_footballdb_pred = (
            df_elo["teams_elo"].isna()
            & df_elo["footballdb_elo"].notna()
            & df_elo["besoccer_elo"].isna()
        )
        if mask_footballdb_pred.any():
            Xp_footballdb = df_elo.loc[mask_footballdb_pred, ["footballdb_elo"]].values
            df_elo.loc[mask_footballdb_pred, "teams_elo"] = predict(Xp_footballdb, reg_footballdb)

    # ——————————————————————————
    # 3) Return as dict
    # ——————————————————————————
    return df_elo["teams_elo"].to_dict()


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
            full_besoccer_teams_elos_dict = get_besoccer_teams_elos()
            full_footballdatabase_teams_elos_dict = get_footballdatabase_teams_elos()
            empty_teams_elos_dict = {key: None for key in full_footballdatabase_teams_elos_dict}

            # Model
            partial_teams_elos_dict_complete = get_model_prediction(full_teams_elos_dict, full_besoccer_teams_elos_dict, full_footballdatabase_teams_elos_dict)
            partial_teams_elos_dict_besoccer = get_model_prediction(full_teams_elos_dict, full_besoccer_teams_elos_dict, empty_teams_elos_dict)

            # full_teams_elos_dict = {
            #     team: (partial_teams_elos_dict_complete[team] + partial_teams_elos_dict_besoccer[team]) / 2
            #     for team in partial_teams_elos_dict_complete
            # }
            full_teams_elos_dict = partial_teams_elos_dict_complete.copy()

            # ─── Fit polynomials y = f(x) of degree 1 ───────────────────────────────
            # x = np.array([full_besoccer_teams_elos_dict[t] for t in common])
            # y = np.array([full_teams_elos_dict[t] for t in common])
            # coeffs1 = np.polyfit(x, y, 1)  # [m,     b]
            # poly1 = np.poly1d(coeffs1)
            # def y_from_x_deg1(x_val):
            #     """Linear: y = m*x + b"""
            #     return poly1(x_val)
            # full_teams_elos_dict = {
            #     team: (
            #         full_teams_elos_dict[team]  # if it was in common, keep the original
            #         if team in common
            #         else y_from_x_deg1(x_bes)  # otherwise predict via your linear fit
            #     )
            #     for team, x_bes in full_besoccer_teams_elos_dict.items()
            # }

    full_teams_elos_dict = dict(
        sorted(full_teams_elos_dict.items(), key=lambda kv: kv[1], reverse=True)
    )

    # Compute the keys present in both source dicts
    common_keys = set(full_besoccer_teams_elos_dict) & set(full_footballdatabase_teams_elos_dict)

    # Filter full_teams_elos_dict in-place (or assign to a new variable)
    full_teams_elos_dict = {k: v for k, v in full_teams_elos_dict.items() if k in common_keys}

    return full_teams_elos_dict


# result = get_teams_elos(country=None, extra_teams=True)
# # pprint(result)
# items = list(result.items())
# print("{")
# for i, (team, elo) in enumerate(items):
#     print(f'  "{team}": {elo}{"," if i < len(items) - 1 else ""}')
# print("}")
