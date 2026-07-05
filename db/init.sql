CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS scores (
    id SERIAL PRIMARY KEY,
    player_id INT REFERENCES players(id),
    reaction_time_ms INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
