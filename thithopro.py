import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Kiểm tra API Key", page_icon="🔑")

st.title("🔑 Tool Check API Key Gemini")

# Nhập Key
api_key = st.text_input("Dán API Key của bạn vào đây:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        
        # Nút bấm để test
        if st.button("🚀 Kiểm tra ngay"):
            with st.spinner("Đang kết nối với Google AI..."):
                # 1. Thử liệt kê các model mà Key này được phép dùng
                available_models = []
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        available_models.append(m.name)
                
                if available_models:
                    st.success("✅ Kết nối thành công!")
                    st.write("### Các model bạn có quyền sử dụng:")
                    for m in available_models:
                        st.code(m)
                    
                    # 2. Thử gọi một câu chào đơn giản bằng model đầu tiên tìm thấy
                    test_model = available_models[0]
                    st.write(f"---")
                    st.write(f"💬 Đang thử gọi model: `{test_model}`...")
                    
                    model = genai.GenerativeModel(test_model)
                    response = model.generate_content("Chào bạn, hãy nói 'OK' nếu bạn nghe thấy tôi.")
                    
                    st.info(f"AI phản hồi: {response.text}")
                else:
                    st.warning("⚠️ Key hợp lệ nhưng không tìm thấy model nào khả dụng.")
                    
    except Exception as e:
        st.error("❌ Lỗi rồi!")
        st.code(str(e))
        st.write("---")
        st.write("👉 **Cách khắc phục lỗi 404:** Nếu danh sách model hiện ra không có `models/gemini-1.5-flash`, bạn phải dùng `models/gemini-pro` trong code chính.")

else:
    st.info("Vui lòng dán mã API Key để bắt đầu kiểm tra.")
