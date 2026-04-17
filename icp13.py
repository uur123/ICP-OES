import streamlit as st
import pandas as pd
import io
import numpy as np

# Oxide conversion dictionary
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
st.title("🧪 Advanced ICP-OES Calculator")

# --- SIDEBAR: GLOBAL PREP ---
with st.sidebar:
    st.header("1. Sample Preparation")
    volume = st.number_input("Solution Volume (mL)", min_value=0.0, value=50.0, step=0.1)
    initial_mass_g = st.number_input("Sample Mass (g)", min_value=0.0, value=0.1, step=0.01)
    st.header("2. Additional Data")
    moisture = st.number_input("Moisture (%)", min_value=0.0, step=0.1)
    loi = st.number_input("LOI (%)", min_value=0.0, step=0.1)

# --- STEP 1: PASTE DATA ---
st.header("3. Paste Data")
raw_data = st.text_area("Paste Excel data (headers + mg/l row):", height=150)

if raw_data:
    try:
        # Load and clean unit row
        df_input = pd.read_csv(io.StringIO(raw_data), sep='\t').dropna(axis=1, how='all')
        if df_input.iloc[0].astype(str).str.contains('mg/l', case=False).any():
            df_input = df_input.iloc[1:].reset_index(drop=True)

        # 4. FLAG DETECTION LIMITS & CLEAN
        limit_flags = []
        def clean_val(val, sample, col):
            if isinstance(val, str) and any(s in val for s in ['<', '>']):
                limit_flags.append((sample, col))
                return val.replace('<', '').replace('>', '').strip()
            return val

        for col in df_input.columns:
            if col != 'Sample':
                df_input[col] = df_input.apply(lambda r: clean_val(r[col], r['Sample'], col), axis=1)
                df_input[col] = pd.to_numeric(df_input[col], errors='coerce')

        # 5. DILUTION FACTORS PER SAMPLE
        st.header("4. Per-Sample Dilution Factors")
        samples = df_input['Sample'].unique()
        dil_df = pd.DataFrame({'Sample': samples, 'Dilution Factor': [1.0] * len(samples)})
        edited_dil = st.data_editor(dil_df, use_container_width=False, hide_index=True)
        dil_map = dict(zip(edited_dil['Sample'], edited_dil['Dilution Factor']))

        # 6. CONFIGURE ELEMENTS
        detected = [e for e in element_to_oxide.keys() if any(c.strip().startswith(f"{e} ") for c in df_input.columns)]
        st.header("5. Configure Display")
        config_cols = st.columns(len(detected))
        element_modes = {e: config_cols[i].radio(f"**{e}**", ["Elem", "Oxide"], key=f"m_{e}") for i, e in enumerate(detected)}

        # 7. CALCULATE
        final_results = []
        highlight_coords = {} # (sample, col_name) -> bool

        for _, row in df_input.iterrows():
            s_name = row['Sample']
            s_dil = dil_map.get(s_name, 1.0)
            res = {"Sample": s_name}
            row_total = 0.0

            for elem in detected:
                m_cols = [c for c in df_input.columns if c.strip().startswith(f"{elem} ")]
                vals = row[m_cols].dropna().values
                
                if len(vals) > 0:
                    avg_mg_l = np.mean(vals)
                    std_mg_l = np.std(vals) if len(vals) > 1 else 0.0
                    
                    # (mg/L * L * Dilution) / mg_mass * 100
                    mass_mg = initial_mass_g * 1000
                    perc = (avg_mg_l * (volume/1000) * s_dil / mass_mg) * 100
                    sd_perc = (std_mg_l * (volume/1000) * s_dil / mass_mg) * 100
                    
                    label = elem
                    if element_modes[elem] == "Oxide":
                        formula, factor = element_to_oxide[elem]
                        perc *= factor
                        sd_perc *= factor
                        label = formula

                    res[f"{label} (%)"] = perc
                    res[f"{label} SD"] = sd_perc
                    row_total += perc
                    
                    if any((s_name, c) in limit_flags for c in m_cols):
                        highlight_coords[(s_name, f"{label} (%)")] = True

            res.update({"Moisture (%)": moisture, "LOI (%)": loi, "Total (%)": row_total + moisture + loi})
            final_results.append(res)

        # DISPLAY
        st.header("6. Results")
        df_final = pd.DataFrame(final_results)
        
        def apply_styles(s):
            return ['background-color: #ffffb3' if (s.Sample, col) in highlight_coords else '' for col in s.index]

        st.dataframe(df_final.style.format(precision=3).apply(apply_styles, axis=1), use_container_width=True)
        st.info("💡 **Yellow cells** indicate original data contained `<` or `>`. **SD columns** show variation between wavelengths.")

    except Exception as e:
        st.error(f"Error: {e}")
