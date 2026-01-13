import pandas as pd
import geopandas as gpd
from geopy.geocoders import Nominatim
from shapely import MultiLineString
from datetime import datetime, timedelta
import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import numpy as np
import branca.colormap as cm



def plot_folium(gdf, columncolor = None, colormap='RdYlBu_r', hovercolumnlist = None):
    '''gdf darf verschiedene geometrien haben, aber geometrycollections werden rausgeworfen hier'''
    gdf = gdf.to_crs(epsg=4326)

    # 'farbe' spalte kodieren
    if columncolor:
        # falls column type is in string format (non-numerical)
        if isinstance(gdf[columncolor][0], str):
            print('Columncolor is in string format')
            allstrings = gdf[columncolor].unique()
            catdict = {}
            for i in range(len(allstrings)):
                catdict[allstrings[i]] = i

            gdf['cat'] = gdf[columncolor].apply(lambda x: catdict[x])

            norm = plt.Normalize(gdf['cat'].min(), gdf['cat'].max())
            cmap = plt.get_cmap(colormap)
            gdf['farbe'] = gdf['cat'].apply(lambda x: cmap(norm(x)))
            gdf['farbe'] = gdf['farbe'].apply(lambda x: '#{:02x}{:02x}{:02x}'.format(int(x[0]*255), int(x[1]*255), int(x[2]*255)))
            print(f'Erste Farbe: {gdf['farbe'][0]}')

            # legende vorbereiten (colormap)
            cmap=plt.colormaps[colormap](np.linspace(0,1, 4))
            hexcolors = ['#{:02x}{:02x}{:02x}'.format(int(color[0]*255), int(color[1]*255), int(color[2]*255)) for color in cmap]

            # Define a linear colormap with specific decimal precision
            colormap = cm.LinearColormap(colors=hexcolors,vmin=gdf['cat'].min(), vmax=gdf['cat'].max())


        else: # if numerical
            print('Columncolor is in numerical format')
            norm = plt.Normalize(gdf[columncolor].min(), gdf[columncolor].max())
            cmap = plt.get_cmap(colormap)
            gdf['farbe'] = gdf[columncolor].apply(lambda x: cmap(norm(x)))
            gdf['farbe'] = gdf['farbe'].apply(lambda x: '#{:02x}{:02x}{:02x}'.format(int(x[0]*255), int(x[1]*255), int(x[2]*255)))
            print(f'Erste Farbe: {gdf['farbe'][0]}')

            # legende vorbereiten (colormap)
            cmap=plt.colormaps[colormap](np.linspace(0,1, 4))
            hexcolors = ['#{:02x}{:02x}{:02x}'.format(int(color[0]*255), int(color[1]*255), int(color[2]*255)) for color in cmap]

            # Define a linear colormap with specific decimal precision
            colormap = cm.LinearColormap(colors=hexcolors,vmin=gdf[columncolor].min(), vmax=gdf[columncolor].max())
        colormap.caption = 'Legende'
    else:
        gdf['farbe'] = '#3D74B6'


    # rule out geometrycollections
    gdf['type'] = gdf.type
    print(f'The gdf contains {len(gdf)} rows with the columns {gdf.columns}')
    gdf = gdf[gdf['type'] != 'GeometryCollection'].reset_index(drop=True)
    print(f'The gdf contains {len(gdf)} rows after the removal of GeometryCollections')


    # split up into Points, Linestring and Polygons
    gdf_points = gdf[gdf['type'].isin(['Point', 'MultiPoint'])]
    gdf_lines = gdf[gdf['type'].isin(['LineString', 'MultiLineString'])]
    gdf_polygons = gdf[gdf['type'].isin(['Polygon', 'MultiPolygon'])]

    # create popups with all fields of the gdf
    print([x for x in gdf_points.columns.values if x != 'geometry'])
    pts_popup = folium.GeoJsonPopup(fields = [x for x in gdf_points.columns.values if x != 'geometry'])
    lns_popup = folium.GeoJsonPopup(fields = [x for x in gdf_lines.columns.values if x != 'geometry'])
    ply_popup = folium.GeoJsonPopup(fields = [x for x in gdf_polygons.columns.values if x != 'geometry'])

    ptshover = folium.GeoJsonTooltip(fields=hovercolumnlist)
    lnshover = folium.GeoJsonTooltip(fields=hovercolumnlist)
    plyhover = folium.GeoJsonTooltip(fields=hovercolumnlist)


    # set up map 
    firsttype = gdf['type'][0]
    if firsttype == 'Point':
        firstloc = [gdf['geometry'][0].y, gdf['geometry'][0].x]
    elif firsttype == 'MultiPoint':
        firstloc = [gdf['geometry'][0].geoms[0].y, gdf['geometry'][0].geoms[0].x]
    elif firsttype == 'LineString':
        firstloc = [gdf['geometry'][0].coords.xy[1][0], gdf['geometry'][0].coords.xy[0][0]]
    elif firsttype == 'MultiLineString':
        firstloc = [gdf['geometry'][0].geoms[0].coords.xy[1][0], gdf['geometry'][0].geoms[0].coords.xy[0][0]]
    elif firsttype == 'Polygon':
        firstloc = [gdf['geometry'][0].centroid.y, gdf['geometry'][0].centroid.x]
    elif firsttype == 'MultiPolygon':
        firstloc = [gdf['geometry'][0].geoms[0].centroid.y, gdf['geometry'][0].geoms[0].centroid.x]

    # convert into geojson and 4326
    gdf_pts_folium = gdf_points.to_crs(epsg=4326).to_json()
    gdf_lns_folium = gdf_lines.to_crs(epsg=4326).to_json()
    gdf_ply_folium = gdf_polygons.to_crs(epsg=4326).to_json()

    m = folium.Map(location = firstloc, zoom_start=15, tiles= 'CartoDB positron')

    # add to the map via feature_groups
    if len(gdf_points) > 0:
        print('Points wird ausgeführt')
        fg_pts = folium.FeatureGroup(name='Points', show=True).add_to(m)
        folium.GeoJson(data = gdf_pts_folium, zoom_on_click=False, marker=folium.CircleMarker(radius=2), style_function=lambda feature: {
            'fillColor': feature['properties']['farbe'],
            'color': feature['properties']['farbe'],
            'weight': 5
        },
        popup = pts_popup, tooltip=ptshover).add_to(fg_pts)

    if len(gdf_lines) > 0:
        print('Lines wird ausgeführt')
        fg_lines = folium.FeatureGroup(name='Lines', show=True).add_to(m)
        folium.GeoJson(data = gdf_lns_folium, zoom_on_click=False, style_function=lambda feature: {
            'fillColor': feature['properties']['farbe'],
            'color': feature['properties']['farbe'],
            'weight': 5
        },
        popup=lns_popup, tooltip=lnshover).add_to(fg_lines)

    if len(gdf_polygons) > 0:
        print('Polygons wird ausgeführt')
        fg_polygons = folium.FeatureGroup(name='Polygons', show=True).add_to(m)
        folium.GeoJson(data = gdf_ply_folium, zoom_on_click=False, style_function=lambda feature: {
            'fillColor': feature['properties']['farbe'],
            'color': feature['properties']['farbe'],
            'weight': 2,
            'fillOpacity': 0.8
        },
        popup=ply_popup, tooltip=plyhover).add_to(fg_polygons)

    tile = folium.TileLayer(
        tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr = 'Esri',
        name = 'Esri Satellite',
        overlay = False,
        control = True
       ).add_to(m)
    folium.TileLayer('CartoDB voyager').add_to(m)

    if columncolor:
        colormap.add_to(m)
    m.add_child(folium.map.LayerControl())
    
    return m



startort = st.text_input(label='Startort eingeben')
endort = st.text_input(label='Zielort eingeben')
# time = "08:30"

# ------------- Geocoding: von Ortsnamen zu Koordinaten 
geolocator = Nominatim(user_agent="my_app_nushejan1")
# store coords (dir(startcoords) für alle methods)
startcoords = geolocator.geocode(startort)
startx, starty = startcoords.longitude, startcoords.latitude
print('gefundene Adresse: ', startcoords.address)
# st.write('gefundene Adresse: ', startcoords.address)
endcoords = geolocator.geocode(endort)
endx, endy = endcoords.longitude, endcoords.latitude
print('gefundene Adresse: ', endcoords.address)
# st.write('gefundene Adresse: ', endcoords.address)


# ------------ ÖV: Stationen finden
response_stationfinder_start = requests.get(
    "http://transport.opendata.ch/v1/locations",
    params={
        'x':startx,
        'y':starty
    }
).json()
response_stationfinder_end = requests.get(
    "http://transport.opendata.ch/v1/locations",
    params={
        'x':endx,
        'y':endy
    }
).json()

def find_next_station(response):
    #listofstations los
    los = []
    for i in response['stations']:
        if not pd.isna(i['icon']):
            # print(i)
            los.append(i)
    # iterate through options and return train if found, else take the first option with a valid icon
    trainconnections = []
    othervehicels = []
    for s in los:
        # print('iterate connections: ', s)
        if s['icon'] == 'train':
            print('train connection here: ', s)
            trainconnections.append(s)
        else:
            othervehicels.append(s)
    
    if len(trainconnections) != 0:
        return trainconnections[0] # erste train connection aus der trainliste returnen
    else:
        return othervehicels[0]

startplatz_json = find_next_station(response=response_stationfinder_start)
startplatz = startplatz_json['name']
print('Startplatz: ', startplatz)
# st.write('Startplatz: ', startplatz)
endplatz_json = find_next_station(response=response_stationfinder_end)
endplatz = endplatz_json['name']
print('Endplatz: ', endplatz)
# st.write('Endplatz: ', endplatz)


# -------------- ÖV-Wegzeit berechnen
# Make a request to get connections
response_öv_zeiten = requests.get(
    "http://transport.opendata.ch/v1/connections",
    params={
        "from": startplatz,
        "to": endplatz,
        #"via": viaort,
        "time": zeit
    }
).json()
# Print the whole response to see what it looks like
# pprint(response_öv_zeiten['connections'][0])
öv_duration = response_öv_zeiten['connections'][0]['duration']

# -------------- MIV-Wegzeiten berechnen
url = f"http://router.project-osrm.org/route/v1/driving/{startx},{starty};{endx},{endy}"
response_miv = requests.get(url, params={
    "overview": "full",      # Get full geometry
    "steps": "true",         # Get turn-by-turn instructions
    "geometries": "geojson"  # Return as GeoJSON
}).json()
miv_duration = response_miv["routes"][0]["duration"]
miv_distance = response_miv["routes"][0]["distance"]
print(f"==>> miv_duration: {miv_duration}")
# st.write(f"==>> miv_duration: {miv_duration}")
# miv_distance = response_miv["routes"][0]["distance"]


# ------------- Wegzeiten vergleichen und entsprechende Karte plotten
hours, minutes, seconds = map(int, öv_duration[3:].split(':'))
öv_duration_time = timedelta(hours=hours, minutes=minutes, seconds=seconds)
print(f"==>> öv_duration_time: {öv_duration_time}")
# st.write(f"==>> öv_duration_time: {öv_duration_time}")
miv_duration_time = timedelta(seconds = miv_duration)
print(f"==>> miv_duration_time: {miv_duration_time}")
# st.write(f"==>> miv_duration_time: {miv_duration_time}")


# ------------- Messages ausgeben
if öv_duration_time < timedelta(seconds=30*60):
    print(f'Die Zugfahrt dauert lediglich {öv_duration_time} min und somit kannst du den ÖV nehmen.')
    fortbewegungsmittel = 'öv'
elif öv_duration_time > miv_duration_time:
    dif = (öv_duration_time-miv_duration_time).seconds/60
    print(f'Du bist mit dem Auto rund {round(dif, 1)} min schneller.')

    if öv_duration_time > 1.5*miv_duration_time:
        faktor = öv_duration_time.seconds/miv_duration_time.seconds
        print(f'Die Zugfahrt dauert {round(faktor,1)} so lange wie die Autofahrt. Somit darfst du mit dem Auto fahren.')
        fortbewegungsmittel = 'miv'
    else:
        faktor = öv_duration_time.seconds/miv_duration_time.seconds
        print(f'Die Zugfahrt dauert nur {round(faktor,1)} so lange wie die Autofahrt. Somit musst du den ÖV nehmen, du armes Schwein haha.')
        fortbewegungsmittel = 'öv'

else:
    dif = (miv_duration_time-öv_duration_time).seconds/60
    print(f'Du bist mit dem ÖV rund {dif} min schneller. Daher nimmst du logischerweise den ÖV.')
    fortbewegungsmittel = 'öv'

# ------------------- Karte ÖV
# Teilabschnitte mit den einzelnen Zwischenstopps
if fortbewegungsmittel == 'öv':
    sections = response_öv_zeiten['connections'][0]['sections'] 
    alle_koordinaten = []
    for s in sections:
        print('s: ', s)
        print('len(s): ', len(s))
        print('s[journey]: ', s['journey'])
        if pd.isna(s['journey']):
            print('hier musste laufen und zwar von ... nach ...')
            print(s['departure']['station']['coordinate'])
            print(s['arrival']['station']['coordinate'])
            alle_koordinaten.append([s['departure']['station']['coordinate']['y'], s['departure']['station']['coordinate']['x']])
            alle_koordinaten.append([s['arrival']['station']['coordinate']['y'], s['arrival']['station']['coordinate']['x']])
        else: # nicht laufen
            print('passList von Nicht-Laufweg: ', s['journey']['passList'])
            for station in s['journey']['passList']:
                print('Name der Station: ', station['station']['name'])
                print('Coords der Station: ', station['station']['coordinate'])
                alle_koordinaten.append([station['station']['coordinate']['y'], station['station']['coordinate']['x']])
    # ÖV Wegkarte
    lines2 = MultiLineString([alle_koordinaten])
    övweg = gpd.GeoDataFrame(geometry=[lines2], crs = 'EPSG:4326')
    route = f'{startort} -> {endort}'
    dauer = f'{round(öv_duration/60, 1)} min'
    övweg['Route'] = [route]
    övweg['Dauer'] = [dauer]
    m2 = f.plot_folium(övweg, hovercolumnlist=['route'])
    st_data = st_folium(m2, height = 500, width = 1300, returned_objects=[])

# ---------------- Karte MIV
else:
    path = response_miv['routes'][0]['geometry']['coordinates']
    lines = MultiLineString([path])
    # lines
    gdf = gpd.GeoDataFrame(geometry=[lines], crs = 'EPSG:4326')
    route = f'{startort} -> {endort}'
    dauer = f'{round(miv_duration/60, 1)} min'
    dist = f'{round(miv_distance/1000,1)} km'
    gdf['Route'] = [route]
    gdf['Dauer'] = [dauer]
    gdf['Distanz'] = [dist]
    m = f.plot_folium(gdf, hovercolumnlist=['Route', 'Dauer', 'Distanz'])
    st_data = st_folium(m, height = 500, width = 1300, returned_objects=[])

