# =================================================
# IMPORTS
# =================================================
import geopandas as gpd
import pandas as pd
import streamlit as st
import plotly.express as px

# =================================================
# STREAMLIT CONFIG
# =================================================
st.set_page_config(
    page_title="APL – Médecins généralistes (2023)",
    layout="wide"
)

st.title("Accessibilité potentielle localisée (APL)")
st.caption("Médecins généralistes – France métropolitaine (2023)")

DATA_DIR = "/Users/sarahboukhari/Documents/M1/S8/datavisu/dataviz"

def box(text, bg="#FAF5FF", border="#B39DDB"):
    st.markdown(f"""
    <div style="
        background-color:{bg};
        padding:16px;
        border-radius:12px;
        border-left:6px solid {border};
        margin-bottom:10px;
    ">
    {text}
    """, unsafe_allow_html=True)


# =================================================
# LOAD APL DATA
# =================================================
@st.cache_data
def load_apl():
    df = pd.read_excel(
        f"{DATA_DIR}/data/aplg.xlsx",
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


# =================================================
# LOAD COMMUNES
# =================================================
@st.cache_data
def load_communes():
    gdf = gpd.read_file(
        f"{DATA_DIR}/data/admincarto/livraison/COMMUNE.shp"
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
        f"{DATA_DIR}/data/admincarto/livraison/ARRONDISSEMENT_MUNICIPAL.shp"
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
        f"{DATA_DIR}/data/admincarto/livraison/DEPARTEMENT.shp"
    )[["INSEE_DEP", "NOM"]]

    gdf["INSEE_DEP"] = gdf["INSEE_DEP"].astype(str)
    return gdf


# =================================================
# LOAD TYPOLOGIE
# =================================================
@st.cache_data
def load_typologie():
    gdf = gpd.read_file(f"{DATA_DIR}/data/typologie")
    gdf = gdf.drop(columns="geometry")

    gdf = gdf.rename(columns={
        "inseecom": "Code commune INSEE",
        "nom_typo": "Typologie"
    })

    gdf["Code commune INSEE"] = gdf["Code commune INSEE"].astype(str)
    return gdf

# =================================================
# LOAD ALL DATA
# =================================================
generaliste_2023 = load_apl()
communes = load_communes()
arrondissements = load_arrondissements()
departements = load_departements()
typologie = load_typologie()

dep_name_map = dict(zip(departements["INSEE_DEP"], departements["NOM"]))


# =================================================
# SELECT DEPARTMENT
# =================================================
deps = (
    generaliste_2023["Departement"]
    .dropna()
    .unique()
)

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

st.markdown("""

Cette carte représente l’accessibilité potentielle localisée aux médecins généralistes à l’échelle communale 
(ou infra-communale pour Paris). Les différences de couleurs traduisent des niveaux d’accessibilité variables, 
reflétant la répartition de l’offre médicale généraliste. Elle met en évidence des disparités territoriales marquées.
""")

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
        hover_col="NOM"
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

    if hide_na:
        gdf_plot = gdf.dropna(subset=["APL aux médecins généralistes"])
    else:
        gdf_plot = gdf

    fig = plot_map(
        gdf_plot,
        title="APL moyenne par commune",
        zoom=7,
        hover_col="NOM"
    )

    st.plotly_chart(fig, use_container_width=True)

st.markdown("<br><br>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    box("""
<h4>📍 Département de l’Isère (38)</h4>
<p>
Dans le département de l’Isère, l’APL aux médecins généralistes présente de fortes disparités communales. 
Les valeurs observées s’étendent globalement d’environ 0 à plus de 8, traduisant des écarts marqués 
entre les territoires. Les communes situées autour de l’aire grenobloise affichent en moyenne des niveaux 
d’APL plus élevés (souvent supérieurs à 5), tandis que plusieurs communes rurales ou de montagne présentent 
des niveaux nettement plus faibles, parfois inférieurs à 2.  
Cette hétérogénéité met en évidence une inégale répartition de l’accessibilité aux soins au sein du département.
</p>
""")

with col2:
    box("""
<h4>📍 Paris – Arrondissements municipaux</h4>
<p>
À Paris, l’accessibilité aux médecins généralistes varie sensiblement selon les arrondissements. 
Les valeurs d’APL s’échelonnent approximativement de 4 à plus de 6,5. Les arrondissements centraux 
présentent les niveaux d’APL les plus élevés, avec des valeurs supérieures à 6, tandis que certains 
arrondissements périphériques affichent des niveaux plus modérés, autour de 4 à 5.  
Ces écarts illustrent des disparités intra-urbaines d’accès aux soins, malgré une offre médicale globalement dense.
</p>
""")


# =================================================
# BOXPLOT — TYPOLOGIE (FRANCE ENTIÈRE, INDÉPENDANT)
# =================================================
st.divider()
st.subheader("Accessibilité aux médecins généralistes selon la typologie des communes (France entière)")

apl_typo = generaliste_2023.merge(
    typologie[["Code commune INSEE", "Typologie"]],
    on="Code commune INSEE",
    how="inner"
)

apl_typo["Typologie_simple"] = apl_typo["Typologie"].replace({
    "Rural autonome peu dense": "Rural",
    "Rural autonome très peu dense": "Rural",
    "Rural sous faible influence d'un pôle": "Périurbain",
    "Rural sous forte influence d'un pôle": "Périurbain",
    "Urbain densité intermédiaire": "Urbain",
    "Urbain dense": "Urbain"
})

apl_typo = apl_typo.dropna(subset=["APL aux médecins généralistes", "Typologie_simple"])

fig_box = px.box(
    apl_typo,
    x="Typologie_simple",
    y="APL aux médecins généralistes",
    title="APL selon la typologie des communes",
    labels={
        "Typologie_simple": "Typologie des espaces",
        "APL aux médecins généralistes": "APL"
    }
)

fig_box.update_layout(
    title_x=0.5,
    xaxis_title=None
)

st.plotly_chart(fig_box, use_container_width=True)

st.markdown("""      
Ce graphique met ainsi en évidence un gradient territorial d’accès aux soins, mais aussi des disparités internes marquées, en particulier dans les espaces urbains : 
            
Le boxplot montre que l’accessibilité aux médecins généralistes est en moyenne plus élevée dans les communes urbaines que dans les communes périurbaines et rurales. La médiane de l’APL est la plus haute en milieu urbain, tandis que les communes rurales présentent des niveaux d’accessibilité plus faibles.
On observe également une variabilité importante au sein des communes urbaines, avec des situations allant de communes très bien dotées à d’autres nettement moins accessibles. À l’inverse, les communes rurales apparaissent plus concentrées autour de niveaux d’APL plus bas, traduisant un accès globalement plus limité aux soins de premier recours.             
""")




