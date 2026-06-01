from base_crawler import BaseCrawler
import requests
import json
import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

class DanawaCrawler(BaseCrawler):
    def __init__(self):
        super().__init__()
        self.api_url = "https://shop.danawa.com/main/?controller=goods&methods=getBillingInternalProductList"
        
        # 구글 시트 API 인증 세팅
        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        # credentials.json 파일 위치 지정
        self.key_path = os.path.join(os.path.dirname(__file__), "credentials.json")

    def fetch_data(self):
        payload = {
            'marketPlaceSeq': '29',
            'page': '1',
            'productListType': 'LIST',
            'categorySeq1': '861',
            'categorySeq2': '873',
            'category1': '100',
            'category2': '594',
            'attribute[]': '873|40|1009198|S', 
            'order': '1|2,2|2', 
            'limit': '30' 
        }
        response = requests.post(self.api_url, headers=self.headers, data=payload)
        response.raise_for_status() 
        return response.text

    def parse_data(self, raw_data, target_model="250K Plus", target_package="정품"):
        """타겟 모델과 패키지를 필터링하여 최저가 단일 데이터를 추출"""
        try:
            json_data = json.loads(raw_data)
            search_list = json_data.get("goodsData", {}).get("searchList", [])
            
            lowest_price_item = None
            min_price = float('inf') 
            
            for item in search_list:
                raw_name = item.get("goodsName", "")
                raw_price = item.get("goodsPrice", "0")
                
                try:
                    clean_price = int(raw_price.replace(",", ""))
                except ValueError:
                    clean_price = 0
                
                if clean_price == 0:
                    continue
                
                if target_model in raw_name and target_package in raw_name:
                    if clean_price < min_price:
                        min_price = clean_price
                        lowest_price_item = {
                            "platform": "Danawa",
                            "model": target_model,
                            "package": target_package,
                            "full_name": raw_name,
                            "price": clean_price
                        }
                        
            return lowest_price_item
            
        except json.JSONDecodeError as e:
            print(f"[에러] JSON 파싱 실패: {e}")
            return None

    def load_to_sheets(self, data):
        """정제된 데이터를 구글 스프레드시트에 적재(Append)"""
        if not data:
            print("[경고] 적재할 데이터가 없어 구글 시트 전송을 취소합니다.")
            return

        try:
            # 인증 오브젝트 생성
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.key_path, self.scope)
            client = gspread.authorize(creds)
            
            # 문서 타이틀 기반으로 시트 열기
            sheet = client.open("comperio_market_price").sheet1
            
            # 데이터 포맷 생성 (날짜, 모델명, 패키지, 최저가)
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row_to_insert = [current_date, data['model'], data['package'], data['price']]
            
            # 시트의 맨 아래 행에 데이터 추가
            sheet.append_row(row_to_insert)
            print(f"[시트 적재 완료] {current_date} | {data['model']} | {data['price']}원")
            
        except Exception as e:
            print(f"[에러] 구글 시트 데이터 전송 중 치명적 오류 발생: {e}")

if __name__ == "__main__":
    crawler = DanawaCrawler()
    
    TARGET_MODEL = "250K Plus"
    TARGET_PACKAGE = "정품"
    
    print(f"[{TARGET_MODEL} / {TARGET_PACKAGE}] 파이프라인 작동 시작...")
    
    # 1. 수집
    raw_text = crawler.fetch_data()
    
    # 2. 정제
    result = crawler.parse_data(raw_text, target_model=TARGET_MODEL, target_package=TARGET_PACKAGE)
    
    # 3. 적재
    crawler.load_to_sheets(result)