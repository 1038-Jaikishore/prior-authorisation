import sys
import os
sys.path.append(os.path.dirname(__file__))
from app.services.cms_api_service import CMSApiService
import json

def fetch_and_show():
    # 1. Use a known HCPCS (E0424 for Home Oxygen Therapy)
    hcpcs = "E0424"
    print(f"--- 1. Fetching LCDs for HCPCS: {hcpcs} ---")
    lcds = CMSApiService.fetch_lcds_by_hcpcs(hcpcs)
    lcd_ids = [lcd.get('lcdId') for lcd in lcds] if lcds else []
    print(f"Found LCD IDs: {lcd_ids}\n")
    
    # 2. Use a known Article ID (A52514 linked to E0424 and LCD 33797)
    article_id = "52514"
    print(f"--- 2. Fetching LCDs & NCDs for Article: {article_id} ---")
    
    # Fetch Article -> related LCDs (In CMS API, usually you fetch Article's related documents)
    art_related = CMSApiService.fetch_article_related_documents(article_id)
    art_lcds = [doc.get('lcdId') for doc in art_related if 'lcdId' in doc] if art_related else []
    print(f"Found related LCDs for Article {article_id}: {art_lcds}")
    
    # Fetch Article -> related NCDs
    art_ncds = CMSApiService.fetch_article_related_ncds(article_id)
    art_ncd_ids = [ncd.get('ncdId') for ncd in art_ncds] if art_ncds else []
    print(f"Found related NCDs for Article {article_id}: {art_ncd_ids}\n")

    # 3. Use the linked LCD (33797) to fetch NCDs directly
    if lcd_ids:
        lcd_id = lcd_ids[0]
        print(f"--- 3. Fetching NCDs directly for LCD: {lcd_id} ---")
        ncds = CMSApiService.fetch_lcd_related_ncds(str(lcd_id))
        ncd_ids = [ncd.get('ncdId') for ncd in ncds] if ncds else []
        print(f"Found NCDs linked to LCD {lcd_id}: {ncd_ids}")

if __name__ == "__main__":
    fetch_and_show()
