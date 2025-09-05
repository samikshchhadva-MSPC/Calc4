import streamlit as st
import pandas as pd

st.set_page_config(page_title="Wealth Ultima - Demo BI", layout="wide")

# ---------------- Header ----------------
st.markdown("""
# Edelweiss Tokio Life Insurance Company Limited  
### Wealth Ultima (UIN: 147L037V01)  
**Benefit Illustration (Demo – Not an official BI)**
---
""")

# ---------------- Inputs ----------------
st.subheader("Policy / Input Parameters")

col1, col2, col3 = st.columns(3)
with col1:
    age = st.number_input("Age of Life Assured", min_value=0, max_value=100, value=30)
with col2:
    gender = st.selectbox("Gender", ["Male", "Female"])
with col3:
    annual_premium = st.number_input("Annual Premium (₹)", min_value=10000, value=100000, step=1000)

col4, col5 = st.columns(2)
with col4:
    policy_term = st.number_input("Policy Term (years)", min_value=10, max_value=40, value=20)
with col5:
    ppt = st.number_input("Premium Paying Term (years)", min_value=5, max_value=40, value=20)

if "show_bi" not in st.session_state:
    st.session_state.show_bi = False

if st.button("Generate BI"):
    st.session_state.show_bi = True

# ---------------- BI Generation ----------------
if st.session_state.show_bi:
    st.subheader("Policyholder Details")
    st.write(f"""
    - **Age of Life Assured:** {age} years  
    - **Gender:** {gender}  
    - **Annual Premium:** ₹{annual_premium:,.0f}  
    - **Policy Term:** {policy_term} years  
    - **Premium Paying Term:** {ppt} years  
    """)

    # Placeholder simple calculations for demo
    years = list(range(1, policy_term + 1))
    data = []
    fund_4, fund_8 = 0, 0

    for yr in years:
        prem = annual_premium if yr <= ppt else 0
        mort_chg = 0.02 * prem   # dummy mortality charge = 2% of premium
        other_chg = 0.03 * prem  # dummy other charge = 3% of premium
        gst = 0.18 * (mort_chg + other_chg)  # GST 18% on charges

        invest_amt = prem - (mort_chg + other_chg + gst)
        fund_4 = (fund_4 + invest_amt) * 1.04
        fund_8 = (fund_8 + invest_amt) * 1.08

        surrender_4 = fund_4 * 0.75  # assume 75% surrender
        surrender_8 = fund_8 * 0.75
        death_ben_4 = max(fund_4, prem * 10)  # dummy min sum assured
        death_ben_8 = max(fund_8, prem * 10)

        data.append([
            yr, prem,
            mort_chg, other_chg, gst, round(fund_4,2), round(surrender_4,2), round(death_ben_4,2),
            mort_chg, other_chg, gst, round(fund_8,2), round(surrender_8,2), round(death_ben_8,2)
        ])

    # Create DataFrame with 14 columns
    df = pd.DataFrame(data, columns=[
        "Policy Year", "Annualized Premium",
        "Mortality, Morbidity Charges (4%)", "Other Charges* (4%)", "GST (4%)",
        "Fund @4% End of Year", "Surrender Value (4%)", "Death Benefit (4%)",
        "Mortality, Morbidity Charges (8%)", "Other Charges* (8%)", "GST (8%)",
        "Fund @8% End of Year", "Surrender Value (8%)", "Death Benefit (8%)"
    ])

    # ---------------- Display Table ----------------
    st.subheader("Benefit Illustration Table (Simplified 14-column)")
    st.dataframe(
        df.style.format("{:,.2f}")
    )

    # ---------------- Disclaimer ----------------
    st.markdown("""
    ---
    ### Important Notes:
    - This is a **demo BI** created for educational purposes, not an official illustration.  
    - All charges, returns, and benefits shown here are dummy assumptions.  
    - For the official Benefit Illustration, please generate it from [bi.edelweisslife.in](https://bi.edelweisslife.in).  
    """)
else:
    st.info("👉 Please fill the Policy / Input Parameters above and click **Generate BI** to see the illustration.")
