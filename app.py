import streamlit as st
import io
import csv
import os
from datetime import datetime, timezone, timedelta
from crawler import mona, umobile, kgmobile 

# 페이지 설정
st.set_page_config(page_title="MVNO 요금제 수집기", layout="wide")
with col1:
    st.title("타사 MVNO 요금제 수집")

with col2:
    st.markdown("---") # 구분선(선택사항)
    st.caption("제작자 : MVNO팀 / 손석우")
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
        st.warning("⚠️ 보안 정책으로 인해 크롤링이 제한되었습니다.")
        st.info("업데이트가 필요하면 제작자에게 문의해주세요.")
        
        # 2. 데이터 파일 읽기 (로컬에서 업로드한 mona.csv)
        try:
            file_path = 'mona.csv'
            
            # 1. 한국 시간대(KST) 설정 (UTC + 9시간)
            KST = timezone(timedelta(hours=9))
            
            # 2. 파일 수정 시간을 KST 기준으로 가져오기
            mtime = os.path.getmtime(file_path)
            last_updated = datetime.fromtimestamp(mtime, tz=KST).strftime('%Y-%m-%d %H:%M')
            
            st.caption(f"마지막 업데이트: {last_updated}")
            
            with open(file_path, 'rb') as f:
                st.download_button(
                    label="📥 최신 데이터 다운로드", 
                    data=f, 
                    file_name="mona.csv", 
                    mime="text/csv", 
                    use_container_width=True
                )
        except FileNotFoundError:
            st.error("데이터 파일이 준비되지 않았습니다.")