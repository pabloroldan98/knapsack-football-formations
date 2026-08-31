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
from itertools import combinations
from urllib.parse import urljoin, urlparse, parse_qs

from useful_functions import find_manual_similar_string, read_dict_data, overwrite_dict_data, create_driver


def get_teams_elos_dict(
        is_country=False,
        country="ESP",
        extra_teams=False,
        alt_elo=False,
        write_file=False,
        file_name="elo_ratings_laliga_data",
        force_scrape=False
):
    data = None
    storage_file_name = file_name
    if alt_elo and not is_country:
        storage_file_name = f"{file_name}_elofootball"

    if force_scrape:
        try:
            data = get_teams_elos(
                is_country=is_country,
                country=country,
                extra_teams=extra_teams,
                alt_elo=alt_elo,
                file_name=file_name
            )
        except:
            pass

    # Save raw scraped values only. Empty/None is never written.
    if write_file and data:
        overwrite_dict_data(data, storage_file_name)

    if not data:
        if is_country:
            storage_file_name = "elo_ratings_countries_data"
        data = read_dict_data(storage_file_name)

    # Scale EloFootball only when returning it, never when scraping/saving.
    if alt_elo and not is_country and data:
        data = _apply_alt_elo_scale(data)
    return data


def get_besoccer_teams_elos(target_url=None):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # 1. Fetch the page
    # # url = 'https://es.besoccer.com/competicion/clasificacion/mundial_clubes'
    # url = 'https://es.besoccer.com/competicion/clasificacion/primera'
    # Default when None/empty
    url = target_url or "https://es.besoccer.com/competicion/clasificacion/primera"
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


def get_footballdatabase_teams_elos(target_url=None):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # 1. Fetch the page
    # # url = 'https://footballdatabase.com/league-scores-tables/fifa-club-world-cup-2025'
    # # url = 'https://footballdatabase.com/league-scores-tables/spain-primera-division-2024-2025'
    # url = 'https://footballdatabase.com/league-scores-tables/spain-primera-division-2025-2026'
    # Default when None/empty
    url = target_url or "https://footballdatabase.com/league-scores-tables/spain-primera-division-2025-2026"
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


# ClubElo / FIFA-style codes that differ from EloFootball ISO-3166 alpha-3.
CLUBELO_TO_ELOFOOTBALL_ISO = {
    "GER": "DEU",
    "NED": "NLD",
    "POR": "PRT",
    "SUI": "CHE",
    "GRE": "GRC",
    "DEN": "DNK",
    "CRO": "HRV",
    "BUL": "BGR",
    "SLO": "SVN",
    "WAL": "WLS",
}

_elofootball_cache = {}


def _elofootball_country_iso(country):
    if country is None:
        return None
    code = str(country).strip().upper()
    return CLUBELO_TO_ELOFOOTBALL_ISO.get(code, code)


def _discover_elofootball_countries(soup, season, base_url):
    countries = []
    seen_country_codes = set()
    for a in soup.find_all("a", href=True):
        parsed = urlparse(urljoin(base_url, a["href"]))
        query = parse_qs(parsed.query)
        country_iso = query.get("countryiso", [None])[0]
        if not country_iso:
            continue
        season_q = query.get("season", [None])[0]
        if season_q and season and season_q != season:
            continue
        if country_iso in seen_country_codes:
            continue
        name = a.get_text(" ", strip=True)
        if re.search(r"20\d{2}", name):
            continue
        seen_country_codes.add(country_iso)
        countries.append({
            "iso": country_iso,
            "name": name or country_iso,
        })
    int_countries = [c for c in countries if c["iso"] == "INT"]
    other_countries = [c for c in countries if c["iso"] != "INT"]
    return other_countries + int_countries


def _parse_elofootball_country_elo(soup):
    for tag in soup.find_all(["h2", "h3", "h4"]):
        text = tag.get_text(" ", strip=True)
        if "Elo:" not in text:
            continue
        match = re.search(r"Elo:\s*(\d+(?:\.\d+)?)", text)
        if not match:
            continue
        elo = float(match.group(1))
        if elo.is_integer():
            elo = int(elo)
        name = text.split("|")[0].strip()
        return name, elo
    return None, None


ALT_ELO_SCALE = 0.85


def _apply_alt_elo_scale(data, factor=ALT_ELO_SCALE):
    if not data:
        return data
    scaled = {}
    for key, value in data.items():
        if isinstance(value, (int, float)) and value == value:
            scaled[key] = value * factor
        else:
            scaled[key] = value
    return scaled


def get_elofootball_teams_elos(season=None, country=None, request_delay=0.15, as_countries=False):
    """
    Scrapes EloFootball.

    country:
        "ESP" / "GER" / ... -> one country (ClubElo codes are mapped, e.g. GER->DEU)
        None  -> all available countries from the country selector

    as_countries:
        False -> club Elos
        True  -> country Elos (top-10 clubs average on each country page)
    """
    base_url = "https://www.elofootball.com/"

    if season is None:
        season, _ = extract_season_tokens()

    country_iso = _elofootball_country_iso(country)
    cache_key = (season, country_iso, bool(as_countries))
    if cache_key in _elofootball_cache:
        return dict(_elofootball_cache[cache_key])

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )
    }
    session = requests.Session()
    session.headers.update(headers)
    request_timeout = 300  # 5 minutes

    if country_iso is not None:
        countries = [{"iso": country_iso, "name": country_iso}]
    else:
        initial_url = f"{base_url}country.php?countryiso=ENG&season={season}"
        response = session.get(initial_url, timeout=request_timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        countries = _discover_elofootball_countries(soup, season, base_url)

    print(
        f"EloFootball: scraping {len(countries)} countries "
        f"for season {season}"
        f"{' (country ratings)' if as_countries else ''}"
    )

    elofootball_teams = {}
    for i, country_data in enumerate(countries, start=1):
        this_iso = country_data["iso"]
        country_name = country_data["name"]
        url = f"{base_url}country.php?countryiso={this_iso}&season={season}"
        try:
            response = session.get(url, timeout=request_timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            if as_countries:
                heading_name, elo = _parse_elofootball_country_elo(soup)
                if elo is None:
                    print(f"[{i}/{len(countries)}] {country_name} ({this_iso}): country elo not found")
                else:
                    label = heading_name or country_name
                    elofootball_teams[find_manual_similar_string(label)] = elo
                    print(f"[{i}/{len(countries)}] {label} ({this_iso}): {elo}")
            else:
                ranking_heading = soup.find(
                    lambda tag: tag.name in ["h2", "h3", "h4"]
                    and "Elo ranking for" in tag.get_text(" ", strip=True)
                )
                if ranking_heading is None:
                    print(f"[{i}/{len(countries)}] {country_name} ({this_iso}): ranking not found")
                    continue

                ranking_table = ranking_heading.find_next("table")
                if ranking_table is None:
                    print(f"[{i}/{len(countries)}] {country_name} ({this_iso}): ranking table not found")
                    continue

                country_team_count = 0
                for tr in ranking_table.find_all("tr"):
                    cells = tr.find_all("td")
                    # 0 global rank, 1 club, 2-7 recent results, 8 Elo rating
                    if len(cells) < 9:
                        continue
                    club_cell = cells[1]
                    club_link = club_cell.find("a")
                    team_name = club_link.get_text(" ", strip=True) if club_link else club_cell.get_text(" ", strip=True)
                    elo_text = cells[8].get_text(" ", strip=True)
                    try:
                        elo = float(elo_text)
                        if elo.is_integer():
                            elo = int(elo)
                    except ValueError:
                        continue
                    if not team_name:
                        continue
                    elofootball_teams[find_manual_similar_string(team_name)] = elo
                    country_team_count += 1

                print(f"[{i}/{len(countries)}] {country_name} ({this_iso}): {country_team_count} teams")
        except requests.RequestException as exc:
            print(f"[{i}/{len(countries)}] {country_name} ({this_iso}): ERROR - {exc}")
        except Exception as exc:
            print(f"[{i}/{len(countries)}] {country_name} ({this_iso}): ERROR - {type(exc).__name__}: {exc}")

        if request_delay and len(countries) > 1:
            time.sleep(request_delay)

    result = dict(sorted(elofootball_teams.items(), key=lambda kv: kv[1], reverse=True))
    _elofootball_cache[cache_key] = result
    return dict(result)


def get_model_prediction(
        teams_elos_dict,
        besoccer_teams_elos_dict,
        footballdatabase_teams_elos_dict,
        opta_teams_elos_dict,
        elofootball_teams_elos_dict=None
):
    """
    Predicts missing values in the PRIMARY Elo scale.

    teams_elos_dict:
        Target source:
        - ClubElo when alt_elo=False
        - EloFootball when alt_elo=True
    """
    elofootball_teams_elos_dict = elofootball_teams_elos_dict or {}

    teams_elo = pd.Series(teams_elos_dict, name="teams_elo", dtype=float)
    sources = {
        "besoccer_elo": pd.Series(besoccer_teams_elos_dict, dtype=float),
        "footballdb_elo": pd.Series(footballdatabase_teams_elos_dict, dtype=float),
        "opta_elo": pd.Series(opta_teams_elos_dict, dtype=float),
    }
    if elofootball_teams_elos_dict:
        sources["elofootball_elo"] = pd.Series(elofootball_teams_elos_dict, dtype=float)

    df_elo = pd.concat(
        [teams_elo, *[series.rename(name) for name, series in sources.items()]],
        axis=1
    )
    predictor_columns = list(sources.keys())

    def fit_linear_regression(X, y):
        X_b = np.c_[np.ones((X.shape[0], 1)), X]
        theta = np.linalg.pinv(X_b.T @ X_b) @ X_b.T @ y
        return theta

    def predict(X, theta):
        X_b = np.c_[np.ones((X.shape[0], 1)), X]
        return X_b @ theta

    models = {}
    for n_features in range(len(predictor_columns), 0, -1):
        for columns in combinations(predictor_columns, n_features):
            columns = list(columns)
            mask_train = df_elo[["teams_elo"] + columns].notna().all(axis=1)
            if mask_train.sum() <= len(columns) + 1:
                continue
            X = df_elo.loc[mask_train, columns].values
            y = df_elo.loc[mask_train, "teams_elo"].values
            models[tuple(columns)] = fit_linear_regression(X, y)

    sorted_models = sorted(models.items(), key=lambda item: len(item[0]), reverse=True)
    for columns_tuple, model in sorted_models:
        columns = list(columns_tuple)
        mask_pred = df_elo["teams_elo"].isna() & df_elo[columns].notna().all(axis=1)
        if not mask_pred.any():
            continue
        Xp = df_elo.loc[mask_pred, columns].values
        df_elo.loc[mask_pred, "teams_elo"] = predict(Xp, model)

    return df_elo["teams_elo"].to_dict()


def extract_season_tokens(file_name=None, today=None):
    """
    Returns (league_span, year_single).
    - league_span: 'YYYY-YYYY' for league URLs.
    - year_single: 'YYYY' for single-year tournaments.
    If file_name is None or no years found, uses the current season and current year.
    """
    if not today:
        today = datetime.date.today()
    if not file_name:
        # now = datetime.datetime.now()
        # European season assumption: Jul–Jun
        if today.month >= 7:
            y1, y2 = today.year, today.year + 1
        else:
            y1, y2 = today.year - 1, today.year
        return f"{y1}-{y2}", str(today.year)

    s = file_name.lower()

    # YYYY ... YYYY (e.g., 2025_2026, 2025-2026)
    m = re.search(r'(20\d{2})\D*(20\d{2})', s)
    if m:
        y1, y2 = m.group(1), m.group(2)
        return f"{y1}-{y2}", y2  # use the second year for single-year tourneys

    # YY ... YY (e.g., 24-25)
    m = re.search(r'\b(\d{2})\D*(\d{2})\b', s)
    if m:
        y1, y2 = 2000 + int(m.group(1)), 2000 + int(m.group(2))
        return f"{y1}-{y2}", str(y2)

    # Single YYYY
    m = re.search(r'(20\d{2})', s)
    if m:
        y = int(m.group(1))
        return f"{y}-{y+1}", str(y)

    # Fallback to current season
    # now = datetime.datetime.now()
    if today.month >= 7:
        y1, y2 = today.year, today.year + 1
    else:
        y1, y2 = today.year - 1, today.year
    return f"{y1}-{y2}", str(today.year)


def elos_urls_from_filename(file_name=None, today=None):
    """
    Returns (besoccer_url, footballdatabase_url) inferred from file_name.
    Defaults to Spain Primera + current season if ambiguous or None.
    """
    norm = re.sub(r'[^a-z0-9]+', '-', (file_name or '').lower())

    league_span, year_single = extract_season_tokens(file_name, today)

    is_champions = any(k in norm for k in [
        'champions', 'championsleague', 'champions-league',
    ])
    is_europaleague = any(k in norm for k in [
        'europaleague', 'europa-league',
    ])
    is_conference = any(k in norm for k in [
        'conference', 'conference-league', 'conferenceleague',
    ])
    is_mundialito = any(k in norm for k in [
        "mundialito", "club-world-cup", "clubworldcup", "mundial-clubes", "mundialclubes",
    ])
    is_laliga = any(k in norm for k in [
        'laliga', 'la-liga', 'primera', 'spain', 'espana', 'espa-a', 'españa',
    ])
    is_premier = any(k in norm for k in [
        'premier', 'premier-league', 'premierleague', 'england', 'inglaterra',
    ])
    is_seriea = any(k in norm for k in [
        'seriea', 'serie-a', 'serie', 'italy', 'italia',
    ])
    is_bundesliga = any(k in norm for k in [
        'bundesliga', 'bundes-liga', 'bundes', 'germany', 'alemania',
    ])
    is_ligue1 = any(k in norm for k in [
        'ligue1', 'ligue-1', 'ligue', 'ligueone', 'ligue-one', 'france', 'francia',
    ])
    is_laliga2 = any(k in norm for k in [
        'laliga2', 'la-liga2', 'la-liga-2', 'segunda', 'segunda-division', 'segundadivision', 'hypermotion', 'la-liga-hypermotion', 'laligahypermotion',
    ])

    if is_champions:
        besoccer = 'https://es.besoccer.com/competicion/clasificacion/champions'
        fdb = f'https://footballdatabase.com/league-scores-tables/uefa-champions-league-{league_span}'
        return besoccer, fdb
    if is_europaleague:
        besoccer = 'https://es.besoccer.com/competicion/clasificacion/uefa'
        fdb = f'https://footballdatabase.com/league-scores-tables/uefa-europa-league-{league_span}'
        return besoccer, fdb
    if is_conference:
        besoccer = 'https://es.besoccer.com/competicion/clasificacion/conference-league'
        fdb = f'https://footballdatabase.com/league-scores-tables/uefa-europa-conference-league-{league_span}'
        return besoccer, fdb
    if is_mundialito:
        besoccer = 'https://es.besoccer.com/competicion/clasificacion/mundial_clubes'
        fdb = f'https://footballdatabase.com/league-scores-tables/fifa-club-world-cup-{year_single}'
        return besoccer, fdb

    # Realmente esto nunca se usa porque va a clubelo en estos casos
    if is_laliga:
        besoccer = 'https://es.besoccer.com/competicion/clasificacion/primera'
        fdb = f'https://footballdatabase.com/league-scores-tables/spain-primera-division-{league_span}'
        return besoccer, fdb
    if is_premier:
        besoccer = 'https://es.besoccer.com/competicion/clasificacion/premier'
        fdb = f'https://footballdatabase.com/league-scores-tables/england-premier-league-{league_span}'
        return besoccer, fdb
    if is_seriea:
        besoccer = 'https://es.besoccer.com/competicion/clasificacion/serie_a'
        fdb = f'https://footballdatabase.com/league-scores-tables/italy-serie-a-{league_span}'
        return besoccer, fdb
    if is_bundesliga:
        besoccer = 'https://es.besoccer.com/competicion/clasificacion/bundesliga'
        fdb = f'https://footballdatabase.com/league-scores-tables/germany-bundesliga-{league_span}'
        return besoccer, fdb
    if is_ligue1:
        besoccer = 'https://es.besoccer.com/competicion/clasificacion/ligue_1'
        fdb = f'https://footballdatabase.com/league-scores-tables/france-ligue-1-{league_span}'
        return besoccer, fdb
    if is_laliga2:
        besoccer = 'https://es.besoccer.com/competicion/clasificacion/segunda'
        fdb = f'https://footballdatabase.com/league-scores-tables/spain-segunda-division-{league_span}'
        return besoccer, fdb

    # Default (or explicit Spain/LaLiga)
    # if is_laliga or True:
    besoccer = 'https://es.besoccer.com/competicion/clasificacion/primera'
    fdb = f'https://footballdatabase.com/league-scores-tables/spain-primera-division-{league_span}'
    return besoccer, fdb


def get_teams_elos(is_country=False, country="ESP", extra_teams=False, alt_elo=False, file_name=None):
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
        today = datetime.date.today()
        league_span, _ = extract_season_tokens(file_name, today)

        if alt_elo:
            full_teams_elos_dict = get_elofootball_teams_elos(
                season=league_span,
                country=country
            )
        else:
            today_string = today.strftime('%Y-%m-%d')
            url = f"http://api.clubelo.com/{today_string}"
            teams_elos_df = pd.read_csv(url)

            if country is not None:
                elo_levels = [0, 1, 2]
                norm = re.sub(r'[^a-z0-9]+', '-', (file_name or '').lower())
                is_segunda = any(k in norm for k in [
                    'laliga2', 'la-liga2', 'la-liga-2', 'segunda', 'segunda-division',
                    'segundadivision', 'hypermotion', 'la-liga-hypermotion', 'laligahypermotion',
                ])
                if is_segunda:
                    elo_levels.append(3)
                filtered_teams_elos_df = teams_elos_df[
                    (teams_elos_df['Country'] == country) &
                    (teams_elos_df['Level'].isin(elo_levels))
                ]
            else:
                filtered_teams_elos_df = teams_elos_df[
                    teams_elos_df['Level'].isin([0, 1])
                ]
            full_teams_elos = dict(zip(filtered_teams_elos_df['Club'], filtered_teams_elos_df['Elo']))
            full_teams_elos_dict = {find_manual_similar_string(key): value for key, value in full_teams_elos.items()}

        if extra_teams:
            # file_name can be None or a string like "laliga" or "mundial_clubes_2025"
            besoccer_url, fdb_url = elos_urls_from_filename(file_name, today)

            full_besoccer_teams_elos_dict = get_besoccer_teams_elos(besoccer_url)
            full_footballdatabase_teams_elos_dict = get_footballdatabase_teams_elos(fdb_url)
            full_opta_teams_elos_dict = get_opta_teams_elos()
            # EloFootball is an extra source ONLY when ClubElo is the primary source.
            if not alt_elo:
                full_elofootball_teams_elos_dict = get_elofootball_teams_elos(
                    season=league_span,
                    country=None
                )
            else:
                full_elofootball_teams_elos_dict = {}

            # Model
            partial_teams_elos_dict_complete = get_model_prediction(
                full_teams_elos_dict,
                full_besoccer_teams_elos_dict,
                full_footballdatabase_teams_elos_dict,
                full_opta_teams_elos_dict,
                full_elofootball_teams_elos_dict
            )
            full_teams_elos_dict = partial_teams_elos_dict_complete.copy()

            # Compute the keys present in both source dicts
            common_keys = set(full_besoccer_teams_elos_dict) & set(full_footballdatabase_teams_elos_dict)
            # Filter full_teams_elos_dict in-place (or assign to a new variable)
            full_teams_elos_dict = {k: v for k, v in full_teams_elos_dict.items() if k in common_keys}

    full_teams_elos_dict = dict(
        sorted(full_teams_elos_dict.items(), key=lambda kv: kv[1], reverse=True)
    )

    return full_teams_elos_dict


# # # result = get_teams_elos(country=None, extra_teams=True)
# # result = get_teams_elos(country=None, extra_teams=False)

# result = get_teams_elos_dict(
#     is_country=False,
#     country="ESP",
#     extra_teams=False,
#     write_file=True,
#     file_name="elo_ratings_laliga_data",
#     force_scrape=True
# )
# pprint(result)
#
# items = list(result.items())
# print("{")
# for i, (team, elo) in enumerate(items):
#     print(f'  "{team}": {elo}{"," if i < len(items) - 1 else ""}')
# print("}")
