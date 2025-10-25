CREATE TABLE IF NOT EXISTS pnl_snapshots (
    id SERIAL PRIMARY KEY,
    model VARCHAR(50) NOT NULL,
    pnl DECIMAL(20, 8) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_model_timestamp UNIQUE (model, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_pnl_snapshots_model ON pnl_snapshots(model);
CREATE INDEX IF NOT EXISTS idx_pnl_snapshots_timestamp ON pnl_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_pnl_snapshots_model_timestamp ON pnl_snapshots(model, timestamp);
