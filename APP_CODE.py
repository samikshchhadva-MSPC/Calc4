# app.py
# Streamlit Demo: Wealth Ultima - detailed BI (monthly model) with PDF download
# NOTE: For PDF download this uses reportlab. If reportlab is not installed in your deploy,
# add 'reportlab' to requirements.txt or use CSV download (available by default).

import streamlit as st
import pandas as pd
import io
from math import pow
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Wealth Ultima - Demo BI (Monthly Model)", layout="wide")

st.title("Edelweiss Tokio Life — Wealth Ultima (Demo BI)")

# ---------------- Inputs (top) ----------------
st.subheader("Policy / Input Parameters")

col1, col2, col3 = st.columns(3)
with col1:
    age = st.number_input("Age of Life Assured", min_value=0, max_value=100, value=30)
with col2:
    gender = st.selectbox("Gender", ["Male", "Female"])
with col3:
    annual_premium = st.number_input("Annual Premium (₹)", min_value=10000, value=100000, step=1000)

col4, col5, col6 = st.columns([1,1,1])
with col4:
    sum_assured = st.number_input("Sum Assured (₹)", min_value=0, value=int(annual_premium*10), step=1000)
with col5:
    policy_term = st.number_input("Policy Term (years)", min_value=10, max_value=40, value=20)
with col6:
    ppt = st.number_input("Premium Paying Term (years)", min_value=5, max_value=40, value=policy_term)

# Fund management charge (FMC) selection (affects net growth)
f1, f2 = st.columns(2)
with f1:
    fund_choice = st.selectbox("Fund Choice (affects FMC)", ["Equity Large Cap", "Bond Fund"])
with f2:
    # map to FMC
    FMC_map = {"Equity Large Cap": 0.0135, "Bond Fund": 0.0125}
    fmc = FMC_map[fund_choice]

# Assumed gross returns
r1 = 0.04
r2 = 0.08

st.markdown("**Notes:** This is a demo model. Mortality rates used here are derived from your rule (0.1% of SAR).")

# Button/Session state
if "show_bi" not in st.session_state:
    st.session_state.show_bi = False

if st.button("Generate BI"):
    st.session_state.show_bi = True

if not st.session_state.show_bi:
    st.info("Fill the inputs above and click Generate BI to produce the illustration.")
    st.stop()

# ---------------- Monthly model ----------------
# Time grid
total_months = int(policy_term * 12)
ppt_months = int(ppt * 12)

# Monthly rates
monthly_return_4 = pow(1 + r1, 1/12.0) - 1
monthly_return_8 = pow(1 + r2, 1/12.0) - 1
monthly_fmc = fmc / 12.0  # FMC charged monthly as fraction

# Prepare trackers per month and per year summary rows
months = list(range(1, total_months + 1))
fund_4_monthly = []
fund_8_monthly = []
premium_monthly = []  # premium receipts monthly (we treat premiums received yearly at month 1 of each policy year)
allocation_charges_monthly = []
admin_charges_monthly = []
mortality_charges_monthly = []
gst_monthly = []
other_charges_monthly = []
guaranteed_additions_monthly = []  # we will add at year-end months
loyalty_additions_monthly = []
booster_additions_monthly = []

# We'll keep the fund value evolving monthly.
fv4 = 0.0
fv8 = 0.0

# Helper to get year index from month (1-based)
def year_of_month(m):
    return (m - 1) // 12 + 1

# For calculating averages for last 12/60 months, keep track of end-of-month fund values
end_of_month_fv4 = []
end_of_month_fv8 = []

# Loop months
for m in months:
    yr = year_of_month(m)
    # Premium paid at the start of policy year => month m where (m-1)%12 == 0
    premium = 0.0
    if (m - 1) % 12 == 0 and yr <= ppt:
        premium = float(annual_premium)  # annual premium paid once per year at month 1 of that year

    # Allocation Charge (PAC) applies on premium received *when it's paid*
    if premium > 0:
        if yr == 1:
            pac_pct = 0.06
        elif 2 <= yr <= 5:
            pac_pct = 0.04
        else:
            pac_pct = 0.0
        pac_amount = premium * pac_pct
    else:
        pac_pct = 0.0
        pac_amount = 0.0

    # Policy admin charge: 1.65% of annual premium for first 5 years (apportioned monthly)
    if 1 <= yr <= 5:
        admin_annual = 0.0165 * annual_premium
    else:
        admin_annual = 0.0
    admin_monthly = admin_annual / 12.0

    # Other charges: here includes PAC (on months where premium received), plus admin monthly
    other_charges = pac_amount + admin_monthly

    # Mortality charge: defined as 0.1% of (death benefit less fund value)
    # Death benefit depends on fund at that time (we'll approximate using current fv before growth)
    # For monthly computation, compute provisional death benefit = max(fv (current), sum_assured)
    # SAR = death_benefit - fund_value
    # Annual mortality = 0.001 * SAR; monthly mortality = annual/12
    current_death_benefit = max(fv4, sum_assured)  # using fv4 as base; same for both scenarios for SAR calc
    sar = max(current_death_benefit - fv4, 0.0)
    annual_mortality = 0.001 * sar
    monthly_mortality = annual_mortality / 12.0

    # For consistency, compute mortality w.r.t fv8 similarly (small difference). We'll compute separate SARs below for each scenario.

    # GST = 18% on (mortality + other_charges) -> for monthly compute on monthly amounts
    # But mortality is monthly_mortality; other_charges in this month = pac_amount + admin_monthly
    gst = 0.18 * (monthly_mortality + other_charges)

    # Investable amount from premium in this month = premium - pac_amount - gst_on_charges - mortality? 
    # In many ULIPs: allocation charge is applied first, then units allocated; admin/mort/misc charges are recovered by canceling units later.
    # For this demo: we will allocate (premium - pac_amount) to fund at the start of month; admin/mort/gst will be deducted from fund monthly (via unit cancellation).
    allocated_units_amount = premium - pac_amount

    # Add allocated amount to funds (both scenarios)
    fv4 += allocated_units_amount
    fv8 += allocated_units_amount

    # Apply monthly growth net of FMC: effective monthly growth = monthly_return - monthly_fmc
    eff_growth_4 = monthly_return_4 - monthly_fmc
    eff_growth_8 = monthly_return_8 - monthly_fmc

    fv4 = fv4 * (1.0 + eff_growth_4)
    fv8 = fv8 * (1.0 + eff_growth_8)

    # Now deduct admin charge, monthly mortality and GST from fund by unit cancellation
    # For mortality, compute SAR based on updated fund after growth (use scenario-specific SAR)
    death_benefit_4 = max(fv4, sum_assured)
    sar4 = max(death_benefit_4 - fv4, 0.0)
    ann_mort4 = 0.001 * sar4
    mort_month4 = ann_mort4 / 12.0

    death_benefit_8 = max(fv8, sum_assured)
    sar8 = max(death_benefit_8 - fv8, 0.0)
    ann_mort8 = 0.001 * sar8
    mort_month8 = ann_mort8 / 12.0

    # For GST, follow rule: GST = 18% of (mortality + other charges)
    gst4 = 0.18 * (mort_month4 + other_charges)
    gst8 = 0.18 * (mort_month8 + other_charges)

    # Deduct charges from funds (we'll deduct average of two scenarios of other_charges? other_charges same for both)
    fv4 -= (admin_monthly + mort_month4 + gst4)
    fv8 -= (admin_monthly + mort_month8 + gst8)

    # Prevent negative
    fv4 = max(fv4, 0.0)
    fv8 = max(fv8, 0.0)

    # Save end of month fund values for average calculations
    end_of_month_fv4.append(fv4)
    end_of_month_fv8.append(fv8)

    # Track monthly breakdown for possible debugging / detailed table (we'll aggregate per year later)
    fund_4_monthly.append(fv4)
    fund_8_monthly.append(fv8)
    premium_monthly.append(premium)
    allocation_charges_monthly.append(pac_amount)
    admin_charges_monthly.append(admin_monthly)
    mortality_charges_monthly.append((mort_month4, mort_month8))
    gst_monthly.append((gst4, gst8))
    other_charges_monthly.append(other_charges)
    guaranteed_additions_monthly.append(0.0)
    loyalty_additions_monthly.append(0.0)
    booster_additions_monthly.append(0.0)

    # Check for year-end to apply additions (Guaranteed, Loyalty, Booster)
    if m % 12 == 0:
        policy_year = m // 12
        # Average daily fund over last 12 months -> approximate by average of end_of_month list last 12 values
        if len(end_of_month_fv4) >= 12:
            avg_last_12_fv4 = sum(end_of_month_fv4[-12:]) / 12.0
            avg_last_12_fv8 = sum(end_of_month_fv8[-12:]) / 12.0
        else:
            avg_last_12_fv4 = sum(end_of_month_fv4) / len(end_of_month_fv4)
            avg_last_12_fv8 = sum(end_of_month_fv8) / len(end_of_month_fv8)

        # Guaranteed additions apply from end of year 6 to maturity: 0.25% of avg last 12 months
        guar_add_4 = 0.0025 * avg_last_12_fv4 if policy_year >= 6 else 0.0
        guar_add_8 = 0.0025 * avg_last_12_fv8 if policy_year >= 6 else 0.0

        # Loyalty additions: 0.15% of avg last 12 months from end year 6 till end of PPT; no loyalty for PPT=5.
        if ppt == 5:
            loy_add_4 = 0.0
            loy_add_8 = 0.0
        else:
            loy_add_4 = 0.0015 * avg_last_12_fv4 if (policy_year >= 6 and policy_year <= ppt) else 0.0
            loy_add_8 = 0.0015 * avg_last_12_fv8 if (policy_year >= 6 and policy_year <= ppt) else 0.0

        # Booster additions: at every 5th policy year starting from end of 10th -> 2.75% of avg daily FV of last 60 months
        if policy_year >= 10 and policy_year % 5 == 0:
            # compute avg last 60 months (or available months)
            last_n = min(len(end_of_month_fv4), 60)
            avg_last_60_fv4 = sum(end_of_month_fv4[-last_n:]) / last_n if last_n > 0 else 0.0
            avg_last_60_fv8 = sum(end_of_month_fv8[-last_n:]) / last_n if last_n > 0 else 0.0
            booster_add_4 = 0.0275 * avg_last_60_fv4
            booster_add_8 = 0.0275 * avg_last_60_fv8
        else:
            booster_add_4 = 0.0
            booster_add_8 = 0.0

        # Add these additions to fund at year-end (i.e., current fv4/fv8)
        fv4 += guar_add_4 + loy_add_4 + booster_add_4
        fv8 += guar_add_8 + loy_add_8 + booster_add_8

        # record in arrays (on that month index)
        guaranteed_additions_monthly[-1] = guar_add_4  # store 4% addition here (for row aggregation we'll use per-year)
        loyalty_additions_monthly[-1] = loy_add_4
        booster_additions_monthly[-1] = booster_add_4

        # Update end-of-month lists after addition
        end_of_month_fv4[-1] = fv4
        end_of_month_fv8[-1] = fv8
        fund_4_monthly[-1] = fv4
        fund_8_monthly[-1] = fv8

# ---------------- Aggregate per Policy Year ----------------
rows = []
for y in range(1, policy_term + 1):
    start_month = (y - 1) * 12
    end_month = y * 12  # exclusive index for python slices is end_month
    # Sum premiums paid in that year
    annual_prem = sum(premium_monthly[start_month:end_month])
    # For charges, aggregate monthly sums
    pac_year = sum(allocation_charges_monthly[start_month:end_month])
    admin_year = sum(admin_charges_monthly[start_month:end_month])
    other_charges_year = pac_year + admin_year
    # Mortality year (annualize monthly mortalities we recorded per month for the two scenarios)
    mort_year_4 = sum(m[0] for m in mortality_charges_monthly[start_month:end_month]) if len(mortality_charges_monthly[start_month:end_month])>0 else 0.0
    mort_year_8 = sum(m[1] for m in mortality_charges_monthly[start_month:end_month]) if len(mortality_charges_monthly[start_month:end_month])>0 else 0.0
    # However we didn't fill mortality_charges_monthly with actual per-scenario values earlier (we set placeholders),
    # so instead recompute per-year annual mortality using final funds at year-end for consistency:
    fv4_end = end_of_month_fv4[end_month-1] if end_month-1 < len(end_of_month_fv4) else end_of_month_fv4[-1]
    fv8_end = end_of_month_fv8[end_month-1] if end_month-1 < len(end_of_month_fv8) else end_of_month_fv8[-1]
    death_benefit_4 = max(fv4_end, sum_assured)
    death_benefit_8 = max(fv8_end, sum_assured)
    sar4 = max(death_benefit_4 - fv4_end, 0.0)
    sar8 = max(death_benefit_8 - fv8_end, 0.0)
    mort_year_4 = 0.001 * sar4  # annual mortality charge
    mort_year_8 = 0.001 * sar8
    # GST on charges = 18% of (mortality + other charges) — apply GST yearly
    gst_year_4 = 0.18 * (mort_year_4 + other_charges_year)
    gst_year_8 = 0.18 * (mort_year_8 + other_charges_year)
    # Surrender value = fund value at year end (we already computed additions at year end)
    surrender_4 = fv4_end
    surrender_8 = fv8_end
    # Death benefit = max(surrender, sum assured)
    death_ben_4 = max(surrender_4, sum_assured)
    death_ben_8 = max(surrender_8, sum_assured)

    # For display/consistency, show "Gross Investment Return" column as the annualized % return assumed (4%/8%)
    gross_return_4 = r1 * 100
    gross_return_8 = r2 * 100

    # Other Charges column to include PAC + admin + (we'll not include FMC here as it's modeled via returns)
    # Note: fund management charges were applied via 'monthly_fmc' reducing returns.
    rows.append({
        "Policy Year": y,
        "Annualized Premium": annual_prem,
        # 4% block
        "At 4% p.a. Gross Investment Return (%)": gross_return_4,
        "Mortality, Morbidity Charges (4%)": round(mort_year_4,2),
        "Other Charges* (4%)": round(other_charges_year,2),
        "GST (4%)": round(gst_year_4,2),
        "Fund at End of Year (4%)": round(surrender_4,2),
        "Surrender Value (4%)": round(surrender_4,2),
        "Death Benefit (4%)": round(death_ben_4,2),
        # 8% block
        "At 8% p.a. Gross Investment Return (%)": gross_return_8,
        "Mortality, Morbidity Charges (8%)": round(mort_year_8,2),
        "Other Charges* (8%)": round(other_charges_year,2),
        "GST (8%)": round(gst_year_8,2),
        "Fund at End of Year (8%)": round(surrender_8,2),
        "Surrender Value (8%)": round(surrender_8,2),
        "Death Benefit (8%)": round(death_ben_8,2)
    })

df = pd.DataFrame(rows)

# Display policyholder details
st.subheader("Policyholder Details")
st.write(f"- Age: {age}  •  - Gender: {gender}  •  - Annual Premium: ₹{annual_premium:,.0f}  •  - Sum Assured: ₹{sum_assured:,.0f}")
st.write(f"- Policy Term: {policy_term} years  •  - PPT: {ppt} years  •  - Fund: {fund_choice}  •  - FMC: {fmc*100:.2f}% p.a.")

# ---------------- Display BI table ----------------
st.subheader("Benefit Illustration Table (Monthly model)")

# Use nicer column ordering for display
display_cols = [
    "Policy Year", "Annualized Premium",
    "At 4% p.a. Gross Investment Return (%)", "Mortality, Morbidity Charges (4%)", "Other Charges* (4%)", "GST (4%)",
    "Fund at End of Year (4%)", "Surrender Value (4%)", "Death Benefit (4%)",
    "At 8% p.a. Gross Investment Return (%)", "Mortality, Morbidity Charges (8%)", "Other Charges* (8%)", "GST (8%)",
    "Fund at End of Year (8%)", "Surrender Value (8%)", "Death Benefit (8%)"
]
st.dataframe(df[display_cols].style.format("{:,.2f}"), height=500)

# ---------------- Download CSV ----------------
csv = df[display_cols].to_csv(index=False).encode('utf-8')
st.download_button("Download BI as CSV", csv, "wealth_ultima_demo_bi.csv", "text/csv")

# ---------------- Generate PDF (reportlab) and download ----------------
def make_pdf(dataframe: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 30
    x = margin
    y = height - margin
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Edelweiss Tokio Life Insurance Company Limited")
    y -= 16
    c.setFont("Helvetica", 10)
    c.drawString(x, y, "Wealth Ultima (UIN: 147L037V01) - Demo Benefit Illustration")
    y -= 20

    # Policy details
    c.setFont("Helvetica", 9)
    c.drawString(x, y, f"Name: Demo  |  Age: {age}  |  Gender: {gender}  |  Sum Assured: ₹{sum_assured:,}")
    y -= 12
    c.drawString(x, y, f"Annual Premium: ₹{annual_premium:,}  |  Policy Term: {policy_term} yrs  |  PPT: {ppt} yrs  |  Fund: {fund_choice}")
    y -= 18

    # Table header
    c.setFont("Helvetica-Bold", 8)
    col_width = (width - 2*margin) / len(display_cols)
    # print header row(s)
    for i, col in enumerate(display_cols):
        tx = x + i * col_width
        c.drawString(tx, y, str(col)[:20])
    y -= 12
    c.setFont("Helvetica", 8)

    # rows
    rows_to_print = dataframe[display_cols].to_dict(orient="records")
    for r in rows_to_print:
        if y < margin + 40:
            c.showPage()
            y = height - margin
        for i, col in enumerate(display_cols):
            tx = x + i * col_width
            txt = f"{r[col]:,.2f}" if isinstance(r[col], (int, float)) else str(r[col])
            c.drawString(tx, y, txt[:20])
        y -= 10

    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

try:
    pdf_bytes = make_pdf(df[display_cols])
    st.download_button("Download BI as PDF", pdf_bytes, file_name="wealth_ultima_demo_bi.pdf", mime="application/pdf")
except Exception as e:
    st.error("PDF generation failed (reportlab may not be installed). You can download CSV or add 'reportlab' to your requirements.txt.")
    st.write("Error:", e)

# Footer / Disclaimer
st.markdown("""
---
**Disclaimer:** This is a demo BI for educational purposes. The model approximates average daily fund value by monthly end values,
applies charges monthly and models FMC as a monthly deduction from returns. Mortality charges are computed as 0.1% p.a. of sum-at-risk
(Death Benefit less Fund Value). This is NOT an official insurer BI. For official illustrations use bi.edelweisslife.in.
""")
