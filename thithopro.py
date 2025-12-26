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
st.set_page_config(page_title="ThiTho Pro - Fixed Multi-line Bold", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main .block-container { max-width: 95% !important; padding-top: 2rem !important; }
    .question-box { background: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    /* Giữ nguyên định dạng xuống dòng và font chữ code chuyên dụng */
    .question-text { font-size: 20px !important; font-weight: 700; color: #1f1f1f; margin-bottom: 15px; white-space: pre-wrap; font-family: 'Consolas', monospace; line-height: 1.6; }
    .ai-explanation { background-color: #f8faff; border-left: 6px solid #007bff; padding: 20px; margin-top: 15px; border-radius: 8px; color: #1a1a1a; font-size: 17px; line-height: 1.7; }
    .warning-box { background-color: #fff3cd; border-left: 6px solid #ffc107; padding: 20px; margin-top: 15px; border-radius: 8px; color: #856404; font-size: 17px; line-height: 1.7; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# --- QUẢN LÝ TRẠNG THÁI ---
for key in ['data_thi', 'user_answers', 'current_idx', 'next_trigger', 'ex_cache']:
    if key not in st.session_state:
        st.session_state[key] = None if key == 'data_thi' else ({} if key in ['user_answers', 'ex_cache'] else (0 if key == 'current_idx' else False))

# --- HÀM ĐỌC WORD: FIX LỖI GOM TẤT CẢ PHẦN IN ĐẬM VÀO CÂU HỎI ---
def read_docx(file_bytes):
    try:
        doc = Document(io.BytesIO(file_bytes))
        data = []
        current_q = None
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text: continue
            
            # Kiểm tra xem dòng này có in đậm không
            is_bold = any(run.bold for run in para.runs)
            
            # Kiểm tra xem dòng này có màu Đỏ hoặc Highlight Vàng không (Dùng làm đáp án đúng)
            is_answer_style = False
            for run in para.runs:
                if (run.font.color and run.font.color.rgb == RGBColor(255, 0, 0)) or \
                   (run.font.highlight_color == WD_COLOR_INDEX.YELLOW):
                    is_answer_style = True
                    break
            
            # Nhận diện tiêu đề câu hỏi mới (Dựa trên chữ "Câu" và số thứ tự)
            is_header = text.lower().startswith("câu") and any(char.isdigit() for char in text[:10])

            if is_header:
                current_q = {"question": text, "options": [], "correct": None}
                data.append(current_q)
            elif current_q is not None:
                if is_answer_style:
                    # Nếu có màu đỏ/vàng -> Đây là đáp án đúng
                    clean_opt = text.strip()
                    if clean_opt not in current_q["options"]:
                        current_q["options"].append(clean_opt)
                        current_q["correct"] = clean_opt
                elif is_bold:
                    # NẾU IN ĐẬM: Gom vào phần nội dung câu hỏi (Fix lỗi code Java nhiều dòng)
                    current_q["question"] += "\n" + text
                else:
                    # Chữ thường: Coi là các phương án lựa chọn nhiễu
                    if len(text) < 200:
                        current_q["options"].append(text)
        
        return [q for q in data if q['options']]
    except Exception as e:
        st.error(f"Lỗi đọc Word: {e}"); return None

# --- HÀM AI GIẢI THÍCH & PHẢN BIỆN ---
def get_ai_explanation(q, options, corr_text):
    try:
        genai.configure(api_key=HIDDEN_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        labels = ["A", "B", "C", "D"]
        corr_label = labels[options.index(corr_text)] if corr_text in options else "?"
        
        prompt = f"""Bạn là giảng viên chuyên ngành Mạng máy tính. 
        Câu hỏi: {q}
        Đáp án tài liệu chọn là: {corr_label}. {corr_text}

        NHIỆM VỤ:
        1. Kiểm tra xem đáp án trong tài liệu có ĐÚNG về mặt kỹ thuật mạng hay không.
        2. Nếu tài liệu SAI, bắt đầu bằng: "⚠️ CẢNH BÁO: Đáp án trong tài liệu có thể chưa chính xác!".
        3. Phân tích chi tiết tại sao chọn {corr_label} và các câu khác sai ở đâu.
        Trình bày bằng gạch đầu dòng, in đậm các thuật ngữ quan trọng."""

        return model.generate_content(prompt).text
    except Exception as e: return f"❌ AI đang bận: {str(e)}"

# --- GIAO DIỆN CHÍNH ---
with st.sidebar:
    st.header("⚙️ CÀI ĐẶT")
    file = st.file_uploader("Tải đề Word (.docx)", type=["docx"])
    t1 = st.checkbox("Đảo câu hỏi")
    t2 = st.checkbox("Đảo đáp án")
    
    if file and st.button("🚀 BẮT ĐẦU", use_container_width=True, type="primary"):
        res = read_docx(file.read())
        if res:
            if t1: random.shuffle(res)
            if t2: 
                for it in res: random.shuffle(it['options'])
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
        # Hiển thị câu hỏi (Dùng white-space: pre-wrap để giữ định dạng code Java)
        st.markdown(f'<div class="question-box"><div class="question-text">{item["question"]}</div></div>', unsafe_allow_html=True)
        
        answered = idx in st.session_state.user_answers
        opts_display = [f"{labels[i]}. {opt}" for i, opt in enumerate(item['options'])]
        
        choice_lbl = st.radio("Đáp án:", opts_display, key=f"r_{idx}", 
                             index=item['options'].index(st.session_state.user_answers[idx]) if answered else None, 
                             disabled=answered, label_visibility="collapsed")
        
        if choice_lbl and not answered:
            st.session_state.user_answers[idx] = item['options'][opts_display.index(choice_lbl)]
            st.session_state.next_trigger = True; st.rerun()
            
        if answered:
            c_idx = item['options'].index(item['correct']) if item['correct'] in item['options'] else 0
            if st.session_state.user_answers[idx] == item['correct']:
                st.success(f"Chính xác! Đáp án đúng là {labels[c_idx]} ✅")
            else:
                st.error(f"Sai rồi! Đáp án đúng là {labels[c_idx]}: {item['correct']}")
            
            if st.button("🔍 Giải thích & Phản biện từ AI"):
                with st.spinner("AI đang thẩm định kiến thức..."):
                    st.session_state.ex_cache[idx] = get_ai_explanation(item['question'], item['options'], item['correct'])
            
            if idx in st.session_state.ex_cache:
                explanation = st.session_state.ex_cache[idx]
                box_class = "warning-box" if "⚠️ CẢNH BÁO" in explanation else "ai-explanation"
                st.markdown(f'<div class="{box_class}"><b>🤖 Phân tích chuyên sâu:</b><br><br>{explanation}</div>', unsafe_allow_html=True)
        
        st.write("---")
        c1, c2 = st.columns(2)
        if c1.button("⬅ Câu trước"): st.session_state.current_idx = max(0, idx - 1); st.rerun()
        if c2.button("Câu sau ➡"): st.session_state.current_idx = min(len(data)-1, idx + 1); st.rerun()

    with col_r:
        st.write("### 📑 Mục lục")
        for i in range(0, len(data), 4):
            cols = st.columns(4)
            for j in range(4):
                curr = i + j
                if curr < len(data):
                    lbl = f"{curr+1}"
                    if curr in st.session_state.user_answers:
                        lbl += "✅" if st.session_state.user_answers[curr] == data[curr]['correct'] else "❌"
                    if cols[j].button(lbl, key=f"m_{curr}", use_container_width=True):
                        st.session_state.current_idx = curr; st.rerun()

    if st.session_state.next_trigger:
        time.sleep(1.0); st.session_state.next_trigger = False
        if st.session_state.current_idx < len(data) - 1:
            st.session_state.current_idx += 1; st.rerun()
else:
    st.info("👈 Nạp file Word để bắt đầu.")
