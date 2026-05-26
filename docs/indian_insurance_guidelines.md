# Indian Health Insurance Claim Auditing Guidelines & Pass Probability Framework

This education guide details the specific rules, capping limits, and regulatory constraints for major Indian health insurance companies (**Bajaj Allianz**, **Aditya Birla Health**, and **ICICI Lombard**). It establishes the standard clinical auditing checkpoints and defines the **Claim Approval Probability scoring algorithm** used by the AI Agent to evaluate claim pass rates.

---

## 🏢 1. Major Indian Insurance Provider Guidelines

### A. Bajaj Allianz Health Insurance
* **Room Rent Capping**: Standard room rent is capped at **1% of the Sum Insured** per day for normal rooms, and **2% of the Sum Insured** for ICU rooms.
  * *Proportionate Deduction*: If the room rent category selected by the patient exceeds this limit, Bajaj Allianz applies proportionate deductions to the entire hospital bill (e.g., if room rent is exceeded by 20%, all associated doctor consultations and nursing fees are also reduced by 20%).
* **Cashless pre-auth**: Cashless authorization requests must be submitted within 24 hours of emergency admission or 48 hours prior to planned admission.

### B. Aditya Birla Health Insurance (Active Health Policy)
* **Chronic Management Program**: Provides up to 100% "HealthReturns" for active wellness. However, chronic conditions (asthma, hypertension, diabetes) have a strict **24-month waiting period** for Pre-Existing Diseases (PED).
* **Zonal Copay**: Applies a **10% to 20% co-pay** if a policy purchased in a Zone II (non-metro) city is used in a Zone I (metro e.g., Mumbai, Delhi, Bangalore) hospital.

### C. ICICI Lombard General Insurance
* **Pre-Existing Disease (PED) Waiting Period**: Strict **36-month waiting period** for all pre-existing chronic conditions. Any clinical note indicating a history of the diagnosed condition prior to policy issuance leads to claim denial.
* **Network Hospital Cashless**: Requires treatment at an **ICICI Network Hospital** for cashless claims; otherwise, the patient must pay out-of-pocket and submit a reimbursement claim (which undergoes 30-day manual clinical auditing).

---

## 🔍 2. Clinical Auditing Checkpoints

When auditing an Indian health claim, the agent verifies:
1. **ICD-10 to CPT Mapping**: Do diagnostic codes (ICD-10) align with the billing treatment codes (CPT)?
2. **Room Rent Limit Validation**: Is the room rate billed within the 1% normal / 2% ICU sum insured cap?
3. **Clinical Log Disclosures**: Do the clinical notes mention any chronic history (hypertension, asthma, diabetes) indicating an undeclared Pre-Existing Disease (PED)?
4. **Pre-Authorization Match**: Does the CPT code on the hospital bill match the pre-authorized CPT code approved by the TPA (Third Party Administrator)?
5. **Supporting Reports Check**: Are diagnostic reports present in the patient record folder for high-value billing line items (e.g., EKG reports for CPT 93000, X-Ray sheets for CPT 71045)?

---

## 📊 3. Claim Approval Probability Scoring Algorithm

To compute the **Claim Pass Probability (0% - 100%)**, the agent begins at **100%** and applies deductions for clinical or administrative discrepancies found in the patient folder:

| Deduction | Penalty | Auditing Trigger |
| :--- | :--- | :--- |
| **Room Rent Violation** | **-20%** | Billed room rent exceeds the policy's 1% normal / 2% ICU sum insured capping limit. |
| **Pre-Existing Disease Waiting Period** | **-35%** | Clinical logs reveal a history of a chronic diagnosis (e.g., asthma, cardiac disease) within the 24/36-month Waiting Period. |
| **Coding Incongruence** | **-15%** | Billed CPT treatment procedure is not clinically justified by the patient's ICD-10 diagnostic codes. |
| **Non-Network Hospital Cashless** | **-15%** | Cashless claim submitted for a hospital marked as Non-Network for the selected provider. |
| **Missing Diagnostic Proof** | **-10%** | High-value procedures (e.g., chest X-ray or ECG billing line items) lack clinical mention or diagnostic proof in the record logs. |
| **Missing Pre-Auth Code** | **-5%** | Cashless claim has no pre-authorized reference number or pre-auth CPT code mismatches. |

### Probability Ranges & Recommendations:
* **85% - 100% (HIGH PROBABILITY)**: Claim is fully compliant. Recommended for instant cashless clearance.
* **60% - 84% (MODERATE RISK / CONDITIONAL PASS)**: Minor discrepancies (e.g., room rent limit exceeded or missing report). Approved with deductions or pending report submission.
* **Below 60% (HIGH RISK / LIKELY REJECTION)**: Severe issues (e.g., pre-existing disease history discovered within the waiting period or non-network cashless attempt). Recommended for rejection or referral to TPA audit.
