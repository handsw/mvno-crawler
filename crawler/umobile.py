import time
import csv
import re
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def parse_umobile_data(raw_data):
    """유모바일 전용 데이터 스펙 표준화 함수"""
    raw = raw_data.replace(' ', '')
    
    def fmt(n): return int(n) if n == int(n) else n
    
    # 1. 괄호가 있는 보너스 데이터 형태: (15+10)GB -> 25(15+10)
    m_paren = re.search(r'\((\d+(?:\.\d+)?)\+(\d+(?:\.\d+)?)\)GB', raw)
    if m_paren:
        a = float(m_paren.group(1))
        b = float(m_paren.group(2))
        return f"{fmt(a+b)}({fmt(a)}+{fmt(b)})"
        
    # 2. 기본 + 일일 제공 형태: 11GB+일2GB -> 71(11GB+일2GB)
    m_plus_daily = re.search(r'(\d+(?:\.\d+)?)GB\+일(\d+(?:\.\d+)?)GB', raw)
    if m_plus_daily:
        base = float(m_plus_daily.group(1))
        daily = float(m_plus_daily.group(2))
        total = base + (daily * 30)
        return f"{fmt(total)}({fmt(base)}GB+일 {fmt(daily)}GB)"
        
    # 3. 순수 일일 제공 형태: 일5GB -> 150(일5GB)
    m_daily = re.search(r'일(\d+(?:\.\d+)?)GB', raw)
    if m_daily:
        daily = float(m_daily.group(1))
        return f"{fmt(daily * 30)}(일 {fmt(daily)}GB)"
        
    # 4. 일반 형태: 7GB -> 7
    return raw.replace('GB', '').strip()

print("로봇이 크롬 브라우저를 엽니다...")
options = webdriver.ChromeOptions()
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
options.page_load_strategy = 'eager' 

driver = webdriver.Chrome(options=options)
url = "https://www.uplusumobile.com/product/pric/usim/pricList"
print("유모바일 접속 중... (요금제가 나타날 때까지 기다립니다)")

try:
    driver.get(url)
    
    # 요금제 껍데기(.box)가 화면에 나타날 때까지 대기
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".box")))

    print("페이지를 스크롤하며 요금제를 불러옵니다...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2) # 유모바일은 로딩이 약간 걸릴 수 있어 2초 대기

    print("데이터 수집 시작...")
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    plans = soup.select('.box') 
    result_data = []
    
    print(f"찾은 요금제 개수: {len(plans)}개")

    for plan in plans:
        try:
            # 1. 요금제명 및 데이터구분 (5G / LTE)
            name_tag = plan.select_one('.pln-tit')
            if not name_tag: continue
            plan_name = name_tag.text.strip()
            if plan_name == "이름없음" or not plan_name: continue
            
            data_type = "5G" if "5G" in plan_name else "LTE"
            
            # 2. 가격 및 할인후가격(.cost)
            price_tag = plan.select_one('.dc')
            cost_tag = plan.select_one('.cost')
            
            current_price = price_tag.text.replace('월', '').replace('원', '').replace(',', '').strip() if price_tag else ""
            after_price = cost_tag.text.replace('월', '').replace('원', '').replace(',', '').strip() if cost_tag else ""
            
            # 3. 할인기간 (유모바일은 평생할인 고정)
            discount_period = "평생할인"

            # 4. 데이터 및 QoS 분석
            data_tag = plan.select_one('.pln-spc')
            data_val, qos_val = "", ""
            
            if data_tag:
                raw_spc = data_tag.text.strip() # 예: "(15+10)GB+3Mbps", "7GB+1Mbps"
                
                # QoS 분리
                if 'Mbps' in raw_spc or 'Kbps' in raw_spc:
                    last_plus_idx = raw_spc.rfind('+')
                    # 정규식으로 숫자 추출
                    m = re.search(r'(\d+)(Mbps|Kbps)', raw_spc[last_plus_idx:])
                    if m:
                        qos_val = m.group(1) + ("Kbps" if m.group(2) == "Kbps" else "")
                    
                    data_part = raw_spc[:last_plus_idx].strip()
                else:
                    data_part = raw_spc
                    
                # 앞서 만든 환산 함수에 데이터 부분만 넣기
                data_val = parse_umobile_data(data_part)

            # 5. 통화, 문자
            txt_tags = plan.select('.pln-txt')
            voice_val, sms_val = "", ""
            
            for txt in txt_tags:
                text = txt.text.strip()
                if '통화' in text and '문자' in text:
                    parts = text.split(',')
                    for p in parts:
                        p = p.strip()
                        if p.startswith('통화'):
                            voice_val = p.replace('통화', '').replace('분', '').strip()
                        elif p.startswith('문자'):
                            sms_val = p.replace('문자', '').replace('건', '').strip()
            
            # 배열에 담기 (KG모바일과 동일한 10개 항목)
            result_data.append([
                "LG", data_type, plan_name, current_price, discount_period, 
                after_price, data_val, qos_val, voice_val, sms_val
            ])
                
        except Exception as e:
            continue

except Exception as e:
    print(f"오류: {e}")

finally:
    driver.quit()

# 6. 파일명에 시간 추가하여 저장
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"umobile_{current_time}.csv"

if result_data:
    header = ["통신망", "데이터구분", "요금제명", "가격", "할인기간", "할인후가격", "데이터(GB)", "QoS(Mbps)", "통화", "문자"]
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(result_data)
    print(f"작업 완료! {len(result_data)}개의 요금제가 [{filename}]으로 저장되었습니다.")
else:
    print("데이터를 찾지 못했습니다.")