import streamlit as st
import json
from openai import OpenAI
from fpdf import FPDF
import os
import pandas as pd
from datetime import datetime

# --- 1. 路径与配置 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "simhei.ttf")
QR_PATH = os.path.join(BASE_DIR, "wechat_qr.png")
DB_PATH = os.path.join(BASE_DIR, "pet_database.csv")

# --- 2. 工具函数 (PDF & 数据保存) ---
class PetReportPDF(FPDF):
    def header(self):
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
        pdf.image(QR_PATH, x=85, y=pdf.get_y(), w=40)
    return bytes(pdf.output())

def save_to_database(data):
    data['录入时间'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    df = pd.DataFrame([data])
    if not os.path.exists(DB_PATH):
        df.to_csv(DB_PATH, index=False, encoding='utf-8-sig')
    else:
        df.to_csv(DB_PATH, mode='a', header=False, index=False, encoding='utf-8-sig')

# --- 3. 界面初始化 ---
st.set_page_config(page_title="高级宠物档案系统", layout="wide")

try:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
    base_url = st.secrets["DEEPSEEK_BASE_URL"]
    admin_password = st.secrets["ADMIN_PASSWORD"] # 读取你刚刚设置的密码
except:
    st.error("❌ 后台配置不完整，请检查 Secrets。")
    st.stop()

# --- 4. 侧边栏设计 ---
with st.sidebar:
    st.header("⚙️ 系统菜单")
    # 客户一般不会去点这个，点开了也需要密码
    is_admin = st.checkbox("🔑 管理员后台")
    st.divider()
    st.write("欢迎使用本系统")

# --- 5. 逻辑分流：管理员界面 vs 客户界面 ---

if is_admin:
    # --- 情况 A: 管理员后台 (加锁) ---
    st.title("📊 内部资料库")
    input_pwd = st.text_input("请输入管理员密码", type="password")
    
    if input_pwd == admin_password:
        st.success("密码正确，已进入后台")
        if os.path.exists(DB_PATH):
            df = pd.read_csv(DB_PATH)
            st.subheader("📋 客户记录明细")
            st.dataframe(df, use_container_width=True)
            
            st.subheader("📈 品种分布统计")
            st.bar_chart(df['品种'].value_counts())
            
            csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 导出资料库 Excel", data=csv_data, file_name="customer_data.csv")
        else:
            st.info("暂无数据。")
    elif input_pwd != "":
        st.error("❌ 密码错误，无法查看信息")

else:
    # --- 情况 B: 客户填表模式 (完全保密) ---
    st.title("🐾 宠物专属档案生成")
    st.write("填写信息后，AI 顾问将为您生成下月养护计划。")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("宠物昵称", value="多多")
        pet_breed = st.text_input("品种", value="布偶猫")
    with col2:
        pet_age = st.text_input("年龄", value="1岁")
        pet_weight = st.number_input("体重 (kg)", value=4.0)
    with col3:
        vaccine = st.selectbox("疫苗情况", ["已齐", "未齐", "不详"])

    col4, col5 = st.columns(2)
    with col4:
        pet_char = st.text_input("性格", value="乖巧")
    with col5:
        pet_food = st.text_input("主粮品牌", value="添赐力")

    if st.button("✨ 生成指导信", type="primary", use_container_width=True):
        pet_info = {
            "名字": pet_name, "品种": pet_breed, "年龄": pet_age, 
            "体重": f"{pet_weight}kg", "性格": pet_char, 
            "主食": pet_food, "疫苗": vaccine
        }
        
        # 存入数据库
        save_to_database(pet_info)
        
        with st.spinner("顾问撰写中..."):
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "system", "content": "你是资深宠物顾问"},
                              {"role": "user", "content": str(pet_info)}]
                )
                st.session_state['report'] = response.choices[0].message.content
                st.success("✅ 生成成功！")
            except Exception as e:
                st.error(f"生成出错: {e}")

    if 'report' in st.session_state:
        st.markdown(st.session_state['report'])
        pdf_data = create_pdf(st.session_state['report'])
        st.download_button("📥 下载专属 PDF 报告", data=pdf_data, file_name=f"{pet_name}养护计划.pdf")
