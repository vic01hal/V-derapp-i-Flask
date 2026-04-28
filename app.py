from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/results", methods=["POST"])
def results():
    city = request.form.get("city")
    return render_template("results.html", city=city, weather=weather_data)

weather_data = {
    "temperature": 17,
    "windspeed": 5,
    "description": "Soligt",
    "humidity": 62,
    "AQI": "Bra"
}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)