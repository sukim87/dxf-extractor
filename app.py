import tempfile
import ezdxf
import streamlit as st

# 1. 웹페이지 제목 꾸미기
st.title("📁 도면(DXF) 텍스트 및 BOM 추출기")
st.write(
    "변환된 DXF 파일을 업로드하면 도면 안의 텍스트와 규격 정보를 찾아줍니다."
)

# 2. 파일 업로드 박스 만들기
uploaded_file = st.file_uploader("DXF 파일을 올려주세요", type=["dxf"])

if uploaded_file is not None:
  # 업로드한 파일을 파이썬이 읽을 수 있도록 임시 파일로 저장
  with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
    tmp.write(uploaded_file.getvalue())
    tmp_path = tmp.name

  try:
    # 3. ezdxf로 도면 파일 읽기
    doc = ezdxf.readfile(tmp_path)
    msp = doc.modelspace()

    extracted_texts = []

    # 도면 안의 일반 텍스트(TEXT, MTEXT) 긁어오기
    for entity in msp.query("TEXT MTEXT"):
      text_content = (
          entity.dxf.text if entity.dxftype() == "TEXT" else entity.text
      )
      if text_content.strip():
        extracted_texts.append(text_content)

    # 4. 결과 화면에 보여주기
    st.success(
        f"분석 완료! 총 {len(extracted_texts)}개의 텍스트를 찾았습니다."
    )

    # 보기 좋게 표나 리스트로 출력
    st.subheader("🔍 추출된 텍스트 목록")
    for idx, text in enumerate(extracted_texts, 1):
      st.text(f"{idx}. {text}")

  except Exception as e:
    st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")