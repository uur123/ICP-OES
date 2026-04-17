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

def parse_and_merge_blocks(text):
    # Split text into blocks where "Sample" starts
    raw_blocks = re.split(r'(?mi)^Sample', text)
    master_dict = {} 
    
    for block in raw_blocks:
        if not block.strip(): continue
        
        # Load block CSV safely, ensuring we treat the first line as a header
        clean_block = "Sample" + block.strip()
        df = pd.read_csv(io.StringIO(clean_block), sep='\t')
        
        # Ensure the first column is explicitly named 'Sample'
        df.columns = ['Sample'] + list(df.columns[1:])
        
        # Filter out metadata and unit rows
        df = df[df['Sample'].notna()]
        df = df[~df['Sample'].astype(str).str.lower().str.contains('mg/l|sample|control|unit|avg|sd', na=False)]
        
        # Map element values to the sample name
        for _, row in df.iterrows():
            s_name = str(row['Sample']).strip()
            if not s_name: continue
            if s_name not in master_dict:
                master_dict[s_name] = {}
            for col in df.columns:
                if col != 'Sample':
                    val = row[col]
                    # Only update if the value is not already there or if current value is NaN
                    if col not in master_dict[s_name] or pd.isna(master_dict[s_name][col]):
                        master_dict[s_name][col] = val
                    
    if not master_dict: return None
    return pd.DataFrame.from_dict(master_dict, orient='index').rename_axis('Sample').reset_index()

if raw_pasted_text:
    try:
        df_full = parse_and_merge_blocks(raw_pasted_text)
        
        if df_full is not None:
            # Numeric cleaning
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

            # --- 2. PER-SAMPLE PREPARATION ---
            st.subheader("2. Sample Preparation & Parameters")
            
            def get_auto_dil(name):
                match = re.search(r'(\d+)\s?[xX]', str(name))
                return float(match.group(1)) if match else 1.0

            s_list = df_full['Sample'].unique()
            p_df = pd.DataFrame({
                'Sample': s_list, 
                'Mass (g)': 0.5, 
                'Vol (mL)': 500.0, 
                'Dilution': [get_auto_dil(s) for s in s_list], 
                'Moisture (%)': 0.0, 
                'LOI (%)': 0.0
            })
            e_prep = st.data_editor(p_df, hide_index=True, use_container_width=True)
            p_map = e_prep.set_index('Sample').to_dict('index')

            # --- 3. ELEMENT CONFIG ---
            # Detect elements based on column names (e.g., "Fe 238.1")
            detected = sorted(list(set([e for e in element_to_oxide.keys() for c in df_full.columns if c.strip().startswith(f"{e} ")])))
            
            st.subheader("3. Select Oxide/Elemental Mode")
            if detected:
                c_modes = st.columns(min(len(detected), 10))
                modes = {e: c_modes[i % 10].radio(f"**{e}**", ["Elem", "Oxide"], key=f"m_{e}") for i, e in enumerate(detected)}
            else:
                st.warning("No standard elements detected in column headers.")

            # --- 5. CALCULATIONS ---
            results, sd_details = [], []
            for _, row in df_full.iterrows():
                sn = row['Sample']
                pm = p_map.get(sn, {'Mass (g)':0.5, 'Vol (mL)':500.0, 'Dilution':1.0, 'Moisture (%)':0.0, 'LOI (%)':0.0})
                res, sd_res, total_measured = {"Sample": sn}, {"Sample": sn}, 0.0

                for elem in detected:
                    m_cols = [c for c in df_full.columns if c.strip().startswith(f"{elem} ")]
                    vals = row[m_cols].dropna().values
                    if len(vals) > 0:
                        av, sd = np.mean(vals), np.std(vals) if len(vals) > 1 else 0.0
                        # Conversion Factor: (mg/L * L) / (g * 1000) -> mg_metal / mg_sample
                        f = (pm['Vol (mL)']/1000) * pm['Dilution'] / (pm['Mass (g)'] * 1000)
                        perc, sd_perc = (av * f) * 100, (sd * f) * 100
                        
                        label = elem
                        if modes[elem] == "Oxide":
                            form, factor = element_to_oxide[elem]
                            perc, sd_perc, label = perc * factor, sd_perc * factor, form
                        
                        res[f"{label} (%)"] = perc
                        sd_res[f"{label} SD"] = sd_perc
                        total_measured += perc

                res.update({"Moisture (%)": pm['Moisture (%)'], "LOI (%)": pm['LOI (%)'], "Total (%)": total_measured + pm['Moisture (%)'] + pm['LOI (%)']})
                results.append(res)
                sd_details.append(sd_res)

            # --- 6. DISPLAY ---
            st.header("5. Analysis Results")
            df_res = pd.DataFrame(results)
            st.dataframe(df_res, use_container_width=True)
            
            csv = df_res.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "icp_results.csv", "text/csv")

    except Exception as e:
        st.error(f"Error processing data: {e}")
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
st.title("🧪 Clean Multi-Block ICP-OES Calculator")

# --- 1. DATA INPUT ---
st.header("1. Paste Data")
raw_pasted_text = st.text_area("Paste your Excel data here:", height=200)

def parse_and_merge_blocks(text):
    # Split text into blocks where "Sample" starts the line (case insensitive)
    raw_blocks = re.split(r'(?mi)^Sample', text)
    master_dict = {} 
    
    for block in raw_blocks:
        if not block.strip(): continue
        
        # Load block CSV safely
        clean_block = "Sample" + block.strip()
        df = pd.read_csv(io.StringIO(clean_block), sep='\t').dropna(axis=1, how='all')
        
        # Standardize: Rename first column to 'Sample' without shifting data
        df = df.rename(columns={df.columns[0]: 'Sample'})
        
        # Clean: Remove Unit rows (mg/l), literal "Sample" text, and empty entries
        df = df[df['Sample'].notna()]
        df = df[~df['Sample'].astype(str).str.lower().str.contains('mg/l|sample|control|unit', na=False)]
        
        # Map element values to the sample name
        for _, row in df.iterrows():
            s_name = str(row['Sample']).strip()
            if not s_name: continue
            if s_name not in master_dict:
                master_dict[s_name] = {}
            for col in df.columns:
                if col != 'Sample':
                    master_dict[s_name][col] = row[col]
                    
    if not master_dict: return None
    return pd.DataFrame.from_dict(master_dict, orient='index').rename_axis('Sample').reset_index()

if raw_pasted_text:
    try:
        df_full = parse_and_merge_blocks(raw_pasted_text)
        
        if df_full is not None:
            # Numeric cleaning & flag limits (<, >)
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

            # --- 2. PER-SAMPLE PREPARATION ---
            st.subheader("2. Sample Preparation & Parameters")
            
            # Restored Dilution Detection Logic
            def get_auto_dil(name):
                # Catches "10x", "10 x", "10X"
                match = re.search(r'(\d+)\s?[xX]', str(name))
                return float(match.group(1)) if match else 1.0

            s_list = df_full['Sample'].unique()
            p_df = pd.DataFrame({
                'Sample': s_list, 
                'Mass (g)': 0.5, 
                'Vol (mL)': 500.0, 
                'Dilution': [get_auto_dil(s) for s in s_list], 
                'Moisture (%)': 0.0, 
                'LOI (%)': 0.0
            })
            e_prep = st.data_editor(p_df, hide_index=True, use_container_width=True)
            p_map = e_prep.set_index('Sample').to_dict('index')

            # --- 3. ELEMENT CONFIG ---
            detected = sorted([e for e in element_to_oxide.keys() if any(c.strip().startswith(f"{e} ") for c in df_full.columns)])
            st.subheader("3. Select Oxide/Elemental Mode")
            c_modes = st.columns(min(len(detected), 10) if detected else 1)
            modes = {e: c_modes[i % 10].radio(f"**{e}**", ["Elem", "Oxide"], key=f"m_{e}") for i, e in enumerate(detected)}

            # --- 4. MEASUREMENT NOTES ---
            st.subheader("4. Measurement Notes")
            user_notes = st.text_area("Notes for the final report:", "Multi-block analysis.")

            # --- 5. CALCULATIONS ---
            results, sd_details, h_res, h_sd = [], [], {}, {}
            for _, row in df_full.iterrows():
                sn = row['Sample']
                pm = p_map.get(sn, {'Mass (g)':0.5, 'Vol (mL)':500.0, 'Dilution':1.0, 'Moisture (%)':0.0, 'LOI (%)':0.0})
                res, sd_res, total_measured = {"Sample": sn}, {"Sample": sn}, 0.0

                for elem in detected:
                    m_cols = [c for c in df_full.columns if c.strip().startswith(f"{elem} ")]
                    vals = row[m_cols].dropna().values
                    if len(vals) > 0:
                        av, sd = np.mean(vals), np.std(vals) if len(vals) > 1 else 0.0
                        f = (pm['Vol (mL)']/1000) * pm['Dilution'] / (pm['Mass (g)'] * 1000)
                        perc, sd_perc = (av * f) * 100, (sd * f) * 100
                        
                        label = elem
                        if modes[elem] == "Oxide":
                            form, factor = element_to_oxide[elem]
                            perc, sd_perc, label = perc * factor, sd_perc * factor, form
                        
                        res[f"{label} (%)"], sd_res[f"{label} SD"], total_measured = perc, sd_perc, total_measured + perc
                        if any((sn, c) in limit_flags for c in m_cols): h_res[(sn, f"{label} (%)")] = 'background-color: #ffffb3'
                        if perc > 0 and (sd_perc / perc) > 0.10: 
                            h_res[(sn, f"{label} (%)")] = 'background-color: #ffcc99'; h_sd[(sn, f"{label} SD")] = 'background-color: #ff9999'

                res.update({"Moisture (%)": pm['Moisture (%)'], "LOI (%)": pm['LOI (%)'], "Total (%)": total_measured + pm['Moisture (%)'] + pm['LOI (%)']})
                results.append(res); sd_details.append(sd_res)

            # --- 6. DISPLAY ---
            st.header("5. Analysis Results")
            t1, t2, t3 = st.tabs(["📊 Main Results", "📏 SD Verification", "🥧 Visual Charts"])
            with t1:
                df_f = pd.DataFrame(results)
                st.dataframe(df_f.style.format(precision=3).apply(lambda r: [h_res.get((r.Sample, c), '') for c in r.index], axis=1), use_container_width=True)
            with t2:
                st.dataframe(pd.DataFrame(sd_details).style.format(precision=4).apply(lambda r: [h_sd.get((r.Sample, c), '') for c in r.index], axis=1), use_container_width=True)
            with t3:
                for i, r_row in enumerate(results):
                    st.write(f"### {r_row['Sample']}")
                    c1, c2 = st.columns(2)
                    bk = {k: v for k, v in r_row.items() if k not in ['Sample', 'Total (%)']}
                    c1.plotly_chart(px.pie(values=list(bk.values()), names=list(bk.keys()), title="Internal Composition"), key=f"p1_{i}")
                    unk = max(0, 100 - r_row['Total (%)'])
                    c2.plotly_chart(px.pie(values=[r_row['Total (%)'], unk], names=['Measured', 'Unknown'], title="Mass Balance"), key=f"p2_{i}")

            full_csv = f"NOTES: {user_notes}\n\n" + df_f.to_csv(index=False)
            st.download_button("Download Report", full_csv, "icp_report.csv", "text/csv")
    except Exception as e:
        st.error(f"Processing Error: {e}")

st.divider()
st.info(f"**Developer:** [Your Name](https://linkedin.com)")
