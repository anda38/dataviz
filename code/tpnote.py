import geopandas as gpd
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import os
import zipfile
import gdown
import streamlit as st

@st.cache_data(show_spinner="Téléchargement des données…")
def download_and_extract_datatp():
    FILE_ID = "1O_2Zi4yLe0iNe_D7c1pBKAHewIR7oH59"

    zip_path = "datatp.zip"
    extract_path = "datatp"

    if os.path.exists(os.path.join(extract_path, "aplg.xlsx")):
        return

    url = f"https://drive.google.com/uc?id={FILE_ID}"

    gdown.download(url, zip_path, quiet=False, fuzzy=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(".")

    os.remove(zip_path)


download_and_extract_datatp()


st.set_page_config(
    page_title="APL – Médecins généralistes (2023)",
    layout="wide"
)


st.title("Accessibilité potentielle localisée (APL)")
st.caption("Médecins généralistes – France métropolitaine (2023)")



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


st.markdown(
"""
<div style="text-align: justify;">

L’accessibilité potentielle localisée (APL) est un indicateur qui mesure l’accès aux médecins généralistes à une échelle géographique fine, celle de la commune. Contrairement aux indicateurs classiques de densité médicale, il prend en compte à la fois l’offre de soins, la population locale, les communes environnantes, ainsi que le niveau d’activité des médecins et la structure par âge de la population.

Exprimée en nombre de consultations accessibles par an et par habitant, l’APL permet de mettre en évidence des inégalités territoriales d’accès aux soins qui peuvent être masquées lorsque l’analyse est réalisée à des échelles plus larges.

Cette application a été réalisée dans le cadre d’un défi proposé par Open Data University. Elle mobilise des données ouvertes pour analyser l’accessibilité aux médecins généralistes en France métropolitaine en 2023 à l’aide de visualisations interactives.

L’objectif est d’observer comment cette accessibilité varie selon les territoires et selon l’échelle d’analyse, du niveau national jusqu’au niveau communal. Les graphiques et cartes sont organisés de manière progressive afin de proposer une lecture guidée des résultats : un département est sélectionné par défaut afin d’illustrer concrètement la manière d’interpréter les différentes visualisations et de suivre un fil conducteur commun entre la carte, l’histogramme et le graphique de synthèse.

Il est toutefois possible de modifier à tout moment le département sélectionné, ainsi que le seuil d’APL considéré comme faible, afin d’explorer d’autres situations territoriales et de comparer les résultats.

Dans cette application, un seuil de 1,90 consultation par an et par habitant est retenu comme valeur de référence pour identifier les territoires à faible accessibilité. Ce seuil permet de repérer les zones les plus en difficulté tout en conservant une lecture cohérente à l’échelle nationale.

Ce travail ne cherche pas à expliquer les causes des inégalités observées, mais à les rendre visibles, lisibles et comparables à travers des visualisations interactives.

<b>Problématique :</b>  
<b>Comment l’accessibilité potentielle aux médecins généralistes se répartit-elle sur le
territoire français, et quels contrastes spatiaux peut-on observer grâce aux
visualisations ?</b>

</div>
""",
unsafe_allow_html=True
)



@st.cache_data
def load_apl():
    df = pd.read_excel(
        "datatp/aplg.xlsx",
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
    gdf = gpd.read_file("datatp/admincarto/COMMUNE.shp")
    gdf["INSEE_COM"] = gdf["INSEE_COM"].astype(str)
    gdf = gdf.to_crs(epsg=2154)
    gdf["geometry"] = gdf["geometry"].simplify(100, preserve_topology=True)
    return gdf.to_crs(epsg=4326)

@st.cache_data
def load_arrondissements():
    gdf = gpd.read_file("datatp/admincarto/ARRONDISSEMENT_MUNICIPAL.shp")
    gdf["INSEE_ARM"] = gdf["INSEE_ARM"].astype(str)
    gdf = gdf.to_crs(epsg=2154)
    gdf["geometry"] = gdf["geometry"].simplify(10, preserve_topology=True)
    return gdf.to_crs(epsg=4326)

@st.cache_data
def load_departements():
    gdf = gpd.read_file("datatp/admincarto/DEPARTEMENT.shp")
    gdf = gdf[["INSEE_DEP", "NOM", "geometry"]]
    gdf["INSEE_DEP"] = gdf["INSEE_DEP"].astype(str)
    return gdf



generaliste_2023 = load_apl()
communes = load_communes()
arrondissements = load_arrondissements()
departements = load_departements()



st.divider()
st.subheader("Identifier les territoires prioritaires")

col_viz, col_text = st.columns([3.2, 1.8], gap="large")


with col_viz:

    seuil_apl = st.slider(
        "Seuil d’APL considéré comme faible",
        min_value=1.0,
        max_value=4.0,
        value=1.90,
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


with col_text:
    
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
    top10_table = top10_table.rename(
    columns={"Nombre de communes": "Nb"}
)


    st.markdown("""
    Cette carte à l’échelle nationale permet d’identifier les communes dont l’APL est inférieure au seuil retenu, ici fixé à 1,90 consultation par an et par habitant, considéré comme un niveau faible d’accessibilité.

Les communes colorées correspondent à celles situées sous ce seuil, tandis que les départements entourés font partie des dix départements qui concentrent le plus grand nombre de communes concernées. Cette représentation permet donc de repérer les territoires où les difficultés d’accès aux médecins généralistes sont les plus fréquentes.

Le Loiret (45) apparaît clairement parmi ces départements. Cela indique que les situations de faible accessibilité y sont nombreuses et ne relèvent pas de cas isolés. On va donc poursuivre l’analyse en se focalisant sur ce département afin d’explorer plus en détail les variations locales d’APL.
    """)

        # découpe du tableau en deux parties (5 + 5)
    left_table = top10_table.iloc[:5]
    right_table = top10_table.iloc[5:]

    col_tab1, col_tab2 = st.columns(2)

    with col_tab1:
        st.dataframe(
            left_table,
            hide_index=True,
            column_config={
        "Département": st.column_config.TextColumn(
            "Département",
            width="medium"
        ),
        "Nb": st.column_config.NumberColumn(
            "Nb",
            width="small"
        )
    },
            use_container_width=True
        )

    with col_tab2:
        st.dataframe(
            right_table,
            hide_index=True,
            column_config={
        "Département": st.column_config.TextColumn(
            "Département",
            width="medium"
        ),
        "Nb": st.column_config.NumberColumn(
            "Nb",
            width="small"
        )
    },
            use_container_width=True
        )




st.divider()

st.subheader(
    "Accessibilité potentielle localisée aux médecins généralistes "
    "en France métropolitaine (2023)"
)

col_viz2, col_text2 = st.columns([3.2, 1.8], gap="large")


with col_text2:

    st.markdown("### Sélection du département")

    deps = sorted(
        d for d in generaliste_2023["Departement"].unique()
        if len(d) == 2 and d not in ["96", "97"]
    )

    DEP_CODE = st.selectbox(
        "Choisissez un département",
        deps,
        index=deps.index("45")
    )
    dep_name = (
    departements
    .loc[departements["INSEE_DEP"] == DEP_CODE, "NOM"]
    .values[0]
)


    hide_na = st.checkbox("Masquer les zones sans données", value=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    st.markdown("""
    ### Lecture
    
Dans le Loiret, une large partie des communes présente une APL inférieure ou proche du seuil. Les communes mieux dotées existent, mais elles restent minoritaires et ne forment pas de pôles très marqués. Les écarts observés sont donc réels, mais relativement limités dans l’espace.

Cette configuration suggère que la faible accessibilité n’est pas concentrée sur un secteur précis du département. Elle concerne une grande partie du territoire, ce qui renforce l’idée d’un problème structurel plutôt que localisé.

La carte met en évidence la localisation des communes en difficulté, mais elle ne permet pas à elle seule d’évaluer l’intensité des écarts entre communes.
    """)


def plot_map_relative_to_seuil(gdf, seuil, zoom, hover_col):
    gdf = gdf.copy()
    gdf["apl_rel"] = gdf["APL aux médecins généralistes"] - seuil

    vmax = max(abs(gdf["apl_rel"].min()), abs(gdf["apl_rel"].max()))

    fig = px.choropleth_map(
        gdf,
        geojson=gdf.geometry,
        locations=gdf.index,
        color="apl_rel",
        color_continuous_scale=[
            "#1F4E79",  # très en dessous du seuil
            "#7FB3D5",
            "#EAF4EF",
            "#FFF7DD",  # autour du seuil
            "#FFFFFF"
        ],
        range_color=(-vmax, vmax),
        map_style="carto-positron",
        hover_name=hover_col,
        zoom=zoom,
        center={
            "lat": gdf.geometry.centroid.y.mean(),
            "lon": gdf.geometry.centroid.x.mean()
        }
    )

    fig.update_traces(
    hovertemplate=
    "<b>%{hovertext}</b><br>"
    "APL : %{customdata[0]:.1f}<br>"
    "Écart au seuil : %{z:+.1f}<extra></extra>",
    customdata=gdf[["APL aux médecins généralistes"]]
)


    fig.update_layout(
        coloraxis_colorbar=dict(
            title="Écart au seuil d’APL",
            ticksuffix=""
        ),
        margin={"r": 0, "t": 10, "l": 0, "b": 0}
    )

    return fig


with col_viz2:

    st.markdown(f"### APL moyenne par territoire / Département {DEP_CODE} ({dep_name})")



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
    plot_map_relative_to_seuil(
        gdf,
        seuil_apl,
        zoom=11,
        hover_col="NOM"
    ),
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
    plot_map_relative_to_seuil(
        gdf,
        seuil_apl,
        zoom=7,
        hover_col="NOM"
    ),
    use_container_width=True
)


st.divider()
st.subheader("Distribution de l’APL au sein du département sélectionné")

col_viz, col_text = st.columns([3, 2], gap="large")

df_dep = generaliste_2023[
    generaliste_2023["Departement"] == DEP_CODE
].dropna(subset=["APL aux médecins généralistes"])

fig_hist_dep = px.histogram(
    df_dep,
    x="APL aux médecins généralistes",
    nbins=30,
    color_discrete_sequence=[PALETTE[0]],
    title=f"Répartition des niveaux d’APL – Département {DEP_CODE}"
)

fig_hist_dep.update_layout(
    height=420,
    title_x=0.5,
    yaxis_title="Nombre de communes",
    xaxis_title="APL",
    bargap=0.15
)

fig_hist_dep.update_traces(
    hovertemplate=
    "APL : %{x:.2f}<br>"
    "Nombre de communes : %{y}<extra></extra>"
)

col_viz.plotly_chart(fig_hist_dep, use_container_width=True)





with col_text:

    st.markdown(f"""
### Lecture
L’histogramme permet d’examiner la distribution des niveaux d’APL entre les communes d'un département.

La majorité des communes se situent dans une plage de valeurs relativement resserrée, avec peu de communes présentant des APL très élevées ou très faibles malgré quelques valeurs extrêmes. Cela traduit une accessibilité globalement faible mais assez homogène à l’échelle du département.

Cette lecture confirme ce qui était suggéré par la carte : la situation du Loiret ne s’explique pas par quelques communes très mal dotées, mais par un niveau d’accessibilité modérément faible partagé par un grand nombre de communes.

Ainsi, la faiblesse moyenne de l’APL observée dans le département correspond à une situation largement répandue sur le territoire.
""")


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
quartile_focus = df_focus["quartile_apl"].values[0]
color_focus = couleurs_quartiles[quartile_focus]

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
        color=color_focus,   # ← couleur cohérente
        size=22,
        line=dict(width=2, color="black")
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

Ce graphique permet de comparer les départements entre eux selon deux dimensions : leur niveau moyen d’APL et la dispersion des valeurs d’APL entre leurs communes.

Le Loiret se situe dans une zone caractérisée par une APL moyenne faible associée à une dispersion limitée. Cela signifie que, par rapport aux autres départements, il cumule une accessibilité moyenne défavorable sans pour autant présenter de fortes inégalités internes.

Contrairement à certains départements où une moyenne correcte masque de forts contrastes entre communes, le Loiret présente une situation plus uniforme. La difficulté d’accès aux médecins généralistes y est donc relativement généralisée à l’échelle départementale.

Ce positionnement synthétise les résultats observés sur la carte et l’histogramme et confirme la cohérence de l’analyse menée aux différentes échelles.

""")

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

