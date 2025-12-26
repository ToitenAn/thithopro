import streamlit as st
from docx2python import docx2python
import google.generativeai as genai
import random
import re

# --- CẤU HÌNH ---
st.set_page_config(page_title="ThiTho Pro - Lập Trình Mạng", layout="wide")
# API Key của bạn từ ảnh trước
API_KEY = "AIzaSyDltPif--RgiBgVARciWVTrmLCHWUr7ZW8"
genai.configure(api_key=API_KEY)

# Giao diện CSS
st.markdown("""
    <style>
    .question-box { background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 6px solid #007bff; margin-bottom: 20px; }
    .question-text { font-size: 19px; font-weight: bold; color: #333; }
    </style>
    """, unsafe_allow_html=True)

if 'data_thi' not in st.session_state:
    st.session_state.update({'data_thi': None, 'user_answers': {}, 'current_idx': 0, 'ex_cache': {}})

# --- HÀM GIẢI THÍCH AI ---
def ai_explain(q, c, u):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Giải thích tại sao '{c}' là đáp án đúng cho câu hỏi: {q}. Người học chọn sai là '{u}'. Trả lời ngắn gọn bằng tiếng Việt."
        return model.generate_content(prompt).text
    except: return "Không thể kết nối AI lúc này."

# --- HÀM ĐỌC FILE TỐI ƯU CHO FILE "Lập trình mạng.docx" ---
def process_docx(uploaded_file):
    with open("temp.docx", "wb") as f: f.write(uploaded_file.getbuffer())
    try:
        with docx2python("temp.docx") as doc:
            # Lấy toàn bộ text thô từ file
            text_content = doc.text
            # Chia file theo từ khóa "Câu "
            sections = re.split(r'\nCâu\s+\d+', text_content)
            
            data = []
            for sec in sections:
                lines = [l.strip() for l in sec.split('\n') if l.strip()]
                if len(lines) < 2: continue
                
                # Tìm đề bài (thường là dòng chứa "HA(" hoặc dòng ngay sau "Câu X")
                question = ""
                options = []
                correct = ""
                
                for line in lines:
                    if "HA(" in line or '="' in line:
                        # Trích xuất nội dung trong ngoặc kép của HA(x) = "..."
                        match = re.search(r'=\s*"(.*)"', line)
                        question = match.group(1) if match else line
                    elif line.startswith("*"): # Đáp án đúng có dấu *
                        ans = line.replace("*", "").strip().strip('"')
                        options.append(ans)
                        correct = ans
                    elif not any(x in line for x in ["(Một đáp án)", "Phần 1", "TA("]):
                        # Các dòng còn lại là đáp án thường
                        ans = line.strip('"')
                        if ans: options.append(ans)
                
                if question and correct:
                    data.append({"question": question, "options": list(set(options)), "correct": correct})
            return data
    except Exception as e:
        st.error(f"Lỗi: {e}")
        return None

# --- GIAO DIỆN ---
with st.sidebar:
    st.header("🎮 ĐIỀU KHIỂN")
    file = st.file_uploader("Tải file Lập trình mạng.docx", type=["docx"])
    if file and st.button("🚀 BẮT ĐẦU HỌC"):
        res = process_docx(file)
        if res:
            st.session_state.data_thi = res
            st.session_state.user_answers = {}
            st.session_state.current_idx = 0
            st.rerun()

if st.session_state.data_thi:
    data = st.session_state.data_thi
    idx = st.session_state.current_idx
    item = data[idx]

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f'<div class="question-box"><div class="question-text">Câu {idx+1}/{len(data)}: {item["question"]}</div></div>', unsafe_allow_html=True)
        
        answered = idx in st.session_state.user_answers
        choice = st.radio("Chọn đáp án đúng:", item['options'], key=f"q_{idx}", index=None if not answered else item['options'].index(st.session_state.user_answers[idx]), disabled=answered)
        
        if choice and not answered:
            st.session_state.user_answers[idx] = choice
            st.rerun()
            
        if answered:
            if st.session_state.user_answers[idx] == item['correct']:
                st.success("Chính xác! 🎉")
            else:
                st.error(f"Sai rồi. Đáp án đúng là: {item['correct']}")
                if st.button("💡 Tại sao sai? (Hỏi AI)"):
                    st.session_state.ex_cache[idx] = ai_explain(item['question'], item['correct'], st.session_state.user_answers[idx])
                if idx in st.session_state.ex_cache:
                    st.info(st.session_state.ex_cache[idx])

        st.write("---")
        c1, c2 = st.columns(2)
        if c1.button("⬅ Câu trước"): st.session_state.current_idx = max(0, idx-1); st.rerun()
        if c2.button("Câu tiếp ➡"): st.session_state.current_idx = min(len(data)-1, idx+1); st.rerun()
    
    with col2:
        st.write("### 🚩 Phím tắt")
        # Hiển thị lưới câu hỏi để nhảy nhanh
        for i in range(0, len(data), 5):
            cols = st.columns(5)
            for j in range(5):
                curr = i + j
                if curr < len(data):
                    btn_label = f"{curr+1}"
                    if curr in st.session_state.user_answers:
                        btn_label += "✅" if st.session_state.user_answers[curr] == data[curr]['correct'] else "❌"
                    if cols[j].button(btn_label, key=f"m_{curr}"):
                        st.session_state.current_idx = curr; st.rerun()
else:
    st.warning("Vui lòng tải file 'Lập trình mạng.docx' ở thanh bên trái để bắt đầu.")
