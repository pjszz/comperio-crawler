import requests
import json
import time
import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def fetch_and_filter_bunjang(keyword):
    url = "https://api.bunjang.co.kr/api/1/find_v2.json"
    params = {
        "q": keyword,
        "order": "date",
        "page": 0,
        "request_id": "20240101000000", 
        "stat_device": "w",
        "n": 50, 
        "version": 4
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    EXCLUDE_KEYWORDS = [
        "고장", "부품용", "부품", "수리", "박스", "쿨러만", "냉납", "화면깨짐", 
        "본체", "컴퓨터", "조립", "데스크탑", "완본체", "pc"
    ]
    
    MIN_PRICE_THRESHOLD = 30000
    MAX_PRICE_THRESHOLD = 250000 

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if not data or "list" not in data:
            return []

        raw_items = data["list"]
        filtered_items = []

        for item in raw_items:
            name = item.get("name", "").lower()
            raw_price = item.get("price", "0")
            is_ad = item.get("ad", False)
            
            if is_ad:
                continue
                
            try:
                price = int(raw_price)
            except ValueError:
                continue
                
            if price < MIN_PRICE_THRESHOLD or price > MAX_PRICE_THRESHOLD:
                continue
                
            name_no_space = name.replace(" ", "")
            if any(bad_word in name_no_space for bad_word in EXCLUDE_KEYWORDS):
                continue
                
            filtered_items.append({
                "name": name,
                "price": price
            })
            
        return filtered_items

    except Exception as e:
        print(f"[에러] API 요청 실패: {e}")
        return []

def load_to_bunjang_sheets(gpu_name, results):
    """수집된 중고 매물 데이터의 평균가를 산출하여 구글 시트에 적재"""
    if not results:
        print(f"[경고] {gpu_name}의 유효 매물이 없어 시트 전송을 취소합니다.")
        return

    # 통계 데이터 산출 (평균가 계산)
    prices = [item['price'] for item in results]
    avg_price = int(sum(prices) / len(prices))
    sample_count = len(prices)

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    key_path = os.path.join(os.path.dirname(__file__), "credentials.json")

    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(key_path, scope)
        client = gspread.authorize(creds)
        
        # comperio_market_price 문서의 used_market_price 시트 지정 타격
        sheet = client.open("comperio_market_price").worksheet("used_market_price")
        
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_to_insert = [current_date, gpu_name, avg_price, sample_count]
        
        sheet.append_row(row_to_insert)
        print(f"[시트 적재 완료] {current_date} | {gpu_name} | 평균 {avg_price}원 ({sample_count}건 표본)")
        
    except Exception as e:
        print(f"[에러] 구글 시트 데이터 전송 중 치명적 오류 발생: {e}")

if __name__ == "__main__":
    TARGET_GPUS = ["GTX 1060 3GB", "GTX 1660", "RTX 2060"]
    
    for gpu in TARGET_GPUS:
        print(f"==================================================")
        print(f"[{gpu}] 파이프라인 가동...")
        print(f"==================================================")
        
        # 1. 수집 및 정제
        filtered_results = fetch_and_filter_bunjang(gpu)
        
        # 2. 통계 산출 및 적재
        load_to_bunjang_sheets(gpu, filtered_results)
        
        time.sleep(2)