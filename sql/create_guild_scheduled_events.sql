CREATE TABLE IF NOT EXISTS guild_scheduled_events (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    event_type ENUM('platoons', 'deployments') NOT NULL,
    daytime TIME NOT NULL,
    guild_id VARCHAR(64) NOT NULL,
    channel_id BIGINT UNSIGNED NOT NULL,
    last_run_date DATE DEFAULT NULL,
    last_run_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_guild_scheduled_event (event_type, daytime, guild_id, channel_id),
    KEY idx_guild_scheduled_events_due (daytime, last_run_date),
    KEY idx_guild_scheduled_events_guild (guild_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
