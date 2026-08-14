import re
from datetime import datetime

def normalize_ncd_id(ncd_id) -> str:
    """Normalize NCD ID by stripping whitespace and converting to string."""
    if ncd_id is None:
        return ""
    val = str(ncd_id).strip()
    return val

def normalize_lcd_id(lcd_id) -> str:
    """Normalize LCD ID to its official display format (e.g. L32553)."""
    if lcd_id is None:
        return ""
    val = str(lcd_id).strip().upper()
    val = re.sub(r'[^A-Z0-9]', '', val)
    if not val:
        return ""
    if not val.startswith('L'):
        val = 'L' + val
    return val

def normalize_lcd_id_numeric(lcd_id) -> str:
    """Normalize LCD ID by stripping any 'L' prefix to get only the numeric string."""
    if lcd_id is None:
        return ""
    val = str(lcd_id).strip().upper()
    if val.startswith('L'):
        val = val[1:]
    return re.sub(r'\D', '', val)

def normalize_article_id(article_id) -> str:
    """Normalize Article ID to its official display format (e.g. A56424)."""
    if article_id is None:
        return ""
    val = str(article_id).strip().upper()
    val = re.sub(r'[^A-Z0-9]', '', val)
    if not val:
        return ""
    if not val.startswith('A'):
        val = 'A' + val
    return val

def normalize_article_id_numeric(article_id) -> str:
    """Normalize Article ID by stripping any 'A' prefix to get only the numeric string."""
    if article_id is None:
        return ""
    val = str(article_id).strip().upper()
    if val.startswith('A'):
        val = val[1:]
    return re.sub(r'\D', '', val)

def normalize_hcpcs_code(code) -> str:
    """Normalize HCPCS/CPT codes: uppercase, alphanumeric only."""
    if code is None:
        return ""
    val = str(code).strip().upper()
    return re.sub(r'[^A-Z0-9]', '', val)

def normalize_icd10_code(code) -> str:
    """Normalize ICD-10 code to its official display dotted format (e.g. C00.0)."""
    if code is None:
        return ""
    val = str(code).strip().upper()
    val = re.sub(r'[^A-Z0-9.]', '', val)
    if not val:
        return ""
    
    # Standard format for CM (e.g. C00.0)
    # PCS codes don't have dots (e.g. GZ2ZZZZ), let's not add a dot if it looks like a PCS code
    # Typically, if it is 7 characters and has no dots, it is a PCS code.
    if len(val) >= 3 and '.' not in val:
        # Check if it matches typical CM diagnosis pattern (letter + 2 digits + optional rest)
        # If it is a CM code, we might add a dot after the 3rd char if it's not present.
        # But let's only do it if it matches CM format and length is > 3.
        if re.match(r'^[A-Z]\d{2}', val) and len(val) > 3:
            # Let's verify if this matches standard CM (PCS is 7 characters alphanumeric, e.g. GZ2ZZZZ)
            # GZ2ZZZZ starts with GZ (letter + letter), so it won't match [A-Z]\d{2} (which is letter + digit + digit).
            # So if it matches [A-Z]\d{2}, it is likely a CM code!
            return val[:3] + '.' + val[3:]
            
    return val

def normalize_icd10_code_numeric(code) -> str:
    """Normalize ICD-10 codes by removing dot to get alphanumeric representation (e.g. C000)."""
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

def build_provenance_field(source_val, canonical_val, display_val):
    """Utility to build document structure for a key preserving raw, display and canonical values."""
    return {
        "source_value": str(source_val) if source_val is not None else "",
        "canonical_value": str(canonical_val) if canonical_val is not None else "",
        "display_value": str(display_val) if display_val is not None else ""
    }
