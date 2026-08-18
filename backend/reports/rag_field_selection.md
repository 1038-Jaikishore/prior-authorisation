# Volume 4 RAG Field Selection Map

This report outlines which fields from NCDs, LCDs, and Articles are selected for narrative vector embedding in RAG indexing.

## NCD Fields

| Field Name | Embed? | Reason |
| --- | --- | --- |
| `title` | **Yes** | Defines the specific scope and subject matter of the National Coverage Determination. |
| `indications_limitations` | **Yes** | Contains core clinical criteria, coverages, indications, and limitations rules for national coverage. |
| `item_service_description` | **Yes** | Narrative describing the medical device, diagnostic, or clinical service addressed. |
| `benefit_category` | **Yes** | Specifies under which Medicare benefit class the service is covered. |
| `transmittal_number` | No | Administrative revision tracking number; has no clinical or medical policy value. |
| `publication_number` | No | CMS manual publication number; administrative/citation metadata only. |

## LCD Fields

| Field Name | Embed? | Reason |
| --- | --- | --- |
| `title` | **Yes** | Primary identifier containing the service name and scope of local coverage. |
| `indication` | **Yes** | Contains vital narrative outlining active coverage indications, limitations, and medical necessity definitions. |
| `cms_cov_policy` | **Yes** | Detailed references and narrative on federal coverage requirements. |
| `coding_guidelines` | **Yes** | Clinical coding instructions and modifiers guidance for billing alignment. |
| `doc_reqs` | **Yes** | Narrative details on the medical record documentation required to support claims. |
| `diagnoses_support` | **Yes** | Descriptions of diagnosis/clinical findings support rules (if formatted as narrative). |
| `diagnoses_dont_support` | **Yes** | Descriptions of findings or diagnoses that do not support medical necessity. |
| `url` | No | Web reference; static link containing no narrative policy criteria. |
| `contractor_name_type` | No | Name of the MAC contractor; processed deterministically during geography routing. |

## Article Fields

| Field Name | Embed? | Reason |
| --- | --- | --- |
| `title` | **Yes** | Identifies the core billing or coding topic covered by the article. |
| `description` | **Yes** | Summary describing the clinical scope, coding changes, or billing clarifications. |
| `cms_cov_policy` | **Yes** | Narrative detailing related LCDs or statutory references for policy compliance. |
| `status` | No | Document state indicator (e.g. Active); resolved deterministically. |
