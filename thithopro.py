import streamlit as st
from docx import Document
from docx.shared import RGBColor
from docx.enum.text import WD_COLOR_INDEX
import google.generativeai as genai
import random
import time
import io
import PyPDF2

# --- CẤU HÌNH API KEY ---
HIDDEN_API_KEY = "AIzaSyCUkNGMJAuz4oZHyAMccN6W8zN4B6U8hWk" 

st.set_page_config(page_title="ThiTho Pro V3", layout="wide")

# CSS tối ưu hiển thị câu hỏi và code
st.markdown("""
    <style>
    .question-box { background: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #dee2e6; margin-bottom: 20px; }
    .question-text { font-size: 19px !important; font-weight: 600; color: #1f1f1f; white-space: pre-wrap; font-family: 'Source Code Pro', monospace; }
    .ai-explanation { background-color: #f0f7ff; border-left: 6px solid #007bff; padding: 20px; border-radius: 8px; font-size: 16px; }
    </style>
    """, unsafe_allow_html=True)

# --- HÀM ĐỌC WORD TỐI ƯU CHO CODE ---
def read_docx(file_bytes):
    try:
        doc = Document(io.BytesIO(file_bytes))
        data = []
        current_q = None
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text: continue
            
            # Kiểm tra xem dòng này có phải là đáp án đúng không (Màu đỏ hoặc Highlight vàng)
            is_answer_style = False
            for run in para.runs:
                if (run.font.color and run.font.color.rgb == RGBColor(255, 0, 0)) or \
                   (run.font.highlight_color == WD_COLOR_INDEX.YELLOW):
                    is_answer_style = True
                    break
            
            # Nhận diện dòng bắt đầu câu hỏi (Ví dụ: "Câu 33:")
            is_new_q = text.lower().startswith("câu") and any(char.isdigit() for char in text[:10])

            if is_new_q:
                current_q = {"question": text, "options": [], "correct": None}
                data.append(current_q)
            elif current_q is not None:
                # Nếu là dòng đáp án (in đậm hoặc có màu đặc biệt)
                # Lưu ý: Nếu đáp án của bạn KHÔNG in đậm, hãy bỏ điều kiện 'any(run.bold...)'
                is_bold = any(run.bold for run in para.runs)
                
                if is_answer_style or (is_bold and len(text) < 100):
                    clean_opt = text.replace("*", "").strip()
                    if clean_opt not in current_q["options"]:
                        current_q["options"].append(clean_opt)
                        if is_answer_style:
                            current_q["correct"] = clean_opt
                else:
                    # Nếu không phải đáp án -> Nó là nội dung code hoặc văn bản của câu hỏi
                    current_q["question"] += "\n" + text
        
        # Lọc bỏ các câu không có đáp án
        return [q for q in data if q['options']]
    except Exception as e:
        st.error(f"Lỗi: {e}"); return None

# --- CÁC HÀM PHỤ TRỢ ---
def get_ai_explanation(q, options, corr_text):
    try:
        genai.configure(api_key=HIDDEN_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        labels = ["A", "B", "C", "D"]
        c_label = labels[options.index(corr_text)] if corr_text in options else "?"
        prompt = f"Phân tích câu hỏi lập trình/mạng sau:\n{q}\nĐáp án đúng là: {corr_text}\nTại sao chọn {c_label} và tại sao các câu khác sai? Nếu đáp án đề cho sai kiến thức hãy cảnh báo."
        return model.generate_content(prompt).text
    except: return "AI đang bận, hãy thử lại sau."

# --- GIAO DIỆN STREAMLIT ---
if 'data_thi' not in st.session_state:
    st.session_state.update({'data_thi': None, 'user_answers': {}, 'current_idx': 0, 'ex_cache': {}})

with st.sidebar:
    st.header("⚙️ QUẢN LÝ ĐỀ")
    file = st.file_uploader("Tải file Word (.docx)", type=["docx"])
    if file and st.button("🚀 NẠP ĐỀ NGAY"):
        res = read_docx(file.read())
        if res:
            st.session_state.update({'data_thi': res, 'user_answers': {}, 'current_idx': 0, 'ex_cache': {}})
            st.success(f"Đã nạp {len(res)} câu hỏi!")
            st.rerun()

if st.session_state.data_thi:
    data = st.session_state.data_thi
    idx = st.session_state.current_idx
    item = data[idx]
    
    col_l, col_m, col_r = st.columns([1, 2.5, 1.2])
    
    with col_m:
        # Hiển thị câu hỏi (bao gồm cả code Java)
        st.markdown(f'<div class="question-box"><div class="question-text">{item["question"]}</div></div>', unsafe_allow_html=True)
        
        answered = idx in st.session_state.user_answers
        labels = ["A", "B", "C", "D"]
        opts = [f"{labels[i]}. {opt}" for i, opt in enumerate(item['options'])]
        
        choice = st.radio("Chọn đáp án:", opts, key=f"q_{idx}", index=None if not answered else item['options'].index(st.session_state.user_answers[idx]), disabled=answered)
        
        if choice and not answered:
            st.session_state.user_answers[idx] = item['options'][opts.index(choice)]
            st.rerun()
            
        if answered:
            correct_opt = item['correct']
            is_right = st.session_state.user_answers[idx] == correct_opt
            if is_right:
                st.success("Chính xác! ✅")
            else:
                st.error(f"Sai rồi. Đáp án đúng là: {correct_opt}")
            
            if st.button("💡 Giải thích & Phản biện"):
                with st.spinner("Đang phân tích code..."):
                    st.session_state.ex_cache[idx] = get_ai_explanation(item['question'], item['options'], correct_opt)
            
            if idx in st.session_state.ex_cache:
                st.markdown(f'<div class="ai-explanation"><b>🤖 Phân tích:</b><br>{st.session_state.ex_cache[idx]}</div>', unsafe_allow_html=True)

        # Điều hướng
        st.write("---")
        c1, c2 = st.columns(2)
        if c1.button("⬅ Câu trước") and idx > 0:
            st.session_state.current_idx -= 1; st.rerun()
        if c2.button("Câu tiếp theo ➡") and idx < len(data) - 1:
            st.session_state.current_idx += 1; st.rerun()

    with col_r:
        st.write("### 📑 Danh sách câu")
        for i in range(0, len(data), 4):
            cols = st.columns(4)
            for j in range(4):
                if i+j < len(data):
                    label = f"{i+j+1}"
                    if i+j in st.session_state.user_answers:
                        label += "✅" if st.session_state.user_answers[i+j] == data[i+j]['correct'] else "❌"
                    if cols[j].button(label, key=f"btn_{i+j}"):
                        st.session_state.current_idx = i+j; st.rerun()
else:
    st.info("Hãy tải file Word ở thanh bên trái để bắt đầu ôn tập.")
