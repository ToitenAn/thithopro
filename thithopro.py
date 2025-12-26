import streamlit as st
from docx2python import docx2python
import google.generativeai as genai
import random
import time
import re
import os

# --- CẤU HÌNH ---
st.set_page_config(page_title="ThiTho Pro - AI Tutor", layout="wide")
API_KEY = "AIzaSyDltPif--RgiBgVARciWVTrmLCHWUr7ZW8"
genai.configure(api_key=API_KEY)

st.markdown("""
    <style>
    .main .block-container { max-width: 95% !important; padding-top: 2rem !important; }
    .question-box { background: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .question-text { font-size: 20px !important; font-weight: 700; color: #1f1f1f; }
    .ai-explanation { background-color: #f0f7ff; border-left: 5px solid #007bff; padding: 20px; margin-top: 15px; border-radius: 8px; color: #1a1a1a; }
    </style>
    """, unsafe_allow_html=True)

if 'data_thi' not in st.session_state:
    st.session_state.data_thi = None
    st.session_state.user_answers = {}
    st.session_state.current_idx = 0
    st.session_state.explanation_cache = {}

def get_ai_explanation(question, correct_answer, user_answer):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Giải thích ngắn gọn tại sao '{correct_answer}' đúng và '{user_answer}' sai cho câu hỏi: {question}. Dùng tiếng Việt."
        return model.generate_content(prompt).text
    except Exception as e: return f"Lỗi AI: {str(e)}"

def process_docx(uploaded_file):
    with open("temp.docx", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    try:
        # html=True giúp giữ lại thẻ <b> cho chữ in đậm
        with docx2python("temp.docx", html=True) as doc:
            all_lines = []
            # Duyệt qua toàn bộ cấu trúc file (body -> table -> row -> cell)
            for part in doc.body:
                for table in part:
                    for row in table:
                        for cell in row:
                            for line in cell:
                                if line.strip(): all_lines.append(line)
            
            data = []
            current_q = None
            
            for line in all_lines:
                text_clean = re.sub('<[^<]+?>', '', line).strip()
                # Đề bài: Chữ đậm (<b>) HOẶC bắt đầu bằng "Câu" HOẶC "Số."
                is_bold = "<b>" in line or "<strong>" in line
                is_q_start = text_clean.lower().startswith("câu") or (text_clean and text_clean[0].isdigit() and "." in text_clean[:5])
                
                if is_bold or is_q_start:
                    current_q = {"question": text_clean, "options": [], "correct": None, "image": None}
                    # Tìm ảnh trong dòng này
                    img_match = re.search(r'----image(\d+)\.(png|jpg|jpeg)----', line)
                    if img_match:
                        img_name = f"image{img_match.group(1)}.{img_match.group(2)}"
                        current_q["image"] = doc.images.get(img_name)
                    data.append(current_q)
                
                elif current_q is not None:
                    # Đáp án: Có dấu * hoặc chữ đỏ/vàng (docx2python thường đánh dấu bằng thẻ span)
                    is_correct = "*" in line or 'color="red"' in line.lower() or 'background="yellow"' in line.lower()
                    
                    # Kiểm tra ảnh trong đáp án (nếu đề bài chưa có ảnh)
                    img_match = re.search(r'----image(\d+)\.(png|jpg|jpeg)----', line)
                    if img_match and not current_q["image"]:
                        img_name = f"image{img_match.group(1)}.{img_match.group(2)}"
                        current_q["image"] = doc.images.get(img_name)

                    clean_ans = text_clean.replace("*", "").strip()
                    if clean_ans and clean_ans not in current_q["options"] and "phần bổ sung" not in clean_ans.lower():
                        current_q["options"].append(clean_ans)
                        if is_correct: current_q["correct"] = clean_ans
            
            return [q for q in data if len(q['options']) >= 1]
    except Exception as e:
        st.error(f"Lỗi đọc file: {e}")
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ CÀI ĐẶT")
    file = st.file_uploader("Tải đề Word (.docx)", type=["docx"])
    t1 = st.checkbox("Đảo câu hỏi")
    t2 = st.checkbox("Đảo đáp án")
    
    if file and st.button("🚀 BẮT ĐẦU", use_container_width=True, type="primary"):
        res = process_docx(file)
        if res:
            st.session_state.data_thi = res
            if t1: random.shuffle(st.session_state.data_thi)
            if t2: 
                for it in st.session_state.data_thi: random.shuffle(it['options'])
            st.session_state.user_answers = {}
            st.session_state.current_idx = 0
            st.session_state.explanation_cache = {}
            st.rerun()
        else:
            st.error("Không tìm thấy câu hỏi nào! Hãy kiểm tra lại file Word có chữ in đậm hoặc chữ 'Câu' không.")

# --- GIAO DIỆN CHÍNH ---
if st.session_state.data_thi:
    data = st.session_state.data_thi
    idx = st.session_state.current_idx
    item = data[idx]
    
    col_l, col_m, col_r = st.columns([1, 2.5, 1.2])
    
    with col_l:
        st.write("### 📊 Thống kê")
        st.metric("🎯 Điểm", f"{(sum(1 for i, a in st.session_state.user_answers.items() if a == data[i]['correct'])/len(data))*10:.2f}")
        st.write(f"Tiến độ: {len(st.session_state.user_answers)}/{len(data)}")

    with col_m:
        st.markdown(f'<div class="question-box"><div class="question-text">Câu {idx + 1}: {item["question"]}</div></div>', unsafe_allow_html=True)
        if item.get("image"): st.image(item["image"], use_container_width=True)
        
        ans = idx in st.session_state.user_answers
        choice = st.radio("Chọn:", item['options'], key=f"r_{idx}", index=item['options'].index(st.session_state.user_answers[idx]) if ans else None, disabled=ans)
        
        if choice and not ans:
            st.session_state.user_answers[idx] = choice
            st.rerun()
            
        if ans:
            if st.session_state.user_answers[idx] == item['correct']: st.success("ĐÚNG! ✅")
            else:
                st.error(f"SAI! ❌ Đáp án: {item['correct']}")
                if st.button("💡 Giải thích"):
                    st.session_state.explanation_cache[idx] = get_ai_explanation(item['question'], item['correct'], st.session_state.user_answers[idx])
                if idx in st.session_state.explanation_cache:
                    st.info(st.session_state.explanation_cache[idx])

        c1, c2 = st.columns(2)
        if c1.button("⬅ Trước"): st.session_state.current_idx = max(0, idx-1); st.rerun()
        if c2.button("Sau ➡"): st.session_state.current_idx = min(len(data)-1, idx+1); st.rerun()

    with col_r:
        st.write("### 📑 Mục lục")
        for i in range(0, len(data), 4):
            cols = st.columns(4)
            for j in range(4):
                if i+j < len(data):
                    if cols[j].button(f"{i+j+1}", key=f"m_{i+j}"):
                        st.session_state.current_idx = i+j; st.rerun()
else:
    st.info("Hãy chọn file và nhấn Bắt đầu.")
