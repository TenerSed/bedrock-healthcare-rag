# Document 3: Common Medical Terminology and Clinical Classifications

## 1. Overview and Purpose

This document describes common medical terminology, core clinical classifications, and frequently used numeric ranges needed for an LLM to interpret and reason over healthcare data in electronic health records (EHRs), claims data, and clinical notes. It focuses on:

- Diagnostic and procedural coding systems.
- Clinical measurements like vital signs and laboratory values.
- Common disease entities, their presentations, and staging systems.
- Standard clinical abbreviations and note structures.

The goal is to give a model enough structure and context to map free-text clinical language and coded data into consistent internal representations for retrieval, summarization, and decision-support in a HIPAA-compliant environment.

---

## 2. Coding Systems and Clinical Classifications

### 2.1 ICD-10-CM Diagnostic Coding

The International Classification of Diseases, 10th Revision, Clinical Modification (ICD‑10‑CM), is the standard system used in the United States for coding diagnoses in inpatient and outpatient settings.

**Key properties:**

- Used for:
  - Diagnoses and conditions (not procedures).
  - Billing, epidemiology, quality metrics, and risk adjustment.
- Structure:
  - 3–7 characters, alphanumeric.
  - Character 1: letter (A–Z, excluding U).
  - Character 2: digit (0–9).
  - Character 3: digit (0–9), often followed by a decimal point.
  - Characters 4–7: letters or digits, increasing specificity (laterality, acuity, episode of care, etc.).

**Example ICD‑10‑CM codes:**

- E11.9 – Type 2 diabetes mellitus without complications.
- I10 – Essential (primary) hypertension.
- I50.9 – Heart failure, unspecified.
- J44.9 – Chronic obstructive pulmonary disease, unspecified.
- N18.4 – Chronic kidney disease, stage 4 (severe).
- I63.9 – Cerebral infarction, unspecified.

**High-level ICD‑10‑CM chapter groupings:**

- A00–B99: Certain infectious and parasitic diseases.
- C00–D49: Neoplasms (benign and malignant tumors).
- E00–E89: Endocrine, nutritional and metabolic diseases (e.g., diabetes, thyroid disorders).
- I00–I99: Diseases of the circulatory system (e.g., hypertension, heart failure, myocardial infarction).
- J00–J99: Diseases of the respiratory system (e.g., COPD, pneumonia, asthma).
- M00–M99: Diseases of the musculoskeletal system and connective tissue.
- N00–N99: Diseases of the genitourinary system.
- O00–O9A: Pregnancy, childbirth and the puerperium.
- P00–P96: Conditions originating in the perinatal period.
- Q00–Q99: Congenital malformations, deformations and chromosomal abnormalities.
- R00–R99: Symptoms, signs and abnormal clinical and laboratory findings (e.g., chest pain, abnormal lab results).
- V00–Y99: External causes of morbidity (e.g., accidents, assaults).
- Z00–Z99: Factors influencing health status and contact with health services (e.g., routine exams, family history).

**LLM considerations:**

- ICD codes are often stored as:
  - Pure code: `E11.9`.
  - Code + text: `E11.9 – Type 2 diabetes mellitus without complications`.
- Codes may appear with or without decimals (e.g., `I10` vs `I10.`).
- When mapping narrative text to ICD‑10, the model should:
  - Look for descriptors of acuity (acute, chronic), laterality (left/right), site, and complications.
  - Understand that `R` codes represent symptoms when a definitive diagnosis is absent.

---

### 2.2 ICD-10-PCS (Inpatient Procedures, US)

ICD‑10‑PCS is used in the US for coding inpatient procedures (not diagnoses) in hospital settings.

**Key properties:**

- 7 characters, all alphanumeric (no decimal).
- Each character has a specific meaning (section, body system, root operation, body part, approach, device, qualifier).
- Used mainly for:
  - Inpatient hospital billing and quality reporting.
  - Not typically used in office/outpatient settings (where CPT is used).

**Example ICD‑10‑PCS procedures:**

- 0DTJ4ZZ – Resection of appendix, percutaneous endoscopic approach.
- 02703ZZ – Dilation of coronary artery, one site, percutaneous approach.

For LLMs, the presence of ICD‑10‑PCS usually means the underlying data is inpatient and highly structured, but clinicians rarely write these codes directly in notes.

---

### 2.3 CPT and HCPCS Codes (Procedures and Services)

**CPT (Current Procedural Terminology)** is the standard US system for coding outpatient procedures, office visits, and many diagnostic tests.

- Examples:
  - 99213 – Office or other outpatient visit for the evaluation and management of an established patient, low complexity.
  - 93000 – Electrocardiogram (ECG) with interpretation and report.
  - 71045 – Chest X‑ray, single view.

**HCPCS (Healthcare Common Procedure Coding System)** extends CPT with additional codes, especially for supplies, medications, and non‑physician services.

- Level II HCPCS examples:
  - J3490 – Unclassified drugs.
  - A0429 – Ambulance service, basic life support, emergency.

LLM mapping:

- CPT/HCPCS codes frequently co‑occur with ICD‑10 codes in claims data.
- Codes may be a key to the *type* of encounter (e.g., evaluation and management vs procedure) and help infer context for vitals, labs, and diagnoses.

---

### 2.4 SNOMED CT (Clinical Concepts Ontology)

SNOMED CT is a comprehensive, hierarchically structured clinical terminology used to represent detailed clinical concepts beyond billing.

**Key characteristics:**

- Concepts are represented by numeric identifiers (e.g., `44054006` for diabetes mellitus).
- Each concept has:
  - Preferred term (e.g., “Type 2 diabetes mellitus”).
  - Synonyms.
  - Relationships to other concepts (e.g., “is a”, “finding site”, “associated morphology”).

**Uses:**

- Problem lists, allergies, findings, procedures, body structures, and organisms.
- Decision support rules and interoperability (e.g., FHIR Condition resources often use SNOMED codes).

LLM mapping:

- Same clinical idea may have:
  - SNOMED CT for conditions / findings.
  - ICD‑10‑CM for billing.
  - CPT for procedures.
- An LLM should treat SNOMED CT as a more granular clinical semantic layer and ICD‑10 as billing-focused; mapping tables often exist between them.

---

### 2.5 LOINC (Laboratory and Observation Identifiers)

LOINC (Logical Observation Identifiers Names and Codes) standardizes codes for laboratory tests and clinical observations.

**Key points:**

- Each lab test or measurement has a unique LOINC code:
  - Example: `718-7` – Hemoglobin [Mass/volume] in Blood.
  - Example: `2345-7` – Glucose [Mass/volume] in Serum or Plasma.
- LOINC encodes:
  - Analyte (what is measured).
  - Property (e.g., mass concentration).
  - Timing (point vs 24‑hour).
  - System (e.g., blood, serum, urine).
  - Scale (quantitative/ordinal).
  - Method (if relevant).

LLM mapping:

- Labs may be present as either:
  - Local test names (e.g., “Glucose Serum”).
  - Standard LOINC codes (e.g., `2345-7`).
- Normal ranges vary by lab, patient age, sex, and sometimes method; the model should treat ranges given in the dataset as authoritative when provided.

---

### 2.6 FHIR Resource Naming and Common Fields

Many modern systems expose data using HL7 FHIR (Fast Healthcare Interoperability Resources).

**Common resources:**

- `Patient`: demographics, identifiers, administrative info.
- `Encounter`: context of a visit (inpatient, outpatient, ED).
- `Observation`: lab results, vitals, some clinical measurements.
- `Condition`: problems and diagnoses.
- `Procedure`: procedures performed.
- `MedicationRequest` / `MedicationAdministration`: orders and administrations.
- `AllergyIntolerance`: documented allergies.

Key fields an LLM should understand:

- `code`: often coded with ICD‑10, SNOMED, LOINC, RxNorm, etc.
- `valueQuantity`: numeric value, unit, and system (e.g., UCUM units like `mg/dL`).
- `effectiveDateTime` / `issued`: timestamp for an observation.
- `status`: current / active / resolved.
- Linkages via `subject` (patient), `encounter`, `basedOn` (orders).

---

## 3. Laboratory Values and Interpretation

### 3.1 Reference Ranges and Units

Laboratory reference ranges vary slightly by lab and assay, but standard ranges provide a useful baseline.

#### Complete Blood Count (CBC)

- White blood cells (WBC): 4.5–11.0 × 10³ cells/µL.
- Red blood cells (RBC):
  - Males: 4.5–5.9 × 10⁶ cells/µL.
  - Females: 4.1–5.1 × 10⁶ cells/µL.
- Hemoglobin (Hgb):
  - Males: 13.5–17.5 g/dL.
  - Females: 12.0–15.5 g/dL.
- Hematocrit (Hct):
  - Males: ~38.8–50.0%.
  - Females: ~34.9–44.5%.
- Mean corpuscular volume (MCV): 80–100 fL.
- Platelets: 150–400 × 10³/µL.

**Interpretive anchors:**

- Low Hgb/Hct → anemia; high → polycythemia.
- Low platelets → thrombocytopenia (risk of bleeding).
- Elevated WBC → infection, inflammation, stress, or hematologic malignancy.

#### Basic and Comprehensive Metabolic Panels

- Glucose (fasting): 70–100 mg/dL.
- Blood urea nitrogen (BUN): 7–20 mg/dL.
- Creatinine:
  - Males: ~0.7–1.3 mg/dL.
  - Females: ~0.6–1.1 mg/dL.
- Sodium: 135–145 mEq/L.
- Potassium: 3.5–5.0 mEq/L.
- Chloride: 98–107 mEq/L.
- Bicarbonate (CO₂): 23–29 mEq/L.

- Estimated glomerular filtration rate (eGFR) is often reported and used to stage chronic kidney disease (CKD).

#### Liver Function Tests

- Alanine aminotransferase (ALT): ~7–35 U/L.
- Aspartate aminotransferase (AST): ~10–40 U/L.
- Alkaline phosphatase: ~30–120 U/L.
- Total bilirubin: 0.1–1.2 mg/dL.
- Albumin: 3.5–5.0 g/dL.

Patterns:

- AST/ALT elevation → hepatocellular injury.
- Alkaline phosphatase elevation → cholestasis, bone disease.
- Low albumin → chronic liver disease, malnutrition, nephrotic syndrome.

#### Cardiac Biomarkers

- Troponin I (high‑sensitivity, lab‑specific): commonly considered elevated above ~99th percentile reference (e.g., >0.04 ng/mL, but lab‑dependent).
- BNP: <100 pg/mL often considered within normal range; higher values suggest heart failure.
- Creatine kinase‑MB (CK‑MB): traditionally <5 ng/mL.

LLM considerations:

- Always respect lab‑provided reference ranges; treat numeric thresholds in data as more authoritative than generic ranges.
- Understand that units matter (`ng/mL` vs `pg/mL`, etc.).
- Acute vs chronic trends (rise/fall pattern) may matter more than a single static value.

---

### 3.2 Derived Scores and Ratios

Some labs are used to calculate risk scores or severity indices:

- eGFR: derived from creatinine, age, sex, and sometimes race; used to stage CKD.
- Anion gap: `Na – (Cl + HCO₃)`; elevation suggests metabolic acidosis.
- A/G ratio: albumin / globulin; altered in some liver and immune disorders.

An LLM processing EHR data should be able to:

- Identify when these are explicitly given vs must be inferred.
- Interpret “High”, “Low”, “Critical” flags that often accompany lab results.

---

## 4. Vital Signs and Clinical Context

### 4.1 Normal Vital Sign Ranges (Adults)

Approximate adult resting ranges:

- Blood pressure:
  - Normal: <120/80 mmHg.
  - Elevated / hypertensive ranges defined separately (see hypertension section).
- Heart rate:
  - 60–100 beats per minute (bpm) at rest.
- Respiratory rate:
  - 12–20 breaths per minute.
- Temperature:
  - 36.1–37.2 °C (97.0–99.0 °F).
- Oxygen saturation:
  - ≥95% on room air in healthy adults.

LLM considerations:

- Vital signs are time‑series; seeing trends is key (e.g., rising heart rate and fever suggest worsening infection).
- Age, pregnancy, and baseline chronic conditions may shift “normal” for a given patient.

---

### 4.2 Hypertension Classification

Commonly used thresholds (US adult):

- Normal: <120 systolic AND <80 diastolic (mmHg).
- Elevated: 120–129 systolic AND <80 diastolic.
- Stage 1 hypertension:
  - 130–139 systolic OR 80–89 diastolic.
- Stage 2 hypertension:
  - ≥140 systolic OR ≥90 diastolic.
- Hypertensive crisis (often flagged): ≥180 systolic and/or ≥120 diastolic, especially with symptoms.

These thresholds are used to interpret repeated measurements; a single high reading may not equal a diagnosis.

---

## 5. Common Diagnoses and Clinical Presentations

### 5.1 Type 2 Diabetes Mellitus

**Definition and pathophysiology:**

Type 2 diabetes mellitus (T2DM) is characterized by insulin resistance and progressive beta‑cell dysfunction, leading to chronic hyperglycemia.

**Diagnostic criteria (non‑pregnant adults):** any of the following, usually confirmed on repeat testing unless symptoms are classic:

- Fasting plasma glucose ≥126 mg/dL (no caloric intake for ≥8 hours).
- 2‑hour plasma glucose ≥200 mg/dL during a 75 g oral glucose tolerance test.
- HbA1c ≥6.5%.
- Random plasma glucose ≥200 mg/dL in a patient with classic symptoms of hyperglycemia or hyperglycemic crisis.

**Typical symptoms:**

- Polyuria, polydipsia, polyphagia.
- Unintentional weight loss (especially early).
- Fatigue, blurred vision.
- Recurrent infections (e.g., candidiasis, skin infections).

**Common chronic complications:**

- Microvascular:
  - Diabetic retinopathy (eye disease).
  - Diabetic nephropathy (kidney disease).
  - Diabetic neuropathy (peripheral, autonomic).
- Macrovascular:
  - Coronary artery disease, stroke, peripheral arterial disease.

**Relevant codes/examples:**

- ICD‑10‑CM:
  - E11.9 – Type 2 diabetes mellitus without complications.
  - E11.65 – Type 2 diabetes mellitus with hyperglycemia.
  - E11.22 – Type 2 diabetes mellitus with diabetic chronic kidney disease.

LLM hints:

- Look for labs: elevated fasting glucose, elevated HbA1c, use of metformin, insulin.
- Recognize synonyms: “T2DM”, “adult‐onset diabetes”, “non‑insulin dependent diabetes” (historical term).
- Track complications as distinct but related conditions.

---

### 5.2 Hypertension

**Definition:**

Hypertension is defined as sustained elevation of systemic arterial blood pressure, typically diagnosed after repeated measurements above threshold.

- Primary (essential) hypertension:
  - ~90–95% of adult cases; no single identifiable secondary cause.
- Secondary hypertension:
  - Due to kidney disease, endocrine disorders (hyperaldosteronism, pheochromocytoma, Cushing’s), medications, or sleep apnea.

**Clinical aspects:**

- Often asymptomatic (“silent”) until complications arise.
- Potential symptoms at high levels: headaches, visual changes, chest pain, shortness of breath, neurologic deficits (e.g., stroke).

**Complications:**

- Left ventricular hypertrophy, heart failure.
- Myocardial infarction, stroke, chronic kidney disease.
- Retinopathy.

**ICD‑10‑CM:**

- I10 – Essential (primary) hypertension.
- I11.0 – Hypertensive heart disease with heart failure.
- I12.0 – Hypertensive chronic kidney disease with stage 5 CKD or ESRD.

LLM mapping:

- Associate “on lisinopril, amlodipine” with underlying hypertension.
- Interpret repeated blood pressure measurements alongside diagnosis and medications.

---

### 5.3 Congestive Heart Failure (CHF)

**Definition:**

Heart failure is a clinical syndrome in which the heart is unable to pump sufficient blood to meet metabolic demands, or can only do so at elevated filling pressures.

**Types:**

- HFrEF (Heart Failure with Reduced Ejection Fraction):
  - LVEF <40%; systolic dysfunction.
- HFpEF (Heart Failure with Preserved Ejection Fraction):
  - LVEF ≥50%; diastolic dysfunction.
- HFmrEF (mildly reduced ejection fraction, intermediate group, often LVEF 40–49%).

**Key symptoms and signs:**

- Dyspnea on exertion, orthopnea, paroxysmal nocturnal dyspnea.
- Fatigue, reduced exercise tolerance.
- Peripheral edema (ankles, legs), weight gain from fluid retention.
- Elevated jugular venous pressure, pulmonary crackles, S3 gallop.

**Common classification: NYHA functional class:**

- Class I: No limitation of physical activity; ordinary activity does not cause symptoms.
- Class II: Slight limitation; comfortable at rest; ordinary activity causes symptoms.
- Class III: Marked limitation; comfortable at rest; less than ordinary activity causes symptoms.
- Class IV: Symptoms at rest; any physical activity increases discomfort.

**ICD‑10‑CM examples:**

- I50.9 – Heart failure, unspecified.
- I50.20 – Unspecified systolic (congestive) heart failure.
- I50.30 – Unspecified diastolic (congestive) heart failure.

LLM hints:

- Combine BNP/NT‑proBNP levels, imaging (echo EF), physical exam, and medications (diuretics, ACE inhibitors, beta‑blockers) to infer severity.
- Recognize that “CHF exacerbation” indicates acute decompensation.

---

### 5.4 Chronic Obstructive Pulmonary Disease (COPD)

**Definition:**

COPD is a preventable, treatable disease characterized by persistent, usually progressive airflow limitation associated with chronic inflammatory response in the airways and lungs.

**Main components:**

- Chronic bronchitis:
  - Productive cough for ≥3 months per year for ≥2 consecutive years.
- Emphysema:
  - Destruction of alveolar walls and airspace enlargement.

**Risk factors:**

- Cigarette smoking (primary).
- Environmental exposures, occupational dusts/chemicals, biomass fuel exposure.
- Genetic factors (e.g., alpha‑1 antitrypsin deficiency).

**Common symptoms:**

- Chronic cough, sputum production.
- Dyspnea, especially with exertion.
- Frequent respiratory infections.

**GOLD classification (post‑bronchodilator FEV₁):**

- GOLD 1 (Mild): FEV₁ ≥80% predicted.
- GOLD 2 (Moderate): 50% ≤ FEV₁ <80% predicted.
- GOLD 3 (Severe): 30% ≤ FEV₁ <50% predicted.
- GOLD 4 (Very Severe): FEV₁ <30% predicted.

**ICD‑10‑CM:**

- J44.9 – Chronic obstructive pulmonary disease, unspecified.
- J44.1 – COPD with acute exacerbation.

LLM mapping:

- Connect chronic tobacco use + inhaler therapy (e.g., LABA, LAMA, ICS) + spirometry to COPD severity.
- Distinguish COPD from asthma (reversibility, atopy, age of onset).

---

## 6. Physical Examination Terminology

### 6.1 General Exam Terms

- **Edema:** Fluid accumulation in interstitial tissue, commonly graded from 1+ (mild) to 4+ (severe pitting).
- **Erythema:** Redness of the skin, usually from inflammation, infection, or vasodilation.
- **Auscultation:** Listening to internal body sounds (heart, lungs, bowel) with a stethoscope.
- **Palpation:** Using hands to feel structures (organs, masses, tenderness).
- **Percussion:** Tapping on the body surface to evaluate underlying structures based on sound differences.

LLM mapping:

- Translate shorthand: “LE edema 2+ bilaterally” → moderate lower‑extremity edema on both sides, often seen in CHF, nephrotic syndrome, or venous disease.
- Distinguish normal vs abnormal descriptors (e.g., “lungs clear to auscultation bilaterally” vs “diffuse wheezes”).

---

### 6.2 Cardiovascular Exam

Typical terms:

- **Regular rate and rhythm (RRR):** Heartbeat with normal rhythm and rate.
- **Murmur:** Extra heart sound from turbulent blood flow; described by timing (systolic/diastolic), location, and grade (I–VI).
- **Gallop:** Additional heart sounds (S3 or S4); S3 often associated with volume overload (e.g., CHF).

Mapping to conditions:

- Systolic murmur at left sternal border radiating to carotids → may suggest aortic stenosis.
- S3 gallop and pitting edema → often consistent with heart failure.

---

### 6.3 Respiratory Exam

Common descriptors:

- **Wheezes:** Continuous musical sounds (usually expiratory) from narrowed airways (e.g., asthma, COPD).
- **Crackles (rales):** Discontinuous popping sounds, often from fluid in alveoli (e.g., pneumonia, CHF).
- **Rhonchi:** Low‑pitched, snore‑like sounds from secretions in large airways.

LLM mapping:

- “Diffuse expiratory wheezes” → obstructive airway disease (asthma/COPD).
- “Bibasilar crackles” → fluid at lung bases, often CHF or pneumonia.

---

## 7. Abbreviations and Note Structure

### 7.1 Common Clinical Abbreviations

LLMs must correctly interpret abbreviations, many of which are context‑dependent.

- ROS: Review of systems.
- HPI: History of present illness.
- PMH: Past medical history.
- PSH: Past surgical history.
- FH: Family history.
- SH / SocHx: Social history.
- NKDA: No known drug allergies.
- NKA: No known allergies.
- NPO: Nothing by mouth.
- BID / TID / QID: Twice / three times / four times daily.
- PRN: As needed.
- PO: By mouth.
- IV / IM / SQ: Intravenous / intramuscular / subcutaneous.
- SOB: Shortness of breath.
- DOE: Dyspnea on exertion.
- CP: Chest pain.

LLM mapping:

- Avoid misinterpretation (e.g., “SOB” is shortness of breath, not pejorative).
- Combine abbreviations with context (e.g., “NPO after midnight for surgery” vs “NPO due to aspiration risk”).

---

### 7.2 SOAP Note Structure

Clinical notes often follow a structured pattern:

- **Subjective (S):**
  - Patient‑reported symptoms and history.
  - Example: “Patient reports worsening shortness of breath over 3 days.”
- **Objective (O):**
  - Measurable  vitals, physical exam, labs, imaging.
- **Assessment (A):**
  - Clinician’s synthesis and diagnoses.
  - Example: “Acute exacerbation of COPD; possible pneumonia.”
- **Plan (P):**
  - Treatment and diagnostic plan.
  - Example: “Start nebulized bronchodilators, order chest X‑ray, start antibiotics.”

For LLMs, this structure guides:

- Where to look for patient narrative vs clinician judgment.
- Where diagnoses are likely to be expressed explicitly.
- How to separate data input (Objective) from medical reasoning (Assessment/Plan).

---

## 8. Medication Terminology (High-Level)

### 8.1 Classes Frequently Seen in Chronic Disease

Recognizing medication classes helps infer underlying conditions.

- **Antihypertensives:**
  - ACE inhibitors (lisinopril).
  - ARBs (losartan).
  - Beta‑blockers (metoprolol).
  - Calcium channel blockers (amlodipine).
  - Diuretics (hydrochlorothiazide, furosemide).
- **Diabetes medications:**
  - Biguanides (metformin).
  - Insulins (basal, bolus).
  - SGLT2 inhibitors (empagliflozin).
  - GLP‑1 receptor agonists (semaglutide).
- **Lipid‑lowering drugs:**
  - Statins (atorvastatin, simvastatin).

LLM mapping:

- Presence of metformin + elevated HbA1c strongly suggests type 2 diabetes.
- Loop diuretics, ACE inhibitor, beta‑blocker, and spironolactone together often imply heart failure.

---

## 9. Data Quality and Modeling Considerations

### 9.1 Handling Units and Conversions

An LLM operating on clinical data must treat units as first‑class elements.

- Ensure `mg/dL` vs `mmol/L` for glucose and lipids is distinguished.
- Temperature in °C vs °F.
- Weight in kg vs lb, height in cm vs inches.

Where possible, normalize values to consistent units internally, but always retain original units for traceability.

---

### 9.2 Dealing with Missingness and Inconsistency

Real-world EHR data is often incomplete and inconsistent.

- Labs may be absent, outdated, or recorded with local names.
- Diagnoses may be coded, free‑text, or implied only by medications.
- Different systems may use different coding systems (e.g., SNOMED vs ICD). 

LLM guidance:

- Treat each data source (codes, narrative, labs, meds) as evidence; cross‑validate where possible (e.g., “I10” plus repeated high blood pressures and antihypertensives).
- Avoid over‑confidence when critical data (e.g., creatinine) is missing.

---

## 10. Summary Guidance for LLM Interpretation

When interpreting healthcare 

1. **Use codes and narrative together.**
   - ICD‑10, SNOMED, LOINC, CPT, meds, and free‑text should all be cross‑referenced.

2. **Respect clinical context.**
   - Encounter type (inpatient vs outpatient), time, and specialty affect interpretation (e.g., ICU vs clinic vitals).

3. **Treat numeric data carefully.**
   - Always link values with units, reference ranges, and timestamps.
   - Understand trends rather than a single data point.

4. **Infer conditions from patterns, not single clues.**
   - Example: Diabetes is best inferred from diagnoses, meds, and repeated labs (glucose/HbA1c), not a single mildly elevated glucose.

5. **Preserve clinical uncertainty.**
   - Distinguish suspected vs confirmed diagnoses and note where data is insufficient.
