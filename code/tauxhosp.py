import pandas as pd
import geopandas as gpd
import streamlit as st  
import plotly.express as px
import matplotlib.pyplot as plt

import pandas as pd
import plotly.express as px


apl = pd.read_excel(
    "data/aplg.xlsx",
    sheet_name=2,
    skiprows=8
)

apl["Code commune INSEE"] = apl["Code commune INSEE"].astype(str)
apl["Departement"] = apl["Code commune INSEE"].str[:2]

apl["APL aux médecins généralistes"] = pd.to_numeric(
    apl["APL aux médecins généralistes"],
    errors="coerce"
)

apl_dep = (
    apl
    .groupby("Departement", as_index=False)
    ["APL aux médecins généralistes"]
    .mean()
)

# -------------------------------------------------
# LOAD MORBIDITY DATA (CSV)
# -------------------------------------------------
morb = pd.read_csv(
    "data/tableau_3.csv",
    sep=";"
)
print(morb.head(10))

# keep only all sexes
morb = morb[
    morb["SEXE"] == "Ensemble"
]
# OPTIONAL: keep one pathology only
morb = morb[
    morb["PATHOLOGIE"] == "01000-Maladies infectieuses et parasitaires"
]

# extract department code (01, 02, …)
morb["Departement"] = morb["ZONE"].str[:2]

morb["Taux standardisé"] = pd.to_numeric(
    morb["Taux standardisé tous âges (en 0/00)"],
    errors="coerce"
)

morb_dep = morb[[
    "Departement",
    "Taux standardisé"
]].drop_duplicates()


df_corr = apl_dep.merge(
    morb_dep,
    on="Departement",
    how="inner"
)


fig = px.scatter(
    df_corr,
    x="APL aux médecins généralistes",
    y="Taux standardisé",
    trendline="ols",
    labels={
        "APL aux médecins généralistes": "APL (médecins généralistes)",
        "Taux standardisé": "Taux standardisé de séjours courts (‰)"
    },
    title="Relation entre APL et accès aux séjours hospitaliers courts<br>(échelle départementale)"
)

fig.update_traces(
    hovertemplate=
    "<b>Département %{customdata[0]}</b><br>"
    "APL : %{x:.2f}<br>"
    "Taux séjours courts : %{y:.2f}‰<extra></extra>",
    customdata=df_corr[["Departement"]]
)

fig.show()
fig = px.histogram(
    morb,
    x="Taux standardisé",
    nbins=20,
    title="Répartition du taux d’accès aux séjours hospitaliers courts<br>par département",
    labels={
        "Taux standardisé": "Taux standardisé (‰)"
    }
)

fig.update_layout(
    bargap=0.1
)

fig.show()

fig = px.histogram(
    apl_dep,
    x="APL aux médecins généralistes",
    nbins=20,
    title="Répartition de l’accessibilité potentielle localisée (APL)<br>aux médecins généralistes par département",
    labels={
        "APL aux médecins généralistes":
        "APL moyenne (consultations accessibles par habitant)"
    }
)

fig.update_layout(bargap=0.1)

fig.show()

