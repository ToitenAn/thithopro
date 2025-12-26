import streamlit as st
from docx import Document
from docx.shared import RGBColor
from docx.enum.text import WD_COLOR_INDEX
import google.generativeai as genai
import random
import time
import io
import PyPDF2

# --- CẤU HÌNH API ---
HIDDEN_API_KEY = "AIzaSyCUkNGMJAuz4oZHyAMccN6W8zN4B6U8hWk" 

st.set_page_config(page_title="ThiTho Pro - Fix Code", layout="wide")

st.markdown("""
    <style>
    .question-box { background: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 20px; }
    .question-text { font-size: 18px !important; font-weight: 600; white-space: pre-wrap; font-family: 'Consolas', monospace; color: #2c3e50; }
    .ai-explanation { background-color: #f4f9ff; border-left: 5px solid #007bff; padding: 15px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

def read_docx(file_bytes):
    try:
        doc = Document(io.BytesIO(file_bytes))
        data = []
        current_q = None
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text: continue
            
            # Kiểm tra định dạng đáp án (Đỏ hoặc Vàng)
            is_answer_style = False
            for run in para.runs:
                if (run.font.color and run.font.color.rgb == RGBColor(255, 0, 0)) or \
                   (run.font.highlight_color == WD_COLOR_INDEX.YELLOW):
                    is_answer_style = True
                    break
            
            # Nhận diện tiêu đề Câu hỏi (Câu 1, Câu 2...)
            is_new_q = text.lower().startswith("câu") and any(char.isdigit() for char in text[:10])

            if is_new_q:
                current_q = {"question": text, "options": [], "correct": None}
                data.append(current_q)
            elif current_q is not None:
                # Nếu dòng có định dạng đáp án -> Lưu vào options
                if is_answer_style:
                    clean_opt = text.strip()
                    if clean_opt not in current_q["options"]:
                        current_q["options"].append(clean_opt)
                        current_q["correct"] = clean_opt
                # Nếu dòng in đậm và ngắn -> Có thể là đáp án không màu
                elif any(run.bold for run in para.runs) and len(text) < 100:
                    clean_opt = text.strip()
                    if clean_opt not in current_q["options"]:
                        current_q["options"].append(clean_opt)
                # Nếu không phải 2 cái trên -> Chắc chắn là nội dung Code Java
                else:
                    current_q["question"] += "\n" + text
        
        return [q for q in data if q['options']]
    except Exception as e:
        st.error(f"Lỗi: {e}"); return None

# --- PHẦN GIAO DIỆN CHÍNH (STREAMLIT) ---
if 'data_thi' not in st.session_state:
    st.session_state.update({'data_thi': None, 'user_answers': {}, 'current_idx': 0, 'ex_cache': {}})

with st.sidebar:
    st.header("⚙️ MENU")
    file = st.file_uploader("Tải file (.docx, .pdf)", type=["docx", "pdf"])
    if file and st.button("🚀 BẮT ĐẦU"):
        if file.name.endswith(".pdf"):
            # Hàm đọc PDF tương tự bản trước nhưng thêm PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
            # (Logic tách câu PDF ở đây...)
            st.warning("Tính năng PDF đang được tối ưu, khuyến khích dùng Word.")
        else:
            res = read_docx(file.read())
            if res:
                st.session_state.update({'data_thi': res, 'user_answers': {}, 'current_idx': 0, 'ex_cache': {}})
                st.rerun()

if st.session_state.data_thi:
    item = st.session_state.data_thi[st.session_state.current_idx]
    idx = st.session_state.current_idx
    
    col_l, col_m, col_r = st.columns([1, 3, 1])
    
    with col_m:
        # Hiển thị khối câu hỏi + Code
        st.markdown(f'<div class="question-box"><div class="question-text">{item["question"]}</div></div>', unsafe_allow_html=True)
        
        answered = idx in st.session_state.user_answers
        choice = st.radio("Chọn đáp án:", item['options'], key=f"q_{idx}", index=None if not answered else item['options'].index(st.session_state.user_answers[idx]), disabled=answered)
        
        if choice and not answered:
            st.session_state.user_answers[idx] = choice
            st.rerun()
            
        if answered:
            if st.session_state.user_answers[idx] == item['correct']:
                st.success("Đúng rồi! ✅")
            else:
                st.error(f"Sai rồi. Đáp án đúng: {item['correct']}")
            
            if st.button("💡 Giải thích chuyên sâu"):
                genai.configure(api_key=HIDDEN_API_KEY)
                model = genai.GenerativeModel('gemini-1.5-flash')
                resp = model.generate_content(f"Giải thích câu hỏi Java/Mạng: {item['question']}. Đáp án: {item['correct']}. Tại sao đúng và tại sao các câu khác sai?")
                st.markdown(f'<div class="ai-explanation">{resp.text}</div>', unsafe_allow_html=True)

        st.write("---")
        c1, c2 = st.columns(2)
        if c1.button("⬅ Câu trước") and idx > 0: st.session_state.current_idx -= 1; st.rerun()
        if c2.button("Câu sau ➡") and idx < len(st.session_state.data_thi)-1: st.session_state.current_idx += 1; st.rerun()
