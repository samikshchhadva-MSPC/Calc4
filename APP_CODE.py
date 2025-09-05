import streamlit as st
import pandas as pd
import numpy as np
import io
import tempfile
import os

# Optional Excel support (only used if user uploads an .xlsm/.xlsx)
try:
    from openpyxl import load_workbook
    from openpyxl.utils import get_column_letter, coordinate_from_string, column_index_from_string
    from xlcalculator import ModelCompiler, Evaluator
    XL_AVAILABLE = True
except Exception:
    XL_AVAILABLE = False

st.set_page_config(page_title="BI UL — Pure Python Benefit Illustration", layout="wide")
st.title("📋 Benefit Illustration — Pure Python (Excel optional)")

st.markdown(
    """
This app runs **without** requiring the Excel workbook to be present on the running machine.
- Use the **sidebar form** to enter policy inputs.
- Press **Compute Benefit Illustration** to run the Python model and display the Output sheet.
- Optionally upload your `BI UL.xlsm` to let the app evaluate the real workbook (if you'd like).
"""
)

# ------------------------
# Editable input schema
# ------------------------
# Edit this schema to add/remove input fields to match your Input sheet.
INPUT_SCHEMA = [
    {"key": "policyholder_name", "label": "Policyholder name", "type": "text", "default": "John Doe"},
    {"key": "age", "label": "Age", "type": "int", "default": 35},
    {"key": "gender", "label": "Gender", "type": "select", "options": ["Male", "Female"], "default": "Male"},
    {"key": "sum_assured", "label": "Sum Assured (INR)", "type": "number", "default": 1000000},
    {"key": "annual_premium", "label": "Annual Premium (INR, annual equivalent)", "type": "number", "default": 50000},
    {"key": "policy_term", "label": "Policy Term (years)", "type": "int", "default": 10},
    {"key": "premium_frequency", "label": "Premium Frequency", "type": "select",
     "options": ["Annual", "Semi-Annual", "Quarterly", "Monthly"], "default": "Annual"},
    {"key": "assumed_rate", "label": "Assumed interest rate (annual %)", "type": "number", "default": 4.0},
    {"key": "surrender_charge_pct", "label": "Surrender charge (%)", "type": "number", "default": 30.0},
]

# ------------------------
# Helper: render input form
# ------------------------
st.sidebar.header("Policy inputs")
inputs = {}
for fld in INPUT_SCHEMA:
    key = fld["key"]
    lbl = fld["label"]
    typ = fld.get("type", "text")
    default = fld.get("default", "")
    if typ == "text":
        inputs[key] = st.sidebar.text_input(lbl, value=str(default))
    elif typ == "int":
        inputs[key] = st.sidebar.number_input(lbl, value=int(default), step=1, format="%d")
    elif typ == "number":
        inputs[key] = st.sidebar.number_input(lbl, value=float(default))
    elif typ == "select":
        opts = fld.get("options", [])
        inputs[key] = st.sidebar.selectbox(lbl, opts, index=opts.index(default) if default in opts else 0)
    else:
        inputs[key] = st.sidebar.text_input(lbl, value=str(default))

# Optionally upload Excel (user may still upload but not required)
st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("Optional: upload BI UL Excel (.xlsm / .xlsx) to evaluate workbook", type=["xlsm", "xlsx"])

# ------------------------
# Pure-Python calculation engine
# ------------------------
def compute_benefit_illustration(inp: dict):
    """
    Compute a simple Benefit Illustration using pure Python.
    Replace/extend these calculations to match the Excel formulas exactly.
    Returns:
      - outputs: dict of summary outputs (numbers)
      - proj_df: DataFrame with per-year projection (Year, PremiumPaidCum, AccumulatedValue, SurrenderValue, GuaranteedBenefit)
    """
    # Read inputs
    SA = float(inp.get("sum_assured", 0.0))
    annual_prem = float(inp.get("annual_premium", 0.0))
    term = int(inp.get("policy_term", 0))
    rate_pct = float(inp.get("assumed_rate", 0.0))
    surrender_charge_pct = float(inp.get("surrender_charge_pct", 0.0))
    freq = inp.get("premium_frequency", "Annual")

    # Frequency mapping if needed (we assume 'annual_prem' is annual equivalent)
    freq_map = {"Annual": 1, "Semi-Annual": 2, "Quarterly": 4, "Monthly": 12}
    payments_per_year = freq_map.get(freq, 1)

    r = rate_pct / 100.0

    # For a simple accumulation model assume premiums are paid at the start of each year and earn interest
    accumulated = 0.0
    projection = []
    total_prem_paid = 0.0
    for y in range(1, term + 1):
        # Add premium for year y (annual equivalent)
        premium_paid_this_year = annual_prem
        total_prem_paid += premium_paid_this_year

        # premiums paid at start of year: they compound for (term - y + 0) years until maturity
        # We'll compute accumulated as previous * (1+r) + premium_paid_this_year * (1+r)**(term - y)
        # Simpler approach: accumulate year by year:
        accumulated = (accumulated + premium_paid_this_year) * (1 + r)

        # For display, compute surrender value after applying surrender charge percentage
        surrender_value = accumulated * (1.0 - surrender_charge_pct / 100.0)

        # GuaranteedBenefit (example): show sum assured (you can plug more accurate guaranteed schedules)
        guaranteed_benefit = SA

        projection.append({
            "Year": y,
            "PremiumPaidThisYear": round(premium_paid_this_year, 2),
            "TotalPremiumsPaidCum": round(total_prem_paid, 2),
            "AccumulatedValue": round(accumulated, 2),
            "SurrenderValue": round(surrender_value, 2),
            "GuaranteedBenefit": round(guaranteed_benefit, 2),
        })

    # Maturity value = accumulated at end of policy term (this simple model)
    maturity_value = accumulated

    # Death benefit (simple): sum assured; you can change to SA + accumulated etc.
    death_benefit = SA

    outputs = {
        "SumAssured": SA,
        "AnnualPremium": annual_prem,
        "PolicyTermYears": term,
        "TotalPremiumsPaid": round(total_prem_paid, 2),
        "MaturityValue": round(maturity_value, 2),
        "DeathBenefit": round(death_benefit, 2),
        "SurrenderValueAtMaturity": round(projection[-1]["SurrenderValue"] if projection else 0.0, 2),
        "AssumedRatePct": rate_pct,
        "SurrenderChargePct": surrender_charge_pct,
    }

    proj_df = pd.DataFrame(projection)
    return outputs, proj_df

# ------------------------
# Excel-assisted evaluator (optional)
# ------------------------
def evaluate_workbook_with_xlcalculator(filelike):
    """
    If xlcalculator is available and the user uploaded a workbook, try to:
    - detect named inputs on the Input sheet and present them (not used here),
    - evaluate the 'Output' sheet cells and return them as a DataFrame.
    This is optional and will only run if XL_AVAILABLE==True.
    """
    if not XL_AVAILABLE:
        raise RuntimeError("Excel evaluation libraries (openpyxl / xlcalculator) are not installed.")
    # Save upload to a temp file if filelike is an uploaded file-like object
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(getattr(filelike, "name", "uploaded.xlsx"))[-1])
    tmp.write(filelike.getbuffer())
    tmp.flush()
    tmp.close()
    tmp_path = tmp.name

    # compile
    compiler = ModelCompiler()
    model = compiler.read_and_parse_archive(tmp_path)
    evaluator = Evaluator(model)

    # pick 'Output' sheet (common names)
    possible_names = ["Output", "OUTPUT", "output"]
    sheetname = None
    for n in possible_names:
        if n in model.workbook.sheets:
            sheetname = n
            break
    if sheetname is None:
        # fallback to any sheet containing 'output'
        for s in model.workbook.sheets:
            if "output" in s.lower():
                sheetname = s
                break
    if sheetname is None:
        sheetname = list(model.workbook.sheets.keys())[-1]

    wb2 = load_workbook(tmp_path, data_only=False)
    ws2 = wb2[sheetname]

    rows = []
    for r in range(1, ws2.max_row + 1):
        row_vals = []
        any_nonempty = False
        for c in range(1, ws2.max_column + 1):
            cell_coord = f"{get_column_letter(c)}{r}"
            ref = f"'{sheetname}'!{cell_coord}"
            try:
                val = evaluator.evaluate(ref)
            except Exception:
                val = ws2.cell(row=r, column=c).value
            row_vals.append(val)
            if val is not None and (str(val).strip() != ""):
                any_nonempty = True
        if any_nonempty:
            rows.append(row_vals)
    if rows:
        max_cols = max(len(r) for r in rows)
        df = pd.DataFrame([r + [None] * (max_cols - len(r)) for r in rows])
    else:
        df = pd.DataFrame()
    return df, sheetname

# ------------------------
# Compute on button press
# ------------------------
if st.button("Compute Benefit Illustration"):
    # First, try Excel evaluation if file uploaded and XL_AVAILABLE
    excel_df = None
    excel_sheet_name = None
    if uploaded_file is not None and XL_AVAILABLE:
        try:
            with st.spinner("Evaluating uploaded workbook (xlcalculator)..."):
                excel_df, excel_sheet_name = evaluate_workbook_with_xlcalculator(uploaded_file)
            st.success(f"Excel workbook evaluated (sheet: {excel_sheet_name}). Displaying that Output below.")
            st.subheader("Output sheet (evaluated from uploaded workbook)")
            st.dataframe(excel_df, use_container_width=True)
        except Exception as e:
            st.warning(f"Excel evaluation failed (falling back to Python model). Error: {e}")

    # Always run the pure-Python model so app works without Excel
    with st.spinner("Running pure-Python Benefit Illustration model..."):
        outputs, proj_df = compute_benefit_illustration(inputs)

    st.success("Pure-Python Benefit Illustration computed.")

    # Summary metrics
    st.header("Final Benefit Illustration — Summary")
    cols = st.columns(4)
    cols[0].metric("Sum Assured", f"₹ {outputs['SumAssured']:,.2f}")
    cols[1].metric("Annual Premium", f"₹ {outputs['AnnualPremium']:,.2f}")
    cols[2].metric("Policy Term (yrs)", f"{outputs['PolicyTermYears']}")
    cols[3].metric("Total Premiums Paid", f"₹ {outputs['TotalPremiumsPaid']:,.2f}")

    cols2 = st.columns(3)
    cols2[0].metric("Maturity Value (assumed)", f"₹ {outputs['MaturityValue']:,.2f}")
    cols2[1].metric("Death Benefit (example)", f"₹ {outputs['DeathBenefit']:,.2f}")
    cols2[2].metric("Surrender Value at maturity (assumed)", f"₹ {outputs['SurrenderValueAtMaturity']:,.2f}")

    # Projection table (year-by-year)
    st.subheader("Projection — year-by-year")
    st.dataframe(proj_df, use_container_width=True)

    # Download outputs (CSV & Excel)
    csv_buf = proj_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download projection (CSV)", data=csv_buf, file_name="bi_projection.csv", mime="text/csv")

    # Excel download for projection
    try:
        output_xl = io.BytesIO()
        with pd.ExcelWriter(output_xl, engine="openpyxl") as writer:
            proj_df.to_excel(writer, index=False, sheet_name="Projection")
            summary_df = pd.DataFrame(list(outputs.items()), columns=["Metric", "Value"])
            summary_df.to_excel(writer, index=False, sheet_name="Summary")
        st.download_button("Download BI (Excel)", data=output_xl.getvalue(), file_name="bi_result.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception:
        # openpy
