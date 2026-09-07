import streamlit as st
import pandas as pd
from datetime import datetime

# 嘗試載入更輕量快速的 pytesseract 或保留 google.generativeai 影像理解來達到秒讀與精準度
try:
    import google.generativeai as genai
    from PIL import Image
    AI_AVAILABLE = True
except Exception:
    AI_AVAILABLE = False

st.set_page_config(
    page_title="外送專法 獨立單單計價補足金額追蹤器",
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
    
    # 這裡利用 Streamlit Secrets 中的 API Key 進行精準 Gemini 影像辨識金額與時間
    if AI_AVAILABLE and "GEMINI_API_KEY" in st.secrets:
        with st.spinner("⚡ AI 正在精準解析截圖中的金額與時間..."):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                # 使用輕量快速的 flash 模型進行視覺解析
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content([
                    image, 
                    "請從這張外送截圖中萃取出兩個數字：1. 金額（數字即可，例如 49） 2. 時間（分鐘，數字即可，例如 13）。請嚴格依照格式回傳 JSON：{\"amount\": 數字, \"duration\": 數字}"
                ])
                import json
                # 清理文字抓取 JSON
                text_res = response.text.strip()
                if "```json" in text_res:
                    text_res = text_res.split("```json")[1].split("```")[0].strip()
                elif "```" in text_res:
                    text_res = text_res.split("```")[1].split("```")[0].strip()
                
                data = json.loads(text_res)
                parsed_amt = float(data.get("amount", 49.0))
                parsed_dur = float(data.get("duration", 13.0))
                
                # 自動更新到當前清單的第一張單
                st.session_state.current_batch[0]["amount"] = parsed_amt
                st.session_state.current_batch[0]["duration"] = parsed_dur
                st.success(f"✅ 成功辨識！金額：${parsed_amt}，時間：{parsed_dur} 分鐘")
            except Exception as e:
                st.warning("⚠️ 自動解析失敗，請直接從下方欄位確認或手動調整。")

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
```[cite: 1]
