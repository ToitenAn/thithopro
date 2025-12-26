import streamlit as st
from docx2python import docx2python
import google.generativeai as genai
import random
import time
import re
import os

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="ThiTho Pro - AI Tutor", layout="wide")

# Thiết lập API Key trực tiếp từ ảnh bạn cung cấp
API_KEY = "AIzaSyDltPif--RgiBgVARciWVTrmLCHWUr7ZW8"
genai.configure(api_key=API_KEY)

st.markdown("""
    <style>
    .main .block-container { max-width: 95% !important; padding-top: 2rem !important; }
    .question-box { 
        background: #ffffff; padding: 25px; border-radius: 12px; 
        border: 1px solid #dee2e6; margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .question-text { font-size: 20px !important; font-weight: 700; color: #1f1f1f; }
    .ai-explanation {
        background-color: #f0f7ff; border-left: 5px solid #007bff;
        padding: 20px; margin-top: 15px; border-radius: 8px;
        color: #1a1a1a; line-height: 1.6;
    }
    div[data-testid="stHorizontalBlock"] button:has(span:contains("✅")) { background-color: #28a745 !important; color: white !important; }
    div[data-testid="stHorizontalBlock"] button:has(span:contains("❌")) { background-color: #ff4b4b !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- QUẢN LÝ TRẠNG THÁI ---
for key in ['data_thi', 'user_answers', 'current_idx', 'next_trigger', 'explanation_cache']:
    if key not in st.session_state:
        st.session_state[key] = None if key == 'data_thi' else ({} if key == 'user_answers' else (0 if key == 'current_idx' else {}))

# --- HÀM GỌI AI GIẢI THÍCH ---
def get_ai_explanation(question, correct_answer, user_answer):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Bạn là giảng viên hỗ trợ ôn thi.
        Câu hỏi: {question}
        Đáp án đúng: {correct_answer}
        Người học chọn sai là: {user_answer}
        Hãy giải thích ngắn gọn tại sao {correct_answer} đúng và tại sao {user_answer} sai. 
        Nếu là code Java, hãy giải thích logic từng dòng. Trả lời bằng tiếng Việt, Markdown.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Lỗi AI: {str(e)}"

# --- HÀM ĐỌC FILE WORD (CHỮ ĐẬM + ẢNH) ---
def process_docx(uploaded_file):
    with open("temp.docx", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # docx2python giúp trích xuất cả ảnh và định dạng HTML (b, i, u)
    with docx2python("temp.docx") as doc:
        all_lines = []
        for part in doc.body:
            for table in part:
                for row in table:
                    for cell in row:
                        for line in cell:
                            if line.strip(): all_lines.append(line)
        
        data = []
        current_q = None
        
        for line in all_lines:
            # Nhận diện Đề bài: Chữ in đậm (<b>) hoặc bắt đầu bằng "Câu"
            is_bold = "<b>" in line
            text_clean = re.sub('<[^<]+?>', '', line).strip()
            img_match = re.search(r'----image(\d+)\.(png|jpg|jpeg)----', line)
            
            if is_bold or text_clean.lower().startswith("câu") or (text_clean and text_clean[0].isdigit() and "." in text_clean[:5]):
                current_q = {"question": text_clean, "options": [], "correct": None, "image": None}
                if img_match:
                    img_name = f"image{img_match.group(1)}.{img_match.group(2)}"
                    current_q["image"] = doc.images.get(img_name)
                data.append(current_q)
            
            elif current_q is not None:
                # Đáp án đúng: Có dấu * hoặc được đánh dấu bôi màu (tùy file)
                is_correct = "*" in line or "highlight" in line.lower()
                
                if img_match and not current_q["image"]:
                    img_name = f"image{img_match.group(1)}.{img_match.group(2)}"
                    current_q["image"] = doc.images.get(img_name)

                clean_ans = text_clean.replace("*", "").strip()
                if clean_ans and "phần bổ sung" not in clean_ans.lower():
                    if clean_ans not in current_q["options"]:
                        current_q["options"].append(clean_ans)
                        if is_correct: current_q["correct"] = clean_ans
                    
        return [q for q in data if len(q['options']) >= 2]

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ CÀI ĐẶT")
    file = st.file_uploader("Tải đề Word (.docx)", type=["docx"])
    t1 = st.checkbox("Đảo câu hỏi")
    t2 = st.checkbox("Đảo đáp án")
    
    if file and st.button("🚀 BẮT ĐẦU", use_container_width=True, type="primary"):
        st.session_state.data_thi = process_docx(file)
        if t1: random.shuffle(st.session_state.data_thi)
        if t2: 
            for it in st.session_state.data_thi: random.shuffle(it['options'])
        st.session_state.user_answers = {}
        st.session_state.current_idx = 0
        st.session_state.explanation_cache = {}
        st.rerun()

# --- GIAO DIỆN CHÍNH ---
if st.session_state.data_thi:
    data = st.session_state.data_thi
    idx = st.session_state.current_idx
    item = data[idx]
    
    col_l, col_m, col_r = st.columns([1, 2.5, 1.2])
    
    with col_l:
        st.write("### 📊 Thống kê")
        tong = len(data)
        da_lam = len(st.session_state.user_answers)
        dung = sum(1 for i, ans in st.session_state.user_answers.items() if ans == data[i]['correct'])
        st.metric("🎯 Điểm", f"{(dung/tong)*10:.2f}" if tong > 0 else "0.00")
        st.write(f"✅ Đúng: **{dung}** | ❌ Sai: **{da_lam - dung}**")
        st.progress(da_lam / tong if tong > 0 else 0)

    with col_m:
        st.markdown(f'<div class="question-box"><div class="question-text">Câu {idx + 1}: {item["question"]}</div></div>', unsafe_allow_html=True)
        
        if item.get("image"):
            st.image(item["image"], use_container_width=True, caption="Hình ảnh minh họa")
        
        answered = idx in st.session_state.user_answers
        choice = st.radio("Chọn đáp án:", item['options'], key=f"r_{idx}", 
                          index=item['options'].index(st.session_state.user_answers[idx]) if answered else None,
                          disabled=answered)
        
        if choice and not answered:
            st.session_state.user_answers[idx] = choice
            st.rerun()
            
        if answered:
            if st.session_state.user_answers[idx] == item['correct']:
                st.success("CHÍNH XÁC! ✅")
            else:
                st.error(f"SAI RỒI! ❌ Đáp án đúng: {item['correct']}")
                if st.button("💡 Giải thích câu này (AI)", key=f"ai_{idx}"):
                    with st.spinner("AI đang phân tích kiến thức..."):
                        exp = get_ai_explanation(item['question'], item['correct'], st.session_state.user_answers[idx])
                        st.session_state.explanation_cache[idx] = exp
                
                if idx in st.session_state.explanation_cache:
                    st.markdown(f'<div class="ai-explanation"><strong>🤖 AI Giải thích:</strong><br>{st.session_state.explanation_cache[idx]}</div>', unsafe_allow_html=True)

        st.write("---")
        c1, c2 = st.columns(2)
        if c1.button("⬅ Trước", use_container_width=True): st.session_state.current_idx = max(0, idx-1); st.rerun()
        if c2.button("Sau ➡", use_container_width=True): st.session_state.current_idx = min(len(data)-1, idx+1); st.rerun()

    with col_r:
        st.write("### 📑 Mục lục")
        grid = 4
        for i in range(0, len(data), grid):
            cols = st.columns(grid)
            for j in range(grid):
                curr = i + j
                if curr < len(data):
                    lbl = f"{curr+1}"
                    if curr in st.session_state.user_answers:
                        lbl += " ✅" if st.session_state.user_answers[curr] == data[curr]['correct'] else " ❌"
                    if cols[j].button(lbl, key=f"m_{curr}", use_container_width=True):
                        st.session_state.current_idx = curr; st.rerun()
else:
    st.info("👈 Hãy tải file Word lên để bắt đầu ôn luyện cùng AI!")