import time
import re
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from crawler.scraper_utils import get_driver, clean_numeric, calculate_data

def run_mona():
    """모나 크롤링 메인 함수"""
    driver = get_driver()
    result_data = []
    error_msg = ""
    
    try:
        driver.set_page_load_timeout(30)
        driver.set_window_size(1920, 1080)
        
        driver.get("https://mobilemona.co.kr/view/plan/rate_plan.aspx")
        
        # 1. 페이지가 로딩될 때까지 대기
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "pb-plan-item")))
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        cards = soup.select('.pb-plan-item')
        
        if not cards:
            return [], "데이터를 찾을 수 없음 (페이지 구조 변경 또는 로딩 실패)"

        for card in cards:
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
                
                result_data.append([
                    'LG', net_type, name, price, period, orig_price, data_final, qos, voice, letter
                ])
            except Exception as e:
                continue
                
    except Exception as e:
        error_msg = str(e)
    finally:
        driver.quit()
        
    return result_data, error_msg

# 로컬에서 테스트할 때만 실행
if __name__ == "__main__":
    data, err = run_mona()
    if err:
        print(f"오류 발생: {err}")
    elif data:
        print(f"{len(data)}개 데이터 수집 완료")