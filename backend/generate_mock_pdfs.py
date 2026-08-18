from fpdf import FPDF
import datetime

class EHR_PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, 'Synthea Health Systems - Electronic Health Record', border=False, new_x="LMARGIN", new_y="NEXT", align='C')
        self.set_font('helvetica', 'I', 10)
        self.cell(0, 10, 'Confidential Medical Record', border=False, new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def create_ehr_pdf(filename, patient_info, clinical_content):
    pdf = EHR_PDF()
    pdf.add_page()
    
    # Demographics Section
    pdf.set_font("helvetica", 'B', 12)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(0, 8, " PATIENT DEMOGRAPHICS & ENCOUNTER INFO", border=1, new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_font("helvetica", size=10)
    
    for key, value in patient_info.items():
        pdf.set_font("helvetica", 'B', 10)
        pdf.cell(40, 6, f"{key}:", border=0)
        pdf.set_font("helvetica", size=10)
        pdf.cell(0, 6, str(value), border=0, new_x="LMARGIN", new_y="NEXT")
        
    pdf.ln(5)
    
    # Clinical Sections
    for section_title, section_text in clinical_content.items():
        pdf.set_font("helvetica", 'B', 12)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, f" {section_title}", border=1, new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.ln(2)
        
        pdf.set_font("helvetica", size=10)
        pdf.multi_cell(0, 5, section_text)
        pdf.ln(5)
        
    pdf.output(filename)
    print(f"Generated realistic EHR: {filename}")

# ==============================================================================
# Scenario 1: Oxygen Therapy (DENY - missing ABG test)
# ==============================================================================
pat_1 = {
    "Patient ID": "PAT-OXYGEN-001",
    "Patient Name": "Robert Jenkins",
    "Age/Gender": "72 years old, Male",
    "Date of Service": "2023-10-15",
    "Facility": "Breathing Easy Pulmonology Clinic",
    "Attending": "Dr. Sarah Miller, MD"
}
clin_1 = {
    "Chief Complaint (CC)": "Shortness of breath and generalized fatigue.",
    "History of Present Illness (HPI)": "Mr. Jenkins is a 72-year-old male with a history of COPD who presents today complaining of worsening dyspnea on exertion over the past 3 weeks. He states that walking to his mailbox now causes him to have to stop and catch his breath. He reports increased fatigue and occasional lightheadedness. He denies any recent fevers, chills, or productive cough.",
    "Past Medical History (PMH) & Medications": "PMH: Chronic Obstructive Pulmonary Disease (COPD), Hypertension, Hyperlipidemia.\nMedications: Albuterol sulfate HFA 90mcg/actuation inhaler, Lisinopril 10mg daily, Atorvastatin 20mg daily.",
    "Review of Systems (ROS)": "Constitutional: Positive for fatigue. Negative for fever or weight loss.\nRespiratory: Positive for shortness of breath. Negative for cough.\nCardiovascular: Negative for chest pain.",
    "Physical Examination (PE)": "Vitals: BP 135/85, HR 88, Temp 98.6F, SpO2 87% on room air.\nGeneral: Alert and oriented, appears mildly dyspneic.\nLungs: Diminished breath sounds bilaterally with prolonged expiratory phase. No wheezing or crackles.",
    "Diagnostic Results": "Pulse Oximetry: Shows resting SpO2 of 87% on room air.\nNote: No Arterial Blood Gas (ABG) test was performed during this visit.",
    "Assessment & Plan (A&P)": "Assessment:\n1. Hypoxemia (ICD-10: R09.02) secondary to COPD.\n\nPlan:\nPatient's resting oxygen saturation is critically low. We will initiate home oxygen therapy to maintain SpO2 > 90%. \nRequested Service: Stationary Compressed Gas Oxygen System (HCPCS: E0424).\nPatient was instructed on safety and usage. Follow up in 4 weeks."
}

# ==============================================================================
# Scenario 2: Prosthetic Limb (PEND - missing surgical/PT eval details)
# ==============================================================================
pat_2 = {
    "Patient ID": "PAT-PROSTH-002",
    "Patient Name": "Maria Gonzalez",
    "Age/Gender": "45 years old, Female",
    "Date of Service": "2023-10-16",
    "Facility": "Mobility Solutions Hospital",
    "Attending": "Dr. James Wilson, Orthopedics"
}
clin_2 = {
    "Chief Complaint (CC)": "Evaluation for prosthetic limb.",
    "History of Present Illness (HPI)": "Patient is a 45-year-old female who recently underwent a below-knee amputation of the right leg. She presents today requesting a permanent prosthesis. She states she has been healing well and is eager to return to her active lifestyle, which previously included hiking and running.",
    "Past Medical History (PMH) & Medications": "PMH: Type 2 Diabetes Mellitus, Peripheral Artery Disease.\nMedications: Metformin 500mg BID, Gabapentin 300mg TID.",
    "Physical Examination (PE)": "Vitals: Stable.\nRight lower extremity: Residual limb is well-healed. Sutures have been removed. No signs of infection, erythema, or breakdown. Good range of motion at the knee joint.",
    "Assessment & Plan (A&P)": "Assessment:\n1. Acquired absence of right leg below knee (ICD-10: Z89.411).\n\nPlan:\nPatient's residual limb is adequately healed for a prosthesis. She is highly motivated. \nRequested Service: Below-knee Prosthesis (HCPCS: L5613).\nPatient will need to follow up with physical therapy for gait training once the device is delivered."
}

# ==============================================================================
# Scenario 3: Ultralight Wheelchair (PEND - Missing specialized PT eval)
# ==============================================================================
pat_3 = {
    "Patient ID": "PAT-WHEEL-003",
    "Patient Name": "David Chen",
    "Age/Gender": "32 years old, Male",
    "Date of Service": "2023-10-17",
    "Facility": "NeuroCare Center",
    "Attending": "Dr. Emily Roberts, Neurology"
}
clin_3 = {
    "Chief Complaint (CC)": "Mobility assessment and equipment request.",
    "History of Present Illness (HPI)": "Mr. Chen is a 32-year-old male with a history of T10 paraplegia following an MVA two years ago. He is currently using a standard manual wheelchair but reports significant shoulder pain and fatigue due to the weight of the chair. He leads an active lifestyle and requires a lighter, more maneuverable chair for daily independence.",
    "Past Medical History (PMH) & Medications": "PMH: T10 complete spinal cord injury, Paraplegia.\nMedications: Baclofen 10mg TID, Oxybutynin 5mg daily.",
    "Physical Examination (PE)": "Neurological: Complete loss of motor and sensory function below T10 dermatome. Upper extremities exhibit 5/5 strength bilaterally. \nMusculoskeletal: Mild tenderness to palpation over bilateral anterior shoulders.",
    "Assessment & Plan (A&P)": "Assessment:\n1. Paraplegia, unspecified (ICD-10: G82.20).\n\nPlan:\nPatient cannot ambulate independently and requires a wheelchair for all mobility. Due to upper extremity strain, a standard wheelchair is inadequate. \nRequested Service: Ultralightweight Wheelchair (HCPCS: K0005).\nWe will submit this request for authorization."
}

# ==============================================================================
# Scenario 4: Experimental Device (NURSE_REVIEW)
# ==============================================================================
pat_4 = {
    "Patient ID": "PAT-RARE-004",
    "Patient Name": "Linda Smith",
    "Age/Gender": "55 years old, Female",
    "Date of Service": "2023-10-18",
    "Facility": "Advanced Research Institute",
    "Attending": "Dr. Alan Turing, Neuromodulation"
}
clin_4 = {
    "Chief Complaint (CC)": "Progressive cognitive decline and movement disorder.",
    "History of Present Illness (HPI)": "Patient is a 55-year-old female suffering from a highly complex and novel neurodegenerative syndrome. Over the past 2 years, she has experienced progressive cognitive decline, involuntary movements, and severe neuropathic pain. She has failed multiple trials of pharmacologic therapy including levodopa, deep brain stimulation (standard), and high-dose corticosteroids.",
    "Past Medical History (PMH) & Medications": "PMH: Novel Neurodegenerative Syndrome X.\nMedications: Carbidopa-levodopa 25-100mg QID (ineffective), Pregabalin 150mg BID.",
    "Physical Examination (PE)": "Neurological: Significant choreiform movements of upper extremities. Cognitive slowing. Cranial nerves intact.",
    "Assessment & Plan (A&P)": "Assessment:\n1. Unspecified neurodegenerative disease (ICD-10: G31.9).\n\nPlan:\nStandard therapies have completely failed. The patient is a candidate for a newly developed experimental neural stimulator on a compassionate use basis. Due to the rarity of the condition, no standard Medicare guidelines explicitly cover or deny this exact presentation.\nRequested Service: Experimental Neural Stimulator (HCPCS: E9999).\nSubmit for prior authorization with individual medical director consideration."
}

# ==============================================================================
# Scenario 5: Simple Approval (Asthma - APPROVE)
# ==============================================================================
pat_5 = {
    "Patient ID": "PAT-ASTHMA-005",
    "Patient Name": "Michael Chang",
    "Age/Gender": "45 years old, Male",
    "Date of Service": "2023-10-19",
    "Facility": "Pulmonary Clinic",
    "Attending": "Dr. Lisa Wong, Pulmonology"
}
clin_5 = {
    "Chief Complaint (CC)": "Frequent asthma exacerbations.",
    "History of Present Illness (HPI)": "Mr. Chang is a 45-year-old male with a long-standing history of asthma. He reports that over the last 3 months, his asthma has become poorly controlled. He is waking up multiple times a week with chest tightness and wheezing. He has been using his rescue albuterol inhaler 4-5 times a day with minimal relief. He states he often struggles to generate enough inspiratory flow to properly use his dry powder inhalers during an acute attack.",
    "Past Medical History (PMH) & Medications": "PMH: Severe Persistent Asthma, Allergic Rhinitis.\nMedications: Fluticasone-salmeterol 250/50mcg BID, Albuterol HFA PRN, Cetirizine 10mg daily.",
    "Review of Systems (ROS)": "Respiratory: Positive for wheezing, chest tightness, and shortness of breath.",
    "Physical Examination (PE)": "Vitals: BP 120/80, HR 92, SpO2 95% on room air.\nLungs: Expiratory wheezing heard diffusely throughout all lung fields. Mild accessory muscle use noted.",
    "Diagnostic Results": "Diagnostic Procedure: Spirometry performed in clinic today.\nResults: FEV1 is 58% of predicted, confirming severe airflow obstruction. Significant reversibility noted post-bronchodilator.",
    "Assessment & Plan (A&P)": "Assessment:\n1. Severe persistent asthma, uncomplicated (ICD-10: J45.50).\n\nPlan:\nPatient is failing standard metered-dose and dry powder inhaler therapies due to inability to inspire deeply during exacerbations. Spirometry confirms severe persistent asthma. \nRequested Service: Standard Nebulizer with compressor (HCPCS: E0570).\nThis will allow for continuous passive delivery of albuterol during severe attacks. Prescription provided to DME supplier."
}

if __name__ == "__main__":
    create_ehr_pdf("scenario1_oxygen.pdf", pat_1, clin_1)
    create_ehr_pdf("scenario2_prosthesis.pdf", pat_2, clin_2)
    create_ehr_pdf("scenario3_wheelchair.pdf", pat_3, clin_3)
    create_ehr_pdf("scenario4_experimental.pdf", pat_4, clin_4)
    create_ehr_pdf("scenario5_asthma.pdf", pat_5, clin_5)
