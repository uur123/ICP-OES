import streamlit as st
import pandas as pd
import io
import numpy as np
import plotly.express as px
import re

# Element to oxide conversion dictionary (B to U)
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

st.set_page_config(page_title="ICP-OES Smart Calculator", layout="wide")
st.title("🧪 Multi-Block ICP-OES Result Calculator")

# --- 1. DATA INPUT ---
st.header("1. Data Input")
raw_data = st.text_area("Paste Excel data here (Multiple 'Sample' blocks supported):", height=200)

if raw_data:
    try:
        # Split data by 'Sample' keyword (handles leading whitespace/tabs)
        sections = [s.strip() for s in re.split(r'(?m)^Sample', raw_data) if s.strip()]
        dfs_to_merge = []

        for section in sections:
            full_sec = "Sample\t" + section
            # Use sep=None with engine='python' to auto-detect tab or comma
            df_temp = pd.read_csv(io.StringIO(full_sec), sep=None, engine='python').dropna(axis=1, how='all')
            
            # Unit row detection and removal
            if not df_temp.empty:
                # Check first row of actual data for mg/l
                if df_temp.iloc[0].astype(str).str.lower().str.contains('mg/l').any():
                    df_temp = df_temp.iloc[1:].reset_index(drop=True)
            
            # Standardize 'Sample' column and set as index for merging
            df_temp['Sample'] = df_temp['Sample'].astype(str).str.strip()
            dfs_to_merge.append(df_temp.set_index('Sample'))

        # Join all tables together based on Sample index
        if dfs_to_merge:
            df_merged = pd.concat(dfs_to_merge, axis=1).reset_index()
        else:
            st.error("Could not find any data blocks starting with 'Sample'.")
            st.stop()

        # SANITIZATION: Filter out literal "Sample", "Control", or blank names
        df_filtered = df_merged[df_merged['Sample'].notna()].copy()
        df_filtered = df_filtered[~df_filtered['Sample'].str.lower().isin(['sample', 'control', 'nan', ''])]
        df_filtered = df_filtered[~df_filtered['Sample'].str.contains('Control', case=False, na=False)].copy()

        # Clean numerical values & flag limit symbols (<, >)
        limit_flags = []
        for col in df_filtered.columns:
            if col != 'Sample':
                def clean_tag(val, sample, cname):
                    if isinstance(val, str) and any(s in val for s in ['<', '>']):
                        limit_flags.append((sample, cname))
                        return val.replace('<', '').replace('>', '').strip()
                    return val
                df_filtered[col] = df_filtered.apply(lambda r: clean_tag(r[col], r['Sample'], col), axis=1)
                df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')

        # --- 2. PER-SAMPLE PARAMETERS ---
        st.subheader("2. Sample Preparation & Parameters")
        def auto_dil(name):
            match = re.search(r'(\d+)\s?[xX]', str(name))
            return float(match.group(1)) if match else 1.0

        samples = df_filtered['Sample'].unique()
        prep_df = pd.DataFrame({
            'Sample': samples, 'Mass (g)': [0.5]*len(samples), 'Vol (mL)': [500.0]*len(samples),
            'Dilution': [auto_dil(s) for s in samples], 'Moist (%)': [0.0]*len(samples), 'LOI (%)': [0.0]*len(samples)
        })
        edited_prep = st.data_editor(prep_df, hide_index=True, use_container_width=True)
        p_map = edited_prep.set_index('Sample').to_dict('index')

        # --- 3. ELEMENT CONFIG ---
        detected = sorted([e for e in element_to_oxide.keys() if any(c.strip().startswith(f"{e} ") for c in df_filtered.columns)])
        st.subheader("3. Select Oxide/Elemental Display")
        config_cols = st.columns(min(len(detected), 10) if detected else 1)
        modes = {e: config_cols[i % 10].radio(f"**{e}**", ["Elem", "Oxide"], key=f"m_{e}") for i, e in enumerate(detected)}

        # --- CALCULATIONS ---
        results, sd_details, h_res, h_sd = [], [], {}, {}
        for _, row in df_filtered.iterrows():
            s = row['Sample']
            p = p_map.get(s, {'Mass (g)':0.5, 'Vol (mL)':500.0, 'Dilution':1.0, 'Moist (%)':0.0, 'LOI (%)':0.0})
            res, sd_res, measured_total = {"Sample": s}, {"Sample": s}, 0.0

            for elem in detected:
                m_cols = [c for c in df_filtered.columns if c.strip().startswith(f"{elem} ")]
                vals = row[m_cols].dropna().values
                if len(vals) > 0:
                    avg_v, std_v = np.mean(vals), np.std(vals) if len(vals) > 1 else 0.0
                    f = (p['Vol (mL)']/1000) * p['Dilution'] / (p['Mass (g)'] * 1000)
                    perc, sd_perc = (avg_v * f) * 100, (std_v * f) * 100
                    
                    label = elem
                    if modes[elem] == "Oxide":
                        formula, factor = element_to_oxide[elem]
                        perc, sd_perc, label = perc * factor, sd_perc * factor, formula
                    
                    res[f"{label} (%)"] = perc
                    sd_res[f"{label} SD"] = sd_perc
                    measured_total += perc
                    if any((s, c) in limit_flags for c in m_cols): h_res[(s, f"{label} (%)")] = 'background-color: #ffffb3'
                    if perc > 0 and (sd_perc / perc) > 0.10: 
                        h_res[(s, f"{label} (%)")] = 'background-color: #ffcc99'
                        h_sd[(s, f"{label} SD")] = 'background-color: #ff9999'

            res.update({"Moisture (%)": p['Moist (%)'], "LOI (%)": p['LOI (%)'], "Total (%)": measured_total + p['Moist (%)'] + p['LOI (%)']})
            results.append(res); sd_details.append(sd_res)

        # --- 4. DISPLAY ---
        st.header("4. Results Analysis")
        t1, t2, t3 = st.tabs(["📊 Results", "📏 SD Verification", "🥧 Charts"])
        
        with t1:
            df_final = pd.DataFrame(results)
            st.dataframe(df_final.style.format(precision=3).apply(lambda r: [h_res.get((r.Sample, c), '') for c in r.index], axis=1), use_container_width=True)
        
        with t2:
            st.dataframe(pd.DataFrame(sd_details).style.format(precision=4).apply(lambda r: [h_sd.get((r.Sample, c), '') for c in r.index], axis=1), use_container_width=True)

        with t3:
            for i, item in enumerate(results):
                st.write(f"### {item['Sample']}")
                c1, c2 = st.columns(2)
                comp = {k: v for k, v in item.items() if k not in ['Sample', 'Total (%)']}
                if sum(comp.values()) > 0:
                    c1.plotly_chart(px.pie(values=list(comp.values()), names=list(comp.keys()), title="Measured Breakdown"), use_container_width=True, key=f"p1_{i}")
                    unk = max(0, 100 - item['Total (%)'])
                    c2.plotly_chart(px.pie(values=[item['Total (%)'], unk], names=['Measured', 'Unknown'], title="Mass Balance"), use_container_width=True, key=f"p2_{i}")

        st.download_button("Download Report", df_final.to_csv(index=False).encode('utf-8'), "icp_final.csv", "text/csv")

    except Exception as e:
        st.error(f"Processing Error: {e}")

st.info(f"**Developer:** [Your Name](https://linkedin.com)")
