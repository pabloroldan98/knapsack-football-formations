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
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

from useful_functions import find_manual_similar_string, read_dict_data, overwrite_dict_data, create_driver


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


def get_opta_teams_elos():
    driver = create_driver()
    wait = WebDriverWait(driver, 15)

    # 1. Load the Opta Power Rankings page
    driver.get("https://dataviz.theanalyst.com/opta-power-rankings/")
    wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "tr[class^='_data-table-row']")
        )
    )

    opta_teams_elos = {}
    clicks = 0

    # 2. Paginate until we have 10 000 entries or 100 clicks
    while len(opta_teams_elos) < 10_000 and clicks < 100:
        # print(clicks)
        # 2a. Grab all rows whose class starts with 'get_opta_opta_teams_elos'
        rows = driver.find_elements(
            By.CSS_SELECTOR, "tr[class^='_data-table-row']"
        )
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 3:
                team_name = cells[1].text.strip().title()
                team_name = find_manual_similar_string(team_name)
                elo_text = cells[2].text.strip()
                try:
                    elo = float(elo_text)
                except ValueError:
                    elo = None
                # dedupe by team_name
                if team_name not in opta_teams_elos:
                    opta_teams_elos[team_name] = elo

        # 2b. Stop if target reached
        if len(opta_teams_elos) >= 10_000:
            break

        # 2c. Click “>” to go to next page
        try:
            next_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[@type='button' and normalize-space(.)='>']")
                )
            )
            next_btn.click()
            clicks += 1
            # give JS a moment to re-render the table
            time.sleep(1)
        except Exception:
            # no more pages or click failed
            break

    driver.quit()

    full_opta_teams_elos = {
        find_manual_similar_string(key): value for key, value in opta_teams_elos.items()
    }

    return full_opta_teams_elos


def get_model_prediction(
        teams_elos_dict,
        besoccer_teams_elos_dict,
        footballdatabase_teams_elos_dict,
        opta_teams_elos_dict
):
    # Create Series for each source
    teams_elo = pd.Series(teams_elos_dict, name="teams_elo")
    besoccer_elo = pd.Series(besoccer_teams_elos_dict, name="besoccer_elo")
    footballdb_elo = pd.Series(footballdatabase_teams_elos_dict, name="footballdb_elo")
    opta_elo = pd.Series(opta_teams_elos_dict, name="opta_elo")

    # Combine into a single DataFrame
    df_elo = pd.concat([teams_elo, besoccer_elo, footballdb_elo, opta_elo], axis=1)

    # Helper functions for OLS
    def fit_linear_regression(X, y):
        X_b = np.c_[np.ones((X.shape[0], 1)), X]  # add intercept
        theta = np.linalg.pinv(X_b.T @ X_b) @ X_b.T @ y
        return theta

    def predict(X, theta):
        X_b = np.c_[np.ones((X.shape[0], 1)), X]
        return X_b @ theta

    # Initialize models
    reg_full = reg_bf = reg_bo = reg_fo = reg_b = reg_f = reg_o = None

    # 1) Fit regressions if enough data
    # a) Full 3-predictor model (besoccer + footballdb + opta)
    mask_full_train = df_elo[["teams_elo", "besoccer_elo", "footballdb_elo", "opta_elo"]].notna().all(axis=1)
    if mask_full_train.sum() > 0:
        X_full = df_elo.loc[mask_full_train, ["besoccer_elo", "footballdb_elo", "opta_elo"]].values
        y_full = df_elo.loc[mask_full_train, "teams_elo"].values
        reg_full = fit_linear_regression(X_full, y_full)

    # b) Pairwise models
    # besoccer + footballdb
    mask_bf_train = df_elo[["teams_elo", "besoccer_elo", "footballdb_elo"]].notna().all(axis=1)
    if mask_bf_train.sum() > 0:
        X_bf = df_elo.loc[mask_bf_train, ["besoccer_elo", "footballdb_elo"]].values
        y_bf = df_elo.loc[mask_bf_train, "teams_elo"].values
        reg_bf = fit_linear_regression(X_bf, y_bf)

    # besoccer + opta
    mask_bo_train = df_elo[["teams_elo", "besoccer_elo", "opta_elo"]].notna().all(axis=1)
    if mask_bo_train.sum() > 0:
        X_bo = df_elo.loc[mask_bo_train, ["besoccer_elo", "opta_elo"]].values
        y_bo = df_elo.loc[mask_bo_train, "teams_elo"].values
        reg_bo = fit_linear_regression(X_bo, y_bo)

    # footballdb + opta
    mask_fo_train = df_elo[["teams_elo", "footballdb_elo", "opta_elo"]].notna().all(axis=1)
    if mask_fo_train.sum() > 0:
        X_fo = df_elo.loc[mask_fo_train, ["footballdb_elo", "opta_elo"]].values
        y_fo = df_elo.loc[mask_fo_train, "teams_elo"].values
        reg_fo = fit_linear_regression(X_fo, y_fo)

    # c) Single-predictor models
    # besoccer-only
    mask_b_train = df_elo[["teams_elo", "besoccer_elo"]].notna().all(axis=1)
    if mask_b_train.sum() > 0:
        X_b = df_elo.loc[mask_b_train, ["besoccer_elo"]].values
        y_b = df_elo.loc[mask_b_train, "teams_elo"].values
        reg_b = fit_linear_regression(X_b, y_b)

    # footballdb-only
    mask_f_train = df_elo[["teams_elo", "footballdb_elo"]].notna().all(axis=1)
    if mask_f_train.sum() > 0:
        X_f = df_elo.loc[mask_f_train, ["footballdb_elo"]].values
        y_f = df_elo.loc[mask_f_train, "teams_elo"].values
        reg_f = fit_linear_regression(X_f, y_f)

    # opta-only
    mask_o_train = df_elo[["teams_elo", "opta_elo"]].notna().all(axis=1)
    if mask_o_train.sum() > 0:
        X_o = df_elo.loc[mask_o_train, ["opta_elo"]].values
        y_o = df_elo.loc[mask_o_train, "teams_elo"].values
        reg_o = fit_linear_regression(X_o, y_o)

    # 2) Predict missing target values
    # a) Full model
    if reg_full is not None:
        mask_full_pred = df_elo["teams_elo"].isna() & df_elo[["besoccer_elo", "footballdb_elo", "opta_elo"]].notna().all(axis=1)
        if mask_full_pred.any():
            Xp = df_elo.loc[mask_full_pred, ["besoccer_elo", "footballdb_elo", "opta_elo"]].values
            df_elo.loc[mask_full_pred, "teams_elo"] = predict(Xp, reg_full)

    # b) Pairwise predictions
    pairs = [
        ("besoccer_elo", "footballdb_elo", reg_bf),
        ("besoccer_elo", "opta_elo", reg_bo),
        ("footballdb_elo", "opta_elo", reg_fo)
    ]
    for col1, col2, model in pairs:
        if model is not None:
            mask_pair = (
                df_elo["teams_elo"].isna() &
                df_elo[col1].notna() &
                df_elo[col2].notna() &
                df_elo[[c for c in ["besoccer_elo","footballdb_elo","opta_elo"] if c not in [col1,col2]]].isna().all(axis=1)
            )
            if mask_pair.any():
                Xp = df_elo.loc[mask_pair, [col1, col2]].values
                df_elo.loc[mask_pair, "teams_elo"] = predict(Xp, model)

    # c) Single predictor predictions
    singles = [
        ("besoccer_elo", reg_b),
        ("footballdb_elo", reg_f),
        ("opta_elo", reg_o)
    ]
    for col, model in singles:
        if model is not None:
            mask_single = (
                df_elo["teams_elo"].isna() &
                df_elo[col].notna() &
                df_elo[[c for c in ["besoccer_elo","footballdb_elo","opta_elo"] if c != col]].isna().all(axis=1)
            )
            if mask_single.any():
                Xp = df_elo.loc[mask_single, [col]].values
                df_elo.loc[mask_single, "teams_elo"] = predict(Xp, model)

    # Return predictions as dict
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
            full_opta_teams_elos_dict = get_opta_teams_elos()
            # pprint(full_opta_teams_elos_dict)
            empty_teams_elos_dict = {key: None for key in full_footballdatabase_teams_elos_dict}

            # Model
            partial_teams_elos_dict_complete = get_model_prediction(full_teams_elos_dict, full_besoccer_teams_elos_dict, full_footballdatabase_teams_elos_dict, full_opta_teams_elos_dict)
            # partial_teams_elos_dict_no_footballdatabase = get_model_prediction(full_teams_elos_dict, full_besoccer_teams_elos_dict, empty_teams_elos_dict, full_opta_teams_elos_dict)
            #
            # full_teams_elos_dict = {
            #     team: (partial_teams_elos_dict_complete[team] + partial_teams_elos_dict_no_footballdatabase[team]) / 2
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
