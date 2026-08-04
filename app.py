import streamlit as st
import requests

# ====== 导入 PDF、Word 文档解析依赖 ======
from pypdf import PdfReader    # pip install pypdf
import docx                    # pip install python-docx

# ====== 通义千问 API Key 配置不变 ======
api_key = st.secrets["DASHSCOPE_API_KEY"]

def call_qwen_resume_enhancer(raw_resume, job_role, polish_focus):
    """
    调用通义千问 API，对简历内容进行智能润色
    """
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 系统提示词，结合岗位和润色重点
    system_prompt = (
        f"你是一位大厂资深技术面试官，请以最专业的视角帮我润色以下简历项目描述或个人介绍，目标岗位为“{job_role}”，润色重点为“{polish_focus}”。请按照如下结构输出：\n"
        "1. 🌟 综合评分与问题诊断（给出1-2句话的总体分析和可能的改进方向）\n"
        "2. ✍️ 润色后的建议文本（以 STAR 法则表达，可直接复制到简历上，逻辑精炼，突出量化/技术/规范等）\n"
        "3. 💡 亮点解析与面试预判问答（列举可能被问及的深度追问以及亮点挖掘）"
    )

    payload = {
        "model": "qwen-plus",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"待润色内容：{raw_resume.strip()}"}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        answer = data.get("choices", [{}])[0].get("message", {}).get("content")
        return answer if answer else "未获取到AI润色内容"
    except requests.exceptions.Timeout:
        return "请求超时啦，AI 忙不过来了，请稍后再试试 😊"
    except requests.exceptions.ConnectionError:
        return "无法连接到通义千问服务，请检查您的网络或稍后再试。"
    except requests.exceptions.HTTPError as e:
        return f"请求通义千问 API 时出现 HTTP 错误：{e.response.status_code} {str(e)}"
    except Exception as e:
        return f"请求通义千问 API 时遇到错误：{str(e)}"

st.set_page_config(page_title="AI 简历极速润色专家", page_icon=":rocket:", layout="centered")

# Sidebar：岗位与润色重点
with st.sidebar:
    st.header("参数设置")
    job_role = st.selectbox("目标岗位", [
        "Python 后端开发实习生",
        "AI 应用开发实习生",
        "数据分析实习生"
    ])
    polish_focus = st.radio("润色重点", [
        "强化 STAR 法则与量化成果", 
        "突出技术栈与架构术语", 
        "修正错别字与语法口语化"
    ])
    st.markdown("---")
    st.info("选择适合你的岗位和希望AI关注的润色方向，再在主页面输入你的简历片段，一键智能进阶！")

CUSTOM_TITLE = """
    <h1 style='text-align: center; color: #255df7;
    font-family: "Helvetica Neue", Helvetica, Arial, "Microsoft Yahei", sans-serif;
    letter-spacing:2px; margin-bottom:30px;'>
    🚀 AI 简历极速润色专家
    </h1>
"""
st.markdown(CUSTOM_TITLE, unsafe_allow_html=True)

# ========== 新增：自适应文本框颜色样式 ==========

st.markdown("""
    <style>
    .result-block {
        background: #f6fbff;
        border-radius: 14px;
        padding: 24px;
        margin-top: 30px;
        box-shadow: 0 1px 8px 0 #e3eaef;
        font-size: 16px;
        color: #1a202c;
    }
    /* 自适应：检测主题色/明暗模式，合理分配文本框背景与文字色 */
    @media (prefers-color-scheme: dark) {
        .stTextArea textarea {
            background: #23272f !important;
            color: #f5f6fa !important;
            caret-color: #f5f6fa !important;
        }
        .stTextArea label, .stTextArea textarea::placeholder {
            color: #eee !important;
            opacity: 1 !important;
        }
        .stTextArea textarea::placeholder {
            color: #999 !important;
        }
    }
    @media (prefers-color-scheme: light) {
        .stTextArea textarea {
            background: #f1f5fa !important;
            color: #23272f !important;
            caret-color: #23272f !important;
        }
        .stTextArea label, .stTextArea textarea::placeholder {
            color: #333 !important;
            opacity: 1 !important;
        }
        .stTextArea textarea::placeholder {
            color: #666 !important;
        }
    }
    /* 确保按钮风格高可用性 */
    .stButton > button {
        font-weight: bold;
        font-size: 18px;
        border-radius: 8px;
        padding: 8px 22px;
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ========== PDF 和 DOCX 解析辅助函数 ==========

def parse_pdf(file):
    """
    解析上传的 PDF 文件为纯文本
    使用 pypdf 库，逐页提取文本并合并
    """
    try:
        pdf_reader = PdfReader(file)
        all_text = []
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                all_text.append(text)
        # 将所有页的文本合并为一个字符串返回
        return "\n".join(all_text).strip()
    except Exception as e:
        return f"[PDF解析出错]{e}"

def parse_docx(file):
    """
    解析上传的 DOCX 文件为纯文本
    使用 python-docx 库，逐段落读取文本合并
    """
    try:
        doc = docx.Document(file)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text.strip()
    except Exception as e:
        return f"[DOCX解析出错]{e}"

# ========== 主页面交互升级 ==========

# 文件上传，支持 PDF 和 DOCX
uploaded_file = st.file_uploader("上传 PDF 或 Word 简历文档：", type=["pdf", "docx"])

# 文件内容解析变量
resume_text_from_file = ""
if uploaded_file is not None:
    filename = uploaded_file.name.lower()
    # 根据文件类型解析内容（加中文注释说明）
    if filename.endswith(".pdf"):
        # 使用 pypdf 针对 PDF 文件提取全部文本
        resume_text_from_file = parse_pdf(uploaded_file)
    elif filename.endswith(".docx"):
        # 使用 python-docx 针对 Word 文档提取全部文本
        resume_text_from_file = parse_docx(uploaded_file)
    # 展示解析后的文本内容供用户确认
    st.info("已自动解析上传文档内容，可在下方审核或补充：")

# 显式使用 file_uploader 解析得来的文本作为默认值
resume_input = st.text_area(
    "简历内容输入区：可粘贴/补充，也可直接用上传文档解析结果 ↓",
    value=resume_text_from_file if resume_text_from_file else "",
    placeholder="例如：负责某电商平台商品推荐模块研发，实现用户点击率提升、系统稳定性优化……",
    key="resume_input",
    height=160
)

submit_col, _ = st.columns([1, 3])
with submit_col:
    submit_btn = st.button("🔥 开始智能润色", use_container_width=True)

if submit_btn:
    # 按优先级取解析后的文件文本，其次取文本框
    resume_for_ai = resume_text_from_file if resume_text_from_file else resume_input
    if not resume_for_ai.strip():
        st.warning("请上传简历文档或输入需要润色的简历片段哦~")
    else:
        with st.spinner("AI 专家正在深度解析和润色中，请稍候...（最长 60 秒）"):
            ai_result = call_qwen_resume_enhancer(resume_for_ai, job_role, polish_focus)
        st.markdown("<div class='result-block'>"+ ai_result.replace("\n", "<br>") +"</div>", unsafe_allow_html=True)
