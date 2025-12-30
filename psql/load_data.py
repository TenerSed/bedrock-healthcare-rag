"""
MIMIC-IV Complete Loader - Full Implementation
Loads all hosp + icu module tables
"""

import kagglehub
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
from pathlib import Path
import sys
from datetime import datetime

DB_CONFIG = {
		'host': 'localhost',
		'port': 5432,
		'database': 'healthcare_rag',
		'user': 'postgres',
		'password': 'iJ9%hSH@3ukD11060D'
}

KAGGLE_DATASET = "montassarba/mimic-iv-clinical-database-demo-2-2"


class MIMICLoader:
		def __init__(self, db_config):
				self.db_config = db_config
				self.conn = None
				self.cursor = None
				self.data_path = None
				self.hosp_path = None
				self.icu_path = None
		
		def connect_db(self):
				print(" Connecting to PostgreSQL...")
				self.conn = psycopg2.connect(**self.db_config)
				self.cursor = self.conn.cursor()
				print(" Connected\n")
		
		def download_dataset(self):
				print(" Downloading from Kaggle...\n")
				self.data_path = Path(kagglehub.dataset_download(KAGGLE_DATASET))
				self.hosp_path = self.data_path / 'hosp'
				self.icu_path = self.data_path / 'icu'
				
				if not self.hosp_path.exists():
						matches = list(self.data_path.rglob('hosp'))
						self.hosp_path = matches[0] if matches else self.data_path
				if not self.icu_path.exists():
						matches = list(self.data_path.rglob('icu'))
						self.icu_path = matches[0] if matches else self.data_path
				
				print(f" Dataset: {self.data_path}")
				print(f"   hosp: {self.hosp_path}")
				print(f"   icu:  {self.icu_path}\n")
				return True
		
		def _h(self, f): return self.hosp_path / f
		def _i(self, f): return self.icu_path / f
		
		def _safe(self, val, typ='str'):
				if pd.isna(val): return None
				try:
						if typ == 'int': return int(val)
						if typ == 'float': return float(val)
						if typ == 'ts': return pd.to_datetime(val)
						if typ == 'date': return pd.to_datetime(val).date()
						return str(val)
				except:
						return None
		
		# === HOSP MODULE ===
		
		def load_patients(self):
				print(" patients...")
				df = pd.read_csv(self._h('patients.csv'))
				data = [(
						self._safe(r['subject_id'], 'int'),
						self._safe(r.get('gender')),
						self._safe(r.get('anchor_age'), 'int'),
						self._safe(r.get('anchor_year'), 'int'),
						self._safe(r.get('anchor_year_group')),
						self._safe(r.get('dod'), 'date')
				) for _, r in df.iterrows()]
				
				execute_batch(self.cursor, """
						INSERT INTO patients (subject_id, gender, anchor_age, anchor_year, anchor_year_group, dod)
						VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
				""", data, page_size=100)
				self.conn.commit()
				print(f"    {len(data)} rows\n")
		
		def load_admissions(self):
				print(" admissions...")
				df = pd.read_csv(self._h('admissions.csv'))
				data = [(
						self._safe(r['hadm_id'], 'int'),
						self._safe(r['subject_id'], 'int'),
						self._safe(r.get('admittime'), 'ts'),
						self._safe(r.get('dischtime'), 'ts'),
						self._safe(r.get('deathtime'), 'ts'),
						self._safe(r.get('admission_type')),
						self._safe(r.get('admit_provider_id')),
						self._safe(r.get('admission_location')),
						self._safe(r.get('discharge_location')),
						self._safe(r.get('insurance')),
						self._safe(r.get('language')),
						self._safe(r.get('marital_status')),
						self._safe(r.get('race', r.get('ethnicity'))),
						self._safe(r.get('edregtime'), 'ts'),
						self._safe(r.get('edouttime'), 'ts'),
						self._safe(r.get('hospital_expire_flag'), 'int')
				) for _, r in df.iterrows()]
				
				execute_batch(self.cursor, """
						INSERT INTO admissions 
						(hadm_id, subject_id, admittime, dischtime, deathtime, admission_type,
						 admit_provider_id, admission_location, discharge_location, insurance,
						 language, marital_status, race, edregtime, edouttime, hospital_expire_flag)
						VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
				""", data, page_size=100)
				self.conn.commit()
				print(f"    {len(data)} rows\n")
		
		def load_transfers(self):
				print(" transfers...")
				path = self._h('transfers.csv')
				if not path.exists():
						print(f"    transfers.csv not found\n")
						return
				
				df = pd.read_csv(path)
				data = [(
						self._safe(r['subject_id'], 'int'),
						self._safe(r.get('hadm_id'), 'int'),
						self._safe(r.get('transfer_id'), 'int'),
						self._safe(r.get('eventtype')),
						self._safe(r.get('careunit')),
						self._safe(r.get('intime'), 'ts'),
						self._safe(r.get('outtime'), 'ts')
				) for _, r in df.iterrows()]
				
				execute_batch(self.cursor, """
						INSERT INTO transfers (subject_id, hadm_id, transfer_id_orig, eventtype, careunit, intime, outtime)
						VALUES (%s,%s,%s,%s,%s,%s,%s)
				""", data, page_size=500)
				self.conn.commit()
				print(f"   {len(data)} rows\n")
		
		def load_d_labitems(self):
				print(" d_labitems...")
				path = self._h('d_labitems.csv')
				if not path.exists():
						print(f"    d_labitems.csv not found\n")
						return
		
				df = pd.read_csv(path)
				data = []
				for _, r in df.iterrows():
						# Provide default label if missing
						label = self._safe(r.get('label'))
						if label is None or label == '':
								label = f"Lab Item {r['itemid']}"  # Default label using itemid
						
						data.append((
								self._safe(r['itemid'], 'int'),
								label,  # Now guaranteed to be non-null
								self._safe(r.get('fluid')),
								self._safe(r.get('category')),
								self._safe(r.get('loinc_code'))
						))
				
				execute_batch(self.cursor, """
						INSERT INTO d_labitems (itemid, label, fluid, category, loinc_code)
						VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
				""", data, page_size=500)
				self.conn.commit()
				print(f"   {len(data)} rows\n")

		
		def load_labevents(self, limit=108000):
				print("🧪 labevents...")
				path = self._h('labevents.csv')
				if not path.exists():
						print(f"    labevents.csv not found\n")
						return
				
				df = pd.read_csv(path)
				if len(df) > limit:
						print(f"   Limiting to {limit} rows (total: {len(df)})")
						df = df.head(limit)
				
				data = [(
						self._safe(r['subject_id'], 'int'),
						self._safe(r.get('hadm_id'), 'int'),
						self._safe(r.get('specimen_id'), 'int'),
						self._safe(r['itemid'], 'int'),
						self._safe(r.get('charttime'), 'ts'),
						self._safe(r.get('storetime'), 'ts'),
						self._safe(r.get('value')),
						self._safe(r.get('valuenum'), 'float'),
						self._safe(r.get('valueuom')),
						self._safe(r.get('ref_range_lower'), 'float'),
						self._safe(r.get('ref_range_upper'), 'float'),
						self._safe(r.get('flag')),
						self._safe(r.get('priority')),
						self._safe(r.get('comments'))
				) for _, r in df.iterrows()]
				
				execute_batch(self.cursor, """
						INSERT INTO labevents 
						(subject_id, hadm_id, specimen_id, itemid, charttime, storetime, value,
						 valuenum, valueuom, ref_range_lower, ref_range_upper, flag, priority, comments)
						VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
				""", data, page_size=1000)
				self.conn.commit()
				print(f"   {len(data)} rows\n")
		
		def load_d_icd_diagnoses(self):
				print(" d_icd_diagnoses...")
				path = self._h('d_icd_diagnoses.csv')
				if not path.exists():
						print(f"    d_icd_diagnoses.csv not found\n")
						return
				
				df = pd.read_csv(path)
				data = [(
						self._safe(r['icd_code']),
						self._safe(r.get('icd_version', 10), 'int'),
						self._safe(r.get('long_title'))
				) for _, r in df.iterrows()]
				
				execute_batch(self.cursor, """
						INSERT INTO d_icd_diagnoses (icd_code, icd_version, long_title)
						VALUES (%s,%s,%s) ON CONFLICT DO NOTHING
				""", data, page_size=500)
				self.conn.commit()
				print(f"   {len(data)} rows\n")
		
		def load_diagnoses_icd(self):
				print(" diagnoses_icd...")
				path = self._h('diagnoses_icd.csv')
				if not path.exists():
						print(f"    diagnoses_icd.csv not found\n")
						return
				
				df = pd.read_csv(path)
				data = [(
						self._safe(r['subject_id'], 'int'),
						self._safe(r['hadm_id'], 'int'),
						self._safe(r.get('seq_num'), 'int'),
						self._safe(r['icd_code']),
						self._safe(r.get('icd_version', 10), 'int')
				) for _, r in df.iterrows()]
				
				execute_batch(self.cursor, """
						INSERT INTO diagnoses_icd (subject_id, hadm_id, seq_num, icd_code, icd_version)
						VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
				""", data, page_size=500)
				self.conn.commit()
				print(f"   {len(data)} rows\n")
		
		def load_d_icd_procedures(self):
				print("📖 d_icd_procedures...")
				path = self._h('d_icd_procedures.csv')
				if not path.exists():
						print(f"    d_icd_procedures.csv not found\n")
						return
				
				df = pd.read_csv(path)
				data = [(
						self._safe(r['icd_code']),
						self._safe(r.get('icd_version', 10), 'int'),
						self._safe(r.get('long_title'))
				) for _, r in df.iterrows()]
				
				execute_batch(self.cursor, """
						INSERT INTO d_icd_procedures (icd_code, icd_version, long_title)
						VALUES (%s,%s,%s) ON CONFLICT DO NOTHING
				""", data, page_size=500)
				self.conn.commit()
				print(f"   {len(data)} rows\n")
		
		def load_procedures_icd(self):
				print("  procedures_icd...")
				path = self._h('procedures_icd.csv')
				if not path.exists():
						print(f"    procedures_icd.csv not found\n")
						return
				
				df = pd.read_csv(path)
				data = [(
						self._safe(r['subject_id'], 'int'),
						self._safe(r['hadm_id'], 'int'),
						self._safe(r.get('seq_num'), 'int'),
						self._safe(r.get('chartdate'), 'date'),
						self._safe(r['icd_code']),
						self._safe(r.get('icd_version', 10), 'int')
				) for _, r in df.iterrows()]
				
				execute_batch(self.cursor, """
						INSERT INTO procedures_icd (subject_id, hadm_id, seq_num, chartdate, icd_code, icd_version)
						VALUES (%s,%s,%s,%s,%s,%s)
				""", data, page_size=500)
				self.conn.commit()
				print(f"   {len(data)} rows\n")
		
		def load_prescriptions(self, limit=20000):
				print(" prescriptions...")
				path = self._h('prescriptions.csv')
				if not path.exists():
						print(f"    prescriptions.csv not found\n")
						return
				
				df = pd.read_csv(path)
				if len(df) > limit:
						print(f"   Limiting to {limit} rows (total: {len(df)})")
						df = df.head(limit)
				
				data = [(
						self._safe(r['subject_id'], 'int'),
						self._safe(r.get('hadm_id'), 'int'),
						self._safe(r.get('pharmacy_id'), 'int'),
						self._safe(r.get('poe_id')),
						self._safe(r.get('poe_seq'), 'int'),
						self._safe(r.get('starttime'), 'ts'),
						self._safe(r.get('stoptime'), 'ts'),
						self._safe(r.get('drug_type')),
						self._safe(r.get('drug')),
						self._safe(r.get('gsn')),
						self._safe(r.get('ndc')),
						self._safe(r.get('prod_strength')),
						self._safe(r.get('form_rx')),
						self._safe(r.get('dose_val_rx')),
						self._safe(r.get('dose_unit_rx')),
						self._safe(r.get('form_val_disp')),
						self._safe(r.get('form_unit_disp')),
						self._safe(r.get('doses_per_24_hrs'), 'float'),
						self._safe(r.get('route'))
				) for _, r in df.iterrows()]
				
				execute_batch(self.cursor, """
						INSERT INTO prescriptions 
						(subject_id, hadm_id, pharmacy_id, poe_id, poe_seq, starttime, stoptime,
						 drug_type, drug, gsn, ndc, prod_strength, form_rx, dose_val_rx, dose_unit_rx,
						 form_val_disp, form_unit_disp, doses_per_24_hrs, route)
						VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
				""", data, page_size=500)
				self.conn.commit()
				print(f"   {len(data)} rows\n")
		
		def load_emar(self, limit=40000):
			"""Load medication administration records (eMAR)"""
			print(" emar...")
			path = self._h('emar.csv')
			if not path.exists():
					print(f"    emar.csv not found\n")
					return
			
			df = pd.read_csv(path)
			if len(df) > limit:
					print(f"   Limiting to {limit} rows (total: {len(df)})")
					df = df.head(limit)
			
			data = [(
					self._safe(r['subject_id'], 'int'),
					self._safe(r.get('hadm_id'), 'int'),
					self._safe(r.get('emar_id')),
					self._safe(r.get('emar_seq'), 'int'),
					self._safe(r.get('poe_id')),
					self._safe(r.get('pharmacy_id'), 'int'),
					self._safe(r.get('charttime'), 'ts'),
					self._safe(r.get('medication')),
					self._safe(r.get('event_txt')),
					self._safe(r.get('scheduletime'), 'ts'),
					self._safe(r.get('storetime'), 'ts')
			) for _, r in df.iterrows()]
			
			execute_batch(self.cursor, """
					INSERT INTO emar 
					(subject_id, hadm_id, emar_id, emar_seq, poe_id, pharmacy_id, 
					charttime, medication, event_txt, scheduletime, storetime)
					VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
			""", data, page_size=500)
			self.conn.commit()
			print(f"   {len(data)} rows\n")
		
		def load_poe(self, limit=46000):
			"""Load provider order entry"""
			print("📝 poe...")
			path = self._h('poe.csv')
			if not path.exists():
					print(f"    poe.csv not found\n")
					return
			
			df = pd.read_csv(path)
			if len(df) > limit:
					print(f"   Limiting to {limit} rows (total: {len(df)})")
					df = df.head(limit)
			
			data = [(
					self._safe(r.get('poe_id')),
					self._safe(r.get('poe_seq'), 'int'),
					self._safe(r['subject_id'], 'int'),
					self._safe(r.get('hadm_id'), 'int'),
					self._safe(r.get('ordertime'), 'ts'),
					self._safe(r.get('order_type')),
					self._safe(r.get('order_subtype')),
					self._safe(r.get('transaction_type')),
					self._safe(r.get('discontinue_of_poe_id')),
					self._safe(r.get('discontinued_by_poe_id')),
					self._safe(r.get('order_provider_id')),
					self._safe(r.get('order_status'))
			) for _, r in df.iterrows()]
			
			execute_batch(self.cursor, """
					INSERT INTO poe 
					(poe_id, poe_seq, subject_id, hadm_id, ordertime, order_type, 
					order_subtype, transaction_type, discontinue_of_poe_id, 
					discontinued_by_poe_id, order_provider_id, order_status)
					VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
			""", data, page_size=500)
			self.conn.commit()
			print(f"   {len(data)} rows\n")
   
		def load_drgcodes(self):
			"""Load DRG (Diagnosis Related Group) codes"""
			print("💰 drgcodes...")
			path = self._h('drgcodes.csv')
			if not path.exists():
					print(f"    drgcodes.csv not found\n")
					return
			
			df = pd.read_csv(path)
			data = [(
					self._safe(r['subject_id'], 'int'),
					self._safe(r['hadm_id'], 'int'),
					self._safe(r.get('drg_type')),
					self._safe(r.get('drg_code')),
					self._safe(r.get('description')),
					self._safe(r.get('drg_severity'), 'int'),
					self._safe(r.get('drg_mortality'), 'int')
			) for _, r in df.iterrows()]
			
			execute_batch(self.cursor, """
					INSERT INTO drgcodes 
					(subject_id, hadm_id, drg_type, drg_code, description, 
					drg_severity, drg_mortality)
					VALUES (%s,%s,%s,%s,%s,%s,%s)
			""", data, page_size=500)
			self.conn.commit()
			print(f"   {len(data)} rows\n")
   
		# === ICU MODULE ===
		
		def load_d_items(self):
				print(" d_items...")
				path = self._i('d_items.csv')
				if not path.exists():
						print(f"    d_items.csv not found\n")
						return
				
				df = pd.read_csv(path)
				data = [(
						self._safe(r['itemid'], 'int'),
						self._safe(r.get('label')),
						self._safe(r.get('abbreviation')),
						self._safe(r.get('linksto')),
						self._safe(r.get('category')),
						self._safe(r.get('unitname')),
						self._safe(r.get('param_type')),
						self._safe(r.get('lownormalvalue'), 'float'),
						self._safe(r.get('highnormalvalue'), 'float')
				) for _, r in df.iterrows()]
				
				execute_batch(self.cursor, """
						INSERT INTO d_items (itemid, label, abbreviation, linksto, category, unitname, param_type, lownormalvalue, highnormalvalue)
						VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
				""", data, page_size=500)
				self.conn.commit()
				print(f"   {len(data)} rows\n")
		
		def load_icustays(self):
				print("🏨 icustays...")
				path = self._i('icustays.csv')
				if not path.exists():
						print(f"    icustays.csv not found\n")
						return
				
				df = pd.read_csv(path)
				data = [(
						self._safe(r['stay_id'], 'int'),
						self._safe(r['subject_id'], 'int'),
						self._safe(r.get('hadm_id'), 'int'),
						self._safe(r.get('first_careunit')),
						self._safe(r.get('last_careunit')),
						self._safe(r.get('intime'), 'ts'),
						self._safe(r.get('outtime'), 'ts'),
						self._safe(r.get('los'), 'float')
				) for _, r in df.iterrows()]
				
				execute_batch(self.cursor, """
						INSERT INTO icustays (stay_id, subject_id, hadm_id, first_careunit, last_careunit, intime, outtime, los)
						VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
				""", data, page_size=500)
				self.conn.commit()
				print(f"   {len(data)} rows\n")
		
		def load_chartevents(self, limit=600000):
				print("📊 chartevents...")
				path = self._i('chartevents.csv')
				if not path.exists():
						print(f"    chartevents.csv not found\n")
						return
				
				df = pd.read_csv(path)
				if len(df) > limit:
						print(f"   Limiting to {limit} rows (total: {len(df)})")
						df = df.head(limit)
				
				data = [(
						self._safe(r['subject_id'], 'int'),
						self._safe(r.get('hadm_id'), 'int'),
						self._safe(r.get('stay_id'), 'int'),
						self._safe(r.get('caregiver_id'), 'int'),
						self._safe(r.get('charttime'), 'ts'),
						self._safe(r.get('storetime'), 'ts'),
						self._safe(r['itemid'], 'int'),
						self._safe(r.get('value')),
						self._safe(r.get('valuenum'), 'float'),
						self._safe(r.get('valueuom')),
						self._safe(r.get('warning'), 'int')
				) for _, r in df.iterrows()]
				
				execute_batch(self.cursor, """
						INSERT INTO chartevents 
						(subject_id, hadm_id, stay_id, caregiver_id, charttime, storetime, itemid, value, valuenum, valueuom, warning)
						VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
				""", data, page_size=1000)
				self.conn.commit()
				print(f"   {len(data)} rows\n")
    
		def load_inputevents(self, limit=21000):
			"""Load ICU input events (IV fluids, medications)"""
			print("💉 inputevents...")
			path = self._i('inputevents.csv')
			if not path.exists():
					print(f"    inputevents.csv not found\n")
					return
			
			df = pd.read_csv(path)
			if len(df) > limit:
					print(f"   Limiting to {limit} rows (total: {len(df)})")
					df = df.head(limit)
			
			data = [(
					self._safe(r['subject_id'], 'int'),
					self._safe(r.get('hadm_id'), 'int'),
					self._safe(r.get('stay_id'), 'int'),
					self._safe(r.get('caregiver_id'), 'int'),
					self._safe(r.get('starttime'), 'ts'),
					self._safe(r.get('endtime'), 'ts'),
					self._safe(r.get('storetime'), 'ts'),
					self._safe(r.get('itemid'), 'int'),
					self._safe(r.get('amount'), 'float'),
					self._safe(r.get('amountuom')),
					self._safe(r.get('rate'), 'float'),
					self._safe(r.get('rateuom')),
					self._safe(r.get('orderid'), 'int'),
					self._safe(r.get('linkorderid'), 'int'),
					self._safe(r.get('ordercategoryname')),
					self._safe(r.get('secondaryordercategoryname')),
					self._safe(r.get('ordercomponenttypedescription')),
					self._safe(r.get('ordercategorydescription')),
					self._safe(r.get('patientweight'), 'float'),
					self._safe(r.get('totalamount'), 'float'),
					self._safe(r.get('totalamountuom')),
					self._safe(r.get('isopenbag'), 'int'),
					self._safe(r.get('continueinnextdept'), 'int'),
					self._safe(r.get('statusdescription')),
					self._safe(r.get('originalamount'), 'float'),
					self._safe(r.get('originalrate'), 'float')
			) for _, r in df.iterrows()]
			
			execute_batch(self.cursor, """
					INSERT INTO inputevents 
					(subject_id, hadm_id, stay_id, caregiver_id, starttime, endtime, storetime,
					itemid, amount, amountuom, rate, rateuom, orderid, linkorderid,
					ordercategoryname, secondaryordercategoryname, ordercomponenttypedescription,
					ordercategorydescription, patientweight, totalamount, totalamountuom,
					isopenbag, continueinnextdept, statusdescription, originalamount, originalrate)
					VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
			""", data, page_size=500)
			self.conn.commit()
			print(f"   {len(data)} rows\n")
		
		def verify(self):
				print("="*80)
				print(" VERIFICATION")
				print("="*80)
				tables = [
						'patients', 'admissions', 'transfers', 'diagnoses_icd', 'd_icd_diagnoses',
						'procedures_icd', 'd_icd_procedures', 'labevents', 'd_labitems',
						'prescriptions', 'emar', 'emar_detail', 'poe', 'microbiologyevents',
						'drgcodes', 'services', 'provider',
						'icustays', 'd_items', 'caregiver', 'chartevents', 'datetimeevents',
						'inputevents', 'ingredientevents', 'outputevents', 'procedureevents'
				]
				for t in tables:
						try:
								self.cursor.execute(f"SELECT COUNT(*) FROM {t}")
								n = self.cursor.fetchone()[0]
								print(f"{t:25} {n:>10,}")
						except:
								print(f"{t:25} {'not loaded':>10}")
				print("="*80 + "\n")
		
		def close(self):
				if self.cursor: self.cursor.close()
				if self.conn: self.conn.close()


def main():
		print("\n" + "="*80)
		print(" MIMIC-IV Complete Loader")
		print("="*80 + "\n")
		
		loader = MIMICLoader(DB_CONFIG)
		try:
				loader.download_dataset()
				loader.connect_db()
				
				# HOSP MODULE
				print("="*80)
				print(" LOADING HOSP MODULE")
				print("="*80 + "\n")
				
				loader.load_patients()
				loader.load_admissions()
				loader.load_transfers()
				loader.load_d_labitems()
				loader.load_labevents()
				loader.load_d_icd_diagnoses()
				loader.load_diagnoses_icd()
				loader.load_d_icd_procedures()
				loader.load_procedures_icd()
				loader.load_prescriptions()
				loader.load_emar()
				loader.load_poe()
				loader.load_drgcodes()
				
				# ICU MODULE
				print("="*80)
				print(" LOADING ICU MODULE")
				print("="*80 + "\n")
				
				loader.load_d_items()
				loader.load_icustays()
				loader.load_chartevents()
				loader.load_inputevents()
				
				loader.verify()
				print(" LOADING COMPLETE!\n")
				print("Next step: Run healthcare assistant CLI")
				print("  python healthcare_assistant_cli.py\n")
				
		except Exception as e:
				print(f" Error: {e}")
				import traceback
				traceback.print_exc()
		finally:
				loader.close()


if __name__ == "__main__":
		main()
