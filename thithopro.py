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
st.set_page_config(page_title="ThiTho Pro", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main .block-container { max-width: 95% !important; padding-top: 2rem !important; }
    .question-box { background: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    /* Giữ định dạng xuống dòng cho code Java */
    .question-text { font-size: 22px !important; font-weight: 700; color: #1f1f1f; margin-bottom: 15px; white-space: pre-wrap; font-family: 'Consolas', monospace; }
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

# --- HÀM XỬ LÝ FILE PDF ---
def read_pdf(file_bytes):
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"
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
    except Exception as e:
        st.error(f"Lỗi đọc PDF: {e}"); return None

# --- HÀM ĐỌC FILE WORD (FIX CHÍNH TẠI ĐÂY) ---
def read_docx(file_bytes):
    try:
        doc = Document(io.BytesIO(file_bytes))
        data, current_q = [], None
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text: continue
            
            # Kiểm tra định dạng (Màu đỏ, Vàng, Dấu *)
            is_bold = any(run.bold for run in para.runs)
            is_correct_style = False
            if "*" in text: is_correct_style = True
            for run in para.runs:
                if (run.font.color and run.font.color.rgb == RGBColor(255, 0, 0)) or \
                   (run.font.highlight_color == WD_COLOR_INDEX.YELLOW):
                    is_correct_style = True
                    break
            
            # Nhận diện tiêu đề câu hỏi
            is_header = text.lower().startswith("câu") and any(char.isdigit() for char in text[:10])

            if is_header:
                current_q = {"question": text, "options": [], "correct": None}
                data.append(current_q)
            elif current_q is not None:
                if is_correct_style:
                    clean_text = text.replace("*", "").strip()
                    if clean_text not in current_q["options"]:
                        current_q["options"].append(clean_text)
                        current_q["correct"] = clean_text
                elif is_bold:
                    # GỘP DÒNG IN ĐẬM VÀO CÂU HỎI (Fix lỗi code Java)
                    current_q["question"] += "\n" + text
                else:
                    clean_text = text.replace("*", "").strip()
                    if clean_text and clean_text not in current_q["options"]:
                        current_q["options"].append(clean_text)
        return [q for q in data if len(q['options']) >= 2]
    except Exception as e:
        st.error(f"Lỗi đọc Word: {e}"); return None

# --- HÀM AI GIẢI THÍCH & PHẢN BIỆN ---
def get_ai_explanation(q, options, corr_text):
    try:
        genai.configure(api_key=HIDDEN_API_KEY)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        models.sort(key=lambda x: ("flash" not in x.lower()))
        
        labels = ["A", "B", "C", "D"]
        corr_label = labels[options.index(corr_text)] if corr_text in options else "?"
        wrong_opts = [f"{labels[i]}. {opt}" for i, opt in enumerate(options) if opt != corr_text]

        prompt = f"""Bạn là giảng viên.
        Câu hỏi: {q}
        Đáp án tài liệu chọn: {corr_label}. {corr_text}
        Các lựa chọn khác: {', '.join(wrong_opts)}

        NHIỆM VỤ:
        1. Kiểm tra tính chính xác của đáp án tài liệu.
        2. Nếu tài liệu SAI: Bắt đầu bằng "⚠️ CẢNH BÁO: Đáp án tài liệu có thể chưa chính xác!". Chỉ ra đáp án đúng thực sự.
        3. Nếu tài liệu ĐÚNG: Trình bày theo cấu trúc:
           - "Bạn nên chọn đáp án **{corr_label}** vì:" (Giải thích chuyên môn).
           - "Tại sao các câu còn lại sai:" (Phân tích đối chứng).
        Dùng gạch đầu dòng, in đậm thuật ngữ chuyên môn."""

        for m_name in models:
            try:
                model = genai.GenerativeModel(m_name)
                return model.generate_content(prompt).text
            except: continue
        return "❌ AI đang bận."
    except Exception as e: return f"❌ Lỗi: {str(e)}"

# --- SIDEBAR ---
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
        st.write("---")
        if st.button("🎯 Ôn lại câu sai", use_container_width=True):
            sai = [st.session_state.data_thi[i] for i in range(len(st.session_state.data_thi)) if st.session_state.user_answers.get(i) != st.session_state.data_thi[i]['correct']]
            if sai: st.session_state.data_thi, st.session_state.user_answers, st.session_state.current_idx, st.session_state.ex_cache = sai, {}, 0, {}; st.rerun()

# --- GIAO DIỆN CHÍNH ---
if st.session_state.data_thi:
    data, idx = st.session_state.data_thi, st.session_state.current_idx
    item, labels = data[idx], ["A", "B", "C", "D"]
    col_l, col_m, col_r = st.columns([1, 2.5, 1.2])
    
    with col_l: # THỐNG KÊ
        with st.container(border=True):
            st.write("### 📊 Thống kê")
            dung = sum(1 for i, ans in st.session_state.user_answers.items() if ans == data[i]['correct'])
            st.write(f"📝 Câu: **{idx+1}/{len(data)}**")
            st.write(f"✅ Đúng: **{dung}** | ❌ Sai: **{len(st.session_state.user_answers)-dung}**")
            st.progress((idx + 1) / len(data))
            st.metric("🎯 Điểm", f"{(dung/len(data))*10:.2f}" if len(data) > 0 else "0.00")

    with col_m: # NỘI DUNG
        st.markdown(f'<div class="question-box"><div class="question-text">Câu {idx + 1}: {item["question"]}</div></div>', unsafe_allow_html=True)
        ans_done = idx in st.session_state.user_answers
        opts_display = [f"{labels[i]}. {opt}" for i, opt in enumerate(item['options'])]
        
        choice_lbl = st.radio("Đáp án:", opts_display, key=f"r_{idx}", index=item['options'].index(st.session_state.user_answers[idx]) if ans_done else None, disabled=ans_done, label_visibility="collapsed")
        
        if choice_lbl and not ans_done:
            st.session_state.user_answers[idx] = item['options'][opts_display.index(choice_lbl)]
            st.session_state.next_trigger = True; st.rerun()
            
        if ans_done:
            c_idx = item['options'].index(item['correct']) if item['correct'] in item['options'] else 0
            if st.session_state.user_answers[idx] == item['correct']: st.success(f"Đúng! Đáp án: {labels[c_idx]} ✅")
            else: st.error(f"Sai! Đáp án đúng: {labels[c_idx]} - {item['correct']}")
            
            if st.button("🔍 Phân tích chuyên sâu (Đúng/Sai)"):
                with st.spinner("AI đang thẩm định kiến thức..."):
                    st.session_state.ex_cache[idx] = get_ai_explanation(item['question'], item['options'], item['correct'])
            
            if idx in st.session_state.ex_cache:
                if "⚠️ CẢNH BÁO" in st.session_state.ex_cache[idx]: st.markdown(f'<div class="warning-box">{st.session_state.ex_cache[idx]}</div>', unsafe_allow_html=True)
                else: st.markdown(f'<div class="ai-explanation"><b>🤖 Phân tích chuyên gia:</b><br><br>{st.session_state.ex_cache[idx]}</div>', unsafe_allow_html=True)
        
        st.write("---")
        c1, c2 = st.columns(2)
        if c1.button("⬅ Trước", use_container_width=True): st.session_state.current_idx = max(0, idx - 1); st.rerun()
        if c2.button("Sau ➡", use_container_width=True): st.session_state.current_idx = min(len(data)-1, idx + 1); st.rerun()

    with col_r: # MỤC LỤC
        st.write("### 📑 Mục lục")
        for i in range(0, len(data), 4):
            cols = st.columns(4)
            for j in range(4):
                curr = i + j
                if curr < len(data):
                    lbl = f"{curr+1}"
                    if curr in st.session_state.user_answers: lbl += "✅" if st.session_state.user_answers[curr] == data[curr]['correct'] else "❌"
                    if cols[j].button(lbl, key=f"m_{curr}", use_container_width=True): st.session_state.current_idx = curr; st.rerun()

    if st.session_state.next_trigger:
        time.sleep(1.0); st.session_state.next_trigger = False
        if st.session_state.current_idx < len(data) - 1: st.session_state.current_idx += 1; st.rerun()
else:
    st.info("👈 Nạp file Word/PDF để bắt đầu.")

