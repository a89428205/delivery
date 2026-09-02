import streamlit as st
from PIL import Image
import numpy as np
import re
import pandas as pd
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="外送算單與時薪加成計算器", layout="centered")

st.title("🛵 外送算單 & 保障加成計算器")

# 歷史紀錄檔案路徑
LOG_FILE = "delivery_records.csv"

# 載入歷史紀錄
def load_records():
    if os.path.exists(LOG_FILE):
        return pd.read_csv(LOG_FILE)
    else:
        return pd.DataFrame(columns=["日期時間", "顯示金額", "預估時間", "實際時間", "里程", "時間補貼", "總收入"])

# 儲存新紀錄
def save_record(price, est_min, act_min, dist, bonus, total):
    df = load_records()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_row = pd.DataFrame([{
        "日期時間": now_str,
        "顯示金額": price,
        "預估時間": est_min,
        "實際時間": act_min,
        "里程": dist,
        "時間補貼": bonus,
        "總收入": total
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(LOG_FILE, index=False)
    return df

# 初始化 RapidOCR
@st.cache_resource
def load_ocr():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR()

ocr = load_ocr()

# 側邊欄：設定目前時段的保障加成
st.sidebar.header("⚙️ 時段加成設定")
hourly_bonus = st.sidebar.number_input("每小時加成金額 ($/HR)", value=110, step=10)
min_rate = hourly_bonus / 60.0
st.sidebar.markdown(f"**目前每分鐘補貼：** `${min_rate:.2f}` 元")

# 上傳截圖
uploaded_file = st.file_uploader("上傳 Uber Eats 接單截圖", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="已上傳截圖", use_container_width=True)
    
    img_np = np.array(image)
    result, _ = ocr(img_np)
    
    full_text = ""
    if result:
        full_text = "\n".join([line[1] for line in result])
    
    price_match = re.search(r'\$\s*(\d+)', full_text)
    price = float(price_match.group(1)) if price_match else 0.0
    
    time_match = re.search(r'(\d+)\s*分鐘', full_text)
    est_minutes = int(time_match.group(1)) if time_match else 0
    
    dist_match = re.search(r'([\d\.]+)\s*公里', full_text)
    distance = float(dist_match.group(1)) if dist_match else 0.0

    st.divider()
    st.subheader("📊 辨識結果與預估")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("顯示單價", f"${price:.0f}")
    col2.metric("預估時間", f"{est_minutes} 分鐘")
    col3.metric("預估里程", f"{distance} km")
    
    est_bonus = est_minutes * min_rate
    est_total = price + est_bonus
    
    st.info(f"💡 **接單預估補貼**：依系統預估 {est_minutes} 分鐘計算，約可多拿 **${est_bonus:.1f}** 元（預估總收入：**${est_total:.1f}** 元）")
    
    st.divider()
    st.subheader("⏱️ 實際完成時間試算與紀錄")
    
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
    
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("實際時間補貼", f"+${actual_bonus:.1f}")
    res_col2.metric("最終預計總入帳", f"${actual_total:.1f}")
    res_col3.metric("實際 CP 值", f"${actual_per_km:.1f} / km")

    # 點擊按鈕儲存紀錄
    if st.button("➕ 儲存這筆訂單紀錄", use_container_width=True):
        save_record(price, est_minutes, actual_minutes, distance, actual_bonus, actual_total)
        st.success("✅ 成功紀錄此單！已更新下方雙週統計。")

# ---------------------------------------------------------
# 雙週統計與歷史紀錄區域
# ---------------------------------------------------------
st.divider()
st.subheader("📈 雙週（14天）補貼統計")

records_df = load_records()

if not records_df.empty:
    records_df['日期時間_dt'] = pd.to_datetime(records_df['日期時間'])
    two_weeks_ago = datetime.now() - timedelta(days=14)
    
    # 篩選出近 14 天的資料
    recent_df = records_df[records_df['日期時間_dt'] >= two_weeks_ago]
    
    total_bonus_14d = recent_df['時間補貼'].sum()
    total_income_14d = recent_df['總收入'].sum()
    total_trips_14d = len(recent_df)
    
    stat_col1, stat_col2, stat_col3 = st.columns(3)
    stat_col1.metric("近兩週補貼總額", f"${total_bonus_14d:.1f} 元")
    stat_col2.metric("近兩週總收入", f"${total_income_14d:.1f} 元")
    stat_col3.metric("近兩週累計趟數", f"{total_trips_14d} 趟")
    
    with st.expander("📋 查看詳細歷史紀錄明細"):
        st.dataframe(records_df[["日期時間", "顯示金額", "實際時間", "里程", "時間補貼", "總收入"]], use_container_width=True)
        if st.button("🗑️ 清空所有歷史紀錄"):
            if os.path.exists(LOG_FILE):
                os.remove(LOG_FILE)
                st.rerun()
else:
    st.write("尚無歷史紀錄，上傳單子試算後點擊「儲存這筆訂單紀錄」即可開始累計！")
