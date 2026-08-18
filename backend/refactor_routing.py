import re

def refactor():
    with open("app/services/policy_routing.py", "r") as f:
        content = f.read()
        
    # Find the start of route_policy
    start_idx = content.find("    @staticmethod\n    def route_policy(request_id: str) -> PolicyRoutingResponse:")
    if start_idx == -1:
        print("Could not find route_policy")
        return
        
    # Find the end of the class/file (it's the last method in the file)
    
    new_method = """    @staticmethod
    def route_policy(request_id: str) -> PolicyRoutingResponse:
        db = db_connection.get_db()
        trace = {}
        warnings = []
        
        def add_trace(step, input_data, output_data):
            trace[step] = {"input": input_data, "output": output_data}

        # -------------------------------------------------------------
        # STEP 1: Load Request & Extraction
        # -------------------------------------------------------------
        req = db["authorization_requests"].find_one({"request_id": request_id})
        if not req:
            raise ValueError(f"Request {request_id} not found.")

        ext = db["document_extractions"].find_one({"request_id": request_id})
        if not ext:
            raise ValueError(f"Extraction for {request_id} not found. Must run Phase 1 first.")

        normalized_request = ext.get("normalized_request", {})
        add_trace("LOAD_EXTRACTION", {"request_id": request_id}, {"extracted_keys": list(normalized_request.keys())})

        # -------------------------------------------------------------
        # STEP 2: Extract Key Identifiers (HCPCS)
        # -------------------------------------------------------------
        norm_hcpcs = None
        unresolved_references = []
        
        req_service = normalized_request.get("Requested_Service", {})
        raw_hcpcs = req_service.get("hcpcs_code")
        if raw_hcpcs and raw_hcpcs.upper() != "UNKNOWN":
            norm_hcpcs = raw_hcpcs.strip().upper()
        else:
            unresolved_references.append("Requested_Service.hcpcs_code")

        patient = normalized_request.get("Patient", {})
        state_code = patient.get("address", {}).get("state")
        state_name = patient.get("address", {}).get("state") # Assume same for mock

        norm_diags = []
        for d in normalized_request.get("Diagnoses", []):
            code = d.get("icd10_code")
            if code and code.upper() != "UNKNOWN":
                norm_diags.append({"canonical_value": code.strip().upper()})

        add_trace("EXTRACT_IDENTIFIERS", None, {"hcpcs": norm_hcpcs, "state": state_code})

        candidate_article_ids = []
        candidate_lcd_ids = []
        candidate_ncd_ids = []
        
        # -------------------------------------------------------------
        # STEP 3: EHR -> HCPCS -> MongoDB article_hcpcs -> Candidate Articles
        # -------------------------------------------------------------
        if norm_hcpcs:
            art_cursor = db["article_hcpcs"].find({"hcpcs_code.canonical_value": norm_hcpcs})
            for a in art_cursor:
                aid = a.get("article_id_numeric")
                if aid:
                    aid = str(aid).strip()
                    if aid and aid != "None" and any(c.isdigit() for c in aid) and aid not in candidate_article_ids:
                        candidate_article_ids.append(aid)

        add_trace("HCPCS_TO_CANDIDATES_LOCAL_CACHE", norm_hcpcs, {"candidate_articles": candidate_article_ids})

        # -------------------------------------------------------------
        # STEP 4: CMS Article Document & CMS Relationship Lookup
        # -------------------------------------------------------------
        related_articles = []
        article_coding_context = {}
        
        for aid in candidate_article_ids:
            # 4a. Fetch CMS Article Document
            art_master = db["articles"].find_one({"article_id.canonical_value": aid})
            if not art_master:
                art_master = CMSApiService.fetch_article_document(aid)
                if art_master:
                    art_master["article_id"] = {"canonical_value": aid, "display_value": f"A{aid}"}
                    db["articles"].update_one({"article_id.canonical_value": aid}, {"$set": art_master}, upsert=True)
                    PolicyIngestionService.ingest_document("ARTICLE", aid, art_master, norm_hcpcs, [d["canonical_value"] for d in norm_diags])
            
            if art_master:
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
        # STEP 5: Validate & Fetch Documents (LCD)
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
                    
                    is_match = False
                    for jur in jur_data:
                        if jur.get("stateCode") == state_code or jur.get("stateName", "").upper() == state_name.upper():
                            is_match = True
                            break
                            
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
                    lcd_master = db["lcds"].find_one({"lcd_id.canonical_value": lcd_id})
                    if not lcd_master:
                        lcd_master = CMSApiService.fetch_lcd_document(lcd_id)
                        if lcd_master:
                            lcd_master["lcd_id"] = {"canonical_value": lcd_id, "display_value": f"L{lcd_id}"}
                            db["lcds"].update_one({"lcd_id.canonical_value": lcd_id}, {"$set": lcd_master}, upsert=True)
                            PolicyIngestionService.ingest_document("LCD", lcd_id, lcd_master, norm_hcpcs, [d["canonical_value"] for d in norm_diags])
                    
                    if lcd_master:
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

        # -------------------------------------------------------------
        # STEP 6: Validate & Fetch Documents (NCD)
        # -------------------------------------------------------------
        applicable_ncds = []
        resolved_ncds = []
        
        # NCDs are national, so they generally bypass strict state geography validation, 
        # but we treat them as applicable if they were linked from the article.
        for ncd_id in candidate_ncd_ids:
            ncd_master = db["ncds"].find_one({"ncd_id.canonical_value": ncd_id})
            if not ncd_master:
                ncd_master = CMSApiService.fetch_ncd_document(ncd_id)
                if ncd_master:
                    ncd_master["ncd_id"] = {"canonical_value": ncd_id, "display_value": ncd_id}
                    db["ncds"].update_one({"ncd_id.canonical_value": ncd_id}, {"$set": ncd_master}, upsert=True)
                    PolicyIngestionService.ingest_document("NCD", ncd_id, ncd_master, norm_hcpcs, [d["canonical_value"] for d in norm_diags])
            
            if ncd_master:
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
            normalized_request=normalized_request,
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
"""
    
    new_content = content[:start_idx] + new_method
    
    with open("app/services/policy_routing.py", "w") as f:
        f.write(new_content)
        
if __name__ == "__main__":
    refactor()
