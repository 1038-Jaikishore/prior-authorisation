import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from app.core.config import settings

logger = logging.getLogger("cms-prior-auth")

class MongoDBConnection:
    def __init__(self):
        self.client = None
        self.db = None

    def connect(self):
        """Establish connection to MongoDB using configured settings."""
        if self.client is not None:
            return
            
        try:
            logger.info("Connecting to MongoDB...")
            # We set a short serverSelectionTimeoutMS so connectivity checks fail fast if the URI is invalid
            self.client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[settings.mongodb_db]
            # Trigger a connection check to verify URI is valid and DB is reachable
            self.client.admin.command('ping')
            logger.info(f"Successfully connected to database: {settings.mongodb_db}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.client = None
            self.db = None
            raise ConnectionFailure(f"Could not connect to database {settings.mongodb_db}: {e}")

    def disconnect(self):
        """Close connection client."""
        if self.client:
            self.client.close()
            logger.info("Closed MongoDB connection.")
            self.client = None
            self.db = None

    def get_db(self):
        """Get the active MongoDB database object, connecting if needed."""
        if self.db is None:
            self.connect()
        return self.db

    def check_health(self) -> dict:
        """Perform database health check ping and return stats."""
        if self.client is None:
            try:
                self.connect()
            except Exception as e:
                return {"status": "unhealthy", "error": str(e)}
        
        try:
            self.client.admin.command('ping')
            # Fetch collection counts for context
            db = self.get_db()
            collections = db.list_collection_names()
            stats = {col: db[col].count_documents({}) for col in collections}
            return {
                "status": "healthy",
                "database": settings.mongodb_db,
                "collections_stats": stats
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

db_connection = MongoDBConnection()
