import streamlit as st
import pandas as pd
import io
import numpy as np

# Element to oxide conversion dictionary with formulas
element_to_oxide = {
    'Na': ('Na2O', 1.348), 'Mg': ('MgO', 1.6583), 'Al': ('Al2O3', 1.8895),
    'Si': ('SiO2', 2.1393), 'P': ('P2O5', 2.291), 'S': ('SO3', 2.499),
    'Cl': ('Cl2O7', 2.628), 'K': ('K2O', 1.2047), 'Ca': ('CaO', 1.3992),
    'Sc': ('Sc2O3', 1.533), 'Ti': ('TiO2', 1.668), 'V': ('V2O5', 1.785),
    'Cr': ('Cr2O3', 1.461), 'Mn': ('MnO2', 1.582), 'Fe': ('Fe2O3', 1.4297),
    'Co': ('CoO', 1.271), 'Ni': ('NiO', 1.273), 'Cu': ('CuO', 1.252),
    'Zn': ('ZnO', 1.245), 'Bi': ('Bi2O3', 1.1148)
}

st.set_page_config(page_title="ICP-OES Result Calculator", layout="wide")
st.title("🧪 Smart ICP-OES Result Calculator")

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Sample Preparation")
    volume = st.number_input("Solution Volume (mL)", min_value=0.0, value=50.0, step=0.1)
    initial_mass_g = st.number_input("Sample Mass (g)", min_value=0.0, value=0.1, step=0.01)
    dilution_factor = st.number_input("Dilution Factor", min_value=1.0, value=1.0, step=0.1, help="Multiply by this factor if sample was diluted.")
    initial_mass_mg = initial_mass_g * 1000 
    
    st.header("2. Additional Data")
    moisture = st.number_input("Moisture Content (%)", min_value=0.0, step=0.1)
    loi = st.number_input("Loss on Ignition (LOI) (%)", min_value=0.0, step=0.1)

# --- DATA PASTE ---
st.header("3. Paste ICP-OES Data")
raw_data = st.text_area("Paste Excel data here (Include headers and mg/l row):", height=150)

if raw_data:
    try:
        df_input = pd.read_csv(io.StringIO(raw_data), sep='\t')
        
        # Flagging detection limit symbols (< or >)
        # We track which sample/element pairs need a warning
        warning_cells = []

        # Remove unit row (mg/l) if present
        if df_input.iloc[0].astype(str).str.contains('mg/l', case=False).any():
            unit_row = df_input.iloc[0]
            df_input = df_input.iloc[1:].reset_index(drop=True)

        def clean_and_flag(val, sample_name, col_name):
            if isinstance(val, str) and ('>' in val or '<' in val):
                warning_cells.append((sample_name, col_name))
                return val.replace('>', '').replace('<', '').strip()
            return val

        # Clean all numeric columns
        for col in df_input.columns:
            if col != 'Sample':
                df_input[col] = df_input.apply(lambda row: clean_and_flag(row[col], row['Sample'], col), axis=1)
                df_input[col] = pd.to_numeric(df_input[col], errors='coerce')

        # Detect elements
        detected_elements = [e for e in element_to_oxide.keys() if any(c.strip().startswith(f"{e} ") for c in df_input.columns)]

        if detected_elements:
            st.header("4. Configure Display")
            config_cols = st.columns(len(detected_elements))
            element_modes = {}
            for i, elem in enumerate(detected_elements):
                with config_cols[i]:
                    element_modes[elem] = st.radio(f"**{elem}**", ["Elem", "Oxide"], key=f"mode_{elem}")

            # Calculations
            results_list = []
            highlight_map = {} # To store which final cells to highlight

            for idx, row in df_input.iterrows():
                sample_name = str(row['Sample'])
                res = {"Sample": sample_name}
                total_row_perc = 0.0
                
                for elem in detected_elements:
                    matching_cols = [c for c in df_input.columns if c.strip().startswith(f"{elem} ")]
                    vals = row[matching_cols].dropna().values
                    
                    if len(vals) > 0:
                        # Calculation with Dilution Factor
                        avg_mg_l = np.mean(vals)
                        perc_elem = (avg_mg_l * (volume / 1000) * dilution_factor / initial_mass_mg) * 100
                        
                        formula_label = elem
                        if element_modes[elem] == "Oxide":
                            formula, factor = element_to_oxide[elem]
                            val = perc_elem * factor
                            formula_label = formula
                        else:
                            val = perc_elem
                        
                        col_key = f"{formula_label} (%)"
                        res[col_key] = val
                        total_row_perc += val

                        # Check if any original column for this element had a < or >
                        if any((sample_name, c) in warning_cells for c in matching_cols):
                            highlight_map[(sample_name, col_key)] = True

                res["Moisture (%)"] = moisture
                res["LOI (%)"] = loi
                res["Total (%)"] = total_row_perc + moisture + loi
                results_list.append(res)

            # --- DISPLAY WITH HIGHLIGHTING ---
            st.header("5. Final Results")
            df_results = pd.DataFrame(results_list)

            def highlight_limits(s):
                return ['background-color: #ffffb3' if (s.Sample, col) in highlight_map else '' for col in s.index]

            st.dataframe(df_results.style.format(precision=3).apply(highlight_limits, axis=1), use_container_width=True)
            st.info("💡 **Yellow cells** indicate that the original data contained detection limit symbols (< or >).")
            
            csv = df_results.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV Report", csv, "icp_report.csv", "text/csv")
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Paste your data to start. The 'mg/l' row and detection symbols will be handled automatically.")
