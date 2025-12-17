# Data Dictionary

## Dataset Overview

- **Source**: `outputs/data/claims_clean.csv`
- **Rows**: 1,000
- **Columns**: 15
- **Grain**: One row per claim (unique Claim ID).

## Column Details

| Column | Type | % Missing | Example Values |
|---|---|---:|---|
| Claim ID | string | 0.0% | 0HO1FSN4AP; 9U86CI2P5A; 1QEU1AIDAU |
| Provider ID | integer | 0.0% | 126528997; 6986719948; 1355108115 |
| Patient ID | integer | 0.0% | 7936697103; 1547160031; 2611585318 |
| Date of Service | string | 0.0% | 2024-08-07; 2024-06-21; 2024-07-04 |
| Billed Amount | integer | 0.0% | 304; 348; 235 |
| Procedure Code | integer | 0.0% | 99231; 99213; 99213 |
| Diagnosis Code | string | 0.0% | A02.1; A16.5; A00.1 |
| Allowed Amount | integer | 0.0% | 218; 216; 148 |
| Paid Amount | integer | 0.0% | 203; 206; 119 |
| Insurance Type | string | 0.0% | Self-Pay; Medicare; Commercial |
| Claim Status | string | 0.0% | Paid; Paid; Under Review |
| Reason Code | string | 0.0% | Incorrect billing information; Pre-existing condition; Duplicate claim |
| Follow-up Required | string | 0.0% | Yes; Yes; No |
| AR Status | string | 0.0% | Pending; Open; Denied |
| Outcome | string | 0.0% | Partially Paid; Denied; Denied |

## Assumptions & Notes

- **Cleaning applied**: Rows with missing `Billed Amount` removed; records with `Billed Amount ≤ 0` removed.
- **Date parsing**: `Date of Service` parsed to datetime; unparseable dates are dropped.
- **Scope**: This is synthetic data from Kaggle (no PHI concerns).
- **Real data considerations**: For production, add PII handling, HIPAA audit trails, and data lineage.
