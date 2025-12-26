import streamlit as st
from docx2python import docx2python
import google.generativeai as genai
import random
import re

# --- CẤU HÌNH ---
st.set_page_config(page_title="ThiTho Pro - Lập Trình Mạng", layout="wide")

# Model chuẩn bạn vừa tìm thấy
# Mình chọn bản 2.0 Flash vì nó cực nhanh và ổn định
SELECTED_MODEL = "models/gemini-2.0-flash"

st.markdown("""
    <style>
    .main .block-container { max-width: 95% !important; padding-top: 2rem !important; }
    .question-box { background: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .question-text { font-size: 20px !important; font-weight: 700; color: #1f1f1f; }
    .ai-explanation { background-color: #f0f7ff; border-left: 5px solid #007bff; padding: 15px; margin-top: 15px; border-radius: 8px; color: #1a1a1a; line-height: 1.6; }
    </style>
    """, unsafe_allow_html=True)

if 'data_thi' not in st.session_state:
    st.session_state.update({'data_thi': None, 'user_answers': {}, 'current_idx': 0, 'ex_cache': {}})

# --- HÀM GIẢI THÍCH AI ---
def get_ai_explanation(api_key, question, correct_answer, user_answer):
    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel(SELECTED_MODEL)
        prompt = f"""
        Bạn là giảng viên môn Lập trình mạng. 
        Câu hỏi: {question}
        Đáp án đúng là: {correct_answer}
        Người học chọn sai là: {user_answer}
        Hãy giải thích ngắn gọn, súc tích tại sao đáp án đúng lại là {correct_answer}. Trả lời bằng tiếng Việt.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Lỗi: {str(e)}"

# --- HÀM ĐỌC FILE WORD ---
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
                    elif not any(x in line for x in ["đáp án", "HA(", "TA(", "Phần"]):
                        clean = line.strip().strip('"')
                        if clean and clean not in options: options.append(clean)
                if question and correct:
                    final_data.append({"question": question, "options": options, "correct": correct})
            return final_data
    except Exception as e:
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔑 CẤU HÌNH")
    user_key = st.text_input("Dán API Key của bạn:", value="AIzaSyCUkNGMJAuz4oZHyAMccN6W8zN4B6U8hWk", type="password")
    file = st.file_uploader("Tải file Lập trình mạng.docx", type=["docx"])
    if file and st.button("🚀 BẮT ĐẦU", use_container_width=True):
        data = process_network_docx(file)
        if data:
            st.session_state.data_thi = data
            st.session_state.user_answers = {}
            st.session_state.current_idx = 0
            st.session_state.ex_cache = {}
            st.rerun()

# --- GIAO DIỆN CHÍNH ---
if st.session_state.data_thi:
    data = st.session_state.data_thi
    idx = st.session_state.current_idx
    item = data[idx]
    
    col_l, col_m, col_r = st.columns([1, 2.5, 1.2])
    with col_m:
        st.markdown(f'<div class="question-box"><div class="question-text">Câu {idx + 1}: {item["question"]}</div></div>', unsafe_allow_html=True)
        
        ans = idx in st.session_state.user_answers
        choice = st.radio("Chọn đáp án:", item['options'], key=f"q_{idx}", index=None if not ans else item['options'].index(st.session_state.user_answers[idx]), disabled=ans)
        
        if choice and not ans:
            st.session_state.user_answers[idx] = choice
            st.rerun()
            
        if ans:
            if st.session_state.user_answers[idx] == item['correct']:
                st.success("Đúng rồi! ✅")
            else:
                st.error(f"Sai rồi! Đáp án đúng: {item['correct']}")
                if user_key and st.button("💡 Giải thích bằng AI"):
                    with st.spinner("AI Gemini 2.0 đang phân tích..."):
                        st.session_state.ex_cache[idx] = get_ai_explanation(user_key, item['question'], item['correct'], st.session_state.user_answers[idx])
                if idx in st.session_state.ex_cache:
                    st.markdown(f'<div class="ai-explanation">{st.session_state.ex_cache[idx]}</div>', unsafe_allow_html=True)

        st.write("---")
        b1, b2 = st.columns(2)
        if b1.button("⬅ Trước"): st.session_state.current_idx = max(0, idx-1); st.rerun()
        if b2.button("Sau ➡"): st.session_state.current_idx = min(
