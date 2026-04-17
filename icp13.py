import streamlit as st
import pandas as pd
import io
import numpy as np

# Dictionary for element to oxide conversion
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
    volume = st.number_input("Volume of solution (mL)", min_value=0.0, value=50.0, step=0.1)
    initial_mass_g = st.number_input("Initial mass of sample (g)", min_value=0.0, value=0.1, step=0.01)
    initial_mass_mg = initial_mass_g * 1000 
    
    st.header("2. Additional Data")
    moisture = st.number_input("Moisture Content (%)", min_value=0.0, step=0.1)
    loi = st.number_input("Loss on Ignition (LOI) (%)", min_value=0.0, step=0.1)

# --- DATA PASTE ---
st.header("3. Paste ICP-OES Data")
raw_data = st.text_area("Paste Excel data here (Include headers and unit row):", height=150)

if raw_data:
    try:
        # Read data
        df_input = pd.read_csv(io.StringIO(raw_data), sep='\t')
        
        # REMOVE UNIT ROW: If first row contains 'mg/l', drop it
        if df_input.iloc[0].astype(str).str.contains('mg/l', case=False).any():
            df_input = df_input.iloc[1:].reset_index(drop=True)

        # CLEAN DATA: Remove symbols like '>', '<', and convert to numbers
        def clean_val(x):
            if isinstance(x, str):
                return x.replace('>', '').replace('<', '').strip()
            return x

        for col in df_input.columns:
            if col != 'Sample':
                df_input[col] = pd.to_numeric(df_input[col].apply(clean_val), errors='coerce')

        # AUTO-DETECT ELEMENTS
        detected_elements = []
        for elem in element_to_oxide.keys():
            if any(col.strip().startswith(f"{elem} ") for col in df_input.columns):
                detected_elements.append(elem)

        if not detected_elements:
            st.warning("No matching elements found in data headers.")
        else:
            st.header("4. Configure Display")
            config_cols = st.columns(len(detected_elements))
            element_modes = {}
            for i, elem in enumerate(detected_elements):
                with config_cols[i]:
                    element_modes[elem] = st.radio(f"**{elem}**", ["Elem", "Oxide"], key=f"mode_{elem}")

            # CALCULATIONS
            results_list = []
            for _, row in df_input.dropna(subset=['Sample']).iterrows():
                res = {"Sample": row['Sample']}
                total_row_perc = 0.0
                
                for elem in detected_elements:
                    matching_cols = [c for c in df_input.columns if c.strip().startswith(f"{elem} ")]
                    vals = row[matching_cols].dropna().values
                    
                    if len(vals) > 0:
                        avg_mg_l = np.mean(vals)
                        perc_elem = (avg_mg_l * (volume / 1000) / initial_mass_mg) * 100
                        
                        if element_modes[elem] == "Oxide":
                            formula, factor = element_to_oxide[elem]
                            val = perc_elem * factor
                            res[f"{formula} (%)"] = val
                        else:
                            val = perc_elem
                            res[f"{elem} (%)"] = val
                        
                        total_row_perc += val
                
                res["Moisture (%)"] = moisture
                res["LOI (%)"] = loi
                res["Total (%)"] = total_row_perc + moisture + loi
                results_list.append(res)

            st.header("5. Final Results")
            df_results = pd.DataFrame(results_list)
            st.dataframe(df_results.style.format(precision=3), use_container_width=True)

            csv = df_results.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV Report", csv, "icp_report.csv", "text/csv")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Paste your data to begin. The unit row (mg/l) will be automatically removed.")
