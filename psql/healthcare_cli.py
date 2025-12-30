"""
Interactive Healthcare Assistant CLI - Full MIMIC-IV Integration
Patient-specific RAG system using complete MIMIC-IV dataset + AWS Bedrock
"""

import boto3
from botocore.exceptions import ClientError
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import sys
import re
from datetime import datetime
from typing import Dict, List, Optional

# Configuration
class Config:
    AWS_REGION = 'us-east-1'
    KNOWLEDGE_BASE_ID = '0U6HHF7FWC'
    MODEL_ARN = 'arn:aws:bedrock:us-east-1:925445553569:inference-profile/us.deepseek.r1-v1:0'
    
    DB_HOST = 'localhost'
    DB_PORT = 5432
    DB_NAME = 'healthcare_rag'
    DB_USER = 'postgres'
    DB_PASSWORD = 'iJ9%hSH@3ukD11060D'


class PatientDataRetriever:
    """Retrieve comprehensive patient data from PostgreSQL"""
    
    def __init__(self):
        self.conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        self.cursor = self.conn.cursor()
    
    def validate_subject_id(self, subject_id: int) -> bool:
        """Check if subject_id exists"""
        self.cursor.execute(
            "SELECT COUNT(*) as count FROM patients WHERE subject_id = %s",
            (subject_id,)
        )
        result = self.cursor.fetchone()
        return result['count'] > 0
    
    def get_patient_profile(self, subject_id: int) -> Dict:
        """Get patient demographics and summary statistics"""
        self.cursor.execute("""
            SELECT 
                p.subject_id,
                p.gender,
                p.anchor_age,
                p.anchor_year_group,
                COUNT(DISTINCT a.hadm_id) as total_admissions,
                COUNT(DISTINCT d.icd_code) as unique_diagnoses,
                COUNT(DISTINCT i.stay_id) as icu_stays,
                COUNT(DISTINCT pr.drug) as unique_medications,
                MAX(a.admittime) as most_recent_admission,
                CASE WHEN p.dod IS NOT NULL THEN 'Deceased' ELSE 'Living' END as status
            FROM patients p
            LEFT JOIN admissions a ON p.subject_id = a.subject_id
            LEFT JOIN diagnoses_icd d ON p.subject_id = d.subject_id
            LEFT JOIN icustays i ON p.subject_id = i.subject_id
            LEFT JOIN prescriptions pr ON p.subject_id = pr.subject_id
            WHERE p.subject_id = %s
            GROUP BY p.subject_id, p.gender, p.anchor_age, p.anchor_year_group, p.dod
        """, (subject_id,))
        return self.cursor.fetchone()
    
    def get_recent_admissions(self, subject_id: int, limit: int = 3) -> List[Dict]:
        """Get recent hospital admissions with detailed info"""
        self.cursor.execute("""
            SELECT 
                a.hadm_id,
                a.admittime,
                a.dischtime,
                a.admission_type,
                a.admission_location,
                a.discharge_location,
                a.insurance,
                a.race,
                EXTRACT(EPOCH FROM (a.dischtime - a.admittime))/86400 as los_days,
                drg.drg_code,
                drg.description as drg_description,
                drg.drg_severity,
                drg.drg_mortality
            FROM admissions a
            LEFT JOIN drgcodes drg ON a.hadm_id = drg.hadm_id
            WHERE a.subject_id = %s
            ORDER BY a.admittime DESC
            LIMIT %s
        """, (subject_id, limit))
        return self.cursor.fetchall()
    
    def get_diagnoses(self, subject_id: int, limit: int = 10) -> List[Dict]:
        """Get diagnoses with full descriptions"""
        self.cursor.execute("""
            SELECT 
                d.icd_code,
                d.icd_version,
                dd.long_title,
                d.seq_num,
                COUNT(*) as occurrence_count,
                MAX(a.admittime) as most_recent
            FROM diagnoses_icd d
            LEFT JOIN d_icd_diagnoses dd ON d.icd_code = dd.icd_code AND d.icd_version = dd.icd_version
            LEFT JOIN admissions a ON d.hadm_id = a.hadm_id
            WHERE d.subject_id = %s
            GROUP BY d.icd_code, d.icd_version, dd.long_title, d.seq_num
            ORDER BY occurrence_count DESC, d.seq_num ASC
            LIMIT %s
        """, (subject_id, limit))
        return self.cursor.fetchall()
    
    def get_procedures(self, subject_id: int, limit: int = 10) -> List[Dict]:
        """Get procedures with descriptions"""
        self.cursor.execute("""
            SELECT 
                p.icd_code,
                dp.long_title,
                p.chartdate,
                COUNT(*) as occurrence_count
            FROM procedures_icd p
            LEFT JOIN d_icd_procedures dp ON p.icd_code = dp.icd_code AND p.icd_version = dp.icd_version
            WHERE p.subject_id = %s
            GROUP BY p.icd_code, dp.long_title, p.chartdate
            ORDER BY p.chartdate DESC
            LIMIT %s
        """, (subject_id, limit))
        return self.cursor.fetchall()
    
    def get_recent_labs(self, subject_id: int, limit: int = 15) -> List[Dict]:
        """Get recent lab results with abnormal flags"""
        self.cursor.execute("""
            SELECT 
                le.charttime,
                li.label,
                li.fluid,
                li.category,
                le.value,
                le.valuenum,
                le.valueuom,
                le.flag,
                le.ref_range_lower,
                le.ref_range_upper
            FROM labevents le
            LEFT JOIN d_labitems li ON le.itemid = li.itemid
            WHERE le.subject_id = %s
            AND le.charttime IS NOT NULL
            ORDER BY le.charttime DESC
            LIMIT %s
        """, (subject_id, limit))
        return self.cursor.fetchall()
    
    def get_medications(self, subject_id: int, limit: int = 15) -> List[Dict]:
        """Get prescribed medications"""
        self.cursor.execute("""
            SELECT 
                drug,
                drug_type,
                route,
                starttime,
                stoptime,
                dose_val_rx,
                dose_unit_rx,
                form_rx,
                gsn,
                ndc
            FROM prescriptions
            WHERE subject_id = %s
            AND drug IS NOT NULL
            ORDER BY starttime DESC
            LIMIT %s
        """, (subject_id, limit))
        return self.cursor.fetchall()
    
    def get_medication_administrations(self, subject_id: int, limit: int = 10) -> List[Dict]:
        """Get actual medication administration records (eMAR)"""
        self.cursor.execute("""
            SELECT 
                charttime,
                medication,
                event_txt,
                scheduletime
            FROM emar
            WHERE subject_id = %s
            AND medication IS NOT NULL
            ORDER BY charttime DESC
            LIMIT %s
        """, (subject_id, limit))
        return self.cursor.fetchall()
    
    def get_provider_orders(self, subject_id: int, limit: int = 10) -> List[Dict]:
        """Get provider orders (POE)"""
        self.cursor.execute("""
            SELECT 
                poe_id,
                ordertime,
                order_type,
                order_subtype,
                transaction_type,
                order_provider_id,
                order_status
            FROM poe
            WHERE subject_id = %s
            ORDER BY ordertime DESC
            LIMIT %s
        """, (subject_id, limit))
        return self.cursor.fetchall()
    
    def get_icu_stays(self, subject_id: int) -> List[Dict]:
        """Get ICU stay information"""
        self.cursor.execute("""
            SELECT 
                stay_id,
                hadm_id,
                first_careunit,
                last_careunit,
                intime,
                outtime,
                los as los_days
            FROM icustays
            WHERE subject_id = %s
            ORDER BY intime DESC
        """, (subject_id,))
        return self.cursor.fetchall()
    
    def get_icu_vitals(self, subject_id: int, limit: int = 20) -> List[Dict]:
        """Get ICU vital signs and assessments"""
        self.cursor.execute("""
            SELECT 
                ce.charttime,
                di.label,
                di.category,
                ce.value,
                ce.valuenum,
                ce.valueuom,
                CASE WHEN ce.warning = 1 THEN 'Warning' ELSE 'Normal' END as status
            FROM chartevents ce
            LEFT JOIN d_items di ON ce.itemid = di.itemid
            WHERE ce.subject_id = %s
            AND di.category IN ('Vital Signs', 'Labs', 'Respiratory')
            ORDER BY ce.charttime DESC
            LIMIT %s
        """, (subject_id, limit))
        return self.cursor.fetchall()
    
    def get_icu_inputs(self, subject_id: int, limit: int = 10) -> List[Dict]:
        """Get ICU fluid/medication inputs"""
        self.cursor.execute("""
            SELECT 
                ie.starttime,
                ie.endtime,
                di.label,
                ie.amount,
                ie.amountuom,
                ie.rate,
                ie.rateuom,
                ie.ordercategoryname,
                ie.statusdescription
            FROM inputevents ie
            LEFT JOIN d_items di ON ie.itemid = di.itemid
            WHERE ie.subject_id = %s
            ORDER BY ie.starttime DESC
            LIMIT %s
        """, (subject_id, limit))
        return self.cursor.fetchall()
    
    def build_patient_context(self, subject_id: int) -> str:
        """Build comprehensive patient context for AI with all available data"""
        profile = self.get_patient_profile(subject_id)
        admissions = self.get_recent_admissions(subject_id, 3)
        diagnoses = self.get_diagnoses(subject_id, 8)
        procedures = self.get_procedures(subject_id, 5)
        labs = self.get_recent_labs(subject_id, 12)
        medications = self.get_medications(subject_id, 10)
        med_admin = self.get_medication_administrations(subject_id, 8)
        orders = self.get_provider_orders(subject_id, 5)
        icu_stays = self.get_icu_stays(subject_id)
        vitals = self.get_icu_vitals(subject_id, 15)
        icu_inputs = self.get_icu_inputs(subject_id, 8)
        
        context = f"""
═══════════════════════════════════════════════════════════════════════════════
PATIENT CLINICAL RECORD (Subject ID: {subject_id})
═══════════════════════════════════════════════════════════════════════════════

DEMOGRAPHICS & SUMMARY:
├─ Gender: {profile['gender']}
├─ Age: {profile['anchor_age']} years
├─ Year Group: {profile['anchor_year_group']}
├─ Status: {profile['status']}
├─ Total Hospital Admissions: {profile['total_admissions']}
├─ ICU Stays: {profile['icu_stays']}
├─ Unique Diagnoses: {profile['unique_diagnoses']}
└─ Unique Medications: {profile['unique_medications']}

"""
        
        # Recent Admissions with DRG codes
        if admissions:
            context += "RECENT HOSPITAL ADMISSIONS:\n"
            for i, adm in enumerate(admissions, 1):
                los = f"{adm['los_days']:.1f} days" if adm['los_days'] else "Ongoing"
                drg_info = ""
                if adm['drg_code']:
                    drg_info = f"\n   DRG: {adm['drg_code']} - {adm['drg_description']}"
                    if adm['drg_severity']:
                        drg_info += f" (Severity: {adm['drg_severity']}, Mortality Risk: {adm['drg_mortality']})"
                
                context += f"{i}. {adm['admission_type']} admission on {adm['admittime'].strftime('%Y-%m-%d')}\n"
                context += f"   Location: {adm['admission_location']} → {adm['discharge_location']}\n"
                context += f"   LOS: {los}, Insurance: {adm['insurance']}{drg_info}\n"
            context += "\n"
        
        # Diagnoses
        if diagnoses:
            context += "DIAGNOSES (ICD-10 Codes with Descriptions):\n"
            for i, diag in enumerate(diagnoses, 1):
                title = diag['long_title'][:70] + '...' if diag['long_title'] and len(diag['long_title']) > 70 else diag['long_title']
                priority = f"[Seq {diag['seq_num']}]" if diag['seq_num'] else ""
                context += f"{i}. {diag['icd_code']} {priority} - {title or 'N/A'} ({diag['occurrence_count']}x)\n"
            context += "\n"
        
        # Procedures
        if procedures:
            context += "PROCEDURES PERFORMED:\n"
            for i, proc in enumerate(procedures, 1):
                title = proc['long_title'][:70] + '...' if proc['long_title'] and len(proc['long_title']) > 70 else proc['long_title']
                date = proc['chartdate'].strftime('%Y-%m-%d') if proc['chartdate'] else 'Unknown'
                context += f"{i}. {proc['icd_code']} - {title or 'N/A'} (Date: {date})\n"
            context += "\n"
        
        # Lab Results
        if labs:
            context += "RECENT LABORATORY RESULTS:\n"
            for i, lab in enumerate(labs, 1):
                label = lab['label'] or "Lab Test"
                category = f"[{lab['category']}]" if lab['category'] else ""
                value = lab['value'] or (f"{lab['valuenum']}" if lab['valuenum'] else "N/A")
                unit = lab['valueuom'] or ''
                
                # Abnormal flag with reference ranges
                flag_info = ""
                if lab['flag'] and lab['flag'].lower() == 'abnormal':
                    flag_info = "  ABNORMAL"
                    if lab['ref_range_lower'] or lab['ref_range_upper']:
                        flag_info += f" (Ref: {lab['ref_range_lower'] or '?'}-{lab['ref_range_upper'] or '?'})"
                
                date = lab['charttime'].strftime('%Y-%m-%d %H:%M') if lab['charttime'] else 'Unknown'
                context += f"{i}. {label} {category}: {value} {unit}{flag_info} ({date})\n"
            context += "\n"
        
        # Medications
        if medications:
            context += "PRESCRIBED MEDICATIONS:\n"
            for i, med in enumerate(medications, 1):
                dose = f"{med['dose_val_rx']} {med['dose_unit_rx']}" if med['dose_val_rx'] else ""
                route = f"via {med['route']}" if med['route'] else ""
                drug_type = f"[{med['drug_type']}]" if med['drug_type'] else ""
                start = med['starttime'].strftime('%Y-%m-%d') if med['starttime'] else 'Unknown'
                context += f"{i}. {med['drug']} {dose} {route} {drug_type} (Started: {start})\n"
            context += "\n"
        
        # Medication Administration
        if med_admin:
            context += "MEDICATION ADMINISTRATION RECORDS (eMAR):\n"
            for i, admin in enumerate(med_admin, 1):
                status = admin['event_txt'] or 'Administered'
                time = admin['charttime'].strftime('%Y-%m-%d %H:%M') if admin['charttime'] else 'Unknown'
                context += f"{i}. {admin['medication']} - {status} ({time})\n"
            context += "\n"
        
        # Provider Orders
        if orders:
            context += "PROVIDER ORDERS (POE):\n"
            for i, order in enumerate(orders, 1):
                order_time = order['ordertime'].strftime('%Y-%m-%d %H:%M') if order['ordertime'] else 'Unknown'
                order_type = order['order_type'] or 'Order'
                if order['order_subtype']:
                    order_type += f" - {order['order_subtype']}"
                status = order['order_status'] or 'Unknown'
                provider = f" by {order['order_provider_id']}" if order['order_provider_id'] else ""
                context += f"{i}. {order_type} [{status}]{provider} ({order_time})\n"
            context += "\n"
        
        # ICU Stays
        if icu_stays:
            context += "INTENSIVE CARE UNIT STAYS:\n"
            for i, stay in enumerate(icu_stays, 1):
                los = f"{stay['los_days']:.1f} days" if stay['los_days'] else "Ongoing"
                intime = stay['intime'].strftime('%Y-%m-%d %H:%M') if stay['intime'] else 'Unknown'
                context += f"{i}. ICU Stay ID {stay['stay_id']}: {stay['first_careunit']} → {stay['last_careunit']}\n"
                context += f"   Admitted: {intime}, LOS: {los}\n"
            context += "\n"
            
            # ICU Vitals
            if vitals:
                context += "   Recent ICU Vital Signs:\n"
                for v in vitals[:10]:
                    time = v['charttime'].strftime('%Y-%m-%d %H:%M') if v['charttime'] else 'Unknown'
                    value = v['value'] or (f"{v['valuenum']}" if v['valuenum'] else "N/A")
                    unit = v['valueuom'] or ''
                    status = f" [{v['status']}]" if v['status'] == 'Warning' else ""
                    context += f"   • {v['label']}: {value} {unit}{status} ({time})\n"
                context += "\n"
            
            # ICU Inputs
            if icu_inputs:
                context += "   ICU Fluid/Medication Inputs:\n"
                for inp in icu_inputs[:8]:
                    start = inp['starttime'].strftime('%Y-%m-%d %H:%M') if inp['starttime'] else 'Unknown'
                    amount = f"{inp['amount']} {inp['amountuom']}" if inp['amount'] else ""
                    rate = f"@ {inp['rate']} {inp['rateuom']}" if inp['rate'] else ""
                    category = inp['ordercategoryname'] or 'Unknown'
                    context += f"   • {inp['label']} ({category}): {amount} {rate} (Started: {start})\n"
                context += "\n"
        
        context += "═══════════════════════════════════════════════════════════════════════════════\n"
        
        return context
    
    def close(self):
        self.cursor.close()
        self.conn.close()


class HealthcareAssistant:
    """RAG assistant with hybrid query routing (direct vs KB)"""
    
    def __init__(self, subject_id: int):
        self.subject_id = subject_id
        self.bedrock_client = boto3.client(
            'bedrock-agent-runtime',
            region_name=Config.AWS_REGION
        )
        self.patient_retriever = PatientDataRetriever()
        self.conversation_history = []
        self.session_id = None
        self.patient_context = self.patient_retriever.build_patient_context(subject_id)
    
    def query(self, user_question: str) -> Dict:
        """Route query to appropriate backend (direct or KB)"""
        start_time = datetime.now()
        
        # Determine query type
        is_patient_specific = self._is_patient_specific_question(user_question)
        
        query_type = "Patient-specific (direct)" if is_patient_specific else "General medical (KB)"
        print(f"[DEBUG] Query type: {query_type}")
        
        if is_patient_specific:
            return self._query_direct(user_question, start_time)
        else:
            return self._query_with_kb(user_question, start_time)
    
    def _is_patient_specific_question(self, user_question: str) -> bool:
        """Determine if question is about patient data vs general medical knowledge"""
        q_lower = user_question.lower()
        
        # Strong indicators this is about the patient's own data
        patient_indicators = [
            'my ', 'i was', 'was i', 'did i', 'when did i', 'have i',
            'am i', 'do i have', 'what did i', 'where was i',
            'this', 'that', 'said', 'those', 'these',
            'at these', 'during this', 'for this', 'for those',
            'prescribed to me', 'diagnosed with', 'admitted for',
            'most recent', 'last time', 'latest'
        ]
        
        # If it's clearly asking about patient's specific records
        if any(indicator in q_lower for indicator in patient_indicators):
            return True
        
        # General medical knowledge questions (no patient context)
        general_indicators = [
            'what does ', 'what is ', 'what are ', 'how does ', 'why does ',
            'explain ', 'define ', 'what causes ',
            'side effects of', 'symptoms of', 'treatment for',
            'difference between', 'types of',
            'used for', 'work', 'mechanism'
        ]
        
        # If asking general questions without patient context
        if any(indicator in q_lower for indicator in general_indicators):
            # Check if there's patient context in the question
            has_patient_context = any(p in q_lower for p in ['my', 'i ', 'me', 'this', 'that', 'these', 'those'])
            if not has_patient_context:
                return False  # Use KB for general medical knowledge
        
        # Default to patient-specific for ambiguous cases
        return True

    
    def _query_direct(self, user_question: str, start_time: datetime) -> Dict:
        """Direct DeepSeek query for patient-specific questions"""
        try:
            bedrock_runtime = boto3.client('bedrock-runtime', region_name=Config.AWS_REGION)
            
            prompt = self._build_full_context_prompt(user_question)
            
            # Call DeepSeek R1 directly (no KB)
            request_body = {
                "messages": [{
                    "role": "user",
                    "content": prompt
                }],
                "max_tokens": 3000,
                "temperature": 0.7
            }
            
            response = bedrock_runtime.invoke_model(
                modelId=Config.MODEL_ARN,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            
            # Parse DeepSeek response (try multiple formats)
            if 'content' in response_body:
                if isinstance(response_body['content'], list):
                    answer = response_body['content'][0].get('text', str(response_body['content'][0]))
                else:
                    answer = response_body['content']
            elif 'choices' in response_body:
                answer = response_body['choices'][0]['message']['content']
            elif 'completion' in response_body:
                answer = response_body['completion']
            else:
                print(f"[DEBUG] Unexpected DeepSeek response format: {list(response_body.keys())}")
                answer = str(response_body)
            
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            self._update_memory(user_question, answer)
            
            self._save_to_database(
                question=user_question,
                answer=answer,
                citations=[],
                response_time_ms=response_time_ms,
                success=True,
                error_message=None
            )
            
            return {
                'success': True,
                'answer': answer,
                'citations': [],
                'session_id': 'direct-query',
                'response_time_ms': response_time_ms,
                'query_type': 'direct'
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            self._save_to_database(
                question=user_question,
                answer=None,
                citations=[],
                response_time_ms=response_time_ms,
                success=False,
                error_message=f"{error_code}: {error_message}"
            )
            
            return {
                'success': False,
                'error': f"{error_code}: {error_message}",
                'response_time_ms': response_time_ms
            }
            
        except Exception as e:
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            self._save_to_database(
                question=user_question,
                answer=None,
                citations=[],
                response_time_ms=response_time_ms,
                success=False,
                error_message=str(e)
            )
            
            return {
                'success': False,
                'error': f"Error: {str(e)}",
                'response_time_ms': response_time_ms
            }
    
    def _query_with_kb(self, user_question: str, start_time: datetime) -> Dict:
        """KB-based query for general medical knowledge questions"""
        try:
            augmented_question = self._build_full_context_prompt(user_question)
            
            config = {
                'input': {'text': augmented_question},
                'retrieveAndGenerateConfiguration': {
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': Config.KNOWLEDGE_BASE_ID,
                        'modelArn': Config.MODEL_ARN
                    }
                }
            }
            
            if self.session_id and self.session_id != 'direct-query':
                config['sessionId'] = self.session_id
            
            response = self.bedrock_client.retrieve_and_generate(**config)
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            self.session_id = response.get('sessionId')
            answer = response['output']['text']
            citations = response.get('citations', [])
            
            self._update_memory(user_question, answer)
            
            self._save_to_database(
                question=user_question,
                answer=answer,
                citations=citations,
                response_time_ms=response_time_ms,
                success=True,
                error_message=None
            )
            
            return {
                'success': True,
                'answer': answer,
                'citations': citations,
                'session_id': self.session_id,
                'response_time_ms': response_time_ms,
                'query_type': 'kb'
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            self._save_to_database(
                question=user_question,
                answer=None,
                citations=[],
                response_time_ms=response_time_ms,
                success=False,
                error_message=f"{error_code}: {error_message}"
            )
            
            return {
                'success': False,
                'error': f"{error_code}: {error_message}",
                'response_time_ms': response_time_ms
            }
            
        except Exception as e:
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            self._save_to_database(
                question=user_question,
                answer=None,
                citations=[],
                response_time_ms=response_time_ms,
                success=False,
                error_message=str(e)
            )
            
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}",
                'response_time_ms': response_time_ms
            }
    
    def _save_to_database(self, question: str, answer: str, citations: list, 
                        response_time_ms: int, success: bool, error_message: str):
        """Save query to PostgreSQL for audit trail and analytics"""
        try:
            if not self.subject_id:
                print(f"\n  Warning: No subject_id set, skipping database save")
                return
            
            self.patient_retriever.cursor.execute("""
                INSERT INTO kb_queries 
                (subject_id, query_text, response_text, session_id, 
                response_time_ms, citation_count, success, error_message, 
                model_arn, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING query_id
            """, (
                self.subject_id,
                question,
                answer,
                self.session_id,
                response_time_ms,
                len(citations) if citations else 0,
                success,
                error_message,
                Config.MODEL_ARN,
                datetime.now()
            ))
            
            result = self.patient_retriever.cursor.fetchone()
            
            if not result or 'query_id' not in result:
                print(f"\n  Warning: Failed to get query_id from database")
                self.patient_retriever.conn.rollback()
                return
            
            query_id = result['query_id']
            
            if not query_id:
                print(f"\n  Warning: Invalid query_id: {query_id}")
                self.patient_retriever.conn.rollback()
                return
            
            # Insert citation records
            if citations and success:
                for citation in citations:
                    refs = citation.get('retrievedReferences', [])
                    for ref in refs:
                        source_uri = ref.get('location', {}).get('s3Location', {}).get('uri', '')
                        source_document = source_uri.split('/')[-1] if source_uri else 'Unknown'
                        excerpt = ref.get('content', {}).get('text', '')
                        
                        metadata = {
                            's3_uri': source_uri,
                            'reference_type': ref.get('location', {}).get('type', 'S3')
                        }
                        
                        self.patient_retriever.cursor.execute("""
                            INSERT INTO kb_citations 
                            (query_id, source_document, excerpt_text, metadata, created_at)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            query_id,
                            source_document,
                            excerpt[:1000] if excerpt else None,
                            json.dumps(metadata),
                            datetime.now()
                        ))
            
            self.patient_retriever.conn.commit()
            
        except psycopg2.Error as e:
            print(f"\n  Warning: PostgreSQL error - {e}")
            try:
                self.patient_retriever.conn.rollback()
            except:
                pass
                
        except Exception as e:
            print(f"\n  Warning: Failed to save query to database: {e}")
            try:
                self.patient_retriever.conn.rollback()
            except:
                pass
    
    def _build_full_context_prompt(self, user_question: str) -> str:
        """Build comprehensive prompt with patient data + conversation history"""
        prompt = ""
        
        # Add conversation history if exists
        if self.conversation_history:
            last_a = self.conversation_history[-1]['answer']
            
            prompt += "═══════════════════════════════════════════════════════════════════════════════\n"
            prompt += " CONVERSATION CONTEXT (User is asking a follow-up question)\n"
            prompt += "═══════════════════════════════════════════════════════════════════════════════\n\n"
            
            prompt += f"Previous Question: {self.conversation_history[-1]['question']}\n\n"
            prompt += f"Previous Answer:\n{last_a}\n\n"
            
            prompt += "═══════════════════════════════════════════════════════════════════════════════\n\n"
            
            # Extract dates mentioned in previous answer
            dates = re.findall(r'\d{4}-\d{2}-\d{2}', last_a)
            
            if dates:
                prompt += f"  IMPORTANT: The previous answer mentioned dates: {', '.join(set(dates))}\n"
                prompt += f"The current question likely refers to events on or around these dates.\n"
                prompt += f"CHECK THE PATIENT'S MEDICATION DATA BELOW FOR THESE DATES.\n\n"
        
        # Add full patient context
        prompt += self.patient_context
        
        # Current question
        prompt += f"\n═══════════════════════════════════════════════════════════════════════════════\n"
        prompt += f"CURRENT QUESTION: {user_question}\n"
        prompt += f"═══════════════════════════════════════════════════════════════════════════════\n\n"
        
        if self.conversation_history:
            prompt += "  CRITICAL INSTRUCTIONS:\n"
            prompt += "- This is a FOLLOW-UP question referring to the previous conversation\n"
            prompt += "- Words like 'this', 'that', 'said procedure' refer to information from the previous answer\n"
            prompt += "- USE THE PATIENT'S ACTUAL MEDICATION DATA shown in the clinical record above\n"
            prompt += "- DO NOT say 'no information available' if medications are listed in the patient record\n"
            prompt += "- Look at PRESCRIBED MEDICATIONS and MEDICATION ADMINISTRATION RECORDS sections\n"
        
        return prompt
    
    def _update_memory(self, question: str, answer: str):
        self.conversation_history.append({
            'question': question,
            'answer': answer,
            'timestamp': datetime.now()
        })
    
    def get_conversation_summary(self) -> str:
        duration = (datetime.now() - self.conversation_history[0]['timestamp']).seconds if self.conversation_history else 0
        return f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║ SESSION SUMMARY FOR PATIENT {self.subject_id}                                      
╚══════════════════════════════════════════════════════════════════════════════╝

Questions Asked: {len(self.conversation_history)}
Session ID: {self.session_id or 'Not started'}
Duration: {duration} seconds ({duration // 60} minutes)
"""
    
    def close(self):
        self.patient_retriever.close()


def print_header():
    print("\n" + "="*80)
    print("🏥 HEALTHCARE ASSISTANT - MIMIC-IV Clinical Intelligence System")
    print("="*80)
    print("Powered by AWS Bedrock (DeepSeek R1) + Complete MIMIC-IV Database")
    print("Hybrid Query: Direct for patient data | KB for medical knowledge")
    print("="*80 + "\n")


def print_patient_summary(assistant: HealthcareAssistant):
    print("\n" + assistant.patient_context)


def main():
    print_header()
    
    # Get Subject ID
    while True:
        try:
            subject_id_input = input("Enter MIMIC-IV Subject ID (or 'quit'): ").strip()
            
            if subject_id_input.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye! \n")
                sys.exit(0)
            
            subject_id = int(subject_id_input)
            
            # Validate
            retriever = PatientDataRetriever()
            if not retriever.validate_subject_id(subject_id):
                print(f" Subject ID {subject_id} not found in database.\n")
                retriever.close()
                continue
            
            retriever.close()
            break
            
        except ValueError:
            print(" Please enter a valid numeric Subject ID.\n")
        except Exception as e:
            print(f" Database error: {str(e)}\n")
            sys.exit(1)
    
    # Initialize Assistant
    print(f"\n Loading complete clinical record for Subject ID: {subject_id}...\n")
    
    try:
        assistant = HealthcareAssistant(subject_id)
    except Exception as e:
        print(f" Error initializing assistant: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Show Full Patient Profile
    print_patient_summary(assistant)
    
    # Interactive Loop
    print("\nAsk clinical questions about this patient or general healthcare topics.")
    print("Commands: 'summary' = session stats | 'profile' = show patient data | 'quit' = exit\n")
    
    while True:
        try:
            question = input("\n🔍 Your question: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ['quit', 'exit', 'q']:
                print(assistant.get_conversation_summary())
                print("\nThank you for using Healthcare Assistant. Goodbye! \n")
                assistant.close()
                break
            
            if question.lower() == 'summary':
                print(assistant.get_conversation_summary())
                continue
            
            if question.lower() == 'profile':
                print_patient_summary(assistant)
                continue
            
            # Query Assistant
            print("\n Analyzing patient data and retrieving relevant medical knowledge...")
            result = assistant.query(question)
            
            if result['success']:
                print("\n" + "─"*80)
                print(" CLINICAL ANSWER:")
                print("─"*80)
                print(result['answer'])
                
                # Show query type and response time
                query_type_icon = "🔍" if result.get('query_type') == 'kb' else "📊"
                query_type_text = "Knowledge Base" if result.get('query_type') == 'kb' else "Patient Data"
                print(f"\n{query_type_icon} Query type: {query_type_text}")
                print(f"  Response time: {result['response_time_ms']}ms")
                
                if result['citations']:
                    print("\n📚 KNOWLEDGE SOURCES:")
                    seen_sources = set()
                    for i, citation in enumerate(result['citations'], 1):
                        refs = citation.get('retrievedReferences', [])
                        for ref in refs:
                            source = ref.get('location', {}).get('s3Location', {}).get('uri', '')
                            if source:
                                source_name = source.split('/')[-1]
                                if source_name not in seen_sources:
                                    print(f"  [{i}] {source_name}")
                                    seen_sources.add(source_name)
                
                print("─"*80)
            else:
                print(f"\n Error: {result['error']}")
                if 'response_time_ms' in result:
                    print(f"⏱  Failed after: {result['response_time_ms']}ms\n")
        
        except KeyboardInterrupt:
            print("\n" + assistant.get_conversation_summary())
            print("\nInterrupted. Goodbye! \n")
            assistant.close()
            break
        except Exception as e:
            print(f"\n Unexpected error: {str(e)}\n")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
