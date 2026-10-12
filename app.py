import os
import re
import tempfile
from io import BytesIO
import ezdxf
import pandas as pd
import streamlit as st

# 페이지 레이아웃 설정
st.set_page_config(
    page_title="Spring Support 도면 데이터 추출기", layout="wide"
)

st.title("📊 Spring Support 도면 데이터 엑셀 자동 변환기")
st.write(
    "DXF 파일을 업로드하면 도면에서 규격, 하중(Hot/Cold Load), 높이 등의"
    " 정보를 추출하여 지정하신 표 형식의 엑셀로 만들어 줍니다."
)

# 파일 업로드 (복수 선택 가능)
uploaded_files = st.file_uploader(
    "DXF 파일을 업로드하세요 (복수 선택 가능)", type=["dxf"], accept_multiple_files=True
)


def extract_support_data_from_dxf(file_path):
  """DXF 파일에서 텍스트를 읽어 주요 항목을 매칭하고 전체 텍스트를 반환하는 함수"""
  try:
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()
  except Exception as e:
    return None, []

  # 도면 내 모든 텍스트 수집 (위치 정보 포함: x, y, text)
  texts = []
  for entity in msp.query("TEXT MTEXT"):
    txt = entity.dxf.text if entity.dxftype() == "TEXT" else entity.text
    if txt.strip():
      pos = entity.dxf.insert
      texts.append({"x": pos.x, "y": pos.y, "text": txt.strip()})

  # 도면 내 전체 텍스트 리스트
  all_text_list = [t["text"] for t in texts]

  # 기본값 설정
  base_name = os.path.basename(file_path).replace(".dxf", "")
  dwg_no = base_name
  support_tag = "N/A"
  type_size = "N/A"

  # 정규식을 이용해 태그나 규격 패턴 찾기
  for t in all_text_list:
    if re.match(r"^SH\d+-\d+", t, re.IGNORECASE):
      support_tag = t
    elif re.match(r"^[A-Z]{2,3}-\d+-\d+", t, re.IGNORECASE):
      type_size = t

  # 표에 들어갈 데이터 구조 (현재는 빈 값으로 두고 추후 값 매칭 확장 가능)
  row_data = {
      "DWG No": dwg_no,
      "SUPPORT TAG No.": support_tag,
      "Type & Size": type_size,
      "Hot Load (단위 : N)": "",
      "Cold Load (단위 : N)": "",
      "Hot Point (단위 : mm)": "",
      "Cold Point (단위 : mm)": "",
      "Hanger 설치높이": "",
      "STANCHION 높이": "",
  }

  return row_data, all_text_list


if uploaded_files:
  extracted_data_list = []

  with st.spinner("도면 파일을 분석하는 중입니다..."):
    for uploaded_file in uploaded_files:
      with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

      row_data, all_texts = extract_support_data_from_dxf(tmp_path)
      if row_data:
        extracted_data_list.append((row_data, all_texts))

  if extracted_data_list:
    # 데이터프레임 생성
    df = pd.DataFrame([item[0] for item in extracted_data_list])

    st.subheader("📋 추출된 데이터 미리보기")
    st.dataframe(df, use_container_width=True)

    # [디버깅용] 도면에서 읽어온 전체 텍스트 원본 확인 박스
    with st.expander("🔍 도면에서 읽어온 전체 텍스트 원본 보기 (클릭)"):
      for idx, (row_data, all_texts) in enumerate(extracted_data_list):
        st.markdown(f"**파일 #{idx+1} ({row_data['DWG No']}) 원본 텍스트 목록**")
        st.write(all_texts)
        st.divider()

    # 엑셀 다운로드 버튼 생성
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
      df.to_excel(writer, index=False, sheet_name="Support_Data")
    excel_data = output.getvalue()

    st.download_button(
        label="📥 엑셀 파일(.xlsx)로 다운로드",
        data=excel_data,
        file_name="Spring_Support_Data.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
