import streamlit as st
import pandas as pd
import requests
import os

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='PDB Structure Dashboard',
    page_icon=':microscope:',  # This is an emoji shortcode. Could be a URL too.
)

# ----------------------------------------------------------------------------- 
# Declare some useful functions.

def fetch_data_from_api(techniques, year_range):
    """Fetch structure counts by technique from the PDBe API."""
    data = []
    BASE_URL_PDBe = "https://www.ebi.ac.uk/pdbe/search/pdb/select"
    
    for technique in techniques:
        for year in year_range:
            query = {
                "q": f'release_year:"{year}" AND experimental_method:"{technique}"',  # Correct query format
                "wt": "json"
            }
            # Send the GET request
            response = requests.get(BASE_URL_PDBe, params=query)
            
            if response.status_code == 200:
                count = response.json().get("response", {}).get("numFound", 0)
            else:
                count = 0

            data.append({"Year": year, "Technique": technique, "Count": count})
    
    return data

@st.cache_data
def get_pdb_data_from_csv_or_api():
    """Check if data exists in CSV and fetch missing data from API if needed."""
    techniques = ["X-ray diffraction", "Solution NMR", "Electron Microscopy"]
    year_range = range(1971, 2025)  # Adjust the range as needed
    csv_file = 'pdb_data.csv'
    
    # Check if the CSV file exists
    if os.path.exists(csv_file):
        # Read the existing CSV
        pdb_df = pd.read_csv(csv_file)
        existing_years = pdb_df['Year'].unique()
        
        # Identify missing years
        missing_years = [year for year in year_range if year not in existing_years]
        
        if missing_years:
            # Fetch data for missing years from API
            missing_data = fetch_data_from_api(techniques, missing_years)
            new_data_df = pd.DataFrame(missing_data)
            
            # Append the new data to the existing data
            pdb_df = pd.concat([pdb_df, new_data_df], ignore_index=True)
            pdb_df.to_csv(csv_file, index=False)  # Update the CSV with the new data
    else:
        # If CSV file does not exist, fetch all data from the API
        pdb_data = fetch_data_from_api(techniques, year_range)
        pdb_df = pd.DataFrame(pdb_data)
        pdb_df.to_csv(csv_file, index=False)  # Save to CSV for future use
    
    return pdb_df, pdb_df['Year'].min(), pdb_df['Year'].max()

pdb_df, min_value, max_value = get_pdb_data_from_csv_or_api()

# ----------------------------------------------------------------------------- 
# Draw the actual page

# Set the title that appears at the top of the page.
'''
# :microscope: PDB Structure Dashboard

Browse structure data from the [Protein Data Bank (PDB)](https://www.rcsb.org/) and [PDBe](https://www.ebi.ac.uk/pdbe/). This dataset contains
information on the number of structures solved by different experimental techniques over time.
'''

# Add some spacing
'' 
''

from_year, to_year = st.slider(
    'Which years are you interested in?',
    min_value=min_value,
    max_value=max_value,
    value=[2000, max_value])

if pdb_df.empty:
    st.error("No data available. Please check the PDB API query format or try again later.")
else:
    techniques = pdb_df['Technique'].unique()

    if not len(techniques):
        st.warning("Select at least one technique")

    selected_techniques = st.multiselect(
        'Which experimental techniques would you like to view?',
        techniques,
        ['X-ray diffraction', 'Solution NMR', 'Electron Microscopy'])

    ''
    ''
    ''

    # Filter the data
    filtered_pdb_df = pdb_df[(
        pdb_df['Technique'].isin(selected_techniques)) 
        & (pdb_df['Year'] <= to_year)
        & (from_year <= pdb_df['Year'])
    ]

    st.header('Structures Solved Over Time', divider='gray')

    ''

    st.line_chart(
        filtered_pdb_df,
        x='Year',
        y='Count',
        color='Technique',
    )

    ''
    ''

    first_year = pdb_df[pdb_df['Year'] == from_year]
    last_year = pdb_df[pdb_df['Year'] == to_year]

    st.header(f'Structures released in {to_year}', divider='gray')

    ''

    cols = st.columns(4)

    for i, technique in enumerate(selected_techniques):
        col = cols[i % len(cols)]

        with col:
            first_count = first_year[first_year['Technique'] == technique]['Count'].iat[0] if not first_year.empty else 0
            last_count = last_year[last_year['Technique'] == technique]['Count'].iat[0] if not last_year.empty else 0

            if first_count == 0:
                growth = 'n/a'
                delta_color = 'off'
            else:
                growth = f'{last_count / first_count:,.2f}x'
                delta_color = 'normal'

            st.metric(
                label=f'{technique} Structures',
                value=f'{last_count:,}',
                delta=growth,
                delta_color=delta_color
            )
