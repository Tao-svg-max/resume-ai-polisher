import streamlit as st
import requests
import json
import pypdf
import docx
from io import BytesIO
import os

st.set_page_config(page_title="AI 简历抛光机")

# ---- 网页浏览次数记录 ----
# 使用本地文件计数，适合 Streamlit Sharing/Cloud、非并发高场景。
VISIT_COUNTER_FILE = "visit_count.txt"

def get_visit_count():
    if not os.path.exists(VISIT_COUNTER_FILE):
        with open(VISIT_COUNTER_FILE, "w") as f:
            f.write("1")
        return 1
    else:
        try:
            with open(VISIT_COUNTER_FILE, "r+") as f:
                count = f.read()
                count = int(count.strip()) if count.strip().isdigit() else 0
                count += 1
                f.seek(0)
                f.write(str(count))
                f.truncate()
            return count
        except Exception:
            return None

visit_count = get_visit_count()

# -- 将累计访问次数显示为左下角小标签，只显示访问次数 --
visit_count_html = f"""
    <div style="
        position: fixed;
        left: 16px;
        bottom: 8px;
        background: rgba(245,245,245,0.85);
        color: #666;
        padding: 2px 12px;
        border-radius: 16px;
        font-size: 12px;
        z-index: 9999;
        box-shadow: 0 0 4px 0 #eee;
        transition: opacity 0.3s;
        ">
        {visit_count if visit_count else "读取失败"}
    </div>
"""
st.markdown(visit_count_html, unsafe_allow_html=True)
# -- END 访问次数左下角展示 --

# 获取 API Key
try:
    api_key = st.secrets.get("DASHSCOPE_API_KEY", "")
except Exception:
    api_key = ""


# 侧边栏配置
with st.sidebar:
    st.title("⚙️ 润色设置")
    target_job = st.selectbox(
        "🎯 目标岗位",
        ["Python 后端开发实习生", "AI 应用开发实习生", "数据分析实习生", "通用软件工程岗位"]
    )
    polishing_focus = st.radio(
        "💡 润色重点",
        ["强化 STAR 法则与量化成果", "突出技术栈与架构术语", "修正错别字与语法口语化"]
    )
    st.markdown("---")
    st.markdown(
        "<span style='font-size: 12px;'>💡 <b>使用提示</b>：本工具以中国大学生为主要使用人群。上传简历或输入文本后点击开始润色，润色完成后可在下方继续输入修改意见进行多轮调整。</span>",
        unsafe_allow_html=True
    )

st.title("AI 简历抛光机")
st.caption("大厂资深技术面试官人设 | 结构化 STAR 法则优化 | 多轮交互")

# 初始化 session_state 保存对话历史与提取文本
if "messages" not in st.session_state:
    st.session_state.messages = []
if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = ""

# 文件解析辅助函数
def extract_text_from_pdf(uploaded_file):
    reader = pypdf.PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text() or ""
        text += page_text + "\n"
    return text

def extract_text_from_docx(uploaded_file):
    doc = docx.Document(uploaded_file)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

# 调用大模型 API 函数
def call_qwen_api(messages_list):
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "qwen-plus",
        "messages": messages_list,
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    if response.status_code == 200:
        res_json = response.json()
        return res_json['choices'][0]['message']['content']
    else:
        st.error(f"API 请求失败，状态码: {response.status_code}, 详情: {response.text}")
        return None

# 文件上传与手动文本输入区域
uploaded_file = st.file_uploader("📄 上传简历文档 (.pdf 或 .docx)", type=["pdf", "docx"])

if uploaded_file is not None:
    if uploaded_file.type == "application/pdf":
        st.session_state.extracted_text = extract_text_from_pdf(uploaded_file)
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        st.session_state.extracted_text = extract_text_from_docx(uploaded_file)
    st.success("✅ 文档解析成功！")

user_input_text = st.text_area(
    "✍️ 简历原始项目描述 / 个人经历",
    value=st.session_state.extracted_text,
    height=180,
    placeholder="在框内粘贴或通过上方上传文档解析..."
)

col1, col2 = st.columns([1, 4])
with col1:
    start_btn = st.button("✨ 开始智能润色", type="primary", use_container_width=True)
with col2:
    if st.button("🗑️ 清空对话历史", use_container_width=False):
        st.session_state.messages = []
        st.rerun()

# 第一次启动润色流程
if start_btn:
    content_to_polish = user_input_text.strip()
    if not content_to_polish:
        st.warning("请先上传简历文档或在文本框中输入需要润色的内容！")
    elif not api_key:
        st.error("未找到 API Key，请先配置 DASHSCOPE_API_KEY！")
    else:
        # 明确要求润色输出为简体中文
        system_prompt = f"""你是一名一线大厂资深技术面试官与简历专家。
你的任务是帮求职者润色简历项目经历。请务必将润色内容输出为简体中文，适合中国学生。如需其他语言，将由用户在对话中提出变更。
- 目标岗位：{target_job}
- 润色重点：{polishing_focus}

请按以下结构输出：
🌟 综合评分与问题诊断
✍️ 润色后的建议文本（可以直接复制到简历上的版本，严格采用 STAR 法则，使用简体中文）
💡 亮点解析与面试预判问答"""

        st.session_state.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请帮我润色以下项目描述，输出请使用简体中文：\n\n{content_to_polish}"}
        ]

        with st.spinner("🤖 大厂面试官 AI 正在深度诊断与润色中..."):
            reply = call_qwen_api(st.session_state.messages)
            if reply:
                st.session_state.messages.append({"role": "assistant", "content": reply})

# 展示多轮对话历史
if st.session_state.messages:
    st.markdown("---")
    st.subheader("💬 润色对话记录")
    
    # 过滤 system 消息，显示 user 和 assistant 的对话
    for idx, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        elif msg["role"] == "assistant":
            with st.chat_message("assistant"):
                st.markdown(msg["content"])

    # 允许用户提出二次修改意见，包括语言变更等
    prompt = st.chat_input("💡 提出修改意见（如需英文简历可输入：'请将润色结果翻译成英文' 等）")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("🤖 正在根据您的意见进行二次调整..."):
                reply = call_qwen_api(st.session_state.messages)
                if reply:
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    st.rerun()
           
