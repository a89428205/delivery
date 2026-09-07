import streamlit as st
import pandas as pd
from datetime import datetime

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
    <p style="color: #94a3b8; font-size: 14px; margin-top: 4px;">極速多單/夾單專用計算器 • 支援無限疊單快速輸入</p>
</div>
""", unsafe_allow_html=True)

if 'records' not in st.session_state:
    st.session_state.records = []

# 初始化當前這趟的多單列表
if 'current_batch' not in st.session_state:
    st.session_state.current_batch = [
        {"amount": 227.0, "duration": 29.0},
        {"amount": 101.0, "duration": 25.0}
    ]

st.markdown("### 📦 本趟行程明細（支援多張夾單/疊單）")

# 動態調整夾單數量
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
            if st.button("🗑️", key=f"del_{i}__"):
                st.session_state.current_batch.pop(i)
                st.rerun()

if st.button("➕ 增加一張夾單/疊單"):
    st.session_state.current_batch.append({"amount": 80.0, "duration": 10.0})
    st.rerun()

# 計算總金額與總時間
total_amount = sum([item["amount"] for item in st.session_state.current_batch])
total_duration = sum([item["duration"] for item in st.session_state.current_batch])

# 專法獨立門檻 (每分鐘 4.1 元，最低 45 元)
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

if st.button("📥 將此趟（含所有夾單）記錄到歷史", type="primary"):
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

if st.session_state.records:
    st.markdown("### 📋 歷史記錄")
    df = pd.DataFrame(st.session_state.records)
    st.dataframe(df, use_container_width=True)
    
    total_shortfall = df["補足金額"].sum()
    st.info(f"💰 累計總需補足金額：**${total_shortfall:.2f}**")
