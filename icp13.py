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
st.title("Enhanced ICP-OES Result Calculator")

# --- SIDEBAR: PREP & ADDITIONAL DATA ---
with st.sidebar:
    st.header("1. Sample Preparation")
    volume = st.number_input("Volume of sample solution (mL)", min_value=0.0, value=50.0, step=0.1, format="%.2f")
    initial_mass_g = st.number_input("Initial mass of sample (g)", min_value=0.0, value=0.1, step=0.01, format="%.2f")
    initial_mass_mg = initial_mass_g * 1000 
    
    st.write("---")
    st.header("2. Additional Data")
    moisture_content = st.number_input("Moisture Content (%)", min_value=0.0, step=0.1, format="%.2f")
    loi = st.number_input("Loss on Ignition (LOI) (%)", min_value=0.0, step=0.1, format="%.2f")

# --- ELEMENT SELECTION ---
st.header("3. Select Elements")
if 'selected_elements' not in st.session_state:
    st.session_state.selected_elements = {}

cols = st.columns(18)
elements = sorted(list(element_to_oxide.keys()))

for i, element in enumerate(elements):
    with cols[i % 18]:
        # Using checkboxes for multi-element selection from paste
        if st.checkbox(element, key=f"check_{element}"):
            if element not in st.session_state.selected_elements:
                st.session_state.selected_elements[element] = "Elemental"
        else:
            st.session_state.selected_elements.pop(element, None)

# --- DATA PASTE ---
st.header("4. Paste Data & Calculate")
raw_data = st.text_area("Paste Excel data here (Include headers):", height=200, 
                        placeholder="Sample\tType\tBi 179.193\tBi 190.241...")

if raw_data and st.session_state.selected_elements:
    try:
        # Read the tab-separated data from Excel
        df_input = pd.read_csv(io.StringIO(raw_data), sep='\t')
        
        # Clean numeric columns (handle commas if needed)
        for col in df_input.columns:
            if col not in ['Sample', 'Type']:
                df_input[col] = pd.to_numeric(df_input[col].astype(str).str.replace(',', ''), errors='coerce')

        # Filter only Sample rows (ignoring Control rows)
        df_samples = df_input[~df_input['Sample'].str.contains('Control', case=False, na=False)]
        
        all_results = []

        for _, row in df_samples.iterrows():
            sample_data = {"Sample": row['Sample']}
            total_sample_percentage = 0.0
            
            for elem in st.session_state.selected_elements:
                # 1. Match columns for this element (e.g. "Bi 179.193", "Bi 190.241")
                matching_cols = [c for c in df_input.columns if c.startswith(f"{elem} ")]
                
                if matching_cols:
                    vals = row[matching_cols].dropna().values
                    if len(vals) > 0:
                        # 2. Average and calculate %
                        # Formula: (mg/L * L) / mg_sample * 100
                        avg_mg_l = np.mean(vals)
                        perc_elemental = (avg_mg_l * (volume / 1000) / initial_mass_mg) * 100
                        
                        # 3. Apply Oxide Conversion if selected (default to elemental for now)
                        final_val = perc_elemental
                        label = elem
                        if st.session_state.selected_elements[elem] == "Oxide":
                            oxide_name, factor = element_to_oxide[elem]
                            final_val = perc_elemental * factor
                            label = oxide_name
                        
                        sample_data[f"{label} (%)"] = final_val
                        total_sample_percentage += final_val

            # Add Moisture and LOI
            if moisture_content > 0: sample_data["Moisture (%)"] = moisture_content
            if loi > 0: sample_data["LOI (%)"] = loi
            
            sample_data["Total (%)"] = total_sample_percentage + moisture_content + loi
            all_results.append(sample_data)

        # Display Final Results
        st.subheader("Calculated Results")
        df_final = pd.DataFrame(all_results)
        st.dataframe(df_final.style.format(precision=3))
        
        # Download
        csv = df_final.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "results.csv", "text/csv")

    except Exception as e:
        st.error(f"Error: {e}. Ensure you include the header row when pasting.")
else:
    st.info("Select elements and paste your data to see the combined report.")
