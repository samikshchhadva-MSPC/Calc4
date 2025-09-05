import streamlit as st
import pandas as pd
import tempfile
import os
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter, coordinate_from_string, column_index_from_string
from xlcalculator import ModelCompiler, Evaluator

st.set_page_config(page_title="BI UL — Benefit Illustration (no VBA)", layout="wide")
st.title("📋 Benefit Illustration — Streamlit (Excel formulas only, VBA ignored)")

# Helper: load workbook (from upload or local fallback)
def load_workbook_from_upload(uploaded_file):
    """
    Returns tuple (workbook, filepath).
    If uploaded_file is None and fallback exists, returns (wb, fallback_path).
    """
    if uploaded_file is None:
        fallback = "/mnt/data/BI UL.xlsm"
        if os.path.exists(fallback):
            wb = load_workbook(fallback, data_only=False)
            return wb, fallback
        return None, None
    else:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[-1])
        tmp.write(uploaded_file.getbuffer())
        tmp.flush()
        tmp.close()
        wb = load_workbook(tmp.name, data_only=False)
        return wb, tmp.name

# Extract defined names (named ranges) that point to single cells and are on the Input sheet
def get_named_inputs_from_wb(wb, sheet_name_candidates=("Input", "INPUT", "input")):
    inputs = {}
    dn = wb.defined_names
    for defn in dn.definedName:
        name = defn.name
        if name is None or name.startswith('_xlnm'):
            continue
        try:
            destinations = list(defn.destinations)
        except Exception:
            continue
        for (sname, coord) in destinations:
            if sname in wb.sheetnames and any(sname == c for c in sheet_name_candidates):
                # handle single cell named ranges
                if ":" not in coord:
                    inputs[name] = (sname, coord)
                else:
                    a, b = coord.split(":")
                    if a == b:
                        inputs[name] = (sname, a)
                break
    return inputs

# Fallback heuristic: assume Input sheet is key-value table with first column labels and second column default values
def get_key_value_inputs_from_sheet(wb, sheet_name_candidates=("Input", "INPUT", "input")):
    for candidate in sheet_name_candidates:
        if candidate in wb.sheetnames:
            ws = wb[candidate]
            kv = {}
            for r in range(1, min(200, ws.max_row) + 1):
                key_cell = ws.cell(row=r, column=1).value
                val_cell = ws.cell(row=r, column=2).value
                if key_cell is None:
                    continue
                key = str(key_cell).strip()
                if key == "":
                    continue
                kv[key] = {"sheet": candidate, "cell": f"{get_column_letter(2)}{r}", "default": val_cell}
            return kv
    return {}

# Write inputs (dict of (sheet, cell, value)) into a workbook and save to a temp file, return temp path
def write_inputs_to_tempfile_and_save(wb, inputs_map):
    # create temp file path
    tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    tmpfile.close()
    # apply inputs_map
    for k, v in inputs_map.items():
        # v is (sheet, cell, value)
        try:
            sname, coord, val = v
        except Exception:
            continue
        if sname in wb.sheetnames:
            ws = wb[sname]
            # write value into the target cell
            ws[coord] = val
    wb.save(tmpfile.name)
    return tmpfile.name

# Evaluate all cells on Output sheet and return as dataframe + sheetname
def evaluate_output_sheet(tempfile_path, output_sheet_name_guess=("Output", "OUTPUT", "output")):
    compiler = ModelCompiler()
    model = compiler.read_and_parse_archive(tempfile_path)
    evaluator = Evaluator(model)

    # choose sheet name
    sheetname = None
    # model.workbook.sheets is a dict-like (keys are sheet names) in xlcalculator models
    try:
        sheet_keys = list(model.workbook.sheets.keys())
    except Exception:
        # fallback to reading with openpyxl
        wb_temp = load_workbook(tempfile_path, data_only=False)
        sheet_keys = wb_temp.sheetnames

    for s in output_sheet_name_guess:
        if s in sheet_keys:
            sheetname = s
            break
    if sheetname is None:
        for s in sheet_keys:
            if s.lower() == "output":
                sheetname = s
                break
    if sheetname is None:
        # try any sheet that contains 'output' in name
        for s in sheet_keys:
            if "output" in s.lower():
                sheetname = s
                break
    if sheetname is None:
        sheetname = sheet_keys[-1]

    # Get dimensions via openpyxl
    wb2 = load_workbook(tempfile_path, data_only=False)
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

    # create DataFrame
    if rows:
        max_cols = max(len(r) for r in rows)
        df = pd.DataFrame([r + [None] * (max_cols - len(r)) for r in rows])
    else:
        df = pd.DataFrame()
    return df, sheetname

# Safely get a cell's current value from workbook
def get_cell_value(wb, sheet, coord):
    try:
        col, row = coordinate_from_string(coord)
        col_idx = column_index_from_string(col)
        return wb[sheet].cell(row=row, column=col_idx).value
    except Exception:
        try:
            return wb[sheet][coord].value
        except Exception:
            return None

# UI: Upload / load workbook
uploaded_file = st.file_uploader("Upload BI UL Excel file (.xlsm or .xlsx). If none uploaded the app will try `/mnt/data/BI UL.xlsm`.", type=["xlsm", "xlsx", "xls"])

wb_obj = None
orig_tmp_path = None
wb_obj, orig_tmp_path = load_workbook_from_upload(uploaded_file)

if wb_obj is None:
    st.info("Please upload your BI UL.xlsm file to continue or place it at /mnt/data/BI UL.xlsm.")
    st.stop()

# Detect named inputs
named_inputs = get_named_inputs_from_wb(wb_obj)
use_named = len(named_inputs) > 0

st.sidebar.header("Input mode")
if use_named:
    st.sidebar.success(f"Detected {len(named_inputs)} named input(s) on Input sheet. Using named inputs.")
else:
    st.sidebar.warning("No named inputs detected. Falling back to key-value heuristic from the Input sheet.")

inputs_map_for_writing = {}

if use_named:
    st.sidebar.subheader("Named inputs (edit values)")
    for name, (sheet, coord) in named_inputs.items():
        val = get_cell_value(wb_obj, sheet, coord)
        if isinstance(val, (int, float)) or (isinstance(val, str) and str(val).replace('.', '', 1).isdigit()):
            default_val = float(val) if val not in (None, "") else 0.0
            new_val = st.sidebar.number_input(f"{name} ({sheet}!{coord})", value=default_val)
        else:
            new_val = st.sidebar.text_input(f"{name} ({sheet}!{coord})", value=str(val) if val is not None else "")
        inputs_map_for_writing[name] = (sheet, coord, new_val)
else:
    kv = get_key_value_inputs_from_sheet(wb_obj)
    if not kv:
        st.sidebar.subheader("Manual inputs (no auto-detected Input sheet)")
        manual_count = st.sidebar.number_input("How many manual inputs to add?", min_value=0, max_value=50, value=0)
        for i in range(manual_count):
            label = st.sidebar.text_input(f"Label #{i+1}", value=f"Input_{i+1}")
            sheet_name = st.sidebar.text_input(f"Sheet for {label}", value="Input")
            cell = st.sidebar.text_input(f"Cell for {label}", value=f"A{i+2}")
            value = st.sidebar.text_input(f"Value for {label}", value="")
            if label:
                inputs_map_for_writing[label] = (sheet_name, cell, value)
    else:
        st.sidebar.subheader("Detected Input key→value pairs (edit defaults)")
        for key, meta in kv.items():
            default = meta.get("default", "")
            if isinstance(default, (int, float)):
                new_val = st.sidebar.number_input(f"{key} ({meta['sheet']}!{meta['cell']})", value=float(default))
            else:
                # allow numeric-like defaults
                try:
                    num = float(default) if default not in (None, "") and str(default).replace('.', '', 1).isdigit() else None
                except Exception:
                    num = None
                if num is not None:
                    new_val = st.sidebar.number_input(f"{key} ({meta['sheet']}!{meta['cell']})", value=num)
                else:
                    new_val = st.sidebar.text_input(f"{key} ({meta['sheet']}!{meta['cell']})", value=str(default) if default is not None else "")
            inputs_map_for_writing[key] = (meta["sheet"], meta["cell"], new_val)

# Confirm & compute button
if st.sidebar.button("Compute Benefit Illustration"):
    with st.spinner("Writing inputs and evaluating formulas..."):
        try:
            # reload workbook fresh from orig_tmp_path where possible to avoid overwriting original
            if orig_tmp_path and os.path.exists(orig_tmp_path):
                wb_to_write = load_workbook(orig_tmp_path, data_only=False)
            else:
                wb_to_write = wb_obj
            temp_path = write_inputs_to_tempfile_and_save(wb_to_write, inputs_map_for_writing)
            df_out, out_sheet = evaluate_output_sheet(temp_path)
        except Exception as e:
            st.error(f"Computation failed: {e}")
            st.stop()

    st.success("Computation finished — showing Benefit Illustration outputs.")
    st.header("Final Benefit Illustration — Output sheet")
    st.subheader(f"Output sheet used: {out_sheet}")
    st.dataframe(df_out, use_container_width=True)

    if not df_out.empty:
        try:
            candidate = df_out.iloc[:, :2].dropna(how="all")
            candidate.columns = ["Label", "Value"] if candidate.shape[1] >= 2 else ["Label"]
            if "Value" in candidate.columns:
                st.subheader("Key outputs (interpreted from leftmost two columns)")
                st.table(candidate.head(50).set_index("Label"))
        except Exception:
            pass

    # allow download of the temp workbook with inputs written
    try:
        with open(temp_path, "rb") as f:
            st.download_button("Download workbook with inputs (temp file)", data=f, file_name="BI_UL_with_inputs.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception:
        pass
else:
    st.sidebar.write("Press **Compute Benefit Illustration** to run formulas and show the Output sheet.")

st.markdown(
    """
    **Notes**
    - Fixes included for import typo and improved robustness.
    - If you still hit errors, please paste the stack trace here and I'll fix the next issue.
    - Install required packages:
      pip install streamlit openpyxl pandas xlcalculator
    """
)
