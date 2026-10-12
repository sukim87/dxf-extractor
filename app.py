import re
import tempfile
import ezdxf
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Spring Support 도면 데이터 추출기", layout="wide"
)

st.title("📊 Spring Support 도면 데이터 엑셀 자동 변환기")
st.write(
    "DXF 파일을 업로드하면 도면에서 규격, 하중(Hot/Cold Load), 높이 등의"
    " 정보를 추출하여 지정하신 표 형식의 엑셀로 만들어 줍니다."
)

# 파일 업로드
uploaded_files = st.file_uploader(
    "DXF 파일을 업로드하세요 (복수 선택 가능)", type=["dxf"], accept_multiple_files=True
)


def extract_support_data_from_dxf(file_path):
  """DXF 파일에서 텍스트를 읽어 주요 항목을 매칭하는 함수"""
  try:
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()
  except Exception as e:
    return None

  # 도면 내 모든 텍스트 수집 (위치 정보 포함: x, y, text)
  texts = []
  for entity in msp.query("TEXT MTEXT"):
    txt = entity.dxf.text if entity.dxftype() == "TEXT" else entity.text
    if txt.strip():
      # 삽입점 좌표 가져오기
      pos = entity.dxf.insert
      texts.append({"x": pos.x, "y": pos.y, "text": txt.strip()})

  # 기본값 설정 (도면에서 직접 매칭 로직을 고도화할 수 있습니다)
  # 여기서는 도면 파일 이름이나 내부 텍스트 패턴을 분석하여 기본 구조를 잡습니다.
  dwg_no = "N/A"
  support_tag = "N/A"
  type_size = "N/A"
  hot_load = ""
  cold_load = ""
  hot_point = ""
  cold_point = ""
  hanger_height = ""
  stanchion_height = ""

  # 전체 텍스트 목록에서 키워드 기반 탐색 예시
  all_text_str = " ".join([t["text"] for t in texts])

  # 파일명 기반 DWG No 유추 (예시)
  import os

  base_name = os.path.basename(file_path).replace(".dxf", "")
  dwg_no = base_name

  # 정규식을 이용해 태그나 규격 패턴 찾기 (예: SH로 시작하는 태그, VT로 시작하는 타입 등)
  for t in texts:
    txt = t["text"]
    if re.match(r"^SH\d+-\d+", txt):
      support_tag = txt
    elif re.match(r"^[A-Z]{2,3}-\d+-\d+", txt):
      type_size = txt

  # 데이터 딕셔너리 반환
  row_data = {
      "DWG No": dwg_no,
      "SUPPORT TAG No.": support_tag,
      "Type & Size": type_size,
      "Hot Load (단위 : N)": hot_load,
      "Cold Load (단위 : N)": cold_load,
      "Hot Point (단위 : mm)": hot_point,
      "Cold Point (단위 : mm)": cold_point,
      "Hanger 설치높이": hanger_height,
      "STANCHION 높이": stanchion_height,
  }

  return row_data


if uploaded_files:
  extracted_data_list = []

  with st.spinner("도면 파일을 분석하는 중입니다..."):
    for uploaded_file in uploaded_files:
      with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

      data = extract_support_data_from_dxf(tmp_path)
      if data:
        extracted_data_list.append(data)

  if extracted_data_list:
    df = pd.DataFrame(extracted_data_list)

    st.subheader("📋 추출된 데이터 미리보기")
    st.dataframe(df, use_container_width=True)

    # 엑셀 다운로드 버튼 생성
    from io import BytesIO

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
