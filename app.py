
from urllib.request import urlopen
import json
with urlopen('https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json') as response:
    countries_geojson = json.load(response)

import pandas as pd
import requests
from flask import Flask, render_template,request,jsonify
import plotly.express as px
import random

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import uuid
import geopandas as gpd
from shapely.geometry import Point
auth_provider = PlainTextAuthProvider(username='cassandra', password='cassandra')
cluster = Cluster(['cassandra'], auth_provider=auth_provider)
session = cluster.connect('weather')

app = Flask(__name__)



@app.route('/weather')
def weather_map():
    # Create plotly figure for weather map
    #data example 
    countries = ['London', 'Liverpool', 'Manchester','Paris','Nantes','Toulouse','Amsterdam','Rotterdam','Delft']
    temperatures = [23, 18, 28, 12, 15, 20, 22, 30, 25]
    humidity = [60, 55, 40, 12, 17, 78, 90, 42, 75]
    #temprature map
    data = {'Country': countries, 'Temperature (Celsius)': temperatures}
    df = pd.DataFrame(data)
    fig = px.choropleth_mapbox(df, geojson=countries_geojson, color='Temperature (Celsius)',
                           locations='Country', featureidkey='properties.name',
                           color_continuous_scale="Reds",
                           center={'lat': 0, 'lon': 0}, mapbox_style='carto-positron', zoom=0)
                          
    fig.update_layout(height=None,width=None,margin={"r":0,"t":0,"l":0,"b":0})

    #humidity map
    dataset2 = {'Country': countries, 'Humidity (%)': humidity}
    df2 = pd.DataFrame(dataset2)
    fig2 = px.choropleth_mapbox(df2, geojson=countries_geojson, color='Humidity (%)',
                           locations='Country', featureidkey='properties.name',
                           color_continuous_scale="Reds",
                           center={'lat': 0, 'lon': 0}, mapbox_style='carto-positron', zoom=0)
                          
    fig2.update_layout(height=None,width=None,margin={"r":0,"t":0,"l":0,"b":0})

    return render_template('weather_map.html', temp_plot=fig.to_html(),humi_plot=fig2.to_html())



@app.route('/getweather', methods=['GET'])
def get_weather():
    api_key = 'a05905ad928bdf01798be26fc3906a0b'  # Replace with your OpenWeatherMap API key
    location = 'New York'     # Replace with desired location
    
    url = f'http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric'
    response = requests.get(url)
    weather_data = response.json()
    
    # Process the weather data
    # Example: Extract temperature from the response
    temperature = weather_data['main']['temp']
    humidity = weather_data['main']['humidity']
    # Return the weather data or render it in a template
    return f'Temperature: {temperature}°C , humidity : {humidity}%'


@app.route('/test', methods=['GET'])
def test():
    # create GeoDataFrame with given cities and their coordinates
    cities = pd.DataFrame({
        'City': ['London', 'Liverpool', 'Manchester', 'Paris', 'Nantes', 'Toulouse', 'Amsterdam', 'Rotterdam', 'Delft'],
        'Latitude': [51.5072, 53.4084, 53.4808, 48.8566, 47.2184, 43.6045, 52.3702, 51.9227, 52.0116],
        'Longitude': [-0.1276, -2.9916, -2.2426, 2.3522, -1.5536, 1.4442, 4.8952, 4.4792, 4.3571]
    })
    cities['Coordinates'] = list(zip(cities.Longitude, cities.Latitude))
    cities['Coordinates'] = cities['Coordinates'].apply(Point)
    temperatures = [23, 18, 28, 12, 15, 20, 22, 30, 25]
    geo_df = gpd.GeoDataFrame(cities, geometry='Coordinates')

    px.set_mapbox_access_token("pk.eyJ1Ijoic3R1ZHkxOTk5IiwiYSI6ImNrZGFmcTVyaTBkb3oycG16Z2JvNWVnYXgifQ.KRT-UOiIZsCBEYLHgGO7HQ")
    fig = px.scatter_mapbox(geo_df,
                        lat=geo_df.geometry.y,
                        lon=geo_df.geometry.x,
                        hover_name=cities.apply(lambda x: f"{x['City']}: {temperatures[x.name]} °C", axis=1),
                        size=temperatures,
                        color_continuous_scale=px.colors.sequential.Redor,
                        color=temperatures,
                        zoom=3)
    fig.update_layout(height=None,width=None,margin={"r":0,"t":0,"l":0,"b":0})
    
    #humidity map
    humidity = [60, 55, 40, 31, 47, 78, 90, 42, 75]
    fig2 = px.scatter_mapbox(geo_df,
                        lat=geo_df.geometry.y,
                        lon=geo_df.geometry.x,
                        hover_name=cities.apply(lambda x: f"{x['City']}: {humidity[x.name]} %", axis=1),
                        size=humidity,
                        color_continuous_scale=px.colors.sequential.Blues,
                        color=humidity,
                        zoom=3)
    fig2.update_layout(height=None,width=None,margin={"r":0,"t":0,"l":0,"b":0})

    return render_template('weather_map.html', temp_plot=fig.to_html(),humi_plot=fig2.to_html())








# Define routes
@app.route('/history', methods=['GET'])
def get():
    rows = session.execute('SELECT * FROM history')
    result = []
    for row in rows:
        result.append({
            'country': row.country,
            'humidity': row.humidity,
            'temperature': row.temperature,
            'timedate': row.timedate
        })

    return render_template('history.html', history=result) 

@app.route('/history', methods=['POST'])
def post():
    country = request.json['country']
    humidity = request.json['humidity']
    temperature = request.json['temperature']
    timedate = request.json['timedate']
    timedate_uuid = uuid.uuid1()

    session.execute(f"INSERT INTO history (country, humidity, temperature, timedate, id) VALUES ('{country}', {humidity}, {temperature}, '{timedate}', {timedate_uuid})")
    return jsonify({'message': 'success'})

@app.route('/history/<uuid:id>', methods=['DELETE'])
def delete(id):
    session.execute(f"DELETE FROM history WHERE id = {id}")
    return jsonify({'message': 'success'})









"""
@app.route('/setup', methods=['GET'])
def setup():
    session.execute("
    CREATE KEYSPACE IF NOT EXISTS weatherdb
    WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};
    ")

    session.set_keyspace('weatherdb')

    session.execute("
        CREATE TABLE IF NOT EXISTS weather (
            id UUID PRIMARY KEY,
            temp float,
            humi float,
            name
        );
    ")
    return f'all good!'
"""
















@app.route('/addData', methods=['GET'])
def addData():
    # List of world cities
    cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose']

    # Generate dummy data for each city
    city_data = []
    for city in cities:
        temperature = random.uniform(0, 40)  # Random temperature between 0 and 40 degrees Celsius
        humidity = random.randint(30, 80)    # Random humidity between 30% and 80%
        city_data.append({
            'city': city,
            'temperature': temperature,
            'humidity': humidity
        })

    # Print the generated data
    for city in city_data:
        print(f"City: {city['city']}, Temperature: {city['temperature']}°C, Humidity: {city['humidity']}%")

if __name__ =="__main__":
    app.run(host='0.0.0.0', debug=True)