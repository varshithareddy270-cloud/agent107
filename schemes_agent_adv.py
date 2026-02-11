import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from openai import OpenAI

# =================================================
# APP CONFIG
# =================================================
st.set_page_config(
    page_title="Government Scheme Intelligence Dashboard",
    layout="wide"
)

st.title("🏛️ Government Scheme Intelligence Dashboard")
st.caption(
    "Rule-based analytics with AI-assisted review notes. "
    "All decisions remain with officers."
)

# =================================================
# API KEY CHECK
# =================================================
if "OPENAI_API_KEY" not in st.secrets:
    st.error("OpenAI API key not found. Please configure Streamlit Secrets.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# =================================================
# SYSTEM PROMPT (LOCKED)
# =================================================
SYSTEM_PROMPT = """
ROLE:
You are a Government Scheme Performance Review Assistant.

RULES:
1. Use formal Government language suitable for official review meetings.
2. Base analysis strictly on the provided numerical data and computed indicators.
3. Do not invent causes, explanations, or policy recommendations unless explicitly asked.
4. Highlight key risks, average performers, and good performers objectively.
5. If information is insufficient, clearly state so.
6. Continue responses fully if analysis is long.

OUTPUT:
- Structured bullet points
- Clear headings
- Review-meeting ready language
"""

# =================================================
# FILE UPLOAD
# =================================================
uploaded_file = st.file_uploader(
    "📤 Upload Scheme Performance Excel File (.xlsx)",
    type=["xlsx"]
)

if not uploaded_file:
    st.info("Please upload an Excel file to proceed.")
    st.stop()

# =================================================
# READ DATA
# =================================================
try:
    df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error("Error reading Excel file.")
    st.exception(e)
    st.stop()

st.subheader("📄 Data Preview")
st.dataframe(df, use_container_width=True)

# =================================================
# FILTERS
# =================================================
st.subheader("🔎 Filters")

districts = ["All"] + sorted(df["District"].dropna().unique().tolist())
selected_district = st.selectbox("Select District", districts)

if selected_district != "All":
    df_filtered = df[df["District"] == selected_district].copy()
else:
    df_filtered = df.copy()

# =================================================
# RULE-BASED RISK LOGIC
# =================================================
def risk_level(util):
    if util < 65:
        return "High Risk"
    elif util < 80:
        return "Medium Risk"
    else:
        return "On Track"

df_filtered["Risk Level"] = df_filtered["% Utilisation"].apply(risk_level)

# =================================================
# KPI DASHBOARD
# =================================================
st.subheader("📌 Key Performance Indicators")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total Allocation (₹ Cr)",
    round(df_filtered["Allocated Budget (₹ Crores)"].sum(), 2)
)

col2.metric(
    "Total Utilisation (₹ Cr)",
    round(df_filtered["Utilised Budget (₹ Crores)"].sum(), 2)
)

col3.metric(
    "Average Utilisation (%)",
    round(df_filtered["% Utilisation"].mean(), 2)
)

col4.metric(
    "High Risk Schemes",
    (df_filtered["Risk Level"] == "High Risk").sum()
)

# =================================================
# DASHBOARDS
# =================================================
st.subheader("📊 Dashboards")

colA, colB = st.columns(2)

# ---- Bar Chart
with colA:
    st.markdown("**Utilisation (%) by Scheme**")
    st.bar_chart(
        df_filtered.set_index("Scheme Name")["% Utilisation"]
    )

# ---- Pie Chart (Matplotlib – Stable)
with colB:
    st.markdown("**Scheme Status Distribution**")
    status_counts = df_filtered["Status"].value_counts()

    fig, ax = plt.subplots()
    ax.pie(
        status_counts.values,
        labels=status_counts.index,
        autopct="%1.1f%%",
        startangle=90
    )
    ax.axis("equal")
    st.pyplot(fig)

# ---- Central vs State
st.subheader("🏛️ Central vs State Scheme Performance")

comparison = (
    df_filtered
    .groupby("Scheme Type (Central/State)")["% Utilisation"]
    .mean()
)

st.bar_chart(comparison)

# =================================================
# RISK TABLE
# =================================================
st.subheader("🚦 Risk Classification Table")

st.dataframe(
    df_filtered[
        [
            "District",
            "Scheme Name",
            "Scheme Type (Central/State)",
            "% Utilisation",
            "Status",
            "Risk Level"
        ]
    ],
    use_container_width=True
)

# =================================================
# AI REVIEW NOTE
# =================================================
st.subheader("🧠 AI-Assisted Review Note")

ai_query = st.text_input(
    "Optional instruction (or leave default)",
    value="Prepare a concise review note highlighting key risks, average performers, and good performers."
)

if st.button("Generate AI Review Note"):
    with st.spinner("Drafting review note..."):
        try:
            data_text = df_filtered.to_string(index=False)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.2,
                max_tokens=1800,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"SCHEME DATA:\n{data_text}"},
                    {"role": "user", "content": ai_query}
                ]
            )

            output_text = response.choices[0].message.content

            st.text_area(
                "AI Draft Review Output (Scrollable)",
                output_text,
                height=450
            )

        except Exception as e:
            st.error("AI service error. Please retry.")
            st.exception(e)

# =================================================
# GOVERNANCE FOOTER
# =================================================
st.markdown(
    """
    ---
    **Governance Disclaimer:**  
    This dashboard provides analytical support and AI-assisted drafting only.  
    All interpretations, decisions, and approvals rest solely with the concerned officers.
    """
)
