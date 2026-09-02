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
        border: 1px solid #06b6d4; padding: 24px; border-radius: 16px; text-align: center; margin-bottom: 24px;
        box-shadow: 0 0 20px rgba(6, 182, 212, 0.25);
    }
    .cyber-header h1 {
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 26px; font-weight: 900; margin: 0;
    }
    [data-testid="stMetric"] { background: #0f172a; border: 1px solid #1e293b; border-radius: 14px; padding: 16px 20px; }
    .stButton > button { background: linear-gradient(135deg, #0284c7 0%, #4f46e5 100%); color: white; border: 1px solid #38bdf8; border-radius: 12px; padding: 12px 24px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="cyber-header">
    <h1>⚖️ 專法「單單計價」需補足金額追蹤器</h1>
    <p style="color:#94a3b8; font-size:13px; margin-top:8px; font-family:monospace;">[ 每單獨立保障 $245/HR 門檻檢視 ]</p>
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

GUARANTEE_HOURLY = 245.0  # 法定保障時薪 $245

uploaded_file = st.file_uploader("上傳 Uber Eats 行程詳細資訊截圖", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="已讀取截圖", use_container_width=True)
    
    img_np = np.array(image)
    result_full, _ = ocr(img_np)
    lines_text = [item[1] for item in result_full] if result_full else []
    full_text = " ".join(lines_text)

    # 辨識金額
    price_match = re.search(r'\$\s*(\d+(\.\d+)?)', full_text)
    total_price = float(price_match.group(1)) if price_match else 0.0
    
    # 辨識時間（分鐘）
    time_match = re.search(r'(\d+)\s*分', full_text)
    total_est_min = int(time_match.group(1)) if time_match else 30

    st.divider()
    st.subheader("⏱️ 行程時間與金額確認")
    
    col_a, col_b = st.columns(2)
    final_price = col_a.number_input("行程實領金額 ($)", value=total_price, step=1.0)
    actual_minutes = col_b.number_input("行程花費時間（分鐘）", value=total_est_min, step=1)
    
    # 單單獨立計算專法門檻
    this_guarantee = (actual_minutes / 60.0) * GUARANTEE_HOURLY
    # 若給的金額小於門檻，計算需補足金額；若大於門檻，需補足金額為 0
    shortfall = max(0.0, this_guarantee - final_price)

    st.divider()
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("單單專法保障門檻", f"${this_guarantee:.1f}")
    res_col2.metric("平台實際給予", f"${final_price:.1f}")
    
    if shortfall > 0:
        res_col3.metric("本單需補足金額", f"${shortfall:.1f}", delta=f"-${shortfall:.1f}", delta_color="inverse")
    else:
        res_col3.metric("本單需補足金額", "$0.0", delta="已達標")

    if st.button("💾 記錄此單需補足金額", use_container_width=True):
        save_record(1, final_price, actual_minutes, round(this_guarantee, 1), round(shortfall, 1))
        st.success("⚡ 已將此單需補足金額存入統計檔案！")

# 歷史需補足金額累積總覽
st.divider()
st.subheader("📊 平台需補足金額累積總覽")

records_df = load_records()

if not records_df.empty:
    total_shortfall = records_df['需補足金額'].sum()
    total_orders = len(records_df)
    
    stat_col1, stat_col2 = st.columns(2)
    stat_col1.metric("已紀錄總筆數", f"{total_orders} 筆")
    stat_col2.metric("平台累計需補足總金額", f"${total_shortfall:.1f}", delta=f"應向平台追討 ${total_shortfall:.1f}" if total_shortfall > 0 else "已達標無差額")

    with st.expander("📋 查看詳細單單差額明細"):
        st.dataframe(records_df[["日期時間", "顯示金額", "實際時間", "專法門檻", "需補足金額", "備註"]], use_container_width=True)
        if st.button("🗑️ 清空所有歷史紀錄"):
            if os.path.exists(LOG_FILE):
                os.remove(LOG_FILE)
                st.rerun()
else:
    st.write("尚無紀錄，請上傳截圖開始追蹤需補足金額！")
