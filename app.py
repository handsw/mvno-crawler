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
        if st.button("크롤링 시작", key="btn_mona"):
            with st.spinner('수집 중...'):
                data, error = mona.run_mona() # 함수가 이제 2개를 줍니다
                
                if error:
                    st.error(f"실패: {error}")
                elif data:
                    st.success(f"{len(data)}개 요금제 발견!")
                    get_csv_download_button(data, "mona")
                else:
                    st.warning("데이터를 하나도 찾지 못했습니다.")