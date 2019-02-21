# -*- coding: utf-8 -*-
"""
Created on Wed Mar 28 01:47:54 2018

@author: Adeola
"""

'''
This project looks to highlight tracts within New YorkCity which would be a great fit for a new coffee shop. The selected tracts are supposed to be:
    be within walkin distance of a subway stop (0.25miles),
    have less than 3 existing competitors, and 
    have more than 24 females within 18 and 49
    have an income above the averege city income per tract.
'''
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import Point
from fiona.crs import from_epsg
from shapely.ops import cascaded_union

# Read in the data
tracts = gpd.read_file(r'G:\pypy\coffee\tl_2012_36_tract_nysp.shp')
boros = gpd.read_file(r'G:\pypy\coffee\boroughs.shp')
demography = pd.read_csv(r'G:\pypy\coffee\demog_data.csv')
coffee_data = pd.read_csv(r'G:\pypy\coffee\nyc_coffee.txt', '\t')
subway_stops = gpd.read_file(r'G:\pypy\coffee\subway_stations.shp')

# To extract county part of the fips code and define the counties to a list then use the code to remove those counties from state map
nyc_counties = boros.bcode.str.slice(2,5).tolist()
nyc_tract = tracts.loc[tracts['COUNTYFP'].isin (nyc_counties)]

#To create the tracts shapefile that clipped to the shoreline
nyc_tracts= gpd.overlay(nyc_tract, boros, how='intersection')

#Change the id field to string just as the tracts data is string
demography['id'] = demography['id'].astype('str')
#To merge the tracts with demographic data
nyc_tracts_data= nyc_tracts.merge(demography, left_on='GEOID', right_on= 'id')
#To form geometry points
points = [Point(xy) for xy in zip(coffee_data.longitude_2010, coffee_data.latitude_2010)]
#To transform to a geodataframe
coffee_shops = gpd.GeoDataFrame(coffee_data, geometry = points)
#To change coffeeshop projection to the tracts projection
coffee_shops.crs = from_epsg(4326) #Setting a crs for the object first before transforming
# Then set it to that of the tracts
nyc_tracts_data.crs = tracts.crs
# Set the projected geodataframe to a variable
coffee_shops_proj = coffee_shops.to_crs(nyc_tracts_data.crs)

#To perform the spatial join
coffee_shops_w_tracts_id= gpd.sjoin(coffee_shops_proj, nyc_tracts_data, how= 'left', op= 'within')
#To create a dataframe of number of coffee shops per tracts
shops_count_df= pd.DataFrame(coffee_shops_w_tracts_id.groupby('GEOID')['abi'].count())
shops_count_df.columns = ['count']
#To join tracts data with coffeeshops per tract dataframe
tracts_w_counts= nyc_tracts_data.merge(shops_count_df, left_on= 'GEOID', how= 'left', right_index= True)
#To replace Nans with 0 so as not to throw off calculations
tracts_w_counts['count'] = tracts_w_counts['count'].fillna(0)
#To create the rate of females per census tract
#To get the average income per tract
avg_income= demography.moe_medinc.mean()

#To select the tracts that have less than 3 competitors,over 24 females & above average income
selected_tracts=tracts_w_counts.loc[(tracts_w_counts['count']<3) 
                                    & (tracts_w_counts['per_fem']>24)
                                    & (tracts_w_counts['moe_medinc']>avg_income)]


# To create the 0.25mile (1320ft) buffer and Cascade the buffers
buffer_quater_mile= subway_stops.buffer(1320) #1320 feet is ud=sed because the crs unit is in feet
buffer_1_4_mile= cascaded_union(buffer_quater_mile)

#To create a geoseries of the dissolved buffers and assign a crs
buffer_gdf= gpd.GeoSeries(buffer_1_4_mile)
buffer_gdf.crs = buffer_quater_mile.crs

#To overlay the earlier selected tracts with the buffered tracts
optimum_areas= gpd.overlay(selected_tracts, gpd.GeoDataFrame(['dissolved_buff'], columns= ['geo_name'], geometry= buffer_gdf ), how = 'intersection')

# VISUALIZATIONS #
plt.style.use('seaborn-white')

#To view coffee shop lcations over NYC tracts
ax=nyc_tracts_data.plot(figsize=(10,10))
coffee_shops_proj.plot(color='black', ax=ax, markersize=5)
plt.tight_layout()
fig=ax.get_figure()

#To view the optimum areas for citing a coffee shop draped over NYC tracts
ax= optimum_areas.plot(figsize= (10,10), facecolor='brown', edgecolor='brown')
nyc_tracts_data.plot(ax=ax, alpha= 0.3, facecolor = 'grey')
plt.tight_layout()
fig=ax.get_figure()
