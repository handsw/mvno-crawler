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

# 유모바일 섹션
with col1:
    with st.container(border=True):
        st.subheader("🟣 유모바일")
        if st.button("크롤링 시작", key="btn_umobile"): # key 변경
            with st.spinner('수집 중...'):
                data = umobile.run_umobile()
                if data:
                    st.success(f"{len(data)}개 발견!")
                    # 다운로드 버튼에도 key를 명확히 부여
                    get_csv_download_button(data, "umobile")
                else: st.error("제작자에게 문의하세요")

# KG모바일 섹션
with col2:
    with st.container(border=True):
        st.subheader("🔵 KG모바일")
        if st.button("크롤링 시작", key="btn_kg"): # key 변경
            with st.spinner('수집 중...'):
                data = kgmobile.run_kgmobile()
                if data:
                    st.success(f"{len(data)}개 발견!")
                    get_csv_download_button(data, "kgmobile")
                else: st.error("제작자에게 문의하세요")

# 모나 섹션
with col3:
    with st.container(border=True):
        st.subheader("🟡 모나(Mona)")
        
        # 1. 제한 메시지 출력
        st.warning("⚠️ 보안 정책으로 인해 실시간 데이터 수집이 제한되었습니다.")
        st.info("업데이트가 필요하면 제작자에게 문의해주세요.")
        
        # 2. 데이터 파일 읽기 (로컬에서 업로드한 mona.csv)
        try:
            import pandas as pd
            df = pd.read_csv('mona.csv')
            
            # (선택) 마지막 업데이트 날짜 표시
            st.caption("마지막 업데이트: 2026-04-28 (예시)")
            
            st.dataframe(df, use_container_width=True)
            
            with open('mona.csv', 'rb') as f:
                st.download_button("📥 데이터 다운로드", f, "mona.csv", mime="text/csv", use_container_width=True)
        except FileNotFoundError:
            st.error("데이터 파일이 준비되지 않았습니다.")