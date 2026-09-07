import streamlit as st
from PIL import Image
import numpy as np
import re
import pandas as pd
from datetime import datetime
import os

try:
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    OCR_AVAILABLE = True
except Exception as e:
    ocr = None
    OCR_AVAILABLE = False

st.set_page_config(
    page_title="外送專法 獨立單單計價補足金額追蹤器",
    page_icon="🛵",
    layout="centered"
)

st.markdown("""
<style>
.stApp { background-color: #030712; color: #f3f4f6; }
.cyber-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #030712 100%);
    border: 1px solid #10b981;
    padding: 16px;
    border-radius: 12px;
    text-align: center;
    margin-bottom: 16px;
    box-shadow: 0 0 15px rgba(16, 185, 129, 0.2);
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="cyber-header">
    <h2 style="color: #10b981; margin:0;">🛵 外送專法獨立單計價補足金額追蹤器</h2>
    <p style="color: #94a3b8; font-size: 14px; margin-top: 4px;">專為外送夥伴打造的即時截圖辨識與補貼計算工具</p>
</div>
""", unsafe_allow_html=True)

if 'records' not in st.session_state:
    st.session_state.records = []

if not OCR_AVAILABLE:
    st.info("ℹ️ 系統尚未載入 OCR 引擎（請確認已在 GitHub 專案中建立 `packages.txt` 並寫入 `libgomp1`）")

uploaded_file = st.file_uploader("已讀取主行程截圖", type=["png", "jpg", "jpeg"])

init_amount = 227.00
duration_mins = 29.00

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="上傳的截圖預覽")
    
    if OCR_AVAILABLE:
        try:
            img_np = np.array(image)
            result, _ = ocr(img_np)
            
            if result:
                full_text = " ".join([line[1] for line in result])
                
                # 優先抓取帶有 $ 符號後面的數字（例如 $227）
                price_match = re.search(r'\$\s*([0-9]+(?:\.[0-9]+)?)', full_text)
                if price_match:
                    init_amount = float(price_match.group(1))
                else:
                    amounts = re.findall(r'([0-9]+(?:\.[0-9]+)?)\s*總計', full_text)
                    if amounts:
                        init_amount = float(amounts[0])
                
                # 時間抓取
                time_match = re.search(r'([0-9]+)\s*分鐘', full_text)
                if time_match:
                    duration_mins = float(time_match.group(1))
        except Exception as e:
            st.error(f"OCR 解析過程發生錯誤: {e}")

st.markdown("### ⏱️ 主行程數據確認")

col1, col2 = st.columns(2)
with col1:
    amount = st.number_input("初始金額 ($)", value=float(init_amount), step=1.00)
with col2:
    duration = st.number_input("行程總時間 (分鐘)", value=float(duration_mins), step=1.0)

threshold = max(45.0, duration * 4.1)
diff = threshold - amount
shortfall = max(0.0, diff)

st.markdown("---")
st.markdown("### 📊 計算結果")
res_col1, res_col2, res_col3 = st.columns(3)

with res_col1:
    st.metric(label="平台實際給予", value=f"${amount:.2f}")
with res_col2:
    st.metric(label="專法獨立門檻", value=f"${threshold:.2f}")
with res_col3:
    st.metric(label="需補足金額", value=f"${shortfall:.2f}", delta=f"-${shortfall:.2f}" if shortfall > 0 else "已達標")

if st.button("➕ 記錄此筆行程", type="primary"):
    new_record = {
        "時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "金額": amount,
        "時間(分)": duration,
        "獨立門檻": threshold,
        "補足金額": shortfall
    }
    st.session_state.records.append(new_record)
    st.success("✅ 行程記錄已新增！")

if st.session_state.records:
    st.markdown("### 📋 歷史記錄")
    df = pd.DataFrame(st.session_state.records)
    st.dataframe(df, use_container_width=True)
    
    total_shortfall = df["補足金額"].sum()
    st.info(f"💰 累計總需補足金額：**${total_shortfall:.2f}**")
