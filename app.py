import os
import tempfile
from io import BytesIO
import ezdxf
import pandas as pd
import streamlit as st

# 페이지 레이아웃 설정
st.set_page_config(
    page_title="Spring Support 도면 실무 추출기", layout="wide"
)

st.title("🛠️ Spring Support 도면 실무형 텍스트 매퍼")
st.write(
    "복잡한 자동화 에러에서 벗어나, 도면의 전체 텍스트를 눈으로 확인하며"
    " 확실하게 엑셀 표로 완성하는 실용적인 프로그램입니다."
)

# 파일 업로드
uploaded_files = st.file_uploader(
    "DXF 파일을 업로드하세요 (복수 선택 가능)", type=["dxf"], accept_multiple_files=True
)


def extract_all_texts_from_dxf(file_path):
  """DXF 파일에서 모든 텍스트를 순수하게 긁어오는 함수"""
  try:
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()
  except Exception as e:
    return []

  texts = []
  for entity in msp.query("TEXT MTEXT"):
    txt = entity.dxf.text if entity.dxftype() == "TEXT" else entity.text
    if txt.strip():
      # MTEXT 포맷팅 태그 제거 정제
      import re

      clean_txt = re.sub(r"\\À?[A-Za-z0-9]+;?", "", txt).strip()
      if clean_txt and clean_txt not in texts:
        texts.append(clean_txt)

  return texts


if uploaded_files:
  # 세션 스테이트를 이용해 데이터 관리
  if "df_data" not in st.session_state:
    initial_rows = []
    for f in uploaded_files:
      with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(f.getvalue())
        tmp_path = tmp.name

      texts = extract_all_texts_from_dxf(tmp_path)
      base_name = os.path.basename(f.name).replace(".dxf", "")

      # 기본 행 구조 생성
      initial_rows.append({
          "DWG No": base_name,
          "SUPPORT TAG No.": "",
          "Type & Size": "",
          "Hot Load (단위 : N)": "",
          "Cold Load (단위 : N)": "",
          "Hot Point (단위 : mm)": "",
          "Cold Point (단위 : mm)": "",
          "Hanger 설치높이": "",
          "STANCHION 높이": "",
          "_raw_texts": " / ".join(texts),  # 참고용 전체 텍스트 모음
      })
    st.session_state.df_data = pd.DataFrame(initial_rows)

  st.divider()
  st.subheader("📝 도면 데이터 입력 및 편집 표")
  st.write(
      "아래 표의 빈칸을 직접 클릭하여 수정하거나, 원본 텍스트를 참고하여 값을"
      " 채워 넣으세요."
  )

  # Streamlit의 강력한 편집 기능 (Data Editor) 활용
  edited_df = st.data_editor(
      st.session_state.df_data,
      num_rows="dynamic",
      use_container_width=True,
      key="support_editor",
  )

  st.divider()

  # 각 파일별 원본 텍스트 서랍장 제공
  with st.expander("🔍 업로드된 도면의 전체 텍스트 원본 확인하기 (복사 참고용)"):
    for idx, f in enumerate(uploaded_files):
      with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(f.getvalue())
        tmp_path = tmp.name
      texts = extract_all_texts_from_dxf(tmp_path)

      st.markdown(f"**파일 이름: {f.name}**")
      st.info(
          " / ".join(texts)
      )  # 한 줄로 쭉 나열해서 복사하기 편하게 보여줌
      st.markdown("---")

  # 엑셀 다운로드 버튼 (내부 관리용 _raw_texts 컬럼은 제외하고 다운로드)
  output = BytesIO()
  export_df = edited_df.drop(
      columns=[col for col in edited_df.columns if col.startswith("_")]
  )

  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    export_df.to_excel(writer, index=False, sheet_name="Spring_Support_Data")
  excel_data = output.getvalue()

  st.download_button(
      label="📥 완성된 엑셀 파일(.xlsx) 다운로드",
      data=excel_data,
      file_name="Spring_Support_Data_Final.xlsx",
      mime=(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
  )
