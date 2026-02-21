"""
Database connection pool and event-logging helpers for Calculadora Fantasy.
Uses PyMySQL (pure-Python MySQL driver) with a simple connection pool.
All writes are fire-and-forget on a background thread so they never slow down API responses.
"""
import json
import logging
import os
import queue
import ssl
import threading
from contextlib import contextmanager

import pymysql

logger = logging.getLogger("db")

# ─── Configuration from environment variables ────────────────────────────────
_DB_HOST = os.getenv("DB_HOST", "")
_DB_PORT = int(os.getenv("DB_PORT", "3306"))
_DB_USER = os.getenv("DB_USER", "")
_DB_PASS = os.getenv("DB_PASSWORD", "")
_DB_NAME = os.getenv("DB_NAME", "defaultdb")
_DB_SSL = os.getenv("DB_SSL", "false").lower() in ("true", "1", "yes")
_DB_SSL_CA = os.getenv("DB_SSL_CA", "")

_POOL_SIZE = min(int(os.getenv("DB_POOL_SIZE", "3")), 10)

DB_ENABLED = bool(_DB_HOST and _DB_USER)

# ─── SSL context ─────────────────────────────────────────────────────────────
_ssl_ctx = None
if _DB_SSL:
    _ssl_ctx = ssl.create_default_context()
    if _DB_SSL_CA and os.path.isfile(_DB_SSL_CA):
        _ssl_ctx.load_verify_locations(_DB_SSL_CA)


# ─── Simple connection pool ──────────────────────────────────────────────────
_pool: queue.Queue = queue.Queue(maxsize=_POOL_SIZE)


def _new_conn():
    kwargs = dict(
        host=_DB_HOST,
        port=_DB_PORT,
        user=_DB_USER,
        password=_DB_PASS,
        database=_DB_NAME,
        charset="utf8mb4",
        autocommit=True,
        connect_timeout=5,
        read_timeout=10,
        write_timeout=10,
    )
    if _ssl_ctx:
        kwargs["ssl"] = _ssl_ctx
    return pymysql.connect(**kwargs)


def _init_pool():
    if not DB_ENABLED:
        return
    for _ in range(_POOL_SIZE):
        try:
            _pool.put_nowait(_new_conn())
        except Exception as e:
            logger.warning("Could not create DB connection for pool: %s", e)


@contextmanager
def get_conn():
    """Borrow a connection from the pool; return it when done."""
    conn = None
    try:
        conn = _pool.get_nowait()
    except queue.Empty:
        conn = _new_conn()

    try:
        conn.ping(reconnect=True)
        yield conn
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        conn = _new_conn()
        raise
    finally:
        if conn:
            try:
                _pool.put_nowait(conn)
            except queue.Full:
                conn.close()


# ─── Background writer (fire-and-forget) ─────────────────────────────────────
_write_q: queue.Queue = queue.Queue(maxsize=500)


def _writer_loop():
    while True:
        sql, params = _write_q.get()
        if sql is None:
            break
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
        except Exception as e:
            logger.error("DB write failed: %s — %s %s", e, sql[:80], params)


_writer_thread: threading.Thread | None = None


def _ensure_writer():
    global _writer_thread
    if _writer_thread and _writer_thread.is_alive():
        return
    _writer_thread = threading.Thread(target=_writer_loop, daemon=True, name="db-writer")
    _writer_thread.start()


def _enqueue(sql: str, params: tuple):
    """Fire-and-forget: enqueue a write to be executed on the background thread."""
    if not DB_ENABLED:
        return
    _ensure_writer()
    try:
        _write_q.put_nowait((sql, params))
    except queue.Full:
        logger.warning("DB write queue full, dropping event")


# ─── Logging functions (called from api.py) ──────────────────────────────────

def log_visit(session_id: str, page: str, lang: str, user_agent: str,
              ip_hash: str, referrer: str, screen_w: int = None, screen_h: int = None):
    _enqueue(
        "INSERT INTO visits (session_id, page, lang, user_agent, ip_hash, referrer, screen_w, screen_h) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (session_id, page, lang, user_agent, ip_hash, referrer, screen_w, screen_h),
    )


def log_player_load(session_id: str, competition: str, app_source: str,
                    jornada_key: str, num_jornadas: int,
                    ignore_form: bool, ignore_fixtures: bool, ignore_penalties: bool,
                    players_loaded: int):
    _enqueue(
        "INSERT INTO player_loads (session_id, competition, app_source, jornada_key, "
        "num_jornadas, ignore_form, ignore_fixtures, ignore_penalties, players_loaded) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (session_id, competition, app_source, jornada_key or None,
         num_jornadas, ignore_form, ignore_fixtures, ignore_penalties, players_loaded),
    )


def log_calculation(session_id: str, calc_type: str, competition: str,
                    app_source: str, budget: int, formations_in: list,
                    formations_out: int, num_players: int,
                    blinded_count: int, banned_count: int,
                    min_prob: float, max_prob: float,
                    speed_up: bool, duration_ms: int) -> int | None:
    """Log a calculation and return the inserted row id (or None on failure)."""
    if not DB_ENABLED:
        return None
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO calculations (session_id, calc_type, competition, app_source, "
                    "budget, formations_in, formations_out, num_players, blinded_count, banned_count, "
                    "min_prob, max_prob, speed_up, duration_ms) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (session_id, calc_type, competition, app_source, budget,
                     json.dumps(formations_in), formations_out, num_players,
                     blinded_count, banned_count, min_prob, max_prob, speed_up, duration_ms),
                )
                return cur.lastrowid
    except Exception as e:
        logger.error("log_calculation failed: %s", e)
        return None


def log_result_formation(calculation_id: int, formation: list, score: float,
                         total_price: float, rank_pos: int, players: list):
    if not calculation_id:
        return
    formation_str = "-".join(str(x) for x in formation)
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO result_formations (calculation_id, formation, score, total_price, rank_pos) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (calculation_id, formation_str, score, total_price, rank_pos),
                )
                rf_id = cur.lastrowid
                for p in players:
                    cur.execute(
                        "INSERT INTO result_players (result_formation_id, player_name, position, price, value, start_probability) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (rf_id, p.get("name", ""), p.get("position", ""),
                         p.get("price", 0), p.get("value", 0), p.get("start_probability", 0)),
                    )
    except Exception as e:
        logger.error("log_result_formation failed: %s", e)


def log_player_action(session_id: str, player_name: str, competition: str, action_type: str):
    _enqueue(
        "INSERT INTO player_actions (session_id, player_name, competition, action_type) "
        "VALUES (%s, %s, %s, %s)",
        (session_id, player_name, competition, action_type),
    )


def log_feedback(email: str, message: str, lang: str = "es"):
    _enqueue(
        "INSERT INTO feedback (email, message, lang) VALUES (%s, %s, %s)",
        (email, message, lang),
    )


# ─── Init ────────────────────────────────────────────────────────────────────
def init():
    if not DB_ENABLED:
        logger.info("Database disabled (DB_HOST not set)")
        return
    logger.info("Connecting to MySQL at %s:%s/%s (SSL=%s)", _DB_HOST, _DB_PORT, _DB_NAME, _DB_SSL)
    try:
        _init_pool()
        _ensure_writer()
        logger.info("Database pool initialised (%d connections)", _pool.qsize())
    except Exception as e:
        logger.error("Database init failed: %s", e)
