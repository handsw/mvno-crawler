import time
import re
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scraper_utils import get_driver, save_csv, get_filename

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
        
    return raw.replace('GB', '').strip()

def run_umobile():
    """크롤링 메인 함수"""
    driver = get_driver()
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
                if not plan_name or plan_name == "이름없음": continue
                
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
                        last_plus_idx = raw_spc.rfind('+')
                        m = re.search(r'(\d+)(Mbps|Kbps)', raw_spc[last_plus_idx:])
                        if m: qos_val = m.group(1) + ("Kbps" if m.group(2) == "Kbps" else "")
                        data_part = raw_spc[:last_plus_idx].strip()
                    else:
                        data_part = raw_spc
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

if __name__ == "__main__":
    # 개별 테스트 실행 시
    data = run_umobile()
    if data:
        save_csv(get_filename('umobile'), data)