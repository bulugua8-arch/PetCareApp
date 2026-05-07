import streamlit as st
import json
from openai import OpenAI
from fpdf import FPDF
import os

# ==========================================
# 1. 路径自动定位
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "simhei.ttf")
QR_PATH = os.path.join(BASE_DIR, "wechat_qr.png")
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")

# ==========================================
# 2. PDF 类与生成逻辑
# ==========================================
class PetReportPDF(FPDF):
    def header(self):
        if os.path.exists(LOGO_PATH):
            self.image(LOGO_PATH, 10, 8, 33)
        self.add_font("SimHei", "", FONT_PATH)
        self.set_font("SimHei", size=16)
        self.cell(0, 10, "高定宠物专属生活与喂养指导信", ln=True, align="C")
        self.ln(10)

def create_pdf(text):
    pdf = PetReportPDF()
    pdf.add_page()
    pdf.add_font("SimHei", "", FONT_PATH)
    pdf.set_font("SimHei", size=11)
    
    # 写入 AI 生成的正文（支持自动换行）
    pdf.multi_cell(0, 7, text)
    
    # 末尾添加个人微信二维码
    if os.path.exists(QR_PATH):
        pdf.ln(10)
        pdf.set_font("SimHei", size=10)
        pdf.cell(0, 10, "--- 扫码添加顾问微信，获取更多专属建议 ---", ln=True, align="C")
        curr_y = pdf.get_y()
        pdf.image(QR_PATH, x=85, y=curr_y, w=40)
    
    return bytes(pdf.output())

# ==========================================
# 3. Streamlit 网页界面
# ==========================================
st.set_page_config(page_title="高级宠物档案系统", page_icon="🐾", layout="wide")

with st.sidebar:
    st.header("⚙️ 系统配置")
    api_key = st.text_input("请输入 API Key:", type="password")
    base_url = st.text_input("API Base URL:", value="https://api.deepseek.com")
    model_name = st.text_input("模型名称:", value="deepseek-chat")
    if not os.path.exists(FONT_PATH):
        st.error("❌ 缺字体 simhei.ttf")
    if not os.path.exists(QR_PATH):
        st.info("💡 放入 wechat_qr.png 即可显示二维码")

st.title("🐾 高定宠物专属档案与计划生成")
st.markdown("---")

# --- 第一行：基础信息 ---
col1, col2, col3 = st.columns(3)
with col1:
    pet_name = st.text_input("宠物昵称", value="多多")
    pet_breed = st.text_input("品种", value="布偶猫")
with col2:
    pet_age = st.text_input("年龄", value="8个月")
    pet_weight = st.number_input("体重 (kg)", value=4.5, step=0.1)
with col3:
    vaccine_status = st.selectbox("疫苗接种情况", ["已完全接种", "接种中(缺针)", "未接种", "抗体合格"])

# --- 第二行：细节偏好 ---
col4, col5, col6 = st.columns(3)
with col4:
    pet_char = st.text_input("性格特征", value="胆小，粘人")
with col5:
    pet_food = st.text_input("目前主食粮品牌", value="添赐力")
with col6:
    wash_freq = st.slider("洗护频率 (天/次)", 1, 60, 14)

st.divider()

# ==========================================
# 4. 生成报告逻辑
# ==========================================
if st.button("✨ 生成并预览专属指导信", type="primary", use_container_width=True):
    if not api_key:
        st.error("请在左侧填入 API Key")
    else:
        # 整理成发给 AI 的档案
        pet_data = {
            "名字": pet_name, "品种": pet_breed, "年龄": pet_age, 
            "体重": f"{pet_weight}kg", "性格": pet_char, 
            "主食": pet_food, "疫苗": vaccine_status, "洗护周期": f"{wash_freq}天"
        }
        
        system_prompt = """你是一位『资深宠物高级营养与护理顾问』。请撰写一封极其专业且充满关怀的『下月指导信』。
        要求：针对客户提供的品种、性格（如胆小则需安抚）、主粮（评价其营养）、疫苗、洗护周期，给出具体的、带有温度的建议。
        排版：使用 emoji，段落清晰，语气高端温暖。"""
        
        with st.spinner("高级顾问正在为您撰写专属计划..."):
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"宠物档案如下：{json.dumps(pet_data, ensure_ascii=False)}"}
                    ]
                )
                st.session_state['report'] = response.choices[0].message.content
                st.success("生成成功！")
            except Exception as e:
                st.error(f"生成失败: {e}")

# ==========================================
# 5. 展示结果与下载按钮
# ==========================================
if 'report' in st.session_state:
    st.markdown(st.session_state['report'])
    
    # 导出 PDF
    try:
        pdf_data = create_pdf(st.session_state['report'])
        st.download_button(
            label="📥 下载专属 PDF 报告 (发给客户)",
            data=pdf_data,
            file_name=f"{pet_name}的专属建议.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    except Exception as e:
        st.warning(f"PDF 导出出错，请检查字体文件: {e}")

    # 网页底部二维码显示
    if os.path.exists(QR_PATH):
        st.divider()
        _, c2, _ = st.columns([1,1,1])
        with c2:
            st.image(QR_PATH, caption="扫码添加顾问微信", width=200)