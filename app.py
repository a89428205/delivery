import streamlit as st
from PIL import Image
import numpy as np
import re
import pandas as pd
from datetime import datetime, timedelta
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

try:
    ocr = load_ocr()
    ocr_loaded = True
except Exception as e:
    ocr_loaded = False
    ocr_err = str(e)

BASE_PRICE = 45.0       
PER_MINUTE_RATE = 4.1   

st.subheader("📦 本趟行程訂單設定")
order_type = st.radio("選擇本趟訂單類型", ["單主單（無疊單）", "雙單疊單（A單 + B單）", "三單疊單（A + B + C單）"], horizontal=True)

num_orders = 1
if "雙單" in order_type:
    num_orders = 2
elif "三單" in order_type:
    num_orders = 3

for i in range(3):
    if f"num_p_{i}" not in st.session_state:
        st.session_state[f"num_p_{i}"] = 49.0 if i == 0 else 40.0
    if f"accept_time_{i}" not in st.session_state:
        st.session_state[f"accept_time_{i}"] = datetime.now().strftime("%H:%M")

if "total_finish_time" not in st.session_state:
    st.session_state["total_finish_time"] = datetime.now().strftime("%H:%M")

orders_data = []
st.markdown("---")

for i in range(num_orders):
    label_name = f"A單" if i == 0 else ("B單" if i == 1 else "C單")
    st.markdown(f"##### 🛵 {label_name} 數據")
    
    up_file = st.file_uploader(f"上傳 {label_name} 截圖", type=["png", "jpg", "jpeg"], key=f"up_{i}")
    
    if up_file is not None:
        if not ocr_loaded:
            st.error(f"❌ OCR 模組載入失敗: {ocr_err}")
        else:
            img = Image.open(up_file)
            res, _ = ocr(np.array(img))
            txt = " ".join([item[1] for item in res]) if res else ""
            
            p_m = re.search(r'\$\s*(\d+(\.\d+)?)', txt)
            # 嘗試從截圖抓取時間格式（例如 14:30 或 12點35分）
            t_m = re.search(r'(\d{1,2}[:：]\d{2})', txt)
            
            changed = False
            if p_m:
                val_p = float(p_m.group(1))
                if st.session_state[f"num_p_{i}"] != val_p:
                    st.session_state[f"num_p_{i}"] = val_p
                    changed = True
            if t_m:
                raw_time_str = t_m.group(1).replace('：', ':')
                if st.session_state[f"accept_time_{i}"] != raw_time_str:
                    st.session_state[f"accept_time_{i}"] = raw_time_str
                    changed = True
                    
            if changed:
                st.success(f"⚡ 自動辨識成功：金額 ${st.session_state[f'num_p_{i}']}，接單時間 {st.session_state[f'accept_time_{i}']}")
                st.rerun()

    c1, c2 = st.columns(2)
    final_p = c1.number_input(f"{label_name} 金額 ($)", step=1.0, key=f"num_p_{i}")
    accept_time_str = c2.text_input(f"{label_name} 接單時間 (例如 12:15)", key=f"accept_time_{i}")
    
    orders_data.append({"price": final_p, "accept_time": accept_time_str})
    st.markdown("")

# 整趟行程總送完時間輸入格
st.markdown("---")
total_finish_time_str = st.text_input("⏰ 本趟行程「總共送完」時間點 (例如 14:30)", key="total_finish_time")

# 自動計算每張單的實際花費分鐘數
calculated_orders = []
base_date = datetime.now().date()

try:
    finish_dt = datetime.strptime(f"{base_date} {total_finish_time_str}", "%Y-%m-%d %H:%M")
except:
    finish_dt = datetime.now()

for o in orders_data:
    try:
        accept_dt = datetime.strptime(f"{base_date} {o['accept_time']}", "%Y-%m-%d %H:%M")
        # 若跨日或格式錯誤防呆
        duration = (finish_dt - accept_dt).total_seconds() / 60.0
        if duration < 0:
            duration = 0.0 # 若完工時間小於接單時間，防呆歸零
    except:
        duration = 15.0 # 預設防呆分
        
    calculated_orders.append({
        "price": o["price"],
        "accept_time": o["accept_time"],
        "duration": round(duration, 1)
    })

total_platform_price = sum([o["price"] for o in calculated_orders])
total_labor_target = sum([max(BASE_PRICE, o["duration"] * PER_MINUTE_RATE) for o in calculated_orders])
shortfall = max(0.0, total_labor_target - total_platform_price)

st.divider()
st.markdown("### 📊 勞動部標準結算結果")

# 顯示每單自動算出來的實跑時間
for idx, co in enumerate(calculated_orders):
    label_name = f"A單" if idx == 0 else ("B單" if idx == 1 else "C單")
    st.caption(f"ℹ️ {label_name}（接單 {co['accept_time']} ➔ 總完工 {total_finish_time_str}） ➔ 自動計算實跑：**{co['duration']} 分鐘**")

r1, r2, r3 = st.columns(3)
r1.metric("勞動部認定總門檻", f"${total_labor_target:.1f}")
r2.metric("平台實際總給予", f"${total_platform_price:.1f}")

if shortfall > 0:
    r3.metric("本趟需補足金額", f"${shortfall:.1f}", delta=f"-${shortfall:.1f}", delta_color="inverse")
else:
    r3.metric("本趟需補足金額", "$0.0", delta="已達標")

# 組合詳細紀錄
orders_desc_parts = [f"{('A單' if idx==0 else ('B單' if idx==1 else 'C單'))}(接{o['accept_time']}): 實跑{o['duration']}分/${o['price']}" for idx, o in enumerate(calculated_orders)]
struct_desc = f"總完工 {total_finish_time_str} | " + " + ".join(orders_desc_parts)

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
