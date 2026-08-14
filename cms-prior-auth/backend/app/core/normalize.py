import re
from datetime import datetime

def normalize_ncd_id(ncd_id) -> str:
    """Normalize NCD ID by stripping whitespace and converting to string."""
    if ncd_id is None:
        return ""
    val = str(ncd_id).strip()
    return val

def normalize_lcd_id(lcd_id) -> str:
    """Normalize LCD ID by stripping 'L' prefix and returning numeric string representation."""
    if lcd_id is None:
        return ""
    val = str(lcd_id).strip().upper()
    if val.startswith('L'):
        val = val[1:]
    return val

def normalize_article_id(article_id) -> str:
    """Normalize Article ID by stripping 'A' prefix and returning numeric string representation."""
    if article_id is None:
        return ""
    val = str(article_id).strip().upper()
    if val.startswith('A'):
        val = val[1:]
    return val

def normalize_hcpcs_code(code) -> str:
    """Normalize HCPCS/CPT codes: uppercase, alphanumeric only."""
    if code is None:
        return ""
    val = str(code).strip().upper()
    return re.sub(r'[^A-Z0-9]', '', val)

def normalize_icd10_code(code) -> str:
    """Normalize ICD-10 (CM or PCS) codes: uppercase, alphanumeric only (strips dots)."""
    if code is None:
        return ""
    val = str(code).strip().upper()
    return re.sub(r'[^A-Z0-9]', '', val)

def normalize_modifier_code(code) -> str:
    """Normalize modifier code: uppercase, alphanumeric only, max 2 chars."""
    if code is None:
        return ""
    val = str(code).strip().upper()
    return re.sub(r'[^A-Z0-9]', '', val)[:2]

def normalize_revenue_code(code) -> str:
    """Normalize revenue codes: pad to 4 digits with leading zeros."""
    if code is None:
        return ""
    val = str(code).strip()
    val = re.sub(r'\D', '', val)
    if not val:
        return ""
    return val.zfill(4)

def normalize_bill_type_code(code) -> str:
    """Normalize Bill Type codes: pad to 4 characters with leading zeros."""
    if code is None:
        return ""
    val = str(code).strip()
    val = re.sub(r'\D', '', val)
    if not val:
        return ""
    return val.zfill(4)

def normalize_date(date_str) -> str:
    """Normalize date strings of various formats into ISO standard YYYY-MM-DD.
    
    If the date format is unrecognized or contains textual non-date info,
    it returns the stripped original string.
    """
    if date_str is None:
        return ""
    val = str(date_str).strip()
    if not val:
        return ""
    
    # Try common formats
    formats = [
        '%m/%d/%Y',  # 08/13/2026
        '%Y-%m-%d',  # 2026-08-13
        '%m/%d/%y',  # 08/13/26
        '%d-%b-%Y',  # 13-Aug-2026
        '%Y/%m/%d',  # 2026/08/13
        '%Y-%m-%d %H:%M:%S',  # 2026-08-13 00:00:00
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(val, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
            
    # Return original if parsing fails
    return val
