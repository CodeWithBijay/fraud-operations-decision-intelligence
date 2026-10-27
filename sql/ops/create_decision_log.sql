-- Records each Fraud Ops decision made in the app (workflow + audit trail).
-- decided_at is a wall-clock audit timestamp, not simulated time.
-- Safe to run repeatedly: the app runs this file every time it starts.
CREATE TABLE IF NOT EXISTS ops_decision_log (
    decision_id    BIGSERIAL PRIMARY KEY,
    transaction_id BIGINT  NOT NULL REFERENCES transaction (transaction_id),
    sim_day        INTEGER NOT NULL,
    policy_code    TEXT    NOT NULL,
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

-- Week 10: model-based queue policies P3 and P4 are now allowed.
ALTER TABLE ops_decision_log DROP CONSTRAINT IF EXISTS ops_decision_log_policy_code_check;
ALTER TABLE ops_decision_log ADD CONSTRAINT ops_decision_log_policy_code_check
    CHECK (policy_code IN ('P0', 'P1', 'P2', 'P3', 'P4'));
