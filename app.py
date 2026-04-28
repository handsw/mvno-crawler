import streamlit as st
import io
import csv
from datetime import datetime
from crawler import mona, umobile, kgmobile 

# 페이지 설정
st.set_page_config(page_title="MVNO 요금제 수집기", layout="wide")
st.title("타사 MVNO 요금제 수집")
st.write("각 통신사별로 '크롤링 시작' 버튼을 누르면 최신 요금제를 가져옵니다.")

# CSV 다운로드 공통 함수
def get_csv_download_button(data, filename_prefix):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["통신망", "데이터구분", "요금제명", "가격", "할인기간", "할인후가격", "데이터(GB)", "QoS(Mbps)", "통화(분)", "문자(건)"])
    writer.writerows(data)
    csv_file = output.getvalue().encode('utf-8-sig')
    filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return st.download_button(label="📥 CSV 다운로드", data=csv_file, file_name=filename, mime="text/csv", use_container_width=True)

# 3열 구성
col1, col2, col3 = st.columns(3)

# 1. 유모바일
with col1:
    with st.container(border=True):
        st.subheader("🟣 유모바일")
        if st.button("크롤링 시작", key="btn1", use_container_width=True):
            with st.spinner('유모바일 데이터를 수집 중입니다...'):
                data = umobile.run_umobile()
                if data:
                    st.success(f"{len(data)}개 요금제 발견!")
                    get_csv_download_button(data, "umobile")
                else: st.error("실패")

# 2. KG모바일
with col2:
    with st.container(border=True):
        st.subheader("🔵 KG모바일")
        if st.button("크롤링 시작", key="btn2", use_container_width=True):
            with st.spinner('KG모바일 데이터를 수집 중입니다...'):
                data = kgmobile.run_kgmobile()
                if data:
                    st.success(f"{len(data)}개 요금제 발견!")
                    get_csv_download_button(data, "kgmobile")
                else: st.error("실패")

# 3. 모나
with col3:
    with st.container(border=True):
        st.subheader("🟡 모나(Mona)")
        if st.button("크롤링 시작", key="btn3", use_container_width=True):
            with st.spinner('모나 데이터를 수집 중입니다...'):
                data = mona.run_mona()
                if data:
                    st.success(f"{len(data)}개 요금제 발견!")
                    get_csv_download_button(data, "mona")
                else: st.error("실패")