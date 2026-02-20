-- ═══════════════════════════════════════════════════════════════════════════
-- Calculadora Fantasy – MySQL Database Schema
-- Compatible with: Aiven MySQL, Oracle Cloud Free Tier, PlanetScale, etc.
-- ═══════════════════════════════════════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS calculadora_fantasy
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE calculadora_fantasy;

-- ─── Page visits / analytics ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS visits (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  session_id  VARCHAR(64)   NOT NULL,
  page        VARCHAR(50)   NOT NULL DEFAULT 'app',  -- 'landing', 'app'
  lang        CHAR(2)       NOT NULL DEFAULT 'es',
  user_agent  TEXT,
  ip_hash     VARCHAR(64),   -- SHA-256 hash of IP (GDPR-friendly)
  referrer    VARCHAR(512),
  created_at  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_created (created_at),
  INDEX idx_session (session_id)
) ENGINE=InnoDB;

-- ─── Calculation events ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS calculations (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  session_id      VARCHAR(64)   NOT NULL,
  calc_type       VARCHAR(20)   NOT NULL,  -- 'budget', 'my11'
  competition     VARCHAR(30)   NOT NULL,
  app_source      VARCHAR(20)   NOT NULL,  -- 'biwenger', 'laligafantasy'
  budget          INT,
  num_formations  INT,
  num_players     INT,
  blinded_count   INT           DEFAULT 0,
  banned_count    INT           DEFAULT 0,
  duration_ms     INT,          -- how long the calculation took
  created_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_created (created_at),
  INDEX idx_competition (competition)
) ENGINE=InnoDB;

-- ─── Popular player searches (anonymised) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS player_searches (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  player_name VARCHAR(100)  NOT NULL,
  competition VARCHAR(30)   NOT NULL,
  search_type VARCHAR(20)   NOT NULL,  -- 'blinded', 'banned', 'my11', 'market'
  created_at  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_player (player_name),
  INDEX idx_created (created_at)
) ENGINE=InnoDB;

-- ─── User feedback (optional contact form) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS feedback (
  id         BIGINT AUTO_INCREMENT PRIMARY KEY,
  email      VARCHAR(255),
  message    TEXT          NOT NULL,
  lang       CHAR(2)       DEFAULT 'es',
  created_at TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ─── Daily aggregated stats (for dashboards) ────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_stats (
  stat_date       DATE         NOT NULL,
  total_visits    INT          DEFAULT 0,
  unique_sessions INT          DEFAULT 0,
  calculations    INT          DEFAULT 0,
  top_competition VARCHAR(30),
  top_app         VARCHAR(20),
  PRIMARY KEY (stat_date)
) ENGINE=InnoDB;
