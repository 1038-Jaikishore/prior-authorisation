# U.S. CMS/Medicare Prior Authorization Decision-Support System

## Project Name
**cms-prior-auth**

## Purpose
This system is designed as a decision-support system to assist with **U.S. CMS/Medicare prior-authorization workflows**. It uses FastAPI, MongoDB Atlas, MongoDB Atlas Vector Search, React/TypeScript, and an LLM provider to evaluate prior-authorization requests against Medicare National Coverage Determinations (NCDs), Local Coverage Determinations (LCDs), and other CMS guidelines.

## Directory Structure & Locations
- **Backend**: Located in `backend/` (FastAPI-based Python application).
- **Frontend**: Located in `frontend/` (React/TypeScript application).
- **Documents & Volume Specifications**: Located in `docs/volumes/`.

## Data Management
- **Raw CMS Datasets**: Belong in `backend/data/cms_data/`. All files placed in this folder must be treated as **READ-ONLY** to preserve original datasets (e.g., the 27 reference CMS datasets).
- **Normalized/Preprocessed Data**: Generated and stored in `backend/data/normalized/`.
- **Audit Reports**: Generated and stored in `backend/reports/`.

## Development Roadmap
Development of this system will proceed **volume-by-volume** to ensure rigorous verification and validation of each component and compliance requirement.
