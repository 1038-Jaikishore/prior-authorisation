import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('.env')
mongo_uri = os.getenv("MONGODB_URI")
client = MongoClient(mongo_uri)
db = client["cms_prior_auth"]

ncd_chunks = list(db.policy_chunks.find({"document_type": "NCD"}).limit(5))

print("=== SAMPLE NCD CHUNKS IN MONGO ===")
for c in ncd_chunks:
    print(f"Doc ID: {c.get('document_id')}")
    print(f"Section: {c.get('section')}")
    print(f"Text: {c.get('text')}\n")
