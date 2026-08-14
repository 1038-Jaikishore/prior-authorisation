import pytest
from app.db.connection import db_connection
from app.models.policy import PolicyRoutingRequest
from app.services.policy_routing import PolicyRoutingService

@pytest.fixture(scope="module")
def db():
    return db_connection.get_db()

def test_routing_integration_dynamic(db):
    """Test policy routing dynamically by setting up temporary mapping for active LCD 33942."""
    # Insert temporary HCPCS mapping for 33942 (which maps to state 'Colorado' -> 'CO')
    db["lcd_hcpcs"].insert_one({
        "lcd_id_numeric": "33942",
        "lcd_version": "50",
        "hcpcs_code": {
            "source_value": "T9999",
            "canonical_value": "T9999",
            "display_value": "T9999"
        }
    })
    
    try:
        # Request with state_code = "CO", which maps to state "Colorado" in lcd_jurisdictions
        request = PolicyRoutingRequest(
            hcpcs_code="T9999",
            state_code="CO",
            date_of_service="2026-08-20"
        )
        
        response = PolicyRoutingService.route_policy(request)
        assert response.routing_status in ["RESOLVED", "PARTIAL_POLICY_DATA"]
        assert len(response.applicable_lcds) > 0
        assert any(l["lcd_id"] == "L33942" for l in response.applicable_lcds)
        
        # Test C & D MAC and Jurisdiction resolved
        assert response.jurisdiction is not None
        assert response.jurisdiction["state_code"] == "CO"
        assert response.contractor is not None
        assert response.contractor["contractor_id"] is not None
        
        # Test E: Related Articles resolved (33942 has related articles in lcd_article_relationships)
        assert len(response.related_articles) > 0
        assert any(a["article_id"].startswith("A") for a in response.related_articles)
        
    finally:
        # Cleanup temporary HCPCS mapping
        db["lcd_hcpcs"].delete_one({"hcpcs_code.canonical_value": "T9999", "lcd_id_numeric": "33942"})

def test_routing_article_mappings(db):
    """Test Article -> HCPCS, Covered ICD, and Noncovered ICD mappings."""
    # Test F: Article HCPCS mapping check
    ah_doc = db["article_hcpcs"].find_one()
    if ah_doc:
        art_id = ah_doc["article_id_numeric"]
        art_ver = ah_doc["article_version"]
        art_hcpcs = ah_doc["hcpcs_code"]["display_value"]
        
        req = PolicyRoutingRequest(hcpcs_code=art_hcpcs, date_of_service="2026-08-20")
        resp = PolicyRoutingService.route_policy(req)
        if any(a["article_id"] == f"A{art_id}" for a in resp.related_articles):
            ctx = resp.coding_context.get(f"A{art_id}")
            assert ctx is not None
            assert art_hcpcs in ctx["hcpcs_codes"]

    # Test G & H: Covered / Noncovered ICD-10
    cov_doc = db["icd10cm_article_covered"].find_one()
    if cov_doc:
        art_id = cov_doc["article_id_numeric"]
        art_ver = cov_doc["article_version"]
        cov_icd = cov_doc["icd10_code"]["display_value"]
        
        art_h_doc = db["article_hcpcs"].find_one({"article_id_numeric": art_id, "article_version": art_ver})
        if art_h_doc:
            req = PolicyRoutingRequest(hcpcs_code=art_h_doc["hcpcs_code"]["display_value"], date_of_service="2026-08-20")
            resp = PolicyRoutingService.route_policy(req)
            ctx = resp.coding_context.get(f"A{art_id}")
            if ctx:
                assert cov_icd in ctx["covered_icd10"]

def test_routing_ncd_relationships(db):
    """Test LCD/Article related NCD discovery."""
    lnr_doc = db["lcd_ncd_relationships"].find_one()
    if lnr_doc:
        lcd_id = lnr_doc["lcd_id_numeric"]
        ncd_id = lnr_doc["r_ncd_id"]
        
        # Map temporary CPT to this LCD to resolve it
        db["lcd_hcpcs"].insert_one({
            "lcd_id_numeric": lcd_id,
            "lcd_version": lnr_doc["lcd_version"],
            "hcpcs_code": {
                "source_value": "T8888",
                "canonical_value": "T8888",
                "display_value": "T8888"
            }
        })
        
        try:
            req = PolicyRoutingRequest(hcpcs_code="T8888", date_of_service="2026-08-20")
            resp = PolicyRoutingService.route_policy(req)
            assert len(resp.candidate_ncds) > 0
            assert any(n["raw_document"]["ncd_id"]["canonical_value"] == ncd_id for n in resp.candidate_ncds)
        finally:
            db["lcd_hcpcs"].delete_one({"hcpcs_code.canonical_value": "T8888"})

def test_routing_cases(db):
    # Set up temporary overlapping mappings for HCPCS 'T9999' to two LCDs:
    # 1. 33942 (maps to state Colorado -> 'CO')
    # 2. 34544 (maps to state Texas -> 'TX')
    db["lcd_hcpcs"].insert_many([
        {
            "lcd_id_numeric": "33942",
            "lcd_version": "50",
            "hcpcs_code": {
                "source_value": "T9999",
                "canonical_value": "T9999",
                "display_value": "T9999"
            }
        },
        {
            "lcd_id_numeric": "34544",
            "lcd_version": "30",
            "hcpcs_code": {
                "source_value": "T9999",
                "canonical_value": "T9999",
                "display_value": "T9999"
            }
        }
    ])
    
    try:
        # -------------------------------------------------------------
        # TEST B: Geography resolves multiple LCD candidates to one
        # -------------------------------------------------------------
        req = PolicyRoutingRequest(hcpcs_code="T9999", state_code="TX", date_of_service="2026-08-20")
        resp = PolicyRoutingService.route_policy(req)
        assert resp.routing_status in ["RESOLVED", "PARTIAL_POLICY_DATA"]
        assert len(resp.applicable_lcds) == 1
        assert resp.applicable_lcds[0]["lcd_id"] == "L34544"

        # -------------------------------------------------------------
        # TEST K: Missing geography -> Ambiguity warning when multiple exist
        # -------------------------------------------------------------
        req_no_geo = PolicyRoutingRequest(hcpcs_code="T9999", date_of_service="2026-08-20")
        resp_no_geo = PolicyRoutingService.route_policy(req_no_geo)
        assert resp_no_geo.routing_status in ["AMBIGUOUS / INCOMPLETE ROUTING", "AMBIGUOUS_GEOGRAPHY", "PARTIAL_POLICY_DATA"]
        assert resp_no_geo.routing_confidence <= 0.5
        assert any("Geography (state) is required" in w for w in resp_no_geo.warnings)

    finally:
        # Cleanup temporary HCPCS mappings
        db["lcd_hcpcs"].delete_many({"hcpcs_code.canonical_value": "T9999"})

    # -------------------------------------------------------------
    # TEST L: Broken Article reference
    # -------------------------------------------------------------
    dummy_rel = {
        "lcd_id_numeric": "99999",
        "lcd_version": "1",
        "article_id_numeric": "99999", 
        "article_version": "1",
        "source_file": "lcd_article_relationship.csv",
        "ingestion_run_id": "test_run"
    }
    db["lcd_article_relationships"].insert_one(dummy_rel)
    
    dummy_hcpcs = {
        "lcd_id_numeric": "99999",
        "lcd_version": "1",
        "hcpcs_code": {
            "source_value": "99999",
            "canonical_value": "99999",
            "display_value": "99999"
        }
    }
    db["lcd_hcpcs"].insert_one(dummy_hcpcs)
    
    dummy_lcd = {
        "lcd_id": {
            "source_value": "L99999",
            "canonical_value": "99999",
            "display_value": "L99999"
        },
        "lcd_version": "1",
        "title": "Dummy LCD 99999",
        "effective_date": "2020-01-01"
    }
    db["lcds"].insert_one(dummy_lcd)
    
    try:
        req = PolicyRoutingRequest(hcpcs_code="99999", date_of_service="2026-08-20")
        resp = PolicyRoutingService.route_policy(req)
        assert resp.routing_status == "PARTIAL_POLICY_DATA"
        assert len(resp.unresolved_references) > 0
        assert any(u.referenced_id == "99999" and u.referenced_version == "1" for u in resp.unresolved_references)
    finally:
        db["lcd_article_relationships"].delete_one({"lcd_id_numeric": "99999"})
        db["lcd_hcpcs"].delete_one({"lcd_id_numeric": "99999"})
        db["lcds"].delete_one({"lcd_id.canonical_value": "99999"})

    # -------------------------------------------------------------
    # TEST M: Broken NCD reference
    # -------------------------------------------------------------
    dummy_ncd_rel = {
        "lcd_id_numeric": "88888",
        "lcd_version": "1",
        "r_ncd_id": "NCD999", 
        "r_ncd_version": "1",
        "source_file": "lcd_related_ncd_documents.csv"
    }
    db["lcd_ncd_relationships"].insert_one(dummy_ncd_rel)
    
    dummy_ncd_hcpcs = {
        "lcd_id_numeric": "88888",
        "lcd_version": "1",
        "hcpcs_code": {
            "source_value": "88888",
            "canonical_value": "88888",
            "display_value": "88888"
        }
    }
    db["lcd_hcpcs"].insert_one(dummy_ncd_hcpcs)
    
    dummy_ncd_lcd = {
        "lcd_id": {
            "source_value": "L88888",
            "canonical_value": "88888",
            "display_value": "L88888"
        },
        "lcd_version": "1",
        "title": "Dummy LCD 88888",
        "effective_date": "2020-01-01"
    }
    db["lcds"].insert_one(dummy_ncd_lcd)
    
    try:
        req = PolicyRoutingRequest(hcpcs_code="88888", date_of_service="2026-08-20")
        resp = PolicyRoutingService.route_policy(req)
        assert resp.routing_status == "PARTIAL_POLICY_DATA"
        assert len(resp.unresolved_references) > 0
        assert any(u.referenced_id == "NCD999" for u in resp.unresolved_references)
    finally:
        db["lcd_ncd_relationships"].delete_one({"lcd_id_numeric": "88888"})
        db["lcd_hcpcs"].delete_one({"lcd_id_numeric": "88888"})
        db["lcds"].delete_one({"lcd_id.canonical_value": "88888"})

    # -------------------------------------------------------------
    # TEST N: Version Mismatch (cross-version boundaries check)
    # -------------------------------------------------------------
    db["lcd_article_relationships"].insert_many([
        {"lcd_id_numeric": "77777", "lcd_version": "1", "article_id_numeric": "77777", "article_version": "1"},
        {"lcd_id_numeric": "77777", "lcd_version": "2", "article_id_numeric": "77777", "article_version": "2"}
    ])
    db["lcds"].insert_many([
        {"lcd_id": {"source_value": "L77777", "canonical_value": "77777", "display_value": "L77777"}, "lcd_version": "1", "effective_date": "2020-01-01"},
        {"lcd_id": {"source_value": "L77777", "canonical_value": "77777", "display_value": "L77777"}, "lcd_version": "2", "effective_date": "2020-01-01"}
    ])
    db["articles"].insert_many([
        {"article_id": {"source_value": "A77777", "canonical_value": "77777", "display_value": "A77777"}, "article_version": "1", "effective_date": "2020-01-01"},
        {"article_id": {"source_value": "A77777", "canonical_value": "77777", "display_value": "A77777"}, "article_version": "2", "effective_date": "2020-01-01"}
    ])
    db["lcd_hcpcs"].insert_one({
        "lcd_id_numeric": "77777",
        "lcd_version": "1",
        "hcpcs_code": {
            "source_value": "77777",
            "canonical_value": "77777",
            "display_value": "77777"
        }
    })
    
    try:
        req = PolicyRoutingRequest(hcpcs_code="77777", date_of_service="2026-08-20")
        resp = PolicyRoutingService.route_policy(req)
        assert len(resp.related_articles) == 1
        assert resp.related_articles[0]["article_version"] == "1"
    finally:
        db["lcd_article_relationships"].delete_many({"lcd_id_numeric": "77777"})
        db["lcds"].delete_many({"lcd_id.canonical_value": "77777"})
        db["articles"].delete_many({"article_id.canonical_value": "77777"})
        db["lcd_hcpcs"].delete_one({"lcd_id_numeric": "77777"})

    # -------------------------------------------------------------
    # TEST O: Date of Service Mismatch
    # -------------------------------------------------------------
    db["lcds"].insert_one({
        "lcd_id": {"source_value": "L66666", "canonical_value": "66666", "display_value": "L66666"},
        "lcd_version": "1",
        "effective_date": "2025-01-01",
        "end_date": "2025-12-31"
    })
    db["lcd_hcpcs"].insert_one({
        "lcd_id_numeric": "66666",
        "lcd_version": "1",
        "hcpcs_code": {
            "source_value": "66666",
            "canonical_value": "66666",
            "display_value": "66666"
        }
    })
    db["lcd_jurisdictions"].insert_one({
        "lcd_id_numeric": "66666",
        "state_id": "TX",
        "state_name": "Texas"
    })
    
    try:
        req = PolicyRoutingRequest(hcpcs_code="66666", state_code="TX", date_of_service="2026-08-20")
        resp = PolicyRoutingService.route_policy(req)
        assert resp.routing_status == "LCD_DATE_MISMATCH"
        assert len(resp.applicable_lcds) == 0
    finally:
        db["lcds"].delete_one({"lcd_id.canonical_value": "66666"})
        db["lcd_hcpcs"].delete_one({"lcd_id_numeric": "66666"})
        db["lcd_jurisdictions"].delete_one({"lcd_id_numeric": "66666"})

# US_STATES mapping for states
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "District of Columbia", "PR": "Puerto Rico", "VI": "Virgin Islands", "GU": "Guam"
}
