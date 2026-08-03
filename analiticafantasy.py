import os
import re
import threading
import requests
import urllib3
import json
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from requests.exceptions import ReadTimeout
from urllib3.exceptions import ReadTimeoutError
from http.client import RemoteDisconnected

from useful_functions import read_dict_data, overwrite_dict_data, find_manual_similar_string, \
    read_dict_data_local_only, create_driver  # same as before


class AnaliticaFantasyScraper:
    def __init__(self, competition: str = None):
        self.base_url = "https://www.analiticafantasy.com"
        self.api_base_url = "https://app.analiticafantasy.com"
        # self.base_url = "https://www.analiticafantasy.com/la-liga/alineaciones-probables"
        # # self.base_url = "https://www.analiticafantasy.com/mundial-clubes/alineaciones-probables"
        self.competition = (
            competition
            if competition is not None
            else "la-liga"
        )
        self.session = requests.Session()
        self._fetch_lock = threading.Lock()
        self._next_data_cache = {}
        self.driver = create_driver()
        self.wait = WebDriverWait(self.driver, 15)
        self.small_wait = WebDriverWait(self.driver, 5)
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }
        self.api_headers = {
            **self.headers,
            "Accept": "application/json",
        }

    def fetch_page(self, url):
        self.driver.get(url)

    def fetch_response(self, url):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        with self._fetch_lock:
            response = self.session.get(url, headers=self.headers, verify=False)
        response.raise_for_status()
        return response.text

    def _dedup_preserve_order(self, items):
        seen, out = set(), []
        for x in items:
            if x and x not in seen:
                seen.add(x)
                out.append(x)
        return out

    def get_team_links(self, html=None):
        """
        From the Alineaciones Probables page, find all <a> with href
        that starts with '/equipo/', like '/equipo/real-madrid'.
        Return the full absolute URLs.
        """
        links = []
        if html:
            soup = BeautifulSoup(html, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                if a_tag["href"].startswith("/equipo/"):
                    # Construct the full URL
                    full_url = f"{self.base_url}{a_tag['href']}"
                    links.append(full_url)
            # # WE DO NOT USE THIS BECAUSE IT IS BETTER THE ORDER IT HAS IN THE HTML
            # links = sorted(
            #     list(set(links)),
            #     key=lambda u: int(u.split('/')[4])
            # )
        else:
            els = self.wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, 'a[href^="/equipo/"]')
                )
            )
            for el in els:
                href = el.get_attribute("href") or ""
                # Some drivers resolve to absolute; others keep it relative
                full_url = ""
                # Construct the full URL
                if "/equipo/" in href:
                    if href.startswith("/equipo/"):
                        full_url = f"{self.base_url}{href}"
                    elif href.startswith(f"{self.base_url}"):
                        full_url = href
                if full_url:
                    links.append(full_url)
        return self._dedup_preserve_order(links)

    def get_match_links(self, html=None):
        """
        From the Alineaciones Probables page, find all <a> with href
        that starts with '/partido/', like '/partido/1208772/alineaciones-probables'.
        Return the full absolute URLs.
        """
        links = []
        if html:
            soup = BeautifulSoup(html, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                if a_tag["href"].startswith("/partido/"):
                    # Construct the full URL
                    full_url = f"{self.base_url}{a_tag['href']}"
                    links.append(full_url)
            # # WE DO NOT USE THIS BECAUSE IT IS BETTER THE ORDER IT HAS IN THE HTML
            # links = sorted(
            #     list(set(links)),
            #     key=lambda u: int(u.split('/')[4])
            # )
        else:
            els = self.wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, 'a[href^="/partido/"]')
                )
            )
            for el in els:
                href = el.get_attribute("href") or ""
                # Some drivers resolve to absolute; others keep it relative
                full_url = ""
                # Construct the full URL
                if "/partido/" in href:
                    if href.startswith("/partido/"):
                        full_url = f"{self.base_url}{href}"
                    elif href.startswith(f"{self.base_url}"):
                        full_url = href
                if full_url:
                    links.append(full_url)
        return self._dedup_preserve_order(links)

    def _empty_match_dict(self):
        return {
            "prices": {},
            "positions": {},
            "forms": {},
            "start_probabilities": {},
            "price_trends": {},
        }

    def _fixture_id_from_url(self, url):
        match = re.search(r"/partido/(\d+)", url)
        return int(match.group(1)) if match else None

    def _extract_flight_push_arguments(self, script_text):
        """
        Return the raw argument text of every self.__next_f.push(...) call, tracking
        quotes and escapes so brackets inside strings do not close the argument early.
        """
        marker = "self.__next_f.push("
        arguments = []
        index = 0
        while True:
            start = script_text.find(marker, index)
            if start == -1:
                break

            i = start + len(marker)
            depth, in_string, quote, escaped = 1, False, "", False
            while i < len(script_text) and depth > 0:
                char = script_text[i]
                if in_string:
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == quote:
                        in_string = False
                elif char in "\"'`":
                    in_string, quote = True, char
                elif char in "([{":
                    depth += 1
                elif char in ")]}":
                    depth -= 1
                i += 1

            if depth == 0:
                arguments.append(script_text[start + len(marker):i - 1])
            index = max(i, start + 1)
        return arguments

    def _flight_payload_from_soup(self, soup):
        """
        Every push argument is a JS array like [1, "<chunk>"]; the concatenation of all
        those string chunks is the Flight payload that replaced __NEXT_DATA__.
        """
        chunks = []
        for script_tag in soup.find_all("script"):
            script_text = script_tag.string or script_tag.get_text() or ""
            if "self.__next_f.push(" not in script_text:
                continue
            for argument in self._extract_flight_push_arguments(script_text):
                try:
                    decoded = json.loads(argument)
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
                if isinstance(decoded, list):
                    chunks.extend(item for item in decoded if isinstance(item, str))
        return "".join(chunks)

    def _json_object_at(self, text, start):
        """Return the balanced {...} substring that starts at text[start]."""
        depth, in_string, escaped = 0, False, False
        for i in range(start, len(text)):
            char = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        return None

    def _is_expanded_lineup_block(self, lineup_block):
        """
        Flight data repeats keys as references ("$L63", "$6:2:props:lineupBlock") before
        the real object, so only a block with both sides expanded is usable.
        """
        if not isinstance(lineup_block, dict):
            return False

        home = lineup_block.get("home")
        away = lineup_block.get("away")
        if not isinstance(home, dict) or not isinstance(away, dict):
            return False

        return isinstance(home.get("players"), list) or isinstance(away.get("players"), list)

    def _find_expanded_lineup_block(self, payload):
        # /partido/ pages expose it as "lineupBlock", /equipo/ pages as "lineup"
        for match in re.finditer(r'"(?:lineupBlock|lineup)"\s*:\s*\{', payload):
            raw_object = self._json_object_at(payload, match.end() - 1)
            if not raw_object:
                continue

            try:
                lineup_block = json.loads(raw_object)
            except (json.JSONDecodeError, TypeError, ValueError):
                continue

            if self._is_expanded_lineup_block(lineup_block):
                return lineup_block
        return None

    def _flight_team_names(self, payload, page_html):
        """
        The lineup block only carries teamId, so resolve the names from the neighbouring
        Flight objects and fall back to the /equipo/{slug}-{teamId} links.
        """
        team_names = {}
        for match in re.finditer(r'"teamId"\s*:\s*(\d+)\s*,\s*"teamName"\s*:\s*"([^"]+)"', payload):
            team_names.setdefault(int(match.group(1)), match.group(2))

        for side in ("home", "away"):
            id_match = re.search(r'"%sTeamId"\s*:\s*(\d+)' % side, payload)
            label_match = re.search(r'"%sTeamLabel"\s*:\s*"([^"]+)"' % side, payload)
            if id_match and label_match:
                team_names.setdefault(int(id_match.group(1)), label_match.group(1))

        for text in (payload, page_html):
            for match in re.finditer(r"/equipo/([a-z0-9\-]+?)-(\d+)", text):
                team_names.setdefault(int(match.group(2)), match.group(1).replace("-", " ").title())

        return team_names

    def _fixture_id_from_flight(self, payload):
        match = re.search(r'"fixtureId"\s*:\s*"?(\d+)"?', payload)
        return int(match.group(1)) if match else None

    def _lineups_from_flight(self, payload, page_html):
        """
        Convert the App Router lineup block into the legacy h/a structure expected by
        _build_match_dict_from_lineups, mapping name -> n and chance -> c.
        """
        lineup_block = self._find_expanded_lineup_block(payload)
        if not lineup_block:
            return {}

        team_names = self._flight_team_names(payload, page_html)
        lineups_data = {}
        for side_key, block_key in (("h", "home"), ("a", "away")):
            side_data = lineup_block.get(block_key)
            if not isinstance(side_data, dict):
                continue

            players = side_data.get("players")
            if not isinstance(players, list):
                continue

            # Match pages no longer ship the fantasy market value nor the price
            # variation, so fmv/fs stay None instead of being invented
            lineups_data[side_key] = {
                "n": team_names.get(side_data.get("teamId")),
                "l": [
                    {
                        "n": player.get("name"),
                        "c": player.get("chance"),
                        "fmv": player.get("fmv"),
                        "fs": player.get("fs"),
                    }
                    for player in players if isinstance(player, dict)
                ],
            }
        return lineups_data

    def _next_data_from_flight(self, soup, page_html):
        """
        Rebuild the legacy __NEXT_DATA__ shape out of the Flight payload so the rest of
        the flow (fixture id lookup and lineupsResponse) keeps working unchanged.
        """
        payload = self._flight_payload_from_soup(soup)
        if not payload:
            return None

        page_props = {}
        fixture_id = self._fixture_id_from_flight(payload)
        if fixture_id:
            page_props["fixtureDataResponse"] = {"partido": {"fixtureId": fixture_id}}

        lineups_data = self._lineups_from_flight(payload, page_html)
        if lineups_data:
            page_props["lineupsResponse"] = lineups_data

        if not page_props:
            return None

        return {"props": {"pageProps": page_props}}

    def _get_next_data(self, url):
        if url in self._next_data_cache:
            return self._next_data_cache[url]

        page_html = self.fetch_response(url)
        soup = BeautifulSoup(page_html, "html.parser")
        script_tag = soup.find("script", id="__NEXT_DATA__")
        if not script_tag:
            # The App Router no longer emits __NEXT_DATA__, so rebuild an equivalent
            # payload from the self.__next_f.push(...) Flight chunks instead.
            data_obj = self._next_data_from_flight(soup, page_html)
            self._next_data_cache[url] = data_obj
            return data_obj

        try:
            data_obj = json.loads(script_tag.string)
        except (json.JSONDecodeError, TypeError):
            data_obj = None
        self._next_data_cache[url] = data_obj
        return data_obj

    def _fixture_id_from_data(self, data_obj, page_url):
        fixture_id = self._fixture_id_from_url(page_url)
        if fixture_id:
            return fixture_id
        page_props = data_obj.get("props", {}).get("pageProps", {})
        partido = (page_props.get("fixtureDataResponse") or {}).get("partido") or {}
        return partido.get("fixtureId")

    def _dedupe_lineup_urls_by_fixture(self, urls):
        """
        /equipo/... and /partido/{id}/... often point at the same fixture.
        Keep the first URL per fixtureId to avoid duplicate API calls.
        """
        deduped = []
        seen_urls = set()
        seen_fixtures = set()
        for url in urls:
            if url in seen_urls:
                continue
            seen_urls.add(url)

            data_obj = self._get_next_data(url)
            if not data_obj:
                deduped.append(url)
                continue

            fixture_id = self._fixture_id_from_data(data_obj, url)
            if fixture_id:
                if fixture_id in seen_fixtures:
                    continue
                seen_fixtures.add(fixture_id)
            deduped.append(url)
        return deduped

    def _fetch_lineups_from_api(self, fixture_id):
        if not fixture_id:
            return {}
        api_url = f"{self.api_base_url}/api/alineaciones/partido/{fixture_id}"
        try:
            with self._fetch_lock:
                response = self.session.get(api_url, headers=self.api_headers, verify=False)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, json.JSONDecodeError, ValueError) as e:
            print(f"Lineups API failed for fixture {fixture_id}: {e!r}")
            return {}
        if isinstance(data, dict) and ("h" in data or "a" in data):
            return data
        return {}

    def _lineups_data_from_page(self, data_obj, page_url):
        page_props = data_obj.get("props", {}).get("pageProps", {})

        # SSR payload: legacy __NEXT_DATA__ or the block rebuilt from the Flight chunks
        lineups_data = page_props.get("lineupsResponse")
        if lineups_data:
            return lineups_data
        # .get("lineupsData", {})

        fixture_id = self._fixture_id_from_data(data_obj, page_url)
        return self._fetch_lineups_from_api(fixture_id)

    def _build_match_dict_from_lineups(self, lineups_data):
        match_dict = self._empty_match_dict()

        # Safely extract home/away lineups
        for side_key in ["h", "a"]:
            team_data = lineups_data.get(side_key, {})
            team_name = team_data.get("n", None)
            team_name = find_manual_similar_string(team_name)
            players = team_data.get("l", [])

            for player in players:
                player_name = (player.get("n") or "").strip().title()
                player_name = find_manual_similar_string(player_name)

                chance_int = player.get("c", None)  # e.g. 40
                chance_fraction = chance_int / 100.0 if chance_int is not None else None  # Convert to fraction, e.g. 40 -> 0.40
                # chance_fraction = chance_int / 100.0 if chance_int else None  # Convert to fraction, e.g. 40 -> 0.40
                price = player.get("fmv", None)
                price_trend = player.get("fs", None)
                form = ((price / (price - price_trend)) - 1) * 100 if (price is not None and price_trend is not None and price != price_trend) else None
                # form = ((price / (price - price_trend)) - 1) * 100 if (price and price_trend and price != price_trend) else None
                position = None

                if team_name and player_name:
                    # Insert into dictionary
                    # if team_name not in match_dict:
                    #     match_dict[team_name] = {}
                    match_dict["prices"].setdefault(team_name, {})
                    match_dict["positions"].setdefault(team_name, {})
                    match_dict["forms"].setdefault(team_name, {})
                    match_dict["start_probabilities"].setdefault(team_name, {})
                    match_dict["price_trends"].setdefault(team_name, {})

                    # match_dict[team_name][player_name] = chance_fraction
                    # Sin los ifs salian duplicados como "Lewandowski" y "Robert Lewandowski"
                    if price is not None:
                        match_dict["prices"][team_name][player_name] = price
                    if position is not None:
                        match_dict["positions"][team_name][player_name] = position
                    if form is not None:
                        match_dict["forms"][team_name][player_name] = form
                    if chance_fraction is not None:
                        match_dict["start_probabilities"][team_name][player_name] = chance_fraction
                    if price_trend is not None:
                        match_dict["price_trends"][team_name][player_name] = price_trend

        return match_dict

    def parse_lineup_page(self, match_url):
        """
        Example logic: parse the match page’s JSON or HTML to extract the chance/team/player data.
        The actual parsing details depend on how the data appears in the HTML.
        """
        fixture_id = self._fixture_id_from_url(match_url)

        # For illustration: suppose a <script id="__NEXT_DATA__"> tag contains a JSON
        # structure with the players’ data. We find and parse it:
        data_obj = self._get_next_data(match_url)
        if not data_obj:
            # The lineup API now answers 404, so it is only kept as a legacy fallback
            # for when the page itself yields no usable payload.
            if fixture_id:
                lineups_data = self._fetch_lineups_from_api(fixture_id)

                if lineups_data:
                    return self._build_match_dict_from_lineups(lineups_data)

            return self._empty_match_dict()
        # print(data_obj)

        # Adjust this path depending on your actual JSON structure.
        # Suppose each player entry looks like:
        # {
        #   "team": { "name": "Valencia" },
        #   "information": { "name": "Player X" },
        #   "chance": 88,
        #   ...
        # }

        # Go into data_obj["props"]["pageProps"]["lineupsData"]
        # New pages ship the h/a lineups inside the self.__next_f.push(...) Flight
        # chunks, which _get_next_data already normalised into lineupsResponse.
        lineups_data = self._lineups_data_from_page(data_obj, match_url)
        if not lineups_data:
            return self._empty_match_dict()

        match_dict = self._build_match_dict_from_lineups(lineups_data)

        # home_players = lineups_data.get("homeLineup", {}).get("players", [])
        # away_players = lineups_data.get("awayLineup", {}).get("players", [])
        # all_chance_players = home_players + away_players
        #
        # match_dict = {}
        # for chance_player in all_chance_players:
        #     # Example: chance=40, team->"name"="Valencia", information->"name"="Diakhaby"
        #     team_name = chance_player.get("team", {}).get("name", "").strip().title()
        #     team_name = find_manual_similar_string(team_name)
        #     player_name = chance_player.get("information", {}).get("name", "").strip().title()
        #     player_name = find_manual_similar_string(player_name)
        #     chance_int = chance_player.get("chance", 0)  # e.g. 40
        #
        #     if team_name and player_name:
        #         # Convert to fraction, e.g. 40 -> 0.40
        #         chance_fraction = chance_int / 100.0
        #         # Insert into dictionary
        #         if team_name not in match_dict:
        #             match_dict[team_name] = {}
        #         match_dict[team_name][player_name] = chance_fraction

        return match_dict

    def _merge_match_data(self, match_data, prices_dict, positions_dict, forms_dict, probabilities_dict, price_trends_dict):
        for team_name, players in match_data["prices"].items():
            if team_name not in prices_dict:
                prices_dict[team_name] = {}
            for player_name, data_val in players.items():
                prices_dict[team_name][player_name] = data_val

        for team_name, players in match_data["positions"].items():
            if team_name not in positions_dict:
                positions_dict[team_name] = {}
            for player_name, data_val in players.items():
                positions_dict[team_name][player_name] = data_val

        for team_name, players in match_data["forms"].items():
            if team_name not in forms_dict:
                forms_dict[team_name] = {}
            for player_name, data_val in players.items():
                forms_dict[team_name][player_name] = data_val

        for team_name, players in match_data["start_probabilities"].items():
            if team_name not in probabilities_dict:
                probabilities_dict[team_name] = {}
            for player_name, data_val in players.items():
                probabilities_dict[team_name][player_name] = data_val

        for team_name, players in match_data["price_trends"].items():
            if team_name not in price_trends_dict:
                price_trends_dict[team_name] = {}
            for player_name, data_val in players.items():
                price_trends_dict[team_name][player_name] = data_val

    def _parse_urls_parallel(self, urls, max_workers=8):
        if not urls:
            return []

        workers = min(max_workers, len(urls))

        with ThreadPoolExecutor(max_workers=workers) as executor:
            return list(executor.map(self.parse_lineup_page, urls))

    def scrape(self):
        """
        1) Grab the main page, find all partido links.
        2) For each match link, parse the chance / team / player data.
        3) Merge them all into a single dictionary.
        """
        try:
            self._next_data_cache = {}

            # To get an error if there is no page
            main_html = self.fetch_response(f"{self.base_url}/{self.competition}/alineaciones-probables")
            # main_html = self.fetch_response(self.base_url)
            # self.fetch_page(self.base_url)
            self.fetch_page(f"{self.base_url}/{self.competition}/alineaciones-probables")
            # print(f"{self.base_url}/{self.competition}/alineaciones-probables")

            prices_dict = {}
            positions_dict = {}
            forms_dict = {}
            price_trends_dict = {}
            probabilities_dict = {}

            # team_links = self.get_team_links(main_html)
            try:
                team_links = self.get_team_links()
            except (TimeoutException, ReadTimeout, ReadTimeoutError, RemoteDisconnected):
                print("Fallback team links")
                team_links = self.get_team_links(main_html)

            # match_links = self.get_match_links(main_html)
            try:
                match_links = self.get_match_links()
            except (TimeoutException, ReadTimeout, ReadTimeoutError, RemoteDisconnected):
                print("Fallback match links")
                match_links = self.get_match_links(main_html)

            # match_links first so dedupe keeps /partido/ URLs over /equipo/ for the same fixture
            all_urls = self._dedup_preserve_order(match_links + team_links)
            lineup_urls = self._dedupe_lineup_urls_by_fixture(all_urls)
            skipped = len(all_urls) - len(lineup_urls)

            if skipped:
                print(f"Skipping {skipped} duplicate fixture URLs (team + match overlap)")

            for match_data in self._parse_urls_parallel(lineup_urls):
                # Merge match_data into probabilities_dict
                self._merge_match_data(
                    match_data, prices_dict, positions_dict, forms_dict, probabilities_dict, price_trends_dict
                )

            return prices_dict, positions_dict, forms_dict, probabilities_dict, price_trends_dict
        finally:
            if self.driver:
                self.driver.quit()


def competition_from_filename(file_name: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', file_name.lower())  # normalize to dashed tokens

    mapping = {
        ("mundialito", "club-world-cup", "clubworldcup", "mundial-clubes", "mundialclubes", ): "mundial-clubes",
        ("champions", "championsleague", "champions-league"): "champions",
        ('europaleague', 'europa-league', ): "europa-league",
        ('conference', 'conferenceleague', 'conference-league', ): "conference-league",
        ("eurocopa", "euro", "europa", "europeo", ): "eurocopa",
        ("copaamerica", "copa-america", ): "copa-america",
        ("mundial", "worldcup", "world-cup", ): "mundial",
        ("laliga", "la-liga", ): "la-liga",
        ('premier', 'premier-league', 'premierleague', ): "premier-league",
        ('seriea', 'serie-a', ): "serie-a",
        ('bundesliga', 'bundes-liga', 'bundes', ): "bundesliga",
        ('ligueone', 'ligue-one', 'ligue1', 'ligue-1', 'ligue', ): "ligue-1",
        ("segunda", "segundadivision", "segunda-division", "laliga2", "la-liga-2", "la-liga-hypermotion", "hypermotion", "laligahypermotion", ): "la-liga-2",
    }

    for keys, slug in mapping.items():
        for k in sorted(keys, key=len, reverse=True):  # longest first
            if k in s:
                return slug

    return "la-liga"


def get_analiticafantasy_data(
        price_file_name="analiticafantasy_prices",
        positions_file_name="analiticafantasy_positions",
        forms_file_name="analiticafantasy_forms",
        start_probability_file_name="analiticafantasy_start_probabilities",
        price_trends_file_name="analiticafantasy_price_trends",
        force_scrape=False
):
    # If not forced to scrape, attempt to read from local file
    if not force_scrape:
        prices_data = read_dict_data(price_file_name)
        positions_data = read_dict_data(positions_file_name)
        forms_data = read_dict_data(forms_file_name)
        start_probabilities_data = read_dict_data(start_probability_file_name)
        price_trends_data = read_dict_data(price_trends_file_name)

        if prices_data and positions_data and forms_data and start_probabilities_data and price_trends_data:
            return prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data

    # Otherwise, scrape fresh data
    competition = competition_from_filename(start_probability_file_name)
    scraper = AnaliticaFantasyScraper(competition=competition)
    prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data = scraper.scrape()

    # Save to file for next time
    overwrite_dict_data(prices_data, price_file_name)
    overwrite_dict_data(positions_data, positions_file_name)
    overwrite_dict_data(forms_data, forms_file_name)
    overwrite_dict_data(start_probabilities_data, start_probability_file_name)
    overwrite_dict_data(price_trends_data, price_trends_file_name)

    return prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data


def get_players_prices_dict_analiticafantasy(
        file_name="analiticafantasy_prices",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = AnaliticaFantasyScraper(competition=competition)
    result, _, _, _, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_positions_dict_analiticafantasy(
        file_name="analiticafantasy_positions",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        # if data:
        return data

    competition = competition_from_filename(file_name)
    scraper = AnaliticaFantasyScraper(competition=competition)
    _, result, _, _, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_forms_dict_analiticafantasy(
        file_name="analiticafantasy_forms",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = AnaliticaFantasyScraper(competition=competition)
    _, _, result, _, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_start_probabilities_dict_analiticafantasy(
        file_name="analiticafantasy_start_probabilities",
        force_scrape=False
):
    if not force_scrape:
        # data = read_dict_data(file_name)
        # if data:
        #     return data
        data = read_dict_data_local_only(file_name)
        if data is not None:
            return data
        return {}

    competition = competition_from_filename(file_name)
    scraper = AnaliticaFantasyScraper(competition=competition)
    _, _, _, result, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_price_trends_dict_analiticafantasy(
        file_name="analiticafantasy_price_trends",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = AnaliticaFantasyScraper(competition=competition)
    _, _, _, _, result = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


# # Example usage:
# prices, positions, forms, start_probabilities, price_trends = get_analiticafantasy_data(
#     price_file_name="test_analiticafantasy_laliga_players_prices",
#     positions_file_name="test_analiticafantasy_laliga_players_positions",
#     forms_file_name="test_analiticafantasy_laliga_players_forms",
#     start_probability_file_name="test_analiticafantasy_laliga_players_start_probabilities",
#     price_trends_file_name="test_analiticafantasy_laliga_players_price_trends",
#     force_scrape=True
# )
#
# print("Prices:")
# for team, players in prices.items():
#     print(team, players)
# print("\nPositions:")
# for team, players in positions.items():
#     print(team, players)
# print("\nForms:")
# for team, players in forms.items():
#     print(team, players)
# print("\nStart Probabilities:")
# for team, players in start_probabilities.items():
#     print(team, players)
# print("\nPrice Trends:")
# for team, players in price_trends.items():
#     print(team, players)
