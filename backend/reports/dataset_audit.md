# CMS Dataset Physical Audit Report

## Overview
This report presents physical characteristics of the 27 CMS reference files.

| Filename | Format | Encoding | Rows | Columns | Duplicates | Malformed Rows | HTML | Accidental Headers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CMS_HCPCS_Code_Groups_All_Articles.csv | CSV | utf-8 | 1945 | 5 | 0 | 0 | Yes | No |
| CMS_HCPCS_Modifier_Groups_All_Articles.csv | CSV | utf-8 | 1286 | 5 | 0 | 0 | Yes | No |
| CMS_HCPCS_Modifiers_All_Articles.csv | CSV | utf-8 | 579 | 7 | 0 | 0 | No | No |
| CMS_HCPC_code.csv | CSV | utf-8 | 14098 | 9 | 0 | 0 | No | No |
| CMS_LCD_HCPCS_All_LCDs (1).csv | CSV | utf-8 | 1910 | 9 | 0 | 0 | Yes | No |
| CMS_LCD_HCPCS_Code_Groups_All_LCDs.csv | CSV | utf-8 | 95 | 5 | 0 | 0 | Yes | No |
| CMS_Other_Coding_Information_All_Articles.csv | CSV | utf-8 | 1221 | 6 | 0 | 0 | Yes | No |
| article_bill_codes.csv | CSV | utf-8 | 1376 | 7 | 0 | 0 | No | No |
| article_related_lcds.csv | CSV | utf-8 | 856 | 10 | 7 | 0 | No | No |
| article_related_ncd_documents_data.csv | CSV | utf-8 | 2515 | 8 | 8 | 0 | No | No |
| articles_700.csv | CSV | utf-8 | 700 | 39 | 0 | 0 | Yes | No |
| cms_article_jurisdiction.csv.xls | CSV | utf-8 | 258 | 5 | 0 | 0 | No | No |
| cms_lcd_primary_jurisdiction.csv.xls | CSV | utf-8 | 240 | 5 | 0 | 0 | No | No |
| icd10_covered_all_articles.csv | CSV | utf-8 | 226419 | 10 | 6 | 0 | No | No |
| icd10_noncovered_all_articles.csv | CSV | utf-8 | 24449 | 9 | 4 | 0 | No | No |
| icd10_pcs_codes.csv | CSV | utf-8 | 259 | 9 | 0 | 0 | No | No |
| icd10cm_tabular_2027.pdf | PDF | binary | 2075 | 1 | 0 | 0 | No | No |
| lcd_article_relationship.csv | CSV | utf-8 | 2172 | 6 | 0 | 0 | No | No |
| lcd_contractor.csv | CSV | utf-8 | 13968 | 6 | 0 | 0 | No | No |
| lcd_documents.csv | CSV | utf-8 | 975 | 12 | 0 | 0 | No | No |
| lcd_full_data.csv | CSV | utf-8 | 975 | 48 | 0 | 0 | Yes | No |
| lcd_master_excel_safe.csv.xlsx | Excel | binary | 1002 | 10 | 1 | 0 | No | No |
| lcd_related_documents.csv | CSV | utf-8 | 1805 | 10 | 0 | 0 | No | No |
| lcd_related_ncd_documents.csv | CSV | utf-8 | 1553 | 8 | 0 | 0 | No | No |
| lcd_revision_history.csv | CSV | utf-8 | 7987 | 6 | 0 | 0 | No | No |
| ncd_documents_data.csv | CSV | utf-8 | 357 | 19 | 0 | 0 | Yes | No |
| revenue_codes.csv | CSV | utf-8 | 356 | 7 | 0 | 0 | No | No |

## Detailed Dataset Schemas

### CMS_HCPCS_Code_Groups_All_Articles.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 1945 rows, 5 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| article_id | int64 | 0 |
| article_version | int64 | 0 |
| hcpc_code_group | int64 | 0 |
| paragraph | object | 630 |
| last_updated | object | 0 |

#### Sample Values:
- **article_id**: `['58679', '58679', '58679']`
- **article_version**: `['38', '38', '38']`
- **hcpc_code_group**: `['1', '2', '3']`
- **paragraph**: `['&lt;p&gt;Single genes and solid tumor panels&lt;&sol;p&gt;', '&lt;p&gt;Hematologic neoplasm panels&lt;&sol;p&gt;', '&lt;p&gt;&lt;!&amp;mdash;&amp;mdash;&amp;mdash;&amp;mdash;StartFragment &amp;mdash;&amp;mdash;&amp;mdash;&amp;mdash;&gt;&lt;&sol;p&gt;\n&lt;p class=&quot;pf0&quot;&gt;&lt;span class=&quot;cf0&quot;&gt;These code(s) are non-covered.&lt;&sol;span&gt;&lt;&sol;p&gt;\n&lt;p&gt;&lt;!&amp;mdash;&amp;mdash;&amp;mdash;&amp;mdash;EndFragment &amp;mdash;&amp;mdash;&amp;mdash;&amp;mdash;&gt;&lt;&sol;p&gt;']`
- **last_updated**: `['08/07/2026', '08/07/2026', '08/07/2026']`

---

### CMS_HCPCS_Modifier_Groups_All_Articles.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 1286 rows, 5 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| article_id | int64 | 0 |
| article_version | int64 | 0 |
| hcpc_modifier_group | int64 | 0 |
| paragraph | object | 902 |
| last_updated | object | 0 |

#### Sample Values:
- **article_id**: `['58679', '60377', '60375']`
- **article_version**: `['38', '5', '5']`
- **hcpc_modifier_group**: `['1', '1', '1']`
- **paragraph**: `['&lt;p&gt;N&sol;A&lt;&sol;p&gt;', '&lt;p&gt;N&sol;A&lt;&sol;p&gt;', '&lt;p&gt;N&sol;A&lt;&sol;p&gt;']`
- **last_updated**: `['08/07/2026', '08/06/2026', '08/06/2026']`

---

### CMS_HCPCS_Modifiers_All_Articles.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 579 rows, 7 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| article_id | int64 | 0 |
| article_version | int64 | 0 |
| hcpc_modifier_code_id | object | 0 |
| hcpc_modifier_code_version | int64 | 0 |
| hcpc_modifier_group | int64 | 0 |
| description | object | 0 |
| last_updated | object | 0 |

#### Sample Values:
- **article_id**: `['58565', '58565', '58565']`
- **article_version**: `['52', '52', '52']`
- **hcpc_modifier_code_id**: `['59', 'F1', 'F2']`
- **hcpc_modifier_code_version**: `['16', '16', '16']`
- **hcpc_modifier_group**: `['1', '1', '1']`

---

### CMS_HCPC_code.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 14098 rows, 9 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| article_id | int64 | 0 |
| article_version | int64 | 0 |
| hcpc_code_id | object | 0 |
| hcpc_code_version | int64 | 0 |
| hcpc_code_group | int64 | 0 |
| long_description | object | 0 |
| short_description | object | 0 |
| range | object | 0 |
| last_updated | object | 0 |

#### Sample Values:
- **article_id**: `['58679', '58679', '58679']`
- **article_version**: `['38', '38', '38']`
- **hcpc_code_id**: `['81202', '81215', '81217']`
- **hcpc_code_version**: `['102', '102', '102']`
- **hcpc_code_group**: `['1', '1', '1']`

---

### CMS_LCD_HCPCS_All_LCDs (1).csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 1910 rows, 9 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| lcd_id | int64 | 0 |
| lcd_version | int64 | 0 |
| hcpc_code_id | object | 0 |
| hcpc_code_version | int64 | 0 |
| hcpc_code_group | int64 | 0 |
| long_description | object | 0 |
| short_description | object | 0 |
| range | object | 0 |
| last_updated | object | 0 |

#### Sample Values:
- **lcd_id**: `['33610', '33610', '33610']`
- **lcd_version**: `['70', '70', '70']`
- **hcpc_code_id**: `['A4223', 'J1459', 'J1552']`
- **hcpc_code_version**: `['102', '102', '102']`
- **hcpc_code_group**: `['1', '1', '1']`

---

### CMS_LCD_HCPCS_Code_Groups_All_LCDs.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 95 rows, 5 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| lcd_id | int64 | 0 |
| lcd_version | int64 | 0 |
| hcpc_code_group | int64 | 0 |
| paragraph | object | 0 |
| last_updated | object | 0 |

#### Sample Values:
- **lcd_id**: `['33610', '33794', '33794']`
- **lcd_version**: `['70', '171', '171']`
- **hcpc_code_group**: `['1', '1', '2']`
- **paragraph**: `['&lt;p&gt;EY - No physician or other licensed health care provider order for this item or service&lt;br &sol;&gt;&lt;br &sol;&gt;JW - Drug amount discarded&sol;not administered to any patient&lt;&sol;p&gt;\n&lt;p&gt;JZ - Zero drug amount discarded&sol;not administered to any patient&lt;br &sol;&gt;&lt;br &sol;&gt;HCPCS CODES:&lt;br &sol;&gt;&lt;br &sol;&gt;&lt;&sol;p&gt;', '&lt;p&gt;The appearance of a code in this section does not necessarily indicate coverage.&lt;&sol;p&gt;\n&lt;p&gt;&lt;strong&gt;HCPCS MODIFIERS:&lt;&sol;strong&gt;&lt;&sol;p&gt;\n&lt;p&gt;EY &amp;ndash; No physician or other licensed health care provider order for this item or service&lt;&sol;p&gt;\n&lt;p&gt;GA &amp;ndash; Waiver of liability statement issued as required by payer policy, individual case&lt;&sol;p&gt;\n&lt;p&gt;GY - Item or service statutorily excluded or does not meet the definition of any Medicare benefit&lt;&sol;p&gt;\n&lt;p&gt;GZ &amp;ndash; Item or service expected to be denied as not reasonable and necessary&lt;&sol;p&gt;\n&lt;p&gt;JB - Administered Subcutaneously&lt;&sol;p&gt;\n&lt;p style=&quot;line-height: normal;&quot;&gt;JK - One month supply or less of drug or biological&lt;&sol;p&gt;\n&lt;p style=&quot;line-height: normal;&quot;&gt;JL - Three month supply of drug or biological&lt;&sol;p&gt;\n&lt;p&gt;JW - Drug amount discarded&sol;not administered to any patient&lt;&sol;p&gt;\n&lt;p&gt;JZ - Zero drug amount discarded&sol;not administered to any patient&lt;&sol;p&gt;\n&lt;p&gt;KX - Requirements specified in the medical policy have been met&lt;&sol;p&gt;\n&lt;p&gt;&lt;strong&gt;HCPCS CODES:&lt;&sol;strong&gt;&lt;&sol;p&gt;\n&lt;p&gt;&lt;strong&gt;EQUIPMENT&lt;&sol;strong&gt;&lt;&sol;p&gt;', '&lt;p&gt;SUPPLIES&lt;&sol;p&gt;']`
- **last_updated**: `['06/19/2026', '06/19/2026', '06/19/2026']`

---

### CMS_Other_Coding_Information_All_Articles.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 1221 rows, 6 columns
- **Candidate Keys**: `['article_id']`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| article_id | int64 | 0 |
| article_version | int64 | 0 |
| other_coding_group | int64 | 0 |
| paragraph | object | 943 |
| codes | object | 1220 |
| last_updated | object | 0 |

#### Sample Values:
- **article_id**: `['58679', '60377', '60375']`
- **article_version**: `['38', '5', '5']`
- **other_coding_group**: `['1', '1', '1']`
- **paragraph**: `['&lt;p&gt;N&sol;A&lt;&sol;p&gt;', '&lt;p&gt;N&sol;A&lt;&sol;p&gt;', '&lt;p&gt;N&sol;A&lt;&sol;p&gt;']`
- **codes**: `['5A02116\n5A0211D\n5A02216\n5A0221D']`

---

### article_bill_codes.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 1376 rows, 7 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| article_id | int64 | 0 |
| article_version | int64 | 0 |
| bill_code_id | int64 | 0 |
| bill_code_version | int64 | 0 |
| description | object | 0 |
| last_updated | object | 0 |
| source_article_id | int64 | 0 |

#### Sample Values:
- **article_id**: `['57414', '57424', '57361']`
- **article_version**: `['30', '14', '46']`
- **bill_code_id**: `['999', '0', '999']`
- **bill_code_version**: `['7', '7', '7']`
- **description**: `['Not Applicable', 'TBD', 'Not Applicable']`

---

### article_related_lcds.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 856 rows, 10 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| article_id | int64 | 0 |
| article_version | int64 | 0 |
| last_updated | object | 0 |
| r_article_id | float64 | 611 |
| r_article_version | float64 | 611 |
| r_contractor_id | int64 | 0 |
| r_lcd_id | float64 | 245 |
| r_lcd_version | float64 | 245 |
| related_num | int64 | 0 |
| url | object | 0 |

#### Sample Values:
- **article_id**: `['58679', '60523', '60377']`
- **article_version**: `['38', '3', '5']`
- **last_updated**: `['06/16/2022', '08/06/2026', '08/06/2026']`
- **r_article_id**: `['60390.0', '58903.0', '60151.0']`
- **r_article_version**: `['3.0', '6.0', '6.0']`

---

### article_related_ncd_documents_data.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 2515 rows, 8 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| article_id | int64 | 0 |
| article_version | int64 | 0 |
| last_updated | object | 0 |
| r_ncd_id | int64 | 0 |
| r_ncd_version | int64 | 0 |
| related_num | int64 | 0 |
| source_article_id | int64 | 0 |
| url | object | 0 |

#### Sample Values:
- **article_id**: `['58679', '57435', '60523']`
- **article_version**: `['38', '27', '3']`
- **last_updated**: `['04/29/2025', '12/18/2025', '08/06/2026']`
- **r_ncd_id**: `['372', '0', '0']`
- **r_ncd_version**: `['1', '1', '1']`

---

### articles_700.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 700 rows, 39 columns
- **Candidate Keys**: `['url']`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| document_id | int64 | 0 |
| document_version | int64 | 0 |
| document_display_id | object | 0 |
| document_type | object | 0 |
| note | object | 566 |
| title | object | 0 |
| contractor_name_type | object | 0 |
| updated_on | object | 0 |
| updated_on_sort | int64 | 0 |
| effective_date | object | 0 |
| retirement_date | object | 586 |
| url | object | 0 |
| article_id | int64 | 0 |
| article_version | int64 | 0 |
| article_type | int64 | 0 |
| article_type_description | object | 0 |
| article_pub_date | object | 0 |
| article_eff_date | object | 74 |
| article_end_date | object | 586 |
| description | object | 0 |
| other_comments | float64 | 700 |
| sad_url | object | 2 |
| thirty_percent | object | 0 |
| status | object | 0 |
| last_updated | object | 0 |
| history_exp | object | 586 |
| key_article | object | 115 |
| icd9_covered_para | float64 | 700 |
| icd9_noncovered_para | float64 | 700 |
| revenue_para | object | 488 |
| article_rev_end_date | object | 591 |
| source_article_id | float64 | 595 |
| date_retired | object | 586 |
| keywords | object | 541 |
| icd10_doc | object | 0 |
| add_icd10_info | object | 516 |
| cms_cov_policy | object | 255 |
| display_id | float64 | 700 |
| reference_article | object | 22 |

#### Sample Values:
- **document_id**: `['60513', '58679', '60523']`
- **document_version**: `['3', '38', '3']`
- **document_display_id**: `['A60513', 'A58679', 'A60523']`
- **document_type**: `['Article', 'Article', 'Article']`
- **note**: `['Future', 'Future', 'Future']`

---

### cms_article_jurisdiction.csv.xls
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 258 rows, 5 columns
- **Candidate Keys**: `['article_id + article_version + state_id']`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| article_id | int64 | 0 |
| article_version | int64 | 0 |
| state_id | int64 | 0 |
| last_updated | object | 0 |
| state_name | object | 0 |

#### Sample Values:
- **article_id**: `['57311', '57311', '57311']`
- **article_version**: `['35', '35', '35']`
- **state_id**: `['8', '11', '10']`
- **last_updated**: `['07/27/2026', '07/27/2026', '07/27/2026']`
- **state_name**: `['Colorado', 'Delaware', 'District of Columbia']`

---

### cms_lcd_primary_jurisdiction.csv.xls
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 240 rows, 5 columns
- **Candidate Keys**: `['lcd_id + lcd_version + state_id']`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| lcd_id | int64 | 0 |
| lcd_version | int64 | 0 |
| state_id | int64 | 0 |
| state_name | object | 0 |
| last_updated | object | 0 |

#### Sample Values:
- **lcd_id**: `['33942', '33942', '33942']`
- **lcd_version**: `['50', '50', '50']`
- **state_id**: `['8', '11', '10']`
- **state_name**: `['Colorado', 'Delaware', 'District of Columbia']`
- **last_updated**: `['07/27/2026', '07/27/2026', '07/27/2026']`

---

### icd10_covered_all_articles.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 226419 rows, 10 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| article_id | int64 | 0 |
| article_version | int64 | 0 |
| icd10_code_id | object | 0 |
| icd10_code_version | int64 | 0 |
| icd10_covered_group | int64 | 0 |
| range | object | 0 |
| sort_order | int64 | 0 |
| description | object | 0 |
| asterisk | object | 0 |
| last_updated | object | 0 |

#### Sample Values:
- **article_id**: `['58679', '58679', '58679']`
- **article_version**: `['38', '38', '38']`
- **icd10_code_id**: `['C00.0', 'C00.1', 'C00.2']`
- **icd10_code_version**: `['18', '18', '18']`
- **icd10_covered_group**: `['1', '1', '1']`

---

### icd10_noncovered_all_articles.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 24449 rows, 9 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| article_id | int64 | 0 |
| article_version | int64 | 0 |
| icd10_code_id | object | 0 |
| icd10_code_version | int64 | 0 |
| icd10_noncovered_group | int64 | 0 |
| range | object | 0 |
| sort_order | int64 | 0 |
| description | object | 0 |
| last_updated | object | 0 |

#### Sample Values:
- **article_id**: `['60155', '60155', '60155']`
- **article_version**: `['6', '6', '6']`
- **icd10_code_id**: `['N17.0', 'N17.1', 'N17.2']`
- **icd10_code_version**: `['17', '17', '17']`
- **icd10_noncovered_group**: `['1', '1', '1']`

---

### icd10_pcs_codes.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 259 rows, 9 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| article_id | object | 0 |
| article_version | object | 0 |
| description | object | 0 |
| icd10_pcs_group | object | 0 |
| icd10_pcs_code | object | 0 |
| range | object | 0 |
| last_updated | object | 0 |
| asterisk | object | 0 |
| icd10_pcs_code_id | object | 0 |

#### Sample Values:
- **article_id**: `['59723', '59723', '59723']`
- **article_version**: `['10', '10', '10']`
- **description**: `['Crisis Intervention', 'Individual Psychotherapy, Interactive', 'Individual Psychotherapy, Behavioral']`
- **icd10_pcs_group**: `['1', '1', '1']`
- **icd10_pcs_code**: `['GZ2ZZZZ', 'GZ50ZZZ', 'GZ51ZZZ']`

---

### icd10cm_tabular_2027.pdf
- **Physical Format**: PDF
- **Encoding**: binary
- **Row/Column Counts**: 2075 rows, 1 columns
- **Candidate Keys**: `['Page Number']`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| Page Content | string | 0 |

#### Sample Values:
- **Page Content**: `PDF Tabular Reference Document`

---

### lcd_article_relationship.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 2172 rows, 6 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| lcd_id | int64 | 0 |
| lcd_version | int64 | 0 |
| article_id | int64 | 0 |
| article_version | int64 | 0 |
| contractor_id | int64 | 0 |
| last_updated | object | 0 |

#### Sample Values:
- **lcd_id**: `['32553', '33252', '33252']`
- **lcd_version**: `['21', '29', '29']`
- **article_id**: `['56424', '57520', '58257']`
- **article_version**: `['20', '43', '3']`
- **contractor_id**: `['228', '368', '368']`

---

### lcd_contractor.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 13968 rows, 6 columns
- **Candidate Keys**: `['lcd_id + lcd_version + contractor_id']`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| lcd_id | int64 | 0 |
| lcd_version | int64 | 0 |
| contractor_id | int64 | 0 |
| contractor_type_id | int64 | 0 |
| contractor_version | int64 | 0 |
| last_updated | object | 0 |

#### Sample Values:
- **lcd_id**: `['32553', '32553', '32553']`
- **lcd_version**: `['21', '21', '21']`
- **contractor_id**: `['239', '228', '240']`
- **contractor_type_id**: `['8', '9', '8']`
- **contractor_version**: `['1', '2', '1']`

---

### lcd_documents.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 975 rows, 12 columns
- **Candidate Keys**: `['url']`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| contractor_name_type | object | 0 |
| document_display_id | object | 0 |
| document_id | int64 | 0 |
| document_type | object | 0 |
| document_version | int64 | 0 |
| effective_date | object | 0 |
| note | object | 830 |
| retirement_date | object | 855 |
| title | object | 0 |
| updated_on | object | 0 |
| updated_on_sort | int64 | 0 |
| url | object | 0 |

#### Sample Values:
- **contractor_name_type**: `['Wellpoint Federal\r\n(MAC - Part A, MAC - Part B)', 'Palmetto GBA\r\n(MAC - Part A, MAC - Part B)', 'Palmetto GBA\r\n(MAC - Part A, MAC - Part B)']`
- **document_display_id**: `['L40330', 'L40328', 'L38026']`
- **document_id**: `['40330', '40328', '38026']`
- **document_type**: `['LCD', 'LCD', 'LCD']`
- **document_version**: `['6', '5', '30']`

---

### lcd_full_data.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 975 rows, 48 columns
- **Candidate Keys**: `['lcd_id + lcd_version']`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| lcd_id | int64 | 0 |
| lcd_version | int64 | 0 |
| display_id | float64 | 975 |
| title | object | 0 |
| determination_number | float64 | 975 |
| cms_cov_policy | object | 25 |
| orig_det_eff_date | object | 0 |
| ent_det_end_date | object | 855 |
| rev_eff_date | object | 80 |
| rev_end_date | object | 863 |
| indication | object | 0 |
| diagnoses_support | float64 | 975 |
| icd9_dont_support_para | float64 | 975 |
| icd9_dont_support_ast | float64 | 975 |
| diagnoses_dont_support | float64 | 975 |
| coding_guidelines | float64 | 975 |
| doc_reqs | float64 | 975 |
| appendices | float64 | 975 |
| util_guide | float64 | 975 |
| source_info | object | 302 |
| adv_meeting | float64 | 975 |
| comment_start_dt | float64 | 975 |
| comment_end_dt | float64 | 975 |
| notice_start_dt | object | 246 |
| rev_hist_num | float64 | 975 |
| history_exp | object | 855 |
| last_reviewed_on | object | 182 |
| thirty_percent | object | 0 |
| status | object | 0 |
| last_updated | object | 0 |
| draft_contact | float64 | 975 |
| revenue_para | float64 | 975 |
| source_lcd_id | float64 | 600 |
| add_icd10_info | float64 | 975 |
| keywords | object | 660 |
| associated_info | object | 279 |
| notice_end_dt | object | 241 |
| date_retired | object | 855 |
| draft_released_date | float64 | 975 |
| icd10_doc | object | 0 |
| synopsis_changes | float64 | 975 |
| bibliography | object | 0 |
| summary_of_evidence | object | 0 |
| analysis_of_evidence | object | 0 |
| mcd_publish_date | float64 | 975 |
| issue | object | 214 |
| issue_change | object | 717 |
| mac_initiated | object | 0 |

#### Sample Values:
- **lcd_id**: `['40330', '40328', '38026']`
- **lcd_version**: `['6', '5', '30']`
- **display_id**: `[]`
- **title**: `['Allergy Diagnostic Testing', 'Allergy Diagnostic Testing', 'Corneal Hysteresis']`
- **determination_number**: `[]`

---

### lcd_master_excel_safe.csv.xlsx
- **Physical Format**: Excel
- **Encoding**: binary
- **Row/Column Counts**: 1002 rows, 10 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| lcd_id | object | 2 |
| lcd_version | object | 1 |
| display_id | object | 1 |
| title | object | 1 |
| cms_cov_policy | object | 32 |
| indication | object | 21 |
| orig_det_eff_date | object | 53 |
| rev_eff_date | object | 134 |
| last_updated | object | 54 |
| keywords | object | 698 |

#### Sample Values:
- **lcd_id**: `['32553', '33252', '33261']`
- **lcd_version**: `['21', '29', '40']`
- **display_id**: `['L32553', 'L33252', 'L33261']`
- **title**: `['Allergy Immunotherapy', 'Psychiatric Diagnostic Evaluation and Psychotherapy Services', 'Allergy Testing']`
- **cms_cov_policy**: `['Language quoted from Centers for Medicare and Medicaid Services (CMS), National Coverage Determinations (NCDs) and coverage provisions in interpretive manuals is italicized throughout the policy. NCDs and coverage provisions in interpretive manuals are not subject to the Local Coverage Determination (LCD) Review Process (42 CFR 405.860[b] and 42 CFR 426 [Subpart D]). In addition, an administrative law judge may not review an NCD. See Section 1869(f)(1)(A)(i) of the Social Security Act.\n\nUnless otherwise specified, italicized text represents quotation from one or more of the following CMS sources:\n\nTitle XVIII of the Social Security Act (SSA):\n\nSection 1862(a)(1)(A) excludes expenses incurred for items or services which are not reasonable and necessary for the diagnosis or treatment of illness or injury or to improve the functioning of a malformed body member.\n\nSection 1833(e) prohibits Medicare payment for any claim which lacks the necessary information to process the claim.\n\nCMS Publications:\n\nCMS Publication 100-02, Medicare Benefit Manual, Chapter 15: Section\n\n20.2 Physician Expense for Allergy Treatment\n\nCMS Publication 100-02, Medicare Benefit Manual, Chapter 15: Section\n\n50.4.4.1 Payment for Antigens\n\nCMS Publication 100-03, Medicare National Coverage Decisions Manual, Chapter 1:\n\n110.9 Antigens Prepared for Sublingual Administration\n\nCMS Publication 100-03, Medicare National Coverage Decisions Manual, Chapter 1:\n\n110.11 Food Allergy Testing and Treatment\nCMS Publication 100-04, Medicare Claims Processing Manual, Chapter 12\n\n200 Allergy Testing and Immunotherapy\nCMS Transmittal No. 1770, Publication 100 â€“ 04, Medicare Claims Processing Manual, Change Request #6520, July 10, 2009, Medicare contractor annual update of the international classification of diseases, ninth revision, clinical modification (ICD-9-CM).', 'This LCD supplements but does not replace, modify or supersede existing Medicare applicable National Coverage Determinations (NCDs) or payment policy rules and regulations for Psychiatric Diagnostic Evaluation and Psychotherapy Services. Federal statute and subsequent Medicare regulations regarding provision and payment for medical services are lengthy. They are not repeated in this LCD. Neither Medicare payment policy rules nor this LCD replace, modify or supersede applicable state statutes regarding medical practice or other health practice professions acts, definitions and/or scopes of practice. All providers who report services for Medicare payment must fully understand and follow all existing laws, regulations and rules for Medicare payment for Psychiatric Diagnostic Evaluation and Psychotherapy Services and must properly submit only valid claims for them. Please review and understand them and apply the medical necessity provisions in the policy within the context of the manual rules. Relevant CMS manual instructions and policies may be found in the following Internet-Only Manuals (IOMs) published on the CMS Web site.\n\nInternet Only Manual (IOM) Citations:\n\nCMS IOM Publication 100-01, Medicare General Information, Eligibility and Entitlement Manual,\n\nChapter 3, Section 30 Outpatient Mental Health Treatment Limitation\n\nCMS IOM Publication 100-02, Medicare Claims Processing Manual,\n\nChapter 15, Section 40.4 Definition of Physician/Practitioner, Section 60 Services and Supplies Furnished Incident To a Physicianâ€™s/NPPâ€™s Professional Service, and Section 160 Clinical Psychologist Services\n\nCMS IOM Publication 100-04, Medicare Claims Processing Manual,\n\nChapter 12, Section 120 Nurse Practitioner(NP) And Clinical Nurse Specialist (CNS) Services Payment Methodology, Section 120.2 Outpatient Mental Health Treatment Limitation, Section 120.3 NP and CNS Billing to the A/B MAC (b), Section 160 Independent Psychologist Services, Section 170 Clinical Psychologist Services, Section 210 Outpatient Mental Health Treatment Limitation, and Section 210.1 Application of the Limitation\n\nCMS IOM Publication 100-08, Medicare Program Integrity Manual,\n\nChapter 3, Section 3.3.2.6 Psychotherapy Notes\n\nChapter 13, Section 13.5.4 Reasonable and Necessary Provision in an LCD\n\nSocial Security Act (Title XVIII) Standard References:\n\nTitle XVIII of the Social Security Act, Section 1862(a)(1)(A) states that no Medicare payment shall be made for items or services which are not reasonable and necessary for the diagnosis or treatment of illness or injury.\n\nTitle XVIII of the Social Security Act, Section 1862(a)(7). This section excludes routine physical examinations.\n\nTitle XVIII of the Social Security Act, Section 1833(e) states that no payment shall be made to any provider for any claim that lacks the necessary information to process the claim.\n\nFederal Register References:\n\nCode of Federal Regulations (CFR), Title 45, Volume 1, Subpart E Privacy of Individually Identifiable Health Information, Part 164.501 Definitions.', 'This LCD supplements but does not replace, modify or supersede existing Medicare applicable National Coverage Determinations (NCDs) or payment policy rules and regulations for allergy testing services. Federal statute and subsequent Medicare regulations regarding provision and payment for medical services are lengthy. They are not repeated in this LCD. Neither Medicare payment policy rules nor this LCD replace, modify or supersede applicable state statutes regarding medical practice or other health practice professions acts, definitions and/or scopes of practice. All providers who report services for Medicare payment must fully understand and follow all existing laws, regulations and rules for Medicare payment for allergy testing services and must properly submit only valid claims for them. Please review and understand them and apply the medical necessity provisions in the policy within the context of the manual rules. Relevant CMS manual instructions and policies may be found in the following Internet-Only Manuals (IOMs) published on the CMS Web site.\n\nIOM Citations:\n\nCMS IOM Publication 100-02, Medicare Benefit Policy Manual,\n\nChapter 15, Sections 20.2 Physician Expense for Allergy Treatment and 50.4.4.1 Antigens\n\nCMS IOM Publication 100-03, Medicare National Coverage Determinations (NCD) Manual,\n\nChapter 1, Part 2, Sections 110.11 Food Allergy Testing and Treatment, 110.12 Challenge Ingestion Food Testing, and 110.13 Cytotoxic Food Tests\n\nChapter 1, Part 4, Section 230.10 Incontinence Control Devices\n\nCMS IOM Publication 100-08, Medicare Program Integrity Manual,\n\nChapter 13, Section 13.5.4 Reasonable and Necessary Provisions in LCDs\n\nSocial Security Act (Title XVIII) Standard References:\n\nTitle XVIII of the Social Security Act, Section 1862(a)(1)(A) states that no Medicare payment shall be made for items or services which are not reasonable and necessary for the diagnosis or treatment of illness or injury.\n\nTitle XVIII of the Social Security Act, Section 1862(a)(7). This section excludes routine physical examinations.']`

---

### lcd_related_documents.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 1805 rows, 10 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| last_updated | object | 0 |
| lcd_id | int64 | 0 |
| lcd_version | int64 | 0 |
| r_article_id | float64 | 399 |
| r_article_version | float64 | 399 |
| r_contractor_id | int64 | 0 |
| r_lcd_id | float64 | 1406 |
| r_lcd_version | float64 | 1406 |
| related_num | int64 | 0 |
| url | object | 0 |

#### Sample Values:
- **last_updated**: `['08/06/2026', '08/06/2026', '08/06/2026']`
- **lcd_id**: `['40330', '40330', '40328']`
- **lcd_version**: `['6', '6', '5']`
- **r_article_id**: `['60377.0', '60523.0', '60375.0']`
- **r_article_version**: `['5.0', '3.0', '5.0']`

---

### lcd_related_ncd_documents.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 1553 rows, 8 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| last_updated | object | 0 |
| lcd_id | int64 | 0 |
| lcd_version | int64 | 0 |
| r_ncd_id | int64 | 0 |
| r_ncd_version | int64 | 0 |
| related_num | int64 | 0 |
| source_lcd_id | int64 | 0 |
| url | object | 0 |

#### Sample Values:
- **last_updated**: `['04/29/2025', '04/29/2025', '04/29/2025']`
- **lcd_id**: `['38926', '38926', '38926']`
- **lcd_version**: `['23', '23', '23']`
- **r_ncd_id**: `['60', '213', '9']`
- **r_ncd_version**: `['1', '1', '1']`

---

### lcd_revision_history.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 7987 rows, 6 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| lcd_id | int64 | 0 |
| lcd_version | int64 | 0 |
| rev_hist_num | int64 | 0 |
| rev_hist_date | object | 0 |
| rev_hist_exp | object | 2 |
| last_updated | object | 0 |

#### Sample Values:
- **lcd_id**: `['32553', '32553', '32553']`
- **lcd_version**: `['21', '21', '21']`
- **rev_hist_num**: `['17', '16', '15']`
- **rev_hist_date**: `['10/25/2025', '11/07/2024', '11/02/2023']`
- **rev_hist_exp**: `['This policy is being replaced with new policy L40056 Allergen Immunotherapy (AIT) with Subcutaneous Immunotherapy (SCIT) that became effective 10/26/2025.', 'R16\nRevision Effective: 11/07/2024\nRevision Explanation: Annual review, no changes were made.\n\n10/29/2024: At this time 21st Century Cures Act will apply to new and revised LCDs that restrict coverage which requires comment and notice. This revision is not a restriction to the coverage determination; and, therefore not all the fields included on the LCD are applicable as noted in this policy.', 'R15\nRevision Effective: 11/02/2023\nRevision Explanation: Annual review, no changes were made.\n\n10/27/2023: At this time 21st Century Cures Act will apply to new and revised LCDs that restrict coverage which requires comment and notice. This revision is not a restriction to the coverage determination; and, therefore not all the fields included on the LCD are applicable as noted in this policy.']`

---

### ncd_documents_data.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 357 rows, 19 columns
- **Candidate Keys**: `['document_display_id', 'document_id', 'title']`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| ama_statement | float64 | 357 |
| benefit_category | object | 0 |
| cross_reference | object | 242 |
| document_display_id | object | 0 |
| document_id | int64 | 0 |
| document_version | int64 | 0 |
| effective_date | object | 0 |
| effective_end_date | object | 345 |
| implementation_date | object | 139 |
| indications_limitations | object | 1 |
| item_service_description | object | 112 |
| other_text | object | 334 |
| publication_number | object | 0 |
| qr_modifier_date | float64 | 357 |
| reasons_for_denial | float64 | 357 |
| revision_history | object | 102 |
| title | object | 0 |
| transmittal_number | float64 | 96 |
| transmittal_url | object | 147 |

#### Sample Values:
- **ama_statement**: `[]`
- **benefit_category**: `["Physicians' Services", 'No Benefit Category', "Physicians' Services"]`
- **cross_reference**: `['See the &lt;a href=&quot;https:&sol;&sol;www.cms.gov&sol;Regulations-and-Guidance&sol;Guidance&sol;Manuals&sol;Internet-Only-Manuals-IOMs-Items&sol;CMS012673&quot;&gt;Medicare Benefit Policy Manual&lt;&sol;a&gt;, Chapter 16, &#167;120.', 'See the &lt;a href=&quot;https:&sol;&sol;www.cms.gov&sol;Regulations-and-Guidance&sol;Guidance&sol;Manuals&sol;Internet-Only-Manuals-IOMs-Items&sol;CMS012673&quot;&gt;Medicare Benefit Policy Manual&lt;&sol;a&gt;, Chapter 6 &#167;20, Chapter 7 &#167;20, Chapter 8 &#167;50, and Chapter 15 &#167;60.2.', '&lt;p&gt;The &lt;a href=&quot;https:&sol;&sol;www.cms.gov&sol;Regulations-and-Guidance&sol;Guidance&sol;Manuals&sol;Internet-Only-Manuals-IOMs-Items&sol;CMS012673&quot;&gt;Medicare Benefit Policy Manual&lt;&sol;a&gt;, Chapter 6, “Hospital Services Covered Under Part B,”&#167;20.&lt;br&gt;\r\nThe &lt;a href=&quot;https:&sol;&sol;www.cms.gov&sol;Regulations-and-Guidance&sol;Guidance&sol;Manuals&sol;Internet-Only-Manuals-IOMs-Items&sol;CMS018912&quot;&gt;Medicare Claims Processing Manual&lt;&sol;a&gt;, Chapter 12, “Physician&sol;Practitioner Billing,” &#167;10.&lt;br&gt;\r\nThe &lt;a href=&quot;https:&sol;&sol;www.cms.gov&sol;Regulations-and-Guidance&sol;Guidance&sol;Manuals&sol;Internet-Only-Manuals-IOMs-Items&sol;CMS050111&quot;&gt;Medicare General Information, Eligibility, and Entitlement Manual&lt;&sol;a&gt;, Chapter 3, “Deductibles, Coinsurance Amounts, and Payment Limitations,” &#167;30.&lt;&sol;p&gt;']`
- **document_display_id**: `['50.8', '140.4', '150.7']`
- **document_id**: `['5', '14', '15']`

---

### revenue_codes.csv
- **Physical Format**: CSV
- **Encoding**: utf-8
- **Row/Column Counts**: 356 rows, 7 columns
- **Candidate Keys**: `[]`

#### Columns and Inferred Types:
| Column Name | Inferred Type | Null Count |
| --- | --- | --- |
| article_id | object | 0 |
| article_version | object | 0 |
| description | object | 0 |
| last_updated | object | 0 |
| range | object | 0 |
| revenue_code | object | 0 |
| revenue_code_id | object | 0 |

#### Sample Values:
- **article_id**: `['57071', '57071', '57071']`
- **article_version**: `['36', '36', '36']`
- **description**: `['Other Imaging Services - Other Imaging Services', 'Emergency Room - General Classification', 'Clinic - General Classification']`
- **last_updated**: `['05/29/2026', '05/29/2026', '05/29/2026']`
- **range**: `['N', 'N', 'X']`

---
