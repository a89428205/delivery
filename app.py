import streamlit as st
import pandas as pd
from datetime import datetime, time
import os
import re

st.set_page_config(
    page_title="🛵 勞動部認定標準 疊單補足金額追蹤器", 
    page_icon="⚖️", 
    layout="centered"
)

VISION_AVAILABLE = False
try:
    from rapidocr_onnxruntime import RapidOCR
    import numpy as np
    from PIL import Image
    ocr_engine = RapidOCR()
    VISION_AVAILABLE = True
except Exception as e:
    VISION_AVAILABLE = False

st.markdown("""
<style>
    .stApp { background-color: #030712; color: #f3f4f6; }
    .cyber-header {
        background: linear-gradient(135deg, #064e3b 0%, #065f46 50%, #030712 100%);
        border: 1px solid #10b981; 
        padding: 16px; 
        border-radius: 12px; 
        text-align: center; 
        margin-bottom: 16px;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.2);
    }
    .cyber-header h1 {
        background: linear-gradient(90deg, #34d399, #10b981, #059669);
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        font-size: 20px; 
        font-weight: 900; 
        margin: 0;
    }
    [data-testid="stMetric"] { 
        background: #022c22 !important; 
        border: 1px solid #10b981 !important; 
        border-radius: 12px; 
        padding: 12px 16px; 
    }
    [data-testid="stMetricLabel"] p {
        color: #a7f3d0 !important;
        font-size: 14px !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"] div {
        color: #ffffff !important;
        font-weight: 800 !important;
    }
    .stCaption p {
        color: #6ee7b7 !important;
        font-size: 13px !important;
        font-weight: 500 !important;
    }
    .stButton > button { 
        background: linear-gradient(135deg, #059669 0%, #10b981 100%); 
        color: white; 
        border: 1px solid #34d399; 
        border-radius: 12px; 
        padding: 12px 24px; 
        font-weight: bold; 
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="cyber-header">
    <h1>⚖️ 勞動部認定標準：疊單補足金額追蹤器</h1>
    <p style="color:#a7f3d0; font-size:12px; margin-top:6px; font-family:monospace;">[ 🎯 時間與金額精準連動修復版 ]</p>
</div>
""", unsafe_allow_html=True)

LOG_FILE = "delivery_labor_standard.csv"

def load_records():
    if os.path.exists(LOG_FILE):
        return pd.read_csv(LOG_FILE)
    else:
        return pd.DataFrame(columns=["日期時間", "訂單結構", "平台總給予", "法定總門檻", "需補足總額", "備註"])

def save_record(struct_str, total_price, total_target, shortfall, note="精算記錄"):
    df = load_records()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_row = pd.DataFrame([{
        "日期時間": now_str,
        "訂單結構": struct_str,
        "平台總給予": total_price,
        "法定總門檻": total_target,
        "需補足總額": shortfall,
        "備註": note
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(LOG_FILE, index=False)
    return df

BASE_PRICE = 45.0       
PER_MINUTE_RATE = 4.1   

st.subheader("📦 本趟行程訂單設定")
order_type = st.radio("選擇本趟訂單類型", ["單主單（無疊單）", "雙單疊單（A單 + B單）", "三單疊單（A + B + C單）"], horizontal=True)

num_orders = 1
if "雙單" in order_type:
    num_orders = 2
elif "三單" in order_type:
    num_orders = 3

orders_data = []
st.markdown("---")

for i in range(num_orders):
    label_name = f"A單" if i == 0 else ("B單" if i == 1 else "C單")
    st.markdown(f"##### 🛵 {label_name} 數據")
    
    num_p_key = f"num_p_{i}"
    start_t_key = f"start_t_{i}"
    end_t_key = f"end_t_{i}"
    
    if num_p_key not in st.session_state:
        st.session_state[num_p_key] = 94.0 if i==0 else (50.0 if i==1 else 40.0)
    if start_t_key not in st.session_state:
        st.session_state[start_t_key] = time(18, 52)
    if end_t_key not in st.session_state:
        st.session_state[end_t_key] = time(19, 16)

    uploaded_file = st.file_uploader(f"📸 上傳 {label_name} 截圖", type=["png", "jpg", "jpeg"], key=f"upload_{i}")
    
    if uploaded_file and VISION_AVAILABLE:
        try:
            image = Image.open(uploaded_file).convert("RGB")
            img_np = np.array(image)
            
            result, _ = ocr_engine(img_np)
            if result:
                full_str = " ".join([r[1] for r in result])
                updated = False
                
                # 1. 抓取左上角系統時間
                time_match = re.search(r'(\d{1,2})[:：](\d{2})', full_str)
                base_time = datetime.now()
                if time_match:
                    hr, mn = int(time_match.group(1)), int(time_match.group(2))
                    base_time = base_time.replace(hour=hr, minute=mn, second=0)
                    st.session_state[start_t_key] = base_time.time()
                    updated = True
                
                # 2. 抓取金額
                found_prices = re.findall(r'[$＄]\s*(\d{2,3})', full_str)
                if found_prices:
                    st.session_state[num_p_key] = float(found_prices[0])
                    st.success(f"💰 成功辨識 {label_name} 金額：${found_prices[0]}")
                    updated = True
                
                # 3. 抓取預估分鐘數
                found_mins = re.findall(r'(\d+)\s*分鐘', full_str)
                if found_mins:
                    total_mins_val = float(found_mins[0])
                    end_dt_calc = base_time + pd.Timedelta(minutes=total_mins_val)
                    st.session_state[end_t_key] = end_dt_calc.time()
                    st.success(f"⏱️ 成功辨識 {label_name} 預估時間：共 {total_mins_val} 分鐘")
                    updated = True
                
                if updated:
                    st.rerun()
        except Exception as e:
            st.warning(f"⚠️ 解析發生錯誤：{e}")

    c1, c2 = st.columns(2)
    final_p = c1.number_input(f"{label_name} 金額 ($)", step=1.0, key=num_p_key)
    
    t_col1, t_col2 = st.columns(2)
    start_t = t_col1.time_input(f"{label_name} 接單時間", key=start_t_key)
    end_t = t_col2.time_input(f"{label_name} 送達時間", key=end_t_key)
    
    start_dt = datetime.combine(datetime.today(), start_t)
    end_dt = datetime.combine(datetime.today(), end_t)
    diff_mins = (end_dt - start_dt).total_seconds() / 60.0
    if diff_mins < 0:
        diff_mins += 24 * 60
        
    st.caption(f"⏱️ {label_name} 獨立計算實跑時間：**{diff_mins:.1f} 分鐘**")
    
    orders_data.append({
        "label": label_name,
        "price": final_p,
        "duration": max(1.0, diff_mins),
        "start": start_t.strftime("%H:%M"),
        "end": end_t.strftime("%H:%M")
    })
    st.markdown("---")

total_trip_minutes = st.number_input("⏱️ 整趟行程實際總花費分鐘數", value=24.0, min_value=1.0, step=1.0, key="total_duration")

calculated_orders = []
for o in orders_data:
    single_target = max(BASE_PRICE, o["duration"] * PER_MINUTE_RATE)
    calculated_orders.append({
        "label": o["label"],
        "price": o["price"],
        "duration": o["duration"],
        "target": single_target,
        "time_str": f"{o['start']}~{o['end']}"
    })

total_platform_price = sum([o["price"] for o in calculated_orders])
total_labor_target = sum([o["target"] for o in calculated_orders])
shortfall = max(0.0, total_labor_target - total_platform_price)

st.markdown("### 📊 勞動部標準結算結果（綠色獨立加總公式）")

for co in calculated_orders:
    st.caption(f"ℹ️ {co['label']}（{co['time_str']}，共 {co['duration']:.0f}分） ➔ 獨立門檻：**${co['target']:.1f} 元**")

r1, r2, r3 = st.columns(3)
r1.metric("勞動部認定總門檻", f"${total_labor_target:.1f}")
r2.metric("平台實際總給予", f"${total_platform_price:.1f}")

if shortfall > 0:
    r3.metric("本趟需補足金額", f"${shortfall:.1f}", delta=f"-${shortfall:.1f}", delta_color="inverse")
else:
    r3.metric("本趟需補足金額", "$0.0", delta="已達標")

orders_desc_parts = [f"{o['label']}({o['time_str']}, {o['duration']:.0f}分): ${o['price']}" for o in calculated_orders]
struct_desc = f"總花費 {total_trip_minutes}分 | " + " | ".join(orders_desc_parts)

if st.button("💾 記錄此趟勞動部標準差額"):
    save_record(order_type, round(total_platform_price, 1), round(total_labor_target, 1), round(shortfall, 1), struct_desc)
    st.success("✅ 已成功寫入歷史紀錄！")

st.divider()
st.subheader("📋 歷史紀錄總覽")
df = load_records()
if not df.empty:
    total_sum = df["需補足總額"].sum()
    st.metric("累計應向平台追討總額", f"${total_sum:.1f}")
    st.dataframe(df, use_container_width=True)
    if st.button("🗑️ 清空歷史紀錄"):
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
            st.rerun()
else:
    st.info("目前尚無紀錄，請於上方輸入資料開始計算！")
