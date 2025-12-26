import streamlit as st
from docx import Document
from docx.shared import RGBColor
from docx.enum.text import WD_COLOR_INDEX
import google.generativeai as genai
import random
import time
import io

# --- CẤU HÌNH BẢO MẬT KEY ---
HIDDEN_API_KEY = "AIzaSyCUkNGMJAuz4oZHyAMccN6W8zN4B6U8hWk" 

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="ThiTho Pro", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main .block-container { max-width: 95% !important; padding-top: 2rem !important; }
    .question-box { background: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .question-text { font-size: 22px !important; font-weight: 700; color: #1f1f1f; margin-bottom: 15px; }
    .ai-explanation { background-color: #f8faff; border-left: 6px solid #007bff; padding: 20px; margin-top: 15px; border-radius: 8px; color: #1a1a1a; font-size: 17px; line-height: 1.7; }
    .ai-label { color: #007bff; font-weight: bold; font-size: 18px; margin-bottom: 8px; display: block; }
    div[data-testid="stHorizontalBlock"] button:has(span:contains("✅")) { background-color: #28a745 !important; color: white !important; }
    div[data-testid="stHorizontalBlock"] button:has(span:contains("❌")) { background-color: #ff4b4b !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- QUẢN LÝ TRẠNG THÁI ---
for key in ['data_thi', 'user_answers', 'current_idx', 'next_trigger', 'ex_cache']:
    if key not in st.session_state:
        st.session_state[key] = None if key == 'data_thi' else ({} if key in ['user_answers', 'ex_cache'] else (0 if key == 'current_idx' else False))

# --- HÀM ĐỌC FILE WORD ---
def read_docx(file_bytes):
    try:
        doc = Document(io.BytesIO(file_bytes))
        data = []
        current_q = None
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text: continue
            is_bold = any(run.bold for run in para.runs)
            if is_bold or text.lower().startswith("câu") or (text and text[0].isdigit() and "." in text[:5]):
                current_q = {"question": text, "options": [], "correct": None}
                data.append(current_q)
            elif current_q is not None:
                is_correct = False
                for run in para.runs:
                    if (run.font.color and run.font.color.rgb == RGBColor(255, 0, 0)) or \
                       (run.font.highlight_color == WD_COLOR_INDEX.YELLOW):
                        is_correct = True
                clean_text = text.replace("*", "").strip()
                if clean_text and clean_text not in current_q["options"]:
                    current_q["options"].append(clean_text)
                    if is_correct: current_q["correct"] = clean_text
        return [q for q in data if len(q['options']) >= 2]
    except Exception as e:
        st.error(f"Lỗi đọc file: {e}")
        return None

# --- HÀM AI GIẢI THÍCH (TỐI ƯU TRÌNH BÀY) ---
def get_ai_explanation(q, options, corr_text):
    try:
        genai.configure(api_key=HIDDEN_API_KEY)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        available_models.sort(key=lambda x: ("flash" not in x.lower()))

        labels = ["A", "B", "C", "D"]
        corr_label = labels[options.index(corr_text)] if corr_text in options else "?"
        
        # Prompt ép AI trình bày có cấu trúc
        prompt = f"""Bạn là giảng viên Mạng máy tính. Hãy giải thích ngắn gọn và dễ nhìn.
        CÂU HỎI: {q}
        
        YÊU CẦU TRÌNH BÀY:
        1. Bắt đầu bằng: "Bạn nên chọn đáp án **{corr_label}** vì:"
        2. Sau đó xuống dòng và dùng các gạch đầu dòng để giải thích lý do chính.
        3. In đậm các thuật ngữ quan trọng.
        4. Trả lời thẳng vào vấn đề, không chào hỏi.
        """

        for m_name in available_models:
            try:
                model = genai.GenerativeModel(m_name)
                return model.generate_content(prompt).text
            except: continue
        return "❌ AI đang bận."
    except Exception as e: return f"❌ Lỗi: {str(e)}"

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ CÀI ĐẶT")
    file = st.file_uploader("Tải đề (Word .docx)", type=["docx"])
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
        st.markdown("---")
        if st.button("🎯 Làm lại câu chưa đúng", use_container_width=True):
            data = st.session_state.data_thi
            sai = [data[i] for i in range(len(data)) if st.session_state.user_answers.get(i) != data[i]['correct']]
            if sai:
                st.session_state.data_thi, st.session_state.user_answers, st.session_state.current_idx, st.session_state.ex_cache = sai, {}, 0, {}
                st.rerun()
        if st.button("🔄 Đổi đề khác", use_container_width=True):
            st.session_state.data_thi = None; st.rerun()

# --- GIAO DIỆN CHÍNH ---
if st.session_state.data_thi:
    data = st.session_state.data_thi
    idx = st.session_state.current_idx
    item = data[idx]
    labels = ["A", "B", "C", "D"]
    
    col_l, col_m, col_r = st.columns([1, 2.5, 1.2])
    
    with col_l: # THỐNG KÊ
        with st.container(border=True):
            st.write("### 📊 Thống kê")
            da_lam = len(st.session_state.user_answers)
            dung = sum(1 for i, ans in st.session_state.user_answers.items() if ans == data[i]['correct'])
            st.write(f"📝 Câu: **{idx+1}/{len(data)}**")
            st.write(f"✅ Đúng: **{dung}** | ❌ Sai: **{da_lam - dung}**")
            st.progress((idx + 1) / len(data))

    with col_m: # NỘI DUNG
        st.markdown(f'<div class="question-box"><div class="question-text">Câu {idx + 1}: {item["question"]}</div></div>', unsafe_allow_html=True)
        
        answered = idx in st.session_state.user_answers
        opts_display = [f"{labels[i]}. {opt}" for i, opt in enumerate(item['options'])]
        
        choice_lbl = st.radio("Đáp án:", opts_display, key=f"r_{idx}", 
                             index=item['options'].index(st.session_state.user_answers[idx]) if answered else None, 
                             disabled=answered, label_visibility="collapsed")
        
        if choice_lbl and not answered:
            st.session_state.user_answers[idx] = item['options'][opts_display.index(choice_lbl)]
            st.session_state.next_trigger = True
            st.rerun()
            
        if answered:
            corr_idx = item['options'].index(item['correct'])
            if st.session_state.user_answers[idx] == item['correct']:
                st.success(f"Chính xác! Đáp án đúng là {labels[corr_idx]} ✅")
            else:
                st.error(f"Sai rồi! Đáp án đúng là {labels[corr_idx]}: {item['correct']}")
            
            if st.button("💡 Giải thích nhanh"):
                with st.spinner("AI đang tóm tắt kiến thức..."):
                    st.session_state.ex_cache[idx] = get_ai_explanation(item['question'], item['options'], item['correct'])
            
            if idx in st.session_state.ex_cache:
                st.markdown(f'<div class="ai-explanation"><span class="ai-label">🤖 AI phân tích:</span><br>{st.session_state.ex_cache[idx]}</div>', unsafe_allow_html=True)
        
        st.write("---")
        c1, c2 = st.columns(2)
        if c1.button("⬅ Câu trước", use_container_width=True):
            st.session_state.current_idx = max(0, idx - 1); st.rerun()
        if c2.button("Câu sau ➡", use_container_width=True):
            st.session_state.current_idx = min(len(data)-1, idx + 1); st.rerun()

    with col_r: # MỤC LỤC
        st.write("### 📑 Mục lục")
        grid = 4
        for i in range(0, len(data), grid):
            cols = st.columns(grid)
            for j in range(grid):
                curr = i + j
                if curr < len(data):
                    lbl = f"{curr+1}"
                    if curr in st.session_state.user_answers:
                        lbl += "✅" if st.session_state.user_answers[curr] == data[curr]['correct'] else "❌"
                    if cols[j].button(lbl, key=f"m_{curr}", use_container_width=True):
                        st.session_state.current_idx = curr; st.rerun()

    if st.session_state.next_trigger:
        time.sleep(1.0)
        st.session_state.next_trigger = False
        if st.session_state.current_idx < len(data) - 1:
            st.session_state.current_idx += 1; st.rerun()
else:
    st.info("👈 Nạp file Word để bắt đầu.")
