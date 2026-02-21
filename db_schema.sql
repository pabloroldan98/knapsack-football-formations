-- ═══════════════════════════════════════════════════════════════════════════
-- Calculadora Fantasy – MySQL Database Schema
-- Compatible with: Aiven MySQL, Oracle Cloud Free Tier, etc.
-- ═══════════════════════════════════════════════════════════════════════════

-- NOTE: On Aiven free tier the DB is called 'defaultdb'. Don't CREATE DATABASE.
-- If using a custom DB name, uncomment the next two lines:
-- CREATE DATABASE IF NOT EXISTS calculadora_fantasy
--   CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE calculadora_fantasy;

-- ─── Page visits / analytics ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS visits (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  session_id  VARCHAR(64)   NOT NULL,
  page        VARCHAR(50)   NOT NULL DEFAULT 'app',  -- 'landing', 'app'
  lang        CHAR(2)       NOT NULL DEFAULT 'es',
  user_agent  TEXT,
  ip_hash     VARCHAR(64),   -- SHA-256 hash of IP (GDPR-friendly)
  referrer    VARCHAR(512),
  screen_w    SMALLINT,
  screen_h    SMALLINT,
  created_at  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_created (created_at),
  INDEX idx_session (session_id)
) ENGINE=InnoDB;

-- ─── Settings snapshot: what sidebar options the user had when loading players ─
CREATE TABLE IF NOT EXISTS player_loads (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  session_id      VARCHAR(64)   NOT NULL,
  competition     VARCHAR(30)   NOT NULL,
  app_source      VARCHAR(20)   NOT NULL,  -- 'biwenger', 'laligafantasy'
  jornada_key     VARCHAR(60),
  num_jornadas    TINYINT       DEFAULT 1,
  ignore_form     BOOLEAN       DEFAULT FALSE,
  ignore_fixtures BOOLEAN       DEFAULT FALSE,
  ignore_penalties BOOLEAN      DEFAULT FALSE,
  players_loaded  INT,
  created_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_created (created_at),
  INDEX idx_competition (competition)
) ENGINE=InnoDB;

-- ─── Calculation events ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS calculations (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  session_id      VARCHAR(64)   NOT NULL,
  calc_type       VARCHAR(20)   NOT NULL,  -- 'budget', 'my11'
  competition     VARCHAR(30)   NOT NULL,
  app_source      VARCHAR(20)   NOT NULL,
  budget          INT,
  formations_in   VARCHAR(200),            -- JSON array of formations requested
  formations_out  TINYINT,                 -- number of valid results returned
  num_players     INT,                     -- players considered after filters
  blinded_count   TINYINT       DEFAULT 0,
  banned_count    TINYINT       DEFAULT 0,
  min_prob        FLOAT,
  speed_up        BOOLEAN       DEFAULT TRUE,
  duration_ms     INT,
  created_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_created (created_at),
  INDEX idx_competition (competition)
) ENGINE=InnoDB;

-- ─── Player interactions (blinded/banned/my11/market) ─────────────────────
CREATE TABLE IF NOT EXISTS player_actions (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  session_id  VARCHAR(64),
  player_name VARCHAR(100)  NOT NULL,
  competition VARCHAR(30)   NOT NULL,
  action_type VARCHAR(20)   NOT NULL,  -- 'blinded', 'banned', 'my11', 'market'
  created_at  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_player (player_name),
  INDEX idx_created (created_at)
) ENGINE=InnoDB;

-- ─── Results: which formations/players appear in results most ─────────────
CREATE TABLE IF NOT EXISTS result_formations (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  calculation_id  BIGINT        NOT NULL,
  formation       VARCHAR(20)   NOT NULL,  -- e.g. '4-4-2'
  score           FLOAT,
  total_price     FLOAT,
  rank_pos        TINYINT,                 -- 1 = best, 2 = second, etc.
  created_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_calc (calculation_id),
  INDEX idx_formation (formation)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS result_players (
  id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
  result_formation_id BIGINT        NOT NULL,
  player_name         VARCHAR(100)  NOT NULL,
  position            VARCHAR(5)    NOT NULL,
  price               FLOAT,
  value               FLOAT,
  created_at          TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_formation (result_formation_id),
  INDEX idx_player (player_name)
) ENGINE=InnoDB;

-- ─── User feedback (optional contact form) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS feedback (
  id         BIGINT AUTO_INCREMENT PRIMARY KEY,
  email      VARCHAR(255),
  message    TEXT          NOT NULL,
  lang       CHAR(2)       DEFAULT 'es',
  created_at TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ─── Daily aggregated stats (for dashboards, populated by a cron/script) ────
CREATE TABLE IF NOT EXISTS daily_stats (
  stat_date         DATE         NOT NULL,
  total_visits      INT          DEFAULT 0,
  unique_sessions   INT          DEFAULT 0,
  total_calculations INT         DEFAULT 0,
  total_player_loads INT         DEFAULT 0,
  top_competition   VARCHAR(30),
  top_app           VARCHAR(20),
  avg_calc_duration_ms INT,
  PRIMARY KEY (stat_date)
) ENGINE=InnoDB;
