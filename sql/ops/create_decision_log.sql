-- Records each Fraud Ops decision made in the app (workflow + audit trail).
-- decided_at is a wall-clock audit timestamp, not simulated time.
CREATE TABLE IF NOT EXISTS ops_decision_log (
    decision_id    BIGSERIAL PRIMARY KEY,
    transaction_id BIGINT  NOT NULL REFERENCES transaction (transaction_id),
    sim_day        INTEGER NOT NULL,
    policy_code    TEXT    NOT NULL CHECK (policy_code IN ('P0', 'P1', 'P2')),
    queue_rank     INTEGER NOT NULL CHECK (queue_rank > 0),
    capacity       INTEGER NOT NULL CHECK (capacity > 0),
    action         TEXT    NOT NULL CHECK (action IN
                     ('ASSIGN_REVIEW', 'CONFIRM_FRAUD', 'CLEAR_LEGITIMATE', 'ESCALATE', 'DEFER')),
    analyst_name   TEXT    NOT NULL,
    note           TEXT,
    decided_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_odl_txn ON ops_decision_log (transaction_id);
CREATE INDEX IF NOT EXISTS idx_odl_day ON ops_decision_log (sim_day);
