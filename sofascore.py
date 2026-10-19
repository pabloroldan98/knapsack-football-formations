# Source: https://github.com/Urbistondo/sofa-score-scraper/blob/master/player_scraper.py

import atexit
import ctypes
import os
import re
import socket
import subprocess
import tempfile
import threading
import uuid
from ctypes import wintypes
from collections import defaultdict
from urllib.parse import urljoin
from urllib.request import urlopen
import tls_requests
import requests
from bs4 import BeautifulSoup
import urllib3
from http.client import RemoteDisconnected
from requests.exceptions import ReadTimeout
from urllib3.exceptions import ReadTimeoutError
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import copy
from pprint import pprint
import ast
import time
import random
from concurrent.futures import ThreadPoolExecutor

from player import Player
from useful_functions import write_dict_data, read_dict_data, overwrite_dict_data, delete_file, create_driver, \
    run_with_timeout, CustomTimeoutException, CustomConnectionException, CustomMissingException, \
    find_manual_similar_string, get_working_proxy, HEADER_POOL


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root

# Maximum wait time for player data (in seconds)
MAX_WAIT_TIME = 2 * 60  # 2 minutes (120 seconds)



def pick_headers():
    # copy() so you don't accidentally mutate the pool entry later
    return random.choice(HEADER_POOL).copy()


def _sofascore_blocked(response) -> bool:
    """True when SofaScore answered with its bot wall instead of the page or API."""
    if response is None:
        return True
    status = getattr(response, "status_code", 0) or 0
    if status in (0, 401, 403, 429):
        return True
    text = getattr(response, "text", "") or ""
    return (
        "cf-turnstile-response" in text
        or "sofa.captcha.token" in text
        or '"reason": "challenge"' in text
        or '"reason":"challenge"' in text
    )


class _SofaScoreResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text or ""

    def json(self):
        return json.loads(self.text)


class _SofaScoreBrowser:
    """
    Chrome started on a hidden desktop, then attached to.

    Sofascore serves a Turnstile wall to tls_requests, to ChromeDriver and to
    Chrome's own headless mode. A normal Chrome process, kept off the user's
    screen, gets the real pages, and fetch() from that page calls the API.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._driver = None
        self._profile = None

    def get(self, url):
        with self._lock:
            self._ensure_open()
            result = self._fetch(url)
            if not isinstance(result, dict):
                result = {"error": "empty browser response"}
            if result.get("status") in (0, 401, 403, 429):
                self._driver.get(_SOFASCORE_READY_URL)
                self._wait_until_ready()
                result = self._fetch(url)
                if not isinstance(result, dict):
                    result = {"error": "empty browser response"}
            if result.get("error"):
                raise CustomConnectionException(
                    f"Chrome could not fetch {url}: {result['error']}"
                )
            return _SofaScoreResponse(result.get("status") or 0, result.get("body") or "")

    def _fetch(self, url):
        self._driver.set_script_timeout(60)
        return self._driver.execute_async_script(
            """
            const done = arguments[arguments.length - 1];
            const target = arguments[0];
            fetch(target, {credentials: 'include', headers: {Accept: '*/*'}})
              .then(async (response) => done({status: response.status, body: await response.text()}))
              .catch((error) => done({error: String(error)}));
            """,
            url,
        )

    def _ensure_open(self):
        if self._driver is not None:
            return
        existing_port = os.environ.get("SOFASCORE_CHROME_PORT")
        if existing_port:
            port = int(existing_port)
        else:
            chrome = _chrome_executable()
            if not chrome:
                raise CustomConnectionException(
                    "Sofascore blocked the HTTP client and Chrome is not installed"
                )
            self._profile = _chrome_user_data_dir()
            port = _free_local_port()
            desktop = _hidden_desktop_name()
            command = [chrome]
            if not desktop:
                command += ["--headless=new", "--disable-gpu", "--window-size=1920,1080"]
            command += [
                f"--user-data-dir={self._profile}",
                f"--remote-debugging-port={port}",
                "--remote-allow-origins=*",
                "--no-first-run",
                "--no-default-browser-check",
                _SOFASCORE_READY_URL,
            ]
            print("Sofascore blocked the direct request. Starting headless Chrome...")
            _start_chrome(command, desktop)
            _wait_for_debug_port(port)
            _wait_for_sofascore_page(port)
        options = webdriver.ChromeOptions()
        options.debugger_address = f"127.0.0.1:{port}"
        self._driver = webdriver.Chrome(options=options)
        self._driver.set_page_load_timeout(45)
        self._wait_until_ready()
        atexit.register(self.close)

    def _wait_until_ready(self):
        deadline = time.time() + 45
        announced = False
        while time.time() < deadline:
            if self._page_is_ready():
                return
            if "captcha" in (self._driver.current_url or "") and not announced:
                announced = True
            time.sleep(0.5)
        raise CustomConnectionException(
            "Sofascore is showing a verification page and the headless browser cannot continue."
        )

    def _page_is_ready(self):
        try:
            current = self._driver.current_url or ""
            html = self._driver.page_source or ""
        except WebDriverException:
            raise CustomConnectionException("Chrome closed before Sofascore finished loading")
        return "captcha" not in current and "__NEXT_DATA__" in html

    def close(self):
        driver = self._driver
        profile = self._profile
        self._driver = None
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
        if profile:
            _stop_chrome_profile(profile)


_SOFASCORE_READY_URL = "https://www.sofascore.com/"
_sofa_browser = _SofaScoreBrowser()
_prefer_browser = False
_prefer_browser_lock = threading.Lock()
_held_process_handles = []


def sofascore_get(url, headers=None, proxy=None):
    """Fetch a Sofascore URL. The direct client is tried first; if Sofascore
    blocks it, the same URL is requested from a headless Chrome via the API."""
    global _prefer_browser
    with _prefer_browser_lock:
        use_browser = _prefer_browser
    if not use_browser:
        try:
            kwargs = {"headers": headers, "verify": False, "timeout": 25}
            if proxy:
                kwargs["proxy"] = proxy
            response = tls_requests.get(url, **kwargs)
        except Exception:
            response = None
        if not _sofascore_blocked(response):
            return response
        with _prefer_browser_lock:
            _prefer_browser = True
    return _sofa_browser.get(url)


def _hidden_desktop_name():
    """A desktop with no taskbar window, so Chrome stays off the user's screen."""
    if os.name != "nt":
        return None
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.CreateDesktopW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p,
        wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
    ]
    user32.CreateDesktopW.restype = wintypes.HANDLE
    user32.OpenDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    user32.OpenDesktopW.restype = wintypes.HANDLE
    name = "SofaScoreHidden"
    access = 0x10000000
    desk = user32.CreateDesktopW(name, None, None, 0, access, None)
    if not desk:
        desk = user32.OpenDesktopW(name, 0, False, access)
    if not desk:
        return None
    _held_process_handles.append(desk)
    return f"WinSta0\\{name}"


def _chrome_executable():
    candidates = [
        os.environ.get("CHROME_PATH"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def _chrome_user_data_dir():
    """Directory Chrome can write.

    An elevated process creates a folder the normal user cannot write. Chrome
    then exits before it opens the debugging port, so the folder is created
    with the user's unelevated token.
    """
    if os.name != "nt" or not _process_is_elevated():
        return tempfile.mkdtemp(prefix="sofascore-chrome-")
    profile = os.path.join(tempfile.gettempdir(), "sofascore-chrome-" + uuid.uuid4().hex[:12])
    _spawn_medium_process(
        [r"C:\Windows\System32\cmd.exe", "/c", "mkdir", profile],
        wait=True,
    )
    if not os.path.isdir(profile):
        raise CustomConnectionException("Chrome could not prepare its profile directory")
    return profile


def _start_chrome(command, desktop=None):
    """Start Chrome without inheriting Cursor's crashpad pipe or stdio handles.

    From an elevated terminal Chrome relaunches itself and that child never
    opens the debugging port. Starting it on Explorer's unelevated token keeps
    the browser alive and lets Sofascore serve the real pages. On Windows the
    browser is placed on a hidden desktop so no window appears.
    """
    if os.name == "nt" and _process_is_elevated():
        _spawn_medium_process(command, wait=False, desktop=desktop)
        return
    env = os.environ.copy()
    env.pop("CHROME_CRASHPAD_PIPE_NAME", None)
    kwargs = {
        "env": env,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        if desktop:
            startup = subprocess.STARTUPINFO()
            startup.lpDesktop = desktop
            kwargs["startupinfo"] = startup
    subprocess.Popen(command, **kwargs)


def _process_is_elevated():
    if os.name != "nt":
        return False
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    advapi32.OpenProcessToken.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)
    ]
    advapi32.OpenProcessToken.restype = wintypes.BOOL
    advapi32.GetTokenInformation.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)
    ]
    advapi32.GetTokenInformation.restype = wintypes.BOOL

    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
        return False

    class TOKEN_ELEVATION(ctypes.Structure):
        _fields_ = [("TokenIsElevated", wintypes.DWORD)]

    elevation = TOKEN_ELEVATION()
    returned = wintypes.DWORD()
    ok = advapi32.GetTokenInformation(
        token, 20, ctypes.byref(elevation), ctypes.sizeof(elevation), ctypes.byref(returned)
    )
    kernel32.CloseHandle(token)
    return bool(ok and elevation.TokenIsElevated)


def _spawn_medium_process(args, wait, desktop=None):
    """Run a process with Explorer's medium-integrity token."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)

    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("lpReserved", wintypes.LPWSTR),
            ("lpDesktop", wintypes.LPWSTR),
            ("lpTitle", wintypes.LPWSTR),
            ("dwX", wintypes.DWORD),
            ("dwY", wintypes.DWORD),
            ("dwXSize", wintypes.DWORD),
            ("dwYSize", wintypes.DWORD),
            ("dwXCountChars", wintypes.DWORD),
            ("dwYCountChars", wintypes.DWORD),
            ("dwFillAttribute", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("wShowWindow", wintypes.WORD),
            ("cbReserved2", wintypes.WORD),
            ("lpReserved2", ctypes.POINTER(wintypes.BYTE)),
            ("hStdInput", wintypes.HANDLE),
            ("hStdOutput", wintypes.HANDLE),
            ("hStdError", wintypes.HANDLE),
        ]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("hProcess", wintypes.HANDLE),
            ("hThread", wintypes.HANDLE),
            ("dwProcessId", wintypes.DWORD),
            ("dwThreadId", wintypes.DWORD),
        ]

    advapi32.CreateProcessWithTokenW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.LPCWSTR,
        ctypes.POINTER(STARTUPINFOW),
        ctypes.POINTER(PROCESS_INFORMATION),
    ]
    advapi32.CreateProcessWithTokenW.restype = wintypes.BOOL

    hwnd = user32.GetShellWindow()
    explorer_pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(explorer_pid))
    explorer = kernel32.OpenProcess(0x1000, False, explorer_pid.value)
    if not explorer:
        raise CustomConnectionException("Chrome could not be opened from the normal user session")
    shell_token = wintypes.HANDLE()
    primary = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(explorer, 0x000A, ctypes.byref(shell_token)):
        kernel32.CloseHandle(explorer)
        raise CustomConnectionException("Chrome could not be opened from the normal user session")
    if not advapi32.DuplicateTokenEx(shell_token, 0x018B, None, 2, 1, ctypes.byref(primary)):
        kernel32.CloseHandle(shell_token)
        kernel32.CloseHandle(explorer)
        raise CustomConnectionException("Chrome could not be opened from the normal user session")
    startup = STARTUPINFOW()
    startup.cb = ctypes.sizeof(STARTUPINFOW)
    if desktop:
        startup.lpDesktop = desktop
    info = PROCESS_INFORMATION()
    created = advapi32.CreateProcessWithTokenW(
        primary,
        0,
        args[0],
        ctypes.create_unicode_buffer(_windows_command_line(args)),
        0,
        None,
        None,
        ctypes.byref(startup),
        ctypes.byref(info),
    )
    if not created:
        kernel32.CloseHandle(primary)
        kernel32.CloseHandle(shell_token)
        kernel32.CloseHandle(explorer)
        raise CustomConnectionException(
            f"Chrome could not be opened ({ctypes.get_last_error()})"
        )
    if wait:
        kernel32.WaitForSingleObject(info.hProcess, 15000)
        kernel32.CloseHandle(info.hThread)
        kernel32.CloseHandle(info.hProcess)
        kernel32.CloseHandle(primary)
        kernel32.CloseHandle(shell_token)
        kernel32.CloseHandle(explorer)
        return
    # Chrome is still starting. Closing the token now stops the debugging
    # port from opening, so these handles stay open for the rest of this process.
    _held_process_handles.extend((info.hThread, info.hProcess, primary, shell_token, explorer))


def _windows_command_line(args):
    def quote(arg):
        if any(ch in arg for ch in ' \t"'):
            return '"' + arg.replace('"', '\\"') + '"'
        return arg

    return " ".join(quote(arg) for arg in args)


def _free_local_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_debug_port(port, timeout=25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(0.25)
    raise CustomConnectionException("Chrome did not open its debugging port")


def _wait_for_sofascore_page(port, timeout=30):
    """Attach only after the real homepage is up.

    A fresh window briefly reports sofascore.com and then, if Selenium connects
    during that moment, Sofascore replaces it with the verification page.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as resp:
                pages = json.loads(resp.read().decode("utf-8", "replace"))
            for page in pages:
                url = page.get("url") or ""
                title = page.get("title") or ""
                if (
                    page.get("type") == "page"
                    and "sofascore.com" in url
                    and "captcha" not in url
                    and " | Sofascore" in title
                ):
                    return
        except Exception:
            pass
        time.sleep(0.5)


def _stop_chrome_profile(profile):
    marker = os.path.basename(profile)
    if os.name != "nt" or not marker:
        return
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
                f"Where-Object {{ $_.CommandLine -like '*{marker}*' }} | "
                "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
            ),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def _fetch_team_player_paths(team_name, team_url, use_buffer=False):
    print('Extracting %s player links...' % team_name)
    player_paths_list = []
    attempt_retries = 3
    while attempt_retries > 0:
        headers = pick_headers()
        player_paths_list = []
        team_id = team_url.split("#")[0].rstrip("/").split("/")[-1]
        response = None
        if team_id.isdigit():
            api_url = f"https://www.sofascore.com/api/v1/team/{team_id}/players"
            api_response = sofascore_get(api_url, headers=headers)
            try:
                data = api_response.json() if api_response is not None and api_response.status_code == 200 else {}
                for item in data.get("players", []):
                    p = item.get("player", {})
                    slug = p.get("slug")
                    pid = p.get("id")
                    if slug and pid:
                        player_paths_list.append(
                            f"https://www.sofascore.com/football/player/{slug}/{pid}"
                        )
            except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
                pass

        if not player_paths_list:
            response = sofascore_get(team_url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser") if response is not None else BeautifulSoup("", "html.parser")

        script = soup.find("script", id="__NEXT_DATA__")
        if script and script.string:
            try:
                data = json.loads(script.string)
                page_props = data["props"]["pageProps"]
                players_list = page_props.get("players", {}).get("players")
                if not players_list:
                    players_list = page_props.get("initialProps", {}).get("players", {}).get("players", [])
                for item in players_list:
                    p = item.get("player", {})
                    slug = p.get("slug")
                    pid = p.get("id")
                    if slug and pid:
                        player_paths_list.append(
                            f"https://www.sofascore.com/football/player/{slug}/{pid}"
                        )
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        if not player_paths_list:
            for a_tag in soup.find_all("a", href=True):
                href_val = a_tag["href"]
                if "/player/" in href_val:
                    full_url = (
                        href_val if href_val.startswith("http")
                        else "https://www.sofascore.com" + href_val
                    )
                    player_paths_list.append(full_url)

        player_paths_list = sorted(list(set(player_paths_list)))
        if player_paths_list:
            break
        attempt_retries -= 1
        if attempt_retries <= 0:
            break
        print(f"No links for {team_name}, retrying ({attempt_retries} left)...")
        if use_buffer:
            time.sleep(2)
    print(player_paths_list)
    return team_name, player_paths_list


def _scrape_one_player(player_url):
    print('Extracting player data from: %s ...' % player_url)
    use_selenium = False
    use_proxies = False
    player_name = ""
    timeout_retries = 3

    while timeout_retries > 0:
        def scrape_players_name_task(use_buffer=False):
            if use_buffer:
                time.sleep(0.25)
            try:
                return get_player_name(player_url, use_proxies=use_proxies)
            except Exception:
                pass
            if use_selenium:
                try:
                    return get_player_name_selenium(player_url)
                except Exception:
                    pass
            raise CustomMissingException("No name was fetched")

        try:
            player_name = run_with_timeout(MAX_WAIT_TIME, scrape_players_name_task)
            print(player_name)
            break
        except (CustomMissingException, CustomTimeoutException, CustomConnectionException, ReadTimeout, ReadTimeoutError, RemoteDisconnected) as e:
            timeout_retries -= 1
            if timeout_retries <= 0:
                print("Failed to fetch name after several attempts.")
                break
            if isinstance(e, CustomMissingException):
                sleep_s = 0
                reason = "element not found"
                extra = ""
            elif isinstance(e, CustomTimeoutException):
                sleep_s = 1
                reason = "timeout"
                extra = f"(waited {MAX_WAIT_TIME}s)"
            else:
                sleep_s = 2
                reason = "connection"
                extra = f"({type(e).__name__})"
            print(
                f"Retrying to fetch sofascore player name ({player_url}) due to {reason} error {extra} "
                f"({timeout_retries} retry left, waiting {sleep_s}s before next retry)"
            )
            time.sleep(sleep_s)

    if not player_name:
        return None

    average_rating = float(6.0)
    timeout_retries = 3
    while timeout_retries > 0:
        def scrape_players_rating_task(use_buffer=False):
            if use_buffer:
                time.sleep(0.25)
            try:
                return float(get_player_average_rating(player_url, use_proxies=use_proxies))
            except Exception:
                pass
            try:
                return float(get_player_last_year_rating(player_url, use_proxies=use_proxies))
            except Exception:
                pass
            return average_rating

        try:
            average_rating = run_with_timeout(MAX_WAIT_TIME, scrape_players_rating_task)
            print(average_rating)
            break
        except (CustomMissingException, CustomTimeoutException, CustomConnectionException, ReadTimeout, ReadTimeoutError, RemoteDisconnected) as e:
            timeout_retries -= 1
            if timeout_retries <= 0:
                print("Failed to fetch rating after several attempts.")
                break
            if isinstance(e, CustomMissingException):
                sleep_s = 0
                reason = "element not found"
                extra = ""
            elif isinstance(e, CustomTimeoutException):
                sleep_s = 1
                reason = "timeout"
                extra = f"(waited {MAX_WAIT_TIME}s)"
            else:
                sleep_s = 2
                reason = "connection"
                extra = f"({type(e).__name__})"
            print(
                f"Retrying to fetch sofascore player rating ({player_url}) due to {reason} error {extra} "
                f"({timeout_retries} retry left, waiting {sleep_s}s before next retry)"
            )
            time.sleep(sleep_s)

    player_name = find_manual_similar_string(player_name)
    average_rating = average_rating if average_rating != 0 else float(6.0)
    return player_name, average_rating


def _scrape_team_ratings(team_name, player_paths, max_workers):
    players_ratings = {}
    player_workers = min(max_workers, len(player_paths) or 1)
    print(
        f"Fetching ratings for {team_name}: {len(player_paths)} players "
        f"({player_workers} workers)..."
    )
    with ThreadPoolExecutor(max_workers=player_workers) as executor:
        for result in executor.map(_scrape_one_player, player_paths):
            if result:
                player_name, average_rating = result
                players_ratings[player_name] = average_rating
    return team_name, players_ratings


def get_players_ratings_list(
        write_file=True,
        file_name="sofascore_players_ratings",
        team_links=None,
        backup_files=True,
        force_scrape=False,
        select_half: int | None = None,
        max_workers=8,
):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    teams_data_dict = get_players_data(
        write_file, file_name, team_links,
        backup_files=backup_files, force_scrape=force_scrape,
        select_half=select_half, max_workers=max_workers,
    )
    players_ratings_list = []
    for team_name, players_ratings in teams_data_dict.items():
        if isinstance(players_ratings, str):
            players_ratings_dict = eval(players_ratings)
        else:
            players_ratings_dict = copy.deepcopy(players_ratings)
        for player_name, rating in players_ratings_dict.items():
            new_player = Player(player_name, sofascore_rating=rating, team=team_name)
            players_ratings_list.append(new_player)
    return players_ratings_list


def fix_team_data(team_data):
    for key, value in team_data.items():
        name, url = value
        if not name:
            # Extract the second to last part of the URL path, replace "-" with " ", and capitalize each word
            name = url.split("/")[-2].replace("-", " ").title().strip()
            team_data[key] = [name, url]
    return team_data


def _current_sofascore_season(ut_id):
    """Season Sofascore lists first. That is the edition currently in progress."""
    response = sofascore_get(
        f"https://www.sofascore.com/api/v1/unique-tournament/{ut_id}/seasons"
    )
    if response is None or response.status_code != 200:
        return None
    seasons = response.json().get("seasons") or []
    return seasons[0] if seasons else None


def _standings_team_ids(ut_id, season_id, headers):
    """Team ids that appear in the season's total standings."""
    standings_url = (
        f"https://www.sofascore.com/api/v1/unique-tournament/{ut_id}"
        f"/season/{season_id}/standings/total"
    )
    response = sofascore_get(standings_url, headers=headers)
    if response is None or response.status_code != 200:
        return set()
    team_ids = set()
    for table in response.json().get("standings") or []:
        for row in table.get("rows") or []:
            team = row.get("team") or {}
            team_id = team.get("id")
            if team_id is not None:
                team_ids.add(team_id)
    return team_ids


def _filter_teams_by_standings(teams, ut_id, season_id, headers):
    team_ids = _standings_team_ids(ut_id, season_id, headers)
    if not team_ids:
        return teams
    return [team for team in teams if team.get("id") in team_ids]


def get_team_links_from_league(league_url):
    # We do a direct HTTP GET
    headers = pick_headers()
    all_teams = []
    # An explicit #id: selects that season. Without it, use the current one.
    season_match = re.search(r"#id:(\d+)", league_url)
    season_id = season_match.group(1) if season_match else None
    ut_id = league_url.split("#")[0].rstrip("/").split("/")[-1]
    if not season_id and ut_id.isdigit():
        season = _current_sofascore_season(ut_id)
        if season and season.get("id"):
            season_id = str(season["id"])
            label = season.get("name") or season.get("year")
            if label:
                print(f"Season: {label}")
    if season_id and ut_id.isdigit():
        api_url = (
            f"https://www.sofascore.com/api/v1/unique-tournament/{ut_id}"
            f"/season/{season_id}/teams"
        )
        api_response = sofascore_get(api_url, headers=headers)
        if api_response is not None and api_response.status_code == 200:
            all_teams = api_response.json().get("teams", [])
            all_teams = _filter_teams_by_standings(all_teams, ut_id, season_id, headers)

    response = None
    if not all_teams:
        response = sofascore_get(league_url, headers=headers)
    html = response.text if response is not None else ""

    soup = BeautifulSoup(html, "html.parser")

    # General
    script = soup.find("script", id="__NEXT_DATA__")
    if script and script.string:
        data = json.loads(script.string)

        def find_teams(obj, out):
            if isinstance(obj, dict):
                if "team" in obj:
                    t = obj["team"]
                    if all(k in t for k in ("name", "slug", "id")):
                        out.append(t)
                for v in obj.values():
                    find_teams(v, out)
            elif isinstance(obj, list):
                for item in obj:
                    find_teams(item, out)

        find_teams(data, all_teams)

    if not all_teams:
        raise CustomConnectionException(f"No teams found for {league_url}")

    team_data = {}
    base = "https://www.sofascore.com/team/football"
    seen_ids = set()
    idx = 0
    for t in all_teams:
        tid = t["id"]
        if tid in seen_ids:
            continue
        seen_ids.add(tid)
        url = urljoin(base + "/", f"{t['slug']}/{tid}")
        team_data[str(idx)] = [t["name"], url]
        idx += 1

    return team_data


def get_player_average_rating_selenium_short(player_url):
    print("Fallback rating")
    driver = create_driver(keep_alive=False)
    wait = WebDriverWait(driver, 15)  # Reusable WebDriverWait
    driver.get(player_url)
    average_rating = float(wait.until(EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Average Sofascore Rating')]/..//..//span[@role='meter']"))).get_attribute('aria-valuenow'))
    average_rating = round(average_rating * 0.95, 4)
    driver.quit()
    return average_rating


def normalize_year(year_raw):
    """
    Normalizes year strings like:
    - "2025" → "2025"
    - "24/25" → "2025"
    - "22/23" → "2023"
    """
    if not year_raw:
        return None
    if "/" in year_raw:
        last_part = year_raw.split("/")[-1]
        return f"20{last_part}"
    return year_raw


def get_player_last_year_rating(player_url, headers=None, use_proxies=False):
    """
    Given a SofaScore player URL like:
        https://www.sofascore.com/player/unai-marrero/1094782
        get https://www.sofascore.com/api/v1/player/1094782/statistics/match-type/overall
    This function:
      1) Extracts the player_id (e.g. 1094782)
      2) Fetches the player's 'statistics/seasons' data
      3) Takes the totalRating and countRating of each seasson, does the sum and gets the average
      4) Return latest year
    """
    print("Fallback rating")
    # time.sleep(5)

    # 1) Extract the player ID from the URL via regex or string split
    match = re.search(r"/player/[^/]+/(\d+)$", player_url)
    if not match:
        print(f"Could not extract player_id from URL: {player_url}")
        return None
    player_id = match.group(1)

    # 2) Fetch seasons info: /api/v1/player/{player_id}/statistics/match-type/overall
    seasons_url = f"https://www.sofascore.com/api/v1/player/{player_id}/statistics/match-type/overall"
    if not headers:
        headers = pick_headers()
    proxy = get_working_proxy(player_url) if use_proxies else None
    resp = sofascore_get(seasons_url, headers=headers, proxy=proxy)
    # if resp.status_code == 403: # If blocked by too many calls
    #     print(f"Status: {resp.status_code} , trying with no headers")
    #     time.sleep(30)
    #     return get_player_last_year_rating(player_url, headers=None)
    if resp.status_code != 200:
        # Raise your custom exception if HTTP status is not 200
        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {seasons_url}")
    data = resp.json()

    # Step 1: Safely get seasons
    seasons = data.get("seasons", [])

    # Step 2: Aggregate totalRating and countRating per year
    ratings_by_year = defaultdict(lambda: {"total": 0.0, "count": 0})

    for season in seasons:
        statistics = season.get("statistics", {})
        year_raw = season.get("year")
        year = normalize_year(year_raw)

        total_rating = statistics.get("totalRating")
        count_rating = statistics.get("countRating")

        if total_rating is not None and count_rating:
            ratings_by_year[year]["total"] += total_rating
            ratings_by_year[year]["count"] += count_rating

    # Step 3: Compute average per year
    average_ratings = {
        year: vals["total"] / vals["count"]
        for year, vals in ratings_by_year.items()
        if vals["count"] > 0
    }

    # Step 4: Return latest year with its average
    if average_ratings:
        latest_year = sorted(average_ratings.keys(), reverse=True)[0]
        rating = average_ratings[latest_year]
        # print(f"Latest year: {latest_year} | Average Rating: {rating:.2f}")
    else:
        print("No valid rating data found.")

    average_rating = float(rating)
    average_rating = round(average_rating * 0.95, 4)
    return average_rating


def get_player_last_tournament_rating_selenium(player_url):
    """
    Given a SofaScore player URL like:
        https://www.sofascore.com/player/unai-marrero/1094782
    This function:
      1) Extracts the player_id (e.g. 1094782)
      2) Fetches the player's 'statistics/seasons' data
      3) Takes the FIRST uniqueTournament and its FIRST season
      4) Calls the 'statistics/overall' endpoint for that uniqueTournament/season
      5) Returns the 'statistics'->'rating' float or None if not found
    """
    print("Fallback rating")
    # time.sleep(5)

    # 1) Extract the player ID from the URL via regex or string split
    match = re.search(r"/player/[^/]+/(\d+)$", player_url)
    if not match:
        print(f"Could not extract player_id from URL: {player_url}")
        return None
    player_id = match.group(1)

    # 2) Fetch seasons info: /api/v1/player/{player_id}/statistics/seasons
    seasons_url = f"https://www.sofascore.com/api/v1/player/{player_id}/statistics/seasons"
    headers = pick_headers()
    resp = sofascore_get(seasons_url, headers=headers)
    if resp.status_code != 200:
        # Raise your custom exception if HTTP status is not 200
        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {seasons_url}")
    data = resp.json()

    # 3) Parse to find the FIRST uniqueTournament and FIRST season ID
    unique_tournament_seasons = data.get("uniqueTournamentSeasons", [])
    if not unique_tournament_seasons:
        print("No uniqueTournamentSeasons found in the response.")
        return None

    first_uts = unique_tournament_seasons[0]
    unique_tournament = first_uts.get("uniqueTournament", {})
    unique_tournament_id = unique_tournament.get("id")

    seasons_list = first_uts.get("seasons", [])
    if not seasons_list:
        print("No seasons found for the first uniqueTournament.")
        return None

    first_season_id = seasons_list[0].get("id")

    if not unique_tournament_id or not first_season_id:
        print("Missing uniqueTournamentId or seasonId.")
        return None

    # 4) Fetch the statistics/overall data:
    stats_url = (f"https://www.sofascore.com/api/v1/player/{player_id}"
                 f"/unique-tournament/{unique_tournament_id}"
                 f"/season/{first_season_id}/statistics/overall")
    resp_stats = sofascore_get(stats_url, headers=headers)
    if resp_stats.status_code != 200:
        # Raise your custom exception if HTTP status is not 200
        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {stats_url}")

    stats_data = resp_stats.json()
    statistics = stats_data.get("statistics", {})
    rating = statistics.get("rating")

    average_rating = float(rating)
    average_rating = round(average_rating * 0.95, 4)
    return average_rating


def get_player_average_rating(player_url, headers=None, use_proxies=False):
    """
    Given a SofaScore player URL like:
        https://www.sofascore.com/player/unai-marrero/1094782
        get https://www.sofascore.com/api/v1/player/1094782/last-year-summary
    This function:
      1) Extracts the player_id (e.g. 1094782)
      2) Fetches the player's 'last-year-summary' data
      3) Calculates average rating based on event type summary
    """
    # 1) Extract the player ID from the URL via regex or string split
    match = re.search(r"/player/[^/]+/(\d+)$", player_url)
    if not match:
        print(f"Could not extract player_id from URL: {player_url}")
        return None
    player_id = match.group(1)

    # 2) Fetch seasons info: /api/v1/player/{player_id}/last-year-summary
    seasons_url = f"https://www.sofascore.com/api/v1/player/{player_id}/last-year-summary"
    if not headers:
        headers = pick_headers()
    proxy = get_working_proxy(player_url) if use_proxies else None
    resp = sofascore_get(seasons_url, headers=headers, proxy=proxy)
    # if resp.status_code == 403: # If blocked by too many calls
    #     print(f"Status: {resp.status_code} , trying with no headers")
    #     time.sleep(30)
    #     return get_player_average_rating(player_url, headers=None)
    if resp.status_code != 200:
        # Raise your custom exception if HTTP status is not 200
        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {seasons_url}")
    data = resp.json()

    # Safely get the list of events from the summary
    summary = data.get("summary", [])

    # Extract float values where type == "event", using safe .get() access
    event_values = [
        float(item.get("value"))
        for item in summary
        if item.get("type") == "event" and item.get("value") is not None
    ]

    # Calculate average safely
    rating = sum(event_values) / len(event_values) if event_values else None

    average_rating = float(rating)
    average_rating = round(average_rating, 2)
    return average_rating


def get_player_average_rating_selenium(player_url):
    """
    Given a SofaScore player URL like:
        https://www.sofascore.com/player/unai-marrero/1094782
    This function:
      1) Try to find the <span role="meter" aria-valuenow="..."> (Summary last 12 months).
    """
    headers = pick_headers()
    resp = sofascore_get(player_url, headers=headers)
    if resp.status_code != 200:
        # Raise your custom exception if HTTP status is not 200
        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {player_url}")

    sp = BeautifulSoup(resp.text, "html.parser")

    # Attempt #1: "Summary (last 12 months)"
    rating_span = sp.find("span", {"role": "meter"})
    if rating_span and rating_span.has_attr("aria-valuenow"):
        average_rating = float(rating_span["aria-valuenow"])
        return average_rating

    return None


def get_player_name(player_url, headers=None, use_proxies=False):
    """
    Given a SofaScore player URL like:
        https://www.sofascore.com/player/unai-marrero/1094782
        get https://www.sofascore.com/api/v1/player/1094782
    This function:
      1) Extracts the player_id (e.g. 1094782)
      2) Fetches the player's 'name' data
    """
    # 1) Extract the player ID from the URL via regex or string split
    match = re.search(r"/player/[^/]+/(\d+)$", player_url)
    if not match:
        print(f"Could not extract player_id from URL: {player_url}")
        return None
    player_id = match.group(1)

    # 2) Fetch seasons info: /api/v1/player/{player_id}/last-year-summary
    player_api_url = f"https://www.sofascore.com/api/v1/player/{player_id}"
    if not headers:
        headers = pick_headers()
    proxy = get_working_proxy(player_url) if use_proxies else None
    resp = sofascore_get(player_api_url, headers=headers, proxy=proxy)
    # if resp.status_code == 403: # If blocked by too many calls
    #     print(f"Status: {resp.status_code} , trying with no headers")
    #     time.sleep(30)
    #     return get_player_average_rating(player_api_url, headers=None)
    if resp.status_code != 200:
        # print(resp.text)
        # Raise your custom exception if HTTP status is not 200
        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {player_api_url}")
    data = resp.json()

    # Safely get the player name (returns None if not found)
    player_name = (data.get("player") or {}).get("name")

    if not player_name:
        # Raise a CustomMissingException exception if no name was fetched
        raise CustomMissingException("No name was fetched")

    return player_name


def get_player_name_selenium(player_url, headers=None):
    """
    Just tries to find an <h2> (like your Selenium code: "(//h2)[1]")
    """
    print("Fallback name")
    if not headers:
        headers = pick_headers()
    resp = sofascore_get(player_url, headers=headers)
    if resp.status_code != 200:
        # print(resp.text)
        # Raise your custom exception if HTTP status is not 200
        raise CustomConnectionException(f"HTTP {resp.status_code} when fetching {player_url}")

    sp = BeautifulSoup(resp.text, "html.parser")
    h2_tag = sp.find("h2")
    if h2_tag:
        try:
            player_name = h2_tag.get_text(strip=True)
            return player_name
        except:
            pass

    # Raise a CustomMissingException exception if no name was fetched
    raise CustomMissingException("No name was fetched")


def competition_from_filename(file_name: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', file_name.lower())  # normalize to dashed tokens

    mapping = {
        ("mundialito", "club-world-cup", "clubworldcup", "mundial-clubes", "mundialclubes", ): "world/club-world-championship/357",
        ("champions", "championsleague", "champions-league"): "europe/uefa-champions-league/7",
        ('europaleague', 'europa-league', ): "europe/uefa-europa-league/679",
        ('conference', 'conferenceleague', 'conference-league', ): "europe/uefa-europa-conference-league/17015",
        ("eurocopa", "euro", "europa", "europeo", ): "europe/european-championship/1",
        ("copaamerica", "copa-america", ): "south-america/copa-america/133",
        ("mundial", "worldcup", "world-cup", ): "world/world-championship/16",
        ("laliga", "la-liga", ): "spain/laliga/8",
        ('premier', 'premier-league', 'premierleague', ): "england/premier-league/17",
        ('seriea', 'serie-a', ): "italy/serie-a/23",
        ('bundesliga', 'bundes-liga', 'bundes', ): "germany/bundesliga/35",
        ('ligueone', 'ligue-one', 'ligue1', 'ligue-1', 'ligue', ): "france/ligue-1/34",
        ("segunda", "segundadivision", "segunda-division", "laliga2", "la-liga-2", "la-liga-hypermotion", "hypermotion", "laligahypermotion", ): "spain/laliga-2/54",
    }
    for keys, slug in mapping.items():
        for k in sorted(keys, key=len, reverse=True):  # longest first
            if k in s:
                return slug
    return "spain/laliga/8"


def get_players_data(
        write_file=True,
        file_name="sofascore_players_ratings",
        team_links=None,
        backup_files=True,
        force_scrape=False,
        select_half: int | None = None,
        max_workers=8,
):
    max_workers = max(1, max_workers)
    existing_data = {}

    # Normal caching behavior only when scraping everything (select_half=None)
    if select_half is None and not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    # If we are scraping halves, we may want to merge with existing file
    if select_half in (1, 2):
        data = read_dict_data(file_name)
        if isinstance(data, dict):
            existing_data = data

    if not team_links:
        competition = competition_from_filename(file_name)
        competition_url = f"https://www.sofascore.com/tournament/football/{competition}"
        team_links = get_team_links_from_league(competition_url)
        # team_links = get_team_links_from_league(
        #     # "https://www.sofascore.com/tournament/football/world/club-world-championship/357#id:69619",
        #     "https://www.sofascore.com/tournament/football/spain/laliga/8#id:77559",
        #     # "https://www.sofascore.com/tournament/football/spain/laliga/8#52376",
        #     # "https://www.sofascore.com/tournament/football/europe/european-championship/1#id:56953",
        #     # "https://www.sofascore.com/tournament/football/south-america/copa-america/133#id:57114",
        # )
    # team_links = {
    #     '0': ['León', 'https://www.sofascore.com/team/football/club-leon/36534'],
    # }
    # If we're doing half selection, split deterministically (based on the idx)
    if select_half in (1, 2):
        items = sorted(team_links.items(), key=lambda kv: int(kv[0]))  # sort by numeric idx

        mid = len(items) // 2
        selected_items = items[:mid] if select_half == 1 else items[mid:]

        team_links = dict(selected_items)
        print(f"[select_half={select_half}] Teams selected: {len(team_links)} / {len(items)}")

    print()
    team_items = [
        (find_manual_similar_string(value[0]), value[1])
        for value in team_links.values()
    ]
    team_players_paths = {}
    team_workers = min(max_workers, len(team_items) or 1)
    print(f"Fetching player links for {len(team_items)} teams ({team_workers} workers)...")
    with ThreadPoolExecutor(max_workers=team_workers) as executor:
        for team_name, paths in executor.map(
            lambda item: _fetch_team_player_paths(item[0], item[1]),
            team_items,
        ):
            team_players_paths[team_name] = paths

    teams_with_players_ratings = dict()
    j = 0

    if backup_files:
        for team_name, player_paths in team_players_paths.items():
            team_name, players_ratings = _scrape_team_ratings(
                team_name, player_paths, max_workers,
            )
            teams_with_players_ratings[team_name] = players_ratings
            overwrite_dict_data(
                teams_with_players_ratings, file_name + "_" + str(j), ignore_valid_file=True,
            )
            j += 1
    else:
        team_scrape_items = list(team_players_paths.items())
        team_workers = min(max_workers, len(team_scrape_items) or 1)
        print(
            f"Fetching ratings for {len(team_scrape_items)} teams in parallel "
            f"({team_workers} workers)..."
        )
        with ThreadPoolExecutor(max_workers=team_workers) as executor:
            for team_name, players_ratings in executor.map(
                lambda item: _scrape_team_ratings(item[0], item[1], max_workers),
                team_scrape_items,
            ):
                teams_with_players_ratings[team_name] = players_ratings

    # If we are scraping halves, merge into any existing data
    if select_half in (1, 2) and existing_data:
        for team_name, players_dict in teams_with_players_ratings.items():
            if team_name not in existing_data or not isinstance(existing_data[team_name], dict):
                existing_data[team_name] = {}
            existing_data[team_name].update(players_dict)

        teams_with_players_ratings = existing_data

    if write_file:
        # write_dict_data(teams_with_players_ratings, file_name)
        overwrite_dict_data(teams_with_players_ratings, file_name)

    if backup_files:
        for k in range(j):
            delete_file(file_name + "_" + str(j))

    return teams_with_players_ratings

# # team_links = get_team_links_from_league("https://www.sofascore.com/tournament/football/world/club-world-championship/357#id:69619")
# team_links = get_team_links_from_league("https://www.sofascore.com/tournament/football/spain/laliga/8#id:77559")
# pprint(team_links)
#
#
# start_time = time.time()
#
# result = get_players_ratings_list(file_name="test", force_scrape=True)#, team_links=team_links)
# # result = get_players_ratings_list(file_name="test")#, team_links=team_links)
#
# end_time = time.time()
# elapsed_time = end_time - start_time
#
# print(f"Execution time: {elapsed_time} seconds")
#
# for p in result:
#     print(p)
#     print(p.sofascore_rating)

# print(get_player_name("https://www.sofascore.com/es/football/player/vinicius-junior/868812"))
