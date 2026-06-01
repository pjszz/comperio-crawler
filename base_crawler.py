from abc import ABC, abstractmethod
import requests

class BaseCrawler(ABC):
    def __init__(self):
        # 공통으로 사용할 헤더 (Bot 탐지 우회용)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    @abstractmethod
    def fetch_data(self):
        """API 또는 HTML 페이지 요청을 수행하는 메서드"""
        pass

    @abstractmethod
    def parse_data(self, raw_data):
        """수집된 raw 데이터를 정제하여 딕셔너리 리스트로 반환하는 메서드"""
        pass

    def run(self):
        """크롤링 파이프라인 실행"""
        raw_data = self.fetch_data()
        parsed_data = self.parse_data(raw_data)
        return parsed_data