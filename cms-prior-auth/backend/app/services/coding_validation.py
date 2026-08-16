import re
from typing import List, Dict, Any, Optional
from app.db.connection import db_connection
from app.models.evaluation import CodingValidation

US_STATES_FULL = {
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

class CodingValidationService:
    @classmethod
    def validate_icd10(
        cls, 
        diagnosis_code: str, 
        article_id: Optional[str]
    ) -> CodingValidation:
        """Validates ICD-10 CM diagnosis code presence in Article covered/noncovered listings."""
        db = db_connection.get_db()
        diag_clean = "".join(diagnosis_code.upper().split("."))
        
        if not article_id:
            return CodingValidation(
                validator="ARTICLE_ICD10",
                status="UNKNOWN",
                subject=diagnosis_code,
                policy_document=None,
                reason="No applicable Article resolved to perform covered diagnosis mapping."
            )
            
        art_numeric = "".join(c for c in article_id if c.isdigit())
        
        # Check covered list
        cov_match = db["icd10cm_article_covered"].find_one({
            "article_id_numeric": art_numeric,
            "icd10_code.canonical_value": diag_clean
        })
        
        if cov_match:
            return CodingValidation(
                validator="ARTICLE_ICD10",
                status="PASS",
                subject=diagnosis_code,
                policy_document=article_id,
                reason=f"Diagnosis code {diagnosis_code} is explicitly covered by Article {article_id} (Group {cov_match.get('icd10_covered_group', '1')}).",
                source_records=[{k: str(v) for k, v in cov_match.items() if k != "_id"}]
            )
            
        # Check noncovered list
        noncov_match = db["icd10cm_article_noncovered"].find_one({
            "article_id_numeric": art_numeric,
            "icd10_code.canonical_value": diag_clean
        })
        
        if noncov_match:
            return CodingValidation(
                validator="ARTICLE_ICD10",
                status="FAIL",
                subject=diagnosis_code,
                policy_document=article_id,
                reason=f"Diagnosis code {diagnosis_code} is explicitly listed as non-covered by Article {article_id}.",
                source_records=[{k: str(v) for k, v in noncov_match.items() if k != "_id"}]
            )
            
        return CodingValidation(
            validator="ARTICLE_ICD10",
            status="UNKNOWN",
            subject=diagnosis_code,
            policy_document=article_id,
            reason=f"Diagnosis code {diagnosis_code} is absent from both covered and noncovered lists of Article {article_id}."
        )

    @classmethod
    def validate_hcpcs(
        cls, 
        hcpcs_code: str, 
        lcd_id: Optional[str], 
        article_id: Optional[str]
    ) -> List[CodingValidation]:
        """Validates CPT/HCPCS code mappings against candidate LCD/Article rules."""
        db = db_connection.get_db()
        validations = []
        
        # 1. Existence check (HCPCS_EXISTS)
        is_synthetic = hcpcs_code.upper().startswith("PROC")
        if is_synthetic:
            validations.append(CodingValidation(
                validator="HCPCS_EXISTS",
                status="WARNING",
                subject=hcpcs_code,
                reason="Custom synthetic HCPCS code detected (PROCxxxx). No master CMS mappings exist."
            ))
            return validations
            
        # Check standard HCPCS exist in references
        hcpcs_exists = db["article_hcpcs"].count_documents({"hcpcs_code.canonical_value": hcpcs_code}) > 0 or \
                       db["lcd_hcpcs"].count_documents({"hcpcs_code.canonical_value": hcpcs_code}) > 0
                       
        if hcpcs_exists:
            validations.append(CodingValidation(
                validator="HCPCS_EXISTS",
                status="PASS",
                subject=hcpcs_code,
                reason=f"HCPCS code {hcpcs_code} is mapped to reference files in CMS database."
            ))
        else:
            validations.append(CodingValidation(
                validator="HCPCS_EXISTS",
                status="UNKNOWN",
                subject=hcpcs_code,
                reason=f"HCPCS code {hcpcs_code} is not mapped to reference files in local CMS database."
            ))
            
        # 2. LCD Mapping (LCD_HCPCS)
        if lcd_id:
            lcd_numeric = "".join(c for c in lcd_id if c.isdigit())
            lcd_match = db["lcd_hcpcs"].find_one({
                "lcd_id_numeric": lcd_numeric,
                "hcpcs_code.canonical_value": hcpcs_code
            })
            if lcd_match:
                validations.append(CodingValidation(
                    validator="LCD_HCPCS",
                    status="PASS",
                    subject=hcpcs_code,
                    policy_document=lcd_id,
                    reason=f"HCPCS code {hcpcs_code} is mapped to LCD {lcd_id}.",
                    source_records=[{k: str(v) for k, v in lcd_match.items() if k != "_id"}]
                ))
            else:
                has_art_match = False
                if article_id:
                    art_numeric = "".join(c for c in article_id if c.isdigit())
                    has_art_match = db["article_hcpcs"].count_documents({
                        "article_id_numeric": art_numeric,
                        "hcpcs_code.canonical_value": hcpcs_code
                    }) > 0
                    
                if has_art_match:
                    validations.append(CodingValidation(
                        validator="LCD_HCPCS",
                        status="WARNING",
                        subject=hcpcs_code,
                        policy_document=lcd_id,
                        reason=f"HCPCS code {hcpcs_code} has no direct mapping to LCD {lcd_id}, but coding applicability is established through the authoritative related Article {article_id}."
                    ))
                else:
                    validations.append(CodingValidation(
                        validator="LCD_HCPCS",
                        status="FAIL",
                        subject=hcpcs_code,
                        policy_document=lcd_id,
                        reason=f"HCPCS code {hcpcs_code} is absent from both LCD {lcd_id} and related Billing & Coding Article {article_id or 'None'} mappings."
                    ))
                
        # 3. Article Mapping (ARTICLE_HCPCS)
        if article_id:
            art_numeric = "".join(c for c in article_id if c.isdigit())
            art_match = db["article_hcpcs"].find_one({
                "article_id_numeric": art_numeric,
                "hcpcs_code.canonical_value": hcpcs_code
            })
            if art_match:
                validations.append(CodingValidation(
                    validator="ARTICLE_HCPCS",
                    status="PASS",
                    subject=hcpcs_code,
                    policy_document=article_id,
                    reason=f"HCPCS code {hcpcs_code} is mapped to Article {article_id}.",
                    source_records=[{k: str(v) for k, v in art_match.items() if k != "_id"}]
                ))
            else:
                validations.append(CodingValidation(
                    validator="ARTICLE_HCPCS",
                    status="FAIL",
                    subject=hcpcs_code,
                    policy_document=article_id,
                    reason=f"HCPCS code {hcpcs_code} is not mapped to Article {article_id} in reference tables."
                ))
                
        return validations

    @classmethod
    def validate_modifier(
        cls, 
        modifiers: List[str], 
        article_id: Optional[str]
    ) -> CodingValidation:
        """Validates provided modifiers against Article rules."""
        db = db_connection.get_db()
        
        if not article_id:
            return CodingValidation(
                validator="ARTICLE_MODIFIER",
                status="UNKNOWN",
                subject=", ".join(modifiers) if modifiers else "None",
                reason="No applicable Article resolved to perform modifier mapping."
            )
            
        art_numeric = "".join(c for c in article_id if c.isdigit())
        
        # Check if Article has modifier rules at all
        has_rules = db["article_modifiers"].count_documents({"article_id_numeric": art_numeric}) > 0
        
        if not modifiers:
            if has_rules:
                return CodingValidation(
                    validator="ARTICLE_MODIFIER",
                    status="UNKNOWN",
                    subject="None",
                    policy_document=article_id,
                    reason=f"Modifiers were not provided, but Article {article_id} contains modifier requirements."
                )
            else:
                return CodingValidation(
                    validator="ARTICLE_MODIFIER",
                    status="PASS",
                    subject="None",
                    policy_document=article_id,
                    reason=f"No modifiers provided, and Article {article_id} has no modifier requirements."
                )
                
        # Validate provided modifiers
        passed_modifiers = []
        failed_modifiers = []
        matched_records = []
        
        for m in modifiers:
            m_clean = m.strip().upper()
            match = db["article_modifiers"].find_one({
                "article_id_numeric": art_numeric,
                "modifier_code.canonical_value": m_clean
            })
            if match:
                passed_modifiers.append(m)
                matched_records.append({k: str(v) for k, v in match.items() if k != "_id"})
            else:
                failed_modifiers.append(m)
                
        if failed_modifiers:
            return CodingValidation(
                validator="ARTICLE_MODIFIER",
                status="FAIL",
                subject=", ".join(modifiers),
                policy_document=article_id,
                reason=f"Modifiers {', '.join(failed_modifiers)} are not listed as allowed modifiers in Article {article_id}.",
                source_records=matched_records
            )
            
        return CodingValidation(
            validator="ARTICLE_MODIFIER",
            status="PASS",
            subject=", ".join(modifiers),
            policy_document=article_id,
            reason=f"Modifiers {', '.join(passed_modifiers)} are allowed by Article {article_id}.",
            source_records=matched_records
        )

    @classmethod
    def validate_bill_type(
        cls, 
        bill_type: Optional[str], 
        article_id: Optional[str]
    ) -> CodingValidation:
        """Validates bill type code against Article rules."""
        db = db_connection.get_db()
        
        if not bill_type:
            return CodingValidation(
                validator="ARTICLE_BILL_TYPE",
                status="NOT_EVALUATED",
                subject="None",
                reason="Bill type was not provided on the prior authorization request."
            )
            
        if not article_id:
            return CodingValidation(
                validator="ARTICLE_BILL_TYPE",
                status="UNKNOWN",
                subject=bill_type,
                reason="No applicable Article resolved to perform bill type mapping."
            )
            
        art_numeric = "".join(c for c in article_id if c.isdigit())
        bill_clean = bill_type.strip().zfill(4) # Pad to canonical length if needed
        
        match = db["bill_codes"].find_one({
            "article_id_numeric": art_numeric,
            "bill_type_code.canonical_value": bill_clean
        })
        
        if match:
            return CodingValidation(
                validator="ARTICLE_BILL_TYPE",
                status="PASS",
                subject=bill_type,
                policy_document=article_id,
                reason=f"Bill type {bill_type} is allowed by Article {article_id}.",
                source_records=[{k: str(v) for k, v in match.items() if k != "_id"}]
            )
            
        return CodingValidation(
            validator="ARTICLE_BILL_TYPE",
            status="FAIL",
            subject=bill_type,
            policy_document=article_id,
            reason=f"Bill type {bill_type} is not listed in allowed bill types for Article {article_id}."
        )

    @classmethod
    def validate_revenue_code(
        cls, 
        revenue_code: Optional[str], 
        article_id: Optional[str]
    ) -> CodingValidation:
        """Validates revenue code against Article rules."""
        db = db_connection.get_db()
        
        if not revenue_code:
            return CodingValidation(
                validator="ARTICLE_REVENUE_CODE",
                status="NOT_EVALUATED",
                subject="None",
                reason="Revenue code was not provided on the prior authorization request."
            )
            
        if not article_id:
            return CodingValidation(
                validator="ARTICLE_REVENUE_CODE",
                status="UNKNOWN",
                subject=revenue_code,
                reason="No applicable Article resolved to perform revenue code mapping."
            )
            
        art_numeric = "".join(c for c in article_id if c.isdigit())
        rev_clean = revenue_code.strip().zfill(4)
        
        match = db["revenue_codes"].find_one({
            "article_id_numeric": art_numeric,
            "revenue_code.canonical_value": rev_clean
        })
        
        if match:
            return CodingValidation(
                validator="ARTICLE_REVENUE_CODE",
                status="PASS",
                subject=revenue_code,
                policy_document=article_id,
                reason=f"Revenue code {revenue_code} is allowed by Article {article_id}.",
                source_records=[{k: str(v) for k, v in match.items() if k != "_id"}]
            )
            
        return CodingValidation(
            validator="ARTICLE_REVENUE_CODE",
            status="FAIL",
            subject=revenue_code,
            policy_document=article_id,
            reason=f"Revenue code {revenue_code} is not listed in allowed revenue codes for Article {article_id}."
        )

    @classmethod
    def validate_jurisdiction(
        cls, 
        state_code: str, 
        lcd_id: str
    ) -> CodingValidation:
        """Validates LCD geographic applicability against resolved state code."""
        db = db_connection.get_db()
        
        lcd_numeric = "".join(c for c in lcd_id if c.isdigit())
        state_name = US_STATES_FULL.get(state_code.upper().strip(), "")
        
        if not state_name:
            return CodingValidation(
                validator="JURISDICTION",
                status="UNKNOWN",
                subject=state_code,
                policy_document=lcd_id,
                reason=f"Unknown or invalid U.S. state code: {state_code}."
            )
            
        match = db["lcd_jurisdictions"].find_one({
            "lcd_id_numeric": lcd_numeric,
            "state_name": state_name
        })
        
        if match:
            return CodingValidation(
                validator="JURISDICTION",
                status="PASS",
                subject=state_code,
                policy_document=lcd_id,
                reason=f"LCD {lcd_id} is geographically applicable in state {state_code} ({state_name}).",
                source_records=[{k: str(v) for k, v in match.items() if k != "_id"}]
            )
            
        return CodingValidation(
            validator="JURISDICTION",
            status="FAIL",
            subject=state_code,
            policy_document=lcd_id,
            reason=f"LCD {lcd_id} is not geographically applicable in state {state_code} ({state_name})."
        )

    @classmethod
    def validate_dates_and_version(
        cls, 
        service_date: str, 
        lcd_id: Optional[str],
        policy_doc: Optional[Dict[str, Any]]
    ) -> CodingValidation:
        """Validates date of service boundaries and version applicability."""
        if not policy_doc:
            return CodingValidation(
                validator="DATE_AND_VERSION",
                status="UNKNOWN",
                subject=service_date,
                reason="Policy document structure is missing to evaluate boundaries."
            )
            
        doc_id = lcd_id or policy_doc.get("lcd_id") or "Policy Doc"
        eff_dt = policy_doc.get("effective_date")
        term_dt = policy_doc.get("end_date") or policy_doc.get("termination_date")
        
        warnings_list = []
        status = "PASS"
        reason = f"Service date {service_date} falls within the active policy boundaries for {doc_id}."
        
        if eff_dt and service_date < eff_dt:
            status = "FAIL"
            reason = f"Service date {service_date} is prior to policy effective date {eff_dt}."
        elif term_dt and service_date > term_dt:
            status = "FAIL"
            reason = f"Service date {service_date} is after policy termination date {term_dt}."
            
        return CodingValidation(
            validator="DATE_AND_VERSION",
            status=status,
            subject=service_date,
            policy_document=doc_id,
            reason=reason,
            warnings=warnings_list
        )
