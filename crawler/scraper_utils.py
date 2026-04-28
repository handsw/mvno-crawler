# scraper_utils.py
import csv
import re
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

HEADERS = ["통신망", "데이터구분", "요금제명", "가격", "할인기간", "할인후가격", "데이터(GB)", "QoS(Mbps)", "통화(분)", "문자(건)"]

def get_filename(company_name):
    """표준화된 파일 이름 생성: 예) mona_20260428_173400.csv"""
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{company_name}_{now}.csv"

def get_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # 서버용 추가 옵션
    options.add_argument('--disable-gpu')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    
    # [핵심] 자동으로 서버 환경에 맞는 드라이버를 설치합니다.
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def clean_numeric(text):
    text = re.sub(r'\(.*\)', '', text).strip()
    if any(char.isdigit() for char in text): return "".join(filter(str.isdigit, text))
    return text

def calculate_data(text):
    norm_text = text.replace('매일', '일')
    norm_text = re.sub(r'일\s*(\d+)\s*G[Bb]?', r'일 \1GB', norm_text)
    is_complex = ('+' in norm_text) or ('일' in norm_text)
    
    daily_match = re.search(r'일\s*(\d+)GB', norm_text)
    daily_val = int(daily_match.group(1)) * 30 if daily_match else 0
    calc_text = re.sub(r'일\s*\d+GB', '', norm_text) if daily_match else norm_text
    
    bases = re.findall(r'(\d+(?:\.\d+)?)GB', calc_text)
    base_val = sum(float(b) for b in bases)
    
    total = base_val + daily_val
    total_str = f"{total:g}" 
    
    return total_str if not is_complex else f"{total_str}({norm_text.strip()})"

def save_csv(filename, data_list):
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        writer.writerows(data_list)
    print(f"저장 완료: {filename} ({len(data_list)}개 데이터)")