import streamlit as st
import pandas as pd
import eurostat
import plotly.express as px

st.set_page_config(page_title="EU Unemployment Dashboard", layout="wide")

EU27 = [
    'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU',
    'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE'
]

COUNTRY_NAMES = {
    'AT': 'Austria', 'BE': 'Belgium', 'BG': 'Bulgaria', 'HR': 'Croatia', 'CY': 'Cyprus',
    'CZ': 'Czechia', 'DK': 'Denmark', 'EE': 'Estonia', 'FI': 'Finland', 'FR': 'France',
    'DE': 'Germany', 'GR': 'Greece', 'HU': 'Hungary', 'IE': 'Ireland', 'IT': 'Italy',
    'LV': 'Latvia', 'LT': 'Lithuania', 'LU': 'Luxembourg', 'MT': 'Malta', 'NL': 'Netherlands',
    'PL': 'Poland', 'PT': 'Portugal', 'RO': 'Romania', 'SK': 'Slovakia', 'SI': 'Slovenia',
    'ES': 'Spain', 'SE': 'Sweden'
}


@st.cache_data(ttl=86400)
def load_data():
    df = eurostat.get_data_df('une_rt_a')

    geo_col = [c for c in df.columns if 'geo' in c.lower()][0]

    filters = {}
    if 'age' in df.columns:
        filters['age'] = 'Y15-74'
    if 'sex' in df.columns:
        filters['sex'] = 'T'
    if 'unit' in df.columns:
        filters['unit'] = 'PC_ACT'

    df_f = df.copy()
    for col, val in filters.items():
        if val in df_f[col].unique():
            df_f = df_f[df_f[col] == val]

    year_cols = [c for c in df_f.columns if str(c).strip().isdigit()]

    df_long = df_f.melt(
        id_vars=[geo_col],
        value_vars=year_cols,
        var_name='year',
        value_name='unemployment_rate'
    )
    df_long = df_long.rename(columns={geo_col: 'country'})
    df_long['year'] = df_long['year'].astype(int)
    df_long = df_long.dropna(subset=['unemployment_rate'])

    df_eu = df_long[df_long['country'].isin(EU27)].copy()
    df_eu['country_name'] = df_eu['country'].map(COUNTRY_NAMES)
    df_eu = df_eu.sort_values(['country', 'year'])

    return df_eu


df_eu = load_data()

# ---------- Header ----------
st.title("EU Unemployment: The Gap That Never Closed")
st.markdown(
    "**Spain's unemployment rate has stayed 3-4x Czechia's for over a decade — "
    "even as the EU average fell by a third since 2003.**"
)

# ---------- KPIs ----------
latest_year = int(df_eu['year'].max())
first_year = int(df_eu['year'].min())

latest_data = df_eu[df_eu['year'] == latest_year]
first_avg = df_eu[df_eu['year'] == first_year]['unemployment_rate'].mean()
latest_avg = latest_data['unemployment_rate'].mean()

highest = latest_data.loc[latest_data['unemployment_rate'].idxmax()]
lowest = latest_data.loc[latest_data['unemployment_rate'].idxmin()]
gap = highest['unemployment_rate'] - lowest['unemployment_rate']

col1, col2, col3, col4 = st.columns(4)
col1.metric(f"EU Avg ({latest_year})", f"{latest_avg:.1f}%", f"{latest_avg - first_avg:+.1f} pp vs {first_year}")
col2.metric(f"Highest ({latest_year})", f"{highest['country_name']}", f"{highest['unemployment_rate']:.1f}%")
col3.metric(f"Lowest ({latest_year})", f"{lowest['country_name']}", f"{lowest['unemployment_rate']:.1f}%")
col4.metric("Gap (max - min)", f"{gap:.1f} pp")

st.divider()

# ---------- Country selector + line chart ----------
st.subheader("Trend Over Time")
default_countries = ['Spain', 'Czechia', 'Germany', 'Greece', 'France']
all_names = sorted(COUNTRY_NAMES.values())

selected = st.multiselect(
    "Select countries to compare",
    options=all_names,
    default=[c for c in default_countries if c in all_names]
)

if selected:
    subset = df_eu[df_eu['country_name'].isin(selected)]
    fig_line = px.line(
        subset, x='year', y='unemployment_rate', color='country_name',
        labels={'unemployment_rate': 'Unemployment rate (%)', 'year': 'Year', 'country_name': 'Country'},
        title='Unemployment Rate by Country'
    )
    fig_line.update_traces(line_width=3)
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("Select at least one country above.")

# ---------- Bar chart ----------
st.subheader(f"Ranking — {latest_year}")
latest_sorted = latest_data.sort_values('unemployment_rate', ascending=False)
fig_bar = px.bar(
    latest_sorted, x='country_name', y='unemployment_rate',
    labels={'unemployment_rate': 'Unemployment rate (%)', 'country_name': 'Country'},
    color='unemployment_rate', color_continuous_scale='Reds'
)
fig_bar.update_layout(xaxis_title=None)
st.plotly_chart(fig_bar, use_container_width=True)

# ---------- Heatmap ----------
st.subheader("Heatmap — All Countries, All Years")
pivot = df_eu.pivot(index='country_name', columns='year', values='unemployment_rate')
pivot = pivot.loc[pivot[latest_year].sort_values(ascending=False).index]

fig_heat = px.imshow(
    pivot,
    labels=dict(x='Year', y='Country', color='Unemployment (%)'),
    color_continuous_scale='Reds',
    aspect='auto'
)
fig_heat.update_layout(height=700)
st.plotly_chart(fig_heat, use_container_width=True)

# ---------- Footer ----------
st.caption("Data source: Eurostat (une_rt_a) — annual unemployment rate, age 15-74, % of active population.")
