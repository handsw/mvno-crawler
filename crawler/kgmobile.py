import time
import csv
import re
from datetime import datetime # 🚨 시간을 가져오기 위한 마법의 도구 추가!
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def parse_data_spec(raw_data):
    """데이터 제공량을 분석하여 71(11GB+일 2GB) 형태로 표준화하는 함수"""
    raw_data = raw_data.replace(' ', '')
    
    base_match = re.search(r'(?<!일)(?<!매일)(\d+(?:\.\d+)?)GB', raw_data)
    daily_match = re.search(r'(?:매일|일)(\d+(?:\.\d+)?)GB', raw_data)
    
    base = float(base_match.group(1)) if base_match else 0
    daily = float(daily_match.group(1)) if daily_match else 0
    
    def fmt(n): return int(n) if n == int(n) else n

    if base > 0 and daily > 0:
        total = fmt(base + (daily * 30))
        return f"{total}({fmt(base)}GB+일 {fmt(daily)}GB)"
    elif base == 0 and daily > 0:
        total = fmt(daily * 30)
        return f"{total}(일 {fmt(daily)}GB)"
    elif base > 0 and daily == 0:
        return str(fmt(base))
    else:
        return raw_data.replace('GB', '').strip()

print("로봇이 크롬 브라우저를 엽니다...")
options = webdriver.ChromeOptions()
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
options.page_load_strategy = 'eager' 

driver = webdriver.Chrome(options=options)
url = "https://www.kgmobile.co.kr/plan"
print("KG모바일 접속 중...")

try:
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".c-accordion_head")))

    print("페이지를 스크롤하며 요금제를 불러옵니다...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)

    print("숨겨진 요금제 탭을 모두 펼칩니다...")
    buttons = driver.find_elements(By.CSS_SELECTOR, '.c-accordion_head button')
    for btn in buttons:
        try:
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.5)
        except: pass

    print("데이터 수집 시작...")
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    
    plans = soup.select('a:has(.c-card-wrapping)')
    result_data = []
    print(f"찾은 요금제 개수: {len(plans)}개")

    for plan in plans:
        try:
            discount_period = "평생할인" 
            prev_head = plan.find_previous('div', class_='c-accordion_head')
            if prev_head:
                tags = prev_head.select('span')
                for tag in tags:
                    if '할인' in tag.text: discount_period = tag.text.replace('#', '').strip()
            
            name_tag = plan.select_one('.c-card-title p')
            if not name_tag: continue
            plan_name = name_tag.text.strip()
            data_type = "5G" if "5G" in plan_name else "LTE"
            
            price_box = plan.select_one('.c-card-price')
            current_price = ""
            after_price = ""
            if price_box:
                st = price_box.select_one('strong')
                p_tag = price_box.select_one('p')
                if st: current_price = st.text.replace(',', '').strip()
                if p_tag: after_price = p_tag.text.replace(',', '').replace('원', '').strip()

            card_item = plan.select_one('.c-card-item:not(.mo-c-card)')
            if not card_item: card_item = plan.select_one('.c-card-item')
            
            data_val, qos_val, voice_val, sms_val = "", "", "", ""
            
            if card_item:
                spans = card_item.select('.items_bloc > span')
                if len(spans) >= 3:
                    raw_full_text = spans[0].text 
                    data_val = parse_data_spec(raw_full_text)
                    
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
        except Exception as e:
            continue

except Exception as e:
    print(f"오류: {e}")

finally:
    driver.quit()

# 🚨 파일명에 현재 시간(년월일_시분초)을 조합하는 로직 추가!
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"kgmobile_{current_time}.csv"

if result_data:
    header = ["통신망", "데이터구분", "요금제명", "가격", "할인기간", "할인후가격", "데이터(GB)", "QoS(Mbps)", "통화", "문자"]
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(result_data)
    print(f"완벽하게 매칭 성공! {len(result_data)}개의 요금제가 [{filename}]으로 저장되었습니다.")