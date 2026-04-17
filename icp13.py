import streamlit as st
import pandas as pd
import io
import numpy as np
import plotly.express as px
import re

# Element to oxide conversion dictionary
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
st.title("🧪 Clean Multi-Block ICP-OES Calculator")

# --- 1. DATA INPUT ---
st.header("1. Paste Data")
raw_pasted_text = st.text_area("Paste your Excel data here (Include 'Sample' headers):", height=200)

def parse_manual(text):
    """Parses text manually to avoid pandas alignment issues with empty/shifted columns."""
    blocks = re.split(r'(?mi)^Sample', text)
    master_data = {}

    for block in blocks:
        if not block.strip(): continue
        lines = [line.strip().split('\t') for line in block.strip().split('\n') if line.strip()]
        if not lines: continue
        
        # Line 0 is the header (e.g., Fe 238.1, Al 167.0)
        headers = lines[0]
        
        # Process every row after the header
        for row in lines[1:]:
            if not row: continue
            
            # The FIRST item is always the Sample Name
            s_name = row[0].strip()
            
            # Skip noise rows (Units, Averages, SDs)
            if any(x in s_name.lower() for x in ['mg/l', 'avg', 'sd', 'unit', 'control']):
                continue
                
            if s_name not in master_data:
                master_data[s_name] = {}
            
            # Match values to headers starting from index 1
            for i in range(1, len(row)):
                if i < len(headers):
                    col_name = headers[i].strip()
                    if col_name:
                        master_data[s_name][col_name] = row[i]
    
    if not master_data: return None
    return pd.DataFrame.from_dict(master_data, orient='index').rename_axis('Sample').reset_index()

if raw_pasted_text:
    try:
        df_full = parse_manual(raw_pasted_text)
        
        if df_full is not None:
            # Numeric cleaning for < and > symbols
            limit_flags = []
            for col in df_full.columns:
                if col != 'Sample':
                    def clean_numeric(val, sample, cname):
                        s = str(val)
                        if any(x in s for x in ['<', '>']):
                            limit_flags.append((sample, cname))
                            return s.replace('<', '').replace('>', '').strip()
                        return val
                    df_full[col] = df_full.apply(lambda r: clean_numeric(r[col], r['Sample'], col), axis=1)
                    df_full[col] = pd.to_numeric(df_full[col], errors='coerce')

            # --- 2. PER-SAMPLE PARAMETERS ---
            st.subheader("2. Sample Preparation & Parameters")
            s_list = df_full['Sample'].unique()
            p_df = pd.DataFrame({
                'Sample': s_list, 
                'Mass (g)': 0.5, 
                'Vol (mL)': 500.0, 
                'Dilution': 1.0, 
                'Moisture (%)': 0.0, 
                'LOI (%)': 0.0
            })
            e_prep = st.data_editor(p_df, hide_index=True, use_container_width=True)
            p_map = e_prep.set_index('Sample').to_dict('index')

            # --- 3. ELEMENT CONFIG ---
            detected = sorted(list(set([e for e in element_to_oxide.keys() for c in df_full.columns if c.strip().startswith(f"{e} ")])))
            st.subheader("3. Select Oxide/Elemental Mode")
            if detected:
                c_modes = st.columns(min(len(detected), 10))
                modes = {e: c_modes[i % 10].radio(f"**{e}**", ["Elem", "Oxide"], key=f"m_{e}") for i, e in enumerate(detected)}
            else:
                st.warning("No standard elements detected. Check your column headers.")

            # --- 5. CALCULATIONS ---
            results = []
            for _, row in df_full.iterrows():
                sn = row['Sample']
                pm = p_map.get(sn, {'Mass (g)':0.5, 'Vol (mL)':500.0, 'Dilution':1.0, 'Moisture (%)':0.0, 'LOI (%)':0.0})
                res, total_measured = {"Sample": sn}, 0.0

                for elem in detected:
                    m_cols = [c for c in df_full.columns if c.strip().startswith(f"{elem} ")]
                    vals = row[m_cols].dropna().values
                    if len(vals) > 0:
                        av = np.mean(vals)
                        f = (pm['Vol (mL)']/1000) * pm['Dilution'] / (pm['Mass (g)'] * 1000)
                        perc = (av * f) * 100
                        
                        label = elem
                        if modes[elem] == "Oxide":
                            form, factor = element_to_oxide[elem]
                            perc, label = perc * factor, form
                        
                        res[f"{label} (%)"] = round(perc, 4)
                        total_measured += perc

                res.update({"Moisture (%)": pm['Moisture (%)'], "LOI (%)": pm['LOI (%)'], "Total (%)": round(total_measured + pm['Moisture (%)'] + pm['LOI (%)'], 3)})
                results.append(res)

            # --- 6. DISPLAY ---
            st.header("4. Analysis Results")
            df_res = pd.DataFrame(results)
            st.dataframe(df_res, use_container_width=True)
            st.download_button("Download CSV", df_res.to_csv(index=False).encode('utf-8'), "results.csv", "text/csv")

    except Exception as e:
        st.error(f"Error parsing data. Please check your paste format. Details: {e}")
