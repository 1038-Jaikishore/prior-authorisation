import pytest
from app.core.normalize import (
    normalize_ncd_id,
    normalize_lcd_id,
    normalize_article_id,
    normalize_hcpcs_code,
    normalize_icd10_code,
    normalize_modifier_code,
    normalize_revenue_code,
    normalize_bill_type_code,
    normalize_date
)
from scripts.audit_cms_datasets import detect_file_info

def test_ncd_normalization():
    assert normalize_ncd_id("50.8") == "50.8"
    assert normalize_ncd_id(" 50.8 ") == "50.8"
    assert normalize_ncd_id(None) == ""

def test_lcd_normalization():
    assert normalize_lcd_id("L40330") == "40330"
    assert normalize_lcd_id("40330") == "40330"
    assert normalize_lcd_id(" l40330 ") == "40330"
    assert normalize_lcd_id(None) == ""

def test_article_normalization():
    assert normalize_article_id("A58679") == "58679"
    assert normalize_article_id("58679") == "58679"
    assert normalize_article_id(" a58679 ") == "58679"
    assert normalize_article_id(None) == ""

def test_hcpcs_normalization():
    assert normalize_hcpcs_code("81202") == "81202"
    assert normalize_hcpcs_code(" J1459 ") == "J1459"
    assert normalize_hcpcs_code("A-4223") == "A4223"
    assert normalize_hcpcs_code(None) == ""

def test_icd10_normalization():
    assert normalize_icd10_code("C00.0") == "C000"
    assert normalize_icd10_code(" N17.0 ") == "N170"
    assert normalize_icd10_code("GZ2ZZZZ") == "GZ2ZZZZ"
    assert normalize_icd10_code(None) == ""

def test_modifier_normalization():
    assert normalize_modifier_code("59") == "59"
    assert normalize_modifier_code(" F1 ") == "F1"
    assert normalize_modifier_code(None) == ""

def test_revenue_code_normalization():
    assert normalize_revenue_code("409") == "0409"
    assert normalize_revenue_code("0409") == "0409"
    assert normalize_revenue_code("ER-450") == "0450"
    assert normalize_revenue_code(None) == ""

def test_bill_type_code_normalization():
    assert normalize_bill_type_code("111") == "0111"
    assert normalize_bill_type_code("0111") == "0111"
    assert normalize_bill_type_code(None) == ""

def test_date_normalization():
    assert normalize_date("08/13/2026") == "2026-08-13"
    assert normalize_date("2026-08-13") == "2026-08-13"
    assert normalize_date("08/13/26") == "2026-08-13"
    assert normalize_date("13-Aug-2026") == "2026-08-13"
    assert normalize_date("longstanding policy") == "longstanding policy"
    assert normalize_date(None) == ""

def test_format_detection():
    # PDF
    assert detect_file_info("icd10cm_tabular_2027.pdf", "/dummy/path.pdf")["format"] == "PDF"
    # Excel
    assert detect_file_info("lcd_master_excel_safe.csv.xlsx", "/dummy/path.xlsx")["format"] == "Excel"
    # CSV ending in xls
    assert detect_file_info("cms_article_jurisdiction.csv.xls", "/dummy/path.csv.xls")["format"] == "CSV"
