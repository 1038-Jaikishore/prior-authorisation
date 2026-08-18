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
from app.services.cms_api_service import CMSApiService
from app.models.policy import PolicyRoutingRequest, PolicyRoutingResponse, RoutingTraceStep, UnresolvedReference
from app.services.policy_ingestion import PolicyIngestionService

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
        hcpcs_pattern = re.compile(r'^[A-Z0-9]{4,5}$')
        hcpcs_valid_syntax = bool(hcpcs_pattern.match(norm_hcpcs))
        if not hcpcs_valid_syntax:
            warnings.append("INVALID HCPCS CODE syntax")
            add_trace("VALIDATE_HCPCS", norm_hcpcs, {"valid": False, "reason": "Syntax invalid (must be 4-5 chars alphanumeric)"})
        else:
            add_trace("VALIDATE_HCPCS", norm_hcpcs, {"valid": True})

        # -------------------------------------------------------------
        # STEP 3: HCPCS to Article via MongoDB
        # -------------------------------------------------------------
        candidate_article_ids = []
        if norm_hcpcs:
            art_cursor = db["article_hcpcs"].find({"hcpcs_code.canonical_value": norm_hcpcs})
            for a in art_cursor:
                aid = a.get("article_id_numeric")
                if aid:
                    aid = str(aid).strip()
                    if aid and aid != "None" and any(c.isdigit() for c in aid) and aid not in candidate_article_ids:
                        candidate_article_ids.append(aid)
                        
        add_trace("HCPCS_TO_ARTICLE_DB", norm_hcpcs, {"candidate_articles": candidate_article_ids})

        # -------------------------------------------------------------
        # STEP 4: Article to LCD & NCD via CMS API
        # -------------------------------------------------------------
        candidate_lcd_ids = []
        candidate_ncd_ids = []
        related_articles = []
        
        for aid in candidate_article_ids:
            # 4a. Validate Article Geography
            jur_data = CMSApiService.fetch_article_primary_jurisdiction(aid)
            
            patient_state_id = None
            if state_name:
                state_doc = db["article_jurisdictions"].find_one({"state_name": {"$regex": f"^{state_name}$", "$options": "i"}})
                if state_doc:
                    patient_state_id = str(state_doc.get("state_id"))

            jur_status = "JURISDICTION_UNRESOLVED"
            is_match = False
            
            if jur_data:
                for jur in jur_data:
                    jur_state_id = str(jur.get("state_id", ""))
                    if jur_state_id == patient_state_id:
                        is_match = True
                        jur_status = "PRIMARY_JURISDICTION_FOUND"
                        break
                if not is_match:
                    jur_status = "JURISDICTION_UNRESOLVED"
            else:
                jur_status = "PRIMARY_JURISDICTION_EMPTY"

            if not is_match:
                jur_match = None
                if patient_state_id:
                    jur_match = db["article_jurisdictions"].find_one({"article_id_numeric": aid, "state_id": patient_state_id})
                if not jur_match and state_name and state_name.upper() != "UNKNOWN":
                    jur_match = db["article_jurisdictions"].find_one({"article_id_numeric": aid, "state_name": re.compile(f"^{state_name}$", re.I)})
                
                if jur_match:
                    is_match = True
                    jur_status = "LOCAL_JURISDICTION_FALLBACK_USED"

            add_trace("RESOLVE_ARTICLE_GEOGRAPHY", aid, {"status": "SUCCESS" if is_match else "FAILED", "reason": jur_status})

            # 4b. CMS Article Document
            art_master = CMSApiService.fetch_article_document(aid)
            if art_master:
                art_master["article_id"] = {"canonical_value": aid, "display_value": f"A{aid}"}
                db["articles"].update_one({"article_id.canonical_value": aid}, {"$set": art_master}, upsert=True)
                
                adoc = {
                    "article_id": art_master.get("article_id", {}).get("display_value", f"A{aid}"),
                    "article_version": art_master.get("articleVersion") or art_master.get("article_version"),
                    "article_type": art_master.get("articleType") or art_master.get("article_type"),
                    "title": art_master.get("title"),
                    "effective_date": art_master.get("effectiveDate") or art_master.get("effective_date"),
                    "status": "Active",
                    "relationship_source": f"HCPCS {norm_hcpcs}",
                    "raw_document": art_master
                }
                if adoc not in related_articles:
                    related_articles.append(adoc)
            
            # 4b. CMS Relationship Lookup (LCD)
            art_lcd_links = CMSApiService.fetch_article_related_documents(aid)
            for link in art_lcd_links:
                lid_raw = link.get("r_lcd_id") or link.get("documentId")
                if lid_raw:
                    lid = ''.join(filter(str.isdigit, str(lid_raw)))
                    if lid and lid != "None" and lid not in candidate_lcd_ids:
                        candidate_lcd_ids.append(lid)
                        
            # 4c. CMS Relationship Lookup (NCD)
            art_ncd_links = CMSApiService.fetch_article_related_ncds(aid)
            for link in art_ncd_links:
                nid_raw = link.get("r_ncd_id") or link.get("ncdId")
                if nid_raw:
                    nid = ''.join(filter(str.isdigit, str(nid_raw)))
                    if nid and nid != "None" and nid not in candidate_ncd_ids:
                        candidate_ncd_ids.append(nid)

        add_trace("CMS_RELATIONSHIP_LOOKUP", candidate_article_ids, {"lcds_found": candidate_lcd_ids, "ncds_found": candidate_ncd_ids})

        # -------------------------------------------------------------
        # STEP 5: Validate LCD & NCD
        # -------------------------------------------------------------
        resolved_jurisdiction = None
        resolved_contractor = None
        geographically_applicable_lcds = []
        applicable_lcds = []
        resolved_lcds = []
        
        if candidate_lcd_ids:
            if not state_code:
                warnings.append("Geography (state) is required to resolve multiple local coverage candidates.")
                add_trace("RESOLVE_GEOGRAPHY", None, {"status": "AMBIGUOUS", "reason": "No state specified"})
            else:
                for lcd_id in candidate_lcd_ids:
                    # Validate: Geography Filtering
                    jur_data = CMSApiService.fetch_lcd_primary_jurisdiction(lcd_id)
                    con_data = CMSApiService.fetch_lcd_contractor(lcd_id)

                    # Determine patient's state_id from local DB
                    patient_state_id = None
                    if state_name and state_name.upper() != "UNKNOWN":
                        state_doc = db["lcd_jurisdictions"].find_one({"state_name": {"$regex": f"^{state_name}$", "$options": "i"}})
                        if state_doc:
                            patient_state_id = str(state_doc.get("state_id"))

                    jur_status = "JURISDICTION_UNRESOLVED"
                    is_match = False
                    
                    if not state_name or state_name.upper() == "UNKNOWN":
                        is_match = True
                        jur_status = "JURISDICTION_BYPASSED_UNKNOWN_STATE"
                    elif jur_data:
                        # Route using CMS API state_id as requested
                        for jur in jur_data:
                            jur_state_id = str(jur.get("state_id", ""))
                            if jur_state_id == patient_state_id:
                                is_match = True
                                jur_status = "PRIMARY_JURISDICTION_FOUND"
                                break
                        
                        if not is_match:
                            jur_status = "JURISDICTION_UNRESOLVED"
                    else:
                        jur_status = "PRIMARY_JURISDICTION_EMPTY"

                    # Fallback to local CMS-derived mapping if unresolved or empty
                    if not is_match:
                        jur_match = None
                        if patient_state_id:
                            jur_match = db["lcd_jurisdictions"].find_one({"lcd_id_numeric": lcd_id, "state_id": patient_state_id})
                        if not jur_match and state_name and state_name.upper() != "UNKNOWN":
                            jur_match = db["lcd_jurisdictions"].find_one({"lcd_id_numeric": lcd_id, "state_name": re.compile(f"^{state_name}$", re.I)})
                        
                        if jur_match:
                            is_match = True
                            jur_status = "LOCAL_JURISDICTION_FALLBACK_USED"

                    add_trace("RESOLVE_GEOGRAPHY", lcd_id, {"status": "SUCCESS" if is_match else "FAILED", "reason": jur_status})
                            
                    if is_match:
                        geographically_applicable_lcds.append(lcd_id)
                        if con_data:
                            resolved_contractor = {
                                "contractor_id": con_data[0].get("contractorNumber") or con_data[0].get("contractorId"),
                                "contractor_name": con_data[0].get("contractorName"),
                                "contractor_type": con_data[0].get("contractorType")
                            }
                            
                resolved_jurisdiction = {
                    "state_code": state_code,
                    "state_name": state_name,
                    "lcd_ids": geographically_applicable_lcds
                }
                
                # Fetch LCD Documents
                for lcd_id in geographically_applicable_lcds:
                    lcd_master = CMSApiService.fetch_lcd_document(lcd_id)
                    if lcd_master:
                        lcd_master["lcd_id"] = {"canonical_value": lcd_id, "display_value": f"L{lcd_id}"}
                        db["lcds"].update_one({"lcd_id.canonical_value": lcd_id}, {"$set": lcd_master}, upsert=True)
                        
                        # Check for explicit HCPCS/Diagnosis exclusions/inclusions
                        lcd_hcpcs = []
                        if hasattr(CMSApiService, "fetch_lcd_hcpcs"):
                            try:
                                lcd_hcpcs = CMSApiService.fetch_lcd_hcpcs(lcd_id)
                            except Exception:
                                pass
                        
                        is_applicable = True
                        if lcd_hcpcs:
                            hcpcs_list = [str(h.get("hcpcs_code")).strip() for h in lcd_hcpcs if h.get("hcpcs_code")]
                            if hcpcs_list and norm_hcpcs not in hcpcs_list:
                                is_applicable = False
                                warnings.append(f"LCD L{lcd_id} does not explicitly cover HCPCS {norm_hcpcs}. Found {len(hcpcs_list)} other codes.")
                        
                        if is_applicable:
                            lcd_doc = {
                                "lcd_id": lcd_master.get("lcd_id", {}).get("display_value", f"L{lcd_id}"),
                                "version": lcd_master.get("lcdVersion") or lcd_master.get("lcd_version"),
                                "title": lcd_master.get("title"),
                                "status": lcd_master.get("status"),
                                "effective_date": lcd_master.get("effectiveDate") or lcd_master.get("effective_date"),
                                "termination_date": lcd_master.get("endDate") or lcd_master.get("termination_date"),
                                "raw_document": lcd_master
                            }
                            resolved_lcds.append(lcd_doc)
                            applicable_lcds.append(lcd_doc)

        add_trace("VALIDATE_FETCH_LCDS", geographically_applicable_lcds, {"retrieved": [l["lcd_id"] for l in resolved_lcds]})

        applicable_ncds = []
        resolved_ncds = []
        for ncd_id in candidate_ncd_ids:
            # NCDs are national, consider them applicable
            ncd_master = CMSApiService.fetch_ncd_document(ncd_id)
            if ncd_master:
                ncd_master["ncd_id"] = {"canonical_value": ncd_id, "display_value": ncd_id}
                db["ncds"].update_one({"ncd_id.canonical_value": ncd_id}, {"$set": ncd_master}, upsert=True)
                
                ndoc = {
                    "ncd_id": ncd_master.get("ncd_id", {}).get("display_value", ncd_id),
                    "version": ncd_master.get("documentVersion") or ncd_master.get("document_version"),
                    "title": ncd_master.get("title"),
                    "status": "Active",
                    "effective_date": ncd_master.get("effectiveDate") or ncd_master.get("effective_date"),
                    "relationship_source": "Article Link",
                    "raw_document": ncd_master
                }
                if ndoc not in resolved_ncds:
                    resolved_ncds.append(ndoc)
                    applicable_ncds.append(ndoc)

        add_trace("VALIDATE_FETCH_NCDS", candidate_ncd_ids, {"retrieved": [n["ncd_id"] for n in resolved_ncds]})

        # -------------------------------------------------------------
        # STEP 6: Fetch Article Coding
        # -------------------------------------------------------------
        article_coding_context = {}
        for aid in candidate_article_ids:
            disp_id = f"A{aid}"
            hcpcs_data = CMSApiService.fetch_article_hcpcs(aid)
            cov_data = CMSApiService.fetch_article_icd10_covered(aid)
            noncov_data = CMSApiService.fetch_article_icd10_noncovered(aid)
            mod_data = CMSApiService.fetch_article_hcpc_modifier(aid)

            article_coding_context[disp_id] = {
                "hcpcs_codes": [h.get("hcpcCode") for h in hcpcs_data if h.get("hcpcCode")],
                "covered_icd10": [i.get("icd10Code") for i in cov_data if i.get("icd10Code")],
                "noncovered_icd10": [i.get("icd10Code") for i in noncov_data if i.get("icd10Code")],
                "modifiers": [m.get("modifierCode") for m in mod_data if m.get("modifierCode")],
                "bill_codes": [],
                "jurisdictions": []
            }

        # -------------------------------------------------------------
        # STEP 7: Determine Final Routing Confidence & Status
        # -------------------------------------------------------------
        if not candidate_lcd_ids and not candidate_ncd_ids:
            routing_status = "NOT_FOUND"
            confidence = 1.0
        elif not applicable_lcds and not applicable_ncds:
            routing_status = "NEEDS_REVIEW"
            confidence = 0.5
        else:
            routing_status = "RESOLVED"
            confidence = 1.0

        if unresolved_references:
            confidence = max(0.1, confidence - 0.3)
            routing_status = "NEEDS_REVIEW"

        return PolicyRoutingResponse(
            routing_status=routing_status,
            normalized_request=request.model_dump(),
            candidate_ncds=resolved_ncds,
            applicable_ncds=applicable_ncds,
            candidate_lcds=resolved_lcds,
            applicable_lcds=applicable_lcds,
            related_articles=related_articles,
            jurisdiction=resolved_jurisdiction,
            contractor=resolved_contractor,
            coding_context=article_coding_context,
            unresolved_references=unresolved_references,
            warnings=warnings,
            routing_confidence=confidence,
            routing_trace=trace
        )
