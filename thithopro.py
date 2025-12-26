import streamlit as st
from docx import Document
from docx.shared import RGBColor
from docx.enum.text import WD_COLOR_INDEX
import google.generativeai as genai
import random
import time
import io
import PyPDF2

# --- CẤU HÌNH BẢO MẬT KEY ---
HIDDEN_API_KEY = "AIzaSyCUkNGMJAuz4oZHyAMccN6W8zN4B6U8hWk" 

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="ThiTho Pro - Final Edition", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main .block-container { max-width: 95% !important; padding-top: 2rem !important; }
    .question-box { background: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .question-text { font-size: 20px !important; font-weight: 700; color: #1f1f1f; margin-bottom: 15px; white-space: pre-wrap; font-family: 'Consolas', monospace; line-height: 1.6; }
    .ai-explanation { background-color: #f8faff; border-left: 6px solid #007bff; padding: 20px; margin-top: 15px; border-radius: 8px; color: #1a1a1a; font-size: 17px; line-height: 1.7; }
    .warning-box { background-color: #fff3cd; border-left: 6px solid #ffc107; padding: 15px; border-radius: 8px; margin-bottom: 15px; color: #856404; font-weight: bold; }
    div[data-testid="stHorizontalBlock"] button:has(span:contains("✅")) { background-color: #28a745 !important; color: white !important; }
    div[data-testid="stHorizontalBlock"] button:has(span:contains("❌")) { background-color: #ff4b4b !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- QUẢN LÝ TRẠNG THÁI ---
for key in ['data_thi', 'user_answers', 'current_idx', 'next_trigger', 'ex_cache']:
    if key not in st.session_state:
        st.session_state[key] = None if key == 'data_thi' else ({} if key in ['user_answers', 'ex_cache'] else (0 if key == 'current_idx' else False))

# --- HÀM ĐỌC WORD: NHẬN DIỆN MÀU ĐỎ, HIGHLIGHT, DẤU * ---
def read_docx(file_bytes):
    try:
        doc = Document(io.BytesIO(file_bytes))
        data, current_q = [], None
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text: continue
            
            # 1. Kiểm tra dấu hiệu đáp án đúng
            is_correct_style = False
            # Kiểm tra dấu * ở đầu hoặc cuối dòng
            has_star = text.startswith("*") or text.endswith("*")
            
            for run in para.runs:
                # Kiểm tra màu đỏ (RGB: 255, 0, 0)
                if (run.font.color and run.font.color.rgb == RGBColor(255, 0, 0)):
                    is_correct_style = True
                # Kiểm tra highlight vàng
                if (run.font.highlight_color == WD_COLOR_INDEX.YELLOW):
                    is_correct_style = True
            
            if has_star: is_correct_style = True

            # 2. Nhận diện tiêu đề câu hỏi (In đậm + bắt đầu bằng chữ "Câu")
            is_bold = any(run.bold for run in para.runs)
            is_new_header = text.lower().startswith("câu") and any(char.isdigit() for char in text[:10])

            if is_new_header:
                current_q = {"question": text, "options": [], "correct": None}
                data.append(current_q)
            elif current_q is not None:
                # Nếu là đáp án đúng (Màu đỏ/Highlight/Dấu *)
                if is_correct_style:
                    clean_text = text.replace("*", "").strip()
                    if clean_text not in current_q["options"]:
                        current_q["options"].append(clean_text)
                        current_q["correct"] = clean_text
                # Nếu dòng in đậm (Code Java hoặc nội dung câu hỏi nhiều dòng)
                elif is_bold:
                    current_q["question"] += "\n" + text
                # Nếu là dòng văn bản bình thường (Phương án nhiễu)
                else:
                    clean_text = text.replace("*", "").strip()
                    if clean_text not in current_q["options"]:
                        current_q["options"].append(clean_text)
        
        return [q for q in data if len(q['options']) >= 2]
    except Exception as e:
        st.error(f"Lỗi: {e}"); return None

# --- GIỮ NGUYÊN HÀM AI GIẢI THÍCH ---
def get_ai_explanation(q, options, corr_text):
    try:
        genai.configure(api_key=HIDDEN_API_KEY)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        models.sort(key=lambda x: ("flash" not in x.lower()))
        labels = ["A", "B", "C", "D"]
        corr_label = labels[options.index(corr_text)] if corr_text in options else "?"
        
        prompt = f"Phân tích câu hỏi: {q}\nĐáp án: {corr_text}\nTại sao chọn {corr_label}? Giải thích chi tiết bằng tiếng Việt."
        
        for m_name in models:
            try:
                model = genai.GenerativeModel(m_name)
                return model.generate_content(prompt).text
            except: continue
        return "❌ AI đang bận."
    except Exception as e: return f"❌ Lỗi: {str(e)}"

# --- GIAO DIỆN ---
with st.sidebar:
    st.header("⚙️ CÀI ĐẶT")
    file = st.file_uploader("Tải file (.docx)", type=["docx"])
    if file and st.button("🚀 BẮT ĐẦU", use_container_width=True, type="primary"):
        res = read_docx(file.read())
        if res:
            st.session_state.data_thi, st.session_state.user_answers, st.session_state.current_idx, st.session_state.ex_cache = res, {}, 0, {}
            st.rerun()

if st.session_state.data_thi:
    data, idx = st.session_state.data_thi, st.session_state.current_idx
    item, labels = data[idx], ["A", "B", "C", "D"]
    col_l, col_m, col_r = st.columns([1, 2.5, 1.2])
    
    with col_m:
        st.markdown(f'<div class="question-box"><div class="question-text">{item["question"]}</div></div>', unsafe_allow_html=True)
        ans_done = idx in st.session_state.user_answers
        opts_display = [f"{labels[i]}. {opt}" for i, opt in enumerate(item['options'])]
        choice_lbl = st.radio("Đáp án:", opts_display, key=f"r_{idx}", index=item['options'].index(st.session_state.user_answers[idx]) if ans_done else None, disabled=ans_done, label_visibility="collapsed")
        
        if choice_lbl and not ans_done:
            st.session_state.user_answers[idx] = item['options'][opts_display.index(choice_lbl)]
            st.session_state.next_trigger = True; st.rerun()
            
        if ans_done:
            c_idx = item['options'].index(item['correct']) if item['correct'] in item['options'] else 0
            if st.session_state.user_answers[idx] == item['correct']: st.success("Chính xác! ✅")
            else: st.error(f"Sai! Đáp án đúng: {labels[c_idx]} - {item['correct']}")
            
            if st.button("🔍 Giải thích chuyên sâu"):
                with st.spinner("AI đang phân tích..."):
                    st.session_state.ex_cache[idx] = get_ai_explanation(item['question'], item['options'], item['correct'])
            
            if idx in st.session_state.ex_cache:
                st.markdown(f'<div class="ai-explanation">{st.session_state.ex_cache[idx]}</div>', unsafe_allow_html=True)
        
        st.write("---")
        c1, c2 = st.columns(2)
        if c1.button("⬅ Trước"): st.session_state.current_idx = max(0, idx - 1); st.rerun()
        if c2.button("Sau ➡"): st.session_state.current_idx = min(len(data)-1, idx + 1); st.rerun()
    
    with col_r:
        st.write("### 📑 Mục lục")
        for i in range(0, len(data), 4):
            cols = st.columns(4)
            for j in range(4):
                curr = i + j
                if curr < len(data):
                    lbl = f"{curr+1}"
                    if curr in st.session_state.user_answers: lbl += "✅" if st.session_state.user_answers[curr] == data[curr]['correct'] else "❌"
                    if cols[j].button(lbl, key=f"m_{curr}"): st.session_state.current_idx = curr; st.rerun()

    if st.session_state.next_trigger:
        time.sleep(1); st.session_state.next_trigger = False
        if st.session_state.current_idx < len(data) - 1: st.session_state.current_idx += 1; st.rerun()
