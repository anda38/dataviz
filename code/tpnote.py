import geopandas as gpd
import pandas as pd
import streamlit as st
import plotly.express as px
import matplotlib.pyplot as plt
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

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
    "#1F4E79",
    "#3E7CB1",
    "#7FB3D5",
    "#B8E0D2",
    "#FFF7DD"
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

Cette application a été réalisée dans le cadre d’un défi proposé par Open Data University.
Elle utilise des données ouvertes pour analyser l’accessibilité aux médecins généralistes
en France métropolitaine en 2023 à l’aide de visualisations interactives.

L’objectif est d’observer comment cette accessibilité varie selon les territoires et selon
l’échelle d’analyse, du niveau national jusqu’au niveau communal.

Ce travail ne cherche pas à expliquer les causes des inégalités observées, mais à les rendre
visibles et comparables à travers des graphiques et des cartes.

<b>Problématique :</b>  
<b>Comment l’accessibilité potentielle aux médecins généralistes se répartit-elle sur le
territoire français, et quels contrastes spatiaux peut-on observer grâce aux
visualisations ?</b>

</div>
""",
unsafe_allow_html=True
)


# =================================================
# Chargement des données
@st.cache_data
def load_apl():
    df = pd.read_excel(
        BASE_DIR / "data" / "aplg.xlsx",
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
    gdf = gpd.read_file(
        BASE_DIR / "data" / "admincarto" / "livraison" / "COMMUNE.shp"
    )
    gdf["INSEE_COM"] = gdf["INSEE_COM"].astype(str)
    gdf = gdf.to_crs(epsg=2154)
    gdf["geometry"] = gdf["geometry"].simplify(100, preserve_topology=True)
    return gdf.to_crs(epsg=4326)


@st.cache_data
def load_arrondissements():
    gdf = gpd.read_file(
        BASE_DIR / "data" / "admincarto" / "livraison" / "ARRONDISSEMENT_MUNICIPAL.shp"
    )
    gdf["INSEE_ARM"] = gdf["INSEE_ARM"].astype(str)
    gdf = gdf.to_crs(epsg=2154)
    gdf["geometry"] = gdf["geometry"].simplify(10, preserve_topology=True)
    return gdf.to_crs(epsg=4326)


@st.cache_data
def load_departements():
    gdf = gpd.read_file(
        BASE_DIR / "data" / "admincarto" / "livraison" / "DEPARTEMENT.shp"
    )
    gdf = gdf[["INSEE_DEP", "NOM", "geometry"]]
    gdf["INSEE_DEP"] = gdf["INSEE_DEP"].astype(str)
    return gdf


@st.cache_data
def load_typologie():
    gdf = gpd.read_file(
        BASE_DIR / "data" / "typologie"
    ).drop(columns="geometry")
    gdf = gdf.rename(columns={
        "inseecom": "Code commune INSEE",
        "nom_typo": "Typologie"
    })
    gdf["Code commune INSEE"] = gdf["Code commune INSEE"].astype(str)
    return gdf


@st.cache_data
def load_social():
    df = pd.read_csv(
        BASE_DIR / "data" / "data.csv",
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

st.divider()
st.subheader("Identifier les territoires prioritaires")

col_viz, col_text = st.columns([3.2, 1.8], gap="large")

# =========================
# COLONNE VISUALISATION
# =========================
with col_viz:

    seuil_apl = st.slider(
        "Seuil d’APL considéré comme faible",
        min_value=1.0,
        max_value=4.0,
        value=3.0,
        step=0.1
    )

    pop_totale = generaliste_2023["Population totale 2021"].sum()
    mask_faible = generaliste_2023["APL aux médecins généralistes"] < seuil_apl
    pop_exposee = generaliste_2023.loc[mask_faible, "Population totale 2021"].sum()
    pct_pop_exposee = 100 * pop_exposee / pop_totale
    nb_communes_exposees = generaliste_2023.loc[
        mask_faible, "Code commune INSEE"
    ].nunique()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Population en zones à faible accessibilité",
            f"{pct_pop_exposee:.1f} %"
        )
    with col2:
        st.metric(
            "Communes concernées",
            f"{nb_communes_exposees:,}".replace(",", " ")
        )
    with col3:
        st.metric(
            "Population concernée",
            f"{pop_exposee:,.0f}".replace(",", " ")
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------
    # Carte nationale
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
    st.markdown("### Communes à faible accessibilité")

    fig, ax = plt.subplots(figsize=(5, 4.2), dpi=150)
    communes_2154.plot(ax=ax, color="#EEF4FA", linewidth=0)
    departements_2154.boundary.plot(ax=ax, color="#D6D6D6", linewidth=0.3)
    gdf_faible_apl.plot(ax=ax, color="#B8E0D2", linewidth=0)
    gdf_dep_top10.boundary.plot(ax=ax, color="#1F4E79", linewidth=0.9)
    ax.set_aspect("equal")
    ax.axis("off")
    st.pyplot(fig, use_container_width=False)

# =========================
# COLONNE TEXTE / TABLE
# =========================
with col_text:
    # push Lecture + table down only
    st.markdown("<br><br><br><br><br><br><br><br><br><br>", unsafe_allow_html=True)

    st.markdown("### Lecture")

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
        .assign(
            Département=lambda df:
            df["Departement"] + " – " + df["NOM"]
        )
        .sort_values("Nombre de communes", ascending=False)
        .head(10)
        [["Département", "Nombre de communes"]]
    )

    st.markdown("""
    La carte met en évidence les communes dont le niveau d’APL est inférieur au seuil choisi.
    Les départements entourés correspondent à ceux qui regroupent le plus grand nombre de
    communes en situation de faible accessibilité.
    """)

    st.dataframe(top10_table, hide_index=True, use_container_width=True)



st.divider()

st.subheader(
    "Accessibilité potentielle localisée aux médecins généralistes "
    "en France métropolitaine (2023)"
)

col_viz2, col_text2 = st.columns([3.2, 1.8], gap="large")

# =========================
# COLONNE TEXTE / CONTROLS
# =========================
with col_text2:

    st.markdown("### Sélection du département")

    deps = sorted(
        d for d in generaliste_2023["Departement"].unique()
        if len(d) == 2 and d not in ["96", "97"]
    )

    DEP_CODE = st.selectbox(
        "Choisissez un département",
        deps,
        index=deps.index("75")
    )

    hide_na = st.checkbox("Masquer les zones sans données", value=True)

    # espace visuel
    st.markdown("<br><br>", unsafe_allow_html=True)

    st.markdown("""
    ### Lecture
    Cette carte permet d’examiner l’accessibilité aux médecins généralistes à l’échelle
    locale. En sélectionnant un département, on peut observer les différences entre
    les communes et repérer d’éventuels contrastes internes.
    """)

# =========================
# COLONNE VISUALISATION
# =========================
with col_viz2:

    st.markdown("### APL moyenne par territoire")

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
            title=None,
            margin={"r": 0, "t": 10, "l": 0, "b": 0}
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
            plot_map(gdf, None, 11, "NOM"),
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
            plot_map(gdf, None, 7, "NOM"),
            use_container_width=True
        )

st.divider()
st.subheader("Distribution de l’APL au sein du département sélectionné")

col_viz, col_text = st.columns([3, 2], gap="large")

df_dep = generaliste_2023[
    generaliste_2023["Departement"] == DEP_CODE
].dropna(subset=["APL aux médecins généralistes"])

with col_viz:

    fig_hist_dep = px.histogram(
        df_dep,
        x="APL aux médecins généralistes",
        nbins=30,
        color_discrete_sequence=[PALETTE[0]],
        labels={"APL aux médecins généralistes": "APL"},
        title=f"Répartition des niveaux d’APL – Département {DEP_CODE}"
    )

    fig_hist_dep.update_layout(title_x=0.5)
    st.plotly_chart(fig_hist_dep, use_container_width=True)

with col_text:

    st.markdown(f"""
### Lecture

Ce graphique montre la répartition des niveaux d’APL entre les communes du département
**{DEP_CODE}**.

Lorsque les valeurs sont proches les unes des autres, la situation est relativement
homogène. À l’inverse, une distribution étalée indique des écarts importants entre
les communes.

Cette visualisation permet de mieux comprendre si les difficultés observées dans le
département concernent l’ensemble du territoire ou seulement certaines communes.
""")


#####
df_dep_stats = (
    generaliste_2023
    .groupby("Departement")
    .agg(
        apl_mean=("APL aux médecins généralistes", "mean"),
        apl_q25=("APL aux médecins généralistes", lambda x: x.quantile(0.25)),
        apl_q75=("APL aux médecins généralistes", lambda x: x.quantile(0.75)),
        n_communes=("Code commune INSEE", "nunique")
    )
    .reset_index()
)

df_dep_stats["IQR"] = df_dep_stats["apl_q75"] - df_dep_stats["apl_q25"]

ordre_quartiles = [
    "APL très faible",
    "APL faible",
    "APL intermédiaire",
    "APL élevée"
]

df_dep_stats["quartile_apl"] = pd.qcut(
    df_dep_stats["apl_mean"],
    q=4,
    labels=ordre_quartiles
)

df_dep_stats["quartile_apl"] = pd.Categorical(
    df_dep_stats["quartile_apl"],
    categories=ordre_quartiles,
    ordered=True
)
df_focus = df_dep_stats[df_dep_stats["Departement"] == DEP_CODE]


couleurs_quartiles = {
    "APL très faible": PALETTE[0],   # bleu foncé
    "APL faible": PALETTE[1],        # bleu moyen
    "APL intermédiaire": PALETTE[3], # vert d’eau
    "APL élevée": PALETTE[4]         # très clair
}

st.divider()
st.subheader(
    "Typologie des situations départementales d’accessibilité aux médecins généralistes"
)

col_viz, col_text = st.columns([3, 2], gap="large")

with col_viz:

    fig_scatter = px.scatter(
        df_dep_stats,
        x="apl_mean",
        y="IQR",
        size="n_communes",
        color="quartile_apl",
        color_discrete_map=couleurs_quartiles,
        category_orders={"quartile_apl": ordre_quartiles},
        hover_name="Departement",
        labels={
            "apl_mean": "APL moyenne départementale",
            "IQR": "Hétérogénéité communale (IQR)",
            "quartile_apl": "Position nationale"
        },
        title=None,
        size_max=26
    )
    if not df_focus.empty:
        fig_scatter.add_trace(
        px.scatter(
            df_focus,
            x="apl_mean",
            y="IQR",
            size="n_communes",   # ← IMPORTANT
            hover_name="Departement"
        ).data[0]
    )

    fig_scatter.data[-1].update(
        marker=dict(
            symbol="diamond",
            color="#2B41C0",
            size=22,
            line=dict(width=3, color="black")
        ),
        name=f"Département sélectionné ({DEP_CODE})",
        showlegend=True
    )

    fig_scatter.update_traces(
    hovertemplate=
    "<b>Département %{hovertext}</b><br>"
    "APL moyenne : %{x:.2f}<br>"
    "Dispersion (IQR) : %{y:.2f}<br>"
    "Nombre de communes : %{customdata}<br>"
    "<extra></extra>",
    customdata=df_dep_stats["n_communes"]
)


    fig_scatter.update_layout(
        legend_title_text="",
        margin=dict(l=0, r=0, t=10, b=0)
    )

    st.plotly_chart(fig_scatter, use_container_width=True)

with col_text:

    st.markdown("""
### Lecture

Ce graphique compare les départements selon leur niveau moyen d’accessibilité aux
médecins généralistes et les différences observées entre leurs communes.

Les départements situés à gauche présentent en moyenne une accessibilité plus faible.
Lorsque cette faible accessibilité s’accompagne d’une dispersion limitée, cela indique
une situation similaire sur l’ensemble du département. À l’inverse, une forte dispersion
traduit des contrastes internes plus marqués.

Ce graphique permet ainsi d’identifier différents profils départementaux, en allant
au-delà d’une simple lecture cartographique.
""")



# =================================================
# Conclusion (inchangée)
# =================================================
st.divider()
st.subheader("Conclusion")

st.markdown("""
Cette exploration met en évidence des différences importantes d’accès aux médecins
généralistes selon les territoires et selon l’échelle d’analyse.

Les visualisations montrent que certaines difficultés sont généralisées à l’échelle
départementale, tandis que d’autres sont plus localisées et concernent uniquement
certaines communes.

L’intérêt principal de ce travail réside dans l’usage de visualisations interactives,
qui permettent d’explorer progressivement les données et de mieux comprendre
la diversité des situations territoriales, sans chercher à établir de relations
causales.
""")

