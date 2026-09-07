import streamlit as st
from PIL import Image
import numpy as np
import re
import pandas as pd
from datetime import datetime
import os

st.set_page_config(
    page_title="🛵 勞動部認定標準 疊單補足金額追蹤器", 
    page_icon="⚖️", 
    layout="centered"
)

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
        background: #022c22; 
        border: 1px solid #047857; 
        border-radius: 12px; 
        padding: 12px 16px; 
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
    <p style="color:#a7f3d0; font-size:12px; margin-top:6px; font-family:monospace;">[ 核心原則：重疊時間分別計入各筆訂單，依每筆實際服務時間獨立計算 ]</p>
</div>
""", unsafe_allow_html=True)

LOG_FILE = "delivery_labor_standard.csv"

def load_records():
    if os.path.exists(LOG_FILE):
        return pd.read_csv(LOG_FILE)
    else:
        return pd.DataFrame(columns=["日期時間", "訂單結構", "平台總給予", "法定總門檻", "需補足總額", "備註"])

def save_record(struct_str, total_price, total_target, shortfall, note="疊單計算"):
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

@st.cache_resource
def load_ocr():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR()

ocr = load_ocr()

BASE_PRICE = 45.0       
PER_MINUTE_RATE = 4.1   

st.subheader("📦 本趟行程訂單設定")
order_type = st.radio("選擇本趟訂單類型", ["單主單（無疊單）", "雙單疊單（A單 + B單）", "三單疊單（A + B + C單）"], horizontal=True)

num_orders = 1
if "雙單" in order_type:
    num_orders = 2
elif "三單" in order_type:
    num_orders = 3

# 初始化 session state
for i in range(3):
    if f"p_{i}" not in st.session_state:
        st.session_state[f"p_{i}"] = 49.0 if i == 0 else 40.0
    if f"d_{i}" not in st.session_state:
        st.session_state[f"d_{i}"] = 15.0 if i == 0 else 20.0

orders_data = []
st.markdown("---")

for i in range(num_orders):
    label_name = f"A單" if i == 0 else ("B單" if i == 1 else "C單")
    st.markdown(f"##### 🛵 {label_name} 數據")
    
    up_file = st.file_uploader(f"上傳 {label_name} 截圖", type=["png", "jpg", "jpeg"], key=f"up_{i}")
    
    if up_file is not None:
        img = Image.open(up_file)
        # 縮小圖片預覽尺寸，避免在手機版上佔滿版面擋住輸入框
        st.image(img, caption=f"已讀取 {label_name}", width=220)
        res, _ = ocr(np.array(img))
        txt = " ".join([item[1] for item in res]) if res else ""
        
        p_m = re.search(r'\$\s*(\d+(\.\d+)?)', txt)
        t_m = re.search(r'(\d+)\s*分', txt)
        
        changed = False
        if p_m:
            val_p = float(p_m.group(1))
            if st.session_state[f"p_{i}"] != val_p:
                st.session_state[f"p_{i}"] = val_p
                changed = True
        if t_m:
            val_d = float(t_m.group(1))
            if st.session_state[f"d_{i}"] != val_d:
                st.session_state[f"d_{i}"] = val_d
                changed = True
                
        if changed:
            st.success(f"⚡ 自動辨識成功：金額 ${st.session_state[f'p_{i}']}，時間 {st.session_state[f'd_{i}']} 分")
            st.rerun()

    c1, c2 = st.columns(2)
    final_p = c1.number_input(f"{label_name} 金額 ($)", value=float(st.session_state[f"p_{i}"]), step=1.0, key=f"num_p_{i}")
    final_d = c2.number_input(f"{label_name} 實際服務時間（分鐘）", value=float(st.session_state[f"d_{i}"]), step=1.0, key=f"num_d_{i}")
    
    st.session_state[f"p_{i}"] = final_p
    st.session_state[f"d_{i}"] = final_d
    
    orders_data.append({"price": final_p, "duration": final_d})
    st.markdown("")

total_platform_price = sum([o["price"] for o in orders_data])
total_labor_target = sum([max(BASE_PRICE, o["duration"] * PER_MINUTE_RATE) for o in orders_data])
shortfall = max(0.0, total_labor_target - total_platform_price)

st.divider()
st.markdown("### 📊 勞動部標準結算結果")
r1, r2, r3 = st.columns(3)

r1.metric("勞動部認定總門檻", f"${total_labor_target:.1f}")
r2.metric("平台實際總給予", f"${total_platform_price:.1f}")

if shortfall > 0:
    r3.metric("本趟需補足金額", f"${shortfall:.1f}", delta=f"-${shortfall:.1f}", delta_color="inverse")
else:
    r3.metric("本趟需補足金額", "$0.0", delta="已達標")

struct_desc = " + ".join([f"{o['duration']}分(${o['price']})" for o in orders_data])

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
    st.info("目前尚無紀錄，請於上方輸入或上傳疊單截圖開始計算！")
