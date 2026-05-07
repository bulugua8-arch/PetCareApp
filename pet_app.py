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
# 2. PDF 生成逻辑 (已修复二进制报错)
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
    pdf.multi_cell(0, 7, text)
    
    if os.path.exists(QR_PATH):
        pdf.ln(10)
        pdf.set_font("SimHei", size=10)
        pdf.cell(0, 10, "--- 扫码添加顾问微信，获取更多专属建议 ---", ln=True, align="C")
        pdf.image(QR_PATH, x=85, y=pdf.get_y(), w=40)
    
    return bytes(pdf.output())

# ==========================================
# 3. 界面布局与后台秘密 (隐藏 API Key)
# ==========================================
st.set_page_config(page_title="高级宠物档案系统", page_icon="🐾", layout="wide")

# 自动从 Streamlit Cloud 的 Secrets 拿密码，客户看不到
try:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
    base_url = st.secrets["DEEPSEEK_BASE_URL"]
    model_name = "deepseek-chat"
except Exception:
    st.error("❌ 后台配置未完成。请在 Streamlit 控制台的 Secrets 中设置 API Key。")
    st.stop()

with st.sidebar:
    st.header("🐾 高端宠物养护顾问")
    st.write("欢迎使用专属档案生成系统")
    if not os.path.exists(FONT_PATH):
        st.error("❌ 缺字体文件 simhei.ttf")
    st.info("💡 填写右侧宠物资料，一键生成下月养护计划。")

st.title("🐾 宠物专属档案与下月计划生成")
st.markdown("---")

# --- 这里就是你消失的“信息栏”，现在找回来了 ---
st.subheader("第一步：录入宠物基础档案")
col1, col2, col3 = st.columns(3)
with col1:
    pet_name = st.text_input("宠物昵称", value="多多")
    pet_breed = st.text_input("品种", value="布偶猫")
with col2:
    pet_age = st.text_input("年龄", value="8个月")
    pet_weight = st.number_input("体重 (kg)", value=4.5, step=0.1)
with col3:
    vaccine_status = st.selectbox("疫苗接种情况", ["已完全接种", "接种中(缺针)", "未接种", "抗体合格"])

st.subheader("第二步：录入生活习惯")
col4, col5, col6 = st.columns(3)
with col4:
    pet_char = st.text_input("性格特征", value="胆小，粘人")
with col5:
    pet_food = st.text_input("目前主食粮品牌", value="添赐力")
with col6:
    wash_freq = st.slider("洗护频率 (天/次)", 1, 60, 14)

st.divider()

# ==========================================
# 4. 运行逻辑
# ==========================================
if st.button("✨ 生成并预览专属指导信", type="primary", use_container_width=True):
    pet_data = {
        "名字": pet_name, "品种": pet_breed, "年龄": pet_age, 
        "体重": f"{pet_weight}kg", "性格": pet_char, 
        "主食": pet_food, "疫苗": vaccine_status, "洗护周期": f"{wash_freq}天"
    }
    
    with st.spinner("高级顾问正在为您撰写专属计划..."):
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "你是一位『资深宠物顾问』，请根据档案撰写一封高端、温暖、专业的指导信。"},
                    {"role": "user", "content": f"档案：{json.dumps(pet_data, ensure_ascii=False)}"}
                ]
            )
            st.session_state['report'] = response.choices[0].message.content
            st.success("生成成功！")
        except Exception as e:
            st.error(f"生成失败，请检查 API 配置: {e}")

if 'report' in st.session_state:
    st.markdown(st.session_state['report'])
    
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
        st.warning(f"PDF 导出出错: {e}")

    if os.path.exists(QR_PATH):
        st.divider()
        _, c2, _ = st.columns([1,1,1])
        with c2:
            st.image(QR_PATH, caption="扫码添加顾问微信", width=200)
