# =================================================
# =================================================
import geopandas as gpd
import pandas as pd
import streamlit as st
import plotly.express as px
import mplcursors

import matplotlib.pyplot as plt

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

PALETTE = [
    "#1F4E79",  # bleu foncé bien ancré
    "#3E7CB1",  # bleu moyen
    "#7FB3D5",  # bleu clair
    "#B8E0D2",  # vert d’eau
    "#FFF7DD"   # très clair
]


def box(text, bg="#C3EAE368", border="#C3EAE368"):
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
        """,
        unsafe_allow_html=True
    )


# =================================================
# Introduction / Problématique
st.markdown(
"""
<div style="text-align: justify;">

Cette application s’inscrit dans le cadre d’un défi proposé par Open Data University. 
L’objectif est d’explorer et d’analyser des données ouvertes à l’aide de visualisations graphiques 
et cartographiques, afin d’apporter des éléments de lecture clairs et pertinents à une problématique 
d’intérêt public.

Cette application propose plus particulièrement une exploration visuelle de l’ accessibilité potentielle localisée (APL) aux médecins généralistes
en France métropolitaine en 2023.

L’objectif n’est pas d’établir des relations causales fortes, mais d’analyser comment 
l’accessibilité aux soins de premier recours varie selon les territoires, à différentes échelles, 
et en fonction de certains contextes géographiques et socio-économiques.

<b>Problématique choisie :</b> 
<b>Comment l’accessibilité potentielle aux médecins généralistes se répartit-elle sur le territoire 
français, et quels contrastes spatiaux et territoriaux peuvent être mis en évidence à l’aide de 
visualisations graphiques et cartographiques ?</b>
</div>
""",
unsafe_allow_html=True
)

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
    gdf = gpd.read_file("data/admincarto/livraison/DEPARTEMENT.shp")
    gdf = gdf[["INSEE_DEP", "NOM", "geometry"]]
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

# =================================================
# GLOBAL DASHBOARD LAYOUT
# =================================================
col_viz, col_text = st.columns([3, 1.2], gap="large")

# =================================================
# AXE 1 — Identifier les territoires prioritaires
# =================================================

from streamlit_extras.stylable_container import stylable_container


# =================================================
# AXE 1 — Identifier les territoires prioritaires
# =================================================

st.subheader("Identifier les territoires prioritaires")

st.markdown("""
Cette section vise à quantifier l’ampleur nationale de la population exposée à une faible accessibilité
aux médecins généralistes, sans distinction de typologie territoriale.
L’objectif est d’identifier les départements où les enjeux concernent le plus grand nombre d’habitants.
""")

# -------------------------------------------------
# Seuil APL
# -------------------------------------------------
seuil_apl = st.slider(
    "Seuil d’APL considéré comme faible",
    min_value=1.0,
    max_value=4.0,
    value=3.0,
    step=0.1
)

# -------------------------------------------------
# Indicateurs nationaux
# -------------------------------------------------
pop_totale = generaliste_2023["Population totale 2021"].sum()
mask_faible = generaliste_2023["APL aux médecins généralistes"] < seuil_apl

pop_exposee = generaliste_2023.loc[mask_faible, "Population totale 2021"].sum()
pct_pop_exposee = 100 * pop_exposee / pop_totale

nb_communes_exposees = generaliste_2023.loc[
    mask_faible, "Code commune INSEE"
].nunique()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Population en zones à faible accessibilité", f"{pct_pop_exposee:.1f} %")

with col2:
    st.metric("Communes concernées", f"{nb_communes_exposees:,}".replace(",", " "))

with col3:
    st.metric("Population concernée", f"{pop_exposee:,.0f}".replace(",", " "))

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------------------------
# % population exposée par département (CALCUL AVANT MAP)
# -------------------------------------------------
dep_expo = (
    generaliste_2023
    .assign(expose=lambda df: df["APL aux médecins généralistes"] < seuil_apl)
    .groupby("Departement")
    .apply(
        lambda df: 100
        * df.loc[df["expose"], "Population totale 2021"].sum()
        / df["Population totale 2021"].sum()
    )
    .reset_index(name="part_pop_exposee")
)

dep_expo_map = dict(zip(dep_expo["Departement"], dep_expo["part_pop_exposee"]))
dep_name_map = dict(zip(departements["INSEE_DEP"], departements["NOM"]))

# -------------------------------------------------
# Données géographiques
# -------------------------------------------------
communes_2154 = communes.to_crs(epsg=2154)
departements_2154 = departements.to_crs(epsg=2154)

gdf_apl = communes_2154.merge(
    generaliste_2023[
        ["Code commune INSEE", "Departement", "APL aux médecins généralistes"]
    ],
    left_on="INSEE_COM",
    right_on="Code commune INSEE",
    how="left"
)

gdf_faible_apl = gdf_apl[
    gdf_apl["APL aux médecins généralistes"] < seuil_apl
]

top10_deps = (
    gdf_faible_apl
    .groupby("Departement")
    .size()
    .sort_values(ascending=False)
    .head(10)
    .index
    .tolist()
)

gdf_dep_top10 = departements_2154[
    departements_2154["INSEE_DEP"].isin(top10_deps)
]
with col_viz:

    fig, ax = plt.subplots(figsize=(7.5, 7.5), dpi=150)

    # Fond France
    communes_2154.plot(ax=ax, color="#EEF4FA", linewidth=0)

    # Contours tous départements
    departements_2154.boundary.plot(
        ax=ax,
        color="#D6D6D6",
        linewidth=0.3
    )

    # Communes à faible APL
    gdf_faible_apl.plot(
        ax=ax,
        color="#B8E0D2",
        linewidth=0
    )

    # Contours top 10 départements
    gdf_dep_top10.boundary.plot(
        ax=ax,
        color="#1F4E79",
        linewidth=0.9
    )

    ax.set_aspect("equal")
    ax.axis("off")

    ax.set_title(
        "Communes à faible accessibilité aux médecins généralistes\n"
        "Contours : 10 départements les plus concernés",
        fontsize=12,
        fontweight="bold",
        color="#1F4E79",
        pad=12
    )

    st.pyplot(fig)

with col_text:

    st.markdown("### Identifier les territoires prioritaires")

    st.markdown("""
    Cette carte met en évidence la répartition spatiale des communes présentant
    une **accessibilité faible aux médecins généralistes** à l’échelle nationale.
    
    Les contours soulignent les **départements où ces communes sont les plus nombreuses**,
    permettant d’identifier des territoires prioritaires du point de vue de l’accès aux soins.
    """)

    st.markdown("#### Top 10 départements les plus concernés")

    top10_table = (
        gdf_faible_apl
        .groupby("Departement")
        .size()
        .reset_index(name="Nombre de communes")
        .merge(
            departements[["INSEE_DEP", "NOM"]],
            left_on="Departement",
            right_on="INSEE_DEP",
            how="left"
        )
        .sort_values("Nombre de communes", ascending=False)
        .head(10)
        [["NOM", "Nombre de communes"]]
    )

    st.dataframe(
        top10_table,
        hide_index=True,
        use_container_width=True
    )



# =================================================
# Visualisation 1 : Carte de l’APL aux médecins généralistes

# =================================================
# APL locale — carte interactive
# =================================================

with col_text:

    st.subheader(
        "Accessibilité potentielle localisée aux médecins généralistes "
        "en France métropolitaine (2023)"
    )

    st.markdown("""
    Cette carte représente l’accessibilité potentielle localisée aux médecins généralistes
    à l’échelle communale, ou infra-communale pour Paris.
    
    L’objectif est avant tout **descriptif**, afin de poser un cadre spatial avant
    l’examen de regroupements ou de distributions plus globales.
    """)

    deps = sorted(
        d for d in generaliste_2023["Departement"].unique()
        if len(d) == 2 and d not in ["96", "97"]
    )

    DEP_CODE = st.selectbox(
        "Choisissez un département",
        deps,
        index=deps.index("75")
    )

    hide_na = st.checkbox(
        "Masquer les zones sans données",
        value=True
    )


with col_viz:

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
            title=dict(text=title, x=0.5),
            margin={"r": 0, "t": 40, "l": 0, "b": 0}
        )

        return fig


    if DEP_CODE == "75":
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

        st.plotly_chart(
            plot_map(gdf, "APL moyenne par arrondissement", 11, "NOM"),
            use_container_width=True
        )

    else:
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
            gdf = gdf.dropna(subset=["APL aux médecins généralistes"])

        st.plotly_chart(
            plot_map(gdf, "APL moyenne par commune", 7, "NOM"),
            use_container_width=True
        )
with col_text:

    box("""
    <h4>Département de l’Isère (38)</h4>
    <p>
    L’APL aux médecins généralistes présente de fortes disparités communales.
    Les communes proches de l’aire grenobloise affichent en moyenne des niveaux
    plus élevés, tandis que plusieurs communes rurales ou de montagne présentent
    des niveaux nettement plus faibles, parfois inférieurs à 2.
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
fig_box.update_layout(title_x=0.5, title_xanchor="center")
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
fig_hist.update_yaxes(title_text="Nombre de départements")
fig_hist.update_layout(title_x=0.5)
fig_hist.update_traces(
    hovertemplate=
    "APL moyenne : %{x}<br>" +
    "Nombre de départements : %{y}<extra></extra>"
)

fig_hist.update_layout(
    title_x=0.5,
    title_xanchor="center"
)

st.plotly_chart(fig_hist, use_container_width=True)


st.markdown("""
Cette distribution montre que la majorité des départements se concentrent autour de niveaux d’APL intermédiaires. 
Les départements très bien ou très mal dotés restent minoritaires, ce qui nuance l’idée d’une opposition simple 
entre territoires favorisés et défavorisés.
            
Par exemple, l’histogramme indique qu’environ 15 départements présentent une APL moyenne comprise entre 2,8 et 3,0, correspondant à l’intervalle le plus fréquent de la distribution.
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
fig_scatter.update_layout(title_x=0.5, title_xanchor="center")

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

st.subheader("Conclusion")

st.markdown("""

Cette exploration met en évidence de fortes disparités spatiales d’accès aux médecins généralistes en France, 
observables à différentes échelles. Si certains contrastes territoriaux apparaissent clairement, les liens 
avec les variables socio-économiques étudiées restent limités.

Dans ce contexte, l’intérêt principal du travail réside dans l’usage de visualisations interactives via Streamlit, 
permettant d’explorer les données de manière progressive et transparente. L’objectif n’est pas de démontrer, 
mais de rendre visibles des dynamiques territoriales complexes.
""")


communes.plot(
    ax=ax,
    color="#EEF4FA",       # bleu très clair
    linewidth=0
)

# Contours de TOUS les départements (gris très clair)
dep_boundaries = departements.boundary.plot(
    ax=ax,
    color="#9C9898",
    linewidth=0.3
)

# Communes à faible APL (vert d’eau)
gdf_faible_apl.plot(
    ax=ax,
    color="#B8E0D2",       # vert d’eau
    linewidth=0,
    alpha=1
)

# Contours des départements prioritaires (bleu foncé)

dep_top10_boundaries = gdf_dep_top10.boundary.plot(
    ax=ax,
    color="#449589",
    linewidth=0.8
)


ax.set_title(
    "Communes à faible accessibilité aux médecins généralistes\n"
    "Contours : 10 départements les plus concernés",
    fontsize=12,
    fontweight="bold",
    color="#1F4E79"
)
