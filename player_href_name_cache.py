import json
import os
import re
import threading

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILES_DIR = os.path.join(ROOT_DIR, 'json_files')
FUTBOLFANTASY_PLAYER_HREF_CACHE_FILE = os.path.join(
    JSON_FILES_DIR, 'futbolfantasy_player_href_cache.json'
)
JORNADAPERFECTA_PLAYER_HREF_CACHE_FILE = os.path.join(
    JSON_FILES_DIR, 'jornadaperfecta_player_href_cache.json'
)

# 0=alt, 1=texto visible, 2=slug href
PRIORITY_ALT = 0
PRIORITY_TEXT = 1
PRIORITY_HREF_SLUG = 2


def _load_disk_cache(path):
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding='utf-8') as cache_file:
            data = json.load(cache_file)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Could not read cache {path}: {e!r}")
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): value for key, value in data.items()}


def _save_disk_cache(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as cache_file:
        json.dump(data, cache_file, ensure_ascii=False, indent=2)


_INVALID_HREFS = frozenset({'#', 'javascript:void(0)', 'javascript:;'})


def normalize_player_href(href):
    """Clave estable por jugador (slug), independiente de dominio o subrutas."""
    if not href:
        return None
    href = href.strip()
    if href.lower() in _INVALID_HREFS:
        return None
    if 'futbolfantasy.com' in href:
        match = re.search(r'/jugadores/([^/?#]+)', href, re.IGNORECASE)
        if match:
            return f'ff:{match.group(1).lower()}'
    if 'jornadaperfecta.com' in href:
        match = re.search(r'/jugador/([^/?#]+)', href, re.IGNORECASE)
        if match:
            return f'jp:{match.group(1).lower()}'
    return href


class PlayerHrefNameCache:
    """Mapea href de jugador → nombre preferido (alt > texto > slug). Persistente en disco."""

    def __init__(self, cache_path, use_disk_cache=True):
        self.cache_path = cache_path
        self.use_disk_cache = use_disk_cache
        self._entries = {}
        self._lock = threading.Lock()
        if use_disk_cache:
            raw = _load_disk_cache(cache_path)
            for key, value in raw.items():
                if key in _INVALID_HREFS:
                    continue
                if isinstance(value, dict) and value.get('name'):
                    self._entries[key] = {
                        'name': value['name'],
                        'priority': int(value.get('priority', PRIORITY_TEXT)),
                    }
                elif isinstance(value, str) and value:
                    self._entries[key] = {'name': value, 'priority': PRIORITY_TEXT}

    def register(self, href, name, priority=PRIORITY_TEXT):
        if not href or not name:
            return
        key = normalize_player_href(href)
        if not key:
            return
        name = str(name).strip()
        if not name:
            return
        with self._lock:
            existing = self._entries.get(key)
            if existing is None:
                self._entries[key] = {'name': name, 'priority': priority}
                return
            better = (
                priority < existing['priority']
                or (priority == existing['priority'] and len(name) >= len(existing['name']))
            )
            if better:
                self._entries[key] = {'name': name, 'priority': priority}

    def resolve(self, href, fallback_name=None, fallback_priority=PRIORITY_TEXT):
        if fallback_name:
            self.register(href, fallback_name, fallback_priority)
        key = normalize_player_href(href)
        if not key:
            return fallback_name
        with self._lock:
            entry = self._entries.get(key)
        if entry:
            return entry['name']
        return fallback_name

    def persist(self):
        if not self.use_disk_cache:
            return
        with self._lock:
            snapshot = {k: dict(v) for k, v in self._entries.items()}
        _save_disk_cache(self.cache_path, snapshot)
