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
    'Zn': ('ZnO', 1.245), 'Bi': ('Bi2O3', 1.1148) # Added Bi for your example
}

st.set_page_config(page_title="ICP-OES Result Calculator", layout="wide")
st.title("Enhanced ICP-OES Result Calculator")

# --- SIDEBAR: PREP DATA ---
with st.sidebar:
    st.header("1. Sample Preparation")
    volume = st.number_input("Volume of solution (mL)", min_value=0.0, value=50.0, step=0.1)
    initial_mass_g = st.number_input("Initial mass of sample (g)", min_value=0.0, value=0.1, step=0.01)
    initial_mass_mg = initial_mass_g * 1000 

# --- STEP 1: ELEMENT SELECTION ---
st.header("2. Select Elements")
if 'selected_elements' not in st.session_state:
    st.session_state.selected_elements = set()

cols = st.columns(18)
elements_list = sorted(list(element_to_oxide.keys()))
for i, elem in enumerate(elements_list):
    with cols[i % 18]:
        if st.checkbox(elem, key=f"check_{elem}"):
            st.session_state.selected_elements.add(elem)
        else:
            st.session_state.selected_elements.discard(elem)

# --- STEP 2: DATA PASTE ---
st.header("3. Paste ICP-OES Data")
raw_data = st.text_area("Paste Excel data here (Include headers):", height=200, placeholder="Sample\tType\tBi 179.193...")

# --- STEP 3: PROCESSING & RESULTS ---
if raw_data and st.session_state.selected_elements:
    try:
        # Load pasted data
        df_input = pd.read_csv(io.StringIO(raw_data), sep='\t')
        
        # We need to calculate values for each sample in the pasted table
        samples = df_input['Sample'].unique()
        results_list = []

        for sample_name in samples:
            sample_row = df_input[df_input['Sample'] == sample_name]
            sample_results = {"Sample": sample_name}
            
            for elem in st.session_state.selected_elements:
                # Find all columns that start with the element symbol (e.g., "Bi ")
                matching_cols = [c for c in df_input.columns if c.startswith(f"{elem} ")]
                
                if matching_cols:
                    # Get values (mg/L)
                    vals = sample_row[matching_cols].values.flatten()
                    
                    # Basic Outlier Removal: Keep values within 20% of the median
                    median_val = np.median(vals)
                    clean_vals = [v for v in vals if 0.8 * median_val <= v <= 1.2 * median_val]
                    avg_conc_mg_l = np.mean(clean_vals) if clean_vals else median_val
                    
                    # Calculate %: (mg/L * L) / mg_sample * 100
                    perc_elemental = (avg_conc_mg_l * (volume / 1000) / initial_mass_mg) * 100
                    
                    # Default display (you can add a toggle per element here if needed)
                    sample_results[f"{elem} (%)"] = perc_elemental
            
            results_list.append(sample_results)

        # Final Table
        df_results = pd.DataFrame(results_list)
        st.subheader("Calculated Results (Elemental %)")
        st.dataframe(df_results.style.format(precision=4))

        # --- OXIDE CONVERSION PREVIEW ---
        if st.checkbox("Show Oxide Conversions"):
            df_oxide = df_results.copy()
            for elem in st.session_state.selected_elements:
                col_name = f"{elem} (%)"
                if col_name in df_oxide.columns:
                    oxide_name, factor = element_to_oxide[elem]
                    df_oxide[f"{oxide_name} (%)"] = df_oxide[col_name] * factor
            st.dataframe(df_oxide.style.format(precision=4))

    except Exception as e:
        st.error(f"Error: {e}. Check if you copied the header row.")
else:
    st.info("Please select elements above and paste your data to begin.")
