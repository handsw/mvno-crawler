import time
import re
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scraper_utils import get_driver, clean_numeric, save_csv, calculate_data, get_filename

def parse_data_spec(raw_data):
    """KG모바일 전용 데이터 제공량 표준화 함수"""
    raw = raw_data.replace(' ', '')
    base_match = re.search(r'(?<!일)(?<!매일)(\d+(?:\.\d+)?)GB', raw)
    daily_match = re.search(r'(?:매일|일)(\d+(?:\.\d+)?)GB', raw)
    
    base = float(base_match.group(1)) if base_match else 0
    daily = float(daily_match.group(1)) if daily_match else 0
    
    def fmt(n): return int(n) if n == int(n) else n

    if base > 0 and daily > 0:
        return f"{fmt(base + (daily * 30))}({fmt(base)}GB+일 {fmt(daily)}GB)"
    elif base == 0 and daily > 0:
        return f"{fmt(daily * 30)}(일 {fmt(daily)}GB)"
    elif base > 0 and daily == 0:
        return str(fmt(base))
    else:
        return raw.replace('GB', '').strip()

def run_kgmobile():
    """KG모바일 크롤링 메인 함수"""
    driver = get_driver()
    result_data = []
    try:
        driver.get("https://www.kgmobile.co.kr/plan")
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".c-accordion_head")))

        # 페이지 스크롤 및 탭 펼치기
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        buttons = driver.find_elements(By.CSS_SELECTOR, '.c-accordion_head button')
        for btn in buttons:
            try:
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.3)
            except: pass

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        plans = soup.select('a:has(.c-card-wrapping)')
        
        for plan in plans:
            try:
                # 할인 기간
                discount_period = "평생할인" 
                prev_head = plan.find_previous('div', class_='c-accordion_head')
                if prev_head:
                    for tag in prev_head.select('span'):
                        if '할인' in tag.text: discount_period = tag.text.replace('#', '').strip()
                
                # 기본 정보
                name_tag = plan.select_one('.c-card-title p')
                if not name_tag: continue
                plan_name = name_tag.text.strip()
                data_type = "5G" if "5G" in plan_name else "LTE"
                
                # 가격
                price_box = plan.select_one('.c-card-price')
                current_price, after_price = "", ""
                if price_box:
                    st = price_box.select_one('strong')
                    p_tag = price_box.select_one('p')
                    if st: current_price = st.text.replace(',', '').strip()
                    if p_tag: after_price = p_tag.text.replace(',', '').replace('원', '').strip()

                # 데이터 및 통화 문자
                card_item = plan.select_one('.c-card-item:not(.mo-c-card)') or plan.select_one('.c-card-item')
                data_val, qos_val, voice_val, sms_val = "", "", "", ""
                
                if card_item:
                    spans = card_item.select('.items_bloc > span')
                    if len(spans) >= 3:
                        data_val = parse_data_spec(spans[0].text)
                        qos_p = spans[0].select_one('p')
                        if qos_p:
                            m = re.search(r'(\d+)(Mbps|Kbps)', qos_p.text)
                            if m: qos_val = m.group(1) + ("Kbps" if m.group(2) == "Kbps" else "")
                        voice_val = spans[1].text.replace('무제한', '기본제공').replace('분', '').strip()
                        sms_val = spans[2].text.replace('무제한', '기본제공').replace('건', '').strip()

                result_data.append([
                    "LG", data_type, plan_name, current_price, 
                    discount_period, after_price, data_val, qos_val, voice_val, sms_val
                ])
            except: continue
    finally:
        driver.quit()
    return result_data

if __name__ == "__main__":
    # 개별 테스트 실행 시
    data = run_kgmobile()
    if data:
        save_csv(get_filename('kgmobile'), data)