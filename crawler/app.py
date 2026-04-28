import streamlit as st
import time
import csv
import re
import io
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ----------------- [1. 공통 셋팅 및 데이터 정제 함수] -----------------
def get_chrome_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.page_load_strategy = 'eager'
    
    # 🚨 서버 환경을 위해 아래 3줄을 반드시 추가/활성화해야 합니다!
    options.add_argument('--headless') # 창 없는 유령 모드
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    return webdriver.Chrome(options=options)

def parse_umobile_data(raw_data):
    raw = raw_data.replace(' ', '')
    def fmt(n): return int(n) if n == int(n) else n
    
    m_paren = re.search(r'\((\d+(?:\.\d+)?)\+(\d+(?:\.\d+)?)\)GB', raw)
    if m_paren: return f"{fmt(float(m_paren.group(1))+float(m_paren.group(2)))}({fmt(float(m_paren.group(1)))}+{fmt(float(m_paren.group(2)))}"
        
    m_plus_daily = re.search(r'(\d+(?:\.\d+)?)GB\+일(\d+(?:\.\d+)?)GB', raw)
    if m_plus_daily: return f"{fmt(float(m_plus_daily.group(1)) + (float(m_plus_daily.group(2)) * 30))}({fmt(float(m_plus_daily.group(1)))}GB+일 {fmt(float(m_plus_daily.group(2)))}GB)"
        
    m_daily = re.search(r'일(\d+(?:\.\d+)?)GB', raw)
    if m_daily: return f"{fmt(float(m_daily.group(1)) * 30)}(일 {fmt(float(m_daily.group(1)))}GB)"
    return raw.replace('GB', '').strip()

def parse_kg_data(raw_data):
    raw = raw_data.replace(' ', '')
    base_match = re.search(r'(?<!일)(?<!매일)(\d+(?:\.\d+)?)GB', raw)
    daily_match = re.search(r'(?:매일|일)(\d+(?:\.\d+)?)GB', raw)
    base = float(base_match.group(1)) if base_match else 0
    daily = float(daily_match.group(1)) if daily_match else 0
    def fmt(n): return int(n) if n == int(n) else n

    if base > 0 and daily > 0: return f"{fmt(base + (daily * 30))}({fmt(base)}GB+일 {fmt(daily)}GB)"
    elif base == 0 and daily > 0: return f"{fmt(daily * 30)}(일 {fmt(daily)}GB)"
    elif base > 0 and daily == 0: return str(fmt(base))
    return raw.replace('GB', '').strip()

# ----------------- [2. 크롤링 본체 (유모바일 & KG모바일)] -----------------
def crawl_umobile():
    driver = get_chrome_driver()
    result_data = []
    try:
        driver.get("https://www.uplusumobile.com/product/pric/usim/pricList")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".box")))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        plans = soup.select('.box') 
        
        for plan in plans:
            try:
                name_tag = plan.select_one('.pln-tit')
                if not name_tag: continue
                plan_name = name_tag.text.strip()
                if plan_name == "이름없음" or not plan_name: continue
                data_type = "5G" if "5G" in plan_name else "LTE"
                
                price_tag = plan.select_one('.dc')
                cost_tag = plan.select_one('.cost')
                current_price = price_tag.text.replace('월', '').replace('원', '').replace(',', '').strip() if price_tag else ""
                after_price = cost_tag.text.replace('월', '').replace('원', '').replace(',', '').strip() if cost_tag else ""
                
                data_tag = plan.select_one('.pln-spc')
                data_val, qos_val = "", ""
                if data_tag:
                    raw_spc = data_tag.text.strip()
                    if 'Mbps' in raw_spc or 'Kbps' in raw_spc:
                        last_plus = raw_spc.rfind('+')
                        m = re.search(r'(\d+)(Mbps|Kbps)', raw_spc[last_plus:])
                        if m: qos_val = m.group(1) + ("Kbps" if m.group(2) == "Kbps" else "")
                        data_part = raw_spc[:last_plus].strip()
                    else: data_part = raw_spc
                    data_val = parse_umobile_data(data_part)

                txt_tags = plan.select('.pln-txt')
                voice_val, sms_val = "", ""
                for txt in txt_tags:
                    text = txt.text.strip()
                    if '통화' in text and '문자' in text:
                        for p in text.split(','):
                            p = p.strip()
                            if p.startswith('통화'): voice_val = p.replace('통화', '').replace('분', '').strip()
                            elif p.startswith('문자'): sms_val = p.replace('문자', '').replace('건', '').strip()
                
                result_data.append(["LG", data_type, plan_name, current_price, "평생할인", after_price, data_val, qos_val, voice_val, sms_val])
            except: continue
    finally:
        driver.quit()
    return result_data

def crawl_kgmobile():
    driver = get_chrome_driver()
    result_data = []
    try:
        driver.get("https://www.kgmobile.co.kr/plan")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".c-accordion_head")))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        for btn in driver.find_elements(By.CSS_SELECTOR, '.c-accordion_head button'):
            try:
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.3)
            except: pass

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        plans = soup.select('a:has(.c-card-wrapping)')

        for plan in plans:
            try:
                discount_period = "평생할인" 
                prev_head = plan.find_previous('div', class_='c-accordion_head')
                if prev_head:
                    for tag in prev_head.select('span'):
                        if '할인' in tag.text: discount_period = tag.text.replace('#', '').strip()
                
                name_tag = plan.select_one('.c-card-title p')
                if not name_tag: continue
                plan_name = name_tag.text.strip()
                data_type = "5G" if "5G" in plan_name else "LTE"
                
                price_box = plan.select_one('.c-card-price')
                current_price, after_price = "", ""
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
                        data_val = parse_kg_data(spans[0].text)
                        qos_p = spans[0].select_one('p')
                        if qos_p:
                            m = re.search(r'(\d+)(Mbps|Kbps)', qos_p.text)
                            if m: qos_val = m.group(1) + ("Kbps" if m.group(2) == "Kbps" else "")
                        voice_val = spans[1].text.replace('무제한', '기본제공').replace('분', '').strip()
                        sms_val = spans[2].text.replace('무제한', '기본제공').replace('건', '').strip()

                result_data.append(["LG", data_type, plan_name, current_price, discount_period, after_price, data_val, qos_val, voice_val, sms_val])
            except: continue
    finally:
        driver.quit()
    return result_data

# ----------------- [3. 웹 화면 UI 만들기 (Streamlit 마법!)] -----------------
st.set_page_config(page_title="MVNO 요금제 수집기", page_icon="📱")

st.title("타사 MVNO 요금제 자동 크롤링")
st.write("버튼을 누르면 실시간으로 홈페이지에 접속해 최신 요금제를 엑셀 파일로 만들어 줍니다.")

header = ["통신망", "데이터구분", "요금제명", "가격", "할인기간", "할인후가격", "데이터(GB)", "QoS(Mbps)", "통화", "문자"]

# 엑셀 파일로 변환해주는 마법 함수
def convert_to_csv(data):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(header)
    writer.writerows(data)
    return output.getvalue().encode('utf-8-sig')

col1, col2 = st.columns(2) # 화면을 2개의 열로 나눔

with col1:
    st.subheader("🟣 유모바일")
    if st.button("유모바일 크롤링 시작", key="btn_umobile", use_container_width=True):
        with st.spinner('로봇이 유모바일 홈페이지를 읽고 있습니다... (약 10초 소요)'):
            data = crawl_umobile()
            if data:
                st.success(f"성공! 총 {len(data)}개의 요금제를 찾았습니다.")
                csv_file = convert_to_csv(data)
                filename = f"umobile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                st.download_button(label="📥 엑셀(CSV) 다운로드", data=csv_file, file_name=filename, mime="text/csv", use_container_width=True)
            else:
                st.error("데이터를 불러오지 못했습니다.")

with col2:
    st.subheader("🔵 KG모바일")
    if st.button("KG모바일 크롤링 시작", key="btn_kgmobile", use_container_width=True):
        with st.spinner('로봇이 KG모바일 홈페이지를 펼치고 있습니다... (약 15초 소요)'):
            data = crawl_kgmobile()
            if data:
                st.success(f"성공! 총 {len(data)}개의 요금제를 찾았습니다.")
                csv_file = convert_to_csv(data)
                filename = f"kgmobile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                st.download_button(label="📥 엑셀(CSV) 다운로드", data=csv_file, file_name=filename, mime="text/csv", use_container_width=True)
            else:
=======
import streamlit as st
import time
import csv
import re
import io
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ----------------- [1. 공통 셋팅 및 데이터 정제 함수] -----------------
def get_chrome_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.page_load_strategy = 'eager'
    
    # 🚨 서버 환경을 위해 아래 3줄을 반드시 추가/활성화해야 합니다!
    options.add_argument('--headless') # 창 없는 유령 모드
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    return webdriver.Chrome(options=options)

def parse_umobile_data(raw_data):
    raw = raw_data.replace(' ', '')
    def fmt(n): return int(n) if n == int(n) else n
    
    m_paren = re.search(r'\((\d+(?:\.\d+)?)\+(\d+(?:\.\d+)?)\)GB', raw)
    if m_paren: return f"{fmt(float(m_paren.group(1))+float(m_paren.group(2)))}({fmt(float(m_paren.group(1)))}+{fmt(float(m_paren.group(2)))}"
        
    m_plus_daily = re.search(r'(\d+(?:\.\d+)?)GB\+일(\d+(?:\.\d+)?)GB', raw)
    if m_plus_daily: return f"{fmt(float(m_plus_daily.group(1)) + (float(m_plus_daily.group(2)) * 30))}({fmt(float(m_plus_daily.group(1)))}GB+일 {fmt(float(m_plus_daily.group(2)))}GB)"
        
    m_daily = re.search(r'일(\d+(?:\.\d+)?)GB', raw)
    if m_daily: return f"{fmt(float(m_daily.group(1)) * 30)}(일 {fmt(float(m_daily.group(1)))}GB)"
    return raw.replace('GB', '').strip()

def parse_kg_data(raw_data):
    raw = raw_data.replace(' ', '')
    base_match = re.search(r'(?<!일)(?<!매일)(\d+(?:\.\d+)?)GB', raw)
    daily_match = re.search(r'(?:매일|일)(\d+(?:\.\d+)?)GB', raw)
    base = float(base_match.group(1)) if base_match else 0
    daily = float(daily_match.group(1)) if daily_match else 0
    def fmt(n): return int(n) if n == int(n) else n

    if base > 0 and daily > 0: return f"{fmt(base + (daily * 30))}({fmt(base)}GB+일 {fmt(daily)}GB)"
    elif base == 0 and daily > 0: return f"{fmt(daily * 30)}(일 {fmt(daily)}GB)"
    elif base > 0 and daily == 0: return str(fmt(base))
    return raw.replace('GB', '').strip()

# ----------------- [2. 크롤링 본체 (유모바일 & KG모바일)] -----------------
def crawl_umobile():
    driver = get_chrome_driver()
    result_data = []
    try:
        driver.get("https://www.uplusumobile.com/product/pric/usim/pricList")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".box")))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        plans = soup.select('.box') 
        
        for plan in plans:
            try:
                name_tag = plan.select_one('.pln-tit')
                if not name_tag: continue
                plan_name = name_tag.text.strip()
                if plan_name == "이름없음" or not plan_name: continue
                data_type = "5G" if "5G" in plan_name else "LTE"
                
                price_tag = plan.select_one('.dc')
                cost_tag = plan.select_one('.cost')
                current_price = price_tag.text.replace('월', '').replace('원', '').replace(',', '').strip() if price_tag else ""
                after_price = cost_tag.text.replace('월', '').replace('원', '').replace(',', '').strip() if cost_tag else ""
                
                data_tag = plan.select_one('.pln-spc')
                data_val, qos_val = "", ""
                if data_tag:
                    raw_spc = data_tag.text.strip()
                    if 'Mbps' in raw_spc or 'Kbps' in raw_spc:
                        last_plus = raw_spc.rfind('+')
                        m = re.search(r'(\d+)(Mbps|Kbps)', raw_spc[last_plus:])
                        if m: qos_val = m.group(1) + ("Kbps" if m.group(2) == "Kbps" else "")
                        data_part = raw_spc[:last_plus].strip()
                    else: data_part = raw_spc
                    data_val = parse_umobile_data(data_part)

                txt_tags = plan.select('.pln-txt')
                voice_val, sms_val = "", ""
                for txt in txt_tags:
                    text = txt.text.strip()
                    if '통화' in text and '문자' in text:
                        for p in text.split(','):
                            p = p.strip()
                            if p.startswith('통화'): voice_val = p.replace('통화', '').replace('분', '').strip()
                            elif p.startswith('문자'): sms_val = p.replace('문자', '').replace('건', '').strip()
                
                result_data.append(["LG", data_type, plan_name, current_price, "평생할인", after_price, data_val, qos_val, voice_val, sms_val])
            except: continue
    finally:
        driver.quit()
    return result_data

def crawl_kgmobile():
    driver = get_chrome_driver()
    result_data = []
    try:
        driver.get("https://www.kgmobile.co.kr/plan")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".c-accordion_head")))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        for btn in driver.find_elements(By.CSS_SELECTOR, '.c-accordion_head button'):
            try:
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.3)
            except: pass

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        plans = soup.select('a:has(.c-card-wrapping)')

        for plan in plans:
            try:
                discount_period = "평생할인" 
                prev_head = plan.find_previous('div', class_='c-accordion_head')
                if prev_head:
                    for tag in prev_head.select('span'):
                        if '할인' in tag.text: discount_period = tag.text.replace('#', '').strip()
                
                name_tag = plan.select_one('.c-card-title p')
                if not name_tag: continue
                plan_name = name_tag.text.strip()
                data_type = "5G" if "5G" in plan_name else "LTE"
                
                price_box = plan.select_one('.c-card-price')
                current_price, after_price = "", ""
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
                        data_val = parse_kg_data(spans[0].text)
                        qos_p = spans[0].select_one('p')
                        if qos_p:
                            m = re.search(r'(\d+)(Mbps|Kbps)', qos_p.text)
                            if m: qos_val = m.group(1) + ("Kbps" if m.group(2) == "Kbps" else "")
                        voice_val = spans[1].text.replace('무제한', '기본제공').replace('분', '').strip()
                        sms_val = spans[2].text.replace('무제한', '기본제공').replace('건', '').strip()

                result_data.append(["LG", data_type, plan_name, current_price, discount_period, after_price, data_val, qos_val, voice_val, sms_val])
            except: continue
    finally:
        driver.quit()
    return result_data

# ----------------- [3. 웹 화면 UI 만들기 (Streamlit 마법!)] -----------------
st.set_page_config(page_title="MVNO 요금제 수집기", page_icon="📱")

st.title("📱 알뜰폰(MVNO) 요금제 자동 수집기")
st.write("버튼을 누르면 실시간으로 홈페이지에 접속해 최신 요금제를 엑셀 파일로 만들어 줍니다.")

header = ["통신망", "데이터구분", "요금제명", "가격", "할인기간", "할인후가격", "데이터(GB)", "QoS(Mbps)", "통화", "문자"]

# 엑셀 파일로 변환해주는 마법 함수
def convert_to_csv(data):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(header)
    writer.writerows(data)
    return output.getvalue().encode('utf-8-sig')

col1, col2 = st.columns(2) # 화면을 2개의 열로 나눔

with col1:
    st.subheader("🟣 유모바일")
    if st.button("유모바일 크롤링 시작", key="btn_umobile", use_container_width=True):
        with st.spinner('로봇이 유모바일 홈페이지를 읽고 있습니다... (약 10초 소요)'):
            data = crawl_umobile()
            if data:
                st.success(f"성공! 총 {len(data)}개의 요금제를 찾았습니다.")
                csv_file = convert_to_csv(data)
                filename = f"umobile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                st.download_button(label="📥 엑셀(CSV) 다운로드", data=csv_file, file_name=filename, mime="text/csv", use_container_width=True)
            else:
                st.error("데이터를 불러오지 못했습니다.")

with col2:
    st.subheader("🔵 KG모바일")
    if st.button("KG모바일 크롤링 시작", key="btn_kgmobile", use_container_width=True):
        with st.spinner('로봇이 KG모바일 홈페이지를 펼치고 있습니다... (약 15초 소요)'):
            data = crawl_kgmobile()
            if data:
                st.success(f"성공! 총 {len(data)}개의 요금제를 찾았습니다.")
                csv_file = convert_to_csv(data)
                filename = f"kgmobile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                st.download_button(label="📥 엑셀(CSV) 다운로드", data=csv_file, file_name=filename, mime="text/csv", use_container_width=True)
            else:
                st.error("데이터를 불러오지 못했습니다.")