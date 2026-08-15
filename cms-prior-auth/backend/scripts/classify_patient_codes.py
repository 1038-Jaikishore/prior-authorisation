import os
import sys
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.connection import db_connection

def classify_codes():
    db = db_connection.get_db()
    requests = list(db["authorization_requests"].find())
    
    total_requests = len(requests)
    cms_compatible_services = 0
    custom_services = 0
    unknown_services = 0
    
    valid_icd10_diagnoses = 0
    custom_diagnoses = 0
    unknown_diagnoses = 0
    
    routable_requests_count = 0
    routable_requests_list = []
    
    classification_details = []
    
    # Pre-load known HCPCS codes from consolidate consolidated CMS tables for quick check
    print("Checking code lists from CMS collections...")
    cms_hcpcs_set = set()
    for col_name in ["ncd_hcpcs", "lcd_hcpcs", "article_hcpcs"]:
        docs = db[col_name].find()
        for doc in docs:
            # Check hcpcs_code dictionary
            h_code = doc.get("hcpcs_code")
            if isinstance(h_code, dict) and "canonical_value" in h_code:
                cms_hcpcs_set.add(h_code["canonical_value"])
            elif isinstance(h_code, str):
                cms_hcpcs_set.add(h_code)
                
    print(f"Loaded {len(cms_hcpcs_set)} standard CPT/HCPCS codes from CMS databases.")
    
    for req in requests:
        req_id = req["request_id"]
        
        # 1. Classify service code
        service_node = req.get("requested_procedure_code", {})
        if isinstance(service_node, dict):
            svc_code = service_node.get("canonical_value", "")
        else:
            svc_code = str(service_node)
            
        svc_class = "UNKNOWN"
        # Standard HCPCS/CPT are 5-character alphanumeric (e.g. 27447, G0277)
        if re.match(r'^[A-Z0-9]{5}$', svc_code):
            svc_class = "STANDARD_HCPCS_OR_CPT"
            cms_compatible_services += 1
        elif svc_code.startswith("PROC"):
            svc_class = "CUSTOM_SYNTHETIC_CODE"
            custom_services += 1
        else:
            unknown_services += 1
            
        # 2. Classify diagnosis code
        diag_node = req.get("diagnosis_code", [])
        if isinstance(diag_node, list):
            diags = [d.get("canonical_value", "") if isinstance(d, dict) else str(d) for d in diag_node]
        elif isinstance(diag_node, dict):
            diags = [diag_node.get("canonical_value", "")]
        else:
            diags = [str(diag_node)]
            
        diag_classes = []
        for d in diags:
            d_class = "UNKNOWN"
            # Standard ICD-10 starts with letter + 2 digits, plus optional sub-digits (alphanumeric, no dots in canonical)
            if re.match(r'^[A-Z]\d{2,6}$', d):
                d_class = "STANDARD_ICD10"
                valid_icd10_diagnoses += 1
            elif d.startswith("DIAG"):
                d_class = "CUSTOM_SYNTHETIC_CODE"
                custom_diagnoses += 1
            else:
                unknown_diagnoses += 1
            diag_classes.append(d_class)
            
        # Determine if fully CMS compatible (routable) without mocks
        # Routable if service code is standard AND actually exists in CMS database, and diagnosis is standard ICD-10
        is_svc_in_cms = svc_code in cms_hcpcs_set
        is_diag_standard = any(c == "STANDARD_ICD10" for c in diag_classes)
        
        is_routable = is_svc_in_cms and is_diag_standard
        
        if is_routable:
            routable_requests_count += 1
            routable_requests_list.append(req_id)
            
        classification_details.append({
            "request_id": req_id,
            "service_code": svc_code,
            "service_class": svc_class,
            "in_cms_dataset": is_svc_in_cms,
            "diagnoses": diags,
            "diagnosis_classes": diag_classes,
            "is_routable": is_routable
        })
        
    # Generate report markdown
    report_lines = [
        "# Patient Code Compatibility & Routing Report",
        "",
        "This report classifies requested procedural service codes and clinical diagnosis codes across all synthetic prior authorization requests.",
        "",
        "## Summary Metrics",
        "",
        f"- **Total Authorization Requests**: `{total_requests}`",
        f"- **Requests with Standard CPT/HCPCS Service Codes**: `{cms_compatible_services}`",
        f"- **Requests with Custom Synthetic Service Codes (`PROCXXXX`)**: `{custom_services}`",
        f"- **Requests with Valid Standard ICD-10 Diagnosis Codes**: `{valid_icd10_diagnoses}`",
        f"- **Requests with Custom Synthetic Diagnosis Codes (`DIAGXX`)**: `{custom_diagnoses}`",
        f"- **Requests Routable to CMS reference policies without mocks**: `{routable_requests_count}`",
        f"- **Genuine CMS-Compatible Demo Case IDs**: `{', '.join(routable_requests_list) if routable_requests_list else 'NO_FULLY_CMS_COMPATIBLE_SYNTHETIC_CASES'}`",
        "",
        "---",
        "",
        "## Detailed Classification List",
        "",
        "| Request ID | Service Code | Service Class | Found in CMS Database | Diagnoses | Diagnosis Class | Fully Routable |",
        "| --- | --- | --- | --- | --- | --- | --- |"
    ]
    
    for c in classification_details:
        diags_str = ", ".join(c["diagnoses"])
        diag_cls_str = ", ".join(c["diagnosis_classes"])
        report_lines.append(
            f"| `{c['request_id']}` | `{c['service_code']}` | `{c['service_class']}` | `{'Yes' if c['in_cms_dataset'] else 'No'}` | `{diags_str}` | `{diag_cls_str}` | `{'Yes' if c['is_routable'] else 'No'}` |"
        )
        
    os.makedirs("reports", exist_ok=True)
    with open("reports/patient_code_compatibility_report.md", "w") as f:
        f.write("\n".join(report_lines))
        
    print(f"Report generated successfully in reports/patient_code_compatibility_report.md")
    print(f"Routable requests list: {routable_requests_list}")

if __name__ == "__main__":
    classify_codes()
