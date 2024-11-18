import streamlit as st
import pandas as pd

# Dictionary for element to oxide conversion with a wider range
element_to_oxide = {
    'Na': ('Na2O', 1.348),
    'Mg': ('MgO', 1.6583),
    'Al': ('Al2O3', 1.8895),
    'Si': ('SiO2', 2.1393),
    'P': ('P2O5', 2.291),
    'S': ('SO3', 2.499),
    'Cl': ('Cl2O7', 2.628),
    'K': ('K2O', 1.2047),
    'Ca': ('CaO', 1.3992),
    'Sc': ('Sc2O3', 1.533),
    'Ti': ('TiO2', 1.668),
    'V': ('V2O5', 1.785),
    'Cr': ('Cr2O3', 1.461),
    'Mn': ('MnO2', 1.582),
    'Fe': ('Fe2O3', 1.4297),
    'Co': ('CoO', 1.271),
    'Ni': ('NiO', 1.273),
    'Cu': ('CuO', 1.252),
    'Zn': ('ZnO', 1.245),
    # Add more elements as needed
}

# App configuration and title
st.set_page_config(page_title="ICP-OES Result Calculator", layout="wide")
st.title("Enhanced ICP-OES Result Calculator")

# Sidebar inputs for sample preparation
with st.sidebar:
    st.header("Sample Preparation")
    volume = st.number_input("Volume of sample solution (mL)", min_value=0.0, step=0.1, format="%.2f")
    initial_mass = st.number_input("Initial mass of sample (g)", min_value=0.0, step=0.1, format="%.2f") * 1000  # Convert g to mg

# Initialize session state for selected elements
if 'selected_elements_data' not in st.session_state:
    st.session_state.selected_elements_data = {}

# Display the periodic table with element buttons
st.header("Select Elements")
cols = st.columns(18)
elements = [e for e in element_to_oxide.keys() if e not in ['H', 'Li', 'O', 'Be', 'C', 'N']]

for i, element in enumerate(elements):
    with cols[i % 18]:
        if st.button(element, key=f"btn_{element}"):
            if element not in st.session_state.selected_elements_data:
                # Add new elements to the top of the dictionary
                st.session_state.selected_elements_data = {
                    element: {"concentration": 0.0, "display_as": "Elemental"},
                    **st.session_state.selected_elements_data
                }

# Editable data table in the sidebar for user inputs
with st.sidebar:
    st.subheader("Edit Selected Elements")
    if st.session_state.selected_elements_data:
        for element, data in st.session_state.selected_elements_data.items():
            st.write(f"### {element}")
            st.session_state.selected_elements_data[element]["concentration"] = st.number_input(
                f"{element} Concentration (mg/mL)",
                min_value=0.0,
                value=data["concentration"],
                step=0.01,
                format="%.2f",
                key=f"concentration_{element}"
            )
            st.session_state.selected_elements_data[element]["display_as"] = st.radio(
                f"Display {element} as:",
                ["Elemental", "Oxide"],
                index=0 if data["display_as"] == "Elemental" else 1,
                key=f"display_{element}"
            )
            if st.button(f"Remove {element}", key=f"remove_{element}"):
                del st.session_state.selected_elements_data[element]

    # Add inputs for moisture content and LOI
    st.write("### Additional Data")
    moisture_content = st.number_input("Moisture Content (%)", min_value=0.0, step=0.1, format="%.2f")
    loi = st.number_input("Loss on Ignition (LOI) (%)", min_value=0.0, step=0.1, format="%.2f")

# Display results table
st.subheader("Results for Selected Elements")
if st.session_state.selected_elements_data:
    data = [{"Element": elem, "Concentration (mg/mL)": data["concentration"], "Display As": data["display_as"]}
            for elem, data in st.session_state.selected_elements_data.items() if data["concentration"] > 0]
    if data:
        df = pd.DataFrame(data)
        
        # Correct calculation for percentage concentration
        df['Concentration (%)'] = (df['Concentration (mg/mL)'] * (volume / 1000)) / (initial_mass / 100)

        # Apply oxide conversion where selected
        df['Converted'] = df.apply(
            lambda row: element_to_oxide[row['Element']][0] if row['Display As'] == "Oxide" else row['Element'],
            axis=1
        )
        df['Concentration (%) (Converted)'] = df.apply(
            lambda row: row['Concentration (%)'] * element_to_oxide[row['Element']][1]
            if row['Display As'] == "Oxide" else row['Concentration (%)'], axis=1
        )

        # Add rows for moisture content and LOI
        if moisture_content > 0:
            df = pd.concat([df, pd.DataFrame([{
                'Element': 'Moisture Content',
                'Converted': 'N/A',
                'Concentration (%) (Converted)': moisture_content
            }])])

        if loi > 0:
            df = pd.concat([df, pd.DataFrame([{
                'Element': 'LOI',
                'Converted': 'N/A',
                'Concentration (%) (Converted)': loi
            }])])

        # Calculate the total percentage
        total_percentage = df['Concentration (%) (Converted)'].sum()
        total_row = pd.DataFrame([{
            'Element': 'Total',
            'Converted': 'N/A',
            'Concentration (%) (Converted)': total_percentage
        }])
        df = pd.concat([df, total_row])

        # Display the results table with better formatting
        st.dataframe(
            df[['Element', 'Converted', 'Concentration (%) (Converted)']].style.format(
                {"Concentration (%) (Converted)": "{:.2f}%"}
            )
        )

        # Download button for CSV export
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Results as CSV",
            data=csv,
            file_name="ICP-OES_results.csv",
            mime="text/csv"
        )
else:
    st.info("Select elements and input concentrations to see results.")

