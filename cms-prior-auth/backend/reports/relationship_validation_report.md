# Volume 2 Referential Integrity & Ingestion Match Rate Validation

## Collection Document Counts

| Collection Name | Total Documents |
| --- | --- |
| ncds | 357 |
| lcds | 979 |
| articles | 700 |
| lcd_article_relationships | 2,911 |
| lcd_ncd_relationships | 1,551 |
| article_ncd_relationships | 2,507 |
| hcpcs_codes | 13,789 |
| lcd_hcpcs | 1,909 |
| article_hcpcs | 13,789 |
| hcpcs_groups | 2,040 |
| article_modifiers | 1,745 |
| icd10cm_article_covered | 198,274 |
| icd10cm_article_noncovered | 24,445 |
| icd10pcs_codes | 259 |
| bill_codes | 1,376 |
| revenue_codes | 356 |
| contractors | 13,968 |
| lcd_jurisdictions | 240 |
| article_jurisdictions | 258 |
| related_documents | 1,805 |
| revision_history | 7,987 |
| coding_information | 1,221 |

## Relationship Match Rates

| Relation Link | Calculated Match Rate |
| --- | --- |
| NCD_LCD | 61.90% |
| LCD_Article (lcd_match_rate) | 79.08% |
| LCD_Article (article_match_rate) | 48.40% |
| Article_HCPCS | 63.17% |
| LCD_HCPCS | 100.00% |
| Article_ICD10_Covered | 100.00% |
| Article_ICD10_Noncovered | 100.00% |
| LCD_Contractor | 100.00% |
| LCD_Jurisdiction | 100.00% |
| Article_Jurisdiction | 18.99% |
| Article_Bill_Codes | 52.11% |
| Article_Modifiers | 51.12% |

## Referential Integrity Observations
1. **NCD-LCD Relationships**: If there are unmatched references in mapping tables, it indicates LCD policies that cite NCD codes that aren't fully represented in the sample NCD subset.
2. **LCD-Article Mappings**: In many cases, billing articles exist without an active LCD, or vice-versa, which represents standard Medicare Administrative Contractor operations.