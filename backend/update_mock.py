import os
from dotenv import load_dotenv
load_dotenv()
from pymongo import MongoClient

db = MongoClient(os.getenv('MONGODB_URI'))[os.getenv('MONGODB_DB')]
res = db['policy_chunks'].update_one(
    {'document_id': 'L33797'}, 
    {'$set': {'text': 'Requires nebulizer or stationary oxygen system. An Arterial Blood Gas (ABG) test is explicitly required to confirm hypoxemia before dispensing stationary oxygen.'}}
)
print(f"Updated {res.modified_count} chunks!")
