import streamlit as st
from PIL import Image
import numpy as np
import re
import pandas as pd
from datetime import datetime
import os

st.set_page_config(
    page_title="⚡ 外送專法 單單需補足金額追蹤器", 
    page_icon="⚖️", 
    layout="centered"
)

st.markdown("""
<style>
    .stApp { background-color: #030712; color: #f3f4f6; }
    
    .cyber-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #030712 100%);
        border: 1px solid #06b6d4; 
        padding: 16px; 
        border-radius: 12px; 
        text-align: center; 
        margin-bottom: 16px;
        box-shadow: 0 0 15px rgba(6, 182, 212, 0.2);
    }
    .cyber-header h1 {
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        font-size: 22px; 
        font-weight: 900; 
        margin: 0;
    }
    
    [data-testid="stMetric"] { 
        background: #0f172a; 
        border: 1px solid #1e293b; 
        border-radius: 12px; 
        padding: 12px 16px; 
    }
    
    @media (max-width: 768px) {
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            margin-bottom: 8px;
        }
        .cyber-header h1 { font-size: 18px; }
    }
    
    .stButton > button { 
        background: linear-gradient(135deg, #0284c7 0%, #4f46e5 100%); 
        color: white; 
        border: 1px solid #38bdf8; 
        border-radius: 12px; 
        padding: 12px 24px; 
        font-weight: bold; 
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="cyber-header">
    <h1>⚖️ 專法「單單計價」需補足金額追蹤器</h1>
    <p style="color:#94a3b8; font-size:12px; margin-top:6px; font-family:monospace;">[ 法定標準：單筆底價 $45 與 服務時間×$4.1 擇高對齊官方明細 ]</p>
</div>
""", unsafe_allow_html=True)

LOG_FILE = "delivery_records.csv"

def load_records():
    if os.path.exists(LOG_FILE):
        return pd.read_csv(LOG_FILE)
    else:
        return pd.DataFrame(columns=["日期時間", "單數", "顯示金額", "實際時間", "專法門檻", "需補足金額", "備註"])

def save_record(order_count, price, act_min, guarantee, shortfall, note="單單"):
    df = load_records()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_row = pd.DataFrame([{
        "日期時間": now_str,
        "單數": order_count,
        "顯示金額": price,
        "實際時間": act_min,
        "專法門檻": guarantee,
        "需補足金額": shortfall,
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

BASE_PRICE = 45.0       # 法定單筆底價 $45
PER_MINUTE_RATE = 4.1   # 每分鐘 $4.1 元

uploaded_file = st.file_uploader("1️⃣ 上傳主要行程 / 初始接單截圖", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="已讀取主行程截圖", use_container_width=True)
    
    img_np = np.array(image)
    result_full, _ = ocr(img_np)
    lines_text = [item[1] for item in result_full] if result_full else []
    full_text = " ".join(lines_text)

    # 1. 辨識主金額
    price_match = re.search(r'\$\s*(\d+(\.\d+)?)', full_text)
    total_price = float(price_match.group(1)) if price_match else 0.0
    
    # 2. 辨識主時間
    time_match = re.search(r'(\d+)\s*分', full_text)
    total_est_min = int(time_match.group(1)) if time_match else 30

    # 3. 辨識主單數
    order_match = re.search(r'外送\s*[\(（](\d+)[\)）]', full_text) or re.search(r'[\(（](\d+)[\)）]', full_text)
    detected_orders = int(order_match.group(1)) if order_match else 1

    st.divider()
    st.subheader("⏱️ 主行程數據確認")
    
    col_a, col_b, col_c = st.columns(3)
    main_price = col_a.number_input("初始金額 ($)", value=total_price, step=1.0)
    main_minutes = col_b.number_input("行程總時間（分鐘）", value=float(total_est_min), step=0.1)
    main_orders = col_c.number_input("初始單數", value=detected_orders, min_value=1, step=1)

    # ---------------- 支援最多 3 張途中夾單模組 ----------------
    st.divider()
    st.subheader("➕ 途中夾單 / 順路加單（最多可追加 3 張）")
    
    extra_count = st.radio("本趟行程途中共增加了幾張夾單？", [0, 1, 2, 3], horizontal=True)
    
    total_extra_orders = 0
    total_extra_price = 0.0
    
    for i in range(1, extra_count + 1):
        st.markdown(f"##### 🛵 第 {i} 張夾單資訊")
        tab_upload, tab_manual = st.tabs([f"📷 上傳第 {i} 張夾單截圖", f"✍️ 手動輸入第 {i} 張"])
        
        ex_orders = 1
        ex_price = 0.0
        
        with tab_upload:
            extra_file = st.file_uploader(f"上傳第 {i} 張夾單截圖", type=["png", "jpg", "jpeg"], key=f"extra_file_{i}")
            if extra_file is not None:
                ex_image = Image.open(extra_file)
                st.image(ex_image, caption=f"已讀取第 {i} 張夾單截圖", use_container_width=True)
                ex_img_np = np.array(ex_image)
                ex_result, _ = ocr(ex_img_np)
                ex_lines = [item[1] for item in ex_result] if ex_result else []
                ex_text = " ".join(ex_lines)
                
                ex_p_match = re.search(r'\$\s*(\d+(\.\d+)?)', ex_text)
                ex_o_match = re.search(r'\+\s*(\d+)', ex_text) or re.search(r'(\d+)\s*單', ex_text)
                
                auto_ex_price = float(ex_p_match.group(1)) if ex_p_match else 0.0
                auto_ex_orders = int(ex_o_match.group(1)) if ex_o_match else 1
                
                up_col1, up_col2 = st.columns(2)
                ex_orders = up_col1.number_input(f"第 {i} 張夾單數 (+單)", value=auto_ex_orders, min_value=1, step=1, key=f"ex_ord_up_{i}")
                ex_price = up_col2.number_input(f"第 {i} 張夾單金額 (+$)", value=auto_ex_price, step=1.0, key=f"ex_prc_up_{i}")
                
        with tab_manual:
            man_col1, man_col2 = st.columns(2)
            man_orders = man_col1.number_input(f"手動第 {i} 張夾單數 (+單)", value=1, min_value=1, step=1, key=f"ex_ord_man_{i}")
            man_price = man_col2.number_input(f"手動第 {i} 張夾單金額 (+$)", value=0.0, step=1.0, key=f"ex_prc_man_{i}")
            
            if extra_file is None:
                ex_orders = man_orders
                ex_price = man_price
                
        total_extra_orders += ex_orders
        total_extra_price += ex_price

    # ---------------- 依照官方明細邏輯：底價與時間換算擇高計算 ----------------
    final_orders = main_orders + total_extra_orders
    final_price = main_price + total_extra_price
    actual_minutes = main_minutes

    # 公式：對應官方明細，法定標準目標為 (單數*底價) 與 (總時間*4.1) 擇高對齊
    statutory_target = max(final_orders * BASE_PRICE, actual_minutes * PER_MINUTE_RATE)
    
    shortfall = max(0.0, statutory_target - final_price)

    st.divider()
    st.markdown(f"#### 📌 最終加總：**共 {final_orders} 單** | 總實領 **${final_price:.1f}**")
    
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("專法法定保障門檻", f"${statutory_target:.1f}")
    res_col2.metric("平台實際給予", f"${final_price:.1f}")
    
    if shortfall > 0:
        res_col3.metric("本單需補足金額", f"${shortfall:.1f}", delta=f"-${shortfall:.1f}", delta_color="inverse")
    else:
        res_col3.metric("本單需補足金額", "$0.0", delta="已達標")

    if st.button("💾 記錄此單需補足金額"):
        note_str = f"{final_orders}單疊單" + (f" (含 {extra_count} 次夾單 +{total_extra_orders}單)" if total_extra_orders > 0 else "")
        save_record(final_orders, final_price, actual_minutes, round(statutory_target, 1), round(shortfall, 1), note_str)
        st.success("⚡ 已將此單需補足金額存入統計檔案！")

# 歷史紀錄總覽
st.divider()
st.subheader("📊 平台需補足金額累積總覽")

records_df = load_records()

if not records_df.empty:
    total_shortfall = records_df['需補足金額'].sum()
    total_orders = len(records_df)
    
    stat_col1, stat_col2 = st.columns(2)
    stat_col1.metric("已紀錄總筆數", f"{total_orders} 筆")
    stat_col2.metric("平台累計需補足總金額", f"${total_shortfall:.1f}", delta=f"應向平台討 ${total_shortfall:.1f}" if total_shortfall > 0 else "已達標無差額")

    with st.expander("📋 查看詳細單單差額明細"):
        st.dataframe(records_df[["日期時間", "單數", "顯示金額", "實際時間", "專法門檻", "需補足金額", "備註"]], use_container_width=True)
        if st.button("🗑️ 清空所有歷史紀錄"):
            if os.path.exists(LOG_FILE):
                os.remove(LOG_FILE)
                st.rerun()
else:
    st.write("尚無紀錄，請上傳截圖開始追蹤需補足金額！")
