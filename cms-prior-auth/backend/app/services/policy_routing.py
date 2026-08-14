import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from app.db.connection import db_connection
from app.core.normalize import (
    normalize_hcpcs_code,
    normalize_icd10_code,
    normalize_icd10_code_numeric,
    normalize_modifier_code,
    normalize_revenue_code,
    normalize_bill_type_code,
    normalize_date,
    build_provenance_field
)
from app.models.policy import PolicyRoutingRequest, PolicyRoutingResponse, RoutingTraceStep, UnresolvedReference

# Mapping for US State Codes to full names
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

class PolicyRoutingService:
    @staticmethod
    def route_policy(request: PolicyRoutingRequest) -> PolicyRoutingResponse:
        db = db_connection.get_db()
        trace: List[RoutingTraceStep] = []
        warnings: List[str] = []
        unresolved_references: List[UnresolvedReference] = []
        step_counter = 1
        
        def add_trace(action: str, input_val: Any, result_val: Any):
            nonlocal step_counter
            trace.append(RoutingTraceStep(step=step_counter, action=action, input=input_val, result=result_val))
            step_counter += 1

        # -------------------------------------------------------------
        # STEP 1: Normalize Inputs
        # -------------------------------------------------------------
        raw_hcpcs = request.hcpcs_code
        norm_hcpcs = normalize_hcpcs_code(raw_hcpcs)
        hcpcs_prov = build_provenance_field(raw_hcpcs, norm_hcpcs, raw_hcpcs)
        add_trace("NORMALIZE_HCPCS", raw_hcpcs, hcpcs_prov)
        
        norm_diags = []
        for d in request.diagnosis_codes:
            d_norm = normalize_icd10_code_numeric(d)
            d_disp = normalize_icd10_code(d)
            norm_diags.append(build_provenance_field(d, d_norm, d_disp))
        add_trace("NORMALIZE_DIAGNOSES", request.diagnosis_codes, norm_diags)
        
        norm_pcs = []
        for p in request.icd10_pcs_codes:
            p_norm = normalize_icd10_code_numeric(p)
            norm_pcs.append(build_provenance_field(p, p_norm, p))
        add_trace("NORMALIZE_PCS_CODES", request.icd10_pcs_codes, norm_pcs)
        
        norm_mods = []
        for m in request.modifiers:
            m_norm = normalize_modifier_code(m)
            norm_mods.append(build_provenance_field(m, m_norm, m))
        add_trace("NORMALIZE_MODIFIERS", request.modifiers, norm_mods)
        
        norm_rev = build_provenance_field(request.revenue_code, normalize_revenue_code(request.revenue_code), request.revenue_code) if request.revenue_code else None
        add_trace("NORMALIZE_REVENUE_CODE", request.revenue_code, norm_rev)
        
        norm_bill = build_provenance_field(request.bill_type_code, normalize_bill_type_code(request.bill_type_code), request.bill_type_code) if request.bill_type_code else None
        add_trace("NORMALIZE_BILL_TYPE_CODE", request.bill_type_code, norm_bill)
        
        # State normalization
        state_name = request.state
        state_code = request.state_code
        
        if state_code:
            state_code = state_code.strip().upper()
            if not state_name and state_code in US_STATES:
                state_name = US_STATES[state_code]
        elif state_name:
            # Look up code by full name
            state_name_clean = state_name.strip().upper()
            for code, name in US_STATES.items():
                if name.upper() == state_name_clean:
                    state_code = code
                    state_name = name
                    break
        
        geo_prov = {
            "state": state_name,
            "state_code": state_code,
            "zip_code": request.zip_code
        }
        add_trace("NORMALIZE_GEOGRAPHY", {"state": request.state, "state_code": request.state_code, "zip_code": request.zip_code}, geo_prov)
        
        date_of_service = normalize_date(request.date_of_service)
        add_trace("NORMALIZE_DATE", request.date_of_service, date_of_service)
        
        normalized_request = {
            "hcpcs_code": hcpcs_prov,
            "diagnosis_codes": norm_diags,
            "icd10_pcs_codes": norm_pcs,
            "modifiers": norm_mods,
            "revenue_code": norm_rev,
            "bill_type_code": norm_bill,
            "geography": geo_prov,
            "date_of_service": date_of_service
        }

        # -------------------------------------------------------------
        # STEP 2: Basic Code Validation
        # -------------------------------------------------------------
        # Check HCPCS syntax and local existence
        hcpcs_pattern = re.compile(r'^[A-Z0-9]{4,5}$')
        hcpcs_valid_syntax = bool(hcpcs_pattern.match(norm_hcpcs))
        
        # Check if code is present in mappings
        in_mappings = db["article_hcpcs"].count_documents({"hcpcs_code.canonical_value": norm_hcpcs}) > 0 or \
                      db["lcd_hcpcs"].count_documents({"hcpcs_code.canonical_value": norm_hcpcs}) > 0
                      
        if not hcpcs_valid_syntax:
            warnings.append("INVALID HCPCS CODE syntax")
            add_trace("VALIDATE_HCPCS", norm_hcpcs, {"valid": False, "reason": "Syntax invalid (must be 4-5 chars alphanumeric)"})
        elif not in_mappings:
            warnings.append("NO HCPCS POLICY MAPPING FOUND IN CURRENT CMS DATASET")
            add_trace("VALIDATE_HCPCS", norm_hcpcs, {"valid": True, "exists_in_cms_dataset": False, "reason": "No policies mapped to this HCPCS code"})
        else:
            add_trace("VALIDATE_HCPCS", norm_hcpcs, {"valid": True, "exists_in_cms_dataset": True})

        # Validate Diagnosis codes format
        diag_pattern = re.compile(r'^[A-Z]\d[A-Z0-9]{1,5}$')
        for d in norm_diags:
            if not diag_pattern.match(d["canonical_value"]):
                warnings.append(f"Diagnosis code {d['source_value']} has invalid syntax")
                
        # Validate Modifiers
        mod_pattern = re.compile(r'^[A-Z0-9]{1,2}$')
        for m in norm_mods:
            if not mod_pattern.match(m["canonical_value"]):
                warnings.append(f"Modifier {m['source_value']} has invalid syntax")

        # -------------------------------------------------------------
        # STEP 3: HCPCS -> Candidate Discovery
        # -------------------------------------------------------------
        candidate_lcd_ids = []
        candidate_article_ids = []
        
        # Query LCD HCPCS
        lcd_h_docs = list(db["lcd_hcpcs"].find({"hcpcs_code.canonical_value": norm_hcpcs}))
        for doc in lcd_h_docs:
            if doc.get("lcd_id_numeric") not in candidate_lcd_ids:
                candidate_lcd_ids.append(doc.get("lcd_id_numeric"))
                
        # Query Article HCPCS
        art_h_docs = list(db["article_hcpcs"].find({"article_id_numeric": {"$exists": True}, "hcpcs_code.canonical_value": norm_hcpcs}))
        for doc in art_h_docs:
            art_id = doc.get("article_id_numeric")
            if art_id not in candidate_article_ids:
                candidate_article_ids.append(art_id)
                
        add_trace("HCPCS_TO_CANDIDATES", norm_hcpcs, {"lcd_ids": candidate_lcd_ids, "article_ids": candidate_article_ids})

        # -------------------------------------------------------------
        # STEP 4: Resolve NCD Candidates
        # -------------------------------------------------------------
        candidate_ncd_ids = []
        ncd_relationships = []
        
        # Check LCD NCD links
        if candidate_lcd_ids:
            ln_docs = list(db["lcd_ncd_relationships"].find({"lcd_id_numeric": {"$in": candidate_lcd_ids}}))
            for doc in ln_docs:
                ncd_id = doc.get("r_ncd_id")
                if ncd_id and ncd_id not in candidate_ncd_ids:
                    candidate_ncd_ids.append(ncd_id)
                    ncd_relationships.append({
                        "ncd_id": ncd_id,
                        "relationship_source": f"LCD L{doc.get('lcd_id_numeric')}",
                        "source_file": "lcd_related_ncd_documents.csv"
                    })
                    
        # Check Article NCD links
        if candidate_article_ids:
            an_docs = list(db["article_ncd_relationships"].find({"article_id_numeric": {"$in": candidate_article_ids}}))
            for doc in an_docs:
                ncd_id = doc.get("r_ncd_id")
                if ncd_id and ncd_id not in candidate_ncd_ids:
                    candidate_ncd_ids.append(ncd_id)
                    ncd_relationships.append({
                        "ncd_id": ncd_id,
                        "relationship_source": f"Article A{doc.get('article_id_numeric')}",
                        "source_file": "article_related_ncd_documents_data.csv"
                    })
                    
        # Look up candidate NCD master records
        resolved_ncds = []
        applicable_ncds = []
        
        for ncd_id in candidate_ncd_ids:
            # Canonical key matching
            ncd_master = db["ncds"].find_one({"ncd_id.canonical_value": ncd_id})
            rel = next((r for r in ncd_relationships if r["ncd_id"] == ncd_id), {})
            
            if ncd_master:
                ncd_doc = {
                    "ncd_id": ncd_master["ncd_id"]["display_value"],
                    "version": ncd_master.get("document_version"),
                    "title": ncd_master.get("title"),
                    "status": "Active",
                    "effective_date": ncd_master.get("effective_date"),
                    "relationship_source": rel.get("relationship_source"),
                    "source_file": rel.get("source_file"),
                    "raw_document": ncd_master
                }
                resolved_ncds.append(ncd_doc)
                
                # Check date-of-service boundary
                eff_dt = ncd_doc["effective_date"]
                end_dt = ncd_master.get("effective_end_date")
                
                date_ok = True
                if eff_dt and date_of_service < eff_dt:
                    date_ok = False
                if end_dt and date_of_service > end_dt:
                    date_ok = False
                    
                if date_ok:
                    applicable_ncds.append(ncd_doc)
            else:
                # Broken reference
                unresolved_references.append(UnresolvedReference(
                    referenced_id=ncd_id,
                    relationship_source=rel.get("relationship_source", "Unknown mapping"),
                    source_file=rel.get("source_file"),
                    reason="NCD master record missing from MongoDB ncds collection."
                ))
                
        add_trace("RESOLVE_NCDS", candidate_ncd_ids, {"resolved": [n["ncd_id"] for n in resolved_ncds], "unresolved": [u.referenced_id for u in unresolved_references if u.reason.startswith("NCD")]})

        # Determine NCD Status
        if resolved_ncds:
            if len(resolved_ncds) == 1:
                ncd_status = "NCD_FOUND"
            else:
                ncd_status = "MULTIPLE_NCD_CANDIDATES"
        elif any(u.reason.startswith("NCD") for u in unresolved_references):
            ncd_status = "NCD_REFERENCE_UNRESOLVED"
        else:
            ncd_status = "NO_NCD_MAPPING"

        # -------------------------------------------------------------
        # STEP 5: Resolve Geography & Local Coverage Fallback
        # -------------------------------------------------------------
        resolved_jurisdiction = None
        resolved_contractor = None
        geographically_applicable_lcds = []
        
        # When local evaluation is needed (e.g. no controlling NCD exclusion overrides it)
        # We need geography to filter candidate LCDs
        if candidate_lcds_exist := len(candidate_lcd_ids) > 0:
            if not state_code:
                warnings.append("Geography (state) is required to resolve multiple local coverage candidates.")
                add_trace("RESOLVE_GEOGRAPHY", None, {"status": "AMBIGUOUS / INCOMPLETE ROUTING", "reason": "No state specified for candidate local coverage policies"})
            else:
                # Resolve state jurisdictions matching candidate LCDs
                lj_records = list(db["lcd_jurisdictions"].find({
                    "lcd_id_numeric": {"$in": candidate_lcd_ids},
                    "state_name": state_name
                }))
                
                geographically_applicable_lcds = list(set(r.get("lcd_id_numeric") for r in lj_records))
                
                # Fetch contractor MAC details for this state and these LCDs
                con_records = list(db["contractors"].find({
                    "lcd_id_numeric": {"$in": geographically_applicable_lcds}
                }))
                
                if con_records:
                    # Capture jurisdiction and contractor for trace
                    resolved_jurisdiction = {
                        "state_code": state_code,
                        "state_name": state_name,
                        "lcd_ids": geographically_applicable_lcds
                    }
                    resolved_contractor = {
                        "contractor_id": con_records[0].get("contractor_id"),
                        "contractor_name": con_records[0].get("contractor_name"),
                        "contractor_type": con_records[0].get("contractor_type")
                    }
                add_trace("RESOLVE_GEOGRAPHY", {"state_code": state_code}, {"applicable_lcds": geographically_applicable_lcds, "jurisdiction": resolved_jurisdiction, "contractor": resolved_contractor})

        # -------------------------------------------------------------
        # STEP 6: Filter Applicable LCDs
        # -------------------------------------------------------------
        resolved_lcds = []
        applicable_lcds = []
        lcd_warnings = []
        
        for lcd_id in candidate_lcd_ids:
            # Query LCD master
            lcd_master = db["lcds"].find_one({"lcd_id.canonical_value": lcd_id})
            
            if lcd_master:
                lcd_doc = {
                    "lcd_id": lcd_master["lcd_id"]["display_value"],
                    "version": lcd_master.get("lcd_version"),
                    "title": lcd_master.get("title"),
                    "status": lcd_master.get("status"),
                    "effective_date": lcd_master.get("effective_date"),
                    "termination_date": lcd_master.get("end_date") or lcd_master.get("termination_date"),
                    "raw_document": lcd_master
                }
                resolved_lcds.append(lcd_doc)
                
                # Date boundary checks
                date_ok = True
                eff_dt = lcd_doc["effective_date"]
                term_dt = lcd_doc["termination_date"]
                
                if eff_dt and date_of_service < eff_dt:
                    date_ok = False
                    lcd_warnings.append(f"LCD {lcd_doc['lcd_id']} has effective date {eff_dt} after service date {date_of_service}")
                if term_dt and date_of_service > term_dt:
                    date_ok = False
                    lcd_warnings.append(f"LCD {lcd_doc['lcd_id']} has termination date {term_dt} before service date {date_of_service}")
                    
                # Geography boundary check
                geo_ok = True
                if state_code and lcd_id not in geographically_applicable_lcds:
                    geo_ok = False
                    lcd_warnings.append(f"LCD {lcd_doc['lcd_id']} is not geographically applicable in {state_code}")
                    
                if date_ok and geo_ok:
                    applicable_lcds.append(lcd_doc)
            else:
                # Broken reference
                unresolved_references.append(UnresolvedReference(
                    referenced_id=lcd_id,
                    relationship_source=f"HCPCS lookup: {norm_hcpcs}",
                    source_file="CMS_LCD_HCPCS_All_LCDs (1).csv",
                    reason="LCD master record missing from MongoDB lcds collection."
                ))
                
        add_trace("FILTER_LCDS", candidate_lcd_ids, {"resolved": [l["lcd_id"] for l in resolved_lcds], "applicable": [l["lcd_id"] for l in applicable_lcds], "warnings": lcd_warnings})

        # Determine LCD Status
        if not candidate_lcd_ids:
            lcd_status = "NO_LOCAL_LCD_MAPPING"
        elif any(u.reason.startswith("LCD") for u in unresolved_references):
            lcd_status = "LCD_REFERENCE_UNRESOLVED"
        elif not state_code:
            lcd_status = "AMBIGUOUS_GEOGRAPHY"
        elif not applicable_lcds:
            if any(l for l in resolved_lcds if date_of_service < l["effective_date"] or (l["termination_date"] and date_of_service > l["termination_date"])):
                lcd_status = "LCD_DATE_MISMATCH"
            else:
                lcd_status = "LCD_GEOGRAPHY_MISMATCH"
        elif len(applicable_lcds) == 1:
            lcd_status = "APPLICABLE_LCD"
        else:
            lcd_status = "MULTIPLE_LCD_CANDIDATES"

        # -------------------------------------------------------------
        # STEP 7: Resolve LCD -> Article Mappings
        # -------------------------------------------------------------
        related_articles = []
        
        # Resolve articles for geographically applicable/active LCDs
        if applicable_lcds:
            active_lcd_ids = [l["raw_document"]["lcd_id"]["canonical_value"] for l in applicable_lcds]
            active_lcd_versions = {l["raw_document"]["lcd_id"]["canonical_value"]: l["version"] for l in applicable_lcds}
            
            lar_docs = list(db["lcd_article_relationships"].find({
                "lcd_id_numeric": {"$in": active_lcd_ids}
            }))
            
            for rel in lar_docs:
                rel_lcd_id = rel.get("lcd_id_numeric")
                rel_lcd_version = rel.get("lcd_version")
                
                # Check version compatibility: prevent crosses!
                expected_version = active_lcd_versions.get(rel_lcd_id)
                if expected_version and rel_lcd_version != expected_version:
                    continue
                    
                art_id = rel.get("article_id_numeric")
                art_ver = rel.get("article_version")
                
                # Look up Article master
                art_master = db["articles"].find_one({
                    "article_id.canonical_value": art_id,
                    "article_version": art_ver
                })
                
                if art_master:
                    art_doc = {
                        "article_id": art_master["article_id"]["display_value"],
                        "article_version": art_ver,
                        "article_type": art_master.get("article_type"),
                        "title": art_master.get("title"),
                        "effective_date": art_master.get("effective_date"),
                        "status": "Active",
                        "relationship_source": f"LCD L{rel_lcd_id} Relationship",
                        "raw_document": art_master
                    }
                    if art_doc not in related_articles:
                        related_articles.append(art_doc)
                else:
                    unresolved_references.append(UnresolvedReference(
                        referenced_id=art_id,
                        referenced_version=art_ver,
                        relationship_source=f"LCD L{rel_lcd_id} V{rel_lcd_version} mapping",
                        source_file="lcd_article_relationship.csv",
                        reason="Article master record missing from MongoDB articles collection."
                    ))
                    
        add_trace("RESOLVE_ARTICLES", [l["lcd_id"] for l in applicable_lcds], {"articles": [a["article_id"] for a in related_articles], "unresolved": [u.referenced_id for u in unresolved_references if u.reason.startswith("Article")]})

        # -------------------------------------------------------------
        # STEP 8: Gather Coding Context
        # -------------------------------------------------------------
        coding_context = {}
        
        def safe_extract_display(items, field_name) -> List[str]:
            res = []
            for item in items:
                val = item.get(field_name)
                if isinstance(val, dict):
                    disp = val.get("display_value")
                    if disp:
                        res.append(disp)
                elif isinstance(val, str) and val:
                    res.append(val)
            return list(set(res))  # Deduplicate values
        
        if related_articles:
            art_ids = [a["raw_document"]["article_id"]["canonical_value"] for a in related_articles]
            art_versions = {a["raw_document"]["article_id"]["canonical_value"]: a["article_version"] for a in related_articles}
            
            for a_id in art_ids:
                a_ver = art_versions[a_id]
                disp_id = f"A{a_id}"
                
                # Retrieve HCPCS mapping
                a_hcpcs = list(db["article_hcpcs"].find({"article_id_numeric": a_id, "article_version": a_ver}))
                hcpcs_codes = safe_extract_display(a_hcpcs, "hcpcs_code")
                
                # Retrieve Covered ICD-10 codes (By indexed keys)
                covered_cursor = db["icd10cm_article_covered"].find({"article_id_numeric": a_id, "article_version": a_ver})
                covered_icd = safe_extract_display(covered_cursor, "icd10_code")
                
                # Retrieve Noncovered ICD-10 codes (By indexed keys)
                noncovered_cursor = db["icd10cm_article_noncovered"].find({"article_id_numeric": a_id, "article_version": a_ver})
                noncovered_icd = safe_extract_display(noncovered_cursor, "icd10_code")
                
                # Retrieve Modifiers
                modifiers_cursor = db["article_modifiers"].find({"article_id_numeric": a_id, "article_version": a_ver})
                modifier_codes = safe_extract_display(modifiers_cursor, "modifier_code")
                
                # Retrieve Bill Codes
                bill_cursor = db["bill_codes"].find({"article_id_numeric": a_id, "article_version": a_ver})
                bill_codes = safe_extract_display(bill_cursor, "bill_type_code")
                
                # Retrieve Jurisdictions
                jur_cursor = db["article_jurisdictions"].find({"article_id_numeric": a_id, "article_version": a_ver})
                jurisdictions = [j.get("state_name") for j in jur_cursor if j.get("state_name")]
                
                coding_context[disp_id] = {
                    "hcpcs_codes": hcpcs_codes,
                    "covered_icd10": covered_icd,
                    "noncovered_icd10": noncovered_icd,
                    "modifiers": modifier_codes,
                    "bill_codes": bill_codes,
                    "jurisdictions": jurisdictions
                }
            add_trace("GATHER_CODING_CONTEXT", art_ids, {k: {"hcpcs_count": len(v["hcpcs_codes"]), "covered_icd_count": len(v["covered_icd10"])} for k, v in coding_context.items()})

        # -------------------------------------------------------------
        # STEP 9: Determine Final Routing Confidence & Status
        # -------------------------------------------------------------
        # Set overall routing status
        if unresolved_references:
            routing_status = "PARTIAL_POLICY_DATA"
        elif ncd_status == "NCD_FOUND":
            routing_status = "RESOLVED"
        elif lcd_status == "APPLICABLE_LCD":
            routing_status = "RESOLVED"
        elif lcd_status == "AMBIGUOUS_GEOGRAPHY":
            routing_status = "AMBIGUOUS / INCOMPLETE ROUTING"
        elif lcd_status == "NO_LOCAL_LCD_MAPPING" and ncd_status == "NO_NCD_MAPPING":
            routing_status = "NO_POLICY_FOUND"
        else:
            routing_status = lcd_status

        # Confidence calculation
        confidence = 1.0
        
        if routing_status == "RESOLVED":
            confidence = 1.0
        elif routing_status == "MULTIPLE_LCD_CANDIDATES":
            confidence = 0.5
            warnings.append("Multiple local coverage policies matched. Add provider facility or geography specificity to narrow down.")
        elif routing_status == "AMBIGUOUS / INCOMPLETE ROUTING":
            confidence = 0.2
        elif routing_status == "PARTIAL_POLICY_DATA":
            confidence = 0.6
            warnings.append("Some relationship references point to master documents missing from the database.")
        elif routing_status == "NO_POLICY_FOUND":
            confidence = 1.0
            
        # Deduct confidence for unresolved references
        if unresolved_references:
            confidence = max(0.1, confidence - 0.3)
            
        # Structure final response
        return PolicyRoutingResponse(
            routing_status=routing_status,
            normalized_request=normalized_request,
            candidate_ncds=resolved_ncds,
            applicable_ncds=applicable_ncds,
            candidate_lcds=resolved_lcds,
            applicable_lcds=applicable_lcds,
            related_articles=related_articles,
            jurisdiction=resolved_jurisdiction,
            contractor=resolved_contractor,
            coding_context=coding_context,
            unresolved_references=unresolved_references,
            warnings=warnings,
            routing_confidence=confidence,
            routing_trace=trace
        )
