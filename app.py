import streamlit as st
from PIL import Image
from rapidocr_onnxruntime import RapidOCR
import numpy as np
import re

st.set_page_config(page_title="外送AI自動看單神器", page_icon="📸", layout="centered")

st.title("📸 外送 AI 截圖看單神器 (精準版)")
st.caption("改用 ONNX 極速引擎，自動精準抓取 Uber Eats 金額、時間、店家數與公里數！")

@st.cache_resource
def load_ocr():
    return RapidOCR()

engine = load_ocr()

uploaded_file = st.file_uploader("選擇或直接上傳派單截圖", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="已上傳截圖", use_container_width=True)
    
    if "ocr_data" not in st.session_state or st.session_state.get("last_file") != uploaded_file.name:
        with st.spinner("⚡ 0.5秒極速掃描中..."):
            img_np = np.array(image)
            results, _ = engine(img_np)
            
            full_text = ""
            if results:
                full_text = " ".join([res[1] for res in results])
            
            # 1. 抓金額 (優先尋找 $ 符號後面的主金額)
            money = 0
            money_matches = re.findall(r'\$\s*(\d{2,4})', full_text)
            if money_matches:
                money = max([int(m) for m in money_matches])
            else:
                alt_match = re.search(r'(?:包含|報酬|\b)\s*(\d{2,4})\b', full_text)
                if alt_match:
                    money = int(alt_match.group(1))

            # 2. 抓時間
            mins_match = re.search(r'(\d{1,3})\s*(?:分鐘|分|min)', full_text, re.IGNORECASE)
            mins = int(mins_match.group(1)) if mins_match else 0
            
            # 3. 抓公里
            km_match = re.search(r'([\d\.]+)\s*(?:公里|km)', full_text, re.IGNORECASE)
            distance = float(km_match.group(1)) if km_match else 0.0
            
            # 4. 精準判斷店家數：抓取 "外送 (N)" 或 "外送 N" 的數字
            shops = 1
            shop_match = re.search(r'外送\s*[\(（]?\s*(\d+)\s*[\)）]?', full_text)
            if shop_match:
                shops = int(shop_match.group(1))
            elif "(3)" in full_text or "（3）" in full_text:
                shops = 3
            elif "(2)" in full_text or "（2）" in full_text:
                shops = 2
            
            # 5. 判斷高樓層 (計算 4 樓以上的地點數量)
            floors = re.findall(r'(\d+)\s*樓', full_text)
            stairs = sum(1 for f in floors if int(f) >= 4)

            st.session_state.ocr_data = {
                "money": money,
                "mins": mins,
                "distance": distance,
                "shops": shops,
                "stairs": stairs
            }
            st.session_state.last_file = uploaded_file.name

    data = st.session_state.ocr_data

    st.success("✨ 解析完成！請確認數據：")

    col1, col2, col3 = st.columns(3)
    with col1:
        money = st.number_input("預估金額 ($)", value=data["money"], step=5)
    with col2:
        mins = st.number_input("預估時間 (分)", value=data["mins"], step=1)
    with col3:
        distance = st.number_input("距離 (公里)", value=data["distance"], step=0.1)

    st.subheader("⚙️ 隱形坑點勾選")
    c1, c2, c3 = st.columns(3)
    shops = c1.number_input("取餐店家數", min_value=1, value=data["shops"], step=1)
    stairs = c2.number_input("高樓層/商辦點數", min_value=0, value=data["stairs"], step=1)
    is_far = c3.checkbox("送達點為邊緣區")

    # 計算邏輯
    extra_time = (shops - 1) * 8 + stairs * 6 + (12 if is_far else 0)
    real_time = mins + extra_time if mins > 0 else 1
    
    real_hourly = (money / real_time) * 60 if real_time > 0 else 0
    km_price = money / distance if distance > 0 else 0

    st.divider()
    st.subheader("📊 算單結果與建議")
    
    st.metric("修正後真實總時間", f"{real_time} 分鐘", f"原預估 {mins} 分 (+{extra_time}分)")
    
    col_a, col_b = st.columns(2)
    col_a.metric("真實折算時薪", f"${real_hourly:.1f} / 時")
    col_b.metric("1 公里價值", f"${km_price:.1f} 元 / km")

    if real_hourly >= 300 and km_price >= 22:
        st.success("✅ **秒接（優質加成單）**")
    elif real_hourly >= 250 and km_price >= 18:
        st.warning("⚠️ **離峰可考慮（保底單）**")
    else:
        st.error("❌ **果斷拉掉（地雷單）**")
