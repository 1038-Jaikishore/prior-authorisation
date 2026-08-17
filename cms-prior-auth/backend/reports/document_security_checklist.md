# Document Security & Safety Verification Checklist

This checklist documents the defensive design parameters, security controls, and audit trails implemented in the document intake service.

## 1. Directory Traversal & Filename Sanitization
* All incoming filenames are stripped of path traversal characters (`..`, `/`, `\`).
* Filenames are sanitized using regex to only contain alphanumeric characters, dots, underscores, and dashes.
* Files are stored in the server `data/uploads` folder using unique UUID prefixes (e.g. `DOC-XXXX_filename.pdf`) to prevent filename collision or directory injections.

## 2. MIME & Size Verification
* Allowed extensions are strictly white-listed in config settings (`allowed_document_types = "pdf,docx,txt"`).
* File size limits are validated before writing files to disk (`max_upload_mb = 10` MB).
* File MIME types are inspected on request upload.

## 3. Reviewer Confirmations & Version Locks
* All extracted clinical facts start as `DRAFT_EXTRACTION`.
* No extracted facts can enter the prior authorization evaluation pipeline until a reviewer manually confirms and locks the data (`CONFIRMED`).
* Any edit made by a reviewer generates an `EditHistoryEntry` containing original values, new values, reviewer ID, and timestamps, incrementing the document version number.

## 4. Safety & Leakage Protection
* **Label Leakage Protection**: Uploaded document texts are scanned and scrubbed of any pre-compiled outcome strings (like "Prior authorization approved" or "Coverage denied") to protect the evaluation pipeline from external decision bias.
* **API Secret Protection**: No server paths or file paths are returned in API response models. Local paths remain strictly restricted to server scopes.
