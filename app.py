import streamlit as st
from PIL import Image
import numpy as np
import re
import pandas as pd
from datetime import datetime, timedelta
import os

st.set_page_config(
    page_title="⚡ 專法雙週補貼精算王", 
    page_icon="⚖️", 
    layout="centered"
)

# 賽博朋克 HUD 風格 CSS
st.markdown("""
<style>
    .stApp { background-color: #030712; color: #f3f4f6; }
    [data-testid="stSidebar"] { background-color: #0b0f19; border-right: 1px solid #1e293b; }
    .cyber-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #030712 100%);
        border: 1px solid #06b6d4; padding: 24px; border-radius: 16px; text-align: center; margin-bottom: 24px;
        box-shadow: 0 0 20px rgba(6, 182, 212, 0.25);
    }
    .cyber-header h1 {
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 26px; font-weight: 900; margin: 0;
    }
    div[data-baseweb="input"] { background-color: #1e293b !important; border: 1px solid #38bdf8 !important; border-radius: 8px !important; }
    div[data-baseweb="input"] input { color: #38bdf8 !important; font-weight: bold !important; }
    [data-testid="stMetric"] { background: #0f172a; border: 1px solid #1e293b; border-radius: 14px; padding: 16px 20px; }
    [data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: 13px !important; }
    [data-testid="stMetricValue"] { color: #38bdf8 !important; font-size: 24px !important; font-weight: bold !important; }
    .stButton > button { background: linear-gradient(135deg, #0284c7 0%, #4f46e5 100%); color: white; border: 1px solid #38bdf8; border-radius: 12px; padding: 12px 24px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="cyber-header">
    <h1>⚖️ 外送專法 雙週保障補貼精算王</h1>
    <p style="color:#94a3b8; font-size:13px; margin-top:8px; font-family:monospace;">[ 專法最低報酬門檻 & 雙週差額檢測器 ]</p>
</div>
""", unsafe_allow_html=True)

LOG_FILE = "delivery_records.csv"

def load_records():
    if os.path.exists(LOG_FILE):
        return pd.read_csv(LOG_FILE)
    else:
        return pd.DataFrame(columns=["日期時間", "單數", "顯示金額", "預估時間", "實際時間", "里程", "備註"])

def save_record(order_count, price, est_min, act_min, dist, note="單單"):
    df = load_records()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_row = pd.DataFrame([{
        "日期時間": now_str,
        "單數": order_count,
        "顯示金額": price,
        "預估時間": est_min,
        "實際時間": act_min,
        "里程": dist,
        "備註": note
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(LOG_FILE, index=False)
    return df

@st.cache_resource
def load_ocr():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR()

ocr = load_ocr()

# 側邊欄：法規保障基準
st.sidebar.header("⚖️ 專法保障參數")
guarantee_hourly = st.sidebar.number_input("專法保障最低時薪 ($/HR)", value=183, step=1)
st.sidebar.caption("💡 說明：專法規定雙週結算，若總報酬低於 (總實跑時數 × 保障時薪)，平台需補足差額。")

uploaded_file = st.file_uploader("上傳 Uber Eats 接單截圖", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="已讀取截圖", use_container_width=True)
    
    img_np = np.array(image)
    result_full, _ = ocr(img_np)
    lines_text = [item[1] for item in result_full] if result_full else []
    full_text = " ".join(lines_text)

    # 判斷單數
    clean_text = full_text.replace("（", "(").replace("）", ")").replace(" ", "")
    bracket_match = re.search(r'外送\(?([2-5])\)?', clean_text)
    address_count = len(re.findall(r'\d{3}\s*台灣|\d{3}台灣|台灣[臺台]北', full_text))

    if bracket_match:
        auto_count = int(bracket_match.group(1))
    elif address_count >= 2:
        auto_count = address_count
    else:
        auto_count = 1

    # 辨識金額、時間、里程
    price_match = re.search(r'\$\s*(\d+)', full_text)
    total_price = float(price_match.group(1)) if price_match else 0.0
    
    time_match = re.search(r'(\d+)\s*分鐘', full_text)
    total_est_min = int(time_match.group(1)) if time_match else 0
    
    dist_match = re.search(r'([\d\.]+)\s*公里', full_text)
    total_dist = float(dist_match.group(1)) if dist_match else 0.0

    st.divider()
    final_count = st.selectbox("🎯 辨識單數確認：", options=[1, 2, 3, 4, 5], index=auto_count - 1)

    col1, col2, col3 = st.columns(3)
    col1.metric("截圖開價金額", f"${total_price:.0f}")
    col2.metric("預估時間", f"{total_est_min} 分鐘")
    col3.metric("預估里程", f"{total_dist:.1f} km")
    
    st.divider()
    st.subheader("⏱️ 輸入這趟實跑時間")
    
    actual_minutes = st.number_input(
        f"輸入這 {final_count} 單實際完成時間（分鐘）：", 
        min_value=1, 
        max_value=300, 
        value=total_est_min if total_est_min > 0 else 20,
        step=1
    )
    
    # 這一單在專法下的基本保障金額
    this_guarantee = (actual_minutes / 60.0) * guarantee_hourly
    
    res_col1, res_col2 = st.columns(2)
    res_col1.metric("這單專法門檻金額", f"${this_guarantee:.1f}")
    if total_price >= this_guarantee:
        res_col2.metric("這單狀態", "高於門檻", delta=f"+${total_price - this_guarantee:.1f}")
    else:
        res_col2.metric("這單狀態", "低於門檻", delta=f"-${this_guarantee - total_price:.1f}", delta_color="inverse")

    note_text = f"{final_count} 疊單" if final_count > 1 else "單單"
    if st.button("💾 記錄此單並併入雙週統計", use_container_width=True):
        save_record(final_count, total_price, total_est_min, actual_minutes, total_dist, note=note_text)
        st.success("⚡ 已成功記入雙週資料庫！")

# 雙週專法結算區塊
st.divider()
st.subheader("📈 近 14 天雙週專法差額結算")

records_df = load_records()

if not records_df.empty:
    records_df['日期時間_dt'] = pd.to_datetime(records_df['日期時間'])
    two_weeks_ago = datetime.now() - timedelta(days=14)
    recent_df = records_df[records_df['日期時間_dt'] >= two_weeks_ago]
    
    total_income_14d = recent_df['顯示金額'].sum()
    total_orders_14d = recent_df['單數'].sum()
    total_minutes_14d = recent_df['實際時間'].sum()
    total_hours_14d = total_minutes_14d / 60.0
    
    # 算雙週總保障金額與差額
    total_guarantee_14d = total_hours_14d * guarantee_hourly
    shortfall_14d = total_guarantee_14d - total_income_14d

    stat_col1, stat_col2, stat_col3 = st.columns(3)
    stat_col1.metric("雙週累積實跑時數", f"{total_hours_14d:.1f} 小時")
    stat_col2.metric("雙週實際總收入", f"${total_income_14d:.0f}")
    stat_col3.metric("雙週專法保障總門檻", f"${total_guarantee_14d:.0f}")

    st.markdown("---")
    if shortfall_14d > 0:
        st.error(f"🚨 **雙週結算檢測結果：未達保障門檻！**\n\n預估平台在雙週結算時，必須補貼您 **`${shortfall_14d:.1f}`** 元差額！")
    else:
        st.success(f"🎉 **雙週結算檢測結果：已達保障門檻！**\n\n您的實際收入高於保障門檻 **`${abs(shortfall_14d):.1f}`** 元，平台無須額外補貼。")

    with st.expander("📋 查看詳細歷史明細"):
        st.dataframe(records_df[["日期時間", "單數", "顯示金額", "預估時間", "實際時間", "里程", "備註"]], use_container_width=True)
        if st.button("🗑️ 清空所有歷史紀錄"):
            if os.path.exists(LOG_FILE):
                os.remove(LOG_FILE)
                st.rerun()
else:
    st.write("尚無歷史紀錄，上傳單子試算後即可開始累積 14 天雙週數據！")
