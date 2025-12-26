import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Check Key Dứt Điểm", page_icon="🧪")

st.title("🧪 Tool Test Key & Model")

# Nhập Key
key_input = st.text_input("Dán API Key vào đây:", type="password")

if key_input:
    try:
        # Cấu hình API
        genai.configure(api_key=key_input.strip())
        
        if st.button("🚀 Kiểm tra Model khả dụng"):
            with st.spinner("Đang truy vấn Google AI..."):
                # Lấy danh sách model chuẩn từ hệ thống
                models = genai.list_models()
                valid_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
                
                if valid_models:
                    st.success(f"✅ Key hoạt động! Tìm thấy {len(valid_models)} model.")
                    
                    # Hiển thị danh sách model chuẩn để bạn copy
                    st.write("### Danh sách Model (Tên chuẩn):")
                    for name in valid_models:
                        st.code(name)
                    
                    # Thử chat với model đầu tiên trong danh sách
                    target = valid_models[0]
                    st.write(f"---")
                    st.write(f"🤖 Đang thử Chat với: `{target}`")
                    
                    model = genai.GenerativeModel(target)
                    response = model.generate_content("Chào bạn, tôi là người dùng mới.")
                    
                    st.success("💬 AI đã phản hồi thành công:")
                    st.info(response.text)
                else:
                    st.error("❌ Key đúng nhưng tài khoản này chưa được cấp quyền dùng bất kỳ model nào.")
                    
    except Exception as e:
        st.error("❌ Lỗi kết nối!")
        # Hiện lỗi chi tiết để bắt bệnh
        error_msg = str(e)
        st.code(error_msg)
        
        if "API_KEY_INVALID" in error_msg:
            st.warning("👉 Key bạn nhập bị sai hoặc đã bị xóa.")
        elif "404" in error_msg:
            st.warning("👉 Lỗi 404: Do tên Model trong code không khớp với tên Google quy định.")
