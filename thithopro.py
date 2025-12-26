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

st.set_page_config(page_title="ThiTho Pro - Lập Trình Mạng", layout="wide")

# --- CSS TỐI ƯU GIAO DIỆN ---
st.markdown("""
    <style>
    .main .block-container { max-width: 95% !important; padding-top: 2rem !important; }
    .question-box { background: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .question-text { font-size: 20px !important; font-weight: 700; color: #1f1f1f; margin-bottom: 10px; }
    .ai-explanation { background-color: #f0f7ff; border-left: 5px solid #007bff; padding: 20px; margin-top: 15px; border-radius: 8px; color: #1a1a1a; font-size: 16px; line-height: 1.6; }
    .ai-header { color: #007bff; font-weight: bold; font-size: 18px; margin-bottom: 10px; display: block; }
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

# --- HÀM AI TẬP TRUNG VÀO ĐÁP ÁN ---
def get_ai_explanation(q, corr, user_ans):
    try:
        genai.configure(api_key=HIDDEN_API_KEY)
        # Tự động lấy các model khả dụng trong tài khoản của bạn
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        available_models.sort(key=lambda x: ("flash" not in x.lower())) # Ưu tiên các dòng Flash

        # PROMPT TẬP TRUNG CAO ĐỘ
        prompt = f"""
        Bạn là chuyên gia về Mạng máy tính. Hãy giải thích câu hỏi trắc nghiệm sau một cách cực kỳ ngắn gọn, đi thẳng vào vấn đề.

        CÂU HỎI: {q}
        ĐÁP ÁN ĐÚNG: {corr}
        NGƯỜI HỌC CHỌN: {user_ans}

        Yêu cầu trả lời theo cấu trúc chính xác như sau:
        1. Khẳng định đáp án đúng.
        2. Tại sao đáp án đúng: Giải thích ngắn gọn tiêu chí hoặc kiến thức chuyên môn (ví dụ: Dưới góc độ địa lý thì mạng chia thành LAN, WAN, GAN...).
        3. Tại sao các đáp án khác sai (nếu cần thiết để làm rõ).
        
        Trả lời bằng tiếng Việt, súc tích, không chào hỏi vòng vo.
        """

        for m_name in available_models:
            try:
                model = genai.GenerativeModel(m_name)
                response = model.generate_content(prompt)
                return f"<span class='ai-header'>🤖 AI Giải thích ({m_name.split('/')[-1]}):</span><br>{response.text}"
            except:
                continue
        return "❌ Các model AI hiện đang quá tải. Thử lại sau giây lát."
    except Exception as e:
        return f"❌ Lỗi hệ thống AI: {str(e)}"

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ CÀI ĐẶT ĐỀ")
    file = st.file_uploader("Tải đề (Word .docx)", type=["docx"])
    dao_cau = st.checkbox("Đảo câu hỏi")
    dao_ap = st.checkbox("Đảo đáp án")
    
    if file and st.button("🚀 BẮT ĐẦU", use_container_width=True, type="primary"):
        res = read_docx(file.read())
        if res:
            if dao_cau: random.shuffle(res)
            if dao_ap: 
                for item in res: random.shuffle(item['options'])
            st.session_state.data_thi, st.session_state.user_answers, st.session_state.current_idx, st.session_state.ex_cache = res, {}, 0, {}
            st.rerun()

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
            st.progress((idx + 1) / len(data))

    with c_main:
        st.markdown(f'<div class="question-box"><div class="question-text">Câu {idx + 1}:</div>{item["question"]}</div>', unsafe_allow_html=True)
        ans_done = idx in st.session_state.user_answers
        
        choice = st.radio("Chọn đáp án:", item['options'], key=f"q_{idx}", 
                          index=None if not ans_done else item['options'].index(st.session_state.user_answers[idx]), 
                          disabled=ans_done, label_visibility="collapsed")
        
        if choice and not ans_done:
            st.session_state.user_answers[idx] = choice
            st.rerun()
            
        if ans_done:
            if st.session_state.user_answers[idx] == item['correct']: 
                st.success("Chính xác! ✅")
            else:
                st.error(f"Sai rồi! Đáp án đúng: **{item['correct']}**")
                
            if st.button("💡 Giải thích bằng AI"):
                with st.spinner("AI đang phân tích kiến thức chuyên môn..."):
                    st.session_state.ex_cache[idx] = get_ai_explanation(item['question'], item['correct'], st.session_state.user_answers[idx])
            
            if idx in st.session_state.ex_cache:
                st.markdown(f'<div class="ai-explanation">{st.session_state.ex_cache[idx]}</div>', unsafe_allow_html=True)

        st.write("---")
        b1, b2 = st.columns(2)
        if b1.button("⬅ Trước", use_container_width=True): 
            st.session_state.current_idx = max(0, idx - 1); st.rerun()
        if b2.button("Sau ➡", use_container_width=True): 
            st.session_state.current_idx = min(len(data) - 1, idx + 1); st.rerun()

    with c_nav:
        st.write("### 📑 Mục lục")
        for i in range(0, len(data), 4):
            cols = st.columns(4)
            for j in range(4):
                curr = i + j
                if curr < len(data):
                    lbl = f"{curr+1}"
                    if curr in st.session_state.user_answers:
                        lbl += "✅" if st.session_state.user_answers[curr] == data[curr]['correct'] else "❌"
                    if cols[j].button(lbl, key=f"n_{curr}", use_container_width=True):
                        st.session_state.current_idx = curr; st.rerun()
else:
    st.info("👈 Hãy tải file Word (.docx) để bắt đầu.")
