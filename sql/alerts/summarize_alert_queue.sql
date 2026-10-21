-- 1. Rule thresholds actually used
SELECT rule_code, rule_name, rule_text, ROUND(threshold, 4) AS threshold, basis
FROM alert_rule_config ORDER BY rule_code;

-- 2. Alert volume
SELECT COUNT(*) AS total_alerts,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM transaction), 2) AS pct_of_transactions,
       COUNT(DISTINCT sim_day) AS days
FROM alert_queue;

-- 3. Alerts per simulated day
SELECT MIN(n) AS min_per_day, ROUND(AVG(n), 1) AS avg_per_day, MAX(n) AS max_per_day
FROM (SELECT sim_day, COUNT(*) AS n FROM alert_queue GROUP BY sim_day) d;

-- 4. How often each rule fires inside alerts
SELECT SUM(r1_velocity::int) AS r1, SUM(r2_amount_spike::int) AS r2,
       SUM(r3_rapid_repeat::int) AS r3, SUM(r4_new_customer::int) AS r4,
       SUM(r5_large_amount::int) AS r5, SUM(r6_new_device::int) AS r6
FROM alert_queue;

-- 5. Retrospective check ONLY (label used for evaluation, never for scoring)
SELECT ROUND(100.0 * AVG(t.is_fraud::int), 2) AS fraud_rate_in_alerts_pct,
       (SELECT ROUND(100.0 * AVG(is_fraud::int), 2) FROM transaction) AS overall_fraud_rate_pct,
       ROUND(100.0 * SUM(t.is_fraud::int) / (SELECT SUM(is_fraud::int) FROM transaction), 2) AS pct_of_all_fraud_alerted
FROM alert_queue a JOIN transaction t USING (transaction_id);
