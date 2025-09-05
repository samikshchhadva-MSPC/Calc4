import streamlit as st
import pandas as pd

st.title("Demo Benefit Illustration - Wealth Ultima (Simplified)")

# User inputs
annual_premium = st.number_input("Enter Annual Premium (₹)", value=50000, step=1000)
policy_term = st.number_input("Enter Policy Term (years)", value=10, step=1)

if st.button("Generate BI"):
    years = list(range(1, policy_term + 1))
    premiums = []
    net_invested = []
    fund_4 = []
    fund_8 = []

    fund_val_4 = 0
    fund_val_8 = 0

    for year in years:
        premium = annual_premium
        charge = 0.05 * premium  # 5% charges
        invest = premium - charge

        # Add invested amount to fund
        fund_val_4 = (fund_val_4 + invest) * 1.04
        fund_val_8 = (fund_val_8 + invest) * 1.08

        premiums.append(premium)
        net_invested.append(invest)
        fund_4.append(round(fund_val_4, 2))
        fund_8.append(round(fund_val_8, 2))

    # Create dataframe
    df = pd.DataFrame({
        "Year": years,
        "Premium Paid": premiums,
        "Net Invested": net_invested,
        "Fund Value @4%": fund_4,
        "Fund Value @8%": fund_8
    })

    st.subheader("Benefit Illustration Table")
    st.dataframe(df)

    # Allow download as CSV
    csv = df.to_csv(index=False)
    st.download_button("Download BI as CSV", csv, "demo_bi.csv", "text/csv")
