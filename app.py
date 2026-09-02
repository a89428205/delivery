import streamlit as st
from PIL import Image
import numpy as np
import re
from rapidocr_onnxruntime import RapidOCR

st.set_page_config(page_title="外送算單與時薪加成計算器", layout="centered")

st.title("🛵 外送算單 & 保障加成計算器")

# 初始化 RapidOCR
@st.cache_resource
def load_ocr():
    return RapidOCR()

ocr = load_ocr()

# 側邊欄：設定目前時段的保障加成 (預設 110 元/小時)
st.sidebar.header("⚙️ 時段加成設定")
hourly_bonus = st.sidebar.number_input("每小時加成金額 ($/HR)", value=110, step=10)
min_rate = hourly_bonus / 60.0

st.sidebar.markdown(f"**目前每分鐘補貼：** `${min_rate:.2f}` 元")

# 檔案上傳
uploaded_file = st.file_uploader("上傳 Uber Eats 接單截圖", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="已上傳截圖", use_column_width=True)
    
    # 轉為 numpy 陣列進行 OCR 辨識
    img_np = np.array(image)
    result, _ = ocr(img_np)
    
    full_text = ""
    if result:
        full_text = "\n".join([line[1] for line in result])
    
    # 提取金額 (例如 $94)
    price_match = re.search(r'\$\s*(\d+)', full_text)
    price = float(price_match.group(1)) if price_match else 0.0
    
    # 提取預估時間 (例如 28 分鐘)
    time_match = re.search(r'(\d+)\s*分鐘', full_text)
    est_minutes = int(time_match.group(1)) if time_match else 0
    
    # 提取預估里程 (例如 7.0 公里)
    dist_match = re.search(r'([\d\.]+)\s*公里', full_text)
    distance = float(dist_match.group(1)) if dist_match else 0.0

    st.divider()
    st.subheader("📊 辨識結果與預估")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("顯示單價", f"${price:.0f}")
    col2.metric("預估時間", f"{est_minutes} 分鐘")
    col3.metric("預估里程", f"{distance} km")
    
    # 計算預估補貼
    est_bonus = est_minutes * min_rate
    est_total = price + est_bonus
    
    st.info(f"💡 **接單預估補貼**：依系統預估 {est_minutes} 分鐘計算，約可多拿 **${est_bonus:.1f}** 元（預估總收入：**${est_total:.1f}** 元）")
    
    st.divider()
    st.subheader("⏱️ 實際完成時間試算")
    
    # 手動填寫/調整實際花費時間
    actual_minutes = st.number_input(
        "輸入實際完成時間（分鐘）：", 
        min_value=1, 
        max_value=180, 
        value=est_minutes if est_minutes > 0 else 20,
        step=1
    )
    
    actual_bonus = actual_minutes * min_rate
    actual_total = price + actual_bonus
    actual_per_km = actual_total / distance if distance > 0 else 0
    
    # 顯示實際計算結果
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("實際時間補貼", f"+${actual_bonus:.1f}")
    res_col2.metric("最終預計總入帳", f"${actual_total:.1f}")
    res_col3.metric("實際 CP 值", f"${actual_per_km:.1f} / km")

    if actual_minutes > est_minutes and est_minutes > 0:
        extra_time = actual_minutes - est_minutes
        extra_pay = extra_time * min_rate
        st.success(f"🎉 因為多花了 {extra_time} 分鐘（如等餐/塞車），時間補貼增加了 **+${extra_pay:.1f}** 元！")
