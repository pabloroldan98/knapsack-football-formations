import json
import os
import re
import threading
import time
import requests
import urllib3
from bs4 import BeautifulSoup

from futbolfantasy_analytics import competition_from_filename
from useful_functions import (
    ROOT_DIR,
    find_manual_similar_string,
    overwrite_dict_data,
    read_dict_data,
)


class ForcedMatchesScraper:
    def __init__(self, base_url: str = None, competition: str = None, max_workers: int = 8):
        self.base_url = base_url or "https://www.futbolfantasy.com"
        self.competition = competition if competition is not None else "laliga"
        self.max_workers = max(1, max_workers)
        self._thread_local = threading.local()
        self.request_delay = 1.0
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }

    def _thread_session(self):
        if not getattr(self._thread_local, "session", None):
            self._thread_local.session = requests.Session()
            self._thread_local.last_request_time = 0.0
        return self._thread_local.session

    def fetch_response(self, url, max_retries=5):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        session = self._thread_session()
        last_request_time = getattr(self._thread_local, "last_request_time", 0.0)
        last_response = None
        for attempt in range(max_retries):
            elapsed = time.time() - last_request_time
            if elapsed < self.request_delay:
                time.sleep(self.request_delay - elapsed)
            last_response = session.get(url, headers=self.headers, verify=False)
            last_request_time = time.time()
            self._thread_local.last_request_time = last_request_time
            if last_response.status_code == 429:
                retry_after = last_response.headers.get("Retry-After")
                try:
                    wait_seconds = int(retry_after)
                except (TypeError, ValueError):
                    wait_seconds = 5 * (attempt + 1)
                time.sleep(wait_seconds)
                continue
            last_response.raise_for_status()
            return last_response.text
        if last_response is not None:
            last_response.raise_for_status()
        raise requests.HTTPError(f"Failed to fetch {url}")

    @staticmethod
    def parse_matches_from_soup(soup):
        matches = []
        for container in soup.find_all(class_="partido-container"):
            home_img = container.find(
                "img",
                class_=lambda c: c and "escudo" in c and "local" in c.split(),
            )
            away_img = container.find(
                "img",
                class_=lambda c: c and "escudo" in c and "visitante" in c.split(),
            )
            if not home_img or not away_img:
                continue
            home_name = find_manual_similar_string(home_img.get("alt", "").strip())
            away_name = find_manual_similar_string(away_img.get("alt", "").strip())
            if home_name and away_name:
                matches.append([home_name, away_name])
        return matches

    def _scrape_jornada(self, jornada_number):
        posibles_alineaciones_url = (
            f"{self.base_url}/{self.competition}/posibles-alineaciones"
        )
        url = f"{posibles_alineaciones_url}/{jornada_number}"
        print(f"Fetching jornada {jornada_number}: {url}")
        html = self.fetch_response(url)
        soup = BeautifulSoup(html, "html.parser")
        matches = self.parse_matches_from_soup(soup)
        return jornada_number, matches

    def scrape(self):
        jornadas = {}
        jornada_number = 1

        while True:
            jornada_number, matches = self._scrape_jornada(jornada_number)
            if not matches:
                print(
                    f"No partido-container matchups for jornada {jornada_number}; "
                    f"stopping at {jornada_number - 1} jornadas."
                )
                break
            jornadas[f"jornada_{jornada_number}"] = matches
            print(f"  -> {len(matches)} matches")
            jornada_number += 1

        return jornadas


def _jornada_sort_key(jornada_key):
    match = re.search(r"(\d+)$", jornada_key)
    return int(match.group(1)) if match else 0


def write_forced_matches_txt(jornadas, txt_path):
    lines = []
    for jornada_key in sorted(jornadas.keys(), key=_jornada_sort_key):
        matches = jornadas[jornada_key]
        lines.append(f"{jornada_key} = [")
        for match in matches:
            lines.append(f"    {json.dumps(match, ensure_ascii=False)},")
        lines.append("]")
        lines.append("")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def get_forced_matches_dict(
        file_name="forced_matches_laliga",
        force_scrape=False,
        max_workers=8,
        write_txt=True,
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = ForcedMatchesScraper(competition=competition, max_workers=max_workers)
    jornadas = scraper.scrape()

    if not jornadas:
        print(
            f"No forced matches found for {competition} "
            f"(no partido-container pages); files not written."
        )
        return {}

    overwrite_dict_data(jornadas, file_name)

    if write_txt:
        txt_path = os.path.join(ROOT_DIR, f"{file_name}.txt")
        write_forced_matches_txt(jornadas, txt_path)
        print(f"Wrote {txt_path}")

    return jornadas


# jornadas = get_forced_matches_dict(
#     file_name="test_forced_matches_laliga",
#     force_scrape=True,
# )
# for jornada_key, matches in jornadas.items():
#     print(jornada_key, matches)
