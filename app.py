import streamlit as st
import pandas as pd
import io
import csv
from datetime import datetime

# 1. 만들어둔 크롤러들을 가져옵니다.
from crawler import mona, umobile, kgmobile 

st.set_page_config(page_title="MVNO 요금제 수집기", page_icon="📱")
st.title("타사 MVNO 요금제 크롤링")

# 다운로드 버튼을 위한 공통 함수
def get_csv_download_button(data, filename_prefix):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["통신망", "데이터구분", "요금제명", "가격", "할인기간", "할인후가격", "데이터(GB)", "QoS(Mbps)", "통화(분)", "문자(건)"])
    writer.writerows(data)
    csv_file = output.getvalue().encode('utf-8-sig')
    filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return st.download_button(label="📥 CSV 다운로드", data=csv_file, file_name=filename, mime="text/csv", use_container_width=True)

# UI 구성
tab1, tab2, tab3 = st.tabs(["🟣 유모바일", "🔵 KG모바일", "🟡 모나(Mona)"])

with tab1:
    st.subheader("유모바일 데이터 수집")
    if st.button("유모바일 크롤링 시작", key="btn1"):
        with st.spinner('수집 중...'):
            data = umobile.run_umobile() # 각 파일의 함수 호출
            if data:
                st.success(f"성공! {len(data)}개 요금제 발견")
                get_csv_download_button(data, "umobile")

with tab2:
    st.subheader("KG모바일 데이터 수집")
    if st.button("KG모바일 크롤링 시작", key="btn2"):
        with st.spinner('수집 중...'):
            data = kgmobile.run_kgmobile()
            if data:
                st.success(f"성공! {len(data)}개 요금제 발견")
                get_csv_download_button(data, "kgmobile")

with tab3:
    st.subheader("모나(Mona) 데이터 수집")
    if st.button("모나 크롤링 시작", key="btn3"):
        with st.spinner('수집 중...'):
            data = mona.run_mona()
            if data:
                st.success(f"성공! {len(data)}개 요금제 발견")
                get_csv_download_button(data, "mona")