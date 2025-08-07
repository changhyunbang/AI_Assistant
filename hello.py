import streamlit as st

# 페이지 제목 설정
st.title("Hello World!")

# 간단한 텍스트 표시
st.write("Streamlit을 사용한 첫 번째 웹 애플리케이션입니다.")

# 추가적인 텍스트 스타일링
st.header("환영합니다!")
st.subheader("이것은 서브헤더입니다.")

# 마크다운 사용
st.markdown("**굵은 텍스트**와 *기울임 텍스트*를 표시할 수 있습니다.")

# 성공 메시지
st.success("Streamlit 애플리케이션이 성공적으로 실행되었습니다!")

# 정보 메시지
st.info("이 애플리케이션은 Streamlit으로 만들어졌습니다.")

# 풍선 효과 (선택사항)
if st.button("축하 버튼 클릭!"):
    st.balloons()
    st.write("축하합니다! 🎉")