import os
import re
import tempfile
from io import BytesIO
import ezdxf
import pandas as pd
import streamlit as st

# 페이지 레이아웃 설정
st.set_page_config(
    page_title="Spring Support 도면 좌표 분석기", layout="wide"
)

st.title("📊 Spring Support 도면 좌표 기반 데이터 추출기")
st.write(
    "도면 내 텍스트의 (X, Y) 좌표를 분석하여 레이블과 숫자를 매칭하는 진짜"
    " 로직이 적용된 프로그램입니다."
)

uploaded_files = st.file_uploader(
    "DXF 파일을 업로드하세요 (복수 선택 가능)", type=["dxf"], accept_multiple_files=True
)


def extract_data_with_coordinates(file_path):
  """텍스트 좌표(X, Y)를 이용해 키워드 근처의 값을 찾아내는 좌표 매칭 함수"""
  try:
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()
  except Exception as e:
    return None, []

  base_name = os.path.basename(file_path).replace(".dxf", "")
  dwg_no = base_name

  # 1. 모든 텍스트와 좌표 수집
  texts = []
  for entity in msp.query("TEXT MTEXT"):
    txt = entity.dxf.text if entity.dxftype() == "TEXT" else entity.text
    if txt.strip():
      pos = entity.dxf.insert
      # MTEXT의 경우 포맷팅 태그 제거 (\A2; 등)
      clean_txt = re.sub(r"\\À?[A-Za-z0-9]+;?", "", txt).strip()
      texts.append({"x": pos.x, "y": pos.y, "text": clean_txt})

  all_text_list = [t["text"] for t in texts]

  # 기본값 초기화
  support_tag = "N/A"
  type_size = "N/A"
  hot_load = ""
  cold_load = ""
  hot_point = ""
  cold_point = ""
  hanger_height = ""
  stanchion_height = ""

  # 2. 정규식으로 태그 및 규격 먼저 찾기 (이건 확실하게 잡힘)
  for t in all_text_list:
    if re.match(r"^SH\d+-\d+", t, re.IGNORECASE):
      support_tag = t
    elif re.match(r"^[A-Z]{2,3}-\d+-\d+", t, re.IGNORECASE):
      type_size = t

  # 3. [진짜 로직] 좌표 기반 근접 텍스트 탐색 함수
  def find_value_near(keyword, max_dx=50, max_dy=10):
    """특정 키워드 좌표 기준으로 오른쪽에 있는 숫자를 찾는 함수"""
    kw_item = None
    # 키워드 텍스트 찾기 (예: 'Hot Load')
    for item in texts:
      if keyword.lower() in item["text"].lower():
        kw_item = item
        break

    if not kw_item:
      return ""

    # 키워드 우측 또는 바로 밑에 위치한 후보군 찾기
    candidates = []
    for item in texts:
      # 같은 아이템이거나 X가 너무 왼쪽이면 제외
      if item == kw_item:
        continue
      dx = item["x"] - kw_item["x"]
      dy = abs(item["y"] - kw_item["y"])

      # 키워드 기준 우측(dx > 0) 이고 높이 오차가 적은(dy < max_dy) 텍스트 탐색
      if 0 < dx <= max_dx and dy <= max_dy:
        candidates.append((dx, item["text"]))

    if candidates:
      # 가장 가까이에 있는 텍스트 반환
      candidates.sort(key=lambda x: x[0])
      return candidates[0][1]

    return ""

  # 키워드 근처 값 탐색 실행 (도면 스타일에 따라 키워드 명칭은 조정 필요)
  # 예시 키워드: 'Hot', 'Cold', 'Load', 'Height' 등
  hot_load = find_value_near("Hot Load") or find_value_near("Hot")
  cold_load = find_value_near("Cold Load") or find_value_near("Cold")
  hot_point = find_value_near("Hot Point")
  cold_point = find_value_near("Cold Point")

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

  return row_data, all_text_list


if uploaded_files:
  extracted_data_list = []

  with st.spinner("도면 좌표 정밀 분석 중..."):
    for uploaded_file in uploaded_files:
      with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

      row_data, all_texts = extract_data_with_coordinates(tmp_path)
      if row_data:
        extracted_data_list.append((row_data, all_texts))

  if extracted_data_list:
    df = pd.DataFrame([item[0] for item in extracted_data_list])

    st.subheader("📋 좌표 분석 결과 미리보기")
    st.dataframe(df, use_container_width=True)

    with st.expander("🔍 도면 전체 텍스트 및 좌표 확인"):
      for idx, (row_data, all_texts) in enumerate(extracted_data_list):
        st.markdown(f"**파일 #{idx+1} ({row_data['DWG No']})**")
        st.write(all_texts)
        st.divider()

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
