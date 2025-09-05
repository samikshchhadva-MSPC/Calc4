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

# ---------------- Policyholder inputs on top ----------------
st.subheader("Policy / Input Parameters")

# First row of inputs
col1, col2, col3 = st.columns(3)
with col1:
    age = st.number_input("Age of Life Assured", min_value=0, max_value=100, value=30)
with col2:
    gender = st.selectbox("Gender", ["Male", "Female"])
with col3:
    annual_premium = st.number_input("Annual Premium (₹)", min_value=10000, value=100000, step=1000)

# Second row of inputs
col4, col5 = st.columns(2)
with col4:
    policy_term = st.number_input("Policy Term (years)", min_value=10, max_value=40, value=20)
with col5:
    ppt = st.number_input("Premium Paying Term (years)", min_value=5, max_value=40, value=20)

# ---------------- Button with session state ----------------
if "show_bi" not in st.session_state:
    st.session_state.show_bi = False

if st.button("Generate BI"):
    st.session_state.show_bi = True

# ---------------- Show BI only if button clicked ----------------
if st.session_state.show_bi:
    # --------- Show Policyholder Details ---------
    st.subheader("Policyholder Details")
    st.write(f"""
    - **Age of Life Assured:** {age} years  
    - **Gender:** {gender}  
    - **Annual Premium:** ₹{annual_premium:,.0f}  
    - **Policy Term:** {policy_term} years  
    - **Premium Paying Term:** {ppt} years  
    """)

    # --------- Simplified BI Calculation ---------
    years = list(range(1, policy_term + 1))
    premiums, net_invested, fund_4, fund_8 = [], [], [], []
    fund_val_4, fund_val_8 = 0, 0

    for year in years:
        premium = annual_premium if year <= ppt else 0
        charge = 0.05 * premium if year <= 5 else 0  # 5% charge first 5 years
        invest = premium - charge
        fund_val_4 = (fund_val_4 + invest) * 1.04
        fund_val_8 = (fund_val_8 + invest) * 1.08

        premiums.append(premium)
        net_invested.append(invest)
        fund_4.append(round(fund_val_4, 2))
        fund_8.append(round(fund_val_8, 2))

    df = pd.DataFrame({
        "Policy Year": years,
        "Premium Paid (₹)": premiums,
        "Net Invested (₹)": net_invested,
        "Fund Value @4% (₹)": fund_4,
        "Fund Value @8% (₹)": fund_8
    })

    # --------- Display BI Table ---------
    st.subheader("Benefit Illustration Table (Simplified)")
    st.markdown("Values are shown at two assumed rates of return (4% and 8%) as per IRDAI guidelines.")

    st.dataframe(
        df.style.format("{:,.2f}")
        .set_table_styles([{'selector': 'th', 'props': [('background-color', '#f0f0f0'), ('font-weight', 'bold')]}])
    )

    # --------- Summary ---------
    st.subheader("Summary at Maturity")
    st.write(f"""
    - **Total Premiums Paid:** ₹{sum(premiums):,.0f}  
    - **Fund Value @4% (Maturity):** ₹{fund_4[-1]:,.0f}  
    - **Fund Value @8% (Maturity):** ₹{fund_8[-1]:,.0f}  
    """)

    # --------- Disclaimers ---------
    st.markdown("""
    ---
    ### Important Notes:
    - This is a **demo BI** created for educational purposes, not an official illustration.  
    - Returns shown at **4% and 8%** are not guaranteed and are as per IRDAI prescribed assumptions.  
    - Actual fund values depend on chosen fund performance, charges, mortality, and applicable taxes.  
    - For the official Benefit Illustration, please generate it from [bi.edelweisslife.in](https://bi.edelweisslife.in).  
    """)
else:
    st.info("👉 Please fill the Policy / Input Parameters above and click **Generate BI** to see the illustration.")
