import streamlit as st
from PIL import Image
import numpy as np
import re
import pandas as pd
from datetime import datetime, timedelta
import os

st.set_page_config(
    page_title="⚡ 補錢計算王 CYBER PRO", 
    page_icon="⚡", 
    layout="centered"
)

# 賽博朋克 / 鋼鐵人 HUD 風格 CSS
st.markdown("""
<style>
    .stApp {
        background-color: #030712;
        color: #f3f4f6;
    }
    
    [data-testid="stSidebar"] {
        background-color: #0b0f19;
        border-right: 1px solid #1e293b;
    }

    .cyber-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #030712 100%);
        border: 1px solid #06b6d4;
        padding: 24px;
        border-radius: 16px;
        text-align: center;
        margin-bottom: 24px;
        box-shadow: 0 0 20px rgba(6, 182, 212, 0.25);
    }
    
    .cyber-header h1 {
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 28px;
        font-weight: 900;
        margin: 0;
        letter-spacing: 1px;
    }

    [data-testid="stMetric"] {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 14px;
        padding: 16px 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        transition: all 0.3s ease;
    }
    
    [data-testid="stMetric"]:hover {
        border-color: #38bdf8;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.4);
        transform: translateY(-2px);
    }
    
    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 13px !important;
        font-weight: 600;
    }
    
    [data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-size: 24px !important;
        font-weight: bold !important;
        text-shadow: 0 0 8px rgba(56, 189, 248, 0.3);
    }

    .stButton > button {
        background: linear-gradient(135deg, #0284c7 0%, #4f46e5 100%);
        color: white;
        border: 1px solid #38bdf8;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: bold;
        font-size: 16px;
        box-shadow: 0 0 15px rgba(2, 132, 199, 0.4);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #0369a1 0%, #4338ca 100%);
        box-shadow: 0 0 25px rgba(56, 189, 248, 0.7);
        transform: scale(1.02);
    }

    [data-testid="stFileUploader"] {
        background-color: transparent !important;
    }

    [data-testid="stFileUploaderDropzone"] {
        background-color: #0f172a !important;
        border: 2px dashed #38bdf8 !important;
        border-radius: 12px !important;
        transition: all 0.3s ease;
    }

    [data-testid="stFileUploaderDropzone"]:hover {
        background-color: #1e293b !important;
        border-color: #818cf8 !important;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.3);
    }

    [data-testid="stFileUploaderDropzone"] button {
        background-color: #1e293b !important;
        color: #38bdf8 !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 8px !important;
    }

    [data-testid="stFileUploaderDropzone"] div, 
    [data-testid="stFileUploaderDropzone"] span,
    [data-testid="stFileUploaderDropzone"] small,
    [data-testid="stFileUploaderDropzone"] p {
        color: #cbd5e1 !important;
    }
</style>
""", unsafe_allow_html=True)

# Banner 區塊
st.markdown("""
<div class="cyber-header">
    <h1>⚡ 補錢計算王 CYBER</h1>
    <p style="color:#94a3b8; font-size:13px; margin-top:8px; font-family:monospace;">[ AI-POWERED OCR & AUTOMATIC MILEAGE TRACKER ]</p>
</div>
""", unsafe_allow_html=True)

LOG_FILE = "delivery_records.csv"

def load_records():
    if os.path.exists(LOG_FILE):
        return pd.read_csv(LOG_FILE)
    else:
        return pd.DataFrame(columns=["日期時間", "單數", "顯示金額", "預估時間", "實際時間", "里程", "時間補貼", "總收入", "備註"])

def save_record(order_count, price, est_min, act_min, dist, bonus, total, note="單單"):
    df = load_records()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_row = pd.DataFrame([{
        "日期時間": now_str,
        "單數": order_count,
        "顯示金額": price,
        "預估時間": est_min,
        "實際時間": act_min,
        "里程": dist,
        "時間補貼": bonus,
        "總收入": total,
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

# 側邊欄
st.sidebar.header("⚙️ 補貼參數設定")
hourly_bonus = st.sidebar.number_input("每小時保障加成 ($/HR)", value=110, step=10)
min_rate = hourly_bonus / 60.0
st.sidebar.markdown(f"⚡ **每分鐘自動算力補貼：** `${min_rate:.2f}` 元")

mode = st.radio("模式選擇", ["⚡ 上傳截圖自動辨識", "➕ 半路夾單（手動累加）"], horizontal=True)

uploaded_file = st.file_uploader("上傳 Uber Eats 接單截圖", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="已讀取截圖", use_container_width=True)
    
    # 判斷整張圖的全圖文字
    img_np = np.array(image)
    result_full, _ = ocr(img_np)
    full_lines = [line[1] for line in result_full] if result_full else []
    full_text = " ".join(full_lines)
    
    # 專門裁切圖片上方 35%（單數資訊通常出現在最頂端標題區）
    w, h = image.size
    top_crop = image.crop((0, 0, w, int(h * 0.35)))
    result_top, _ = ocr(np.array(top_crop))
    top_lines = [line[1] for line in result_top] if result_top else []
    top_text = " ".join(top_lines)

    # === 精準單數判斷機制 ===
    auto_count = 1
    
    # 1. 在頂部區域尋找 (X) 或 ( X ) 相關特徵
    top_bracket = re.search(r'[\(（\s]+([2-5])[\)）\s]+', top_text)
    # 2. 尋找「外送」前後緊鄰的數字
    delivery_near_num = re.search(r'外送.*?([2-5])|([2-5]).*?外送', top_text)
    # 3. 全圖尋找 "X 筆" 或 "X 個"
    items_count = re.search(r'([2-5])\s*(?:筆|個|份)', full_text)

    if top_bracket:
        auto_count = int(top_bracket.group(1))
    elif delivery_near_num:
        num = delivery_near_num.group(1) or delivery_near_num.group(2)
        auto_count = int(num)
    elif items_count:
        auto_count = int(items_count.group(1))

    # 金額、時間、里程辨識
    price_match = re.search(r'\$\s*(\d+)', full_text)
    price1 = float(price_match.group(1)) if price_match else 0.0
    
    time_match = re.search(r'(\d+)\s*分鐘', full_text)
    est_min1 = int(time_match.group(1)) if time_match else 0
    
    dist_match = re.search(r'([\d\.]+)\s*公里', full_text)
    dist1 = float(dist_match.group(1)) if dist_match else 0.0

    st.divider()
    
    final_count = st.selectbox(
        "🎯 辨識單數確認：", 
        options=[1, 2, 3, 4, 5], 
        index=auto_count - 1
    )

    extra_price, extra_min, extra_dist = 0.0, 0, 0.0

    if mode == "➕ 半路夾單（手動累加）":
        st.subheader("➕ 半路夾單補充")
        extra_orders = st.number_input("追加單數", min_value=1, max_value=5, value=1, step=1)
        final_count += extra_orders
        
        col_a, col_b, col_c = st.columns(3)
        extra_price = col_a.number_input("夾單累加金額 ($)", value=45.0 * extra_orders, step=5.0)
        extra_min = col_b.number_input("夾單累加時間 (分)", value=10 * extra_orders, step=1)
        extra_dist = col_c.number_input("夾單累加里程 (km)", value=2.0 * extra_orders, step=0.5)

    total_price = price1 + extra_price
    total_est_min = est_min1 + extra_min
    total_dist = dist1 + extra_dist

    col1, col2, col3 = st.columns(3)
    col1.metric("開價總額", f"${total_price:.0f}")
    col2.metric("預估時間", f"{total_est_min} 分鐘")
    col3.metric("預估里程", f"{total_dist:.1f} km")
    
    st.divider()
    st.subheader("⏱️ 實跑精算")
    
    actual_minutes = st.number_input(
        f"輸入這 {final_count} 單實際完成時間（分鐘）：", 
        min_value=1, 
        max_value=300, 
        value=total_est_min if total_est_min > 0 else 30,
        step=1
    )
    
    actual_bonus = actual_minutes * min_rate
    actual_total = total_price + actual_bonus
    actual_per_km = actual_total / total_dist if total_dist > 0 else 0
    
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("時間補貼金額", f"+${actual_bonus:.1f}")
    res_col2.metric("最終預計總入帳", f"${actual_total:.1f}")
    res_col3.metric("實際 CP 值", f"${actual_per_km:.1f}/km")

    note_text = f"{final_count} 疊單" if final_count > 1 else "單單"
    if st.button("💾 寫入資料庫並自動記帳", use_container_width=True):
        save_record(final_count, total_price, total_est_min, actual_minutes, total_dist, actual_bonus, actual_total, note=note_text)
        st.success(f"⚡ 成功紀錄 {final_count} 疊單行程！")

# 雙週數據
st.divider()
st.subheader("📈 雙週（14天）算力與帳務總覽")

records_df = load_records()

if not records_df.empty:
    records_df['日期時間_dt'] = pd.to_datetime(records_df['日期時間'])
    two_weeks_ago = datetime.now() - timedelta(days=14)
    recent_df = records_df[records_df['日期時間_dt'] >= two_weeks_ago]
    
    total_bonus_14d = recent_df['時間補貼'].sum()
    total_income_14d = recent_df['總收入'].sum()
    total_orders_14d = recent_df['單數'].sum()
    
    stat_col1, stat_col2, stat_col3 = st.columns(3)
    stat_col1.metric("近兩週補貼總額", f"${total_bonus_14d:.1f}")
    stat_col2.metric("近兩週總預估收入", f"${total_income_14d:.1f}")
    stat_col3.metric("近兩週完成單數", f"{total_orders_14d} 單")
    
    with st.expander("📋 查看詳細歷史明細"):
        st.dataframe(records_df[["日期時間", "單數", "顯示金額", "實際時間", "里程", "時間補貼", "總收入", "備註"]], use_container_width=True)
        if st.button("🗑️ 清空所有歷史紀錄"):
            if os.path.exists(LOG_FILE):
                os.remove(LOG_FILE)
                st.rerun()
else:
    st.write("尚無歷史紀錄，上傳單子試算後即可開始自動記帳！")
