-- v2.10 (13 Eylül 2026): güvenlik günlüğü (security audit trail).
-- Prod'da elle: docker exec -i nexstream_db psql -U nexstream -d nexstream < migrations/v2_10_security_events.sql
-- Dev'de create_all otomatik oluşturur.

CREATE TABLE IF NOT EXISTS security_events (
    id          SERIAL PRIMARY KEY,
    category    VARCHAR(16)  NOT NULL,
    event_type  VARCHAR(40)  NOT NULL,
    email       VARCHAR(255),
    user_id     INTEGER,
    ip          VARCHAR(64),
    user_agent  VARCHAR(256),
    request_id  VARCHAR(64),
    path        VARCHAR(255),
    detail      VARCHAR(500),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_security_events_email      ON security_events (email);
CREATE INDEX IF NOT EXISTS ix_security_events_ip         ON security_events (ip);
CREATE INDEX IF NOT EXISTS ix_security_events_created_at ON security_events (created_at);
CREATE INDEX IF NOT EXISTS ix_security_events_event_type ON security_events (event_type);
