import pydeck as pdk
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import streamlit as st
import numpy as np
from shapely.geometry import box


data_path = 'points_test_colours.csv'

# Page config
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded"
)

# Write title
st.title('TAPIOCA CSE test')

# Import data
@st.cache_data
def load_data(path):
    data = gpd.read_file(path)
    return data

df_points = load_data(data_path)
df_points['start_date'] = pd.to_datetime(df_points['start_date'])
df_points['end_date'] = pd.to_datetime(df_points['end_date'])
df_points["lat"] = df_points["lat"].astype(float)
df_points["lon"] = df_points["lon"].astype(float)

# Type selector
#sel_type = st.multiselect('Simple Type', volcanos.SimpleType.unique(), default=volcanos.SimpleType.unique())

#%% Variables to process data

#date_1 = pd.to_datetime("2022-01-01")
#date_2 = pd.to_datetime("2023-03-03")

# Sidebar for date selection
date_1 = st.sidebar.date_input(
    "Start date",
    value=pd.to_datetime("2022-01-01"),
    min_value=pd.to_datetime("2020-01-01"),
    max_value=pd.to_datetime("2030-12-31")
)
date_2 = st.sidebar.date_input(
    "End date",
    value=pd.to_datetime("2024-01-03"),
    min_value=pd.to_datetime("2020-01-01"),
    max_value=pd.to_datetime("2030-12-31")
)

# Convert to datetime if needed
date_1 = pd.to_datetime(date_1)
date_2 = pd.to_datetime(date_2)

#cell_size = 0.08  # taille des carrés (en degrés)
cell_size = st.sidebar.slider(
    "Cell size (in degrees)",  # label
    min_value=0.01,            # plus petit carré possible
    max_value=1.0,             # plus grand carré
    value=0.08,                # valeur par défaut
    step=0.01                  # incrément
)


#%% Functions to process data

def process_data(df, date_1, date_2): 
    # time filtering
    df_time = df[(df["start_date"] >= date_1) & (df["start_date"] <= date_2)]
    print(df_time)
    # Convert in a geodataframe
    gdf_points = gpd.GeoDataFrame(
        df_time,
        geometry=gpd.points_from_xy(df_time.lon, df_time.lat),
        crs="EPSG:4326"
    )
    return gdf_points

def create_grid(gdf, cell_size) :
    # Définir l'étendue de ta carte (bbox)
    minx = gdf["lon"].min() -2  # ouest
    maxx = gdf["lon"].max() +2 # est
    miny = gdf["lat"].min() -2 # sud
    maxy = gdf["lat"].max() +2# nord
    # Générer la grille
    grid_cells = []
    for x in np.arange(minx, maxx, cell_size):
        for y in np.arange(miny, maxy, cell_size):
            grid_cells.append(box(x, y, x + cell_size, y + cell_size))
    grid = gpd.GeoDataFrame(geometry=grid_cells, crs="EPSG:4326") # simple grid created
    
    # Spatial joint, add a gdf column with number of cell corresponding to each point, NaN possible if no matching cell
    joined = gpd.sjoin(gdf, grid, how="left", predicate="within")
    
    # Index of the cell with points included inside
    agg = joined.groupby("index_right").agg({
        "names": lambda x: list(x)
    })
    # agg = table with index of cells that have points inside and the name of the points 
    
    # grid object with name of point inside each cell and number (fill 'names' and 'count' row in grid)
    grid["names"] = agg["names"]
    grid["names"] = grid["names"].apply(lambda x: x if isinstance(x, list) else [])
    grid["count"] = grid["names"].apply(len)

    return grid

#%% Process data

gdf_data = process_data(df_points, date_1, date_2)
grid = create_grid(gdf_data, cell_size)

#%% Map

# Convertir en GeoJSON
grid_json = grid.__geo_interface__

# grid layer
layer = pdk.Layer(
    "GeoJsonLayer",
    grid_json,
    stroked=True,
    get_line_color=[0, 0, 0],
    line_width_min_pixels=1,
    pickable=True,
    # color of the cell
    get_fill_color=""" 
        properties.count > 0
        ? [255, 0, 0, 120]
        : [0, 0, 0, 0]
    """
)

# Pydeck layer
points_layer = pdk.Layer(
    "ScatterplotLayer",
    data = gdf_data,
    get_position= '[lon, lat]',
    get_fill_color=[255, 0, 0, 180],  # rouge
    #get_fill_color='k',
    get_radius=200,
    pickable=True
)


# Initial view
view_state = pdk.ViewState(
    latitude=-8.05,
    longitude=-34.9,
    zoom=10
)

# Map and all layers 
pdk_map= pdk.Deck(
    layers=[layer, points_layer],
    map_style='light',
    initial_view_state=view_state,
    tooltip={"text": "{names}"}
)

pdk_map

# Display pydeck map
st.pydeck_chart(pdk_map)

