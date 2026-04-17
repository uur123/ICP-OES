import streamlit as st
import pandas as pd
import io
import numpy as np

# Dictionary for element to oxide conversion (Boron to Uranium)
element_to_oxide = {
    'Ag': ('Ag2O', 1.0741), 'Al': ('Al2O3', 1.8895), 'As': ('As2O3', 1.3203), 'Au': ('Au2O3', 1.1218),
    'B': ('B2O3', 3.2199), 'Ba': ('BaO', 1.1165), 'Bi': ('Bi2O3', 1.1148), 'Br': ('Br', 1.0),
    'C': ('CO2', 3.6667), 'Ca': ('CaO', 1.3992), 'Cd': ('CdO', 1.1423), 'Ce': ('CeO2', 1.2284),
    'Cl': ('Cl2O7', 2.628), 'Co': ('CoO', 1.2715), 'Cr': ('Cr2O3', 1.4615), 'Cs': ('Cs2O', 1.0602),
    'Cu': ('CuO', 1.2518), 'Dy': ('Dy2O3', 1.1477), 'Er': ('Er2O3', 1.1435), 'Eu': ('Eu2O3', 1.1579),
    'F': ('F', 1.0), 'Fe': ('Fe2O3', 1.4297), 'Ga': ('Ga2O3', 1.3442), 'Gd': ('Gd2O3', 1.1526),
    'Ge': ('GeO2', 1.4408), 'Hf': ('HfO2', 1.1793), 'Hg': ('HgO', 1.0798), 'Ho': ('Ho2O3', 1.1455),
    'I': ('I', 1.0), 'In': ('In2O3', 1.2091), 'Ir': ('IrO2', 1.1665), 'K': ('K2O', 1.2046),
    'La': ('La2O3', 1.1728), 'Lu': ('Lu2O3', 1.1371), 'Mg': ('MgO', 1.6583), 'Mn': ('MnO', 1.2912),
    'Mo': ('MoO3', 1.5003), 'N': ('N2O5', 3.855), 'Na': ('Na2O', 1.348), 'Nb': ('Nb2O5', 1.4305),
    'Nd': ('Nd2O3', 1.1664), 'Ni': ('NiO', 1.2725), 'Os': ('OsO4', 1.336), 'P': ('P2O5', 2.2914),
    'Pb': ('PbO', 1.0772), 'Pd': ('PdO', 1.1504), 'Pr': ('Pr6O11', 1.2082), 'Pt': ('PtO2', 1.164),
    'Rb': ('Rb2O', 1.0936), 'Re': ('Re2O7', 1.292), 'Rh': ('Rh2O3', 1.233), 'Ru': ('RuO2', 1.3165),
    'S': ('SO3', 2.497), 'Sb': ('Sb2O3', 1.1971), 'Sc': ('Sc2O3', 1.5338), 'Se': ('SeO2', 1.403),
    'Si': ('SiO2', 2.1393), 'Sm': ('Sm2O3', 1.1596), 'Sn': ('SnO2', 1.2696), 'Sr': ('SrO', 1.1826),
    'Ta': ('Ta2O5', 1.2211), 'Tb': ('Tb4O7', 1.1762), 'Te': ('TeO2', 1.2508), 'Th': ('ThO2', 1.1379),
    'Ti': ('TiO2', 1.6681), 'Tl': ('Tl2O3', 1.1174), 'Tm': ('Tm2O3', 1.1421), 'U': ('U3O8', 1.1792),
    'V': ('V2O5', 1.7852), 'W': ('WO3', 1.2611), 'Y': ('Y2O3', 1.2699), 'Yb': ('Yb2O3', 1.1387),
    'Zn': ('ZnO', 1.2448), 'Zr': ('ZrO2', 1.3508)
}

st.set_page_config(page_title="ICP-OES Result Calculator", layout="wide")
st.title("🧪 Automatic ICP-OES Calculator")

with st.sidebar:
    st.header("1. Sample Preparation")
    vol = st.number_input("Solution Volume (mL)", min_value=0.0, value=250.0, step=50.0)
    mass_g = st.number_input("Sample Mass (g)", min_value=0.0, value=0.5, step=0.01)
    st.header("2. Additional Data")
    moist = st.number_input("Moisture (%)", min_value=0.0, step=0.1)
    loi_val = st.number_input("LOI (%)", min_value=0.0, step=0.1)

st.header("3. Paste Data")
raw_data = st.text_area("Paste Excel data (headers + units row):", height=150)

if raw_data:
    try:
        df_input = pd.read_csv(io.StringIO(raw_data), sep='\t').dropna(axis=1, how='all')
        
        # Clean unit row if it exists
        if not df_input.empty:
            is_unit_row = df_input.iloc[0].astype(str).str.lower().str.contains('mg/l').any()
            if is_unit_row:
                df_input = df_input.iloc[1:].reset_index(drop=True)

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

        st.header("4. Per-Sample Dilution Factors")
        samples = df_input['Sample'].unique()
        dil_df = pd.DataFrame({'Sample': samples, 'Dilution Factor': [1.0] * len(samples)})
        edited_dil = st.data_editor(dil_df, hide_index=True)
        dil_map = dict(zip(edited_dil['Sample'], edited_dil['Dilution Factor']))

        detected = sorted([e for e in element_to_oxide.keys() if any(c.strip().startswith(f"{e} ") for c in df_input.columns)])
        
        st.header("5. Configure Display (Alphabetic Order)")
        config_cols = st.columns(min(len(detected), 10) if detected else 1)
        element_modes = {e: config_cols[i % 10].radio(f"**{e}**", ["Elem", "Oxide"], key=f"m_{e}") for i, e in enumerate(detected)}

        results, sd_details, highlights = [], [], {}

        for _, row in df_input.iterrows():
            s_name, s_dil = row['Sample'], dil_map.get(row['Sample'], 1.0)
            res, sd_res, row_total = {"Sample": s_name}, {"Sample": s_name}, 0.0

            for elem in detected:
                m_cols = [c for c in df_input.columns if c.strip().startswith(f"{elem} ")]
                vals = row[m_cols].dropna().values
                
                if len(vals) > 0:
                    avg_v, std_v = np.mean(vals), np.std(vals) if len(vals) > 1 else 0.0
                    factor_base = (vol/1000) * s_dil / (mass_g * 1000)
                    perc, sd_perc = (avg_v * factor_base) * 100, (std_v * factor_base) * 100
                    
                    label = elem
                    if element_modes[elem] == "Oxide":
                        formula, factor = element_to_oxide[elem]
                        perc, sd_perc, label = perc * factor, sd_perc * factor, formula

                    res[f"{label} (%)"], sd_res[f"{label} SD"], row_total = perc, sd_perc, row_total + perc
                    key = (s_name, f"{label} (%)")
                    if any((s_name, c) in limit_flags for c in m_cols): highlights[key] = 'background-color: #ffffb3'
                    if perc > 0 and (sd_perc / perc) > 0.10: highlights[key] = 'background-color: #ffcc99'

            res.update({"Moisture (%)": moist, "LOI (%)": loi_val, "Total (%)": row_total + moist + loi_val})
            results.append(res); sd_details.append(sd_res)

        st.header("6. Analysis Results")
        tab1, tab2 = st.tabs(["Main Percentages", "SD Details"])
        
        with tab1:
            df_final = pd.DataFrame(results)
            st.dataframe(df_final.style.format(precision=3).apply(lambda s: [highlights.get((s.Sample, c), '') for c in s.index], axis=1), use_container_width=True)
            st.info("💡 **Yellow**: Includes < or >. **Orange**: High wavelength variation (>10%).")
        
        with tab2:
            st.dataframe(pd.DataFrame(sd_details).style.format(precision=4), use_container_width=True)

        st.download_button("Download CSV", df_final.to_csv(index=False).encode('utf-8'), "icp_report.csv", "text/csv")

    except Exception as e:
        st.error(f"Processing Error: {e}")
