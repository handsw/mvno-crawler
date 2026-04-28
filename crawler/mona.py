import time
import re
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from crawler.scraper_utils import get_driver, clean_numeric, calculate_data

def run_mona():
    driver = get_driver()
    result_data = []
    error_msg = ""
    
    try:
        driver.get("https://mobilemona.co.kr/view/plan/rate_plan.aspx")
        
        # 20초 동안 기다리기
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "pb-plan-item")))
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        cards = soup.select('.pb-plan-item')
        
        # 디버깅: 몇 개가 발견되었는지 터미널/로그에 출력
        print(f"DEBUG: 발견된 카드 개수: {len(cards)}")
        
        if not cards:
            return [], "데이터를 찾을 수 없습니다. 페이지가 로딩되지 않았거나 사이트 구조가 바뀌었습니다."

        for i, card in enumerate(cards):
            try:
                name = card.select_one('.pb-plan-item_name').text.strip()
                net_type = card.select_one('.netdiv').text.strip() if card.select_one('.netdiv') else "LTE"
                
                # 데이터 파싱
                data_text = card.select_one('.pb-plan-data_name.data').text.strip() if card.select_one('.pb-plan-data_name.data') else ""
                qos_match = re.search(r'(\d+)\s*(mbps|kbps)', data_text, re.IGNORECASE)
                qos = qos_match.group(1) + ("Kbps" if qos_match.group(2).lower() == 'kbps' else "") if qos_match else "-"
                
                data_raw = re.sub(r'\+\s*\d+\s*(mbps|kbps)', '', data_text, flags=re.IGNORECASE)
                data_final = calculate_data(data_raw)
                
                price_el = card.select_one('.pb-text-vat_bold.discount')
                price = price_el.get('data-value') if price_el else "0"
                orig_el = card.select_one('.pb-is-linethrough')
                orig_price = orig_el.text.replace('월', '').replace(',', '').replace('원', '').strip() if orig_el else price
                
                period = card.select_one('.event-period').text.strip() if card.select_one('.event-period') else "정보없음"
                voice = clean_numeric(card.select_one('.pb-plan-data_name.voice').text.strip() if card.select_one('.pb-plan-data_name.voice') else "기본제공")
                letter = clean_numeric(card.select_one('.pb-plan-data_name.letter').text.strip() if card.select_one('.pb-plan-data_name.letter') else "기본제공")
                
                result_data.append(['LG', net_type, name, price, period, orig_price, data_final, qos, voice, letter])
            except Exception as e:
                print(f"DEBUG: {i}번째 카드 파싱 에러: {e}")
                continue
                
    except Exception as e:
        error_msg = f"접속/로딩 에러: {str(e)}"
    finally:
        driver.quit()
        
    return result_data, error_msg