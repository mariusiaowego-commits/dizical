-- dizical MySQL Schema (从 SQLite 自动转换)
-- 生成时间: extract_schema.py
-- 来源 DB: /Users/mt16/dev/dizical/data/dizi.db
-- 表数: 14, 索引数: 9

SET FOREIGN_KEY_CHECKS=0;

DROP TABLE IF EXISTS `achievement_badges`;
CREATE TABLE achievement_badges (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    achievement_id  TEXT NOT NULL,
    url             TEXT NOT NULL,
    is_locked       BIGINT NOT NULL DEFAULT 0,
    version         BIGINT NOT NULL DEFAULT 1,
    is_current      BIGINT NOT NULL DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS `achievement_stats`;
CREATE TABLE achievement_stats (
    achievement_id VARCHAR(255) PRIMARY KEY,
    achieved       TEXT NOT NULL ,
    achieved_at    DATETIME,
    raw_stats      TEXT NOT NULL ,
    computed_value BIGINT
);

DROP TABLE IF EXISTS `achievements`;
CREATE TABLE achievements (
    id                VARCHAR(255) PRIMARY KEY,
    name              TEXT NOT NULL,
    type              TEXT NOT NULL,
    category          TEXT NOT NULL ,
    stat_logic        TEXT NOT NULL,
    description       TEXT NOT NULL,
    display_format    TEXT NOT NULL,
    threshold         BIGINT,
    unlocked_template TEXT,
    placeholder       TEXT,
    locked_template   TEXT,
    sort_order        BIGINT DEFAULT 0,
    seasonal_type     TEXT,
    cond_text         TEXT,
    unlock_strategy   TEXT,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
, achieved_at_override TEXT, display_on_achievements BIGINT DEFAULT 1, sort_order_override BIGINT);

DROP TABLE IF EXISTS `daily_practices`;
CREATE TABLE daily_practices (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    date DATE NOT NULL UNIQUE,
                    items TEXT NOT NULL ,
                    total_minutes BIGINT NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                , log TEXT, practiced TEXT NOT NULL , behavior_log TEXT NOT NULL , practice_at DATETIME);

DROP TABLE IF EXISTS `lessons`;
CREATE TABLE lessons (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    date DATE NOT NULL,
                    time TIME NOT NULL,
                    `status` TEXT NOT NULL ,
                    fee BIGINT NOT NULL DEFAULT 600,
                    fee_paid TINYINT(1) NOT NULL DEFAULT 0,
                    is_holiday_conflict TINYINT(1) NOT NULL DEFAULT 0,
                    notes TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

DROP TABLE IF EXISTS `payments`;
CREATE TABLE payments (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    payment_date DATE NOT NULL,
                    amount BIGINT NOT NULL,
                    lesson_ids TEXT NOT NULL ,
                    payment_method TEXT NOT NULL ,
                    notes TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

DROP TABLE IF EXISTS `practice_audit_log`;
CREATE TABLE practice_audit_log (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    channel TEXT NOT NULL,
                    method TEXT NOT NULL,
                    practice_date DATE NOT NULL,
                    input_items JSON,
                    result_items JSON,
                    total_minutes BIGINT,
                    session_id TEXT,
                    error TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

DROP TABLE IF EXISTS `practice_categories`;
CREATE TABLE practice_categories (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    sort_order BIGINT NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

DROP TABLE IF EXISTS `practice_items`;
CREATE TABLE `practice_items` (
            item_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            category_id BIGINT REFERENCES practice_categories(id),
            sort_order BIGINT NOT NULL DEFAULT 0,
            is_active TINYINT(1) NOT NULL DEFAULT 1,
            is_archived TINYINT(1) NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        , last_tempo_note TEXT, last_tempo_bpm BIGINT, last_session_at DATETIME, content_options TEXT);

DROP TABLE IF EXISTS `practice_reports`;
CREATE TABLE practice_reports (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  year BIGINT NOT NULL,
  month BIGINT NOT NULL,
  style TEXT NOT NULL ,
  prompt TEXT,
  image_path TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS `practice_sessions`;
CREATE TABLE practice_sessions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    practice_date DATE NOT NULL,
    item_id BIGINT NOT NULL,
    item_name TEXT NOT NULL,
    duration_minutes BIGINT NOT NULL,
    tempo_note TEXT NOT NULL ,
    tempo_bpm BIGINT NOT NULL DEFAULT 80,
    content TEXT NOT NULL ,
    content_source TEXT NOT NULL ,
    is_extra TINYINT(1) NOT NULL DEFAULT 0,
    started_at TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES practice_items(item_id)
);

DROP TABLE IF EXISTS `schema_migrations`;
CREATE TABLE schema_migrations (
                    version BIGINT PRIMARY KEY,
                    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

DROP TABLE IF EXISTS `settings`;
CREATE TABLE settings (
                    `key` VARCHAR(255) PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

DROP TABLE IF EXISTS `weekly_assignments`;
CREATE TABLE `weekly_assignments` (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    lesson_date DATE NOT NULL,
    stage_start DATE NOT NULL,
    stage_end DATE,
    items TEXT NOT NULL,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    images TEXT
, stage_order BIGINT);

-- SKIP: CREATE INDEX idx_assignments_lesson ON weekly_assignments(lesson_date)  (col lesson_date is TEXT, MySQL 5.7 索引需前缀长度, 业务允许跳过);
-- SKIP: CREATE INDEX idx_assignments_stage ON weekly_assignments(stage_start)  (col stage_start is TEXT, MySQL 5.7 索引需前缀长度, 业务允许跳过);
-- SKIP: CREATE INDEX idx_assignments_week ON weekly_assignments(lesson_date)  (col lesson_date is TEXT, MySQL 5.7 索引需前缀长度, 业务允许跳过);
-- SKIP: CREATE INDEX idx_audit_channel ON practice_audit_log(channel)  (col channel is TEXT, MySQL 5.7 索引需前缀长度, 业务允许跳过);
-- SKIP: CREATE INDEX idx_audit_date ON practice_audit_log(practice_date)  (col practice_date is TEXT, MySQL 5.7 索引需前缀长度, 业务允许跳过);
-- SKIP: CREATE INDEX idx_lessons_date ON lessons(date)  (col date is TEXT, MySQL 5.7 索引需前缀长度, 业务允许跳过);
-- SKIP: CREATE INDEX idx_practice_sessions_date ON practice_sessions(practice_date)  (col practice_date is TEXT, MySQL 5.7 索引需前缀长度, 业务允许跳过);
CREATE INDEX idx_practice_sessions_item_date ON practice_sessions(item_id, practice_date);
-- SKIP: CREATE INDEX idx_practices_date ON daily_practices(date)  (col date is TEXT, MySQL 5.7 索引需前缀长度, 业务允许跳过);
SET FOREIGN_KEY_CHECKS=1;
