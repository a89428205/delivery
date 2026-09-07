import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import google.generativeai as genai

# ==========================================
# 💡 請把金鑰直接貼在下方引號內（最快最穩）
# ==========================================
MY_API_KEY = "AQ.Ab8RN6JdRzqLfOyWicsiEY6n1znm9FC0pzaTc1ia1lLy3NZOGA"

try:
    genai.configure(api_key=MY_API_KEY)
    AI_AVAILABLE = True
except Exception:
    AI_AVAILABLE = False

st.set_page_config(
    page_title="外送專法 獨立單計價補足金額追蹤器",
    page_icon="🛵",
    layout="centered"
)

st.markdown("""
<style>
.stApp { background-color: #030712; color: #f3f4f6; }
.cyber-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #030712 100%);
    border: 1px solid #10b981;
    padding: 16px;
    border-radius: 12px;
    text-align: center;
    margin-bottom: 16px;
    box-shadow: 0 0 15px rgba(16, 185, 129, 0.2);
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="cyber-header">
    <h2 style="color: #10b981; margin:0;">🛵 外送專法獨立單計價補足金額追蹤器</h2>
    <p style="color: #94a3b8; font-size: 14px; margin-top: 4px;">AI 智慧截圖自動解析 • 支援主行程與多張夾單</p>
</div>
""", unsafe_allow_html=True)

if 'records' not in st.session_state:
    st.session_state.records = []

if 'current_batch' not in st.session_state:
    st.session_state.current_batch = [
        {"amount": 49.0, "duration": 13.0}
    ]

uploaded_file = st.file_uploader("📷 上傳外送截圖（自動秒讀金額與時間）", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="已上傳的截圖預覽")
    
    if AI_AVAILABLE and MY_API_KEY != "你的實際API金鑰":
        with st.spinner("⚡ AI 正在精準解析截圖中的金額與時間..."):
            try:
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content([
                    image, 
                    "這是一張外送訂單截圖。請幫我找出兩個數值：1. 金額（例如圖中的 101） 2. 時間（分鐘，例如圖中的 25）。請嚴格只回傳 JSON 格式：{\"amount\": 數字, \"duration\": 數字}"
                ])
                import json
                text_res = response.text.strip()
                if "```json" in text_res:
                    text_res = text_res.split("```json")[1].split("```")[0].strip()
                elif "```" in text_res:
                    text_res = text_res.split("```")[1].split("```")[0].strip()
                
                data = json.loads(text_res)
                parsed_amt = float(data.get("amount", 49.0))
                parsed_dur = float(data.get("duration", 13.0))
                
                st.session_state.current_batch[0]["amount"] = parsed_amt
                st.session_state.current_batch[0]["duration"] = parsed_dur
                st.success(f"✅ 成功辨識！金額：${parsed_amt}，時間：{parsed_dur} 分鐘")
                st.rerun()
            except Exception as e:
                st.error(f"⚠️ AI 解析錯誤：{e}")
    else:
        st.warning("⚠️ 請先在程式碼第 8 行填入你的 Gemini API 金鑰！")

st.markdown("### 📦 本趟行程明細（首張單 + 夾單/疊單）")

for i, item in enumerate(st.session_state.current_batch):
    cols = st.columns([3, 3, 1])
    with cols[0]:
        st.session_state.current_batch[i]["amount"] = st.number_input(
            f"第 {i+1} 張單金額 ($)", value=float(item["amount"]), step=1.0, key=f"amt_{i}"
        )
    with cols[1]:
        st.session_state.current_batch[i]["duration"] = st.number_input(
            f"第 {i+1} 張單時間 (分)", value=float(item["duration"]), step=1.0, key=f"dur_{i}"
        )
    with cols[2]:
        st.write("")
        st.write("")
        if len(st.session_state.current_batch) > 1:
            if st.button("🗑️", key=f"del_{i}"):
                st.session_state.current_batch.pop(i)
                st.rerun()

if st.button("➕ 增加一張夾單/疊單"):
    st.session_state.current_batch.append({"amount": 80.0, "duration": 10.0})
    st.rerun()

total_amount = sum([item["amount"] for item in st.session_state.current_batch])
total_duration = sum([item["duration"] for item in st.session_state.current_batch])

threshold = max(45.0, total_duration * 4.1)
diff = threshold - total_amount
shortfall = max(0.0, diff)

st.markdown("---")
st.markdown("### 📊 本趟計算結果")
res_col1, res_col2, res_col3 = st.columns(3)

with res_col1:
    st.metric(label="平台實際總給予", value=f"${total_amount:.2f}")
with res_col2:
    st.metric(label="專法獨立總門檻", value=f"${threshold:.2f}")
with res_col3:
    st.metric(label="總需補足金額", value=f"${shortfall:.2f}", delta=f"-${shortfall:.2f}" if shortfall > 0 else "已達標")

if st.button("📥 將此趟記錄到歷史", type="primary"):
    new_record = {
        "時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "單數": f"{len(st.session_state.current_batch)} 張單",
        "總金額": total_amount,
        "總時間(分)": total_duration,
        "獨立門檻": threshold,
        "補足金額": shortfall
    }
    st.session_state.records.append(new_record)
    st.success("✅ 行程記錄已成功累積！")
    st.session_state.current_batch = [{"amount": 50.0, "duration": 15.0}]
    st.rerun()

if st.session_state.records:
    st.markdown("### 📋 歷史記錄")
    df = pd.DataFrame(st.session_state.records)
    st.dataframe(df, use_container_width=True)
    
    total_shortfall = df["補足金額"].sum()
    st.info(f"💰 累計總需補足金額：**${total_shortfall:.2f}**")
