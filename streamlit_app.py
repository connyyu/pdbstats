import streamlit as st
import altair as alt
import pandas as pd
import requests
import urllib.parse

st.set_page_config(
    page_title='PDB Statistics Dashboard',
    page_icon=':bar_chart:',
)

EXPERIMENTAL_METHODS = [
    "EM", "X-ray", "NMR", "Neutron", "Multiple methods", "Other"
]

# Mapping for short names to full names
display_mapping = {
    "EM": "Electron Microscopy",
    "X-ray": "X-ray Crystallography",
    "NMR": "Nuclear Magnetic Resonance",
    "Neutron": "Neutron Diffraction",
    "Multiple methods": "Multiple Methods",
    "Other": "Other Techniques"
}

def fetch_data_for_method(method):
    """Fetch structure count by year for a given experimental method."""
    query = {
        "query": {
            "type": "group",
            "nodes": [
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_entry_info.experimental_method",
                        "operator": "exact_match",
                        "value": method
                    }
                }
            ],
            "logical_operator": "or"
        },
        "return_type": "entry",
        "request_options": {
            "paginate": {"rows": 0},
            "facets": [
                {
                    "name": "Release Date",
                    "aggregation_type": "date_histogram",
                    "attribute": "rcsb_accession_info.initial_release_date",
                    "interval": "year",
                    "min_interval_population": 1,
                    "facets": [
                        {
                            "name": "Experimental Method",
                            "aggregation_type": "terms",
                            "attribute": "rcsb_entry_info.experimental_method",
                            "min_interval_population": 1
                        }
                    ]
                }
            ]
        }
    }

    # URL encode the JSON query
    encoded_query = urllib.parse.quote(str(query).replace("'", '"'))
    url = f"https://search.rcsb.org/rcsbsearch/v2/query?json={encoded_query}"
    
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch data for {method}. Status Code: {response.status_code}")
        return None

def process_data():
    """Fetch and process PDB data for all methods."""
    records = []
    for method in EXPERIMENTAL_METHODS:
        data = fetch_data_for_method(method)
        if not data or "facets" not in data:
            continue

        for year_bucket in data["facets"][0].get("buckets", []):
            year = int(year_bucket["label"])
            for method_bucket in year_bucket.get("facets", [])[0].get("buckets", []):
                technique = method_bucket["label"]
                count = method_bucket["population"]
                records.append({
                    "Year": year,
                    "Technique": technique,  # Short name
                    "Technique Full": display_mapping.get(technique, technique),  # Full name
                    "Count": count
                })

    return pd.DataFrame(records)

@st.cache_data
def get_pdb_data():
    """Fetch and cache PDB data."""
    pdb_df = process_data()
    return pdb_df, pdb_df['Year'].min(), pdb_df['Year'].max()

pdb_df, min_value, max_value = get_pdb_data()

# -----------------------------------------------------------------------------

'''
# :bar_chart: PDB Statistics Dashboard

Number of macromolecular structures determined by various experimental techniques,
based on information from the [RCSB PDB](https://www.rcsb.org/statistics/growth/experimental-method) database.

'''

if pdb_df.empty:
    st.error("No data available. Please try again later.")
else:
    from_year, to_year = st.slider(
        'Select the range of release year:',
        min_value=min_value,
        max_value=max_value,
        value=[2000, max_value-1])

    # Unique short technique names
    techniques = sorted(pdb_df['Technique'].unique())

    # Multiselect shows only short names
    selected_techniques = st.multiselect(
        'Select the experimental technique(s):',
        techniques,
        default=["X-ray", "EM", "NMR"]
    )

    # Filter the data
    filtered_pdb_df = pdb_df[
        (pdb_df['Technique'].isin(selected_techniques)) &
        (pdb_df['Year'] <= to_year) &
        (pdb_df['Year'] >= from_year)
    ]

    st.markdown("<h1 style='font-size: 30px;'>Structures Determined by Different Techniques</h1>", unsafe_allow_html=True)

    # Chart uses full names in the legend
    chart = (
        alt.Chart(filtered_pdb_df)
        .mark_line()
        .encode(
            x=alt.X("Year:O", title="Year"),
            y=alt.Y("Count:Q", title="Structures released per year"),
            color=alt.Color("Technique Full:N", legend=alt.Legend(title="Techniques", orient="bottom",
                                                                  titleFontSize=12, labelFontSize=12, columns=2))
        )
    )

    st.altair_chart(chart, use_container_width=True)

    first_year = filtered_pdb_df[filtered_pdb_df['Year'] == from_year]
    last_year = filtered_pdb_df[filtered_pdb_df['Year'] == to_year]

    st.subheader(f'Structures determined in {to_year}, changes from {from_year}', divider='gray')

    cols = st.columns(3)

    for i, technique in enumerate(selected_techniques):
        col = cols[i % len(cols)]

        with col:
            first_count = first_year[first_year['Technique'] == technique]['Count'].sum()
            last_count = last_year[last_year['Technique'] == technique]['Count'].sum()

            if first_count == 0:
                growth = 'n/a'
                delta_color = 'off'
                delta_value = 0
            else:
                growth = f'{((last_count - first_count) / first_count)*100:,.2f} %'
                delta_color = "normal"

            st.metric(
                label=f'{technique} Structures',
                value=f'{last_count:,}',
                delta=growth,
                delta_color=delta_color
            )

st.markdown("""
    <a href='https://github.com/connyyu' target='_blank'>
        <img src='https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Octicons-mark-github.svg/1024px-Octicons-mark-github.svg.png' 
        style='position: fixed; bottom: 5%; left: 10%; transform: translateX(-50%); width: 30px; height: 30px;'/>
    </a>
""", unsafe_allow_html=True)


