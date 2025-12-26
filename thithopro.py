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

st.set_page_config(page_title="ThiTho Pro", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main .block-container { max-width: 95% !important; padding-top: 2rem !important; }
    .question-box { background: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .question-text { font-size: 20px !important; font-weight: 700; color: #1f1f1f; margin-bottom: 15px; white-space: pre-wrap; }
    .ai-explanation { background-color: #f8faff; border-left: 6px solid #007bff; padding: 20px; margin-top: 15px; border-radius: 8px; font-size: 17px; line-height: 1.7; }
    .warning-box { background-color: #fff3cd; border-left: 6px solid #ffc107; padding: 15px; border-radius: 8px; color: #856404; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- QUẢN LÝ TRẠNG THÁI ---
for key in ['data_thi', 'user_answers', 'current_idx', 'next_trigger', 'ex_cache']:
    if key not in st.session_state:
        st.session_state[key] = None if key == 'data_thi' else ({} if key in ['user_answers', 'ex_cache'] else (0 if key == 'current_idx' else False))

# --- HÀM ĐỌC FILE WORD (ĐÃ FIX LỖI MẤT NỘI DUNG CODE) ---
def read_docx(file_bytes):
    try:
        doc = Document(io.BytesIO(file_bytes))
        data = []
        current_q = None
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text: continue
            
            # Kiểm tra định dạng dòng (In đậm hoặc bắt đầu bằng "Câu")
            is_bold = any(run.bold for run in para.runs)
            is_header = text.lower().startswith("câu") or (text and text[0].isdigit() and "." in text[:5])
            
            # Nếu là tiêu đề câu hỏi mới
            if is_header:
                current_q = {"question": text, "options": [], "correct": None}
                data.append(current_q)
            
            elif current_q is not None:
                # Kiểm tra xem dòng này có phải đáp án đúng không (Chữ đỏ hoặc bôi vàng)
                is_correct_style = False
                for run in para.runs:
                    if (run.font.color and run.font.color.rgb == RGBColor(255, 0, 0)) or \
                       (run.font.highlight_color == WD_COLOR_INDEX.YELLOW):
                        is_correct_style = True
                
                # LOGIC QUAN TRỌNG: 
                # Nếu dòng có chữ đỏ/vàng hoặc in đậm (mà không phải header) -> Coi là đáp án
                # Nếu dòng bình thường (như đoạn code Java) -> Gộp vào nội dung câu hỏi
                if is_correct_style or (is_bold and not is_header):
                    clean_text = text.replace("*", "").strip()
                    if clean_text not in current_q["options"]:
                        current_q["options"].append(clean_text)
                        if is_correct_style: current_q["correct"] = clean_text
                else:
                    # Gộp thêm vào nội dung câu hỏi (cho các đoạn code nhiều dòng)
                    current_q["question"] += "\n" + text

        return [q for q in data if len(q['options']) >= 2]
    except Exception as e:
        st.error(f"Lỗi đọc Word: {e}"); return None

# --- CÁC HÀM AI & PDF GIỮ NGUYÊN ---
def read_pdf(file_bytes):
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        full_text = ""
        for page in reader.pages: full_text += page.extract_text() + "\n"
        lines = full_text.split('\n')
        data, current_q = [], None
        for line in lines:
            line = line.strip()
            if not line: continue
            if line.lower().startswith("câu") or (line and line[0].isdigit() and "." in line[:5]):
                current_q = {"question": line, "options": [], "correct": None}
                data.append(current_q)
            elif current_q is not None and len(current_q["options"]) < 4:
                is_correct = "*" in line
                clean_opt = line.replace("*", "").strip()
                current_q["options"].append(clean_opt)
                if is_correct: current_q["correct"] = clean_opt
        return [q for q in data if len(q['options']) >= 2]
    except Exception as e: st.error(f"Lỗi đọc PDF: {e}"); return None

def get_ai_explanation(q, options, corr_text):
    try:
        genai.configure(api_key=HIDDEN_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        labels = ["A", "B", "C", "D"]
        corr_label = labels[options.index(corr_text)] if corr_text in options else "?"
        prompt = f"Câu hỏi: {q}\nĐáp án: {corr_text}\nGiải thích tại sao chọn {corr_label} và tại sao các câu khác sai. Nếu đáp án tài liệu sai hãy phản biện."
        return model.generate_content(prompt).text
    except: return "❌ AI đang bận."

# --- GIAO DIỆN (GIỮ NGUYÊN CẤU TRÚC 3 CỘT CỦA BẠN) ---
with st.sidebar:
    st.header("⚙️ CÀI ĐẶT")
    file = st.file_uploader("Tải đề (Word/PDF)", type=["docx", "pdf"])
    t1, t2 = st.checkbox("Đảo câu hỏi"), st.checkbox("Đảo đáp án")
    if file and st.button("🚀 BẮT ĐẦU", use_container_width=True, type="primary"):
        fb = file.read()
        res = read_pdf(fb) if file.name.endswith(".pdf") else read_docx(fb)
        if res:
            if t1: random.shuffle(res)
            if t2: [random.shuffle(it['options']) for it in res]
            st.session_state.data_thi, st.session_state.user_answers, st.session_state.current_idx, st.session_state.ex_cache = res, {}, 0, {}
            st.rerun()

if st.session_state.data_thi:
    data, idx = st.session_state.data_thi, st.session_state.current_idx
    item, labels = data[idx], ["A", "B", "C", "D"]
    col_l, col_m, col_r = st.columns([1, 2.5, 1.2])
    
    with col_l:
        with st.container(border=True):
            st.write("### 📊 Thống kê")
            dung = sum(1 for i, ans in st.session_state.user_answers.items() if ans == data[i]['correct'])
            st.write(f"📝 Câu: **{idx+1}/{len(data)}**")
            st.progress((idx + 1) / len(data))
            st.metric("✅ Đúng", dung)

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
            if st.session_state.user_answers[idx] == item['correct']: st.success(f"Đúng! ✅")
            else: st.error(f"Sai! Đáp án đúng: {labels[c_idx]}")
            
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
        time.sleep(1.0); st.session_state.next_trigger = False
        if st.session_state.current_idx < len(data) - 1: st.session_state.current_idx += 1; st.rerun()
else:
    st.info("👈 Nạp file Word/PDF để bắt đầu.")
