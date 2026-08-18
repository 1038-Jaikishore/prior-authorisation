import requests
import json
import time
import os

BASE_URL = "http://localhost:8000/api/prior-auth"

def run_test(pdf_path: str):
    print(f"\n{'='*60}\nTesting: {os.path.basename(pdf_path)}\n{'='*60}")
    
    # 1. Upload & Extract
    print("1. Uploading and extracting...")
    with open(pdf_path, 'rb') as f:
        files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
        res = requests.post(f"{BASE_URL}/upload", files=files)
        
    if not res.ok:
        print(f"FAILED UPLOAD: {res.status_code}")
        print(res.text)
        return
        
    upload_data = res.json()
    packet = upload_data.get("clinical_evidence_packet")
    print(f"Extracted Packet HCPCS: {packet['requested_service']['code']}")
    
    # 2. Create Request in DB
    print("2. Saving request to MongoDB...")
    res = requests.post(f"{BASE_URL}", json=packet)
    if not res.ok:
        print(f"FAILED DB SAVE: {res.status_code}")
        print(res.text)
        return
        
    auth_id = res.json().get("request_id")
    print(f"Created Auth ID: {auth_id}")
    
    # 3. Evaluate Full Pipeline
    print("3. Running full 8-Phase evaluation...")
    res = requests.post(f"{BASE_URL}/{auth_id}/evaluate-full-pipeline")
    if not res.ok:
        print(f"FAILED EVALUATION: {res.status_code}")
        print(res.text)
        return
        
    eval_data = res.json()
    
    # Print results
    print(f"\n--- PIPELINE RESULTS ---")
    print(f"Final Status: {eval_data.get('final_status')}")
    
    phase7 = eval_data.get("phase7_decision", {})
    print(f"Confidence: {phase7.get('overall_confidence_score')}")
    
    print("\n--- PHASE 8 EXPLANATION LETTER ---\n")
    print(eval_data.get("final_explanation", "No explanation returned"))
    print("\n")

if __name__ == "__main__":
    run_test(r"e:\synthea_sample_data_ccda_latest\cms-prior-auth\backend\EHR_Approve_Oxygen.pdf")
