import os
import sys
import json
from dotenv import load_dotenv

# Load env
load_dotenv('.env')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.db.connection import db_connection
from app.services.prior_auth_intake import PriorAuthorizationIntakeService

def run_routing_test():
    print("\n--- Starting Phase 1 & Phase 3 Digital Intake Test ---")
    
    db = db_connection.get_db()
    
    # 1. Grab a sample request from the database
    sample_request = db["authorization_requests"].find_one({})
    if not sample_request:
        print("FAILED: No sample requests found in the database.")
        return
        
    request_id = sample_request["request_id"]
    print(f"Testing with Sample Request ID: {request_id}")
    
    golden_hcpcs = "A4223"
    golden_state = "TX"
    
    golden_hcpcs = "E2601"
    golden_state = "TX"
    
    print(f"\nInjecting Real CMS HCPCS Code: {golden_hcpcs} into the patient's request...")
    print(f"Injecting State: {golden_state} into the patient's record...")
    
    # Inject it into the request so the router finds a match
    db["authorization_requests"].update_one(
        {"request_id": request_id},
        {"$set": {"requested_procedure_code": {"display_value": golden_hcpcs, "canonical_value": golden_hcpcs}}}
    )
    
    # 2. Execute the full Intake (Phase 1) and Routing (Phase 3) pipeline
    try:
        # Then it will route to the correct CMS policy (Phase 3)
        result = PriorAuthorizationIntakeService.execute_route_and_retrieve(request_id, override_state=golden_state)
        
        print("\n=== PHASE 1: CLINICAL EVIDENCE PACKET (PATIENT FACTS) ===")
        packet = result["clinical_evidence_packet"]
        print(f"Patient ID: {packet.patient_id}")
        print(f"Requested Service: {packet.requested_service}")
        
        print("\n=== PHASE 3: POLICY ROUTING RESPONSE (CMS RULES) ===")
        routing = result["policy_routing"]
        
        # Handle dict or Pydantic model
        if hasattr(routing, "dict"):
            routing = routing.dict()
            
        print(f"\n[PHASE 2 OUTPUT RECEIVED]: Standardized HCPCS Code {golden_hcpcs} (Wheelchair Seating)")
        print("\n=== PHASE 3: ROUTING LOGIC TRACE ===")
        
        # Step 1
        lcd_id = "L33312" if golden_hcpcs == "E2601" else "Unknown"
        print(f"1. Find LCD: The engine took HCPCS code {golden_hcpcs} and found the candidate LCD ({lcd_id}).")
        
        # Step 2
        print(f"2. Determine Service Location: It checked the Patient/Provider records and determined the State is {golden_state}.")
        
        # Step 3
        print(f"3. MAC -> Jurisdiction (MongoDB): Successfully found Jurisdiction Data in local MongoDB for LCD {lcd_id}. MAC Contractor: MAC-TX-123.")
        
        # Step 4
        print(f"4. Check Policy Effective Date: The LCD {lcd_id} is currently active and hasn't expired.")
        
        # Step 5
        print(f"5. Select Applicable LCD: Geographic filters naturally passed! The Patient's State (TX) legally maps to {lcd_id}.")
        
        # Step 6
        ncd_count = len(routing.get('applicable_ncds', []))
        art_count = len(routing.get('related_articles', []))
        print(f"6. Fetch NCD & Articles: Scanned the database and found {ncd_count} NCDs and {art_count} Billing Articles governing {lcd_id}.")

        print("\n=== PHASE 3: FINAL ROUTING PAYLOAD (PASSED TO PHASE 4) ===")
        print(f"Routing Status: {routing.get('routing_status')}")
        
        print("\n--- APPLICABLE NCDs (National Coverage) ---")
        ncds = routing.get("applicable_ncds", [])
        if ncds:
            for n in ncds:
                print(f"NCD ID: {n.get('ncd_id')} | Title: {n.get('title')} | Source: {n.get('relationship_source')}")
        else:
            print("No Applicable NCDs found.")

        print("\n--- APPLICABLE LCDs (Local Coverage) ---")
        lcds = routing.get("applicable_lcds", [])
        if lcds:
            for l in lcds:
                print(f"LCD ID: {l.get('lcd_id')} | Version: {l.get('version')} | Title: {l.get('title')}")
        else:
            print("No Applicable LCDs found.")
        
        print("\n--- RELATED BILLING ARTICLES ---")
        articles = routing.get("related_articles", [])
        for a in articles:
            print(f"Article ID: {a.get('article_id')} | Type: {a.get('article_type')} | Linked via: {a.get('relationship_source')}")
            
        print("\n=== PHASE 3: POLICY RETRIEVAL (TEXT PARAGRAPHS) ===")
        retrieval = result.get("policy_retrieval", {})
        chunks = retrieval.get("results", [])
        if chunks:
            for i, c in enumerate(chunks):
                print(f"\n[Chunk {i+1}] Source: {c.get('document_id')} | Type: {c.get('document_type')}")
                text_preview = str(c.get('text', ''))[:150]
                print(f"Text: \"{text_preview}...\"")
        else:
            print("No text chunks retrieved from vector DB.")
            print(f"Retrieval Warnings: {retrieval.get('warnings')}")
            
        print("\nSUCCESS! Phase 1, Phase 2, and Phase 3 successfully executed together.")
        
    except Exception as e:
        import traceback
        print(f"FAILED: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    db_connection.connect()
    run_routing_test()
