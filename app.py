from flask import Flask, render_template, request
import openmeteo_requests
import requests_cache
from retry_requests import retry
import requests

app = Flask(__name__)

cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
retry_session = retry(cache_session, retries=2, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

weather_url = "https://api.open-meteo.com/v1/forecast"
geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"

current_variables = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "is_day",
    "precipitation",
    "weather_code",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m"
]


def get_coordinates(city):
    params = {
        "name": city,
        "count": 1,
        "language": "sv",
        "format": "json"
    }

    response = retry_session.get(geocoding_url, params=params, timeout=0.2)
    response.raise_for_status()
    data = response.json()

    if "results" not in data or not data["results"]:
        return None

    place = data["results"][0]

    return {
        "name": place["name"],
        "country": place.get("country", ""),
        "latitude": place["latitude"],
        "longitude": place["longitude"]
    }

#Väderkod till emoji dict är gjord av ChatGPT, för jag orkade inte
def weather_emoji(weather_code, is_day):
    weather_code = int(weather_code)
    is_day = int(is_day)

    if weather_code == 0:
        if is_day == 1:
            return "☀️"
        else:
            return "🌙"

    weather_emojis = {
        1: "🌤️",
        2: "⛅",
        3: "☁️",
        45: "🌫️",
        48: "🌫️",
        51: "🌦️",
        53: "🌦️",
        55: "🌧️",
        56: "🌧️",
        57: "🌧️",
        61: "🌦️",
        63: "🌧️",
        65: "⛈️",
        66: "🌧️",
        67: "⛈️",
        71: "🌨️",
        73: "❄️",
        75: "❄️",
        77: "❄️",
        80: "🌦️",
        81: "🌧️",
        82: "⛈️",
        85: "🌨️",
        86: "❄️",
        95: "⛈️",
        96: "⛈️",
        99: "⛈️"
    }

    return weather_emojis.get(weather_code, "🌍")

def get_weather(latitude, longitude):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": current_variables,
        "daily": ["precipitation_sum"],
        "timezone": "auto"
    }

    responses = openmeteo.weather_api(weather_url, params=params)
    response = responses[0]

    current = response.Current()
    daily = response.Daily()

    weather_data = {
        "temperature": round(current.Variables(0).Value(), 1),
        "humidity": int(round(current.Variables(1).Value(), 0)),
        "apparent_temperature": round(current.Variables(2).Value(), 1),
        "is_day": int(current.Variables(3).Value()),
        "precipitation": round(current.Variables(4).Value(), 1),
        "weather_code": int(current.Variables(5).Value()),
        "weather_description": get_weather_description(
            current.Variables(5).Value(),
            current.Variables(3).Value()
        ),
        "weather_emoji": weather_emoji(
            current.Variables(5).Value(),
            current.Variables(3).Value()
        ),
        "cloud_cover": int(round(current.Variables(6).Value(), 0)),
        "wind_speed": round(current.Variables(7).Value() / 3.6, 1),
        "wind_direction": int(round(current.Variables(8).Value(), 0)),
        "precipitation_today": round(daily.Variables(0).ValuesAsNumpy()[0], 1)
    }

    return weather_data


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/results", methods=["POST"])
def results():
    city = request.form.get("city", "").strip()

    if not city:
        return render_template("results.html", error="Skriv en stad.")

    try:
        place = get_coordinates(city)

        if place is None:
            return render_template("results.html", error="Stad kunde inte hittas.")

        weather_data = get_weather(place["latitude"], place["longitude"])

        return render_template(
            "results.html",
            city=place["name"],
            country=place["country"],
            weather=weather_data
        )

    except Exception as e:
        print(f"Fel: {e}")
        return render_template(
            "results.html",
            error="Det gick inte att hämta väderdata just nu."
    )
    
def get_weather_description(weather_code, is_day):
    weather_code = int(weather_code)

    #Denna dict är också ChatGPT, för jag är lat
    weather_codes = {
        0: "Klart",
        1: "Mestadels klart",
        2: "Delvis molnigt",
        3: "Mulet",
        45: "Dimma",
        48: "Rimfrost-dimma",
        51: "Lätt duggregn",
        53: "Måttligt duggregn",
        55: "Tätt duggregn",
        56: "Lätt underkylt duggregn",
        57: "Tätt underkylt duggregn",
        61: "Lätt regn",
        63: "Måttligt regn",
        65: "Kraftigt regn",
        66: "Lätt underkylt regn",
        67: "Kraftigt underkylt regn",
        71: "Lätt snöfall",
        73: "Måttligt snöfall",
        75: "Kraftigt snöfall",
        77: "Snökorn",
        80: "Lätta regnskurar",
        81: "Måttliga regnskurar",
        82: "Kraftiga regnskurar",
        85: "Lätta snöbyar",
        86: "Kraftiga snöbyar",
        95: "Åskväder",
        96: "Åskväder med lätt hagel",
        99: "Åskväder med kraftigt hagel"
    }

    if weather_code == 0 and int(is_day) == 0:
        return "Klar natt"

    return weather_codes.get(weather_code, "Okänt väder")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)