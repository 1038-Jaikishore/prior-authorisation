import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.db.connection import db_connection
from app.models.evaluation import PolicyRequirement, PatientEvidence, RequirementEvaluation, CodingValidation, EvaluationBundle
from app.services.prior_auth_intake import PriorAuthorizationIntakeService
from app.services.requirement_extraction import PolicyRequirementExtractor
from app.services.evidence_matching import PolicyEvidenceMatcher
from app.services.coding_validation import CodingValidationService

class PriorAuthorizationEvaluationService:
    @classmethod
    def evaluate_request(
        cls, 
        request_id: str, 
        override_state: Optional[str] = None, 
        override_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Orchestrates structured intake, routing, retrieval, requirement extraction, matching, and validations."""
        db = db_connection.get_db()
        
        # 1. Fetch raw intake/routing/retrieval response
        intake_res = PriorAuthorizationIntakeService.execute_route_and_retrieve(
            request_id=request_id,
            override_state=override_state,
            override_date=override_date
        )
        
        packet = intake_res["clinical_evidence_packet"]
        routing = intake_res["policy_routing"]
        retrieval = intake_res["policy_retrieval"]
        
        from app.models.patient import ClinicalEvidencePacket
        if isinstance(packet, dict):
            packet = ClinicalEvidencePacket(**packet)
            
        if hasattr(routing, "model_dump"):
            routing = routing.model_dump()
        elif hasattr(routing, "dict"):
            routing = routing.dict()
            
        if hasattr(retrieval, "model_dump"):
            retrieval = retrieval.model_dump()
        elif hasattr(retrieval, "dict"):
            retrieval = retrieval.dict()
        
        eval_id = f"EVAL-{request_id}-{uuid.uuid4().hex[:8]}"
        
        # Create base context lists
        controlling_policies = []
        applicable_policies = []
        related_reference_policies = []
        warnings = list(intake_res.get("warnings", []))
        
        # Check if routing is unavailable or has missing geography
        routing_status = routing.get("routing_status", "NO_POLICY_FOUND")
        
        if routing_status == "MISSING_ROUTING_GEOGRAPHY":
            bundle = EvaluationBundle(
                authorization_id=request_id,
                evaluation_id=eval_id,
                policy_context={
                    "controlling_policies": [],
                    "applicable_policies": [],
                    "related_reference_policies": []
                },
                requirements=[],
                requirement_evaluations=[],
                coding_validations=[],
                administrative_validations=[
                    CodingValidation(
                        validator="JURISDICTION",
                        status="FAIL",
                        subject=override_state or "None",
                        reason="Geography validation failed: Facility location state code is missing."
                    )
                ],
                summary={
                    "requirements_total": 0, "met": 0, "not_met": 0, "unclear": 0, "not_applicable": 0,
                    "validation_pass": 0, "validation_fail": 1, "validation_warning": 0
                },
                missing_information=["Provider state geography is missing. Please provide a manual state code."],
                warnings=warnings,
                provenance={
                    "evaluated_at": datetime.now(timezone.utc).isoformat(),
                    "intake_status": "MISSING_ROUTING_GEOGRAPHY",
                    "reason": "Intake geography state code is unresolved."
                }
            )
            # Persist bundle to DB
            db["evaluation_bundles"].insert_one(bundle.model_dump())
            return bundle.model_dump()
            
        if routing_status == "NO_POLICY_FOUND":
            bundle = EvaluationBundle(
                authorization_id=request_id,
                evaluation_id=eval_id,
                policy_context={
                    "controlling_policies": [],
                    "applicable_policies": [],
                    "related_reference_policies": []
                },
                requirements=[],
                requirement_evaluations=[],
                coding_validations=[
                    CodingValidation(
                        validator="LCD_HCPCS",
                        status="UNKNOWN",
                        subject=packet.requested_service.get("code", "None"),
                        reason="No matching LCD reference policy exists in CMS database for this requested service."
                    )
                ],
                administrative_validations=[],
                summary={
                    "requirements_total": 0, "met": 0, "not_met": 0, "unclear": 0, "not_applicable": 0,
                    "validation_pass": 0, "validation_fail": 0, "validation_warning": 1
                },
                missing_information=["No applicable CMS policies were matched by the routing engine."],
                warnings=warnings + ["POLICY_EVALUATION_UNAVAILABLE: No applicable CMS policy matched. Evaluation is unavailable."],
                provenance={
                    "evaluated_at": datetime.now(timezone.utc).isoformat(),
                    "intake_status": "POLICY_EVALUATION_UNAVAILABLE",
                    "reason": "NO_APPLICABLE_CMS_POLICY"
                }
            )
            db["evaluation_bundles"].insert_one(bundle.model_dump())
            return bundle.model_dump()
            
        # 2. Extract policy roles and classify RELATED vs CONTROLLING NCDs
        hcpcs_val = packet.requested_service.get("code")
        direct_ncd_ids = set()
        if hcpcs_val:
            direct_ncd_ids = set(
                d.get("ncd_id_numeric")
                for d in db["ncd_hcpcs"].find({"hcpcs_code.canonical_value": hcpcs_val})
                if d.get("ncd_id_numeric")
            )
            
        # Categorize policy filters
        candidate_policies = []
        geography_compatible_policies = []
        
        for l in routing.get("candidate_lcds", []):
            candidate_policies.append(l["lcd_id"])
        for n in routing.get("candidate_ncds", []):
            candidate_policies.append(n["ncd_id"])
            
        for l in routing.get("applicable_lcds", []):
            geography_compatible_policies.append(l["lcd_id"])
        for n in routing.get("applicable_ncds", []):
            geography_compatible_policies.append(n["ncd_id"])
            
        # Determine final applicable LCDs based on diagnosis mapping
        final_applicable_lcds = []
        if len(geography_compatible_policies) == 1:
            final_applicable_lcds = list(geography_compatible_policies)
        elif len(geography_compatible_policies) > 1:
            # Check which LCDs cover the diagnoses
            patient_diags = []
            for d in getattr(packet, "diagnosis_codes", []):
                patient_diags.append("".join(c for c in d if c.isalnum()).upper())
                
            diagnosis_matching_lcds = set()
            for art in routing.get("related_articles", []):
                art_id = art["article_id"]
                art_numeric = "".join(c for c in art_id if c.isdigit())
                
                cov_count = db["icd10cm_article_covered"].count_documents({
                    "article_id_numeric": art_numeric,
                    "icd10_code.canonical_value": {"$in": patient_diags}
                })
                if cov_count > 0:
                    lar_docs = list(db["lcd_article_relationships"].find({"article_id_numeric": art_numeric}))
                    for doc in lar_docs:
                        lcd_id = doc.get("lcd_id_numeric")
                        if lcd_id:
                            diagnosis_matching_lcds.add(f"L{lcd_id}")
                            
            matched_lcds = [l for l in geography_compatible_policies if l in diagnosis_matching_lcds]
            if len(matched_lcds) == 1:
                final_applicable_lcds = matched_lcds
            elif len(matched_lcds) > 1:
                final_applicable_lcds = matched_lcds
                warnings.append("POLICY_APPLICABILITY_UNCERTAIN: Multiple LCDs match patient diagnosis. Unable to determine single controlling policy.")
            else:
                final_applicable_lcds = []
                warnings.append("POLICY_APPLICABILITY_UNCERTAIN: No single LCD covers patient diagnosis code. Multiple active LCDs found.")

        policy_roles = {}
        for n in routing.get("applicable_ncds", []):
            n_id = n["ncd_id"]
            if n_id in direct_ncd_ids:
                policy_roles[n_id] = "CONTROLLING"
                controlling_policies.append(n_id)
            else:
                policy_roles[n_id] = "RELATED_REFERENCE"
                related_reference_policies.append(n_id)
            
        for n in routing.get("candidate_ncds", []):
            n_id = n["ncd_id"]
            if n_id not in policy_roles:
                if n_id in direct_ncd_ids:
                    policy_roles[n_id] = "APPLICABLE"
                    applicable_policies.append(n_id)
                else:
                    policy_roles[n_id] = "RELATED_REFERENCE"
                    related_reference_policies.append(n_id)
                
        for l in routing.get("applicable_lcds", []):
            l_id = l["lcd_id"]
            if l_id in final_applicable_lcds:
                policy_roles[l_id] = "APPLICABLE"
                applicable_policies.append(l_id)
            else:
                policy_roles[l_id] = "RELATED_REFERENCE"
                related_reference_policies.append(l_id)
            
        for l in routing.get("candidate_lcds", []):
            l_id = l["lcd_id"]
            if l_id not in policy_roles:
                if l_id in final_applicable_lcds:
                    policy_roles[l_id] = "APPLICABLE"
                    applicable_policies.append(l_id)
                else:
                    policy_roles[l_id] = "RELATED_REFERENCE"
                    related_reference_policies.append(l_id)
                
        # Related reference articles or secondary relationship matches are classified as RELATED_REFERENCE
        for a in routing.get("related_articles", []):
            policy_roles[a["article_id"]] = "RELATED_REFERENCE"
            related_reference_policies.append(a["article_id"])
            
        # 3. Extract and deduplicate Policy Requirements from retrieval chunks
        retrieved_chunks = retrieval.get("results", [])
        requirements = PolicyRequirementExtractor.extract_requirements(
            retrieved_chunks=retrieved_chunks,
            policy_roles=policy_roles
        )
        
        # 4. Run clinical Evidence Matching
        evaluations = PolicyEvidenceMatcher.match_evidence(
            requirements=requirements,
            evidence_packet=packet
        )
        
        # 5. Perform deterministic coding/administrative validation
        coding_validations: List[CodingValidation] = []
        admin_validations: List[CodingValidation] = []
        
        primary_lcd = routing["applicable_lcds"][0]["lcd_id"] if routing["applicable_lcds"] else (
            routing["candidate_lcds"][0]["lcd_id"] if routing["candidate_lcds"] else None
        )
        primary_article = routing["related_articles"][0]["article_id"] if routing["related_articles"] else None
        
        # Diagnosis validations (ICD-10)
        for diag in packet.diagnosis_codes:
            coding_validations.append(CodingValidationService.validate_icd10(
                diagnosis_code=diag,
                article_id=primary_article
            ))
            
        # HCPCS validations
        hcpcs_code = packet.requested_service.get("code", "")
        coding_validations.extend(CodingValidationService.validate_hcpcs(
            hcpcs_code=hcpcs_code,
            lcd_id=primary_lcd,
            article_id=primary_article
        ))
        
        # Modifier validations
        # Extract active modifiers if they exist on packet or requested service details
        req_doc = db["authorization_requests"].find_one({"request_id": request_id})
        modifiers = []
        if req_doc and "modifiers" in req_doc:
            modifiers = req_doc["modifiers"]
        coding_validations.append(CodingValidationService.validate_modifier(
            modifiers=modifiers,
            article_id=primary_article
        ))
        
        # Bill Type validation
        bill_type = req_doc.get("bill_type_code") if req_doc else None
        coding_validations.append(CodingValidationService.validate_bill_type(
            bill_type=bill_type,
            article_id=primary_article
        ))
        
        # Revenue Code validation
        revenue_code = req_doc.get("revenue_code") if req_doc else None
        coding_validations.append(CodingValidationService.validate_revenue_code(
            revenue_code=revenue_code,
            article_id=primary_article
        ))
        
        # Administrative validations (MAC / State Jurisdiction)
        state_code = packet.demographics.get("state_code", "")
        if state_code and primary_lcd:
            admin_validations.append(CodingValidationService.validate_jurisdiction(
                state_code=state_code,
                lcd_id=primary_lcd
            ))
            
        # Date & Version checks
        service_date = override_date or packet.demographics.get("request_date") or req_doc.get("request_date") if req_doc else None
        if service_date and primary_lcd:
            # Query lcd record from db for boundary dates
            lcd_master = db["lcds"].find_one({"display_id": primary_lcd})
            admin_validations.append(CodingValidationService.validate_dates_and_version(
                service_date=service_date,
                lcd_id=primary_lcd,
                policy_doc=lcd_master
            ))
            
        # 6. Compile counts and missing details summaries
        met_count = 0
        not_met_count = 0
        unclear_count = 0
        not_applicable_count = 0
        missing_info = []
        
        for ev in evaluations:
            # Retain RELATED_REFERENCE evaluation for context, but do NOT automatically treat failures as overall metrics
            role = ev.policy_requirement.policy_role
            if role == "RELATED_REFERENCE":
                continue
                
            if ev.status == "MET":
                met_count += 1
            elif ev.status == "NOT_MET":
                not_met_count += 1
            elif ev.status == "NOT_APPLICABLE":
                not_applicable_count += 1
            else:
                unclear_count += 1
                missing_info.extend(ev.missing_information)
                
        pass_val = 0
        fail_val = 0
        warn_val = 0
        
        for cv in (coding_validations + admin_validations):
            if cv.status == "PASS":
                pass_val += 1
            elif cv.status == "FAIL":
                fail_val += 1
            elif cv.status in ("WARNING", "UNKNOWN"):
                warn_val += 1
                
        summary = {
            "requirements_total": len([e for e in evaluations if e.policy_requirement.policy_role != "RELATED_REFERENCE"]),
            "met": met_count,
            "not_met": not_met_count,
            "unclear": unclear_count,
            "not_applicable": not_applicable_count,
            "validation_pass": pass_val,
            "validation_fail": fail_val,
            "validation_warning": warn_val
        }
        
        bundle = EvaluationBundle(
            authorization_id=request_id,
            evaluation_id=eval_id,
            policy_context={
                "controlling_policies": list(set(controlling_policies)),
                "applicable_policies": list(set(applicable_policies)),
                "related_reference_policies": list(set(related_reference_policies))
            },
            requirements=requirements,
            requirement_evaluations=evaluations,
            coding_validations=coding_validations,
            administrative_validations=admin_validations,
            summary=summary,
            missing_information=list(set(missing_info)),
            warnings=warnings,
            provenance={
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
                "extraction_engine_version": "1.0.0",
                "matching_engine_version": "1.0.0",
                "validation_engine_version": "1.0.0"
            }
        )
        
        # Save bundle to database
        db["evaluation_bundles"].insert_one(bundle.model_dump())
        
        # Attach additional metadata fields for reporting
        dump = bundle.model_dump()
        dump["policy_context"]["candidate_policies"] = list(set(candidate_policies))
        dump["policy_context"]["geography_compatible_policies"] = list(set(geography_compatible_policies))
        dump["policy_context"]["service_relevant_policies"] = list(set(geography_compatible_policies))  # All active LCDs mapped 97110
        return dump
        
    @classmethod
    def get_latest_evaluation(cls, request_id: str) -> Optional[Dict[str, Any]]:
        """Fetches the latest completed evaluation bundle for a request ID."""
        db = db_connection.get_db()
        doc = db["evaluation_bundles"].find_one(
            {"authorization_id": request_id},
            sort=[("provenance.evaluated_at", -1)]
        )
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    @classmethod
    def get_evaluation_by_id(cls, evaluation_id: str) -> Optional[Dict[str, Any]]:
        """Fetches a specific completed evaluation bundle by its evaluation ID."""
        db = db_connection.get_db()
        doc = db["evaluation_bundles"].find_one({"evaluation_id": evaluation_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc
