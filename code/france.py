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

generaliste_2023["Code commune INSEE"] = generaliste_2023["Code commune INSEE"].astype(str)
generaliste_2023.columns

generaliste_2023["Departement"] = generaliste_2023["Code commune INSEE"].str[:2]

generaliste_2023["Departement"]

communes = gpd.read_file("data/admincarto/livraison/COMMUNE.shp")
arrondissements = gpd.read_file("data/admincarto/livraison/ARRONDISSEMENT_MUNICIPAL.shp")
# head the first 10 lines of "NOM" column
print(arrondissements["NOM"].head(10))

arrondissements.columns
communes["INSEE_COM"] = communes["INSEE_COM"].astype(str)

communes.plot()
plt.show()

gdf = communes.merge(
    generaliste_2023,
    left_on="INSEE_COM",
    right_on="Code commune INSEE",
    how="left"
)
gdf["DEP"] = gdf["INSEE_COM"].str[:2]

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


departement = gpd.read_file("data/admincarto/livraison/DEPARTEMENT.shp")[["INSEE_DEP", "NOM", "geometry"]]

departement["geometry"] = departement["geometry"].simplify(
    tolerance=1000, preserve_topology=True
)


gdf2 = departement.merge(
    generaliste_2023,
    left_on="INSEE_DEP",
    right_on="Departement",
    how="left"
)

gdf2.columns

gdf_dep2 = gdf2.dissolve(
    by="INSEE_DEP",
    aggfunc={
        "APL aux médecins généralistes": "mean",
        "NOM": "first"  
    }
).reset_index()

gdf_dep2 = gdf_dep2.to_crs(epsg=4326)

gdf_dep2["APL aux médecins généralistes"] = pd.to_numeric(
    gdf_dep2["APL aux médecins généralistes"], errors="coerce"
)

fig = px.choropleth_map(
    gdf_dep2,
    geojson=gdf_dep2.geometry,
    locations=gdf_dep2.index,
    color="APL aux médecins généralistes",
    color_continuous_scale="Viridis",
    center={"lat": 46.6, "lon": 2.5},
    zoom=4.8,
    map_style="carto-positron",
    hover_name="NOM"   
)

fig.update_layout(
    title={
        "text": "Accessibilité potentielle localisée (APL)<br>aux médecins généralistes par département (France, 2023)",
        "x": 0.5
    },
    margin={"r":0,"t":50,"l":0,"b":0}
)

fig.show()

