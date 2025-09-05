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

col4, col5, col6 = st.columns(3)
with col4:
    policy_term = st.number_input("Policy Term (years)", min_value=10, max_value=40, value=20)
with col5:
    ppt = st.number_input("Premium Paying Term (years)", min_value=5, max_value=40, value=20)
with col6:
    sum_assured = st.number_input("Sum Assured (₹)", min_value=100000, step=50000, value=1000000)

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
    - **Sum Assured:** ₹{sum_assured:,.0f}  
    """)

    # Placeholder monthly calculation loop
    years = list(range(1, policy_term + 1))
    data_bi, data_charges = [], []
    fund_4, fund_8 = 0, 0

    for yr in years:
        prem = annual_premium if yr <= ppt else 0

        # Charges
        pac = 0
        if yr == 1:
            pac = 0.06 * prem
        elif yr <= 5:
            pac = 0.04 * prem
        policy_admin = 0.0165 * prem if yr <= 5 else 0
        other_chg = pac + policy_admin

        mort_chg_4 = 0.001 * max(sum_assured - fund_4, 0)
        mort_chg_8 = 0.001 * max(sum_assured - fund_8, 0)

        gst_4 = 0.18 * (mort_chg_4 + other_chg)
        gst_8 = 0.18 * (mort_chg_8 + other_chg)

        # Monthly growth
        invest_4 = prem - (other_chg + mort_chg_4 + gst_4)
        invest_8 = prem - (other_chg + mort_chg_8 + gst_8)

        fund_4 = (fund_4 + invest_4) * ((1 + 0.04) ** (1/12)) ** 12
        fund_8 = (fund_8 + invest_8) * ((1 + 0.08) ** (1/12)) ** 12

        # Additions (placeholders for now, we’ll refine later)
        guaranteed_add = 0
        loyalty_add = 0
        booster_add = 0
        if yr >= 6:
            guaranteed_add = 0.0025 * fund_4  # just approx
            loyalty_add = 0.0015 * fund_4 if ppt > 5 else 0
        if yr % 5 == 0 and yr >= 10:
            booster_add = 0.0275 * fund_4

        fund_4 += guaranteed_add + loyalty_add + booster_add
        fund_8 += guaranteed_add + loyalty_add + booster_add

        # Benefits
        surrender_4 = fund_4
        surrender_8 = fund_8
        death_ben_4 = max(surrender_4, sum_assured)
        death_ben_8 = max(surrender_8, sum_assured)

        # Table 1: Charges & Additions
        data_charges.append([
            yr, prem, pac, prem - pac, mort_chg_4, gst_4, policy_admin, other_chg,
            guaranteed_add, loyalty_add, booster_add
        ])

        # Table 2: Main BI Table (14 cols)
        data_bi.append([
            yr, prem,
            mort_chg_4, other_chg, gst_4, round(fund_4, 2), round(surrender_4, 2), round(death_ben_4, 2),
            mort_chg_8, other_chg, gst_8, round(fund_8, 2), round(surrender_8, 2), round(death_ben_8, 2)
        ])

    # Charges & Additions Table
    df_charges = pd.DataFrame(data_charges, columns=[
        "Policy Year", "Annualized Premium (AP)", "Premium Allocation Charge (PAC)",
        "Annualized Premium - PAC", "Mortality Charge", "GST",
        "Policy Admin. Charge", "Other Charges*", "Guaranteed Addition",
        "Loyalty Addition", "Booster Addition"
    ])

    st.subheader("Table 1: Charges & Additions")
    st.dataframe(df_charges.style.format("{:,.2f}"))

    # BI Table (existing one)
    df_bi = pd.DataFrame(data_bi, columns=[
        "Policy Year", "Annualized Premium",
        "Mortality, Morbidity Charges (4%)", "Other Charges* (4%)", "GST (4%)",
        "Fund @4% End of Year", "Surrender Value (4%)", "Death Benefit (4%)",
        "Mortality, Morbidity Charges (8%)", "Other Charges* (8%)", "GST (8%)",
        "Fund @8% End of Year", "Surrender Value (8%)", "Death Benefit (8%)"
    ])

    st.subheader("Table 2: Benefit Illustration (Simplified)")
    st.dataframe(df_bi.style.format("{:,.2f}"))

    # Download CSV (main BI)
    csv = df_bi.to_csv(index=False).encode("utf-8")
    st.download_button("Download BI as CSV", data=csv, file_name="demo_bi.csv", mime="text/csv")

    st.markdown("""
    ---
    ### Important Notes:
    - This is a **demo BI** created for educational purposes, not an official illustration.  
    - All charges, returns, and benefits shown here are **dummy assumptions** for demo.  
    - For the official Benefit Illustration, please generate it from [bi.edelweisslife.in](https://bi.edelweisslife.in).  
    """)
else:
    st.info("👉 Please fill the Policy / Input Parameters above and click **Generate BI** to see the illustration.")
