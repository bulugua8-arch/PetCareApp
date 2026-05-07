import streamlit as st
import json
from openai import OpenAI
from fpdf import FPDF
import os
import pandas as pd
from datetime import datetime

# --- 1. 文件路径配置 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "simhei.ttf")
QR_PATH = os.path.join(BASE_DIR, "wechat_qr.png")
DB_PATH = os.path.join(BASE_DIR, "pet_database.csv") # 客户资料库文件名

# --- 2. PDF 生成逻辑 ---
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

# --- 3. 【核心新增】保存到表格的功能 ---
def save_to_database(data):
    data['录入时间'] = datetime.now().strftime("%Y-%m-%d %H:%M") # 记录时间
    df = pd.DataFrame([data])
    if not os.path.exists(DB_PATH):
        df.to_csv(DB_PATH, index=False, encoding='utf-8-sig') # 新建
    else:
        df.to_csv(DB_PATH, mode='a', header=False, index=False, encoding='utf-8-sig') # 追加

# --- 4. 网页界面布局 ---
st.set_page_config(page_title="高级宠物档案系统", layout="wide")

# 自动读取后台 Key
try:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
    base_url = st.secrets["DEEPSEEK_BASE_URL"]
    model_name = "deepseek-chat"
except:
    st.error("❌ 请在 Streamlit 后台 Secrets 配置 API Key")
    st.stop()

# 侧边栏：管理员开关
with st.sidebar:
    st.header("⚙️ 顾问后台")
    is_admin = st.checkbox("🔑 开启管理员模式")
    st.divider()
    st.info("客户填写信息后，系统会自动保存到后台资料库。")

if not is_admin:
    # --- 客户录入模式 ---
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

    col4, col5 = st.columns(2)
    with col4:
        pet_char = st.text_input("性格", value="乖巧")
    with col5:
        pet_food = st.text_input("主粮品牌", value="添赐力")

    if st.button("✨ 生成指导信并存档", type="primary", use_container_width=True):
        # 准备数据
        pet_info = {
            "名字": pet_name, "品种": pet_breed, "年龄": pet_age, 
            "体重": f"{pet_weight}kg", "性格": pet_char, 
            "主食": pet_food, "疫苗": vaccine
        }
        
        # 自动存档
        save_to_database(pet_info)
        
        with st.spinner("AI 正在写信..."):
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "system", "content": "你是资深宠物顾问"},
                              {"role": "user", "content": str(pet_info)}]
                )
                st.session_state['report'] = response.choices[0].message.content
                st.success("✅ 生成成功！信息已存入资料库。")
            except Exception as e:
                st.error(f"失败: {e}")

    if 'report' in st.session_state:
        st.markdown(st.session_state['report'])
        pdf_data = create_pdf(st.session_state['report'])
        st.download_button("📥 下载 PDF 发给客户", data=pdf_data, file_name=f"{pet_name}建议.pdf")

else:
    # --- 管理员模式：查看统计 ---
    st.title("📊 店内宠物资料库")
    if os.path.exists(DB_PATH):
        df = pd.read_csv(DB_PATH)
        
        # 显示数据表
        st.subheader("📋 客户记录")
        st.dataframe(df, use_container_width=True)
        
        # 品种统计图
        st.subheader("📈 品种数量统计")
        breed_stats = df['品种'].value_counts()
        st.bar_chart(breed_stats)
        
        # 导出按钮
        csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("📥 导出资料库 Excel", data=csv_data, file_name="客户资料.csv")
    else:
        st.info("目前还没有任何客户录入数据。")
