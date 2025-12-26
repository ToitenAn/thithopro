import streamlit as st
from docx2python import docx2python
import google.generativeai as genai
import random
import re

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="ThiTho Pro - Lập Trình Mạng", layout="wide")

# --- HÀM GIẢI THÍCH AI (TỰ ĐỘNG DÒ MODEL) ---
def get_ai_explanation(api_key, question, correct_answer, user_answer):
    try:
        api_key = api_key.strip()
        genai.configure(api_key=api_key)
        
        # Danh sách model thử dần từ mới đến cũ
        models_to_try = [
            'gemini-1.5-flash', 
            'gemini-1.5-pro', 
            'gemini-pro',
            'models/gemini-1.0-pro'
        ]
        
        prompt = f"""
        Bạn là giảng viên môn Lập trình mạng. 
        Câu hỏi: {question}
        Đáp án đúng: {correct_answer}
        Người học chọn sai: {user_answer}
        Giải thích ngắn gọn tại sao {correct_answer} đúng. Dùng tiếng Việt.
        """

        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and response.text:
                    return f"(Sử dụng model: {model_name})\n\n{response.text}"
            except Exception:
                continue # Nếu model này bị 404, thử model tiếp theo
        
        return "❌ Không tìm thấy model nào khả dụng. Hãy kiểm tra lại vùng hỗ trợ của tài khoản Google AI."
    except Exception as e:
        return f"❌ Lỗi hệ thống: {str(e)}"

# --- HÀM XỬ LÝ FILE WORD (DÀNH RIÊNG CHO FILE CỦA BẠN) ---
def process_network_docx(uploaded_file):
    with open("temp.docx", "wb") as f:
        f.write(uploaded_file.getbuffer())
    try:
        with docx2python("temp.docx") as doc:
            full_text = doc.text
            sections = re.split(r'\nCâu\s+\d+', full_text)
            final_data = []
            for sec in sections:
                lines = [l.strip() for l in sec.split('\n') if l.strip()]
                if not lines: continue
                question, options, correct = "", [], ""
                for line in lines:
                    if 'HA(' in line and '="' in line:
                        m = re.search(r'=\s*"(.*)"', line)
                        if m: question = m.group(1)
                    if line.startswith('*'):
                        clean = line.replace('*', '').strip().strip('"')
                        options.append(clean); correct = clean
                    elif not any(x in line for x in ["(Một đáp án)", "HA(", "TA(", "Phần 1"]):
                        clean = line.strip().strip('"')
                        if clean and clean not in options: options.append(clean)
                if question and correct:
                    final_data.append({"question": question, "options": options, "correct": correct})
            return final_data
    except Exception as e:
        return None

# --- GIAO DIỆN STREAMLIT ---
if 'data_thi' not in st.session_state:
    st.session_state.update({'data_thi': None, 'user_answers': {}, 'current_idx': 0, 'ex_cache': {}})

with st.sidebar:
    st.header("🔑 AI KEY")
    # Tự điền Key mới của bạn vào đây
    user_key = st.text_input("Dán API Key:", value="AIzaSyCUkNGMJAuz4oZHyAMccN6W8zN4B6U8hWk", type="password")
    file = st.file_uploader("Tải file Lập trình mạng.docx", type=["docx"])
    if file and st.button("🚀 BẮT ĐẦU"):
        data = process_network_docx(file)
        if data:
            st.session_state.data_thi = data
            st.session_state.user_answers = {}
            st.session_state.current_idx = 0
            st.rerun()

if st.session_state.data_thi:
    data = st.session_state.data_thi
    idx = st.session_state.current_idx
    item = data[idx]
    
    col_main, col_nav = st.columns([3, 1])
    
    with col_main:
        st.info(f"Câu {idx + 1} / {len(data)}")
        st.subheader(item["question"])
        
        answered = idx in st.session_state.user_answers
        choice = st.radio("Chọn đáp án:", item['options'], key=f"q_{idx}", index=None if not answered else item['options'].index(st.session_state.user_answers[idx]), disabled=answered)
        
        if choice and not answered:
            st.session_state.user_answers[idx] = choice
            st.rerun()
            
        if answered:
            if st.session_state.user_answers[idx] == item['correct']:
                st.success("Đúng rồi! ✅")
            else:
                st.error(f"Sai rồi! Đáp án đúng: {item['correct']}")
                if user_key and st.button("💡 Giải thích bằng AI"):
                    with st.spinner("AI đang tìm model phù hợp..."):
                        st.session_state.ex_cache[idx] = get_ai_explanation(user_key, item['question'], item['correct'], st.session_state.user_answers[idx])
                if idx in st.session_state.ex_cache:
                    st.write("---")
                    st.markdown(st.session_state.ex_cache[idx])

        st.write("---")
        c1, c2 = st.columns(2)
        if c1.button("⬅ Câu trước"): st.session_state.current_idx = max(0, idx-1); st.rerun()
        if c2.button("Sau ➡"): st.session_state.current_idx = min(len(data)-1, idx+1); st.rerun()

    with col_nav:
        st.write("### Mục lục")
        for i in range(0, len(data), 4):
            cols = st.columns(4)
            for j in range(4):
                if i+j < len(data):
                    label = f"{i+j+1}"
                    if i+j in st.session_state.user_answers:
                        label += "✅" if st.session_state.user_answers[i+j] == data[i+j]['correct'] else "❌"
                    if cols[j].button(label, key=f"n_{i+j}"):
                        st.session_state.current_idx = i+j; st.rerun()
