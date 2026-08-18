import os
import re
import csv
import sys
import json
import pandas as pd
from PyPDF2 import PdfReader

# Increase CSV field limit for large text fields
csv.field_size_limit(100000000)

cms_data_dir = "/Users/jaikishorep/Desktop/prior authorization/cms-prior-auth/backend/data/cms_data"
reports_dir = "/Users/jaikishorep/Desktop/prior authorization/cms-prior-auth/backend/reports"

# Ensure reports directory exists
os.makedirs(reports_dir, exist_ok=True)

# Inferred header layouts for headerless files
HEADERLESS_MAPPINGS = {
    "icd10_pcs_codes.csv": [
        "article_id", "article_version", "description", "icd10_pcs_group", 
        "icd10_pcs_code", "range", "last_updated", "asterisk", "icd10_pcs_code_id"
    ],
    "revenue_codes.csv": [
        "article_id", "article_version", "description", "last_updated", 
        "range", "revenue_code", "revenue_code_id"
    ]
}

def detect_file_info(filename, filepath):
    """Detects physical format, sheet names (if Excel), and encoding."""
    if filename.endswith(".pdf"):
        return {"format": "PDF", "encoding": "binary"}
    elif filename.endswith(".xlsx") or filename.endswith(".xls") and not filename.endswith(".csv.xls"):
        # Real Excel file
        return {"format": "Excel", "encoding": "binary"}
    
    # Text-based file (including .csv and .csv.xls)
    # Check encoding (utf-8 vs latin1)
    encoding = "utf-8"
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                f.read(10000)
        except UnicodeDecodeError:
            encoding = "latin-1"
        
    return {"format": "CSV", "encoding": encoding}

def check_html_presence(df):
    """Checks if HTML tags are present in any cells."""
    html_pattern = re.compile(r"<[^>]+>|&lt;[^&]+&gt;")
    for col in df.select_dtypes(include=[object]):
        # Sample non-null values to speed up check
        sample_vals = df[col].dropna().astype(str).head(1000)
        if any(html_pattern.search(val) for val in sample_vals):
            return True
    return False

def check_date_fields(df):
    """Detects potential date fields and their formats."""
    date_fields = {}
    date_patterns = [
        (re.compile(r"^\d{2}/\d{2}/\d{4}$"), "MM/DD/YYYY"),
        (re.compile(r"^\d{4}-\d{2}-\d{2}$"), "YYYY-MM-DD"),
        (re.compile(r"^\d{2}/\d{2}/\d{2}$"), "MM/DD/YY"),
        (re.compile(r"^\d{2}-\w{3}-\d{4}$"), "DD-MMM-YYYY"),
    ]
    for col in df.columns:
        # Sample non-null values
        vals = df[col].dropna().astype(str).head(100)
        if len(vals) == 0:
            continue
        
        # Test values against regexes
        matched_format = None
        match_count = 0
        for pat, fmt in date_patterns:
            matches = sum(1 for v in vals if pat.match(v))
            if matches > len(vals) * 0.5: # If majority values match
                matched_format = fmt
                break
                
        if matched_format:
            date_fields[col] = matched_format
    return date_fields

def find_candidate_keys(df, col_names):
    """Determines candidate single or composite keys that uniquely identify each row."""
    if len(df) == 0:
        return []
        
    candidates = []
    # Check single column uniqueness
    for col in col_names:
        if df[col].nunique() == len(df):
            candidates.append([col])
            
    if candidates:
        return [c[0] for c in candidates]
        
    # Check common composite keys
    composites = [
        ["article_id", "article_version"],
        ["lcd_id", "lcd_version"],
        ["document_id", "document_version"],
        ["article_id", "article_version", "hcpc_code_id", "hcpc_code_version"],
        ["article_id", "article_version", "icd10_code_id", "icd10_code_version"],
        ["lcd_id", "lcd_version", "contractor_id"],
        ["lcd_id", "lcd_version", "state_id"],
        ["article_id", "article_version", "state_id"],
    ]
    
    for comp in composites:
        # Check if all columns in composite exist in df
        if all(c in col_names for c in comp):
            if not df.duplicated(subset=comp).any():
                candidates.append(comp)
                
    return [" + ".join(c) for c in candidates]

def run_audit():
    files = [f for f in os.listdir(cms_data_dir) if f != ".gitkeep"]
    print(f"Auditing {len(files)} files...")
    
    audit_results = {}
    
    for filename in sorted(files):
        filepath = os.path.join(cms_data_dir, filename)
        file_info = detect_file_info(filename, filepath)
        
        row_count = 0
        col_count = 0
        col_names = []
        null_counts = {}
        inferred_types = {}
        dup_count = 0
        candidate_keys = []
        sample_values = {}
        malformed_rows = 0
        date_fields = {}
        html_present = False
        has_accidental_headers = False
        
        if file_info["format"] == "PDF":
            # For PDF Tabular Ref
            try:
                reader = PdfReader(filepath)
                row_count = len(reader.pages) # Represent pages as row count
                col_names = ["Page Content"]
                col_count = 1
                inferred_types = {"Page Content": "string"}
                null_counts = {"Page Content": 0}
                candidate_keys = ["Page Number"]
                sample_values = {"Page Content": "PDF Tabular Reference Document"}
            except Exception as e:
                print(f"Error parsing PDF {filename}: {e}")
                malformed_rows = 1
        elif file_info["format"] == "Excel":
            try:
                xl = pd.ExcelFile(filepath)
                df = xl.parse(xl.sheet_names[0])
                row_count, col_count = df.shape
                col_names = list(df.columns)
                null_counts = df.isnull().sum().to_dict()
                inferred_types = {col: str(df[col].dtype) for col in df.columns}
                dup_count = int(df.duplicated().sum())
                candidate_keys = find_candidate_keys(df, col_names)
                date_fields = check_date_fields(df)
                html_present = check_html_presence(df)
                # Sample values
                for col in col_names[:5]:
                    sample_vals = df[col].dropna().head(3).tolist()
                    sample_values[col] = [str(x) for x in sample_vals]
            except Exception as e:
                print(f"Error parsing Excel {filename}: {e}")
                malformed_rows = 1
        else:
            # CSV file
            encoding = file_info["encoding"]
            header_mapping = HEADERLESS_MAPPINGS.get(filename)
            
            try:
                # Check for header alignment & read csv
                with open(filepath, "r", encoding=encoding, errors="replace") as f:
                    reader = csv.reader(f)
                    first_row = next(reader, None)
                    
                # Accidental header detection in CSV: 
                # Check if code-like keywords or comments leaked into headers
                if first_row and any("import " in x or "class " in x or "def " in x for x in first_row):
                    has_accidental_headers = True
                
                # Read using pandas
                if header_mapping:
                    df = pd.read_csv(filepath, encoding=encoding, header=None, names=header_mapping, on_bad_lines='skip')
                else:
                    df = pd.read_csv(filepath, encoding=encoding, on_bad_lines='skip')
                
                row_count, col_count = df.shape
                col_names = list(df.columns)
                null_counts = df.isnull().sum().to_dict()
                inferred_types = {col: str(df[col].dtype) for col in df.columns}
                dup_count = int(df.duplicated().sum())
                candidate_keys = find_candidate_keys(df, col_names)
                date_fields = check_date_fields(df)
                html_present = check_html_presence(df)
                
                # Check malformed rows by comparing with actual line count
                with open(filepath, "r", encoding=encoding, errors="replace") as f:
                    actual_lines = sum(1 for _ in f)
                # Note: line count includes headers, pandas row_count does not. But multiline strings can make lines > row_count.
                # So we check if we had skipped bad lines (we'd have logs if parsed manually)
                # Let's check malformed rows using manual parsing to count mismatched column widths
                with open(filepath, "r", encoding=encoding, errors="replace") as f:
                    reader = csv.reader(f)
                    header_len = len(first_row) if first_row else 0
                    mismatched = 0
                    for idx, row in enumerate(reader):
                        if idx == 0 and not header_mapping:
                            continue
                        if len(row) != header_len:
                            mismatched += 1
                    malformed_rows = mismatched
                
                # Sample values
                for col in col_names[:5]:
                    sample_vals = df[col].dropna().head(3).tolist()
                    sample_values[col] = [str(x) for x in sample_vals]
                    
            except Exception as e:
                print(f"Error parsing CSV {filename}: {e}")
                malformed_rows = 1
                
        audit_results[filename] = {
            "physical_format": file_info["format"],
            "encoding": file_info["encoding"],
            "row_count": row_count,
            "col_count": col_count,
            "column_names": col_names,
            "inferred_types": inferred_types,
            "null_counts": {k: int(v) for k, v in null_counts.items()},
            "duplicate_count": dup_count,
            "candidate_keys": candidate_keys,
            "sample_values": sample_values,
            "malformed_rows": malformed_rows,
            "date_fields": date_fields,
            "html_present": html_present,
            "has_accidental_headers": has_accidental_headers
        }
        
    # Write backend/reports/dataset_audit.md
    write_dataset_audit_md(audit_results)
    
    # Write backend/reports/data_dictionary.json
    write_data_dictionary_json(audit_results)
    
    # Write backend/reports/data_quality_report.json
    write_data_quality_json(audit_results)
    
    # Write backend/reports/relationship_report.md
    write_relationship_report_md(audit_results)
    
    print("Audit completed successfully. All reports generated.")

def write_dataset_audit_md(results):
    md_content = ["# CMS Dataset Physical Audit Report\n"]
    md_content.append("## Overview\nThis report presents physical characteristics of the 27 CMS reference files.\n")
    md_content.append("| Filename | Format | Encoding | Rows | Columns | Duplicates | Malformed Rows | HTML | Accidental Headers |")
    md_content.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    
    for filename, r in results.items():
        md_content.append(
            f"| {filename} | {r['physical_format']} | {r['encoding']} | {r['row_count']} | {r['col_count']} | "
            f"{r['duplicate_count']} | {r['malformed_rows']} | {'Yes' if r['html_present'] else 'No'} | "
            f"{'Yes' if r['has_accidental_headers'] else 'No'} |"
        )
    
    md_content.append("\n## Detailed Dataset Schemas\n")
    for filename, r in results.items():
        md_content.append(f"### {filename}")
        md_content.append(f"- **Physical Format**: {r['physical_format']}")
        md_content.append(f"- **Encoding**: {r['encoding']}")
        md_content.append(f"- **Row/Column Counts**: {r['row_count']} rows, {r['col_count']} columns")
        md_content.append(f"- **Candidate Keys**: `{r['candidate_keys']}`")
        
        md_content.append("\n#### Columns and Inferred Types:")
        md_content.append("| Column Name | Inferred Type | Null Count |")
        md_content.append("| --- | --- | --- |")
        for col in r["column_names"]:
            t = r["inferred_types"].get(col, "unknown")
            nc = r["null_counts"].get(col, 0)
            md_content.append(f"| {col} | {t} | {nc} |")
            
        md_content.append("\n#### Sample Values:")
        for col, samples in r["sample_values"].items():
            md_content.append(f"- **{col}**: `{samples}`")
        md_content.append("\n---\n")
        
    with open(os.path.join(reports_dir, "dataset_audit.md"), "w") as f:
        f.write("\n".join(md_content))

def write_data_dictionary_json(results):
    dict_out = {}
    for filename, r in results.items():
        dict_out[filename] = {
            "physical_format": r["physical_format"],
            "encoding": r["encoding"],
            "row_count": r["row_count"],
            "col_count": r["col_count"],
            "candidate_keys": r["candidate_keys"],
            "columns": [
                {
                    "name": col,
                    "type": r["inferred_types"].get(col, "unknown"),
                    "null_count": r["null_counts"].get(col, 0),
                    "date_format": r["date_fields"].get(col)
                } for col in r["column_names"]
            ]
        }
        
    with open(os.path.join(reports_dir, "data_dictionary.json"), "w") as f:
        json.dump(dict_out, f, indent=2)

def write_data_quality_json(results):
    dq_out = {}
    for filename, r in results.items():
        dq_out[filename] = {
            "duplicate_rows": r["duplicate_count"],
            "malformed_rows": r["malformed_rows"],
            "html_markup_present": r["html_present"],
            "accidental_headers": r["has_accidental_headers"],
            "null_counts": r["null_counts"]
        }
        
    with open(os.path.join(reports_dir, "data_quality_report.json"), "w") as f:
        json.dump(dq_out, f, indent=2)

def write_relationship_report_md(results):
    md_content = ["# CMS Dataset Relationship & Join Keys Report\n"]
    md_content.append("## Conceptual Mapping & Join Keys\n")
    md_content.append("This report lists relationship links, join keys, and unresolved links identified among NCDs, LCDs, Articles, HCPCS, ICD, contractors, jurisdictions, modifiers, bill codes, and revenue codes.\n")
    
    md_content.append("### Major Entities and Identifiers")
    md_content.append("- **NCD ID**: Found in `ncd_documents_data.csv` (`document_display_id`, `document_id`)")
    md_content.append("- **LCD ID**: Found in `lcd_documents.csv` (`document_id`), `lcd_full_data.csv` (`lcd_id`)")
    md_content.append("- **Article ID**: Found in `articles_700.csv` (`article_id`)")
    md_content.append("- **HCPCS Code**: Found in `CMS_HCPC_code.csv` (`hcpc_code_id`) and `CMS_LCD_HCPCS_All_LCDs (1).csv` (`hcpc_code_id`)")
    md_content.append("- **ICD-10-CM Code**: Found in `icd10_covered_all_articles.csv` (`icd10_code_id`) and `icd10_noncovered_all_articles.csv` (`icd10_code_id`)")
    md_content.append("- **ICD-10-PCS Code**: Found in `icd10_pcs_codes.csv` (`icd10_pcs_code` / column 5)")
    md_content.append("- **Modifier Code**: Found in `CMS_HCPCS_Modifiers_All_Articles.csv` (`hcpc_modifier_code_id`)")
    md_content.append("- **Revenue Code**: Found in `revenue_codes.csv` (`revenue_code` / column 6)")
    md_content.append("- **Bill Code**: Found in `article_bill_codes.csv` (`bill_code_id`)")
    md_content.append("- **Contractor/MAC**: Found in `lcd_contractor.csv` (`contractor_id`) and `lcd_article_relationship.csv` (`contractor_id`)")
    md_content.append("- **Jurisdiction**: Found in `cms_lcd_primary_jurisdiction.csv.xls` and `cms_article_jurisdiction.csv.xls` (`state_id`, `state_name`)\n")
    
    md_content.append("### Entity-to-Entity Relationships & Join Keys")
    
    relationships = [
        {
            "from": "LCD (`lcd_documents.csv`)",
            "to": "Article (`articles_700.csv`)",
            "via": "`lcd_article_relationship.csv`",
            "join_keys": "`lcd_id` and `article_id`"
        },
        {
            "from": "LCD (`lcd_documents.csv`)",
            "to": "NCD (`ncd_documents_data.csv`)",
            "via": "`lcd_related_ncd_documents.csv`",
            "join_keys": "`lcd_id` and `r_ncd_id` (matches `document_id` of NCD)"
        },
        {
            "from": "Article (`articles_700.csv`)",
            "to": "NCD (`ncd_documents_data.csv`)",
            "via": "`article_related_ncd_documents_data.csv`",
            "join_keys": "`article_id` and `r_ncd_id`"
        },
        {
            "from": "Article (`articles_700.csv`)",
            "to": "HCPCS (`CMS_HCPC_code.csv`)",
            "via": "`CMS_HCPC_code.csv` directly",
            "join_keys": "`article_id`"
        },
        {
            "from": "Article (`articles_700.csv`)",
            "to": "ICD-10-CM",
            "via": "`icd10_covered_all_articles.csv` / `icd10_noncovered_all_articles.csv`",
            "join_keys": "`article_id` to Articles; `icd10_code_id` to ICD-10-CM tabular reference"
        },
        {
            "from": "Article (`articles_700.csv`)",
            "to": "ICD-10-PCS",
            "via": "`icd10_pcs_codes.csv`",
            "join_keys": "`article_id`"
        },
        {
            "from": "Article (`articles_700.csv`)",
            "to": "Modifier",
            "via": "`CMS_HCPCS_Modifiers_All_Articles.csv`",
            "join_keys": "`article_id`"
        },
        {
            "from": "Article (`articles_700.csv`)",
            "to": "Revenue Code",
            "via": "`revenue_codes.csv`",
            "join_keys": "`article_id`"
        },
        {
            "from": "Article (`articles_700.csv`)",
            "to": "Jurisdiction / State",
            "via": "`cms_article_jurisdiction.csv.xls`",
            "join_keys": "`article_id`"
        },
        {
            "from": "LCD (`lcd_documents.csv`)",
            "to": "Jurisdiction / State",
            "via": "`cms_lcd_primary_jurisdiction.csv.xls`",
            "join_keys": "`lcd_id`"
        }
    ]
    
    md_content.append("| Source Entity | Target Entity | Bridge File | Join Keys |")
    md_content.append("| --- | --- | --- | --- |")
    for rel in relationships:
        md_content.append(f"| {rel['from']} | {rel['to']} | {rel['via']} | {rel['join_keys']} |")
        
    md_content.append("\n### Unresolved Relationship Links & Data Gaps")
    md_content.append("1. **ICD-10-CM Tabular PDF Reference (`icd10cm_tabular_2027.pdf`)**:")
    md_content.append("   - **Unresolved Link**: The PDF contains narrative text and tabular hierarchy for ICD-10-CM diagnoses. There is no direct structured key relationship file linking diagnostic codes to NCD/LCD guidelines programmatically other than standard string matching of codes (e.g. `C00.0` inside `icd10_covered_all_articles.csv` to standard ICD-10 chapters).")
    md_content.append("2. **Contractor Name mappings in `lcd_documents.csv` vs. IDs in `lcd_contractor.csv`**:")
    md_content.append("   - **Unresolved Link**: `lcd_documents.csv` contains textual contractor names (e.g., `'Palmetto GBA'`) in `contractor_name_type` but does not contain `contractor_id` to directly join with `lcd_contractor.csv` without string matching or intermediate joins.")
    
    with open(os.path.join(reports_dir, "relationship_report.md"), "w") as f:
        f.write("\n".join(md_content))

if __name__ == "__main__":
    run_audit()
