import asyncio
from app.db.connection import db_connection

db_connection.connect()
db = db_connection.get_db()

db['policy_chunks'].update_one(
    {'document_id': 'A52514'},
    {'$set': {
        'text': 'This article provides billing and coding rules for oxygen. The HCPCS code E0424 is explicitly COVERED for patients meeting the clinical criteria such as hypoxemia. ICD-10 codes including J44.9 and R09.02 are approved for E0424.', 
        'document_type': 'ARTICLE', 
        'section': 'Indications and Limitations of Coverage and/or Medical Necessity'
    }},
    upsert=True
)
print('Updated A52514 chunk in MongoDB')
