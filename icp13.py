import streamlit as st
import pandas as pd
import re
import io

def clean_value(val):
    """Removes < or > signs and converts to float."""
    if pd.isna(val) or val == "": return 0.0
    cleaned = str(val).replace('<', '').replace('>', '').strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def get_dilution(name):
    """Detects '10x' or '10 x' and returns the factor."""
    match = re.search(r'(\d+)\s*x', str(name), re.IGNORECASE)
    return float(match.group(1)) if match else 1.0

st.title("🧪 ICP Result Processor")
st.write("Upload your ICP data or paste it below to calculate percentages.")

# Text input for the data
raw_data = st.text_area("Paste ICP Table Here", height=300)

if raw_data:
    # Use a separator that handles multiple spaces/tabs
    df = pd.read_csv(io.StringIO(raw_data), sep=r'\t|\s{2,}', engine='python', skipblanklines=True)
    
    # Identify headers and drop 'mg/l' rows
    df = df[df['Sample'] != 'mg/l']
    
    # Filter out 'control' samples
    df = df[~df['Sample'].str.contains('control', case=False, na=False)]
    
    # Group by Sample and process
    results = []
    for name, group in df.groupby('Sample'):
        dilution = get_dilution(name)
        
        # Melt and clean values
        melted = group.melt(id_vars=['Sample'], var_name='Element', value_name='Value')
        melted['CleanValue'] = melted['Value'].apply(clean_value) * dilution
        
        # Sum by element (auto-concatenation)
        element_sums = melted.groupby('Element')['CleanValue'].sum()
        total_mass = element_sums.sum()
        
        # Calculate percentages
        if total_mass > 0:
            percentages = (element_sums / total_mass * 100).to_dict()
        else:
            percentages = {el: 0.0 for el in element_sums.index}
            
        percentages['Sample'] = name
        results.append(percentages)

    final_df = pd.DataFrame(results).set_index('Sample')
    
    st.subheader("Processed Percentages (%)")
    st.dataframe(final_df.style.format("{:.2f}%"))
    
    # Download option
    csv = final_df.to_csv().encode('utf-8')
    st.download_button("Download CSV", csv, "icp_percentages.csv", "text/csv")
