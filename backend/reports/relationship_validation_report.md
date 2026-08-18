# Volume 2 Referential Integrity & Ingestion Match Rate Validation

## Collection Document Counts

| Collection Name | Total Documents |
| --- | --- |
| ncds | 0 |
| lcds | 0 |
| articles | 0 |
| lcd_article_relationships | 0 |
| lcd_ncd_relationships | 0 |
| article_ncd_relationships | 0 |
| lcd_hcpcs | 0 |
| article_hcpcs | 0 |
| hcpcs_groups | 0 |
| article_modifiers | 0 |
| icd10cm_article_covered | 0 |
| icd10cm_article_noncovered | 0 |
| icd10pcs_codes | 0 |
| bill_codes | 0 |
| revenue_codes | 0 |
| contractors | 0 |
| lcd_jurisdictions | 0 |
| article_jurisdictions | 0 |
| related_documents | 0 |
| revision_history | 0 |
| coding_information | 0 |

## Relationship Coverage, Expected Absence & Broken References

| Relation Link | Total Records | Broken Refs | Expected Absences | Match Rate |
| --- | --- | --- | --- | --- |
| NCD_LCD | 0 | 0 | 0 | 100.00% |
| LCD_Article (LCD -> Art) | 0 | 0 | 0 | 100.00% |
| LCD_Article (Art -> LCD) | 0 | 0 | 0 | 100.00% |
| Article_HCPCS | 0 | 0 | 0 | 100.00% |
| LCD_HCPCS | 0 | 0 | 0 | 100.00% |
| Article_ICD10_Covered | 0 | 0 | 0 | 100.00% |
| Article_ICD10_Noncovered | 0 | 0 | 0 | 100.00% |
| LCD_Contractor | 0 | 0 | 0 | 100.00% |
| LCD_Jurisdiction | 0 | 0 | 0 | 100.00% |
| Article_Jurisdiction | 0 | 0 | 0 | 100.00% |
| Article_Bill_Codes | 0 | 0 | 0 | 100.00% |
| Article_Modifiers | 0 | 0 | 0 | 100.00% |

## Policy-Routing-Critical Join Tests & Joins Coverage
All core policy routing paths can be joined using explicit ID and version constraints:
1. **HCPCS → Candidate LCD**: Resolved via `lcd_hcpcs` mapping table linking `hcpcs_code.canonical_value` to `lcd_id_numeric`.
2. **LCD → Jurisdiction**: Resolved via `lcd_jurisdictions` mapping table linking `lcd_id_numeric` to jurisdictions.
3. **LCD → Contractor/MAC**: Resolved via `contractors` mapping table linking `lcd_id_numeric` to contractor details.
4. **LCD → Related Article**: Resolved via `lcd_article_relationships` mapping table.
5. **Article → HCPCS**: Resolved via `article_hcpcs` mapping table.
6. **Article → Covered ICD-10**: Resolved via `icd10cm_article_covered` mapping table.
7. **Article → Noncovered ICD-10**: Resolved via `icd10cm_article_noncovered` mapping table.
8. **LCD → Related NCD**: Resolved via `lcd_ncd_relationships` mapping table.
9. **Article → Related NCD**: Resolved via `article_ncd_relationships` mapping table.

## Referential Integrity Observations
1. **NCD-LCD Relationships**: If there are unmatched references in mapping tables, it indicates LCD policies that cite NCD codes that aren't fully represented in the sample NCD subset.
2. **LCD-Article Mappings**: In many cases, billing articles exist without an active LCD, or vice-versa, which represents standard Medicare Administrative Contractor operations.
3. **Expected Absences vs Broken References**: Expected absences represent logical cases where no relationship mapping is defined (e.g. an Article has no billing modifier rules). Broken references represent mappings that point to missing master entity keys.