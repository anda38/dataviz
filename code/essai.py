import os

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

from shapely.geometry import Point, LineString, Polygon, MultiPolygon

import plotly.express as px

os.chdir("/Users/andalouse/M1/dataviz")

generaliste = pd.ExcelFile("data/aplg.xlsx")
generaliste.sheet_names


generaliste_2023 = pd.read_excel(
    generaliste,
    sheet_name= 2,
    skiprows= 8
)
print(generaliste_2023.head(10))

generaliste_2023.columns

communes = gpd.read_file("data/admincarto/livraison/COMMUNE.shp")

communes.plot()
plt.show()

generaliste_2023["Code commune INSEE"] = generaliste_2023["Code commune INSEE"].astype(str)
communes["INSEE_COM"] = communes["INSEE_COM"].astype(str)


gdf = communes.merge(
    generaliste_2023,
    left_on="INSEE_COM",
    right_on="Code commune INSEE",
    how="left"
)

fig, ax = plt.subplots(figsize=(10, 10))

gdf.plot(
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
    fontsize=14,
    fontweight="bold"
)

ax.axis("off")
plt.show()


gdf["DEP"] = gdf["INSEE_COM"].str[:2]


gdf_dep = gdf.dissolve(
    by="DEP",
    aggfunc={
        "APL aux médecins généralistes": "mean"
    }
)

gdf_dep = gdf_dep.reset_index()
gdf_dep["geometry"] = gdf_dep["geometry"].simplify(500)


gdf_dep["APL aux médecins généralistes"] = pd.to_numeric(
    gdf_dep["APL aux médecins généralistes"],
    errors="coerce"
)


gdf_dep.crs = "EPSG:2154"
gdf_dep = gdf_dep.to_crs("EPSG:4326")

fig = px.choropleth_map(
    gdf_dep,
    geojson=gdf_dep.__geo_interface__,
    locations="DEP",
    featureidkey="properties.DEP",
    color="APL aux médecins généralistes",
    color_continuous_scale="Viridis",
    center={"lat": 46.6, "lon": 2.5},
    map_style="carto-positron",
    zoom=4.8
)

fig.update_layout(
    title={
        "text": "Accessibilité potentielle localisée (APL)<br>aux médecins généralistes par département (France, 2023)",
        "x": 0.5
    },
    margin={"r":0,"t":50,"l":0,"b":0}
)

fig.show()