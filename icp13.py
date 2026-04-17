import streamlit as st
import pandas as pd
import io
import numpy as np
import plotly.express as px
import re

# Extended oxide conversion dictionary (B to U)
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
st.title("🧪 Automatic ICP-OES Result Calculator")

# --- STEP 1: PASTE DATA ---
st.header("1. Data Input")
raw_data = st.text_area("Paste Excel data (headers + unit row):", height=150)

if raw_data:
    try:
        df_input = pd.read_csv(io.StringIO(raw_data), sep='\t').dropna(axis=1, how='all')
        
        # Unit row removal
        if not df_input.empty:
            first_row_str = df_input.iloc[0].astype(str).str.lower()
            if any(first_row_str.str.contains('mg/l')):
                df_input = df_input.iloc[1:].reset_index(drop=True)

        # SKIP CONTROL ROWS
        df_filtered = df_input[~df_input['Sample'].str.contains('Control', case=False, na=False)].copy()

        # Clean symbols and parse numbers
        limit_flags = []
        for col in df_filtered.columns:
            if col != 'Sample':
                def clean_and_tag(val, sample, cname):
                    if isinstance(val, str) and any(s in val for s in ['<', '>']):
                        limit_flags.append((sample, cname))
                        return val.replace('<', '').replace('>', '').strip()
                    return val
                df_filtered[col] = df_filtered.apply(lambda r: clean_and_tag(r[col], r['Sample'], col), axis=1)
                df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')

        # PER-SAMPLE PREP TABLE (Includes Mass, Volume, Moisture, LOI)
        st.subheader("2. Sample Details")
        def get_auto_dilution(name):
            match = re.search(r'(\d+)[xX]', str(name))
            return float(match.group(1)) if match else 1.0

        samples = df_filtered['Sample'].unique()
        prep_df = pd.DataFrame({
            'Sample': samples,
            'Mass (g)': [0.1] * len(samples),
            'Volume (mL)': [50.0] * len(samples),
            'Dilution': [get_auto_dilution(s) for s in samples],
            'Moisture (%)': [0.0] * len(samples),
            'LOI (%)': [0.0] * len(samples)
        })
        
        edited_prep = st.data_editor(prep_df, hide_index=True, use_container_width=True)
        prep_map = edited_prep.set_index('Sample').to_dict('index')

        # Element Configuration
        detected = sorted([e for e in element_to_oxide.keys() if any(c.strip().startswith(f"{e} ") for c in df_filtered.columns)])
        st.subheader("3. Select Oxide/Elemental Display")
        config_cols = st.columns(min(len(detected), 8) if detected else 1)
        element_modes = {e: config_cols[i % 8].radio(f"**{e}**", ["Elem", "Oxide"], key=f"m_{e}") for i, e in enumerate(detected)}

        # Measurement Notes
        st.subheader("4. Measurement Notes")
        meas_notes = st.text_area("Add internal notes about this measurement run:", "Standard ICP-OES run.")

        # PROCESS RESULTS
        results, sd_details, highlights, sd_highlights = [], [], {}, {}
        for _, row in df_filtered.iterrows():
            s_name = row['Sample']
            p = prep_map.get(s_name, {'Mass (g)': 0.3, 'Volume (mL)': 250.0, 'Dilution': 1.0, 'Moisture (%)': 0.0, 'LOI (%)': 0.0})
            res, sd_res, row_total = {"Sample": s_name}, {"Sample": s_name}, 0.0

            for elem in detected:
                m_cols = [c for c in df_filtered.columns if c.strip().startswith(f"{elem} ")]
                vals = row[m_cols].dropna().values
                
                if len(vals) > 0:
                    avg_v, std_v = np.mean(vals), np.std(vals) if len(vals) > 1 else 0.0
                    factor = (p['Volume (mL)']/1000) * p['Dilution'] / (p['Mass (g)'] * 1000)
                    perc, sd_perc = (avg_v * factor) * 100, (std_v * factor) * 100
                    
                    label = elem
                    if element_modes[elem] == "Oxide":
                        formula, f_ox = element_to_oxide[elem]
                        perc, sd_perc, label = perc * f_ox, sd_perc * f_ox, formula

                    res[f"{label} (%)"] = perc
                    sd_res[f"{label} SD"] = sd_perc
                    row_total += perc
                    
                    # Highlight logic
                    key_res = (s_name, f"{label} (%)")
                    key_sd = (s_name, f"{label} SD")
                    if any((s_name, c) in limit_flags for c in m_cols):
                        highlights[key_res] = 'background-color: #ffffb3'
                    if perc > 0 and (sd_perc / perc) > 0.10:
                        highlights[key_res] = 'background-color: #ffcc99'
                        sd_highlights[key_sd] = 'background-color: #ff9999; color: black; font-weight: bold'

            res.update({"Moisture (%)": p['Moisture (%)'], "LOI (%)": p['LOI (%)'], "Total (%)": row_total + p['Moisture (%)'] + p['LOI (%)']})
            results.append(res); sd_details.append(sd_res)

        # FINAL ANALYSIS
        st.header("5. Results & Visualization")
        tab1, tab2, tab3 = st.tabs(["📊 Main Results", "📏 SD Details (Verification)", "🥧 Sample Charts"])
        
        with tab1:
            df_final = pd.DataFrame(results)
            st.dataframe(df_final.style.format(precision=3).apply(lambda s: [highlights.get((s.Sample, c), '') for c in s.index], axis=1), use_container_width=True)
            st.info("💡 **Yellow**: Near detection limit. **Orange**: High wavelength deviation (check SD).")
        
        with tab2:
            st.write("Wavelength standard deviations. **Red** flags indicate significantly weird data consistency.")
            df_sd = pd.DataFrame(sd_details)
            st.dataframe(df_sd.style.format(precision=4).apply(lambda s: [sd_highlights.get((s.Sample, c), '') for c in s.index], axis=1), use_container_width=True)

        with tab3:
            for s_res in results:
                plot_vals = {k: v for k, v in s_res.items() if k not in ['Sample', 'Total (%)']}
                if sum(plot_vals.values()) > 0:
                    st.plotly_chart(px.pie(values=list(plot_vals.values()), names=list(plot_vals.keys()), title=f"Sample: {s_res['Sample']}"), use_container_width=True)

        # Download with Notes
        final_csv_str = df_final.to_csv(index=False)
        full_output = f"NOTE: {meas_notes}\n\n" + final_csv_str
        st.download_button("Download Results + Notes", full_output, "icp_final_report.csv", "text/csv")

    except Exception as e:
        st.error(f"Error: {e}")

st.divider()
#st.info(f"**Developer:** [Your Name](https://linkedin.com)")
