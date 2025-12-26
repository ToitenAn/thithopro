import streamlit as st
from docx2python import docx2python
import google.generativeai as genai
import random
import re
import os

# --- CẤU HÌNH ---
st.set_page_config(page_title="ThiTho Pro - Lập Trình Mạng", layout="wide")

# Sử dụng API Key bạn đã cung cấp
API_KEY = "AIzaSyCUkNGMJAuz4oZHyAMccN6W8zN4B6U8hWk"
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
for key in ['data_thi', 'user_answers', 'current_idx', 'ex_cache']:
    if key not in st.session_state:
        st.session_state[key] = None if key == 'data_thi' else ({} if key == 'user_answers' else (0 if key == 'current_idx' else {}))

# --- HÀM GIẢI THÍCH AI ---
def get_ai_explanation(question, correct_answer, user_answer):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Bạn là giảng viên Lập trình mạng.
        Câu hỏi: {question}
        Đáp án đúng: {correct_answer}
        Người học chọn sai: {user_answer}
        Hãy giải thích ngắn gọn tại sao đáp án đúng lại là {correct_answer}. Trả lời bằng tiếng Việt, dùng Markdown.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Lỗi kết nối AI: {str(e)}"

# --- HÀM ĐỌC FILE WORD ĐẶC THÙ ---
def process_network_docx(uploaded_file):
    with open("temp_network.docx", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    try:
        with docx2python("temp_network.docx") as doc:
            # Tách nội dung theo từ khóa "Câu "
            full_text = doc.text
            # Loại bỏ phần header "Phần 1"
            content = re.split(r'\nCâu\s+\d+', full_text)
            
            final_data = []
            for section in content:
                lines = [l.strip() for l in section.split('\n') if l.strip()]
                if not lines: continue
                
                question = ""
                options = []
                correct = ""
                
                for line in lines:
                    # Tìm nội dung câu hỏi trong HA(x) = "..."
                    if 'HA(' in line and '="' in line:
                        match = re.search(r'=\s*"(.*)"', line)
                        if match: question = match.group(1)
                    # Nếu không có HA, lấy dòng đầu tiên không phải dòng tiêu đề "Một đáp án"
                    elif not question and not any(x in line for x in ["đáp án", "Phần"]):
                        question = line
                    
                    # Tìm đáp án (dòng có dấu * là đúng)
                    if line.startswith('*'):
                        clean_ans = line.replace('*', '').strip().strip('"')
                        options.append(clean_ans)
                        correct = clean_ans
                    elif line.startswith('"') or (len(line) > 1 and not line.startswith('HA(')):
                        clean_ans = line.strip().strip('"')
                        if clean_ans and clean_ans not in options:
                            options.append(clean_ans)
                
                if question and correct and len(options) >= 2:
                    final_data.append({
                        "question": question,
                        "options": options,
                        "correct": correct
                    })
            return final_data
    except Exception as e:
        st.error(f"Lỗi xử lý file: {e}")
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ CÀI ĐẶT")
    file = st.file_uploader("Tải file Lập trình mạng.docx", type=["docx"])
    if file and st.button("🚀 BẮT ĐẦU", use_container_width=True, type="primary"):
        data = process_network_docx(file)
        if data:
            st.session_state.data_thi = data
            st.session_state.user_answers = {}
            st.session_state.current_idx = 0
            st.session_state.ex_cache = {}
            st.rerun()
        else:
            st.error("Không đọc được dữ liệu. Hãy kiểm tra lại định dạng file.")

# --- GIAO DIỆN CHÍNH ---
if st.session_state.data_thi:
    data = st.session_state.data_thi
    idx = st.session_state.current_idx
    item = data[idx]
    
    col_stats, col_main, col_nav = st.columns([1, 2.5, 1.2])
    
    with col_stats:
        st.write("### 📊 Tiến độ")
        done = len(st.session_state.user_answers)
        total = len(data)
        correct_count = sum(1 for i, a in st.session_state.user_answers.items() if a == data[i]['correct'])
        st.metric("Điểm số", f"{(correct_count/total)*10:.2f}" if total > 0 else "0.00")
        st.write(f"Đã làm: {done}/{total}")
        st.progress(done/total if total > 0 else 0)

    with col_main:
        st.markdown(f'<div class="question-box"><div class="question-text">Câu {idx + 1}: {item["question"]}</div></div>', unsafe_allow_html=True)
        
        answered = idx in st.session_state.user_answers
        choice = st.radio("Chọn đáp án:", item['options'], key=f"q_{idx}", 
                          index=item['options'].index(st.session_state.user_answers[idx]) if answered else None,
                          disabled=answered)
        
        if choice and not answered:
            st.session_state.user_answers[idx] = choice
            st.rerun()
            
        if answered:
            if st.session_state.user_answers[idx] == item['correct']:
                st.success("Đúng rồi! ✅")
            else:
                st.error(f"Sai rồi! ❌ Đáp án đúng là: **{item['correct']}**")
                if st.button("💡 Giải thích bằng AI"):
                    with st.spinner("AI đang suy nghĩ..."):
                        st.session_state.ex_cache[idx] = get_ai_explanation(item['question'], item['correct'], st.session_state.user_answers[idx])
                
                if idx in st.session_state.ex_cache:
                    st.markdown(f'<div class="ai-explanation">{st.session_state.ex_cache[idx]}</div>', unsafe_allow_html=True)

        st.write("---")
        b1, b2 = st.columns(2)
        if b1.button("⬅ Câu trước", use_container_width=True): st.session_state.current_idx = max(0, idx-1); st.rerun()
        if b2.button("Câu sau ➡", use_container_width=True): st.session_state.current_idx = min(total-1, idx+1); st.rerun()

    with col_nav:
        st.write("### 📑 Mục lục")
        rows = (total // 4) + 1
        for r in range(rows):
            cols = st.columns(4)
            for c in range(4):
                curr = r * 4 + c
                if curr < total:
                    label = f"{curr+1}"
                    if curr in st.session_state.user_answers:
                        label += "✅" if st.session_state.user_answers[curr] == data[curr]['correct'] else "❌"
                    if cols[c].button(label, key=f"nav_{curr}", use_container_width=True):
                        st.session_state.current_idx = curr; st.rerun()
else:
    st.info("👈 Vui lòng tải file 'Lập trình mạng.docx' lên để bắt đầu học tập.")


