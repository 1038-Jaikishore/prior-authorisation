import sys

def refactor():
    with open("app/services/policy_routing.py", "r") as f:
        content = f.read()
        
    start_str = "        # -------------------------------------------------------------\n        # STEP 3: HCPCS -> Candidate Discovery (Local Cache Initial Routing)"
    
    start_idx = content.find(start_str)
    if start_idx == -1:
        print("Could not find start string")
        return
        
    new_logic = """        # -------------------------------------------------------------
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
            # 4a. CMS Article Document
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
                    lcd_master = CMSApiService.fetch_lcd_document(lcd_id)
                    if lcd_master:
                        lcd_master["lcd_id"] = {"canonical_value": lcd_id, "display_value": f"L{lcd_id}"}
                        db["lcds"].update_one({"lcd_id.canonical_value": lcd_id}, {"$set": lcd_master}, upsert=True)
                        
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
            normalized_request=request,
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
    
    new_content = content[:start_idx] + new_logic
    with open("app/services/policy_routing.py", "w") as f:
        f.write(new_content)
        
if __name__ == "__main__":
    refactor()
