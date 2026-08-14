# CMS Dataset Relationship & Join Keys Report

## Conceptual Mapping & Join Keys

This report lists relationship links, join keys, and unresolved links identified among NCDs, LCDs, Articles, HCPCS, ICD, contractors, jurisdictions, modifiers, bill codes, and revenue codes.

### Major Entities and Identifiers
- **NCD ID**: Found in `ncd_documents_data.csv` (`document_display_id`, `document_id`)
- **LCD ID**: Found in `lcd_documents.csv` (`document_id`), `lcd_full_data.csv` (`lcd_id`)
- **Article ID**: Found in `articles_700.csv` (`article_id`)
- **HCPCS Code**: Found in `CMS_HCPC_code.csv` (`hcpc_code_id`) and `CMS_LCD_HCPCS_All_LCDs (1).csv` (`hcpc_code_id`)
- **ICD-10-CM Code**: Found in `icd10_covered_all_articles.csv` (`icd10_code_id`) and `icd10_noncovered_all_articles.csv` (`icd10_code_id`)
- **ICD-10-PCS Code**: Found in `icd10_pcs_codes.csv` (`icd10_pcs_code` / column 5)
- **Modifier Code**: Found in `CMS_HCPCS_Modifiers_All_Articles.csv` (`hcpc_modifier_code_id`)
- **Revenue Code**: Found in `revenue_codes.csv` (`revenue_code` / column 6)
- **Bill Code**: Found in `article_bill_codes.csv` (`bill_code_id`)
- **Contractor/MAC**: Found in `lcd_contractor.csv` (`contractor_id`) and `lcd_article_relationship.csv` (`contractor_id`)
- **Jurisdiction**: Found in `cms_lcd_primary_jurisdiction.csv.xls` and `cms_article_jurisdiction.csv.xls` (`state_id`, `state_name`)

### Entity-to-Entity Relationships & Join Keys
| Source Entity | Target Entity | Bridge File | Join Keys |
| --- | --- | --- | --- |
| LCD (`lcd_documents.csv`) | Article (`articles_700.csv`) | `lcd_article_relationship.csv` | `lcd_id` and `article_id` |
| LCD (`lcd_documents.csv`) | NCD (`ncd_documents_data.csv`) | `lcd_related_ncd_documents.csv` | `lcd_id` and `r_ncd_id` (matches `document_id` of NCD) |
| Article (`articles_700.csv`) | NCD (`ncd_documents_data.csv`) | `article_related_ncd_documents_data.csv` | `article_id` and `r_ncd_id` |
| Article (`articles_700.csv`) | HCPCS (`CMS_HCPC_code.csv`) | `CMS_HCPC_code.csv` directly | `article_id` |
| Article (`articles_700.csv`) | ICD-10-CM | `icd10_covered_all_articles.csv` / `icd10_noncovered_all_articles.csv` | `article_id` to Articles; `icd10_code_id` to ICD-10-CM tabular reference |
| Article (`articles_700.csv`) | ICD-10-PCS | `icd10_pcs_codes.csv` | `article_id` |
| Article (`articles_700.csv`) | Modifier | `CMS_HCPCS_Modifiers_All_Articles.csv` | `article_id` |
| Article (`articles_700.csv`) | Revenue Code | `revenue_codes.csv` | `article_id` |
| Article (`articles_700.csv`) | Jurisdiction / State | `cms_article_jurisdiction.csv.xls` | `article_id` |
| LCD (`lcd_documents.csv`) | Jurisdiction / State | `cms_lcd_primary_jurisdiction.csv.xls` | `lcd_id` |

### Unresolved Relationship Links & Data Gaps
1. **ICD-10-CM Tabular PDF Reference (`icd10cm_tabular_2027.pdf`)**:
   - **Unresolved Link**: The PDF contains narrative text and tabular hierarchy for ICD-10-CM diagnoses. There is no direct structured key relationship file linking diagnostic codes to NCD/LCD guidelines programmatically other than standard string matching of codes (e.g. `C00.0` inside `icd10_covered_all_articles.csv` to standard ICD-10 chapters).
2. **Contractor Name mappings in `lcd_documents.csv` vs. IDs in `lcd_contractor.csv`**:
   - **Unresolved Link**: `lcd_documents.csv` contains textual contractor names (e.g., `'Palmetto GBA'`) in `contractor_name_type` but does not contain `contractor_id` to directly join with `lcd_contractor.csv` without string matching or intermediate joins.