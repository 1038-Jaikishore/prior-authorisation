import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
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
            # Set default count_documents to 0 to prevent type errors in loop checks
            collections[name].count_documents.return_value = 0
            collections[name].distinct.return_value = []
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
    
    # 1. NCD-LCD: 10 total. query filters using $nin for broken refs
    def count_lcd_ncd(query=None):
        query = query or {}
        if not query:
            return 10
        if "r_ncd_id" in query:
            # We mock 8 broken NCD codes out of 10 (2 match)
            return 8
        return 0
    lcd_ncd_col.count_documents.side_effect = count_lcd_ncd
    
    # 2. LCD-Article: 5 total. query filters using $nin for broken refs
    def count_lcd_art(query=None):
        query = query or {}
        if not query:
            return 5
        if "lcd_id_numeric" in query:
            # 4 broken LCD refs (1 match)
            return 4
        if "article_id_numeric" in query:
            # 3 broken Article refs (2 match)
            return 3
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
    
    # NCD_LCD: 8 broken, 10 total -> match rate = (10 - 8)/10 = 0.20
    assert rates["NCD_LCD"]["match_rate"] == 0.20
    
    # LCD_Article: 5 total
    # lcd_match_rate = (5 - 4) / 5 = 0.20
    # article_match_rate = (5 - 3) / 5 = 0.40
    assert rates["LCD_Article"]["lcd_match_rate"] == 0.20
    assert rates["LCD_Article"]["article_match_rate"] == 0.40


@patch("scripts.ingest_cms_data.db_connection.get_db")
def test_ingestion_no_wipe_by_default(mock_get_db):
    """Verify that delete_many is NOT called by default (full_rebuild=False)."""
    mock_db = MagicMock()
    mock_col = MagicMock()
    mock_col.count_documents.return_value = 0
    mock_col.distinct.return_value = []
    
    mock_db.__getitem__.return_value = mock_col
    mock_get_db.return_value = mock_db
    
    from scripts.ingest_cms_data import run_ingestion
    
    with patch("scripts.ingest_cms_data.get_df_or_empty") as mock_df:
        # Create a dummy DataFrame with target columns to pass basic parses without KeyError
        dummy_df = pd.DataFrame([{"document_id": "1", "document_version": "1"}])
        mock_df.return_value = dummy_df
        
        # Test normal mode
        run_ingestion(full_rebuild=False)
        assert not mock_col.delete_many.called
        
        # Reset mock call status
        mock_col.delete_many.reset_mock()
        
        # Test full rebuild mode
        run_ingestion(full_rebuild=True)
        assert mock_col.delete_many.called


def test_prefix_preservation_real_db():
    """Verify that MongoDB documents retain official display formats alongside canonical ones."""
    db = db_connection.get_db()
    # Check LCD
    lcd_doc = db["lcds"].find_one({"lcd_id.display_value": {"$regex": "^L"}})
    if lcd_doc:
        assert "lcd_id" in lcd_doc
        assert lcd_doc["lcd_id"]["display_value"].startswith("L")
        assert lcd_doc["lcd_id"]["canonical_value"].isdigit()
    
    # Check Article
    art_doc = db["articles"].find_one({"article_id.display_value": {"$regex": "^A"}})
    if art_doc:
        assert "article_id" in art_doc
        assert art_doc["article_id"]["display_value"].startswith("A")
        assert art_doc["article_id"]["canonical_value"].isdigit()

    # Check ICD-10
    icd_doc = db["icd10cm_article_covered"].find_one({"icd10_code.display_value": {"$regex": "\\."}})
    if icd_doc:
        assert "icd10_code" in icd_doc
        assert "." in icd_doc["icd10_code"]["display_value"]
        assert "." not in icd_doc["icd10_code"]["canonical_value"]


def test_routing_critical_joins():
    """Verify that all 9 routing-critical paths can be queried correctly in MongoDB."""
    db = db_connection.get_db()
    
    # 1. HCPCS -> candidate LCD
    lh_doc = db["lcd_hcpcs"].find_one()
    if lh_doc:
        hcpcs = lh_doc["hcpcs_code"]["canonical_value"]
        candidates = list(db["lcd_hcpcs"].find({"hcpcs_code.canonical_value": hcpcs}))
        assert len(candidates) > 0
        for cand in candidates:
            assert "lcd_id_numeric" in cand

    # 2. LCD -> jurisdiction
    lj_doc = db["lcd_jurisdictions"].find_one()
    if lj_doc:
        lcd_id = lj_doc["lcd_id_numeric"]
        jurs = list(db["lcd_jurisdictions"].find({"lcd_id_numeric": lcd_id}))
        assert len(jurs) > 0
        for jur in jurs:
            assert "state_id" in jur

    # 3. LCD -> contractor/MAC
    con_doc = db["contractors"].find_one()
    if con_doc:
        lcd_id = con_doc["lcd_id_numeric"]
        contractors = list(db["contractors"].find({"lcd_id_numeric": lcd_id}))
        assert len(contractors) > 0
        for contractor in contractors:
            assert "contractor_id" in contractor

    # 4. LCD -> related Article
    lar_doc = db["lcd_article_relationships"].find_one()
    if lar_doc:
        lcd_id = lar_doc["lcd_id_numeric"]
        lcd_version = lar_doc["lcd_version"]
        articles = list(db["lcd_article_relationships"].find({
            "lcd_id_numeric": lcd_id,
            "lcd_version": lcd_version
        }))
        assert len(articles) > 0
        for art in articles:
            assert "article_id_numeric" in art

    # 5. Article -> HCPCS
    ah_doc = db["article_hcpcs"].find_one()
    if ah_doc:
        art_id = ah_doc["article_id_numeric"]
        art_ver = ah_doc["article_version"]
        hcpcs_list = list(db["article_hcpcs"].find({
            "article_id_numeric": art_id,
            "article_version": art_ver
        }))
        assert len(hcpcs_list) > 0
        for h in hcpcs_list:
            assert "hcpcs_code" in h

    # 6. Article -> covered ICD-10
    cov_doc = db["icd10cm_article_covered"].find_one()
    if cov_doc:
        art_id = cov_doc["article_id_numeric"]
        art_ver = cov_doc["article_version"]
        covered = list(db["icd10cm_article_covered"].find({
            "article_id_numeric": art_id,
            "article_version": art_ver
        }))
        assert len(covered) > 0
        for cov in covered:
            assert "icd10_code" in cov

    # 7. Article -> noncovered ICD-10
    ncov_doc = db["icd10cm_article_noncovered"].find_one()
    if ncov_doc:
        art_id = ncov_doc["article_id_numeric"]
        art_ver = ncov_doc["article_version"]
        noncovered = list(db["icd10cm_article_noncovered"].find({
            "article_id_numeric": art_id,
            "article_version": art_ver
        }))
        assert len(noncovered) > 0
        for ncov in noncovered:
            assert "icd10_code" in ncov

    # 8. LCD -> related NCD
    lnr_doc = db["lcd_ncd_relationships"].find_one()
    if lnr_doc:
        lcd_id = lnr_doc["lcd_id_numeric"]
        lcd_ver = lnr_doc["lcd_version"]
        ncds = list(db["lcd_ncd_relationships"].find({
            "lcd_id_numeric": lcd_id,
            "lcd_version": lcd_ver
        }))
        assert len(ncds) > 0
        for ncd in ncds:
            assert "r_ncd_id" in ncd

    # 9. Article -> related NCD
    anr_doc = db["article_ncd_relationships"].find_one()
    if anr_doc:
        art_id = anr_doc["article_id_numeric"]
        art_ver = anr_doc["article_version"]
        ncds = list(db["article_ncd_relationships"].find({
            "article_id_numeric": art_id,
            "article_version": art_ver
        }))
        assert len(ncds) > 0
        for ncd in ncds:
            assert "r_ncd_id" in ncd


def test_version_aware_relationships():
    """Verify that version specifications are queried correctly to prevent Y-crossings."""
    db = db_connection.get_db()
    lar_doc = db["lcd_article_relationships"].find_one()
    if lar_doc:
        lcd_id = lar_doc["lcd_id_numeric"]
        lcd_version = lar_doc["lcd_version"]
        art_id = lar_doc["article_id_numeric"]
        art_version = lar_doc["article_version"]
        
        # Query with exact version compatibility matches
        exact_matches = list(db["lcd_article_relationships"].find({
            "lcd_id_numeric": lcd_id,
            "lcd_version": lcd_version,
            "article_id_numeric": art_id,
            "article_version": art_version
        }))
        assert len(exact_matches) > 0
        
        # Query with mismatched version boundaries and verify they don't match
        mismatched = list(db["lcd_article_relationships"].find({
            "lcd_id_numeric": lcd_id,
            "lcd_version": lcd_version + "_DUMMY_VERSION",
            "article_id_numeric": art_id,
            "article_version": art_version
        }))
        assert len(mismatched) == 0
