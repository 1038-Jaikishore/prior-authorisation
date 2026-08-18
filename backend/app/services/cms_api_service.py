import os
import time
import requests
import asyncio
from datetime import datetime

class CMSApiService:
    _token = None
    _token_expiry = 0
    _base_url = "https://api.coverage.cms.gov/v1" 
    
    @classmethod
    def refresh_token(cls):
        """Fetches a new License Agreement token from CMS (valid for 1 hour)."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] CMS API: Fetching new License Agreement token...")
        try:
            response = requests.get(
                f"{cls._base_url}/metadata/license-agreement/",
                headers={'accept': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0 and "Token" in data["data"][0]:
                cls._token = data["data"][0]["Token"]
            elif "data" in data and isinstance(data["data"], dict) and "token" in data["data"]:
                cls._token = data["data"]["token"]
            elif "token" in data:
                cls._token = data["token"]
            else:
                cls._token = "mock_firewall_token"
                
            cls._token_expiry = time.time() + 3600 # Valid for 1 hour
            print("CMS API Token successfully refreshed.")
        except requests.exceptions.RequestException as e:
            print(f"CMS API Request Failed: Failed to fetch token. Using mock token. Error: {e}")
            cls._token = "mock_firewall_token"
            cls._token_expiry = time.time() + 3600

    @classmethod
    def get_valid_token(cls):
        """Returns the current token, refreshing if it's expired or missing."""
        if not cls._token or time.time() > cls._token_expiry - 300: # Refresh 5 mins early
            cls.refresh_token()
        return cls._token
        
    @classmethod
    def _fetch_endpoint(cls, endpoint: str, params: dict, context_msg: str) -> list:
        token = cls.get_valid_token()
        headers = {"Authorization": f"Bearer {token}"}
        try:
            print(f"CMS API -> {context_msg} (Endpoint: {endpoint})")
            response = requests.get(f"{cls._base_url}{endpoint}", params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if "data" in data and isinstance(data["data"], list):
                return data["data"]
            elif "data" in data and isinstance(data["data"], dict):
                return [data["data"]]
            return []
        except requests.exceptions.RequestException as e:
            print(f"CMS API Request failed for {context_msg}: {e}")
            return []

    @classmethod
    def fetch_lcds_by_hcpcs(cls, hcpcs_code: str) -> list:
        return cls._fetch_endpoint("/data/lcd/hcpc-code", {"hcpccode": hcpcs_code}, f"Finding LCDs for HCPCS {hcpcs_code}")

    @classmethod
    def fetch_lcd_contractor(cls, lcd_id: str) -> list:
        clean_id = ''.join(filter(str.isdigit, str(lcd_id)))
        return cls._fetch_endpoint("/data/lcd/contractor", {"lcdid": clean_id}, f"Fetching Contractor for LCD {clean_id}")

    @classmethod
    def fetch_lcd_primary_jurisdiction(cls, lcd_id: str) -> list:
        clean_id = ''.join(filter(str.isdigit, str(lcd_id)))
        return cls._fetch_endpoint("/data/lcd/primary-jurisdiction", {"lcdid": clean_id}, f"Fetching Jurisdiction for LCD {clean_id}")

    @classmethod
    def fetch_lcd_document(cls, lcd_id: str) -> dict:
        clean_id = ''.join(filter(str.isdigit, str(lcd_id)))
        res = cls._fetch_endpoint("/data/lcd", {"lcdid": clean_id}, f"Fetching full LCD document {clean_id}")
        return res[0] if res else None

    @classmethod
    def fetch_lcd_related_ncds(cls, lcd_id: str) -> list:
        clean_id = ''.join(filter(str.isdigit, str(lcd_id)))
        return cls._fetch_endpoint("/data/lcd/related-ncd-documents", {"lcdid": clean_id}, f"Fetching NCDs related to LCD {clean_id}")

    @classmethod
    def fetch_ncd_document(cls, ncd_id: str) -> dict:
        res = cls._fetch_endpoint("/data/ncd", {"ncdid": ncd_id}, f"Fetching full NCD document {ncd_id}")
        return res[0] if res else None

    @classmethod
    def fetch_lcd_related_documents(cls, lcd_id: str) -> list:
        clean_id = ''.join(filter(str.isdigit, str(lcd_id)))
        return cls._fetch_endpoint("/data/lcd/related-documents", {"lcdid": clean_id}, f"Fetching related documents for LCD {clean_id}")

    @classmethod
    def fetch_article_document(cls, article_id: str) -> dict:
        clean_id = ''.join(filter(str.isdigit, str(article_id)))
        res = cls._fetch_endpoint("/data/article", {"articleid": clean_id}, f"Fetching full Article document {clean_id}")
        return res[0] if res else None

    @classmethod
    def fetch_article_related_documents(cls, article_id: str) -> list:
        clean_id = ''.join(filter(str.isdigit, str(article_id)))
        return cls._fetch_endpoint("/data/article/related-documents", {"articleid": clean_id}, f"Fetching related documents for Article {clean_id}")

    @classmethod
    def fetch_article_related_ncds(cls, article_id: str) -> list:
        clean_id = ''.join(filter(str.isdigit, str(article_id)))
        return cls._fetch_endpoint("/data/article/related-ncd-documents", {"articleid": clean_id}, f"Fetching related NCDs for Article {clean_id}")

    @classmethod
    def fetch_article_hcpcs(cls, article_id: str) -> list:
        clean_id = ''.join(filter(str.isdigit, str(article_id)))
        return cls._fetch_endpoint("/data/article/hcpc-code", {"articleid": clean_id}, f"Fetching HCPCS for Article {clean_id}")

    @classmethod
    def fetch_article_primary_jurisdiction(cls, article_id: str) -> list:
        clean_id = ''.join(filter(str.isdigit, str(article_id)))
        return cls._fetch_endpoint("/data/article/primary-jurisdiction", {"articleid": clean_id}, f"Fetching Jurisdiction for Article {clean_id}")

    @classmethod
    def fetch_article_icd10_covered(cls, article_id: str) -> list:
        clean_id = ''.join(filter(str.isdigit, str(article_id)))
        return cls._fetch_endpoint("/data/article/icd10-covered", {"articleid": clean_id}, f"Fetching Covered ICD-10 for Article {clean_id}")

    @classmethod
    def fetch_article_icd10_noncovered(cls, article_id: str) -> list:
        clean_id = ''.join(filter(str.isdigit, str(article_id)))
        return cls._fetch_endpoint("/data/article/icd10-noncovered", {"articleid": clean_id}, f"Fetching Non-Covered ICD-10 for Article {clean_id}")
        
    @classmethod
    def fetch_article_hcpc_modifier(cls, article_id: str) -> list:
        clean_id = ''.join(filter(str.isdigit, str(article_id)))
        return cls._fetch_endpoint("/data/article/hcpc-modifier", {"articleid": clean_id}, f"Fetching Modifiers for Article {clean_id}")

    @classmethod
    def fetch_article_revenue_code(cls, article_id: str) -> list:
        clean_id = ''.join(filter(str.isdigit, str(article_id)))
        return cls._fetch_endpoint("/data/article/revenue-code", {"articleid": clean_id}, f"Fetching Revenue Codes for Article {clean_id}")

    @staticmethod
    async def token_rotation_worker():
        """Background worker intended to run in FastAPI lifespan to keep the token fresh."""
        while True:
            await asyncio.sleep(3300)
            CMSApiService.refresh_token()

