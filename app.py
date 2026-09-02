import streamlit as st
from PIL import Image
import numpy as np
import re
import pandas as pd
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="外送算單與時薪加成計算器", layout="centered")

st.title("🛵 外送算單 & 保障加成計算器")

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

# 側邊欄：設定保障加成
st.sidebar.header("⚙️ 時段加成設定")
hourly_bonus = st.sidebar.number_input("每小時加成金額 ($/HR)", value=110, step=10)
min_rate = hourly_bonus / 60.0
st.sidebar.markdown(f"**目前每分鐘補貼：** `${min_rate:.2f}` 元")

# 模式選擇
mode = st.radio("選擇接單型態", ["標準模式（自動辨識單數/雙單/三單）", "半路多次夾單（手動/多次累加）"], horizontal=True)

uploaded_file = st.file_uploader("上傳 Uber Eats 接單截圖", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="已上傳截圖", use_container_width=True)
    
    img_np = np.array(image)
    result, _ = ocr(img_np)
    full_text = "\n".join([line[1] for line in result]) if result else ""
    
    # 1. 自動辨識單數 (例如: 外送 (2) 或 外送 (3))
    count_match = re.search(r'外送\s*\(\s*(\d+)\s*\)', full_text)
    auto_count = int(count_match.group(1)) if count_match else 1
    
    # 2. 辨識金額
    price_match = re.search(r'\$\s*(\d+)', full_text)
    price1 = float(price_match.group(1)) if price_match else 0.0
    
    # 3. 辨識預估時間
    time_match = re.search(r'(\d+)\s*分鐘', full_text)
    est_min1 = int(time_match.group(1)) if time_match else 0
    
    # 4. 辨識里程
    dist_match = re.search(r'([\d\.]+)\s*公里', full_text)
    dist1 = float(dist_match.group(1)) if dist_match else 0.0

    extra_price, extra_min, extra_dist = 0.0, 0, 0.0
    final_count = auto_count

    if mode == "半路多次夾單（手動/多次累加）":
        st.divider()
        st.subheader("➕ 半路夾單（第二單/第三單等）補充輸入")
        
        extra_orders = st.number_input("額外夾單數量（如夾兩單填 2）", min_value=1, max_value=5, value=1, step=1)
        final_count = auto_count + extra_orders
        
        col_a, col_b, col_c = st.columns(3)
        extra_price = col_a.number_input("夾單累加總金額 ($)", value=45.0 * extra_orders, step=5.0)
        extra_min = col_b.number_input("夾單累加總時間 (分鐘)", value=10 * extra_orders, step=1)
        extra_dist = col_c.number_input("夾單累加總里程 (km)", value=2.0 * extra_orders, step=0.5)

    total_price = price1 + extra_price
    total_est_min = est_min1 + extra_min
    total_dist = dist1 + extra_dist

    st.divider()
    st.subheader("📊 辨識與統計結果")
    
    st.success(f"🎯 **辨識成功**：此行程共計 **{final_count}** 張單（{'單單' if final_count==1 else f'{final_count} 疊單'}）")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("顯示總金額", f"${total_price:.0f}")
    col2.metric("預估總時間", f"{total_est_min} 分鐘")
    col3.metric("預估總里程", f"{total_dist:.1f} km")
    
    st.divider()
    st.subheader("⏱️ 實際完成時間試算")
    
    actual_minutes = st.number_input(
        f"輸入這 {final_count} 單實際完成總時間（分鐘）：", 
        min_value=1, 
        max_value=300, 
        value=total_est_min if total_est_min > 0 else 30,
        step=1
    )
    
    actual_bonus = actual_minutes * min_rate
    actual_total = total_price + actual_bonus
    actual_per_km = actual_total / total_dist if total_dist > 0 else 0
    
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("實際時間總補貼", f"+${actual_bonus:.1f}")
    res_col2.metric("最終預計總入帳", f"${actual_total:.1f}")
    res_col3.metric("實際 CP 值", f"${actual_per_km:.1f} / km")

    note_text = f"{final_count} 疊單" if final_count > 1 else "單單"
    if st.button("➕ 儲存這筆行程紀錄", use_container_width=True):
        save_record(final_count, total_price, total_est_min, actual_minutes, total_dist, actual_bonus, actual_total, note=note_text)
        st.success(f"✅ 成功紀錄 {final_count} 單行程！已更新下方雙週統計。")

# ---------------------------------------------------------
# 雙週統計
# ---------------------------------------------------------
st.divider()
st.subheader("📈 雙週（14天）補貼統計")

records_df = load_records()

if not records_df.empty:
    records_df['日期時間_dt'] = pd.to_datetime(records_df['日期時間'])
    two_weeks_ago = datetime.now() - timedelta(days=14)
    recent_df = records_df[records_df['日期時間_dt'] >= two_weeks_ago]
    
    total_bonus_14d = recent_df['時間補貼'].sum()
    total_income_14d = recent_df['總收入'].sum()
    total_orders_14d = recent_df['單數'].sum()
    
    stat_col1, stat_col2, stat_col3 = st.columns(3)
    stat_col1.metric("近兩週補貼總額", f"${total_bonus_14d:.1f} 元")
    stat_col2.metric("近兩週總收入", f"${total_income_14d:.1f} 元")
    stat_col3.metric("近兩週累計總單數", f"{total_orders_14d} 單")
    
    with st.expander("📋 查看詳細歷史紀錄明細"):
        st.dataframe(records_df[["日期時間", "單數", "顯示金額", "實際時間", "里程", "時間補貼", "總收入", "備註"]], use_container_width=True)
        if st.button("🗑️ 清空所有歷史紀錄"):
            if os.path.exists(LOG_FILE):
                os.remove(LOG_FILE)
                st.rerun()
else:
    st.write("尚無歷史紀錄，上傳單子試算後點擊「儲存這筆行程紀錄」即可開始累計！")
