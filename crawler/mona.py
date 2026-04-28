from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import csv
import re
import os
from datetime import datetime
from crawler.scraper_utils import get_driver, clean_numeric, save_csv, calculate_data, get_filename

# --- 설정 및 도구 함수 ---
def get_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

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

def clean_numeric(text):
    text = re.sub(r'\(.*\)', '', text).strip()
    if any(char.isdigit() for char in text): return "".join(filter(str.isdigit, text))
    return text

# --- 메인 로직 ---
def run_mona():
    driver = get_driver()
    result_data = []
    try:
        driver.get("https://mobilemona.co.kr/view/plan/rate_plan.aspx")
        time.sleep(7)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        cards = soup.select('.pb-plan-item')
        print(f"찾은 요금제 개수: {len(cards)}개")

        for card in cards:
            # try-except를 잠시 제거해서 에러가 나면 바로 뜨게 함 (디버깅용)
            name = card.select_one('.pb-plan-item_name').text.strip()
            net_type = card.select_one('.netdiv').text.strip() if card.select_one('.netdiv') else "LTE"
            
            # 데이터 및 QoS
            data_text = card.select_one('.pb-plan-data_name.data').text.strip() if card.select_one('.pb-plan-data_name.data') else ""
            qos_match = re.search(r'(\d+)\s*(mbps|kbps)', data_text, re.IGNORECASE)
            qos = qos_match.group(1) + ("Kbps" if qos_match.group(2).lower() == 'kbps' else "") if qos_match else "-"
            
            data_raw = re.sub(r'\+\s*\d+\s*(mbps|kbps)', '', data_text, flags=re.IGNORECASE)
            data_final = calculate_data(data_raw)
            
            # 가격
            price_el = card.select_one('.pb-text-vat_bold.discount')
            price = price_el.get('data-value') if price_el else "0"
            orig_el = card.select_one('.pb-is-linethrough')
            orig_price = orig_el.text.replace('월', '').replace(',', '').replace('원', '').strip() if orig_el else price
            
            period = card.select_one('.event-period').text.strip() if card.select_one('.event-period') else "정보없음"
            voice = clean_numeric(card.select_one('.pb-plan-data_name.voice').text.strip() if card.select_one('.pb-plan-data_name.voice') else "기본제공")
            letter = clean_numeric(card.select_one('.pb-plan-data_name.letter').text.strip() if card.select_one('.pb-plan-data_name.letter') else "기본제공")
            
            result_data.append([
                "LG", net_type, name, price, period, orig_price, data_final, qos, voice, letter
            ])
            
    finally:
        driver.quit()
    return result_data

if __name__ == "__main__":
    result_data = run_mona()
    
    if result_data:
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mona_{current_time}.csv"
        
        header = ["통신망", "데이터구분", "요금제명", "가격", "할인기간", "할인후가격", "데이터(GB)", "QoS(Mbps)", "통화(분)", "문자(건)"]
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(result_data)
        print(f"작업 완료! {len(result_data)}개의 요금제가 [{filename}]으로 저장되었습니다.")
    else:
        print("데이터를 찾지 못했습니다.")