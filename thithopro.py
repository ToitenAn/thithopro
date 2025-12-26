import streamlit as st
from docx import Document
from docx.shared import RGBColor
from docx.enum.text import WD_COLOR_INDEX
import google.generativeai as genai
import random
import time
import io

# --- CẤU HÌNH BẢO MẬT KEY (ẨN TRONG CODE) ---
HIDDEN_API_KEY = "AIzaSyCUkNGMJAuz4oZHyAMccN6W8zN4B6U8hWk" 
SELECTED_MODEL = "models/gemini-2.0-flash"

st.set_page_config(page_title="ThiTho Pro", layout="wide")

# --- STYLE GIAO DIỆN ---
st.markdown("""
    <style>
    .main .block-container { max-width: 95% !important; padding-top: 2rem !important; }
    .question-box { background: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; margin-bottom: 20px; }
    .question-text { font-size: 20px !important; font-weight: 700; color: #1f1f1f; }
    .ai-explanation { background-color: #f0f7ff; border-left: 5px solid #007bff; padding: 15px; margin-top: 15px; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- QUẢN LÝ TRẠNG THÁI ---
for key in ['data_thi', 'user_answers', 'current_idx', 'next_trigger', 'ex_cache']:
    if key not in st.session_state:
        st.session_state[key] = None if key == 'data_thi' else ({} if key in ['user_answers', 'ex_cache'] else (0 if key == 'current_idx' else False))

# --- HÀM ĐỌC FILE WORD (TỐI ƯU) ---
def read_docx(file_bytes):
    try:
        doc = Document(io.BytesIO(file_bytes))
        data = []
        current_q = None
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text: continue
            
            # Nhận diện câu hỏi (In đậm hoặc bắt đầu bằng Câu)
            is_bold = any(run.bold for run in para.runs)
            if is_bold or text.lower().startswith("câu") or (text[0].isdigit() and "." in text[:5]):
                current_q = {"question": text, "options": [], "correct": None}
                data.append(current_q)
            elif current_q is not None:
                is_correct = False
                for run in para.runs:
                    # Kiểm tra màu đỏ hoặc highlight vàng cho đáp án đúng
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

# --- HÀM AI ---
def get_ai_explanation(q, corr, user_ans):
    try:
        genai.configure(api_key=HIDDEN_API_KEY)
        model = genai.GenerativeModel(SELECTED_MODEL)
        prompt = f"Giải thích ngắn gọn tại sao '{corr}' là đáp án đúng cho câu hỏi: {q}. Người học chọn sai: {user_ans}. Trả lời bằng tiếng Việt."
        return model.generate_content(prompt).text
    except Exception as e: return f"❌ Lỗi AI: {str(e)}"

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ CÀI ĐẶT")
    file = st.file_uploader("Tải đề (Word .docx)", type=["docx"])
    dao_cau = st.checkbox("Đảo câu hỏi")
    dao_ap = st.checkbox("Đảo đáp án")
    
    if file and st.button("🚀 BẮT ĐẦU", use_container_width=True, type="primary"):
        content = file.read() # Đọc file dưới dạng bytes
        res = read_docx(content)
        if res:
            if dao_cau: random.shuffle(res)
            if dao_ap: 
                for item in res: random.shuffle(item['options'])
            st.session_state.data_thi = res
            st.session_state.user_answers = {}
            st.session_state.current_idx = 0
            st.session_state.ex_cache = {}
            st.rerun()

    if st.session_state.data_thi:
        st.write("---")
        if st.button("🎯 Làm lại câu sai", use_container_width=True):
            data = st.session_state.data_thi
            sai = [data[i] for i in range(len(data)) if st.session_state.user_answers.get(i) != data[i]['correct']]
            if sai:
                st.session_state.data_thi = sai
                st.session_state.user_answers = {}; st.session_state.current_idx = 0; st.rerun()

# --- GIAO DIỆN CHÍNH ---
if st.session_state.data_thi:
    data = st.session_state.data_thi
    idx = st.session_state.current_idx
    item = data[idx]
    
    c_stats, c_main, c_nav = st.columns([1, 2.5, 1.2])
    
    with c_stats:
        with st.container(border=True):
            st.write(f"📝 Câu: **{idx+1}/{len(data)}**")
            dung = sum(1 for i, a in st.session_state.user_answers.items() if a == data[i]['correct'])
            st.metric("✅ Đúng", dung)
            st.metric("❌ Sai", len(st.session_state.user_answers) - dung)

    with c_main:
        st.markdown(f'<div class="question-box"><div class="question-text">Câu {idx + 1}:</div>{item["question"]}</div>', unsafe_allow_html=True)
        ans = idx in st.session_state.user_answers
        choice = st.radio("Chọn:", item['options'], key=f"q_{idx}", index=None if not ans else item['options'].index(st.session_state.user_answers[idx]), disabled=ans)
        
        if choice and not ans:
            st.session_state.user_answers[idx] = choice
            st.session_state.next_trigger = True
            st.rerun()
            
        if ans:
            if st.session_state.user_answers[idx] == item['correct']: st.success("Chính xác!")
            else:
                st.error(f"Sai! Đáp án: {item['correct']}")
                if st.button("💡 Giải thích"):
                    with st.spinner("AI đang nghĩ..."):
                        st.session_state.ex_cache[idx] = get_ai_explanation(item['question'], item['correct'], st.session_state.user_answers[idx])
                if idx in st.session_state.ex_cache:
                    st.markdown(f'<div class="ai-explanation">{st.session_state.ex_cache[idx]}</div>', unsafe_allow_html=True)

        st.write("---")
        b1, b2 = st.columns(2)
        if b1.button("⬅ Trước"): st.session_state.current_idx = max(0, idx-1); st.rerun()
        if b2.button("Sau ➡"): st.session_state.current_idx = min(len(data)-1, idx+1); st.rerun()

    with c_nav:
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

    if st.session_state.next_trigger:
        time.sleep(1.0)
        st.session_state.next_trigger = False
        st.session_state.current_idx = min(len(data)-1, idx + 1); st.rerun()
else:
    st.info("👈 Hãy tải file Word để bắt đầu học.")
