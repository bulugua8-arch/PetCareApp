import streamlit as st
import json
from openai import OpenAI
from fpdf import FPDF
import os
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. 初始化云端表格连接 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. 路径配置 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "simhei.ttf")
QR_PATH = os.path.join(BASE_DIR, "wechat_qr.png") # 你的微信二维码
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")

# --- 3. PDF 生成类 ---
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
    # PDF 底部也带上二维码
    if os.path.exists(QR_PATH):
        pdf.ln(10)
        pdf.image(QR_PATH, x=85, y=pdf.get_y(), w=40)
    return bytes(pdf.output())

# --- 4. 自动写入云端表格逻辑 ---
def sync_to_gsheets(new_data):
    try:
        new_data['录入时间'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        existing_data = conn.read(spreadsheet=st.secrets["GSHEETS_URL"])
        updated_df = pd.concat([existing_data, pd.DataFrame([new_data])], ignore_index=True)
        conn.update(spreadsheet=st.secrets["GSHEETS_URL"], data=updated_df)
        return True
    except:
        return False

# --- 5. 界面初始化 ---
st.set_page_config(page_title="高级宠物档案系统", layout="wide")

try:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
    base_url = st.secrets["DEEPSEEK_BASE_URL"]
    admin_pwd = st.secrets["ADMIN_PASSWORD"]
    gsheets_url = st.secrets["GSHEETS_URL"]
except:
    st.error("❌ Secrets 配置不完整，请检查 API Key、密码和表格网址。")
    st.stop()

# 侧边栏
with st.sidebar:
    st.header("⚙️ 顾问后台")
    is_admin = st.checkbox("🔑 进入管理员模式")
    st.divider()
    st.info("填写右侧信息，一键生成专属报告。")

# --- 6. 逻辑分流 ---

if is_admin:
    # 管理员后台
    st.title("📊 实时客户资料库")
    input_pwd = st.text_input("请输入管理员密码", type="password")
    if input_pwd == admin_pwd:
        df = conn.read(spreadsheet=gsheets_url)
        st.dataframe(df, use_container_width=True)
        st.subheader("🐱 品种分布统计")
        if not df.empty and '品种' in df.columns:
            st.bar_chart(df['品种'].value_counts())
    elif input_pwd != "":
        st.error("密码错误")

else:
    # 客户填表模式
    st.title("🐾 宠物专属档案生成")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("宠物昵称", value="多多")
        pet_breed = st.text_input("品种", value="布偶猫")
    with col2:
        pet_age = st.text_input("年龄", value="1岁")
        pet_weight = st.number_input("体重 (kg)", value=4.0)
    with col3:
        vaccine = st.selectbox("疫苗情况", ["已齐", "未齐", "不详"])

    if st.button("✨ 生成指导信并同步", type="primary", use_container_width=True):
        info = {"名字": pet_name, "品种": pet_breed, "年龄": pet_age, "体重": pet_weight, "疫苗": vaccine}
        
        # 自动同步到 Google 表格
        if sync_to_gsheets(info):
            st.toast("✅ 数据已存档到云端", icon="📈")
        
        with st.spinner("顾问正在撰写中..."):
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                resp = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role":"system","content":"你是一位资深宠物顾问"},
                              {"role":"user","content":str(info)}]
                )
                st.session_state['report'] = resp.choices[0].message.content
            except Exception as e:
                st.error(f"生成失败: {e}")

    # --- 报告显示区域 ---
    if 'report' in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state['report'])
        
        # 按钮：下载 PDF
        pdf_data = create_pdf(st.session_state['report'])
        st.download_button("📥 下载专属 PDF 报告", data=pdf_data, file_name=f"{pet_name}建议.pdf", use_container_width=True)
        
        # 【重点：这里把你的二维码找回来】
        if os.path.exists(QR_PATH):
            st.divider()
            col_a, col_b, col_c = st.columns([1, 1, 1])
            with col_b: # 放在中间一栏，更美观
                st.image(QR_PATH, caption="扫码添加顾问微信，领取精美礼品", width=250)
