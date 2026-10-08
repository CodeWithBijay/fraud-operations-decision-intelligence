-- ============================================================
-- Load Validated Version 1 Transaction Identity Data
-- ============================================================
--
-- Generated from transaction_identity.csv.
--
-- CSV columns: 41
-- PostgreSQL target columns: 41
--
-- Expected identity population: 144233 rows
--
-- Execute only when transaction_identity is empty.
--
-- ============================================================

\copy transaction_identity (transaction_id, id_01, id_02, id_03, id_04, id_05, id_06, id_07, id_08, id_09, id_10, id_11, id_12, id_13, id_14, id_15, id_16, id_17, id_18, id_19, id_20, id_21, id_22, id_23, id_24, id_25, id_26, id_27, id_28, id_29, id_30, id_31, id_32, id_33, id_34, id_35, id_36, id_37, id_38, device_type, device_info) FROM '/Users/bijay/Desktop/fraud-risk-project/data/generated/final/transaction_identity.csv' WITH (FORMAT csv, HEADER true)
