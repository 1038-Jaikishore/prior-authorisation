import os
import json
import pandas as pd
from typing import Dict, Any, List

def audit_datasets():
    data_dir = "data/patient_data"
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    csv_files = sorted([f for f in os.listdir(data_dir) if f.endswith(".csv")])
    
    audit_results = {}
    data_dictionary = {}
    quality_report = {}
    relationship_results = {}
    
    # Pre-classify label leakage fields
    leakage_mapping = {
        "ai_reasoning": "AI_GENERATED_LABEL",
        "medical_necessity": "SOURCE_TEXT", # Contains narrative justifications
        "evidence_for_medical_necessity": "SOURCE_TEXT",
        "threshold_met": "PRECOMPUTED_LABEL",
        "step_therapy_requirement_met": "PRECOMPUTED_LABEL",
        "necessity_evaluation_support": "PRECOMPUTED_LABEL",
        "duplicate_request_flag": "PRECOMPUTED_LABEL",
        "duplicate_service_flag": "PRECOMPUTED_LABEL",
        "status": "OUTCOME_LABEL",
        "claim_status": "OUTCOME_LABEL",
        "authorization_status": "OUTCOME_LABEL"
    }

    # Loaded DataFrames for relationship validation
    dfs = {}

    print("Auditing patient datasets...")
    for filename in csv_files:
        filepath = os.path.join(data_dir, filename)
        
        # Read the file
        try:
            df = pd.read_csv(filepath)
        except Exception as e:
            print(f"Error reading {filename}: {str(e)}")
            continue
            
        dfs[filename] = df
        
        row_count = len(df)
        col_count = len(df.columns)
        columns = list(df.columns)
        
        # Datatypes
        types = {col: str(df[col].dtype) for col in columns}
        
        # Null counts
        null_counts = {col: int(df[col].isnull().sum()) for col in columns}
        
        # Duplicate rows count
        duplicate_count = int(df.duplicated().sum())
        
        # Candidate keys
        candidate_keys = []
        for col in columns:
            if df[col].nunique() == row_count and df[col].isnull().sum() == 0:
                candidate_keys.append(col)
                
        # Date fields (heuristics)
        date_fields = [col for col in columns if "date" in col.lower() or "dob" in col.lower()]
        
        # Code fields (heuristics)
        code_fields = [col for col in columns if "code" in col.lower()]
        
        # Coverages
        has_patient_id = "patient_id" in columns
        has_provider_id = "provider_id" in columns
        # Check standard request/auth ID fields
        has_auth_id = any(c in columns for c in ["request_id", "authorization_id", "claim_id"])
        
        audit_results[filename] = {
            "row_count": row_count,
            "column_count": col_count,
            "columns": columns,
            "types": types,
            "null_counts": null_counts,
            "duplicate_count": duplicate_count,
            "candidate_keys": candidate_keys,
            "date_fields": date_fields,
            "code_fields": code_fields,
            "patient_id_coverage": has_patient_id,
            "provider_id_coverage": has_provider_id,
            "authorization_id_coverage": has_auth_id,
            "malformed_rows": 0 # Pandas parsing succeeded cleanly
        }
        
        # Add to data dictionary
        data_dictionary[filename] = {
            "row_count": row_count,
            "columns": {col: {"type": str(df[col].dtype), "null_count": int(df[col].isnull().sum())} for col in columns}
        }
        
        # Add to quality report
        quality_report[filename] = {
            "duplicate_count": duplicate_count,
            "null_counts": null_counts,
            "completeness_score": 1.0 - (sum(null_counts.values()) / (row_count * col_count) if row_count * col_count > 0 else 0)
        }

    # -------------------------------------------------------------
    # 2. Relationship Validation (Joins Check)
    # -------------------------------------------------------------
    patients_df = dfs.get("patients.csv")
    providers_df = dfs.get("providers.csv")
    auth_requests_df = dfs.get("authorization_requests.csv")
    
    if patients_df is not None:
        valid_patients = set(patients_df["patient_id"].astype(str))
    else:
        valid_patients = set()
        
    if providers_df is not None:
        valid_providers = set(providers_df["provider_id"].astype(str))
    else:
        valid_providers = set()

    for filename, df in dfs.items():
        if filename == "patients.csv":
            continue
            
        columns = df.columns
        rel_info = {}
        
        # Verify patient_id coverage and joins
        if "patient_id" in columns:
            child_keys = df["patient_id"].astype(str).tolist()
            matched_count = sum(1 for k in child_keys if k in valid_patients)
            total = len(child_keys)
            match_rate = matched_count / total if total > 0 else 1.0
            broken_refs = list(set(k for k in child_keys if k not in valid_patients))
            
            rel_info["patient_id_join"] = {
                "parent_table": "patients.csv",
                "matched_count": matched_count,
                "total_count": total,
                "match_rate": match_rate,
                "broken_references_count": len(broken_refs),
                "broken_references": broken_refs[:10] # cap list display
            }
            
        # Verify provider_id coverage and joins
        if "provider_id" in columns:
            child_keys = df["provider_id"].astype(str).tolist()
            matched_count = sum(1 for k in child_keys if k in valid_providers)
            total = len(child_keys)
            match_rate = matched_count / total if total > 0 else 1.0
            broken_refs = list(set(k for k in child_keys if k not in valid_providers))
            
            rel_info["provider_id_join"] = {
                "parent_table": "providers.csv",
                "matched_count": matched_count,
                "total_count": total,
                "match_rate": match_rate,
                "broken_references_count": len(broken_refs),
                "broken_references": broken_refs[:10]
            }
            
        if rel_info:
            relationship_results[filename] = rel_info

    # -------------------------------------------------------------
    # 3. Output JSON Reports
    # -------------------------------------------------------------
    with open("reports/patient_data_dictionary.json", "w") as f:
        json.dump(data_dictionary, f, indent=2)
        
    with open("reports/patient_data_quality_report.json", "w") as f:
        json.dump(quality_report, f, indent=2)

    # -------------------------------------------------------------
    # 4. Generate patient_dataset_audit.md
    # -------------------------------------------------------------
    md_lines = [
        "# Patient Dataset Audit Report",
        "",
        "This report summarizes the static structure of the 21 patient CSV files.",
        "",
        "## Summary Metrics Table",
        "",
        "| Filename | Row Count | Col Count | Duplicates | Candidate Key(s) | Has Patient ID | Has Provider ID |",
        "| --- | --- | --- | --- | --- | --- | --- |"
    ]
    
    for fname, res in audit_results.items():
        cand_keys = ", ".join(res["candidate_keys"]) if res["candidate_keys"] else "None"
        md_lines.append(
            f"| `{fname}` | {res['row_count']} | {res['column_count']} | {res['duplicate_count']} | `{cand_keys}` | {'Yes' if res['patient_id_coverage'] else 'No'} | {'Yes' if res['provider_id_coverage'] else 'No'} |"
        )
        
    md_lines.append("\n## Detailed Columns & Types\n")
    for fname, res in audit_results.items():
        md_lines.append(f"### {fname}")
        md_lines.append("")
        md_lines.append("| Column Name | Type | Null Count |")
        md_lines.append("| --- | --- | --- |")
        for col in res["columns"]:
            md_lines.append(f"| `{col}` | `{res['types'][col]}` | {res['null_counts'][col]} |")
        md_lines.append("")
        
    with open("reports/patient_dataset_audit.md", "w") as f:
        f.write("\n".join(md_lines))

    # -------------------------------------------------------------
    # 5. Generate patient_relationship_report.md
    # -------------------------------------------------------------
    rel_lines = [
        "# Patient Relationship Join Report",
        "",
        "This report details the integrity of joins linking child tables back to parent tables (`patients` and `providers`).",
        "",
        "| Filename | Join Key | Target Table | Match Count | Total Rows | Match Rate | Broken Refs Count |",
        "| --- | --- | --- | --- | --- | --- | --- |"
    ]
    
    for fname, joins in relationship_results.items():
        for key, info in joins.items():
            key_name = "patient_id" if "patient" in key else "provider_id"
            rel_lines.append(
                f"| `{fname}` | `{key_name}` | `{info['parent_table']}` | {info['matched_count']} | {info['total_count']} | {info['match_rate'] * 100:.1f}% | {info['broken_references_count']} |"
            )
            
    rel_lines.append("\n## Broken References Detail (Sample display)\n")
    for fname, joins in relationship_results.items():
        for key, info in joins.items():
            if info["broken_references_count"] > 0:
                rel_lines.append(f"### {fname} -> {info['parent_table']} (unmatched keys)")
                rel_lines.append(f"- **Count**: {info['broken_references_count']}")
                rel_lines.append(f"- **Samples**: {info['broken_references']}")
                rel_lines.append("")
                
    with open("reports/patient_relationship_report.md", "w") as f:
        f.write("\n".join(rel_lines))

    # -------------------------------------------------------------
    # 6. Generate patient_field_role_map.md
    # -------------------------------------------------------------
    role_lines = [
        "# Patient Field Role Classification Map",
        "",
        "This map classifies all columns across the 21 patient datasets to detect and isolate precomputed labels, AI-generated reasonings, or outcome leakage fields.",
        "",
        "| Filename | Column | Classification | Reason / Role |",
        "| --- | --- | --- | --- |"
    ]
    
    for fname, df in dfs.items():
        for col in df.columns:
            # Determine classification
            if col in leakage_mapping:
                role = leakage_mapping[col]
                desc = "Precomputed conclusion or outcome status; must NOT be used as policy logic ground truth."
            elif "id" in col.lower():
                role = "ADMINISTRATIVE_FACT"
                desc = "Primary/Foreign database tracking identifier."
            elif "date" in col.lower() or "dob" in col.lower():
                role = "ADMINISTRATIVE_FACT"
                desc = "Chronological timestamp record."
            elif "code" in col.lower():
                role = "RAW_CLINICAL_FACT"
                desc = "Raw structured clinical code (e.g. HCPCS, CPT, ICD-10)."
            elif col in ["clinical_indication", "medical_necessity", "provider_justification", "previous_treatment_info", "summary_card_text"]:
                role = "SOURCE_TEXT"
                desc = "Clinical narrative text block containing patient facts."
            elif col in ["first_name", "last_name", "dob", "age", "gender", "insurance_plan", "member_id"]:
                role = "ADMINISTRATIVE_FACT"
                desc = "Administrative or demographic patient metadata."
            else:
                role = "RAW_CLINICAL_FACT"
                desc = "Structured raw clinical measure or metric value."
                
            role_lines.append(f"| `{fname}` | `{col}` | **{role}** | {desc} |")
            
    with open("reports/patient_field_role_map.md", "w") as f:
        f.write("\n".join(role_lines))
        
    print("Auditing completed successfully. Output files saved in reports/.")

if __name__ == "__main__":
    audit_datasets()
