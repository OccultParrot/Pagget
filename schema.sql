BEGIN;

DROP TABLE IF EXISTS afflictions;
DROP TABLE IF EXISTS berries;
DROP TABLE IF EXISTS gather_outcomes;
DROP TABLE IF EXISTS servers;
DROP TYPE IF EXISTS rarity;
DROP TYPE IF EXISTS season;

CREATE TYPE rarity AS ENUM ('common', 'uncommon', 'rare', 'legendary');
CREATE TYPE season AS ENUM ('spring', 'summer', 'fall', 'winter');

CREATE TABLE servers
(
    id                      BIGINT PRIMARY KEY,
    name                    TEXT  NOT NULL,
    affliction_chance       FLOAT NOT NULL DEFAULT .25,
    minor_affliction_chance FLOAT NOT NULL DEFAULT .35,
    starting_pay            INT   NOT NULL DEFAULT 100,
    minimum_bet             INT   NOT NULL DEFAULT 100,
    created_at              TIMESTAMPTZ    DEFAULT NOW(),
    updated_at              TIMESTAMPTZ    DEFAULT NOW()
);

CREATE TABLE afflictions
(
    id              SERIAL PRIMARY KEY,
    server_id       BIGINT  NOT NULL REFERENCES servers (id) ON DELETE CASCADE,
    title           TEXT    NOT NULL,
    description     TEXT    NOT NULL,
    rarity          rarity  NOT NULL,
    is_minor        BOOLEAN NOT NULL DEFAULT FALSE,
    is_birth_defect BOOLEAN NOT NULL DEFAULT FALSE,
    seasons         season[],
    created_at      TIMESTAMPTZ      DEFAULT NOW(),
    updated_at      TIMESTAMPTZ      DEFAULT NOW()
);

CREATE TABLE berries
(
    id         BIGINT PRIMARY KEY,
    server_id  BIGINT NOT NULL REFERENCES servers (id) ON DELETE CASCADE,
    balance    BIGINT      DEFAULT 0 CHECK ( balance >= 0 ),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE gather_outcomes
(
    id          SERIAL PRIMARY KEY,
    server_id   BIGINT  NOT NULL REFERENCES servers (id) ON DELETE CASCADE,
    is_robbery  BOOLEAN NOT NULL DEFAULT FALSE,
    value       INT     NOT NULL DEFAULT 0,
    description TEXT    NOT NULL,
    rarity      rarity  NOT NULL
);

CREATE INDEX idx_afflictions_server_id ON afflictions (server_id);
CREATE INDEX idx_berries_server_id ON berries (server_id);
CREATE INDEX idx_gather_outcomes_id ON gather_outcomes (server_id);

COMMIT;