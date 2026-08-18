import os
from pymongo import MongoClient
from dotenv import load_dotenv

def inject_mock_policies():
    load_dotenv('.env')
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)
    db = client["cms_prior_auth"]

    print("Injecting Mock Oxygen, Asthma, Wheelchair Policies into MongoDB...")

    # 1. NCDs
    ncds = [
        {
            "ncd_id": {"canonical_value": "240.2", "display_value": "240.2"},
            "title": "Home Use of Oxygen",
            "status": "Active",
            "effective_date": "2000-01-01",
        },
        {
            "ncd_id": {"canonical_value": "PROS", "display_value": "PROS"},
            "title": "Prosthetic Devices",
            "effective_date": "2000-01-01",
        },
        {
            "ncd_id": {"canonical_value": "WHEEL", "display_value": "WHEEL"},
            "title": "Ultralight Wheelchairs",
            "effective_date": "2000-01-01",
        },
        {
            "ncd_id": {"canonical_value": "EXPERIMENTAL", "display_value": "EXPERIMENTAL"},
            "title": "Experimental Devices",
            "effective_date": "2000-01-01",
        },
        {
            "ncd_id": {"canonical_value": "ASTHMA", "display_value": "ASTHMA"},
            "title": "Nebulizers for Asthma",
            "effective_date": "2000-01-01",
        }
    ]
    for n in ncds:
        db.ncds.update_one({"ncd_id.canonical_value": n["ncd_id"]["canonical_value"]}, {"$set": n}, upsert=True)

    # 2. LCDs
    lcds = [
        {
            "lcd_id": {"canonical_value": "OXYGEN", "display_value": "L-OXYGEN"},
            "lcd_version": "1",
            "title": "Oxygen and Oxygen Equipment",
            "status": "Active",
            "effective_date": "2000-01-01",
        },
        {
            "lcd_id": {"canonical_value": "PROS", "display_value": "L-PROS"},
            "lcd_version": "1",
            "title": "Lower Limb Prostheses",
            "effective_date": "2000-01-01",
        },
        {
            "lcd_id": {"canonical_value": "WHEEL", "display_value": "L-WHEEL"},
            "lcd_version": "1",
            "title": "Wheelchair Seating",
            "effective_date": "2000-01-01",
        },
        {
            "lcd_id": {"canonical_value": "EXPERIMENTAL", "display_value": "L-EXPERIMENTAL"},
            "lcd_version": "1",
            "title": "Experimental Therapy",
            "effective_date": "2000-01-01",
        },
        {
            "lcd_id": {"canonical_value": "ASTHMA", "display_value": "L-ASTHMA"},
            "lcd_version": "1",
            "title": "Nebulizers",
            "effective_date": "2000-01-01",
        }
    ]
    for l in lcds:
        db.lcds.update_one({"lcd_id.canonical_value": l["lcd_id"]["canonical_value"]}, {"$set": l}, upsert=True)

    # 3. Articles
    articles = [
        {
            "article_id": {"canonical_value": "OXYGEN", "display_value": "A-OXYGEN"},
            "article_version": "1",
            "article_type": "Billing",
            "title": "Billing: Oxygen",
            "effective_date": "2000-01-01",
        },
        {
            "article_id": {"canonical_value": "PROS", "display_value": "A-PROS"},
            "article_version": "1",
            "article_type": "Billing",
            "title": "Billing: Prostheses",
            "effective_date": "2000-01-01",
        },
        {
            "article_id": {"canonical_value": "WHEEL", "display_value": "A-WHEEL"},
            "article_version": "1",
            "article_type": "Billing",
            "title": "Billing: Wheelchairs",
            "effective_date": "2000-01-01",
        },
        {
            "article_id": {"canonical_value": "EXPERIMENTAL", "display_value": "A-EXPERIMENTAL"},
            "article_version": "1",
            "article_type": "Billing",
            "title": "Billing: Experimental",
            "effective_date": "2000-01-01",
        },
        {
            "article_id": {"canonical_value": "ASTHMA", "display_value": "A-ASTHMA"},
            "article_version": "1",
            "article_type": "Billing",
            "title": "Billing: Nebulizers",
            "effective_date": "2000-01-01",
        }
    ]
    for a in articles:
        db.articles.update_one({"article_id.canonical_value": a["article_id"]["canonical_value"]}, {"$set": a}, upsert=True)

    # 4. HCPCS Mappings (lcd_hcpcs and article_hcpcs)
    hcpcs_mapping = {
        "OXYGEN": "E0424",
        "PROS": "L5613",
        "WHEEL": "K0005",
        "EXPERIMENTAL": "E9999",
        "ASTHMA": "E0570"
    }

    for numeric_id, hcpcs in hcpcs_mapping.items():
        # LCD HCPCS mapping
        db.lcd_hcpcs.update_one(
            {"lcd_id_numeric": numeric_id},
            {"$set": {"lcd_id_numeric": numeric_id, "hcpcs_code": {"canonical_value": hcpcs}}},
            upsert=True
        )
        # Article HCPCS mapping
        db.article_hcpcs.update_one(
            {"article_id_numeric": numeric_id},
            {"$set": {"article_id_numeric": numeric_id, "hcpcs_code": {"canonical_value": hcpcs}}},
            upsert=True
        )

    # 5. Relationships (LCD to NCD, Article to NCD, LCD to Article)
    ncd_mapping = {
        "OXYGEN": "240.2",
        "PROS": "PROS",
        "WHEEL": "WHEEL",
        "EXPERIMENTAL": "EXPERIMENTAL",
        "ASTHMA": "ASTHMA"
    }
    
    for numeric_id, ncd_id in ncd_mapping.items():
        # LCD -> NCD
        db.lcd_ncd_relationships.update_one(
            {"lcd_id_numeric": numeric_id},
            {"$set": {"lcd_id_numeric": numeric_id, "r_ncd_id": ncd_id}},
            upsert=True
        )
        # LCD -> Article
        db.lcd_article_relationships.update_one(
            {"lcd_id_numeric": numeric_id},
            {"$set": {"lcd_id_numeric": numeric_id, "article_id_numeric": numeric_id}},
            upsert=True
        )
        
    # 6. LCD Jurisdictions (for Geographic routing)
    for numeric_id in hcpcs_mapping.keys():
        db.lcd_jurisdictions.update_one(
            {"lcd_id_numeric": numeric_id, "state_name": "Texas"},
            {"$set": {"lcd_id_numeric": numeric_id, "state_name": "Texas", "contractor_id": "MOCK-MAC-TX"}},
            upsert=True
        )

    # 7. Policy Chunks
    chunks = [
        # OXYGEN (E0424)
        {"document_id": "240.2", "document_type": "NCD", "section": "indications", "text": "Stationary oxygen is covered for patients with severe hypoxemia documented by an ABG test."},
        {"document_id": "L-OXYGEN", "document_type": "LCD", "section": "indications", "text": "Patient must have tried conservative therapy."},
        {"document_id": "A-OXYGEN", "document_type": "ARTICLE", "section": "coding", "text": "R09.02 is an approved diagnosis code for E0424."},
        
        # PROSTHESIS (L5613)
        {"document_id": "PROS", "document_type": "NCD", "section": "indications", "text": "Prosthetics are covered for patients with amputations."},
        {"document_id": "L-PROS", "document_type": "LCD", "section": "indications", "text": "Coverage requires a detailed surgical report of the amputation date and outcome."},
        {"document_id": "A-PROS", "document_type": "ARTICLE", "section": "coding", "text": "Z89.419 is covered for L5613."},
        
        # WHEELCHAIR (K0005)
        {"document_id": "WHEEL", "document_type": "NCD", "section": "indications", "text": "Ultralight wheelchairs require a specialized PT/OT evaluation to prove the patient cannot use a standard wheelchair."},
        {"document_id": "L-WHEEL", "document_type": "LCD", "section": "indications", "text": "A standard wheelchair evaluation must have failed."},
        {"document_id": "A-WHEEL", "document_type": "ARTICLE", "section": "coding", "text": "G82.20 is a covered code for K0005."},
        
        # EXPERIMENTAL (E9999)
        {"document_id": "EXPERIMENTAL", "document_type": "NCD", "section": "indications", "text": "Coverage is considered on an individual basis by the medical director for rare and complex neurodegenerative presentations not otherwise specified."},
        {"document_id": "L-EXPERIMENTAL", "document_type": "LCD", "section": "indications", "text": "Experimental neural stimulators are evaluated individually due to clinical ambiguity."},
        {"document_id": "A-EXPERIMENTAL", "document_type": "ARTICLE", "section": "coding", "text": "E9999 can be billed for experimental devices under individual consideration."},
        
        # ASTHMA (E0570)
        {"document_id": "ASTHMA", "document_type": "NCD", "section": "indications", "text": "Standard nebulizers are covered for severe persistent asthma when the patient has failed standard inhaler therapies and spirometry confirms severity."},
        {"document_id": "L-ASTHMA", "document_type": "LCD", "section": "indications", "text": "Coverage requires documented spirometry and failure of inhalers."},
        {"document_id": "A-ASTHMA", "document_type": "ARTICLE", "section": "coding", "text": "E0570 is covered for severe persistent asthma. Diagnosis J45.50 is covered."},
    ]

    for chunk in chunks:
        db.policy_chunks.update_one(
            {"document_id": chunk["document_id"], "document_type": chunk["document_type"]},
            {"$set": chunk},
            upsert=True
        )

    print("Injection complete! The real PolicyRoutingService will now successfully resolve E0424 to Oxygen policies.")

if __name__ == "__main__":
    inject_mock_policies()
