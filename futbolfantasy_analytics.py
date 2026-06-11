import ast
import os
import re
import copy
import shutil
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pprint import pprint

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
import csv
import requests
from bs4 import BeautifulSoup
import urllib3

from useful_functions import overwrite_dict_data, read_dict_data, create_driver, find_manual_similar_string, \
    read_dict_data_local_only
from player_href_name_cache import (
    PlayerHrefNameCache,
    FUTBOLFANTASY_PLAYER_HREF_CACHE_FILE,
    normalize_player_href,
)

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root


class FutbolFantasyScraper:
    def __init__(self, base_url: str = None, competition: str = None, max_workers: int = 8):
        self.base_url = "https://www.futbolfantasy.com"
        # self.base_url = 'https://www.futbolfantasy.com/analytics/laliga-fantasy/mercado'
        # # self.base_url = 'https://www.futbolfantasy.com/analytics/biwenger/mercado'
        self.competition =  (
            competition
            if competition is not None
            else "laliga"
        )
        self.max_workers = max(1, max_workers)
        self.driver = create_driver()
        self.wait = WebDriverWait(self.driver, 15)
        self.small_wait = WebDriverWait(self.driver, 5)
        self.session = requests.Session()
        self._thread_local = threading.local()
        self._player_href_cache = PlayerHrefNameCache(FUTBOLFANTASY_PLAYER_HREF_CACHE_FILE)
        self._last_request_time = 0.0
        self.request_delay = 1.0
        # Use this custom headers dict when making GET requests
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }

    def fetch_page(self, url):
        self.driver.get(url)

    def _thread_session(self):
        if not getattr(self._thread_local, 'session', None):
            self._thread_local.session = requests.Session()
            self._thread_local.last_request_time = 0.0
        return self._thread_local.session

    def fetch_response(self, url, max_retries=5):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        session = self._thread_session()
        last_request_time = getattr(self._thread_local, 'last_request_time', 0.0)
        last_response = None
        for attempt in range(max_retries):
            elapsed = time.time() - last_request_time
            if elapsed < self.request_delay:
                time.sleep(self.request_delay - elapsed)
            last_response = session.get(url, headers=self.headers, verify=False)
            last_request_time = time.time()
            self._thread_local.last_request_time = last_request_time
            if last_response.status_code == 429:
                retry_after = last_response.headers.get('Retry-After')
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

    def accept_cookies(self):
        # This function was used to click a cookie accept button with Selenium,
        # but it's not needed when using requests unless the site strictly requires
        # special headers or cookies. We'll leave it here to keep the comment.
        pass

    def get_team_options(self, html):
        # select = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="main_wrapper"]/div/div[1]/main/div[3]/div[2]/div[2]/select')))
        # Instead, parse HTML with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        select = soup.find('select', {'name': 'equipo'})
        team_options = {}
        if select:
            options = select.find_all('option')
            for option in options:
                value = option.get('value', '')
                if value and value != '0':
                    team_options[value] = option.text.strip()
        return team_options

    def get_player_elements(self, html):
        # players_container = self.wait.until(EC.presence_of_element_located((By.XPATH, f'//div[@class="lista_elementos"]')))
        # Instead, parse HTML with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        players_container = soup.find(class_='lista_elementos')
        if not players_container:
            return []
        # Mercado actual: tbody.lista_elementos > tr.elemento_jugador (datos en data-*)
        player_elements = players_container.find_all('tr', class_='elemento_jugador')
        if player_elements:
            return player_elements
        # Formato antiguo: div.lista_elementos > div hijos directos
        # player_elements = players_container.find_elements(By.XPATH, './div')
        return players_container.find_all('div', recursive=False)

    def get_player_data(self, player_element):
        # We gather attributes from the HTML element
        # Because these are stored in data-* attributes, we can access them via get(...)
        name = player_element.get('data-nombre', '').strip().title()
        name = find_manual_similar_string(name)
        price = player_element.get('data-valor', '').strip()
        position = player_element.get('data-posicion', '').strip()
        team_id = player_element.get('data-equipo', '').strip()
        form = player_element.get('data-diferencia-pct1', '').strip()
        price_trend = player_element.get('data-diferencia1', '').strip() or "0"
        return name, price, position, team_id, form, price_trend

    @staticmethod
    def _as_root_list(roots):
        # Permite pasar un Tag/BeautifulSoup individual o una lista de varios
        if roots is None:
            return []
        if isinstance(roots, (list, tuple, set)):
            return [r for r in roots if r is not None]
        return [roots]

    _FORMATION_LABEL_RE = re.compile(r'\(?\s*\d+(?:\s*[-x\s]\s*\d+){1,4}\s*\)?', re.IGNORECASE)
    _LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)
    _SIDE_LABEL_RE = re.compile(r"\(?\s*(?:izq\.?|dcha\.?)\s*\)?", re.IGNORECASE)

    def _is_formation_label(self, name):
        # Filtra textos como "(4-3-3)" o "4-2-3-1" (y los residuos tipo "(--)" tras
        # quitar dígitos). Cualquier cadena sin letras se considera no-jugador.
        # También filtra etiquetas de lado como "(Izq.)" o "(Dcha.)".
        if not name:
            return True
        name = name.strip()
        if self._SIDE_LABEL_RE.fullmatch(name):
            return True
        if not self._LETTER_RE.search(name):
            return True
        return bool(self._FORMATION_LABEL_RE.fullmatch(name))

    def find_camiseta_elements(self, roots, include_substitutes=True):
        # Equivalente a //*[contains(@class, "camiseta ")] (excluye camiseta-wrapper)
        results = []
        for root in self._as_root_list(roots):
            for element in root.find_all('a'):
                classes = element.get('class') or []
                if 'camiseta' not in classes:
                    continue
                if not include_substitutes and 'camiseta-previa' in classes:
                    continue
                results.append(element)
        return results

    def _starter_camiseta_elements(self, roots):
        return [
            a for a in self.find_camiseta_elements(roots, include_substitutes=True)
            if 'camiseta-previa' not in (a.get('class') or [])
        ]

    def _substitute_camiseta_elements(self, roots):
        return [
            a for a in self.find_camiseta_elements(roots, include_substitutes=True)
            if 'camiseta-previa' in (a.get('class') or [])
        ]

    def _find_camiseta_wrapper(self, camiseta):
        for parent in camiseta.parents:
            classes = parent.get('class') or []
            if 'camiseta-wrapper' in classes:
                return parent
        return None

    def _get_juggador_alternatives(self, wrapper):
        # Devuelve los juggadores dentro de un wrapper excluyendo pos-0 (el mismo titular)
        if wrapper is None:
            return []
        juggadores_div = wrapper.find(class_='juggadores')
        if not juggadores_div:
            return []
        alternatives = []
        for juggador in juggadores_div.find_all('a', class_='juggador'):
            classes = juggador.get('class') or []
            if 'pos-0' in classes:
                continue
            alternatives.append(juggador)
        return alternatives

    def _alternative_probabilities(self, options_count):
        # Reparto por defecto cuando el principal no tiene porcentaje
        if options_count <= 0:
            return []
        if options_count == 1:
            return [0.8]
        if options_count == 2:
            return [0.6, 0.4]
        return [0.4] + [0.6 / (options_count - 1)] * (options_count - 1)

    def _starter_default_probability(self, wrapper):
        # Default para el titular cuando no tiene data-probabilidad
        alternatives_count = len(self._get_juggador_alternatives(wrapper))
        return self._alternative_probabilities(1 + alternatives_count)[0]

    def _resolve_player_name(self, *display_names):
        # Alt / texto visible. Si hay varios (p. ej. alt "Íñigo Lekue" y span "Lekue"),
        # nos quedamos con el más completo.
        candidates = []
        for display_name in display_names:
            if not display_name:
                continue
            display_name = display_name.strip()
            if display_name and not self._is_formation_label(display_name):
                candidates.append(find_manual_similar_string(display_name))
        if not candidates:
            return None
        return max(candidates, key=lambda name: (len(name.split()), len(name)))

    def _name_from_player_href(self, href):
        # Solo como respaldo en juggadores sin alt: el slug no tiene tildes.
        if not href:
            return None
        match = re.search(r'/jugadores/([^/?#]+)', href)
        if not match:
            return None
        slug = match.group(1).replace('-', ' ')
        return find_manual_similar_string(slug.title())

    def _get_player_name_from_juggador(self, juggador):
        span = juggador.find('span', class_='truncate-name')
        span_name = span.get_text(strip=True) if span else juggador.get_text(strip=True)
        alt_name = None
        img = juggador.find('img', alt=True)
        if img and img.get('alt'):
            alt_name = img['alt'].strip()
        display_name = self._resolve_player_name(span_name, alt_name)
        if display_name and len(display_name.split()) >= 2:
            return display_name
        href_name = self._name_from_player_href(juggador.get('href'))
        return self._resolve_player_name(display_name, href_name)

    def get_player_name_from_camiseta(self, player_element):
        alt_names = []
        for parent in player_element.parents:
            parent_classes = parent.get('class') or []
            if any('fotocontainer' in cls for cls in parent_classes):
                img = parent.find('img', alt=True)
                if img and img.get('alt'):
                    alt_names.append(img['alt'].strip())
                    break
        if not alt_names:
            img = player_element.find(
                class_=lambda c: c and 'img' in ' '.join(c if isinstance(c, list) else [c])
            )
            if img and img.get('alt'):
                alt_names.append(img['alt'].strip())
        if not alt_names:
            img = player_element.find('img', alt=True)
            if img and img.get('alt'):
                alt_names.append(img['alt'].strip())
        return self._resolve_player_name(*alt_names)

    def normalize_probability_text(self, probability, default=None):
        if probability is None:
            probability = default
        if probability is None:
            return None
        probability = str(probability).strip()
        if probability == "Titular":
            probability = "100%"
        if probability == "Suplente":
            probability = "0%"
        probability = re.sub(r'[^0-9%]', '', probability)
        if not probability:
            return None
        return float(probability.replace('%', '')) / 100

    def _clean_player_name(self, name):
        if not name:
            return None
        if self._is_formation_label(name):
            return None
        name = re.sub(r'[\d%]', '', name).strip()
        if not name or self._is_formation_label(name):
            return None
        return find_manual_similar_string(name)

    def _get_player_info_from_camiseta(self, camiseta):
        """(href, name, priority)  priority: 0=alt, 2=href_slug"""
        href = (camiseta.get('href') or '').strip() or None
        alt_name = None
        for parent in camiseta.parents:
            parent_classes = parent.get('class') or []
            if any('fotocontainer' in cls for cls in parent_classes):
                img = parent.find('img', alt=True)
                if img and img.get('alt'):
                    alt_name = img['alt'].strip()
                break
        if not alt_name:
            img = camiseta.find(
                class_=lambda c: c and 'img' in ' '.join(c if isinstance(c, list) else [c])
            )
            if img and img.get('alt'):
                alt_name = img['alt'].strip()
        if not alt_name:
            img = camiseta.find('img', alt=True)
            if img and img.get('alt'):
                alt_name = img['alt'].strip()
        if alt_name and not self._is_formation_label(alt_name):
            name = find_manual_similar_string(alt_name)
            if name:
                return href, name, 0
        if href:
            href_name = self._name_from_player_href(href)
            if href_name:
                return href, href_name, 2
        return href, None, 2

    def _get_player_info_from_juggador(self, juggador):
        """(href, name, priority)  priority: 0=alt, 1=text, 2=href_slug"""
        href = (juggador.get('href') or '').strip() or None
        img = juggador.find('img', alt=True)
        alt_name = img['alt'].strip() if (img and img.get('alt')) else None
        if alt_name and not self._is_formation_label(alt_name):
            name = find_manual_similar_string(alt_name)
            if name and len(name.split()) >= 2:
                return href, name, 0
        span = juggador.find('span', class_='truncate-name')
        span_name = span.get_text(strip=True) if span else juggador.get_text(strip=True)
        if span_name and not self._is_formation_label(span_name):
            text_name = find_manual_similar_string(span_name.strip())
            if text_name and len(text_name.split()) >= 2:
                return href, text_name, 1
        if href:
            href_name = self._name_from_player_href(href)
            if href_name:
                return href, href_name, 2
        # Nombre de una sola palabra (apellido truncado) como último recurso
        if span_name and not self._is_formation_label(span_name):
            return href, find_manual_similar_string(span_name.strip()), 1
        if alt_name and not self._is_formation_label(alt_name):
            return href, find_manual_similar_string(alt_name), 0
        return href, None, 2

    def _record_key(self, href, name):
        cache_key = normalize_player_href(href)
        if cache_key:
            return cache_key
        if name:
            return f'__noref__{name}'
        return None

    def _update_player_record(self, records, href, name, priority, prob):
        """Acumula jugadores keyed por href.
        - Nombre: menor prioridad gana (0=alt > 1=texto > 2=slug); empate: más largo gana; igual: último.
        - Probabilidad: la más alta gana.
        """
        key = self._record_key(href, name)
        if not key:
            return
        name = name or ''
        existing = records.get(key)
        if existing is None:
            records[key] = {'name': name, 'priority': priority, 'prob': prob}
        else:
            better_name = (
                priority < existing['priority'] or
                (priority == existing['priority'] and len(name) >= len(existing['name']))
            )
            if better_name and name:
                records[key]['name'] = name
                records[key]['priority'] = priority
            if prob is not None and (existing['prob'] is None or prob > existing['prob']):
                records[key]['prob'] = prob
        self._player_href_cache.register(href, name, priority)

    def _records_to_probabilities(self, records):
        """Convierte el dict interno keyed-by-href a {nombre: probabilidad}."""
        result = {}
        for key, data in records.items():
            name = data.get('name')
            prob = data.get('prob')
            if name and prob is not None:
                if not str(key).startswith('__noref__'):
                    name = self._player_href_cache.resolve(key, name) or name
                if name not in result or prob > result[name]:
                    result[name] = prob
        return result

    def _is_lineup_confirmed(self, roots):
        for root in self._as_root_list(roots):
            if not hasattr(root, 'get_text'):
                continue
            text = root.get_text(' ', strip=True).lower()
            if 'alineación confirmada' in text or 'alineacion confirmada' in text:
                return True
        return False

    def parse_camiseta_probabilities(self, roots, include_substitutes=False):
        # Acepta un root o una lista (p. ej. [titulares, suplentes] en un partido)
        root_list = self._as_root_list(roots)
        if not root_list:
            return {}

        starter_camisetas = self._starter_camiseta_elements(root_list)
        substitute_camisetas = (
            self._substitute_camiseta_elements(root_list) if include_substitutes else []
        )

        # 1) Alineación confirmada → 1.0 a los del XI, 0 a los que no
        if self._is_lineup_confirmed(root_list):
            return self._parse_confirmed_lineup(starter_camisetas, substitute_camisetas)

        # 2) Sin porcentajes en titulares (p. ej. world-cup): reparto por defecto en cada grupo
        if not any(c.get('data-probabilidad') for c in starter_camisetas):
            return self._parse_default_juggadores_groups(root_list)

        # 3) Con porcentajes: titulares con su prob, suplentes con su prob (si los hay)
        #    o, en su defecto, alternativas del grupo con (1 - prob_titular) / n
        return self._parse_lineup_with_probabilities(starter_camisetas, substitute_camisetas)

    def _parse_confirmed_lineup(self, starter_camisetas, substitute_camisetas):
        records = {}
        for camiseta in starter_camisetas + substitute_camisetas:
            probability = self.normalize_probability_text(
                camiseta.get('data-probabilidad'),
                default='0%',
            )
            if probability is None:
                continue
            href, name, priority = self._get_player_info_from_camiseta(camiseta)
            name = self._clean_player_name(name)
            if name:
                self._update_player_record(records, href, name, priority, probability)
        return self._records_to_probabilities(records)

    def _parse_default_juggadores_groups(self, roots):
        records = {}
        seen_wrappers = set()
        for root in roots:
            for wrapper in root.find_all(class_=lambda c: c and 'camiseta-wrapper' in c):
                if id(wrapper) in seen_wrappers:
                    continue
                seen_wrappers.add(id(wrapper))
                juggadores_div = wrapper.find(class_='juggadores')
                if not juggadores_div:
                    continue
                player_infos = []
                for juggador in juggadores_div.find_all('a', class_='juggador'):
                    href, name, priority = self._get_player_info_from_juggador(juggador)
                    name = self._clean_player_name(name)
                    if name:
                        player_infos.append((href, name, priority))
                if not player_infos:
                    continue
                for (href, name, priority), probability in zip(
                    player_infos,
                    self._alternative_probabilities(len(player_infos)),
                ):
                    self._update_player_record(records, href, name, priority, probability)
        return self._records_to_probabilities(records)

    def _parse_lineup_with_probabilities(self, starter_camisetas, substitute_camisetas):
        records = {}
        starter_records = []  # (href, name, priority, prob, wrapper)
        for camiseta in starter_camisetas:
            wrapper = self._find_camiseta_wrapper(camiseta)
            raw_probability = camiseta.get('data-probabilidad')
            probability = (
                self.normalize_probability_text(raw_probability) if raw_probability
                else self._starter_default_probability(wrapper)
            )
            if probability is None:
                continue
            href, name, priority = self._get_player_info_from_camiseta(camiseta)
            name = self._clean_player_name(name)
            if not name:
                continue
            self._update_player_record(records, href, name, priority, probability)
            starter_records.append((href, name, priority, probability, wrapper))

        substitute_records = []
        for camiseta in substitute_camisetas:
            probability = self.normalize_probability_text(camiseta.get('data-probabilidad'))
            if probability is None:
                continue
            href, name, priority = self._get_player_info_from_camiseta(camiseta)
            name = self._clean_player_name(name)
            if name:
                substitute_records.append((href, name, priority, probability))

        if substitute_records:
            # Los suplentes con porcentaje traen el nombre completo (img alt). No procesamos
            # las alternativas del grupo para no sobrescribir con apellidos truncados.
            for href, name, priority, probability in substitute_records:
                self._update_player_record(records, href, name, priority, probability)
            return self._records_to_probabilities(records)

        # Sin suplentes con probabilidad: las alternativas del grupo (juggador pos>0) reciben
        # (1 - prob_titular) repartido equitativamente entre ellas.
        for href_t, titular_name, priority_t, titular_prob, wrapper in starter_records:
            alternatives = []
            for juggador in self._get_juggador_alternatives(wrapper):
                href_a, alt_name, alt_priority = self._get_player_info_from_juggador(juggador)
                alt_name = self._clean_player_name(alt_name)
                if alt_name and alt_name != titular_name:
                    alternatives.append((href_a, alt_name, alt_priority))
            if not alternatives:
                continue
            remaining = max(1 - titular_prob, 0)
            share = remaining / len(alternatives)
            for href_a, alt_name, alt_priority in alternatives:
                self._update_player_record(records, href_a, alt_name, alt_priority, share)
        return self._records_to_probabilities(records)

    def _find_element_by_class_prefix(self, root, prefix):
        # BeautifulSoup separa "equipo local" en ['equipo', 'local', ...]
        prefix_tokens = prefix.strip().split()
        for element in root.find_all(True):
            classes = element.get('class') or []
            if not classes:
                continue
            class_str = ' '.join(classes)
            if class_str.startswith(prefix.strip()):
                return element
            if len(prefix_tokens) > 1 and classes[:len(prefix_tokens)] == prefix_tokens:
                return element
        return None

    def _get_match_team_names(self, soup):
        home_team_name = ""
        away_team_name = ""
        local_el = soup.select_one('.resultado .equipo.local') or self._find_element_by_class_prefix(soup, 'equipo local ')
        if local_el:
            nombre_el = local_el.select_one('.nombre') or self._find_element_by_class_prefix(local_el, 'nombre ')
            if nombre_el:
                home_team_name = find_manual_similar_string(nombre_el.get_text(strip=True))
        visit_el = soup.select_one('.resultado .equipo.visitante') or self._find_element_by_class_prefix(soup, 'equipo visitante ')
        if visit_el:
            nombre_el = visit_el.select_one('.nombre') or self._find_element_by_class_prefix(visit_el, 'nombre ')
            if nombre_el:
                away_team_name = find_manual_similar_string(nombre_el.get_text(strip=True))
        return home_team_name, away_team_name

    def _get_match_lineup_containers(self, soup):
        home_start = soup.select_one('div.row.fondo-campo .row-local')
        away_start = soup.select_one('div.row.fondo-campo .row-visitante')
        if not home_start or not away_start:
            row = soup.select_one('div.row.fondo-campo.m-auto')
            if row:
                team_divs = [child for child in row.find_all('div', recursive=False) if child.get('class')]
                if len(team_divs) >= 2:
                    home_start, away_start = team_divs[0], team_divs[1]
        home_sup = soup.select_one('.suplentes-container .alineacion_superwrapper.local')
        away_sup = soup.select_one('.suplentes-container .alineacion_superwrapper.visitante')
        if not home_sup or not away_sup:
            sup_container = soup.select_one('.suplentes-container')
            if sup_container:
                sup_row = sup_container.select_one('.row')
                if sup_row:
                    sup_cols = [
                        col for col in sup_row.find_all('div', recursive=False)
                        if col.get('class')
                    ]
                    if len(sup_cols) >= 2:
                        home_sup, away_sup = sup_cols[0], sup_cols[1]
        return home_start, away_start, home_sup, away_sup

    def _parse_jornada_from_page_header(self, soup):
        for element in soup.find_all(['h1', 'h2']):
            jornada_match = re.search(
                r'Jornada\s*(\d+)',
                element.get_text(' ', strip=True),
                re.IGNORECASE,
            )
            if jornada_match:
                return int(jornada_match.group(1))
        return None

    def _parse_jornada_from_select_option_url(self, url):
        match = re.search(r'/posibles-alineaciones/(\d+)/?$', url or '')
        if match:
            return int(match.group(1))
        return None

    def _get_selected_jornada_from_soup(self, soup):
        for select in soup.find_all('select', attrs={'name': 'jornada'}):
            numeric_options = []
            for option in select.find_all('option'):
                jornada = self._parse_jornada_from_select_option_url(
                    option.get('value', '').strip(),
                )
                if jornada is None:
                    continue
                numeric_options.append((option, jornada))
            if not numeric_options:
                continue
            for option, jornada in numeric_options:
                if option.has_attr('selected'):
                    return jornada
            return numeric_options[0][1]
        return None

    def _get_posibles_alineaciones_jornada_numbers(self, soup):
        current_jornada = self._get_selected_jornada_from_soup(soup)
        if current_jornada is None:
            current_jornada = self._parse_jornada_from_page_header(soup)
        if current_jornada is None:
            current_jornada = 1
        return [current_jornada, current_jornada + 1]

    def _extract_match_links_from_posibles_alineaciones(self, soup):
        main = soup.find('main')
        if not main:
            return []
        match_links = []
        for anchor in main.find_all('a', href=True):
            href = anchor['href']
            if 'www.futbolfantasy.com/partidos/' in href:
                match_links.append(href)
        return match_links

    def scrape_teams_probabilities(self):
        teams_list_url = f"{self.base_url}/{self.competition}/clasificacion"
        # teams_list_url = "https://www.futbolfantasy.com/laliga/clasificacion"
        # # teams_list_url = "https://www.futbolfantasy.com/mundial-clubes/clasificacion"
        html = self.fetch_response(teams_list_url)
        soup = BeautifulSoup(html, 'html.parser')

        # Equivalente a //a[@href and @title]
        team_elements = soup.find_all('a', href=True, title=True)
        pattern = re.compile(
            r"^https://www\.futbolfantasy\.com/.*/equipos/[^/]+$"
        )
        team_links = {}
        for team_element in team_elements:
            team_link = team_element.get("href", "").strip()
            team_name = team_element.get("title", "").strip()
            team_name = find_manual_similar_string(team_name)
            if team_name and team_link and pattern.match(team_link):# and team_name == "Leganés":
                team_links[team_name] = team_link

        # team_elements = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, '//tr[contains(@class,"team")][td[contains(@class,"column left nombre")]]')))
        # # team_elements = team_elements[:20]
        # team_links = {}
        # for team_element in team_elements:
        #     team_name = team_element.find_element(By.TAG_NAME, 'strong').text.strip()
        #     team_name = team_name.split("\\")[0]
        #     team_name = find_manual_similar_string(team_name)
        #     team_link = team_element.find_element(By.TAG_NAME, 'a').get_attribute('href').strip()
        #     team_links[team_name] = team_link
        # team_links = {k.split("\n")[0]: v for k, v in team_links.items() if v != "https://www.futbolfantasy.com/"}

        probabilities_dict = {}
        items = list(team_links.items())
        workers = min(self.max_workers, len(items) or 1)
        print(f"Fetching team probabilities for {len(items)} teams ({workers} workers)...")
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(self._scrape_team_probabilities, team_name, team_link)
                for team_name, team_link in items
            ]
            for future in as_completed(futures):
                team_name, team_probabilities = future.result()
                if team_probabilities:
                    probabilities_dict[team_name] = team_probabilities

        return probabilities_dict

    def _scrape_team_probabilities(self, team_name, team_link):
        print('Extracting probabilities from %s ...' % team_name)
        team_html = self.fetch_response(team_link)
        team_soup = BeautifulSoup(team_html, 'html.parser')
        team_probabilities = self.parse_camiseta_probabilities(
            team_soup,
            include_substitutes=True,
        )
        return team_name, team_probabilities

    def scrape_matches_probabilities(self, probabilities_dict=None):
        if not probabilities_dict:
            probabilities_dict = {}

        # 1) Fetch posibles-alineaciones (sin jornada + jornada del select + siguiente)
        posibles_alineaciones_url = f"{self.base_url}/{self.competition}/posibles-alineaciones"
        # posibles_alineaciones_url = "https://www.futbolfantasy.com/laliga/posibles-alineaciones"
        html = self.fetch_response(posibles_alineaciones_url)
        soup = BeautifulSoup(html, 'html.parser')
        jornada_numbers = self._get_posibles_alineaciones_jornada_numbers(soup)
        posibles_alineaciones_urls = [posibles_alineaciones_url]
        if jornada_numbers:
            posibles_alineaciones_urls.extend(
                f"{posibles_alineaciones_url}/{jornada}" for jornada in jornada_numbers
            )

        match_links = []
        extra_list_urls = [
            list_url for list_url in posibles_alineaciones_urls
            if list_url != posibles_alineaciones_url
        ]
        page_soup = BeautifulSoup(html, 'html.parser')
        match_links.extend(self._extract_match_links_from_posibles_alineaciones(page_soup))
        if extra_list_urls:
            workers = min(self.max_workers, len(extra_list_urls))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                for page_html in executor.map(self.fetch_response, extra_list_urls):
                    page_soup = BeautifulSoup(page_html, 'html.parser')
                    match_links.extend(
                        self._extract_match_links_from_posibles_alineaciones(page_soup)
                    )
        match_links = sorted(set(match_links))

        workers = min(self.max_workers, len(match_links) or 1)
        print(f"Fetching match probabilities for {len(match_links)} matches ({workers} workers)...")
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(self._scrape_match_probabilities, match_url)
                for match_url in match_links
            ]
            for future in as_completed(futures):
                for team_name, team_probabilities in future.result():
                    if not team_name or not team_probabilities:
                        continue
                    if team_name not in probabilities_dict:
                        probabilities_dict[team_name] = {}
                    for match_player_name, chance_val in team_probabilities.items():
                        probabilities_dict[team_name][match_player_name] = chance_val

        return probabilities_dict

    def _scrape_match_probabilities(self, match_url):
        match_html = self.fetch_response(match_url)
        match_soup = BeautifulSoup(match_html, 'html.parser')

        home_team_name, away_team_name = self._get_match_team_names(match_soup)
        home_start, away_start, home_sup, away_sup = self._get_match_lineup_containers(match_soup)
        teams_elements = {
            home_team_name: [x for x in (home_start, home_sup) if x is not None],
            away_team_name: [x for x in (away_start, away_sup) if x is not None],
        }

        if not any((home_start, home_sup, away_start, away_sup)):
            return []

        results = []
        for team_name, containers in teams_elements.items():
            if not team_name or not containers:
                continue
            team_probabilities = self.parse_camiseta_probabilities(
                containers,
                include_substitutes=True,
            )
            if team_probabilities:
                results.append((team_name, team_probabilities))
        return results

    def scrape_probabilities(self):
        teams_probabilities_dict = self.scrape_teams_probabilities()
        matches_probabilities_dict = self.scrape_matches_probabilities(teams_probabilities_dict)
        self._player_href_cache.persist()
        probabilities_dict = copy.deepcopy(matches_probabilities_dict)

        return probabilities_dict

    def scrape(self):
        # self.fetch_page(self.base_url)
        # self.accept_cookies()
        # main_html = self.fetch_response(self.base_url)
        main_html = self.fetch_response(f"{self.base_url}/analytics/laliga-fantasy/mercado")
        # main_html = self.fetch_response(f"{self.base_url}/analytics/biwenger/mercado")
        team_options = self.get_team_options(main_html)

        positions_normalize = {
            "Portero": "GK",
            "Defensa": "DEF",
            "Mediocampista": "MID",
            "Delantero": "ATT",
        }

        prices_dict = {team_name: {} for team_name in team_options.values()}
        positions_dict = {team_name: {} for team_name in team_options.values()}
        forms_dict = {team_name: {} for team_name in team_options.values()}
        price_trends_dict = {team_name: {} for team_name in team_options.values()}

        player_elements = self.get_player_elements(main_html)
        for player_element in player_elements:
            name, price, position, team_id, form, price_trend = self.get_player_data(player_element)
            team_name = team_options.get(team_id)
            team_name = find_manual_similar_string(team_name)
            position_name = positions_normalize.get(position)
            if team_name:
                prices_dict[team_name][name] = float(price)
                positions_dict[team_name][name] = position_name
                forms_dict[team_name][name] = float(form)
                price_trends_dict[team_name][name] = float(price_trend)

        probabilities_dict = self.scrape_probabilities()

        # We don't have a browser to quit, but we'll keep the comment
        # self.driver.quit()
        return prices_dict, positions_dict, forms_dict, probabilities_dict, price_trends_dict


def competition_from_filename(file_name: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', file_name.lower())  # normalize to dashed tokens

    mapping = {
        ("mundialito", "club-world-cup", "clubworldcup", "mundial-clubes", "mundialclubes", ): "mundial-clubes",
        ("champions", "championsleague", "champions-league"): "champions",
        ('europaleague', 'europa-league', ): "europa-league",
        ('conference', 'conferenceleague', 'conference-league', ): "conference-league",
        ("eurocopa", "euro", "europa", "europeo", ): "eurocopa",
        ("copaamerica", "copa-america", ): "copa-america",
        ("mundial", "worldcup", "world-cup", ): "world-cup",
        ("laliga", "la-liga", ): "laliga",
        ('premier', 'premier-league', 'premierleague', ): "premier-league",
        ('seriea', 'serie-a', ): "serie-a",
        ('bundesliga', 'bundes-liga', 'bundes', ): "bundesliga",
        ('ligueone', 'ligue-one', 'ligue1', 'ligue-1', 'ligue', ): "ligue-1",
        ("segunda", "segundadivision", "segunda-division", "laliga2", "la-liga-2", "la-liga-hypermotion", "hypermotion", "laligahypermotion", ): "laliga2",
    }
    for keys, slug in mapping.items():
        for k in sorted(keys, key=len, reverse=True):  # longest first
            if k in s:
                return slug
    return "laliga"


def get_futbolfantasy_data(
        price_file_name="futbolfantasy_prices",
        positions_file_name="futbolfantasy_positions",
        forms_file_name="futbolfantasy_forms",
        start_probability_file_name="futbolfantasy_start_probabilities",
        price_trends_file_name="futbolfantasy_price_trends",
        force_scrape=False
):
    if not force_scrape:
        prices_data = read_dict_data(price_file_name)
        positions_data = read_dict_data(positions_file_name)
        forms_data = read_dict_data(forms_file_name)
        start_probabilities_data = read_dict_data(start_probability_file_name)
        price_trends_data = read_dict_data(price_trends_file_name)

        if prices_data and positions_data and forms_data and start_probabilities_data and price_trends_data:
            return prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data

    competition = competition_from_filename(start_probability_file_name)
    scraper = FutbolFantasyScraper(competition=competition)
    prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data = scraper.scrape()

    overwrite_dict_data(prices_data, price_file_name)
    overwrite_dict_data(positions_data, positions_file_name)
    overwrite_dict_data(forms_data, forms_file_name)
    overwrite_dict_data(start_probabilities_data, start_probability_file_name)
    overwrite_dict_data(price_trends_data, price_trends_file_name)

    return prices_data, positions_data, forms_data, start_probabilities_data, price_trends_data


def get_players_prices_dict_futbolfantasy(
        file_name="futbolfantasy_prices",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = FutbolFantasyScraper(competition=competition)
    result, _, _, _, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_positions_dict_futbolfantasy(
        file_name="futbolfantasy_positions",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = FutbolFantasyScraper(competition=competition)
    _, result, _, _, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_forms_dict_futbolfantasy(
        file_name="futbolfantasy_forms",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = FutbolFantasyScraper(competition=competition)
    _, _, result, _, _ = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


def get_players_start_probabilities_dict_futbolfantasy(
        file_name="futbolfantasy_start_probabilities",
        force_scrape=False,
        max_workers=8,
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
    scraper = FutbolFantasyScraper(competition=competition, max_workers=max_workers)
    # _, _, _, result, _ = scraper.scrape()
    result = scraper.scrape_probabilities()

    overwrite_dict_data(result, file_name)

    return result


def get_players_price_trends_dict_futbolfantasy(
        file_name="futbolfantasy_price_trends",
        force_scrape=False
):
    if not force_scrape:
        data = read_dict_data(file_name)
        if data:
            return data

    competition = competition_from_filename(file_name)
    scraper = FutbolFantasyScraper(competition=competition)
    _, _, _, _, result = scraper.scrape()

    overwrite_dict_data(result, file_name)

    return result


# prices, positions, forms, start_probabilities, price_trends = get_futbolfantasy_data(
#     price_file_name="test_futbolfantasy_laliga_players_prices",
#     positions_file_name="test_futbolfantasy_laliga_players_positions",
#     forms_file_name="test_futbolfantasy_laliga_players_forms",
#     start_probability_file_name="test_futbolfantasy_laliga_players_start_probabilities",
#     price_trends_file_name="test_futbolfantasy_laliga_players_price_trends",
#     force_scrape=True
# )
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
