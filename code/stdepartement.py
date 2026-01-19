
import geopandas as gpd
import pandas as pd
import streamlit as st
import plotly.express as px


st.set_page_config(
    page_title="APL – Médecins généralistes (2023)",
    layout="wide"
)

st.title("Accessibilité potentielle localisée (APL)")
st.caption("Médecins généralistes – France métropolitaine (2023)")


@st.cache_data
def load_apl():
    df = pd.read_excel(
        f"data/aplg.xlsx",
        sheet_name=2,
        skiprows=8
    )

    df = df.dropna(subset=["Code commune INSEE"])
    df["Code commune INSEE"] = df["Code commune INSEE"].astype(str)
    df["Departement"] = df["Code commune INSEE"].str[:2]

    df["APL aux médecins généralistes"] = pd.to_numeric(
        df["APL aux médecins généralistes"],
        errors="coerce"
    )

    return df



@st.cache_data
def load_communes():
    gdf = gpd.read_file(
        f"data/admincarto/livraison/COMMUNE.shp"
    )

    gdf["INSEE_COM"] = gdf["INSEE_COM"].astype(str)

    gdf = gdf.to_crs(epsg=2154)
    gdf["geometry"] = gdf["geometry"].simplify(
        tolerance=100,
        preserve_topology=True
    )

    return gdf.to_crs(epsg=4326)


# =================================================
# LOAD ARRONDISSEMENTS (PARIS)
# =================================================
@st.cache_data
def load_arrondissements():
    gdf = gpd.read_file(
        f"data/admincarto/livraison/ARRONDISSEMENT_MUNICIPAL.shp"
    )

    gdf["INSEE_ARM"] = gdf["INSEE_ARM"].astype(str)

    gdf = gdf.to_crs(epsg=2154)
    gdf["geometry"] = gdf["geometry"].simplify(
        tolerance=10,
        preserve_topology=True
    )

    return gdf.to_crs(epsg=4326)


# =================================================
# LOAD DEPARTEMENTS (NOMS)
# =================================================
@st.cache_data
def load_departements():
    gdf = gpd.read_file(
        f"data/admincarto/livraison/DEPARTEMENT.shp"
    )[["INSEE_DEP", "NOM"]]

    gdf["INSEE_DEP"] = gdf["INSEE_DEP"].astype(str)
    return gdf


# =================================================
# LOAD ALL DATA
# =================================================
generaliste_2023 = load_apl()
communes = load_communes()
arrondissements = load_arrondissements()
departements = load_departements()

dep_name_map = dict(zip(departements["INSEE_DEP"], departements["NOM"]))


# =================================================
# SELECT DEPARTMENT (FILTER 96 / 97 / NA)
# =================================================
deps = (
    generaliste_2023["Departement"]
    .dropna()
    .unique()
)

# suppression DOM et codes non souhaités
deps = [
    d for d in deps
    if d not in ["96", "97"] and len(d) == 2
]

deps = sorted(deps)

DEP_CODE = st.selectbox(
    "Choisissez un département",
    deps,
    index=deps.index("75") if "75" in deps else 0
)

hide_na = st.checkbox(
    "Masquer les zones sans données",
    value=True
)

# =================================================
# PLOT FUNCTION
# =================================================
def plot_map(gdf, title, zoom, hover_col):
    fig = px.choropleth_map(
        gdf,
        geojson=gdf.geometry,
        locations=gdf.index,
        color="APL aux médecins généralistes",
        color_continuous_scale="Viridis",
        map_style="carto-positron",
        hover_name=hover_col,
        center={
            "lat": gdf.geometry.centroid.y.mean(),
            "lon": gdf.geometry.centroid.x.mean()
        },
        zoom=zoom
    )

    fig.update_traces(
        hovertemplate=
        "<b>%{hovertext}</b><br>"
        "APL moyenne : %{z:.2f}<extra></extra>"
    )

    fig.update_layout(
        title={"text": title, "x": 0.5},
        margin={"r": 0, "t": 50, "l": 0, "b": 0}
    )

    return fig


# =================================================
# PARIS — ARRONDISSEMENTS
# =================================================
if DEP_CODE == "75":

    st.subheader("Paris – arrondissements municipaux")

    apl_paris = generaliste_2023[
        generaliste_2023["Code commune INSEE"].str.startswith("751")
    ]

    arr_paris = arrondissements[
        arrondissements["INSEE_ARM"].str.startswith("751")
    ]

    gdf = arr_paris.merge(
        apl_paris,
        left_on="INSEE_ARM",
        right_on="Code commune INSEE",
        how="left"
    )

    if hide_na:
        gdf = gdf.dropna(subset=["APL aux médecins généralistes"])

    fig = plot_map(
        gdf,
        title="APL moyenne par arrondissement",
        zoom=11,
        hover_col="NOM"   # arrondissement
    )

    st.plotly_chart(fig, use_container_width=True)

# =================================================
# OTHER DEPARTMENTS — COMMUNES
# =================================================
else:

    dep_name = dep_name_map.get(DEP_CODE, DEP_CODE)

    st.subheader(f"Département {DEP_CODE} – {dep_name}")

    apl_dep = generaliste_2023[
        generaliste_2023["Departement"] == DEP_CODE
    ]

    gdf = communes.merge(
        apl_dep,
        left_on="INSEE_COM",
        right_on="Code commune INSEE",
        how="left"
    )

    gdf["NOM_DEP"] = dep_name

# if hide_na:
# gdf = gdf.dropna(subset=["APL aux médecins généralistes"])

    if hide_na:
        gdf_plot = gdf.dropna(subset=["APL aux médecins généralistes"])
    else:
        gdf_plot = gdf[gdf["APL aux médecins généralistes"].notna()]


    fig = plot_map(
        gdf_plot,
        title=f"APL moyenne par commune ",
        zoom=7,
        hover_col="NOM"  
    )

    st.plotly_chart(fig, use_container_width=True)