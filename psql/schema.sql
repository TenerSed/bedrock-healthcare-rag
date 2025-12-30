-- ================================================================
-- MIMIC-IV Clinical Database Demo - Complete Schema
-- Modules: hosp (hospital EHR) + icu (ICU MetaVision)
-- + RAG Query Tables
-- ================================================================

-- =================
-- RAG QUERY TABLES
-- =================

CREATE TABLE kb_queries (
    query_id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    response_text TEXT,
    session_id VARCHAR(255),
    subject_id INTEGER,  -- Link to MIMIC patient
    response_time_ms INTEGER,
    citation_count INTEGER DEFAULT 0,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    model_arn VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT check_response_time CHECK (response_time_ms >= 0)
);

CREATE INDEX idx_kb_queries_subject_id ON kb_queries(subject_id) WHERE subject_id IS NOT NULL;
CREATE INDEX idx_kb_queries_created_at ON kb_queries(created_at DESC);
CREATE INDEX idx_kb_queries_session_id ON kb_queries(session_id) WHERE session_id IS NOT NULL;
CREATE INDEX idx_kb_queries_success ON kb_queries(success, created_at DESC);

CREATE TABLE kb_citations (
    citation_id SERIAL PRIMARY KEY,
    query_id INTEGER NOT NULL REFERENCES kb_queries(query_id) ON DELETE CASCADE,
    source_document VARCHAR(500) NOT NULL,
    excerpt_text TEXT,
    relevance_score FLOAT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT check_relevance_score CHECK (relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 1))
);

CREATE INDEX idx_kb_citations_query ON kb_citations(query_id);
CREATE INDEX idx_kb_citations_source ON kb_citations(source_document);
CREATE INDEX idx_kb_citations_metadata ON kb_citations USING GIN (metadata);

CREATE TABLE user_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_identifier VARCHAR(255),
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    query_count INTEGER DEFAULT 0,
    total_response_time_ms INTEGER DEFAULT 0,
    session_metadata JSONB,
    
    CONSTRAINT check_query_count CHECK (query_count >= 0)
);

CREATE INDEX idx_user_sessions_activity ON user_sessions(last_activity DESC);
CREATE INDEX idx_user_sessions_user ON user_sessions(user_identifier);


CREATE TABLE knowledge_sources (
    source_id SERIAL PRIMARY KEY,
    document_name VARCHAR(500) NOT NULL UNIQUE,
    document_type VARCHAR(50),
    s3_uri TEXT NOT NULL,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_sync_date TIMESTAMP,
    word_count INTEGER,
    citation_count INTEGER DEFAULT 0,
    metadata JSONB
);

CREATE INDEX idx_knowledge_sources_type ON knowledge_sources(document_type);
CREATE INDEX idx_knowledge_sources_name ON knowledge_sources(document_name);


-- ====================
-- HOSP MODULE (Hospital EHR Data)
-- ====================

-- Core patient demographics with deidentification
CREATE TABLE patients (
    subject_id INTEGER PRIMARY KEY,
    gender VARCHAR(1) CHECK (gender IN ('M', 'F')),
    anchor_age INTEGER,  -- Age in anchor_year (91 if >89)
    anchor_year INTEGER,  -- Deidentified year (2100-2200)
    anchor_year_group VARCHAR(20),  -- Actual year range (2008-2019)
    dod DATE,  -- Date of death (hospital or state records, censored at 1 year post-discharge)
    
    CONSTRAINT check_anchor_age CHECK (anchor_age >= 0 AND anchor_age <= 91),
    CONSTRAINT check_anchor_year CHECK (anchor_year >= 2100 AND anchor_year <= 2300)
);

COMMENT ON COLUMN patients.anchor_age IS 'Patient age in anchor_year. 91 indicates >89 years old.';
COMMENT ON COLUMN patients.anchor_year IS 'Deidentified year (2100-2200) for date shifting.';
COMMENT ON COLUMN patients.anchor_year_group IS 'Actual 3-year range when care occurred (2008-2019).';
COMMENT ON COLUMN patients.dod IS 'Date of death. NULL if survived >1 year post-discharge. Censored for privacy.';


-- Hospital admissions
CREATE TABLE admissions (
    hadm_id INTEGER PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    admittime TIMESTAMP NOT NULL,
    dischtime TIMESTAMP,
    deathtime TIMESTAMP,
    admission_type VARCHAR(50),  -- EMERGENCY, ELECTIVE, URGENT, etc.
    admit_provider_id VARCHAR(50),  -- Provider who admitted patient
    admission_location VARCHAR(100),
    discharge_location VARCHAR(100),
    insurance VARCHAR(50),
    language VARCHAR(50),
    marital_status VARCHAR(50),
    race VARCHAR(100),  -- Updated from ethnicity
    edregtime TIMESTAMP,  -- Emergency department registration time
    edouttime TIMESTAMP,  -- Emergency department departure time
    hospital_expire_flag SMALLINT CHECK (hospital_expire_flag IN (0, 1)),
    
    CONSTRAINT check_times CHECK (dischtime IS NULL OR dischtime >= admittime)
);

CREATE INDEX idx_admissions_subject ON admissions(subject_id);
CREATE INDEX idx_admissions_time ON admissions(admittime, dischtime);
CREATE INDEX idx_admissions_admit_provider ON admissions(admit_provider_id);

COMMENT ON TABLE admissions IS 'Hospital admissions with timestamps and admission metadata.';


-- Intra-hospital transfers
CREATE TABLE transfers (
    transfer_id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    hadm_id INTEGER REFERENCES admissions(hadm_id),
    transfer_id_orig INTEGER,  -- Original transfer ID from source system
    eventtype VARCHAR(50),  -- admit, transfer, discharge
    careunit VARCHAR(50),  -- Care unit name (ICU, ward, etc.)
    intime TIMESTAMP,
    outtime TIMESTAMP
);

CREATE INDEX idx_transfers_subject ON transfers(subject_id);
CREATE INDEX idx_transfers_hadm ON transfers(hadm_id);
CREATE INDEX idx_transfers_careunit ON transfers(careunit);


-- Laboratory events
CREATE TABLE labevents (
    labevent_id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    hadm_id INTEGER REFERENCES admissions(hadm_id),
    specimen_id INTEGER,  -- Links multiple tests from same specimen
    itemid INTEGER NOT NULL,  -- Links to d_labitems
    charttime TIMESTAMP,
    storetime TIMESTAMP,
    value VARCHAR(200),
    valuenum NUMERIC,
    valueuom VARCHAR(50),  -- Unit of measurement
    ref_range_lower NUMERIC,
    ref_range_upper NUMERIC,
    flag VARCHAR(10),  -- abnormal, normal, delta
    priority VARCHAR(10),  -- STAT, ROUTINE
    comments TEXT
);

CREATE INDEX idx_labevents_subject ON labevents(subject_id);
CREATE INDEX idx_labevents_hadm ON labevents(hadm_id);
CREATE INDEX idx_labevents_itemid ON labevents(itemid);
CREATE INDEX idx_labevents_charttime ON labevents(charttime);
CREATE INDEX idx_labevents_specimen ON labevents(specimen_id);


-- Lab items dictionary
CREATE TABLE d_labitems (
    itemid INTEGER PRIMARY KEY,
    label VARCHAR(200) NOT NULL,
    fluid VARCHAR(100),  -- Blood, Urine, etc.
    category VARCHAR(100),
    loinc_code VARCHAR(50)
);


-- Diagnoses (ICD codes)
CREATE TABLE diagnoses_icd (
    diagnosis_id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    hadm_id INTEGER NOT NULL REFERENCES admissions(hadm_id),
    seq_num INTEGER,  -- Diagnosis priority/sequence
    icd_code VARCHAR(10) NOT NULL,
    icd_version INTEGER CHECK (icd_version IN (9, 10)),
    
    CONSTRAINT unique_diagnosis_per_admission UNIQUE (hadm_id, seq_num)
);

CREATE INDEX idx_diagnoses_hadm ON diagnoses_icd(hadm_id);
CREATE INDEX idx_diagnoses_icd ON diagnoses_icd(icd_code);
CREATE INDEX idx_diagnoses_subject ON diagnoses_icd(subject_id);


-- ICD diagnosis dictionary
CREATE TABLE d_icd_diagnoses (
    icd_code VARCHAR(10) NOT NULL,
    icd_version INTEGER NOT NULL CHECK (icd_version IN (9, 10)),
    long_title TEXT,
    
    PRIMARY KEY (icd_code, icd_version)
);


-- Procedures (ICD codes)
CREATE TABLE procedures_icd (
    procedure_id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    hadm_id INTEGER NOT NULL REFERENCES admissions(hadm_id),
    seq_num INTEGER,
    chartdate DATE,
    icd_code VARCHAR(10) NOT NULL,
    icd_version INTEGER CHECK (icd_version IN (9, 10))
);

CREATE INDEX idx_procedures_hadm ON procedures_icd(hadm_id);
CREATE INDEX idx_procedures_icd ON procedures_icd(icd_code);


-- ICD procedure dictionary
CREATE TABLE d_icd_procedures (
    icd_code VARCHAR(10) NOT NULL,
    icd_version INTEGER NOT NULL CHECK (icd_version IN (9, 10)),
    long_title TEXT,
    
    PRIMARY KEY (icd_code, icd_version)
);


-- Medication administration (eMAR)
CREATE TABLE emar (
    emar_id VARCHAR(50) PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    hadm_id INTEGER REFERENCES admissions(hadm_id),
    emar_seq INTEGER,
    poe_id VARCHAR(50),  -- Links to provider orders
    pharmacy_id INTEGER,
    charttime TIMESTAMP,
    medication TEXT,
    event_txt VARCHAR(100),  -- Given, Not Given, etc.
    scheduletime TIMESTAMP,
    storetime TIMESTAMP
);

CREATE INDEX idx_emar_subject ON emar(subject_id);
CREATE INDEX idx_emar_hadm ON emar(hadm_id);
CREATE INDEX idx_emar_charttime ON emar(charttime);


-- Medication details
CREATE TABLE emar_detail (
    emar_id VARCHAR(50) REFERENCES emar(emar_id),
    emar_seq INTEGER,
    parent_field_ordinal NUMERIC,
    administration_type VARCHAR(50),
    pharmacy_id INTEGER,
    barcode_type VARCHAR(50),
    reason_for_no_barcode TEXT,
    complete_dose_not_given VARCHAR(10),
    dose_due VARCHAR(100),
    dose_due_unit VARCHAR(50),
    dose_given VARCHAR(100),
    dose_given_unit VARCHAR(50),
    will_remainder_of_dose_be_given VARCHAR(10),
    product_amount_given VARCHAR(50),
    product_unit VARCHAR(50),
    product_code VARCHAR(50),
    product_description TEXT,
    product_description_other TEXT,
    prior_infusion_rate VARCHAR(50),
    infusion_rate VARCHAR(50),
    infusion_rate_adjustment VARCHAR(50),
    infusion_rate_unit VARCHAR(50),
    route VARCHAR(50),
    infusion_complete VARCHAR(10),
    completion_interval VARCHAR(50),
    new_iv_bag_hung VARCHAR(10),
    continued_infusion_in_other_location VARCHAR(10),
    restart_interval VARCHAR(50),
    side VARCHAR(50),
    site VARCHAR(100),
    non_formulary_visual_verification VARCHAR(10)
);

CREATE INDEX idx_emar_detail_emar ON emar_detail(emar_id);


-- Prescriptions
CREATE TABLE prescriptions (
    prescription_id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    hadm_id INTEGER REFERENCES admissions(hadm_id),
    pharmacy_id INTEGER,
    poe_id TEXT,
    poe_seq INTEGER,
    starttime TIMESTAMP,
    stoptime TIMESTAMP,
    drug_type TEXT,
    drug TEXT,
    gsn TEXT,  -- Generic Sequence Number
    ndc TEXT,  -- National Drug Code
    prod_strength TEXT,
    form_rx TEXT,
    dose_val_rx TEXT,
    dose_unit_rx TEXT,
    form_val_disp TEXT,
    form_unit_disp VARCHAR(50),
    doses_per_24_hrs NUMERIC,
    route VARCHAR(50)
);

CREATE INDEX idx_prescriptions_subject ON prescriptions(subject_id);
CREATE INDEX idx_prescriptions_hadm ON prescriptions(hadm_id);
CREATE INDEX idx_prescriptions_drug ON prescriptions(drug);


-- Provider orders (POE)
CREATE TABLE poe (
    poe_id VARCHAR(50) PRIMARY KEY,
    poe_seq INTEGER,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    hadm_id INTEGER REFERENCES admissions(hadm_id),
    ordertime TIMESTAMP,
    order_type VARCHAR(50),
    order_subtype VARCHAR(100),
    transaction_type VARCHAR(50),
    discontinue_of_poe_id VARCHAR(50),
    discontinued_by_poe_id VARCHAR(50),
    order_provider_id VARCHAR(50),  -- Provider who ordered
    order_status VARCHAR(50)
);

CREATE INDEX idx_poe_subject ON poe(subject_id);
CREATE INDEX idx_poe_hadm ON poe(hadm_id);
CREATE INDEX idx_poe_provider ON poe(order_provider_id);


-- Microbiology events
CREATE TABLE microbiologyevents (
    microevent_id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    hadm_id INTEGER REFERENCES admissions(hadm_id),
    micro_specimen_id INTEGER,
    chartdate DATE,
    charttime TIMESTAMP,
    spec_itemid INTEGER,  -- Specimen type
    spec_type_desc VARCHAR(100),
    test_seq INTEGER,
    storedate DATE,
    storetime TIMESTAMP,
    test_itemid INTEGER,
    test_name VARCHAR(100),
    org_itemid INTEGER,
    org_name VARCHAR(100),
    isolate_num SMALLINT,
    quantity VARCHAR(50),
    ab_itemid INTEGER,  -- Antibiotic
    ab_name VARCHAR(50),
    dilution_text VARCHAR(50),
    dilution_comparison VARCHAR(10),
    dilution_value NUMERIC,
    interpretation VARCHAR(50)  -- R, S, I (Resistant, Susceptible, Intermediate)
);

CREATE INDEX idx_micro_subject ON microbiologyevents(subject_id);
CREATE INDEX idx_micro_hadm ON microbiologyevents(hadm_id);
CREATE INDEX idx_micro_specimen ON microbiologyevents(micro_specimen_id);


-- DRG (Diagnosis Related Group) codes
CREATE TABLE drgcodes (
    drg_id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    hadm_id INTEGER NOT NULL REFERENCES admissions(hadm_id),
    drg_type VARCHAR(50),
    drg_code VARCHAR(10),
    description TEXT,
    drg_severity SMALLINT,
    drg_mortality SMALLINT
);

CREATE INDEX idx_drgcodes_hadm ON drgcodes(hadm_id);


-- Services (clinical service transfers)
CREATE TABLE services (
    service_id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    hadm_id INTEGER REFERENCES admissions(hadm_id),
    transfertime TIMESTAMP,
    prev_service VARCHAR(50),
    curr_service VARCHAR(50)
);

CREATE INDEX idx_services_hadm ON services(hadm_id);


-- Provider information
CREATE TABLE provider (
    provider_id VARCHAR(50) PRIMARY KEY  -- Deidentified provider ID
);

COMMENT ON TABLE provider IS 'Deidentified care provider lookup. Used with *_provider_id columns across tables.';


-- ====================
-- ICU MODULE (MetaVision Data)
-- ====================

-- ICU stays
CREATE TABLE icustays (
    stay_id INTEGER PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    hadm_id INTEGER REFERENCES admissions(hadm_id),
    first_careunit VARCHAR(50),
    last_careunit VARCHAR(50),
    intime TIMESTAMP,
    outtime TIMESTAMP,
    los NUMERIC  -- Length of stay in days
);

CREATE INDEX idx_icustays_subject ON icustays(subject_id);
CREATE INDEX idx_icustays_hadm ON icustays(hadm_id);
CREATE INDEX idx_icustays_time ON icustays(intime, outtime);


-- ICU item definitions (central dictionary for all ICU events)
CREATE TABLE d_items (
    itemid INTEGER PRIMARY KEY,
    label VARCHAR(200),
    abbreviation VARCHAR(100),
    linksto VARCHAR(50),  -- Which events table this links to
    category VARCHAR(100),
    unitname VARCHAR(50),
    param_type VARCHAR(50),
    lownormalvalue NUMERIC,
    highnormalvalue NUMERIC
);


-- Charted events (vital signs, assessments, etc.)
CREATE TABLE chartevents (
    chartevent_id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    hadm_id INTEGER REFERENCES admissions(hadm_id),
    stay_id INTEGER REFERENCES icustays(stay_id),
    caregiver_id INTEGER,  -- Links to caregiver table
    charttime TIMESTAMP,
    storetime TIMESTAMP,
    itemid INTEGER NOT NULL REFERENCES d_items(itemid),
    value VARCHAR(200),
    valuenum NUMERIC,
    valueuom VARCHAR(50),
    warning SMALLINT  -- Data quality warning flag
);

CREATE INDEX idx_chartevents_subject ON chartevents(subject_id);
CREATE INDEX idx_chartevents_stay ON chartevents(stay_id);
CREATE INDEX idx_chartevents_itemid ON chartevents(itemid);
CREATE INDEX idx_chartevents_charttime ON chartevents(charttime);


-- Datetime events
CREATE TABLE datetimeevents (
    datetimeevent_id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    hadm_id INTEGER REFERENCES admissions(hadm_id),
    stay_id INTEGER REFERENCES icustays(stay_id),
    caregiver_id INTEGER,
    charttime TIMESTAMP,
    storetime TIMESTAMP,
    itemid INTEGER NOT NULL REFERENCES d_items(itemid),
    value TIMESTAMP,
    valueuom VARCHAR(50),
    warning SMALLINT
);

CREATE INDEX idx_datetimeevents_stay ON datetimeevents(stay_id);
CREATE INDEX idx_datetimeevents_itemid ON datetimeevents(itemid);


-- Input events (IV fluids, medications)
CREATE TABLE inputevents (
    inputevent_id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    hadm_id INTEGER REFERENCES admissions(hadm_id),
    stay_id INTEGER REFERENCES icustays(stay_id),
    caregiver_id INTEGER,
    starttime TIMESTAMP,
    endtime TIMESTAMP,
    storetime TIMESTAMP,
    itemid INTEGER NOT NULL REFERENCES d_items(itemid),
    amount NUMERIC,
    amountuom VARCHAR(50),
    rate NUMERIC,
    rateuom VARCHAR(50),
    orderid INTEGER,
    linkorderid INTEGER,
    ordercategoryname VARCHAR(100),
    secondaryordercategoryname VARCHAR(100),
    ordercomponenttypedescription VARCHAR(200),
    ordercategorydescription VARCHAR(100),
    patientweight NUMERIC,
    totalamount NUMERIC,
    totalamountuom VARCHAR(50),
    isopenbag SMALLINT,
    continueinnextdept SMALLINT,
    cancelreason SMALLINT,
    statusdescription VARCHAR(50),
    originalamount NUMERIC,
    originalrate NUMERIC
);

CREATE INDEX idx_inputevents_stay ON inputevents(stay_id);
CREATE INDEX idx_inputevents_itemid ON inputevents(itemid);
CREATE INDEX idx_inputevents_time ON inputevents(starttime, endtime);


-- Ingredient events (ingredients in inputevents)
CREATE TABLE ingredientevents (
    ingredientevent_id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    hadm_id INTEGER REFERENCES admissions(hadm_id),
    stay_id INTEGER REFERENCES icustays(stay_id),
    caregiver_id INTEGER,
    starttime TIMESTAMP,
    endtime TIMESTAMP,
    storetime TIMESTAMP,
    itemid INTEGER NOT NULL REFERENCES d_items(itemid),
    amount NUMERIC,
    amountuom VARCHAR(50),
    rate NUMERIC,
    rateuom VARCHAR(50),
    orderid INTEGER,
    linkorderid INTEGER,
    statusdescription VARCHAR(50),
    originalamount NUMERIC,
    originalrate NUMERIC
);

CREATE INDEX idx_ingredientevents_stay ON ingredientevents(stay_id);
CREATE INDEX idx_ingredientevents_itemid ON ingredientevents(itemid);


-- Output events (urine, drains, etc.)
CREATE TABLE outputevents (
    outputevent_id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    hadm_id INTEGER REFERENCES admissions(hadm_id),
    stay_id INTEGER REFERENCES icustays(stay_id),
    caregiver_id INTEGER,
    charttime TIMESTAMP,
    storetime TIMESTAMP,
    itemid INTEGER NOT NULL REFERENCES d_items(itemid),
    value NUMERIC,
    valueuom VARCHAR(50)
);

CREATE INDEX idx_outputevents_stay ON outputevents(stay_id);
CREATE INDEX idx_outputevents_itemid ON outputevents(itemid);


-- Procedure events
CREATE TABLE procedureevents (
    procedureevent_id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES patients(subject_id),
    hadm_id INTEGER REFERENCES admissions(hadm_id),
    stay_id INTEGER REFERENCES icustays(stay_id),
    caregiver_id INTEGER,
    starttime TIMESTAMP,
    endtime TIMESTAMP,
    storetime TIMESTAMP,
    itemid INTEGER NOT NULL REFERENCES d_items(itemid),
    value NUMERIC,
    valueuom VARCHAR(50),
    location VARCHAR(100),
    locationcategory VARCHAR(50),
    orderid INTEGER,
    linkorderid INTEGER,
    ordercategoryname VARCHAR(100),
    secondaryordercategoryname VARCHAR(100),
    ordercategorydescription VARCHAR(100),
    patientweight NUMERIC,
    totalamount NUMERIC,
    totalamountuom VARCHAR(50),
    isopenbag SMALLINT,
    continueinnextdept SMALLINT,
    cancelreason SMALLINT,
    statusdescription VARCHAR(50),
    comments_date TIMESTAMP,
    originalamount NUMERIC,
    originalrate NUMERIC
);

CREATE INDEX idx_procedureevents_stay ON procedureevents(stay_id);
CREATE INDEX idx_procedureevents_itemid ON procedureevents(itemid);


-- Caregiver information
CREATE TABLE caregiver (
    caregiver_id INTEGER PRIMARY KEY  -- Deidentified caregiver ID
);

COMMENT ON TABLE caregiver IS 'Deidentified care provider who documented ICU data in MetaVision.';


-- ======================
-- ANALYTICS VIEWS
-- ======================

-- Patient summary (updated)
CREATE VIEW patient_summary AS
SELECT 
    p.subject_id,
    p.gender,
    p.anchor_age,
    p.anchor_year_group,
    CASE WHEN p.dod IS NOT NULL THEN 'Deceased' ELSE 'Living' END as status,
    COUNT(DISTINCT a.hadm_id) as total_admissions,
    COUNT(DISTINCT i.stay_id) as total_icu_stays,
    COUNT(DISTINCT d.icd_code) as unique_diagnoses,
    COUNT(DISTINCT le.itemid) as unique_lab_tests,
    MAX(a.admittime) as most_recent_admission
FROM patients p
LEFT JOIN admissions a ON p.subject_id = a.subject_id
LEFT JOIN icustays i ON p.subject_id = i.subject_id
LEFT JOIN diagnoses_icd d ON p.subject_id = d.subject_id
LEFT JOIN labevents le ON p.subject_id = le.subject_id
GROUP BY p.subject_id, p.gender, p.anchor_age, p.anchor_year_group, p.dod;


-- Diagnosis frequency
CREATE VIEW diagnosis_frequency AS
SELECT 
    d.icd_code,
    d.icd_version,
    di.long_title,
    COUNT(*) as occurrence_count,
    COUNT(DISTINCT d.subject_id) as patient_count,
    COUNT(DISTINCT d.hadm_id) as admission_count
FROM diagnoses_icd d
LEFT JOIN d_icd_diagnoses di ON d.icd_code = di.icd_code AND d.icd_version = di.icd_version
GROUP BY d.icd_code, d.icd_version, di.long_title
ORDER BY occurrence_count DESC;


-- RAG query analytics
CREATE VIEW query_analytics AS
SELECT 
    DATE_TRUNC('day', created_at) as query_date,
    COUNT(*) as total_queries,
    AVG(response_time_ms) as avg_response_time,
    AVG(citation_count) as avg_citations,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_queries,
    SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failed_queries,
    COUNT(DISTINCT subject_id) as unique_patients_queried
FROM kb_queries
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY query_date DESC;


-- Sample data inserts
INSERT INTO knowledge_sources (document_name, document_type, s3_uri) VALUES
('hipaa-privacy-rule.md', 'hipaa_privacy', 's3://your-bucket/documents/hipaa-privacy-rule.md'),
('hipaa-security-rule.md', 'hipaa_security', 's3://your-bucket/documents/hipaa-security-rule.md'),
('medical-terminology.md', 'medical_terminology', 's3://your-bucket/documents/medical-terminology.md'),
('ehr-standards.md', 'ehr_standards', 's3://your-bucket/documents/ehr-standards.md'),
('quality-metrics.md', 'quality_metrics', 's3://your-bucket/documents/quality-metrics.md');
