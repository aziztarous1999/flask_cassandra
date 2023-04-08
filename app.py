
from urllib.request import urlopen
import json
with urlopen('https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json') as response:
    countries_geojson = json.load(response)
import pandas as pd
import requests
from flask import Flask, render_template,request,jsonify,redirect, url_for
import plotly.express as px
import random
import datetime
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import uuid
import geopandas as gpd
from shapely.geometry import Point
from geopy.geocoders import Nominatim

import smtplib
from email.mime.text import MIMEText
import time


#aziz
auth_provider = PlainTextAuthProvider(username='cassandra', password='cassandra')
cluster = Cluster(['cassandra'], auth_provider=auth_provider)
session = cluster.connect('weather')

app = Flask(__name__)




@app.route('/myweather', methods=['GET'])
def myweather():
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
                        mapbox_style='light',
                        zoom=3)
    fig.update_layout(height=None,width=None,margin={"r":0,"t":0,"l":0,"b":0})
    
    #humidity map
    humidity = [60, 55, 40, 31, 47, 78, 90, 42, 75]
    fig2 = px.scatter_mapbox(geo_df,
                        lat=geo_df.geometry.y,
                        lon=geo_df.geometry.x,
                        hover_name=cities.apply(lambda x: f"{x['City']}: {humidity[x.name]} %", axis=1),
                        size=humidity,
                        color_continuous_scale=px.colors.sequential.Bluered_r,
                        color=humidity,
                        mapbox_style='light',
                        zoom=3)
    fig2.update_layout(height=None,width=None,margin={"r":0,"t":0,"l":0,"b":0})

    return render_template('weather_map.html', temp_plot=fig.to_html(),humi_plot=fig2.to_html())








# Define routes
@app.route('/allhistory', methods=['GET'])
def get():
    rows = session.execute('SELECT * FROM history')
    result = []
    for row in rows:
        result.append({
            'country': row.country,
            'humidity': row.humidity,
            'temperature': row.temperature,
            'timedate': row.timedate,
            'id':row.id,
            'temp_max':row.temp_max,
            'temp_min':row.temp_min,
            'weather_description':row.weather_description,
            'weather_details':row.weather_details
        })

    return render_template('history.html', history=result) 


@app.route('/history/<item_id>', methods=['POST'])
def delete(item_id):
    session.execute(f"DELETE FROM history WHERE id = {item_id}")
    return redirect(url_for('get'))


@app.route('/history', methods=['POST'])
def post():
    city = request.form.get('city')
    api_key = 'a05905ad928bdf01798be26fc3906a0b'  # Replace with your OpenWeatherMap API key
    url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'
    response = requests.get(url)
    weather_data = response.json()
    # Process the weather data
    # Example: Extract temperature from the response
    temperature = '{:.2f}'.format(weather_data['main']['temp'])
    humidity = weather_data['main']['humidity']
    temp_max = weather_data['main']['temp_max']
    temp_min = weather_data['main']['temp_min']
    weather_description = weather_data['weather'][0]['main']
    weather_details = weather_data['weather'][0]['description']
    temp = float(temperature)
    timedate = datetime.datetime.now()
    timedate_uuid = uuid.uuid1()

    session.execute(f"INSERT INTO history (country, humidity, temperature, timedate, id,temp_max,temp_min,weather_description,weather_details) VALUES ('{city}', {humidity}, {temp}, '{timedate}', {timedate_uuid}, '{temp_max}','{temp_min}','{weather_description}','{weather_details}')")
    return redirect(url_for('get'))



#malek



def get_location_data(ip_address):
    response = requests.get(f"http://api.ipstack.com/{ip_address}?access_key=53aad8b231335f8e3a6ca4b39e4d5e61")
    data = response.json()
    location = f"{data['city']}, {data['region_name']}, {data['country_name']}"
    geolocator = Nominatim(user_agent="my_app")
    location = geolocator.geocode(location)
    longitude = location.longitude
    latitude = location.latitude
    zoom = 15
    print(longitude)
    print(latitude)
    print(location)
    return {'longitude': longitude, 'latitude': latitude, 'zoom': zoom,'location':location}



@app.route("/", methods=["GET", "POST"])
def hello():
    
    # Get the IP address of the client
    ip_address ='afd9-197-3-228-20.eu.ngrok.io' #request.remote_addr
    # Make a request to IPStack to get the location information
    response = requests.get(f'http://api.ipstack.com/{ip_address}?access_key=53aad8b231335f8e3a6ca4b39e4d5e61')
    location_data = response.json()
    print(location_data)
    # Extract the relevant location information
    city = location_data['city']
    region = location_data['region_name']
    country = location_data['country_name']

    # Return the location information to the client
    print(city)
    print(region)
    print(country)
    # Make a request to OpenWeather to get the weather information
    response = requests.get(f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid=38afed0f43d4911d6ce1a06f7dacbf68')
    weather_data = response.json()
    print(response)
    # Extract the relevant weather information
    temperature = round(weather_data['main']['temp'] - 273.15, 2) # convert to Celsius and round to 2 decimal places
    description = weather_data['weather'][0]['description']  

    print(temperature)
    print(description)

    #partie map
      # create GeoDataFrame with given cities and their coordinates
    cities = pd.DataFrame({
        'City': ['London', 'Liverpool', 'Manchester', 'Paris', 'Nantes', 'Toulouse', 'Amsterdam', 'Rotterdam', 'Delft'],
        'Latitude': [52.370216,52.011577,53.408371, 51.507351, 53.480759, 47.218371,48.856613,51.92442,  43.604652],
        'Longitude': [4.895168, 4.357068, -2.991573, -0.127758, -2.242631, -1.553621, 2.352222, 4.477733,1.444209]
    })
    cities['Coordinates'] = list(zip(cities.Longitude, cities.Latitude))
    cities['Coordinates'] = cities['Coordinates'].apply(Point)
    #temperatures = [23, 18, 28, 12, 15, 20, 22, 30, 25]

    #metric 
    temperatures = []
    humidity = []

    #getting temp and humidity from database
    rows = session.execute('SELECT * FROM history')
    for row in rows:
        temperatures.append(row.temperature)
        humidity.append(row.humidity)



    geo_df = gpd.GeoDataFrame(cities, geometry='Coordinates')

    px.set_mapbox_access_token("pk.eyJ1Ijoic3R1ZHkxOTk5IiwiYSI6ImNrZGFmcTVyaTBkb3oycG16Z2JvNWVnYXgifQ.KRT-UOiIZsCBEYLHgGO7HQ")
    fig = px.scatter_mapbox(geo_df,
                        lat=geo_df.geometry.y,
                        lon=geo_df.geometry.x,
                        hover_name=cities.apply(lambda x: f"{x['City']}: { round(temperatures[x.name] ,2) } °C", axis=1),
                        size=cities.apply(lambda x: round(temperatures[x.name]), axis=1),
                        color_continuous_scale=px.colors.sequential.Redor,
                        color=cities.apply(lambda x: round(temperatures[x.name]), axis=1),
                        mapbox_style='light',
                        zoom=3)
    fig.update_layout(height=None,width=None,margin={"r":0,"t":0,"l":0,"b":0})

    #humidity map
    #humidity = [60, 55, 40, 31, 47, 78, 90, 42, 75]
    fig2 = px.scatter_mapbox(geo_df,
                        lat=geo_df.geometry.y,
                        lon=geo_df.geometry.x,
                        hover_name=cities.apply(lambda x: f"{x['City']}: {humidity[x.name]} %", axis=1),
                        size=humidity,
                        color_continuous_scale=px.colors.sequential.Blues,
                        color=humidity,
                        mapbox_style='light',
                        zoom=3)
    fig2.update_layout(height=None,width=None,margin={"r":0,"t":0,"l":0,"b":0})




    #forcast
    ip_address ='afd9-197-3-228-20.eu.ngrok.io' #request.remote_addr
    print(ip_address)
    # Make a request to IPStack to get the location information
    response = requests.get(f'http://api.ipstack.com/{ip_address}?access_key=53aad8b231335f8e3a6ca4b39e4d5e61')
    location_data = response.json()
    print(location_data)
    # Extract the relevant location information
    city = location_data['city']
    region = location_data['region_name']
    country = location_data['country_name']
    api_key = 'b4e44ae423a1d68110e989819ca31261' # replace with your API key

    url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric' #
    resp = requests.get(url).json()
    forecast_data = []
    # for i in range(7):
    #   date_time = resp['list'][i]['dt_txt']
    #   date = date_time.split()[0]
    #   time = date_time.split()[1][:-3]
    #   temp = resp['list'][i]['main']['temp']
    #   feels_like = resp['list'][i]['main']['feels_like']
    #   humidity = resp['list'][i]['main']['humidity']
    #   description = resp['list'][i]['weather'][0]['description']
    #   icon_id = resp['list'][i]['weather'][0]['icon']
    #   wind_speed = resp['list'][i]['wind']['speed']
    #   forecast_data.append({
    #           'date': date,
    #           'time': time,
    #           'temp': temp,
    #           'feels_like': feels_like,
    #           'humidity': humidity,
    #           'description': description,
    #           'icon_id': icon_id,
    #           'wind_speed': wind_speed,
    #           'location':city
    #       })
    #   print (forecast_data)
    print(resp)
    # date_time = resp['list']['dt_txt']
    # date = date_time.split()[0]
    # time = date_time.split()[1][:-3]
    temp = resp['main']['temp']
    feels_like = resp['main']['feels_like']
    humidity = resp['main']['humidity']
    description = resp['weather'][0]['description']
    icon_id = resp['weather'][0]['icon']
    wind_speed = resp['wind']['speed']
    forecast_data.append({
            # 'date': date,
            # 'time': time,
            'temp': temp,
            'feels_like': feels_like,
            'humidity': humidity,
            'description': description,
            'icon_id': icon_id,
            'wind_speed': wind_speed,
            'location':city
        })
    
    #tunis current weather
    url = f'https://api.openweathermap.org/data/2.5/weather?q=tunis&appid=b4e44ae423a1d68110e989819ca31261&units=metric' #
    resp = requests.get(url).json()

    current_time = datetime.datetime.now()
    one_hour = datetime.timedelta(hours=1)
    new_time = current_time + one_hour

    formatted_time = new_time.strftime("%I:%M %p")
    formatted_date = current_time.strftime("%A, %d %B %Y")
    tunisObj ={
        "description" : resp['weather'][0]['description'],
        "temp" : resp['main']['temp'],
        "curtime" : formatted_time,
        "curdate" : formatted_date
    }


    return render_template('index.html', temp_plot=fig.to_html(),humi_plot=fig2.to_html(), forecast_data=forecast_data,tunisObj=tunisObj)



# Get the IP address of the client
ip_address ='afd9-197-3-228-20.eu.ngrok.io' #request.remote_addr
# Make a request to IPStack to get the location information
response = requests.get(f'http://api.ipstack.com/{ip_address}?access_key=53aad8b231335f8e3a6ca4b39e4d5e61')
location_data = response.json()
print(location_data)
# Extract the relevant location information
city = location_data['city']
region = location_data['region_name']
country = location_data['country_name']

@app.route("/profil")
def profil():
  zoom = 15
  return render_template('profil.html',location_data=get_location_data(ip_address), active_page='coordination')

@app.route('/profil/locations')
def locations():
    return render_template('locations.html',location_data=get_location_data(ip_address),  active_page='locations')



@app.route('/weather')
def weather():
    ip_address ='afd9-197-3-228-20.eu.ngrok.io' #request.remote_addr
    print(ip_address)
    # Make a request to IPStack to get the location information
    response = requests.get(f'http://api.ipstack.com/{ip_address}?access_key=53aad8b231335f8e3a6ca4b39e4d5e61')
    location_data = response.json()
    print(location_data)
    # Extract the relevant location information
    city = location_data['city']
    region = location_data['region_name']
    country = location_data['country_name']
    api_key = 'b4e44ae423a1d68110e989819ca31261' # replace with your API key

    url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric' #
    resp = requests.get(url).json()
    forecast_data = []
    # for i in range(7):
    #   date_time = resp['list'][i]['dt_txt']
    #   date = date_time.split()[0]
    #   time = date_time.split()[1][:-3]
    #   temp = resp['list'][i]['main']['temp']
    #   feels_like = resp['list'][i]['main']['feels_like']
    #   humidity = resp['list'][i]['main']['humidity']
    #   description = resp['list'][i]['weather'][0]['description']
    #   icon_id = resp['list'][i]['weather'][0]['icon']
    #   wind_speed = resp['list'][i]['wind']['speed']
    #   forecast_data.append({
    #           'date': date,
    #           'time': time,
    #           'temp': temp,
    #           'feels_like': feels_like,
    #           'humidity': humidity,
    #           'description': description,
    #           'icon_id': icon_id,
    #           'wind_speed': wind_speed,
    #           'location':city
    #       })
    #   print (forecast_data)
    print(resp)
    # date_time = resp['list']['dt_txt']
    # date = date_time.split()[0]
    # time = date_time.split()[1][:-3]
    temp = resp['main']['temp']
    feels_like = resp['main']['feels_like']
    humidity = resp['main']['humidity']
    description = resp['weather'][0]['description']
    icon_id = resp['weather'][0]['icon']
    wind_speed = resp['wind']['speed']
    forecast_data.append({
            # 'date': date,
            # 'time': time,
            'temp': temp,
            'feels_like': feels_like,
            'humidity': humidity,
            'description': description,
            'icon_id': icon_id,
            'wind_speed': wind_speed,
            'location':city
        })
    return render_template('weather.html', forecast_data=forecast_data)   


#youssef



subscriptions = {}

# Dummy weather data for three cities
alert_data = {
    "London": {"temp": 50,"humidity":70,"visibility":900,"wind_speed":0.75},
    "New York": {"temp": -25,"humidity":90,"visibility":10000,"wind_speed":90},
    "Tokyo": {"temp": 30,"humidity":55,"visibility":8000,"wind_speed":8.5},
}

def send_email(email, city, message):
     """A function to send email to a user"""
     sender_email = 'youssef.chaker@etudiant-isi.utm.tn'
     sender_password = '14325145'
     recipient_email = email

     msg = MIMEText(message)
     msg['Subject'] = f"{city} weather alert"
     msg['From'] = sender_email
     msg['To'] = recipient_email

    # Send the message via SMTP server
     smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
     smtp_server.starttls()
     smtp_server.login(sender_email, sender_password)
     smtp_server.sendmail(sender_email, recipient_email, msg.as_string())
     smtp_server.quit()
    

def check_alerts():
    """Function to check temperature alerts and send emails to subscribed users"""
    while True:
        for city, email_list in subscriptions.items():
            weather = alert_data.get(city)
            if weather:
                temp = weather.get("temp")
                message = f"Temperature alert: {city} is currently {temp} degrees Celsius"
                for email in email_list:
                    send_email(email, city, message)
        # Wait for 1 minute before checking alerts again
        time.sleep(60)

@app.route('/notif', methods=['GET', 'POST'])
def notif():
    cities = list(alert_data.keys())
    if request.method == 'POST':
        city = request.form['city']
        print(f"****************** {city}")
        email = request.form['email']
        if city in subscriptions:
            subscriptions[city].append(email)
        else:
            subscriptions[city] = [email]
        message = f"Thank you for subscribing to temperature alerts for {city}."
        send_email(email, city, message)
        message = f"You have subscribed to temperature alerts for {city}."
        return render_template('notif.html', message=message, cities=cities)
    else:
        # Display subscription form
        return render_template('notif.html', cities=cities)



@app.route('/alert', methods=['GET', 'POST'])
def alert():
    cities = list(alert_data.keys())
    
    if request.method == 'POST':
        city = request.form['city']
        email = request.form['email']
        temperature = 0
        humidity= 0
        visibility= 0
        wind_speed= 0
        country=""
        #alert specification message
        str1= ""
        str2= ""
        str3= ""
        str4= ""
        alertMsg= ""
        problem = 0
        alertcounter= 0
        
        if city in subscriptions:
            weather = alert_data.get(city)
            print(f"******************* {weather}")
            country=city
            subscriptions[city].append(email)
            temperature = weather['temp']
            humidity= weather['humidity']
            visibility= weather['visibility']
            wind_speed= weather['wind_speed']
            #temperature
            if temperature > 40:
                str1= f"- Extreme heat: {temperature}°C\n\t"
                problem= problem +1
            elif temperature<-20:
                str1= f"- Extreme cold: {temperature}°C\n\t"
                problem= problem +1

            #humidity
            if humidity > 60:
                str2= f"- High humidity: {humidity}%\n\t"
                problem= problem +1
            
            #visibility
            if visibility<1000:
                str3= f"- Extreme low visibility:{visibility} meters\n\t"
                problem= problem +1

            #wind_speed
            if wind_speed > 80:
                str4=f"- Extreme wind speed {wind_speed}km/h\n\t"
                problem= problem +1

            if problem>0:
                alertcounter= alertcounter+ 1
                str= f"\n{country}:\n\t{str1}{str2}{str3}{str4}"
                alertMsg+ str
        
            if alertcounter>0:
                alertMsg= "Alert: Please be careful from these extreme weather cases\n"+ str
            
            else:
                alertMsg= "all good"
        else:
            subscriptions[city] = [email]
        
        
        
    

        send_email(email, city, alertMsg)
        message = f"You have recived alerts for {city}."
        return render_template('alert.html', message=message, cities=cities)
    else:
        # Display subscription form
        return render_template('alert.html', cities=cities)








if __name__ =="__main__":
    app.run(host='0.0.0.0', debug=True)