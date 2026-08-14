import pytest
from unittest.mock import MagicMock
from app.db.connection import db_connection
from scripts.ingest_cms_data import calculate_match_rates

def test_db_health_check_structure():
    """Verify that check_health returns a dictionary with the correct keys."""
    health = db_connection.check_health()
    assert isinstance(health, dict)
    assert "status" in health
    if health["status"] == "healthy":
        assert "database" in health
        assert "collections_stats" in health
    else:
        assert "error" in health

def test_calculate_match_rates_mocked():
    """Test relationship match rate calculations with a mock database."""
    mock_db = MagicMock()
    
    # Store unique mocks for each collection name
    collections = {}
    def get_collection(name):
        if name not in collections:
            collections[name] = MagicMock()
        return collections[name]
    
    mock_db.__getitem__.side_effect = get_collection
    
    # Configure unique collections
    lcd_ncd_col = get_collection("lcd_ncd_relationships")
    ncds_col = get_collection("ncds")
    lcd_art_col = get_collection("lcd_article_relationships")
    lcds_col = get_collection("lcds")
    articles_col = get_collection("articles")
    
    # Mock distinct results
    ncds_col.distinct.return_value = ["NCD1", "NCD2"]
    lcds_col.distinct.return_value = ["111"]
    articles_col.distinct.return_value = ["A1", "A2"]
    
    # 1. NCD-LCD
    def count_lcd_ncd(query=None):
        query = query or {}
        if not query:
            return 10
        if "r_ncd_id" in query:
            # We mock 2 matching NCD codes out of 10
            return 2
        return 0
    lcd_ncd_col.count_documents.side_effect = count_lcd_ncd
    
    # 2. LCD-Article
    def count_lcd_art(query=None):
        query = query or {}
        if not query:
            return 5
        if "lcd_id_numeric" in query:
            # 1 matching LCD
            return 1
        if "article_id_numeric" in query:
            # 2 matching Articles
            return 2
        return 0
    lcd_art_col.count_documents.side_effect = count_lcd_art
    
    # Set other collection counts to 0
    for name in [
        "article_hcpcs", "lcd_hcpcs", "icd10cm_article_covered", 
        "icd10cm_article_noncovered", "contractors", "lcd_jurisdictions", 
        "article_jurisdictions", "bill_codes", "article_modifiers"
    ]:
        get_collection(name).count_documents.return_value = 0
        
    rates = calculate_match_rates(mock_db)
    
    # NCD_LCD: 2 matched, 10 total -> 0.20
    assert rates["NCD_LCD"] == 0.20
    
    # LCD_Article: 5 total
    # lcd_match_rate = 1 / 5 = 0.20
    # article_match_rate = 2 / 5 = 0.40
    assert rates["LCD_Article"]["lcd_match_rate"] == 0.20
    assert rates["LCD_Article"]["article_match_rate"] == 0.40
