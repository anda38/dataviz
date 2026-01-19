# =================================================
# =================================================
import geopandas as gpd
import pandas as pd
import streamlit as st
import plotly.express as px

# =================================================
# Ici on configure Streamlit
st.set_page_config(
    page_title="APL – Médecins généralistes (2023)",
    layout="wide"
)

st.title("Accessibilité potentielle localisée (APL)")
st.caption("Médecins généralistes – France métropolitaine (2023)")


# =================================================
# Ici on définit une palette de couleurs et une fonction pour afficher des encadrés

PALETTE = ["#80A1BA", "#91C4C3", "#B4DEBD", "#FFF7DD"]

def box(text, bg="#B5E1BF7E", border="#E2FFE9BE"):
    st.markdown(
        f"""
        <div style="
            background-color: {bg};
            padding: 18px;
            border-radius: 12px;
            border-left: 6px solid {border};
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            margin-bottom: 16px;
            display: block;
        ">
            {text}
        </div>
        """,
        unsafe_allow_html=True
    )


# =================================================
# Introduction / Problématique
st.markdown("""
Cette application propose une exploration visuelle de l’accessibilité potentielle localisée (APL) aux médecins généralistes en France métropolitaine en 2023.

L’objectif n’est pas d’établir des relations causales fortes, mais d’explorer comment l’accessibilité aux soins de premier recours varie selon les territoires, à différentes échelles, et selon certains contextes géographiques et socio-économiques.

L’analyse repose principalement sur des visualisations interactives. Elles permettent d’identifier des contrastes spatiaux, des distributions et d’éventuelles tendances, même lorsque les liens entre variables restent faibles ou hétérogènes.
""")

# =================================================
# Chargement des données
@st.cache_data
def load_apl():
    df = pd.read_excel(
        "data/aplg.xlsx",
        sheet_name=2,
        skiprows=8
    )
    df = df.dropna(subset=["Code commune INSEE"])
    df["Code commune INSEE"] = df["Code commune INSEE"].astype(str)
    df["Departement"] = df["Code commune INSEE"].str[:2]
    df["APL aux médecins généralistes"] = pd.to_numeric(
        df["APL aux médecins généralistes"], errors="coerce"
    )
    return df

@st.cache_data
def load_communes():
    gdf = gpd.read_file("data/admincarto/livraison/COMMUNE.shp")
    gdf["INSEE_COM"] = gdf["INSEE_COM"].astype(str)
    gdf = gdf.to_crs(epsg=2154)
    gdf["geometry"] = gdf["geometry"].simplify(100, preserve_topology=True)
    return gdf.to_crs(epsg=4326)

@st.cache_data
def load_arrondissements():
    gdf = gpd.read_file("data/admincarto/livraison/ARRONDISSEMENT_MUNICIPAL.shp")
    gdf["INSEE_ARM"] = gdf["INSEE_ARM"].astype(str)
    gdf = gdf.to_crs(epsg=2154)
    gdf["geometry"] = gdf["geometry"].simplify(10, preserve_topology=True)
    return gdf.to_crs(epsg=4326)

@st.cache_data
def load_departements():
    gdf = gpd.read_file("data/admincarto/livraison/DEPARTEMENT.shp")[["INSEE_DEP", "NOM"]]
    gdf["INSEE_DEP"] = gdf["INSEE_DEP"].astype(str)
    return gdf

@st.cache_data
def load_typologie():
    gdf = gpd.read_file("data/typologie").drop(columns="geometry")
    gdf = gdf.rename(columns={
        "inseecom": "Code commune INSEE",
        "nom_typo": "Typologie"
    })
    gdf["Code commune INSEE"] = gdf["Code commune INSEE"].astype(str)
    return gdf

@st.cache_data
def load_social():
    df = pd.read_csv(
        "data/data.csv",
        sep=";",
        skiprows=2,
        na_values=["NA", "N/A", "pas de solution", ""]
    )
    df.columns = df.columns.str.strip()
    df = df.rename(columns={
        "Médiane du niveau de vie 2021": "niveau_vie"
    })
    df["niveau_vie"] = pd.to_numeric(df["niveau_vie"], errors="coerce")
    df["Code"] = df["Code"].astype(str).str.zfill(2)
    return df

# =================================================
# On charge les données
generaliste_2023 = load_apl()
communes = load_communes()
arrondissements = load_arrondissements()
departements = load_departements()
typologie = load_typologie()
social = load_social()

dep_name_map = dict(zip(departements["INSEE_DEP"], departements["NOM"]))

# =================================================
# Visualisation 1 : Carte de l’APL aux médecins généralistes

st.subheader("Accessibilité potentielle localisée aux médecins généralistes")

st.markdown("""
Cette carte représente l’accessibilité potentielle localisée aux médecins généralistes à l’échelle communale, 
ou infra-communale pour Paris. Elle permet d’identifier visuellement les territoires bien dotés et ceux où l’accès 
aux soins de premier recours apparaît plus limité.

L’objectif ici est avant tout descriptif, afin de poser un cadre spatial avant d’examiner des regroupements et 
des distributions plus globales.
""")

deps = sorted(d for d in generaliste_2023["Departement"].unique() if len(d) == 2 and d not in ["96", "97"])
DEP_CODE = st.selectbox("Choisissez un département", deps, index=deps.index("75"))
hide_na = st.checkbox("Masquer les zones sans données", value=True)

def plot_map(gdf, title, zoom, hover_col):
    fig = px.choropleth_map(
        gdf,
        geojson=gdf.geometry,
        locations=gdf.index,
        color="APL aux médecins généralistes",
        color_continuous_scale=PALETTE,
        map_style="carto-positron",
        hover_name=hover_col,
        zoom=zoom,
        center={
            "lat": gdf.geometry.centroid.y.mean(),
            "lon": gdf.geometry.centroid.x.mean()
        }
    )

    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>APL moyenne : %{z:.2f}<extra></extra>"
    )

    
    fig.update_layout(
        title=dict(text=title, x=0.5) if title else None,
        margin={"r": 0, "t": 40, "l": 0, "b": 0}
    )

    return fig


if DEP_CODE == "75":
    st.subheader("Paris – arrondissements municipaux")
    apl_paris = generaliste_2023[generaliste_2023["Code commune INSEE"].str.startswith("751")]
    arr_paris = arrondissements[arrondissements["INSEE_ARM"].str.startswith("751")]
    gdf = arr_paris.merge(apl_paris, left_on="INSEE_ARM", right_on="Code commune INSEE", how="left")
    if hide_na:
        gdf = gdf.dropna(subset=["APL aux médecins généralistes"])
    st.plotly_chart(plot_map(gdf, "APL moyenne par arrondissement", 11, "NOM"), use_container_width=True)
else:
    apl_dep = generaliste_2023[generaliste_2023["Departement"] == DEP_CODE]
    gdf = communes.merge(apl_dep, left_on="INSEE_COM", right_on="Code commune INSEE", how="left")
    if hide_na:
        gdf = gdf.dropna(subset=["APL aux médecins généralistes"])
    st.plotly_chart(plot_map(gdf, "APL moyenne par commune", 7, "NOM"), use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    box("""
<h4> Département de l’Isère (38)</h4>
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
<h4>Paris – Arrondissements municipaux</h4>
<p>
À Paris, l’accessibilité aux médecins généralistes varie sensiblement selon les arrondissements. 
Les valeurs d’APL s’échelonnent approximativement de 4 à plus de 6,5. Les arrondissements centraux 
présentent les niveaux d’APL les plus élevés, avec des valeurs supérieures à 6, tandis que certains 
arrondissements périphériques affichent des niveaux plus modérés, autour de 4 à 5.  
Ces écarts illustrent des disparités intra-urbaines d’accès aux soins, malgré une offre médicale globalement dense.
</p>
""")


# =================================================
# Visualisation 2 : APL selon la typologie des communes

st.divider()
st.subheader("Accessibilité selon la typologie des communes")

apl_typo = generaliste_2023.merge(
    typologie[["Code commune INSEE", "Typologie"]],
    on="Code commune INSEE"
)

apl_typo["Typologie simplifiée"] = apl_typo["Typologie"].replace({
    "Rural autonome peu dense": "Rural",
    "Rural autonome très peu dense": "Rural",
    "Rural sous faible influence d'un pôle": "Périurbain",
    "Rural sous forte influence d'un pôle": "Périurbain",
    "Urbain dense": "Urbain",
    "Urbain densité intermédiaire": "Urbain"
})

fig_box = px.box(
    apl_typo.dropna(subset=["APL aux médecins généralistes"]),
    x="Typologie simplifiée",
    y="APL aux médecins généralistes",
    color="Typologie simplifiée",
    color_discrete_sequence=PALETTE,
    labels={
        "APL aux médecins généralistes": "APL",
        "Typologie simplifiée": "Type de territoire"
    },
    title="Distribution de l’APL selon la typologie des communes"
)
fig_box.update_layout(title_x=0.5)
st.plotly_chart(fig_box, use_container_width=True)

st.markdown("""
Ce graphique met en évidence un gradient territorial d’accès aux soins, avec une accessibilité en moyenne plus élevée 
dans les espaces urbains. Toutefois, la dispersion importante des valeurs, en particulier en milieu urbain, montre 
que le type de territoire ne suffit pas à expliquer à lui seul les écarts observés.
""")

# =================================================
# Visualisation 3 : APL moyenne par département

st.subheader("Distribution de l’APL moyenne par département")

apl_dep_mean = (
    generaliste_2023
    .groupby("Departement")["APL aux médecins généralistes"]
    .mean()
    .reset_index()
)

fig_hist = px.histogram(
    apl_dep_mean,
    x="APL aux médecins généralistes",
    nbins=30,
    color_discrete_sequence=[PALETTE[0]],
    labels={"APL aux médecins généralistes": "APL moyenne"},
    title="Répartition des niveaux d’APL moyenne entre les départements"
)
fig_hist.update_layout(title_x=0.5)
st.plotly_chart(fig_hist, use_container_width=True)

st.markdown("""
Cette distribution montre que la majorité des départements se concentrent autour de niveaux d’APL intermédiaires. 
Les départements très bien ou très mal dotés restent minoritaires, ce qui nuance l’idée d’une opposition simple 
entre territoires favorisés et défavorisés.
""")

# =================================================
# Visualisation 4 : APL et niveau de vie
st.subheader("APL et niveau de vie")

df_scatter = apl_dep_mean.merge(
    social,
    left_on="Departement",
    right_on="Code"
)

fig_scatter = px.scatter(
    df_scatter,
    x="niveau_vie",
    y="APL aux médecins généralistes",
    labels={
        "niveau_vie": "Médiane du niveau de vie (€)",
        "APL aux médecins généralistes": "APL moyenne"
    },
    title="Lien entre niveau de vie et accessibilité aux médecins généralistes",
    color_discrete_sequence=[PALETTE[1]]
)
fig_scatter.update_traces(marker=dict(size=9))
fig_scatter.update_layout(title_x=0.5)
st.plotly_chart(fig_scatter, use_container_width=True)

st.markdown("""
Ce graphique suggère qu’il n’existe pas de relation forte et systématique entre le niveau de vie médian 
et l’accessibilité moyenne aux médecins généralistes à l’échelle départementale. Certains départements 
relativement favorisés présentent une accessibilité modérée, tandis que d’autres, moins favorisés, ne sont 
pas nécessairement les moins bien dotés.

Cette absence de lien marqué souligne l’intérêt des visualisations pour explorer les données sans chercher 
à imposer des relations explicatives qui ne sont pas clairement soutenues par les résultats.
""")

# =================================================
# Résumé et conclusion
st.divider()
st.markdown("""
**Conclusion**

Cette exploration met en évidence de fortes disparités spatiales d’accès aux médecins généralistes en France, 
observables à différentes échelles. Si certains contrastes territoriaux apparaissent clairement, les liens 
avec les variables socio-économiques étudiées restent limités.

Dans ce contexte, l’intérêt principal du travail réside dans l’usage de visualisations interactives via Streamlit, 
permettant d’explorer les données de manière progressive et transparente. L’objectif n’est pas de démontrer, 
mais de rendre visibles des dynamiques territoriales complexes.
""")
