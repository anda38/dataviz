import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st



# --------------------
# Streamlit config
# --------------------
st.set_page_config(
    page_title="APL Médecins généralistes – France (2023)",
    layout="wide"
)

st.title("Accessibilité potentielle localisée (APL)")
st.subheader("Médecins généralistes – France, 2023")


# --------------------
# Data loading (cached)
# --------------------
@st.cache_data
def load_apl_data():
    xls = pd.ExcelFile("data/aplg.xlsx")
    df = pd.read_excel(xls, sheet_name=2, skiprows=8)

    df["Code commune INSEE"] = df["Code commune INSEE"].astype(str)
    df["Departement"] = df["Code commune INSEE"].str[:2]

    df["APL aux médecins généralistes"] = pd.to_numeric(
        df["APL aux médecins généralistes"],
        errors="coerce"
    )

    return df


@st.cache_data
def load_communes():
    gdf = gpd.read_file("data/admincarto/livraison/COMMUNE.shp")
    gdf["INSEE_COM"] = gdf["INSEE_COM"].astype(str)
    return gdf


@st.cache_data
def load_departements():
    gdf = gpd.read_file(
        "data/admincarto/livraison/DEPARTEMENT.shp"
    )[["INSEE_DEP", "NOM", "geometry"]]

    gdf["geometry"] = gdf["geometry"].simplify(
        tolerance=1000, preserve_topology=True
    )

    return gdf


generaliste_2023 = load_apl_data()
communes = load_communes()
departement = load_departements()


# --------------------
# Commune-level map (matplotlib)
# --------------------
st.header("Carte par commune")

gdf_communes = communes.merge(
    generaliste_2023,
    left_on="INSEE_COM",
    right_on="Code commune INSEE",
    how="left"
)

fig, ax = plt.subplots(figsize=(8, 8))

gdf_communes.plot(
    column="APL aux médecins généralistes",
    scheme="quantiles",
    k=5,
    cmap="viridis",
    linewidth=0,
    legend=True,
    ax=ax,
    missing_kwds={
        "color": "lightgrey",
        "label": "Données manquantes"
    },
    legend_kwds={
        "title": "APL\n(consultations accessibles\npar habitant)",
        "loc": "lower left"
    }
)

ax.set_title(
    "Accessibilité potentielle localisée (APL)\n"
    "aux médecins généralistes par commune (France, 2023)",
    fontsize=12,
    fontweight="bold"
)

ax.axis("off")

st.pyplot(fig)


# --------------------
# Department aggregation
# --------------------
st.header("Carte par département")

dept_stats = (
    generaliste_2023
    .groupby("Departement", as_index=False)
    ["APL aux médecins généralistes"]
    .mean()
)

gdf_dep = departement.merge(
    dept_stats,
    left_on="INSEE_DEP",
    right_on="Departement",
    how="left"
)

gdf_dep = gdf_dep.to_crs(epsg=4326)


# --------------------
# Department map (Plotly)
# --------------------
fig_dep = px.choropleth_map(
    gdf_dep,
    geojson=gdf_dep.__geo_interface__,
    locations="INSEE_DEP",
    featureidkey="properties.INSEE_DEP",
    color="APL aux médecins généralistes",
    color_continuous_scale="Viridis",
    center={"lat": 46.6, "lon": 2.5},
    zoom=4.8,
    map_style="carto-positron",
    hover_name="NOM"
)

fig_dep.update_layout(
    title={
        "text": "Accessibilité potentielle localisée (APL)<br>"
                "aux médecins généralistes par département (France, 2023)",
        "x": 0.5
    },
    margin={"r": 0, "t": 50, "l": 0, "b": 0}
)

st.plotly_chart(fig_dep, use_container_width=True)
