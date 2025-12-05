import requests
import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# 1. Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# ==========================================
# 🔑 GET KEYS FROM ENV
# ==========================================
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Check if keys exist to prevent errors later
if not WEATHER_API_KEY or not GEMINI_API_KEY:
    raise ValueError("❌ Missing API Keys. Please check your .env file.")

# ==========================================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/weather", methods=["POST"])
def get_weather():
    city = request.json.get("city")

    if not city:
         return jsonify({"error": "City name is required"}), 400

    try:
        # 1. Fetch from OpenWeatherMap
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={WEATHER_API_KEY}"
        res = requests.get(url).json()

        if res.get("cod") != 200:
            return jsonify({"error": "City not found"}), 404

        # 2. Extract ALL Possible Data
        weather = {
            "city": res["name"],
            "country": res["sys"]["country"],
            "description": res["weather"][0]["description"].title(),
            "icon": f"http://openweathermap.org/img/wn/{res['weather'][0]['icon']}@2x.png",
            
            # Temperature
            "temp": res["main"]["temp"],
            "feels_like": res["main"]["feels_like"],
            "temp_min": res["main"]["temp_min"],
            "temp_max": res["main"]["temp_max"],
            
            # Atmosphere
            "humidity": res["main"]["humidity"],
            "pressure": res["main"]["pressure"],
            "visibility": res.get("visibility", 0) / 1000, # Convert meters to km
            
            # Wind & Clouds
            "wind_speed": res["wind"]["speed"],
            "wind_deg": res["wind"]["deg"],
            "clouds": res["clouds"]["all"],
            
            # Precipitation
            "rain": res.get("rain", {}).get("1h", 0)
        }
        
    except Exception as e:
        print(f"Weather Error: {e}")
        return jsonify({"error": "Weather Service Error"}), 500

    # 3. Gemini AI Analysis
    # Note: Using gemini-1.5-flash as 2.5 is not standard yet. Change back if you have specific access.
    ai_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    Act as a disaster management AI. Analyze this detailed weather report:
    Location: {weather['city']}, {weather['country']}
    Condition: {weather['description']}
    Temp: {weather['temp']}C (Feels like {weather['feels_like']}C)
    Wind: {weather['wind_speed']} m/s
    Pressure: {weather['pressure']} hPa
    Rain (1h): {weather['rain']} mm
    Humidity: {weather['humidity']}%
    Visibility: {weather['visibility']} km

    Identify any potential risks (Flood, Storm, Heatwave, Low Visibility).
    If safe, say "Conditions are stable."
    Keep response under 3 sentences.
    """

    ai_msg = "AI Analysis Unavailable"
    ai_success = False

    try:
        ai_res = requests.post(ai_url, json={"contents": [{"parts": [{"text": prompt}]}]}).json()
        
        if "candidates" in ai_res:
            ai_msg = ai_res["candidates"][0]["content"]["parts"][0]["text"]
            ai_success = True
        else:
            # Better error logging
            print("Gemini Error:", ai_res) 
            ai_msg = ai_res.get('error', {}).get('message', 'AI quota exceeded or key invalid.')
            
    except Exception as e:
        print(f"AI Connection Failed: {e}")
        ai_msg = "AI Service Unreachable"

    return jsonify({
        "weather": weather,
        "ai_report": ai_msg,
        "ai_success": ai_success
    })

if __name__ == "__main__":
    app.run(debug=True)

