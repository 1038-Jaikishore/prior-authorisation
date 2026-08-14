import os
import sys
import csv
import json
import uuid
import pandas as pd
from datetime import datetime
from pymongo import UpdateOne

# Ensure backend folder is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.connection import db_connection
from app.core.normalize import (
    normalize_ncd_id,
    normalize_lcd_id,
    normalize_lcd_id_numeric,
    normalize_article_id,
    normalize_article_id_numeric,
    normalize_hcpcs_code,
    normalize_icd10_code,
    normalize_icd10_code_numeric,
    normalize_modifier_code,
    normalize_revenue_code,
    normalize_bill_type_code,
    normalize_date,
    build_provenance_field
)

# Increase CSV size limits
csv.field_size_limit(100000000)

raw_data_dir = "/Users/jaikishorep/Desktop/prior authorization/cms-prior-auth/backend/data/cms_data"
normalized_dir = "/Users/jaikishorep/Desktop/prior authorization/cms-prior-auth/backend/data/normalized"
reports_dir = "/Users/jaikishorep/Desktop/prior authorization/cms-prior-auth/backend/reports"
os.makedirs(normalized_dir, exist_ok=True)
os.makedirs(reports_dir, exist_ok=True)

# Run Metadata
INGESTION_RUN_ID = datetime.utcnow().strftime("%Y%m%d_%H%M%S_") + str(uuid.uuid4())[:8]
NORMALIZATION_VERSION = "1.1.0"

def get_df_or_empty(filename, mapping=None):
    """Safely loads a raw CMS file as a pandas DataFrame."""
    filepath = os.path.join(raw_data_dir, filename)
    if not os.path.exists(filepath):
        print(f"File not found: {filename}")
        return pd.DataFrame()
        
    encoding = "utf-8"
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            f.read(10000)
    except UnicodeDecodeError:
        encoding = "latin-1"
        
    try:
        if filename.endswith(".xlsx"):
            xl = pd.ExcelFile(filepath)
            return xl.parse(xl.sheet_names[0])
        elif filename.endswith(".xls") and not filename.endswith(".csv.xls"):
            # Real excel
            return pd.read_excel(filepath)
        else:
            # CSV (includes .csv and .csv.xls)
            if mapping:
                return pd.read_csv(filepath, encoding=encoding, header=None, names=mapping, on_bad_lines='skip')
            return pd.read_csv(filepath, encoding=encoding, on_bad_lines='skip')
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return pd.DataFrame()

def save_normalized_json(collection_name, data):
    """Saves normalized records to backend/data/normalized/ for validation."""
    out_path = os.path.join(normalized_dir, f"{collection_name}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Saved {len(data)} normalized records to {out_path}")

def run_ingestion():
    db = db_connection.get_db()
    print(f"Verified connection to: {db.name}")
    
    # Store run start
    ingestion_runs_col = db["ingestion_runs"]
    ingestion_runs_col.insert_one({
        "run_id": INGESTION_RUN_ID,
        "started_at": datetime.utcnow(),
        "status": "started",
        "normalization_version": NORMALIZATION_VERSION
    })
    
    counts = {}
    
    # 1. NCDs
    print("Normalizing NCDs...")
    ncd_df = get_df_or_empty("ncd_documents_data.csv")
    ncd_docs = []
    if not ncd_df.empty:
        ncd_df = ncd_df.fillna("")
        for idx, row in ncd_df.iterrows():
            ncd_docs.append({
                "ncd_id": build_provenance_field(row.get("document_id"), normalize_ncd_id(row.get("document_id")), normalize_ncd_id(row.get("document_id"))),
                "document_display_id": str(row.get("document_display_id")),
                "document_version": str(row.get("document_version")),
                "title": str(row.get("title")),
                "effective_date": normalize_date(row.get("effective_date")),
                "effective_end_date": normalize_date(row.get("effective_end_date")),
                "indications_limitations": str(row.get("indications_limitations")),
                "item_service_description": str(row.get("item_service_description")),
                "benefit_category": str(row.get("benefit_category")),
                "publication_number": str(row.get("publication_number")),
                "transmittal_number": str(row.get("transmittal_number")),
                "source_file": "ncd_documents_data.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("ncds", ncd_docs)
    
    # 2. LCDs (Consolidated)
    print("Normalizing LCDs (Consolidating)...")
    lcd_docs = {}
    
    # Merge lcd_documents.csv
    lcd_docs_df = get_df_or_empty("lcd_documents.csv")
    if not lcd_docs_df.empty:
        lcd_docs_df = lcd_docs_df.fillna("")
        for idx, row in lcd_docs_df.iterrows():
            lid = normalize_lcd_id_numeric(row.get("document_id"))
            lver = str(row.get("document_version"))
            key = (lid, lver)
            
            lcd_docs[key] = {
                "lcd_id": build_provenance_field(row.get("document_id"), lid, normalize_lcd_id(row.get("document_id"))),
                "lcd_version": lver,
                "display_id": str(row.get("document_display_id")),
                "title": str(row.get("title")),
                "effective_date": normalize_date(row.get("effective_date")),
                "retirement_date": normalize_date(row.get("retirement_date")),
                "contractor_name_type": str(row.get("contractor_name_type")),
                "url": str(row.get("url")),
                "note": str(row.get("note")),
                "source_files": ["lcd_documents.csv"],
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            }
            
    # Merge lcd_full_data.csv
    lcd_full_df = get_df_or_empty("lcd_full_data.csv")
    if not lcd_full_df.empty:
        lcd_full_df = lcd_full_df.fillna("")
        for idx, row in lcd_full_df.iterrows():
            lid = normalize_lcd_id_numeric(row.get("lcd_id"))
            lver = str(row.get("lcd_version"))
            key = (lid, lver)
            
            if key not in lcd_docs:
                lcd_docs[key] = {
                    "lcd_id": build_provenance_field(row.get("lcd_id"), lid, normalize_lcd_id(row.get("lcd_id"))),
                    "lcd_version": lver,
                    "display_id": str(row.get("display_id")),
                    "title": str(row.get("title")),
                    "source_files": [],
                    "ingestion_run_id": INGESTION_RUN_ID,
                    "normalization_version": NORMALIZATION_VERSION
                }
            lcd_docs[key].update({
                "cms_cov_policy": str(row.get("cms_cov_policy")),
                "indication": str(row.get("indication")),
                "diagnoses_support": str(row.get("diagnoses_support")),
                "diagnoses_dont_support": str(row.get("diagnoses_dont_support")),
                "coding_guidelines": str(row.get("coding_guidelines")),
                "doc_reqs": str(row.get("doc_reqs")),
                "status": str(row.get("status")),
                "last_updated": normalize_date(row.get("last_updated"))
            })
            lcd_docs[key]["source_files"].append("lcd_full_data.csv")
            
    # Merge lcd_master_excel_safe.csv.xlsx
    lcd_master_df = get_df_or_empty("lcd_master_excel_safe.csv.xlsx")
    if not lcd_master_df.empty:
        lcd_master_df = lcd_master_df.fillna("")
        for idx, row in lcd_master_df.iterrows():
            lid = normalize_lcd_id_numeric(row.get("lcd_id"))
            lver = str(row.get("lcd_version"))
            key = (lid, lver)
            
            if key not in lcd_docs:
                lcd_docs[key] = {
                    "lcd_id": build_provenance_field(row.get("lcd_id"), lid, normalize_lcd_id(row.get("lcd_id"))),
                    "lcd_version": lver,
                    "display_id": str(row.get("display_id")),
                    "title": str(row.get("title")),
                    "source_files": [],
                    "ingestion_run_id": INGESTION_RUN_ID,
                    "normalization_version": NORMALIZATION_VERSION
                }
            lcd_docs[key].update({
                "keywords": str(row.get("keywords")),
                "rev_eff_date": normalize_date(row.get("rev_eff_date"))
            })
            lcd_docs[key]["source_files"].append("lcd_master_excel_safe.csv.xlsx")
            
    lcd_docs_list = list(lcd_docs.values())
    save_normalized_json("lcds", lcd_docs_list)
    
    # 3. Articles
    print("Normalizing Articles...")
    art_df = get_df_or_empty("articles_700.csv")
    art_docs = []
    if not art_df.empty:
        art_df = art_df.fillna("")
        for idx, row in art_df.iterrows():
            art_docs.append({
                "article_id": build_provenance_field(row.get("article_id"), normalize_article_id_numeric(row.get("article_id")), normalize_article_id(row.get("article_id"))),
                "article_version": str(row.get("article_version")),
                "title": str(row.get("title")),
                "article_type_description": str(row.get("article_type_description")),
                "article_eff_date": normalize_date(row.get("article_eff_date")),
                "article_end_date": normalize_date(row.get("article_end_date")),
                "description": str(row.get("description")),
                "cms_cov_policy": str(row.get("cms_cov_policy")),
                "status": str(row.get("status")),
                "source_file": "articles_700.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("articles", art_docs)
    
    # 4. LCD-Article Relationships
    print("Normalizing LCD-Article Relationships...")
    lar_docs = []
    rel_df = get_df_or_empty("lcd_article_relationship.csv")
    if not rel_df.empty:
        rel_df = rel_df.fillna("")
        for idx, row in rel_df.iterrows():
            lar_docs.append({
                "lcd_id_numeric": normalize_lcd_id_numeric(row.get("lcd_id")),
                "lcd_version": str(row.get("lcd_version")),
                "article_id_numeric": normalize_article_id_numeric(row.get("article_id")),
                "article_version": str(row.get("article_version")),
                "contractor_id": str(row.get("contractor_id")),
                "last_updated": normalize_date(row.get("last_updated")),
                "source_file": "lcd_article_relationship.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
            
    # Also load from article_related_lcds.csv to build robust mappings
    art_rel_df = get_df_or_empty("article_related_lcds.csv")
    if not art_rel_df.empty:
        art_rel_df = art_rel_df.fillna("")
        for idx, row in art_rel_df.iterrows():
            lar_docs.append({
                "lcd_id_numeric": normalize_lcd_id_numeric(row.get("r_lcd_id")),
                "lcd_version": str(row.get("r_lcd_version")),
                "article_id_numeric": normalize_article_id_numeric(row.get("article_id")),
                "article_version": str(row.get("article_version")),
                "contractor_id": str(row.get("r_contractor_id")),
                "last_updated": normalize_date(row.get("last_updated")),
                "source_file": "article_related_lcds.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("lcd_article_relationships", lar_docs)
    
    # 5. LCD-NCD Relationships
    print("Normalizing LCD-NCD Relationships...")
    lnr_docs = []
    ln_df = get_df_or_empty("lcd_related_ncd_documents.csv")
    if not ln_df.empty:
        ln_df = ln_df.fillna("")
        for idx, row in ln_df.iterrows():
            lnr_docs.append({
                "lcd_id_numeric": normalize_lcd_id_numeric(row.get("lcd_id")),
                "lcd_version": str(row.get("lcd_version")),
                "r_ncd_id": normalize_ncd_id(row.get("r_ncd_id")),
                "r_ncd_version": str(row.get("r_ncd_version")),
                "source_file": "lcd_related_ncd_documents.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("lcd_ncd_relationships", lnr_docs)
    
    # 6. Article-NCD Relationships
    print("Normalizing Article-NCD Relationships...")
    anr_docs = []
    an_df = get_df_or_empty("article_related_ncd_documents_data.csv")
    if not an_df.empty:
        an_df = an_df.fillna("")
        for idx, row in an_df.iterrows():
            anr_docs.append({
                "article_id_numeric": normalize_article_id_numeric(row.get("article_id")),
                "article_version": str(row.get("article_version")),
                "r_ncd_id": normalize_ncd_id(row.get("r_ncd_id")),
                "r_ncd_version": str(row.get("r_ncd_version")),
                "source_file": "article_related_ncd_documents_data.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("article_ncd_relationships", anr_docs)
    
    # 7. HCPCS Codes (article mappings)
    print("Normalizing HCPCS Codes...")
    hcpcs_docs = []
    h_df = get_df_or_empty("CMS_HCPC_code.csv")
    if not h_df.empty:
        h_df = h_df.fillna("")
        for idx, row in h_df.iterrows():
            hcpcs_docs.append({
                "article_id_numeric": normalize_article_id_numeric(row.get("article_id")),
                "article_version": str(row.get("article_version")),
                "hcpcs_code": build_provenance_field(row.get("hcpc_code_id"), normalize_hcpcs_code(row.get("hcpc_code_id")), normalize_hcpcs_code(row.get("hcpc_code_id"))),
                "hcpc_code_version": str(row.get("hcpc_code_version")),
                "hcpc_code_group": str(row.get("hcpc_code_group")),
                "long_description": str(row.get("long_description")),
                "short_description": str(row.get("short_description")),
                "source_file": "CMS_HCPC_code.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("hcpcs_codes", hcpcs_docs)
    
    # 8. LCD HCPCS Mappings
    print("Normalizing LCD HCPCS Mappings...")
    lh_docs = []
    lh_df = get_df_or_empty("CMS_LCD_HCPCS_All_LCDs (1).csv")
    if not lh_df.empty:
        lh_df = lh_df.fillna("")
        for idx, row in lh_df.iterrows():
            lh_docs.append({
                "lcd_id_numeric": normalize_lcd_id_numeric(row.get("lcd_id")),
                "lcd_version": str(row.get("lcd_version")),
                "hcpcs_code": build_provenance_field(row.get("hcpc_code_id"), normalize_hcpcs_code(row.get("hcpc_code_id")), normalize_hcpcs_code(row.get("hcpc_code_id"))),
                "hcpc_code_version": str(row.get("hcpc_code_version")),
                "hcpc_code_group": str(row.get("hcpc_code_group")),
                "long_description": str(row.get("long_description")),
                "short_description": str(row.get("short_description")),
                "source_file": "CMS_LCD_HCPCS_All_LCDs (1).csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("lcd_hcpcs", lh_docs)
    
    # 9. Article HCPCS Mappings
    print("Normalizing Article HCPCS Mappings...")
    # article_hcpcs is identical in structure to hcpcs_codes (which links Articles to HCPCS)
    # We can save it under the name article_hcpcs for database isolation
    save_normalized_json("article_hcpcs", hcpcs_docs)
    
    # 10. HCPCS Groups (Consolidated)
    print("Normalizing HCPCS Groups...")
    groups_docs = []
    
    # Article HCPCS Groups
    ag_df = get_df_or_empty("CMS_HCPCS_Code_Groups_All_Articles.csv")
    if not ag_df.empty:
        ag_df = ag_df.fillna("")
        for idx, row in ag_df.iterrows():
            groups_docs.append({
                "entity_type": "article",
                "entity_id_numeric": normalize_article_id_numeric(row.get("article_id")),
                "entity_version": str(row.get("article_version")),
                "hcpc_code_group": str(row.get("hcpc_code_group")),
                "paragraph": str(row.get("paragraph")),
                "source_file": "CMS_HCPCS_Code_Groups_All_Articles.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
            
    # LCD HCPCS Groups
    lg_df = get_df_or_empty("CMS_LCD_HCPCS_Code_Groups_All_LCDs.csv")
    if not lg_df.empty:
        lg_df = lg_df.fillna("")
        for idx, row in lg_df.iterrows():
            groups_docs.append({
                "entity_type": "lcd",
                "entity_id_numeric": normalize_lcd_id_numeric(row.get("lcd_id")),
                "entity_version": str(row.get("lcd_version")),
                "hcpc_code_group": str(row.get("hcpc_code_group")),
                "paragraph": str(row.get("paragraph")),
                "source_file": "CMS_LCD_HCPCS_Code_Groups_All_LCDs.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("hcpcs_groups", groups_docs)
    
    # 11. Article Modifiers
    print("Normalizing Article Modifiers...")
    mod_docs = []
    
    # Modifiers
    m_df = get_df_or_empty("CMS_HCPCS_Modifiers_All_Articles.csv")
    if not m_df.empty:
        m_df = m_df.fillna("")
        for idx, row in m_df.iterrows():
            mod_docs.append({
                "article_id_numeric": normalize_article_id_numeric(row.get("article_id")),
                "article_version": str(row.get("article_version")),
                "modifier_code": build_provenance_field(row.get("hcpc_modifier_code_id"), normalize_modifier_code(row.get("hcpc_modifier_code_id")), normalize_modifier_code(row.get("hcpc_modifier_code_id"))),
                "hcpc_modifier_code_version": str(row.get("hcpc_modifier_code_version")),
                "hcpc_modifier_group": str(row.get("hcpc_modifier_group")),
                "description": str(row.get("description")),
                "source_file": "CMS_HCPCS_Modifiers_All_Articles.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
            
    # Modifier Groups
    mg_df = get_df_or_empty("CMS_HCPCS_Modifier_Groups_All_Articles.csv")
    if not mg_df.empty:
        mg_df = mg_df.fillna("")
        for idx, row in mg_df.iterrows():
            mod_docs.append({
                "article_id_numeric": normalize_article_id_numeric(row.get("article_id")),
                "article_version": str(row.get("article_version")),
                "hcpc_modifier_group": str(row.get("hcpc_modifier_group")),
                "paragraph": str(row.get("paragraph")),
                "source_file": "CMS_HCPCS_Modifier_Groups_All_Articles.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("article_modifiers", mod_docs)
    
    # 12. ICD-10 covered
    print("Normalizing ICD-10 Covered...")
    covered_docs = []
    cov_df = get_df_or_empty("icd10_covered_all_articles.csv")
    if not cov_df.empty:
        cov_df = cov_df.fillna("")
        for idx, row in cov_df.iterrows():
            covered_docs.append({
                "article_id_numeric": normalize_article_id_numeric(row.get("article_id")),
                "article_version": str(row.get("article_version")),
                "icd10_code": build_provenance_field(row.get("icd10_code_id"), normalize_icd10_code_numeric(row.get("icd10_code_id")), normalize_icd10_code(row.get("icd10_code_id"))),
                "icd10_code_version": str(row.get("icd10_code_version")),
                "icd10_covered_group": str(row.get("icd10_covered_group")),
                "description": str(row.get("description")),
                "asterisk": str(row.get("asterisk")),
                "source_file": "icd10_covered_all_articles.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("icd10cm_article_covered", covered_docs)
    
    # 13. ICD-10 noncovered
    print("Normalizing ICD-10 Noncovered...")
    noncovered_docs = []
    ncov_df = get_df_or_empty("icd10_noncovered_all_articles.csv")
    if not ncov_df.empty:
        ncov_df = ncov_df.fillna("")
        for idx, row in ncov_df.iterrows():
            noncovered_docs.append({
                "article_id_numeric": normalize_article_id_numeric(row.get("article_id")),
                "article_version": str(row.get("article_version")),
                "icd10_code": build_provenance_field(row.get("icd10_code_id"), normalize_icd10_code_numeric(row.get("icd10_code_id")), normalize_icd10_code(row.get("icd10_code_id"))),
                "icd10_code_version": str(row.get("icd10_code_version")),
                "icd10_noncovered_group": str(row.get("icd10_noncovered_group")),
                "description": str(row.get("description")),
                "source_file": "icd10_noncovered_all_articles.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("icd10cm_article_noncovered", noncovered_docs)
    
    # 14. ICD-10 PCS
    print("Normalizing ICD-10 PCS...")
    pcs_docs = []
    pcs_mapping = HEADERLESS_MAPPINGS["icd10_pcs_codes.csv"]
    pcs_df = get_df_or_empty("icd10_pcs_codes.csv", pcs_mapping)
    if not pcs_df.empty:
        pcs_df = pcs_df.fillna("")
        for idx, row in pcs_df.iterrows():
            pcs_docs.append({
                "article_id_numeric": normalize_article_id_numeric(row.get("article_id")),
                "article_version": str(row.get("article_version")),
                "icd10_pcs_code": build_provenance_field(row.get("icd10_pcs_code"), normalize_icd10_code_numeric(row.get("icd10_pcs_code")), normalize_icd10_code(row.get("icd10_pcs_code"))),
                "description": str(row.get("description")),
                "icd10_pcs_group": str(row.get("icd10_pcs_group")),
                "source_file": "icd10_pcs_codes.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("icd10pcs_codes", pcs_docs)
    
    # 15. Bill Codes
    print("Normalizing Bill Codes...")
    bill_docs = []
    b_df = get_df_or_empty("article_bill_codes.csv")
    if not b_df.empty:
        b_df = b_df.fillna("")
        for idx, row in b_df.iterrows():
            bill_docs.append({
                "article_id_numeric": normalize_article_id_numeric(row.get("article_id")),
                "article_version": str(row.get("article_version")),
                "bill_type_code": build_provenance_field(row.get("bill_code_id"), normalize_bill_type_code(row.get("bill_code_id")), normalize_bill_type_code(row.get("bill_code_id"))),
                "bill_code_version": str(row.get("bill_code_version")),
                "description": str(row.get("description")),
                "source_file": "article_bill_codes.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("bill_codes", bill_docs)
    
    # 16. Revenue Codes
    print("Normalizing Revenue Codes...")
    rev_docs = []
    rev_mapping = HEADERLESS_MAPPINGS["revenue_codes.csv"]
    r_df = get_df_or_empty("revenue_codes.csv", rev_mapping)
    if not r_df.empty:
        r_df = r_df.fillna("")
        for idx, row in r_df.iterrows():
            rev_docs.append({
                "article_id_numeric": normalize_article_id_numeric(row.get("article_id")),
                "article_version": str(row.get("article_version")),
                "revenue_code": build_provenance_field(row.get("revenue_code"), normalize_revenue_code(row.get("revenue_code")), normalize_revenue_code(row.get("revenue_code"))),
                "description": str(row.get("description")),
                "source_file": "revenue_codes.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("revenue_codes", rev_docs)
    
    # 17. Contractors
    print("Normalizing Contractors...")
    con_docs = []
    c_df = get_df_or_empty("lcd_contractor.csv")
    if not c_df.empty:
        c_df = c_df.fillna("")
        for idx, row in c_df.iterrows():
            con_docs.append({
                "lcd_id_numeric": normalize_lcd_id_numeric(row.get("lcd_id")),
                "lcd_version": str(row.get("lcd_version")),
                "contractor_id": str(row.get("contractor_id")),
                "contractor_type_id": str(row.get("contractor_type_id")),
                "contractor_version": str(row.get("contractor_version")),
                "source_file": "lcd_contractor.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("contractors", con_docs)
    
    # 18. LCD Jurisdictions
    print("Normalizing LCD Jurisdictions...")
    lj_docs = []
    lj_df = get_df_or_empty("cms_lcd_primary_jurisdiction.csv.xls")
    if not lj_df.empty:
        lj_df = lj_df.fillna("")
        for idx, row in lj_df.iterrows():
            lj_docs.append({
                "lcd_id_numeric": normalize_lcd_id_numeric(row.get("lcd_id")),
                "lcd_version": str(row.get("lcd_version")),
                "state_id": str(row.get("state_id")),
                "state_name": str(row.get("state_name")),
                "source_file": "cms_lcd_primary_jurisdiction.csv.xls",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("lcd_jurisdictions", lj_docs)
    
    # 19. Article Jurisdictions
    print("Normalizing Article Jurisdictions...")
    aj_docs = []
    aj_df = get_df_or_empty("cms_article_jurisdiction.csv.xls")
    if not aj_df.empty:
        aj_df = aj_df.fillna("")
        for idx, row in aj_df.iterrows():
            aj_docs.append({
                "article_id_numeric": normalize_article_id_numeric(row.get("article_id")),
                "article_version": str(row.get("article_version")),
                "state_id": str(row.get("state_id")),
                "state_name": str(row.get("state_name")),
                "source_file": "cms_article_jurisdiction.csv.xls",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("article_jurisdictions", aj_docs)
    
    # 20. Related Documents
    print("Normalizing Related Documents...")
    rd_docs = []
    rd_df = get_df_or_empty("lcd_related_documents.csv")
    if not rd_df.empty:
        rd_df = rd_df.fillna("")
        for idx, row in rd_df.iterrows():
            rd_docs.append({
                "lcd_id_numeric": normalize_lcd_id_numeric(row.get("lcd_id")),
                "lcd_version": str(row.get("lcd_version")),
                "r_article_id_numeric": normalize_article_id_numeric(row.get("r_article_id")),
                "r_article_version": str(row.get("r_article_version")),
                "r_contractor_id": str(row.get("r_contractor_id")),
                "r_lcd_id_numeric": normalize_lcd_id_numeric(row.get("r_lcd_id")),
                "r_lcd_version": str(row.get("r_lcd_version")),
                "related_num": str(row.get("related_num")),
                "url": str(row.get("url")),
                "source_file": "lcd_related_documents.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("related_documents", rd_docs)
    
    # 21. Revision History
    print("Normalizing Revision History...")
    rev_hist_docs = []
    rh_df = get_df_or_empty("lcd_revision_history.csv")
    if not rh_df.empty:
        rh_df = rh_df.fillna("")
        for idx, row in rh_df.iterrows():
            rev_hist_docs.append({
                "lcd_id_numeric": normalize_lcd_id_numeric(row.get("lcd_id")),
                "lcd_version": str(row.get("lcd_version")),
                "rev_hist_num": str(row.get("rev_hist_num")),
                "rev_hist_date": normalize_date(row.get("rev_hist_date")),
                "rev_hist_exp": str(row.get("rev_hist_exp")),
                "source_file": "lcd_revision_history.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("revision_history", rev_hist_docs)
    
    # 22. Coding Information
    print("Normalizing Coding Information...")
    ci_docs = []
    ci_df = get_df_or_empty("CMS_Other_Coding_Information_All_Articles.csv")
    if not ci_df.empty:
        ci_df = ci_df.fillna("")
        for idx, row in ci_df.iterrows():
            ci_docs.append({
                "article_id_numeric": normalize_article_id_numeric(row.get("article_id")),
                "article_version": str(row.get("article_version")),
                "other_coding_group": str(row.get("other_coding_group")),
                "paragraph": str(row.get("paragraph")),
                "codes": str(row.get("codes")),
                "source_file": "CMS_Other_Coding_Information_All_Articles.csv",
                "source_row": idx,
                "ingestion_run_id": INGESTION_RUN_ID,
                "normalization_version": NORMALIZATION_VERSION
            })
    save_normalized_json("coding_information", ci_docs)
    
    # Upload collections maps
    collection_data = {
        "ncds": (ncd_docs, ["ncd_id.canonical_value", "document_version"]),
        "lcds": (lcd_docs_list, ["lcd_id.canonical_value", "lcd_version"]),
        "articles": (art_docs, ["article_id.canonical_value", "article_version"]),
        "lcd_article_relationships": (lar_docs, ["lcd_id_numeric", "lcd_version", "article_id_numeric", "article_version"]),
        "lcd_ncd_relationships": (lnr_docs, ["lcd_id_numeric", "lcd_version", "r_ncd_id", "r_ncd_version"]),
        "article_ncd_relationships": (anr_docs, ["article_id_numeric", "article_version", "r_ncd_id", "r_ncd_version"]),
        "hcpcs_codes": (hcpcs_docs, ["article_id_numeric", "article_version", "hcpcs_code.canonical_value"]),
        "lcd_hcpcs": (lh_docs, ["lcd_id_numeric", "lcd_version", "hcpcs_code.canonical_value"]),
        "article_hcpcs": (hcpcs_docs, ["article_id_numeric", "article_version", "hcpcs_code.canonical_value"]),
        "hcpcs_groups": (groups_docs, ["entity_type", "entity_id_numeric", "entity_version", "hcpc_code_group"]),
        "article_modifiers": (mod_docs, ["article_id_numeric", "article_version", "modifier_code.canonical_value"]),
        "icd10cm_article_covered": (covered_docs, ["article_id_numeric", "article_version", "icd10_code.canonical_value", "icd10_code_version"]),
        "icd10cm_article_noncovered": (noncovered_docs, ["article_id_numeric", "article_version", "icd10_code.canonical_value", "icd10_code_version"]),
        "icd10pcs_codes": (pcs_docs, ["article_id_numeric", "article_version", "icd10_pcs_code.canonical_value"]),
        "bill_codes": (bill_docs, ["article_id_numeric", "article_version", "bill_type_code.canonical_value"]),
        "revenue_codes": (rev_docs, ["article_id_numeric", "article_version", "revenue_code.canonical_value"]),
        "contractors": (con_docs, ["lcd_id_numeric", "lcd_version", "contractor_id"]),
        "lcd_jurisdictions": (lj_docs, ["lcd_id_numeric", "lcd_version", "state_id"]),
        "article_jurisdictions": (aj_docs, ["article_id_numeric", "article_version", "state_id"]),
        "related_documents": (rd_docs, ["lcd_id_numeric", "lcd_version", "r_article_id_numeric", "r_lcd_id_numeric"]),
        "revision_history": (rev_hist_docs, ["lcd_id_numeric", "lcd_version", "rev_hist_num"]),
        "coding_information": (ci_docs, ["article_id_numeric", "article_version", "other_coding_group"])
    }
    
    # Perform upserts
    print("Starting Idempotent bulk uploading to MongoDB...")
    for col_name, (docs, unique_fields) in collection_data.items():
        if not docs:
            print(f"Skipping empty collection: {col_name}")
            counts[col_name] = 0
            continue
            
        col = db[col_name]
        operations = []
        
        try:
            # Clear collection for clean idempotent load
            col.delete_many({})
            
            # Deduplicate documents in memory
            seen = set()
            unique_docs = []
            for doc in docs:
                # build a key from unique_fields
                key_parts = []
                for field in unique_fields:
                    parts = field.split('.')
                    val = doc
                    for part in parts:
                        if isinstance(val, dict):
                            val = val.get(part)
                        else:
                            val = None
                    key_parts.append(str(val))
                key = tuple(key_parts)
                if key not in seen:
                    seen.add(key)
                    unique_docs.append(doc)
            
            # Perform bulk insert
            if unique_docs:
                col.insert_many(unique_docs)
            print(f"Collection '{col_name}': inserted {len(unique_docs)} records (removed {len(docs) - len(unique_docs)} duplicates).")
            counts[col_name] = len(unique_docs)
            
            # Create indexes
            for field in unique_fields:
                col.create_index(field)
            print(f"Created indexes for Unique Keys on '{col_name}'")
        except Exception as e:
            print(f"Error writing to {col_name}: {e}")
            counts[col_name] = 0
            
    # Save statistics and match rates
    rates = calculate_match_rates(db)
    
    # Complete ingestion run logs
    ingestion_runs_col.update_one(
        {"run_id": INGESTION_RUN_ID},
        {"$set": {
            "status": "completed",
            "completed_at": datetime.utcnow(),
            "records_inserted": counts,
            "relationship_match_rates": rates
        }}
    )
    
    # Generate Relationship Report MD
    write_relationship_validation_report_md(rates, counts)
    
    return counts, rates

def calculate_match_rates(db):
    """Calculates match rates for referenced entities to evaluate referential integrity."""
    print("Calculating relationship referential-integrity match rates...")
    rates = {}
    
    # Pre-fetch distinct canonical keys for fast local memory lookup/matching if small
    ncds = db["ncds"].distinct("ncd_id.canonical_value")
    lcds = db["lcds"].distinct("lcd_id.canonical_value")
    arts = db["articles"].distinct("article_id.canonical_value")
    
    # 1. NCD <-> LCD
    lcd_ncd_count = db["lcd_ncd_relationships"].count_documents({})
    if lcd_ncd_count > 0:
        matched = db["lcd_ncd_relationships"].count_documents({"r_ncd_id": {"$in": ncds}})
        rates["NCD_LCD"] = matched / lcd_ncd_count
    else:
        rates["NCD_LCD"] = 1.0
        
    # 2. LCD <-> Article
    lcd_art_count = db["lcd_article_relationships"].count_documents({})
    if lcd_art_count > 0:
        matched_lcd = db["lcd_article_relationships"].count_documents({"lcd_id_numeric": {"$in": lcds}})
        matched_art = db["lcd_article_relationships"].count_documents({"article_id_numeric": {"$in": arts}})
        rates["LCD_Article"] = {
            "lcd_match_rate": matched_lcd / lcd_art_count,
            "article_match_rate": matched_art / lcd_art_count
        }
    else:
        rates["LCD_Article"] = {"lcd_match_rate": 1.0, "article_match_rate": 1.0}
        
    # 3. Article <-> HCPCS
    art_hcpcs_count = db["article_hcpcs"].count_documents({})
    if art_hcpcs_count > 0:
        matched = db["article_hcpcs"].count_documents({"article_id_numeric": {"$in": arts}})
        rates["Article_HCPCS"] = matched / art_hcpcs_count
    else:
        rates["Article_HCPCS"] = 1.0
        
    # 4. LCD <-> HCPCS
    lcd_hcpcs_count = db["lcd_hcpcs"].count_documents({})
    if lcd_hcpcs_count > 0:
        matched = db["lcd_hcpcs"].count_documents({"lcd_id_numeric": {"$in": lcds}})
        rates["LCD_HCPCS"] = matched / lcd_hcpcs_count
    else:
        rates["LCD_HCPCS"] = 1.0
        
    # 5. Article <-> ICD-10 Covered
    cov_count = db["icd10cm_article_covered"].count_documents({})
    if cov_count > 0:
        matched = db["icd10cm_article_covered"].count_documents({"article_id_numeric": {"$in": arts}})
        rates["Article_ICD10_Covered"] = matched / cov_count
    else:
        rates["Article_ICD10_Covered"] = 1.0
        
    # 6. Article <-> ICD-10 Noncovered
    ncov_count = db["icd10cm_article_noncovered"].count_documents({})
    if ncov_count > 0:
        matched = db["icd10cm_article_noncovered"].count_documents({"article_id_numeric": {"$in": arts}})
        rates["Article_ICD10_Noncovered"] = matched / ncov_count
    else:
        rates["Article_ICD10_Noncovered"] = 1.0
        
    # 7. LCD <-> Contractor/MAC
    con_count = db["contractors"].count_documents({})
    if con_count > 0:
        matched = db["contractors"].count_documents({"lcd_id_numeric": {"$in": lcds}})
        rates["LCD_Contractor"] = matched / con_count
    else:
        rates["LCD_Contractor"] = 1.0
        
    # 8. LCD <-> Jurisdiction
    lj_count = db["lcd_jurisdictions"].count_documents({})
    if lj_count > 0:
        matched = db["lcd_jurisdictions"].count_documents({"lcd_id_numeric": {"$in": lcds}})
        rates["LCD_Jurisdiction"] = matched / lj_count
    else:
        rates["LCD_Jurisdiction"] = 1.0
        
    # 9. Article <-> Jurisdiction
    aj_count = db["article_jurisdictions"].count_documents({})
    if aj_count > 0:
        matched = db["article_jurisdictions"].count_documents({"article_id_numeric": {"$in": arts}})
        rates["Article_Jurisdiction"] = matched / aj_count
    else:
        rates["Article_Jurisdiction"] = 1.0
        
    # 10. Article <-> Bill Codes
    bill_count = db["bill_codes"].count_documents({})
    if bill_count > 0:
        matched = db["bill_codes"].count_documents({"article_id_numeric": {"$in": arts}})
        rates["Article_Bill_Codes"] = matched / bill_count
    else:
        rates["Article_Bill_Codes"] = 1.0
        
    # 11. Article <-> Modifiers
    mod_count = db["article_modifiers"].count_documents({})
    if mod_count > 0:
        matched = db["article_modifiers"].count_documents({"article_id_numeric": {"$in": arts}})
        rates["Article_Modifiers"] = matched / mod_count
    else:
        rates["Article_Modifiers"] = 1.0
        
    return rates

def write_relationship_validation_report_md(rates, counts):
    """Outputs the referential integrity match rate validation report."""
    md_content = ["# Volume 2 Referential Integrity & Ingestion Match Rate Validation\n"]
    md_content.append("## Collection Document Counts\n")
    md_content.append("| Collection Name | Total Documents |")
    md_content.append("| --- | --- |")
    for col_name, count in counts.items():
        md_content.append(f"| {col_name} | {count:,} |")
        
    md_content.append("\n## Relationship Match Rates\n")
    md_content.append("| Relation Link | Calculated Match Rate |")
    md_content.append("| --- | --- |")
    
    for k, v in rates.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                md_content.append(f"| {k} ({sub_k}) | {sub_v * 100:.2f}% |")
        else:
            md_content.append(f"| {k} | {v * 100:.2f}% |")
            
    md_content.append("\n## Referential Integrity Observations")
    md_content.append("1. **NCD-LCD Relationships**: If there are unmatched references in mapping tables, it indicates LCD policies that cite NCD codes that aren't fully represented in the sample NCD subset.")
    md_content.append("2. **LCD-Article Mappings**: In many cases, billing articles exist without an active LCD, or vice-versa, which represents standard Medicare Administrative Contractor operations.")
    
    report_path = os.path.join(reports_dir, "relationship_validation_report.md")
    with open(report_path, "w") as f:
        f.write("\n".join(md_content))
    print(f"Generated validation match report: {report_path}")

# Inferred header layouts mapping definition for reference
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

if __name__ == "__main__":
    run_ingestion()
