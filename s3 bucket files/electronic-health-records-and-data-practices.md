Electronic health record (EHR) standards define how clinical and administrative data are structured, exchanged, and interpreted across healthcare systems, enabling interoperability and consistent representation of patient information. This document describes core EHR messaging standards, modern FHIR resources, regulatory certification concepts, and common clinical documentation elements in an encyclopedia-style format.

---

## HL7 Version 2.x Messaging

HL7 Version 2.x (HL7 v2) is a widely used healthcare messaging standard that defines how systems exchange clinical and administrative data using delimited text messages composed of segments, fields, components, and subcomponents. HL7 v2 is event-driven and commonly used for admission, discharge, transfer (ADT), orders, results, scheduling, and billing workflows in hospitals and laboratories.

### HL7 v2 Message Structure

An HL7 v2 message is a sequence of segments separated by carriage returns, where each segment is a line starting with a three-character identifier such as MSH or PID. Segments contain fields separated by the pipe character `|`, and fields may contain components separated by `^`, subcomponents separated by `&`, and repetitions separated by `~`.

**Key concepts:**
- **Segment:** Logical group of related fields, identified by a three-letter code (for example MSH, PID, OBR, OBX).  
- **Field:** Positionally defined element within a segment that represents a data value, such as patient ID or observation value.  
- **Component:** Subdivision of a field, often used for coded values with code, text, and coding system.  
- **Subcomponent:** Further subdivision of a component, used for detailed coding structures.

### Common HL7 v2 Segments

HL7 v2 defines many segments, but EHR and integration workflows typically rely on a subset that carry core clinical and administrative data.

- **MSH (Message Header):**  
  - Identifies sending and receiving applications and facilities.  
  - Specifies message type, trigger event, control ID, processing ID, and HL7 version.

- **EVN (Event Type):**  
  - Describes the event that triggered the message, such as an admission or discharge.  
  - Contains event type code and event timestamp.

- **PID (Patient Identification):**  
  - Holds patient identifiers (for example medical record number), name, date of birth, administrative sex, address, phone, and demographic attributes.  
  - Used to uniquely associate other clinical data to a specific patient.

- **PV1 (Patient Visit):**  
  - Represents encounter details including patient class (inpatient, outpatient), location, attending provider, admission type, and visit number.  
  - Links clinical events to a specific encounter episode.

- **OBR (Observation Request):**  
  - Encodes order-level information for diagnostic tests, imaging, or other observations.  
  - Includes placer and filler order numbers, ordering provider, ordering facility, and requested procedure.

- **OBX (Observation Result):**  
  - Carries observation values such as laboratory results, vital signs, or other measurements.  
  - Includes value type, observation identifier, observation value, units, reference ranges, abnormal flags, and result status.

- **RXA (Pharmacy/Treatment Administration):**  
  - Documents administration events for medications, vaccines, or other treatments.  
  - Contains administered drug, dose, route, administration time, and administering provider.

- **ADT (Admission/Discharge/Transfer) Messages:**  
  - Use combinations of MSH, EVN, PID, PV1, and related segments to represent patient registration and movement.  
  - Common trigger events include ADT^A01 (admit/visit notification) and ADT^A03 (discharge).

### HL7 v2 Use in EHR Systems

HL7 v2 messages are often used as the integration backbone between registration, laboratory, radiology, pharmacy, and EHR systems. Systems maintain internal data models and transform local representations to and from HL7 v2 messages at interface boundaries.

Common HL7 v2 flows:
- **Registration:** ADT messages communicate creation and updates of patient demographics and encounters from registration systems to downstream consumers.  
- **Orders and Results:** ORM and ORU messages carry orders and results between provider order entry systems, labs, and EHR result modules.  
- **Scheduling:** SIU messages support scheduling events for appointments, procedures, and resources.

---

## FHIR (Fast Healthcare Interoperability Resources)

Fast Healthcare Interoperability Resources (FHIR) is a modern standard that defines modular resources, RESTful APIs, and data formats such as JSON and XML for exchanging healthcare information. FHIR focuses on composable resources, standardized extensions, and web-friendly architectures, making it well suited for EHR integration, mobile apps, and cloud-based services.

### FHIR Resource Model

FHIR resources are discrete data structures representing clinical or administrative concepts, each with a defined set of elements and references to other resources. Resources share common patterns for identifiers, metadata, narrative text, and references, enabling consistent handling across different resource types.

Key characteristics:
- **Resource granularity:** Each resource represents a specific concept such as Patient, Encounter, Observation, or MedicationRequest.  
- **Linking via references:** Resources reference each other, forming a graph of patient-related data.  
- **Profiles and extensions:** Implementation guides constrain resources and define extensions for local needs while retaining interoperability.

### Core Clinical FHIR Resources

These resources capture core EHR data elements commonly retrieved in clinical workflows and API-based integration.

- **Patient:**  
  - Represents demographic and administrative information about an individual receiving care.  
  - Contains identifiers, name, telecom, gender, birth date, address, marital status, communication preferences, and links to related persons.

- **Encounter:**  
  - Describes an interaction between a patient and healthcare provider or organization.  
  - Includes class (inpatient, outpatient), status, type, period, reason, participants, and location.

- **Condition:**  
  - Represents problems, diagnoses, or health concerns attributed to a patient.  
  - Includes clinical status, verification status, category, code, body site, onset, abatement, and recorder.

- **Observation:**  
  - Captures measurements, test results, assessments, or simple assertions such as vital signs and laboratory values.  
  - Includes status, category (for example vital-signs or laboratory), code, subject, effective time, value, units, interpretation, and reference range.

- **Medication and MedicationRequest:**  
  - Medication defines details about a drug or therapeutic agent, including ingredient and form.  
  - MedicationRequest represents an order or request for supply and administration of a medication to a patient, including status, intent, dosage instructions, and dispense details.

- **AllergyIntolerance:**  
  - Documents allergies and intolerances, including substance, clinical status, verification status, criticality, and reactions.  
  - Enables decision support around contraindications and adverse reaction risk.

### FHIR Interactions and APIs

FHIR defines RESTful interactions such as read, search, create, update, and delete, using standard HTTP methods and resource-specific endpoints. Systems use query parameters to retrieve resources by identifiers, references, or attributes, such as searching for Observations by patient subject or code.

Examples:
- Retrieve a patient by ID: `GET [base]/Patient/12345`.  
- Search all Observations for a patient: `GET [base]/Observation?subject=Patient/12345`.

FHIR can also be used with messaging, documents, and services (operations), but RESTful APIs are the primary pattern for modern EHR integrations.

---

## SMART on FHIR and App Integration

SMART on FHIR is an application platform and security profile that uses OAuth 2.0 and OpenID Connect to enable third-party applications to launch within or alongside EHRs using FHIR APIs. It defines scopes, launch contexts, and token handling conventions to provide controlled, patient-specific access to FHIR resources.

Key aspects:
- **Launch context:** EHR launches the app with context such as patient ID or encounter ID.  
- **FHIR scopes:** Access to resources is requested using scopes like `patient/Observation.read` or `user/Patient.read`.  
- **Standards-based authentication:** OAuth authorization servers issue access tokens that the app uses to call FHIR endpoints securely.

SMART on FHIR enables ecosystem-style integration where specialized apps can provide decision support, visualizations, or patient engagement using standardized data.

---

## Meaningful Use and 2015 Edition Certification

Meaningful Use, later incorporated into Promoting Interoperability programs, established criteria for eligible providers and hospitals to use certified EHR technology in ways that improve quality, safety, and efficiency. Certification criteria specify technical capabilities that EHR products must implement to support these policy goals.

### Meaningful Use Concepts

Core ideas associated with Meaningful Use include:
- **Capture of structured health information:** EHRs must capture key data elements in coded formats to support decision support and reporting.  
- **Exchange of information for care coordination:** Systems must send and receive standardized summary documents and notifications.  
- **Clinical quality measure reporting:** Providers must use EHR data to report standardized quality measures to regulators.

Meaningful Use adoption was phased in stages, with Stage 1 focused on basic data capture and sharing, and later stages emphasizing advanced clinical processes and outcomes.

### 2015 Edition EHR Certification Criteria

The 2015 Edition Health IT Certification Criteria define capabilities and standards that health IT modules must support, many of which are used by EHR incentive and interoperability programs. These criteria reference interoperability standards such as HL7, FHIR, and the United States Core Data for Interoperability (USCDI).

Relevant capability areas include:
- **Patient Registration and Demographics:** Support electronic capture and display of basic demographics, identifiers, and contact information.  
- **Patient Access to Data:** Provide mechanisms for patients to view, download, or transmit their health information, typically via portals or APIs.  
- **Clinical Notes and Summaries:** Capture, store, and exchange clinical notes and care summaries, often using standards like C-CDA or FHIR-based documents.  
- **Secure Messaging:** Enable secure electronic messaging between patients and providers with audit capabilities.  
- **Laboratory and Result Display:** Receive, display, and incorporate laboratory results in structured formats.

These criteria ensure that certified EHR products can interoperate and support regulatory reporting requirements across different providers and settings.

---

## Common EHR Data Elements

EHR systems capture a consistent set of clinical documentation elements for each encounter to support care, billing, quality reporting, and interoperability. These elements are often organized using standard clinical note structures such as SOAP (Subjective, Objective, Assessment, Plan) or similar templates.

### Chief Complaint

The **chief complaint (CC)** is a concise statement describing the primary reason for the patient encounter, typically in the patient’s own words. It is usually documented as a short phrase such as “chest pain,” “shortness of breath,” or “follow-up for diabetes.”

Characteristics:
- Required for most encounter documentation as the anchor for history and evaluation.  
- May be explicitly entered or inferred from the history of present illness if clearly documented.

### History of Present Illness (HPI)

The **history of present illness (HPI)** provides a detailed narrative of the patient’s current symptoms, including onset, duration, severity, associated symptoms, and modifying factors. It focuses on the current problem and may reference prior episodes or related conditions when clinically relevant.

Common elements:
- **Quality:** Description of symptom characteristics (for example sharp, dull, burning).  
- **Severity:** Degree or intensity of symptoms, often using numeric scales.  
- **Timing:** Onset date or time, course (acute, chronic, intermittent), and pattern.  
- **Modifying factors:** What improves or worsens symptoms, such as movement or medication.  
- **Associated symptoms:** Other complaints that may be related, such as nausea with chest pain.  
- **Location and radiation:** Site of symptoms and any spread to other regions.

### Past Medical History (PMH)

**Past medical history** documents prior illnesses, surgeries, hospitalizations, injuries, and chronic conditions relevant to ongoing care. Chronic diseases such as hypertension, diabetes, and asthma are tracked as persistent problems that influence management decisions.

Typical components:
- **Chronic conditions:** Long-term diagnoses requiring ongoing monitoring and treatment.  
- **Surgeries and procedures:** Past operations and interventions with dates when available.  
- **Hospitalizations:** Prior admissions for acute events or complicated illnesses.

### Medications and Allergies

EHRs maintain structured lists of active medications and known allergies to support safe prescribing and decision support.

- **Medications:**  
  - Include active prescriptions, over-the-counter drugs, and relevant supplements with name, dose, frequency, route, and indication.  
  - Can be mapped to standardized vocabularies such as RxNorm to support interoperability and clinical decision support.

- **Allergies and Intolerances:**  
  - Record substances, reaction types, severity, and status (for example active or inactive).  
  - Represented in systems as allergy entries that trigger warnings during ordering.

### Social History

**Social history** captures lifestyle and environmental factors that affect health, such as tobacco use, alcohol intake, drug use, occupation, and living arrangements. These data elements help explain risk factors and support preventive care interventions.

Common components:
- Tobacco status and pack-year history.  
- Alcohol consumption patterns.  
- Illicit drug use and route.  
- Occupational exposures and stressors.  
- Living situation and support system.

### Physical Examination

The **physical examination** section documents objective findings from the clinician’s examination, organized by body system such as cardiovascular, respiratory, or neurological. Findings may be structured as normal or abnormal for each system, with specific abnormalities described in detail.

Typical structure:
- **General appearance:** Overall impression of the patient’s condition.  
- **Vital signs:** Temperature, blood pressure, heart rate, respiratory rate, and oxygen saturation when measured.  
- **System-specific findings:** Detailed observations for each relevant system.

### Assessment and Plan

The **assessment and plan** section summarizes clinical impressions and documents the planned diagnostic and therapeutic actions for each identified problem. It is central to clinical reasoning and often organized as a problem list with associated plans.

- **Assessment:**  
  - Includes diagnoses, differential diagnoses, and clinical reasoning.  
  - May reference supporting findings such as lab results or imaging.

- **Plan:**  
  - Outlines tests, treatments, referrals, patient counseling, and follow-up.  
  - May include contingency plans based on symptom changes or test results.

---

## EHR Representation of Encounters and Notes

EHRs represent encounters as structured entities linked to patients, clinicians, locations, and documentation in note form. Documentation templates often enforce capture of required data elements for regulatory compliance, billing, and quality measurement.

### Encounter-Level Data

Encounter records store information such as:
- **Encounter type:** Inpatient, outpatient, emergency, telehealth, or observation.  
- **Dates and times:** Start and end of the encounter or visit.  
- **Location:** Facility and department where care was provided.  
- **Providers:** Attending and consulting clinicians associated with the encounter.

These data link clinical notes, orders, and results to specific visit episodes, enabling longitudinal and episode-based analysis.

### Note Types and Templates

Common EHR note types include history and physical (H&P), progress notes, consultation notes, operative reports, discharge summaries, and procedure notes. Templates often define required sections and prompts to ensure capture of chief complaint, HPI, review of systems, exam, assessment, and plan.

Template characteristics:
- **Section headings:** Standardized headings improve readability and support NLP extraction.  
- **Structured fields:** Drop-downs and checkboxes capture discrete data in addition to free text.  
- **Decision support hooks:** Contextual prompts remind clinicians to document risk factors or required elements.

---

## Laboratory and Diagnostic Results in EHRs

Laboratory and diagnostic results represent a major class of EHR data, commonly exchanged via HL7 v2 messages and represented as Observation resources in FHIR. Consistent coding and units are essential for accurate interpretation and longitudinal analysis.

### Lab Orders and Results

Lab workflows typically involve:
- **Order placement:** Clinicians submit orders specifying tests, priority, and specimen details.  
- **Specimen collection and processing:** Samples are collected, labeled, and processed in the lab.  
- **Result reporting:** Lab systems produce structured results that EHRs ingest and display.

In HL7 v2, OBR segments represent order-level information and OBX segments carry individual test results with codes, values, units, and abnormal flags. In FHIR, each laboratory result is represented as an Observation resource with code, value, units, and interpretation.

### Interpretation and Reference Ranges

Lab results usually include reference ranges and interpretation flags indicating high, low, or critical values. EHRs may present color-coded displays and alerts to highlight abnormal or urgent results for clinician review.

Key elements:
- **Reference range:** Expected normal range for a measurement based on population and lab methods.  
- **Interpretation code:** Qualitative assessment such as high, low, normal, or critical.

---

## Summary

EHR data standards such as HL7 v2 and FHIR define structured messages and resources for representing patient demographics, encounters, conditions, medications, observations, and other clinical information. Common EHR documentation elements including chief complaint, HPI, past medical history, medications, allergies, social history, physical exam, and assessment and plan provide a consistent framework for describing encounters and supporting downstream analytics and decision support.
