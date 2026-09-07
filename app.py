import streamlit as st
from PIL import Image
import numpy as np
import re
import pandas as pd
from datetime import datetime

# 嘗試載入快速 OCR 引擎
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
    <p style="color: #94a3b8; font-size: 14px; margin-top: 4px;">智慧截圖自動辨識 • 支援主行程與夾單計算</p>
</div>
""", unsafe_allow_html=True)

if 'records' not in st.session_state:
    st.session_state.records = []

if not OCR_AVAILABLE:
    st.warning("⚠️ 系統尚未偵測到 OCR 引擎，請確認 GitHub 中有 `packages.txt`（內含 `libgomp1`）與 `requirements.txt`。")

# 上傳截圖
uploaded_file = st.file_uploader("📷 上傳外送行程截圖（自動辨識金額與時間）", type=["png", "jpg", "jpeg"])

detected_amount = 101.00
detected_duration = 25.00

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="已上傳的截圖預覽")
    
    if OCR_AVAILABLE:
        try:
            with st.spinner("⚡ 正在極速自動解析截圖..."):
                img_np = np.array(image)
                result, _ = ocr(img_np)
                
                if result:
                    full_text = " ".join([line[1] for line in result])
                    
                    # 抓取金額（$ 後面的數字）
                    price_match = re.search(r'\$\s*([0-9]+(?:\.[0-9]+)?)', full_text)
                    if price_match:
                        detected_amount = float(price_match.group(1))
                    
                    # 抓取時間（分鐘前方的數字）
                    time_match = re.search(r'([0-9]+)\s*分鐘', full_text)
                    if time_match:
                        detected_duration = float(time_match.group(1))
        except Exception as e:
            st.error(f"OCR 解析過程發生錯誤: {e}")

st.markdown("### ⏱️ 行程數據確認與夾單調整")

col1, col2 = st.columns(2)
with col1:
    main_amount = st.number_input("主行程金額 ($)", value=float(detected_amount), step=1.00)
with col2:
    main_duration = st.number_input("主行程時間 (分鐘)", value=float(detected_duration), step=1.0)

# 夾單功能
is_stacked = st.checkbox("📦 這是一筆夾單 / 疊單")

stacked_amount = 0.0
stacked_duration = 0.0

if is_stacked:
    st.markdown("#### 🔄 夾單附加數據")
    scol1, scol2 = st.columns(2)
    with scol1:
        stacked_amount = st.number_input("夾單金額 ($)", value=0.00, step=1.00)
    with scol2:
        stacked_duration = st.number_input("夾單附加時間 (分鐘)", value=0.0, step=1.0)

# 總計計算
total_amount = main_amount + stacked_amount
total_duration = main_duration + stacked_duration

# 專法獨立門檻 (每分鐘 4.1 元，最低 45 元)
threshold = max(45.0, total_duration * 4.1)
diff = threshold - total_amount
shortfall = max(0.0, diff)

st.markdown("---")
st.markdown("### 📊 計算結果")
res_col1, res_col2, res_col3 = st.columns(3)

with res_col1:
    st.metric(label="平台實際總給予", value=f"${total_amount:.2f}")
with res_col2:
    st.metric(label="專法獨立總門檻", value=f"${threshold:.2f}")
with res_col3:
    st.metric(label="總需補足金額", value=f"${shortfall:.2f}", delta=f"-${shortfall:.2f}" if shortfall > 0 else "已達標")

if st.button("➕ 記錄此筆行程", type="primary"):
    new_record = {
        "時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "類型": "夾單/疊單" if is_stacked else "一般單",
        "總金額": total_amount,
        "總時間(分)": total_duration,
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
