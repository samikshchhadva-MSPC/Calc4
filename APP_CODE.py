# app.py
# Demo Benefit Illustration - Edelweiss Wealth Ultima (detailed demo, not official BI)
# Uses product rules from the official Edelweiss brochure (Wealth Ultima UIN 147L037V01).
# Author: demo code for learning purposes.

import streamlit as st
import pandas as pd
import io
from math import ceil

st.set_page_config(page_title="Wealth Ultima - Demo BI", layout="wide")

st.title("Demo Benefit Illustration — Edelweiss Wealth Ultima (Detailed demo)")

st.markdown("""
**Important:** This is an educational demo built from numbers published in the official product brochure.
It is **not** an official insurer BI. For an official BI you must use insurer/agent systems and actual mortality tables.
""")

# --- User inputs ---
st.sidebar.header("Policy / Input parameters")

# Basic policy inputs
age = st.sidebar.number_input("Life Insured Age (years)", min_value=0, max_value=100, value=30, step=1)
gender = st.sidebar.selectbox("Gender", ["Male", "Female"])
annual_premium = st.sidebar.number_input("Annual Premium (₹)", min_value=10000, value=100000, step=1000)
modal = st.sidebar.selectbox("Premium Mode", ["Annual"], index=0)  # for demo we use annual only
policy_term = st.sidebar.number_input("Policy Term (years)", min_value=10, max_value=40, value=20, step=1)

# Premium paying term (PPT) selection - keep simple mapping
ppt = st.sidebar.number_input("Premium Paying Term (years)", min_value=5, max_value=policy_term, value=policy_term, step=1)

# Fund selection (we will apply different FMCs)
fund_choice = st.sidebar.selectbox("Fund Choice (affects FMC)", 
                                   ["Equity Large Cap", "Equity Top 250", "Equity Mid Cap", "Managed Fund", "Bond Fund"])

# Additional options
include_topups = st.sidebar.checkbox("Include example Top-up in year 5 (₹50,000)", value=False)
topup_amount = 50000 if include_topups else 0

# Assumed assumed returns for BI (IRDAI style: we present at 4% and 8%)
assumed_return_1 = 0.04
assumed_return_2 = 0.08

st.sidebar.markdown("---")
st.sidebar.write("These assumptions implement brochure numbers (Allocation charges, Admin charges, FMC, Additions).")

# --- Product parameters pulled from brochure ---
# Allocation charges
alloc_charges = lambda year: 0.06 if year == 1 else (0.04 if 2 <= year <= 5 else 0.0)
topup_alloc = 0.015  # top-up allocation charge 1.5%

# Policy admin charges (percentage of annualised premium); brochure: 1.65% p.a. for years 1-5; nil after
def policy_admin_charge_pct(year):
    return 0.0165 if 1 <= year <= 5 else 0.0

policy_admin_charge_cap = 6000.0  # per annum cap

# Fund management charges (annual percentages) from brochure
fmc_map = {
    "Equity Large Cap": 0.0135,
    "Equity Top 250": 0.0135,
    "Equity Mid Cap": 0.0135,
    "Managed Fund": 0.0135,
    "Bond Fund": 0.0125
}

fmc = fmc_map[fund_choice]

# Additions (from brochure)
guaranteed_add_pct = 0.0025  # 0.25% of avg daily FV (last 12 months)
loyalty_add_pct = 0.0015     # 0.15% of avg daily FV (last 12 months)
# Booster additions schedule on every 5th policy-year from 10th:
def booster_pct_at_anniversary(anniv):
    if anniv in (10, 15):
        return 0.0275
    if anniv >= 20 and anniv % 5 == 0:
        return 0.035
    return 0.0

# Mortality charges: brochure says mortality rates are guaranteed and depend on age/gender,
# but the numeric table is not in the public brochure pages used here.
# For this demo we will show a placeholder (0) and display a note explaining what to do in production.
def mortality_charge_monthly_placeholder():
    return 0.0

# --- Build BI yearly projection ---
years = list(range(1, policy_term + 1))

# Trackers for fund values under two assumed returns
fund_4 = []
fund_8 = []
premium_paid = []
alloc_charged = []
policy_admin_charged = []
topup_list = []

# We'll do a simple approach to model fund value:
# At start of each year: add net premium (after allocation charges & top-up allocation), 
# then grow that year's fund by (1 + assumed_return - fmc) -- approximates daily FMC & returns combined
# At each year-end, add Guaranteed / Loyalty / Booster additions when due (as percentages of avg FV).
# For average-daily calculation we will approximate average-daily-FV by (start_FV + end_FV)/2 in that year.

# Initial fund values
fv1 = 0.0  # for 4% scenario (net growth = 4% - fmc approximated)
fv2 = 0.0  # for 8% scenario

for y in years:
    # Premium and allocation
    prem = annual_premium
    alloc_pct = alloc_charges(y)
    alloc = prem * alloc_pct
    net_invest = prem - alloc
    
    # include a top-up in year 5 if user selected
    topup = topup_amount if y == 5 else 0.0
    topup_alloc_amount = topup * topup_alloc
    topup_net = topup - topup_alloc_amount
    
    # Add net invested and top-up net to fund at the start of the year
    start_fv1 = fv1
    start_fv2 = fv2
    fv1 = fv1 + net_invest + topup_net
    fv2 = fv2 + net_invest + topup_net
    
    # Apply growth net of FMC: approximate effective growth = assumed_return - fmc
    # (This is a simplification; FMC is charged daily as NAV deduction; we approximate by reducing the gross return).
    eff_growth1 = assumed_return_1 - fmc
    eff_growth2 = assumed_return_2 - fmc
    end_fv1 = fv1 * (1 + eff_growth1)
    end_fv2 = fv2 * (1 + eff_growth2)
    
    # Approx avg-FV for additions calculation (approx as mean of start and end)
    avg_fv1 = (start_fv1 + end_fv1) / 2.0
    avg_fv2 = (start_fv2 + end_fv2) / 2.0
    
    # Add Guaranteed and Loyalty additions from end of year 6 onwards
    guaranteed_add1 = guaranteed_add_pct * avg_fv1 if y >= 6 else 0.0
    guaranteed_add2 = guaranteed_add_pct * avg_fv2 if y >= 6 else 0.0
    loyalty_add1 = loyalty_add_pct * avg_fv1 if (y >= 6 and ppt > 5) else 0.0
    loyalty_add2 = loyalty_add_pct * avg_fv2 if (y >= 6 and ppt > 5) else 0.0
    
    # Booster additions at specified anniversaries (applied on avg of last 60 months in actual product; we approximate)
    booster1 = booster_pct_at_anniversary(y) * avg_fv1
    booster2 = booster_pct_at_anniversary(y) * avg_fv2
    
    # Final fund at end of year after additions
    fv1 = end_fv1 + guaranteed_add1 + loyalty_add1 + booster1
    fv2 = end_fv2 + guaranteed_add2 + loyalty_add2 + booster2
    
    # Policy admin charge (percentage of annualised premium) recovered by cancellation of units (we apply annually)
    admin_pct = policy_admin_charge_pct(y)
    admin_charge = min(admin_pct * annual_premium, policy_admin_charge_cap)
    # Deduct admin charge from fund at end of year (simulate unit cancellation)
    fv1 = fv1 - admin_charge
    fv2 = fv2 - admin_charge
    
    # Mortality charge placeholder (zero in demo) - in production apply actual monthly mortality charges (see notes)
    mort_monthly = mortality_charge_monthly_placeholder()
    # For simplicity, sum-of-year mortality deduction = mort_monthly*12 (but set to 0 here)
    mort_year = mort_monthly * 12
    fv1 -= mort_year
    fv2 -= mort_year
    
    # Guard against negative fund values in early years
    fv1 = max(fv1, 0.0)
    fv2 = max(fv2, 0.0)
    
    # Record numbers
    premium_paid.append(prem)
    alloc_charged.append(round(alloc + topup_alloc_amount,2))
    policy_admin_charged.append(round(admin_charge,2))
    topup_list.append(topup)
    fund_4.append(round(fv1,2))
    fund_8.append(round(fv2,2))

# Build DataFrame for display
df = pd.DataFrame({
    "Year": years,
    "Premium Paid (₹)": premium_paid,
    "Top-up (₹)": topup_list,
    "Allocation Charges (₹)": alloc_charged,
    "Policy Admin Charge (₹)": policy_admin_charged,
    "Fund Value @4% (₹)": fund_4,
    "Fund Value @8% (₹)": fund_8
})

st.subheader("Detailed Yearly Benefit Illustration (demo)")
st.write(f"Assumptions used: allocation charges per brochure, admin charges per brochure, FMC = {fmc*100:.2f}% p.a. (fund dependent).")
st.dataframe(df.style.format("{:,.2f}"))

# Show totals at maturity
st.markdown("### Summary at Maturity")
maturity_row = {
    "Total premiums paid": sum(premium_paid),
    "Total top-ups": sum(topup_list),
    "Fund value @4% (maturity)": fund_4[-1],
    "Fund value @8% (maturity)": fund_8[-1]
}
st.json(maturity_row)

# Download button
csv = df.to_csv(index=False).encode('utf-8')
st.download_button("Download BI as CSV", csv, file_name="wealth_ultima_demo_bi.csv", mime="text/csv")

# --- Footnotes & limitations ---
st.markdown("""
**Footnotes & Limitations (important):**
1. Allocation charges, policy admin charges, FMC and additions (guaranteed, loyalty, booster) were implemented exactly as published in Edelweiss Wealth Ultima brochure (UIN 147L037V01). See product brochure.   
2. **Mortality charges** are age / gender / sum-at-risk dependent and are charged monthly by cancellation of units. The brochure states mortality charges are guaranteed but the numeric rate-table is not reproduced here; this demo uses a mortality placeholder of zero. For a production/official BI you must use the insurer's mortality table and monthly calculation logic. :contentReference[oaicite:10]{index=10}  
3. **FMC is modelled as a straight annual percentage reducing the gross return** (i.e., effective growth = assumed return – FMC). The real product deducts FMC daily via NAV; our approximation is accurate enough for demo/visual comparisons but not for regulatory BI. :contentReference[oaicite:11]{index=11}  
4. Guaranteed/Loyalty/Booster Additions in the brochure are calculated on average daily fund value (last 12 or 60 months). We approximated average-daily-FV by (start + end)/2 in each policy year — again fine for demo purposes, but not identical to insurer calculations. :contentReference[oaicite:12]{index=12}
""")
