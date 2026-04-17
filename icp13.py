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

# --- SIDEBAR: PREP & ADDITIONAL DATA ---
with st.sidebar:
    st.header("1. Sample Preparation")
    volume = st.number_input("Volume of solution (mL)", min_value=0.0, value=50.0, step=0.1)
    initial_mass_g = st.number_input("Initial mass of sample (g)", min_value=0.0, value=0.1, step=0.01)
    initial_mass_mg = initial_mass_g * 1000 
    
    st.header("2. Additional Data")
    moisture = st.number_input("Moisture Content (%)", min_value=0.0, step=0.1)
    loi = st.number_input("Loss on Ignition (LOI) (%)", min_value=0.0, step=0.1)

# --- STEP 1: PASTE DATA ---
st.header("3. Paste ICP-OES Data")
raw_data = st.text_area("Paste Excel data here (Include headers):", height=150)

if raw_data:
    try:
        df_input = pd.read_csv(io.StringIO(raw_data), sep='\t')
        
        # Auto-detect elements based on column headers
        detected_elements = []
        for elem in element_to_oxide.keys():
            if any(col.startswith(f"{elem} ") for col in df_input.columns):
                detected_elements.append(elem)

        if not detected_elements:
            st.warning("No matching elements from the dictionary found in data.")
        else:
            # --- STEP 2: DYNAMIC CONTROLS ---
            st.header("4. Configure Elements")
            st.write("Detected elements from your data. Choose how to display them:")
            
            # Use columns to show toggles for detected elements
            config_cols = st.columns(len(detected_elements))
            element_modes = {}
            
            for i, elem in enumerate(detected_elements):
                with config_cols[i]:
                    mode = st.radio(f"**{elem}**", ["Elem", "Oxide"], key=f"mode_{elem}")
                    element_modes[elem] = mode

            # --- STEP 3: CALCULATIONS ---
            results_list = []
            # Filter out control/blank rows if they exist
            df_samples = df_input[~df_input['Sample'].str.contains('Control|Blank', case=False, na=False)]

            for _, row in df_samples.iterrows():
                res = {"Sample": row['Sample']}
                total_row_perc = 0.0
                
                for elem in detected_elements:
                    # Find and average all wavelengths for this element
                    matching_cols = [c for c in df_input.columns if c.startswith(f"{elem} ")]
                    vals = pd.to_numeric(row[matching_cols], errors='coerce').dropna().values
                    
                    if len(vals) > 0:
                        avg_mg_l = np.mean(vals)
                        # mg/L -> mg in total volume -> % of total mass
                        perc_elem = (avg_mg_l * (volume / 1000) / initial_mass_mg) * 100
                        
                        if element_modes[elem] == "Oxide":
                            ox_name, factor = element_to_oxide[elem]
                            val = perc_elem * factor
                            res[f"{ox_name} (%)"] = val
                        else:
                            val = perc_elem
                            res[f"{elem} (%)"] = val
                        
                        total_row_perc += val
                
                # Add Moisture/LOI to total
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
        st.error(f"Processing Error: {e}")
else:
    st.info("Paste your ICP-OES data (including headers) to see the analysis.")
