from flask import Flask, render_template, request, session, redirect, url_for, Response
import requests
import os
import json
from datetime import datetime, timedelta
from collections import OrderedDict

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "weather-secret-key-2024")

# API key is read from the environment (see .env.example). If it is missing,
# the app automatically runs in OFFLINE DEMO MODE using bundled sample data.
API_KEY = os.environ.get("OPENWEATHER_API_KEY", "").strip()
BASE_URL = "http://api.openweathermap.org/data/2.5/"
#http://api.openweathermap.org/data/2.5/weather?q=London&appid=YOUR_KEY

# ---------------------------------------------------------------------------
# Offline demo support
# ---------------------------------------------------------------------------
SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "samples", "sample_weather.json")


def _load_samples():
    try:
        with open(SAMPLE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"default_city": "London", "cities": {}}


SAMPLES = _load_samples()
DEFAULT_DEMO_CITY = SAMPLES.get("default_city", "London")


def offline_mode():
    """True when no API key is configured -> serve bundled sample data."""
    return not API_KEY


def _match_sample_city(city):
    """Return (canonical_name, sample_dict) for a requested city, or default."""
    cities = SAMPLES.get("cities", {})
    if city:
        key = city.strip().lower()
        for name, payload in cities.items():
            if name.lower() == key:
                return name, payload
    # fall back to default demo city so the page is always populated
    if DEFAULT_DEMO_CITY in cities:
        return DEFAULT_DEMO_CITY, cities[DEFAULT_DEMO_CITY]
    if cities:
        name = next(iter(cities))
        return name, cities[name]
    return None, None


def deg_to_compass(num):
    val = int((num / 22.5) + 0.5)
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return directions[(val % 16)]


def aqi_description(aqi):
    return {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}.get(aqi, "Unknown")


def uv_description(uvi):
    """Plain-English UV index band, per the WHO scale."""
    if uvi is None:
        return None
    if uvi < 3:
        return "Low"
    if uvi < 6:
        return "Moderate"
    if uvi < 8:
        return "High"
    if uvi < 11:
        return "Very High"
    return "Extreme"


_SYNODIC_MONTH = 29.530588853
_KNOWN_NEW_MOON = datetime(2000, 1, 6, 18, 14)  # a reference new moon, UTC

_MOON_PHASES = [
    (0.02, "New Moon", "🌑"),
    (0.25, "Waxing Crescent", "🌒"),
    (0.27, "First Quarter", "🌓"),
    (0.48, "Waxing Gibbous", "🌔"),
    (0.52, "Full Moon", "🌕"),
    (0.73, "Waning Gibbous", "🌖"),
    (0.75, "Last Quarter", "🌗"),
    (0.98, "Waning Crescent", "🌘"),
    (1.01, "New Moon", "🌑"),
]


def moon_phase(dt_utc):
    """Current moon phase for a given UTC datetime -- computed locally with a
    standard synodic-month formula, no API call needed. Returns a name, an
    emoji, and how far through the cycle we are (0 = new, 0.5 = full)."""
    days_since = (dt_utc - _KNOWN_NEW_MOON).total_seconds() / 86400.0
    fraction = (days_since % _SYNODIC_MONTH) / _SYNODIC_MONTH
    for threshold, name, emoji in _MOON_PHASES:
        if fraction < threshold:
            return {"name": name, "emoji": emoji, "fraction": round(fraction, 3)}
    return {"name": "New Moon", "emoji": "🌑", "fraction": round(fraction, 3)}


_ICON_TO_MAIN = {
    "01": "clear", "02": "clouds", "03": "clouds", "04": "clouds",
    "09": "drizzle", "10": "rain", "11": "thunderstorm", "13": "snow", "50": "mist",
}


def _infer_weather_main(weather_item):
    """The full OpenWeather 'weather' object always has a 'main' field, but the
    bundled offline sample data trims it to save space -- fall back to the
    icon code, then to the description text, so every code path still gets a
    usable weather_main for backgrounds/outfit logic."""
    if weather_item.get("main"):
        return weather_item["main"].lower()
    code = (weather_item.get("icon") or "")[:2]
    if code in _ICON_TO_MAIN:
        return _ICON_TO_MAIN[code]
    desc = (weather_item.get("description") or "").lower()
    for key in ("thunderstorm", "drizzle", "rain", "snow", "mist", "fog", "haze", "smoke", "cloud"):
        if key in desc:
            return "clouds" if key == "cloud" else key
    return "clear"


# ---------------------------------------------------------------------------
# Outfit / "should I go out" advisor
# ---------------------------------------------------------------------------
def _dedupe(seq):
    seen = set()
    out = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def build_outfit_advice(temp_c, feels_like_c=None, weather_main="", description="",
                         humidity=None, wind_speed=None, pop=None, aqi=None, is_day=True):
    """Rule-based outfit + outing advisor. Combines temperature, sky condition,
    wind, rain probability and air quality into plain-English clothing tips
    and a single traffic-light verdict on whether it's a good day to go out."""

    weather_main = (weather_main or "").lower()
    t = feels_like_c if feels_like_c is not None else temp_c
    if t is None:
        t = 20.0
    wind_speed = wind_speed or 0
    pop = pop or 0

    # --- clothing tier from "feels like" temperature ---
    if t >= 35:
        headline = "Scorching Hot"
        clothing = ["Light, loose cotton or linen clothing", "Short sleeves & shorts",
                    "Light colours that reflect heat"]
        accessories = ["Sunglasses", "Wide-brim hat", "Sunscreen SPF 30+", "Carry water"]
        temp_severity = 2
    elif t >= 28:
        headline = "Hot & Sunny"
        clothing = ["T-shirt & shorts, or a light dress", "Breathable, light-coloured fabrics"]
        accessories = ["Sunglasses", "Sunscreen", "A cap or hat"]
        temp_severity = 1
    elif t >= 20:
        headline = "Warm & Pleasant"
        clothing = ["T-shirt or light shirt", "Jeans, chinos or a skirt"]
        accessories = ["Sunglasses (if sunny)"]
        temp_severity = 0
    elif t >= 12:
        headline = "Mild"
        clothing = ["Light sweater or long-sleeve shirt", "A light jacket for later in the day"]
        accessories = []
        temp_severity = 0
    elif t >= 5:
        headline = "Chilly"
        clothing = ["Warm jacket or coat", "Sweater underneath", "Full-length trousers"]
        accessories = ["Scarf"]
        temp_severity = 2
    elif t >= -5:
        headline = "Cold"
        clothing = ["Heavy insulated coat", "Thermal base layer", "Warm sweater"]
        accessories = ["Gloves", "Scarf", "Warm hat"]
        temp_severity = 3
    else:
        headline = "Freezing"
        clothing = ["Heavy-duty insulated coat", "Multiple thermal layers", "Insulated boots"]
        accessories = ["Insulated gloves", "Thermal scarf", "Warm hat covering ears"]
        temp_severity = 4

    tips = []
    condition_severity = 0

    if "thunderstorm" in weather_main:
        tips.append("Thunderstorms are expected — stay indoors and away from open areas or tall isolated trees.")
        condition_severity = 4
    elif "snow" in weather_main:
        clothing.append("Waterproof, insulated boots")
        accessories += ["Gloves", "Warm hat"]
        tips.append("Snowfall expected — paths may be slippery, walk carefully.")
        condition_severity = max(condition_severity, 3)
    elif "rain" in weather_main or "drizzle" in weather_main or pop >= 60:
        accessories += ["Umbrella", "Waterproof jacket"]
        clothing.append("Water-resistant shoes")
        tips.append("Rain is likely — carry an umbrella and wear water-resistant shoes.")
        condition_severity = max(condition_severity, 2)
    elif pop >= 30:
        accessories.append("A compact umbrella just in case")
        tips.append("There's a chance of rain later — keep an umbrella handy.")
        condition_severity = max(condition_severity, 1)

    if any(k in weather_main for k in ("mist", "fog", "haze", "smoke")):
        tips.append("Visibility is reduced — take extra care while driving, cycling or walking near roads.")
        condition_severity = max(condition_severity, 1)

    if wind_speed >= 15:
        accessories.append("A sturdy windbreaker")
        tips.append("Very strong winds — secure loose items, hats and umbrellas.")
        condition_severity = max(condition_severity, 3)
    elif wind_speed >= 8:
        accessories.append("Windbreaker")
        tips.append("Breezy conditions — a windproof layer will help.")
        condition_severity = max(condition_severity, 1)

    aqi_severity = 0
    if aqi:
        if aqi >= 5:
            accessories.append("N95 / pollution mask")
            tips.append("Air quality is very poor — limit outdoor exertion, especially for children and the elderly.")
            aqi_severity = 3
        elif aqi == 4:
            accessories.append("Pollution mask")
            tips.append("Air quality is poor — sensitive groups should limit prolonged outdoor activity.")
            aqi_severity = 2
        elif aqi == 3:
            tips.append("Air quality is moderate — generally fine for most people.")
            aqi_severity = 1

    if not is_day:
        tips.append("It's dark out — wear something reflective or carry a light if you're heading out.")

    severity = max(temp_severity, condition_severity, aqi_severity)
    verdicts = {
        0: ("Great for Outing!", "great"),
        1: ("Good Day to Go Out", "good"),
        2: ("Fair — Plan Accordingly", "fair"),
        3: ("Caution Advised", "caution"),
        4: ("Best to Stay Indoors", "avoid"),
    }
    verdict_text, verdict_class = verdicts[severity]

    return {
        "headline": headline,
        "clothing": _dedupe(clothing),
        "accessories": _dedupe(accessories),
        "tips": tips,
        "verdict": verdict_text,
        "verdict_class": verdict_class,
    }


# ---------------------------------------------------------------------------
# Current weather
# ---------------------------------------------------------------------------
def _next_countdown(target, now):
    """Time remaining until `target` (a daily event like sunrise/sunset).
    If `target` already happened today, roll it forward a day at a time
    until it's in the future, so the countdown is always a sane positive
    duration -- this also keeps the bundled offline demo data (which has a
    fixed, non-rolling sunrise/sunset timestamp) from ever showing a
    confusing negative countdown."""
    delta = target - now
    guard = 0
    while delta.total_seconds() < 0 and guard < 3650:
        target += timedelta(days=1)
        delta = target - now
        guard += 1
    return str(delta).split(".")[0]


def _normalize_alerts(alerts, timezone_offset):
    """Turn raw OpenWeather alert objects (unix start/end, long descriptions)
    into something simple to render: readable local times and a trimmed
    description."""
    out = []
    for a in (alerts or []):
        try:
            start = datetime.utcfromtimestamp(a["start"] + timezone_offset).strftime("%d %b, %H:%M")
        except Exception:
            start = None
        try:
            end = datetime.utcfromtimestamp(a["end"] + timezone_offset).strftime("%d %b, %H:%M")
        except Exception:
            end = None
        desc = (a.get("description") or "").strip()
        if len(desc) > 400:
            desc = desc[:400].rsplit(" ", 1)[0] + "…"
        out.append({
            "event": a.get("event", "Weather Alert"),
            "sender": a.get("sender_name"),
            "start": start,
            "end": end,
            "description": desc,
        })
    return out


def _build_current_from_response(response, air_res, dew_point, uvi=None, alerts=None):
    """Shared parser: turns raw OpenWeather-shaped dicts into the template dict.
    Works identically for live API responses and bundled sample responses."""
    timezone_offset = response["timezone"]
    local_time = datetime.utcnow() + timedelta(seconds=timezone_offset)
    sunrise = datetime.utcfromtimestamp(response["sys"]["sunrise"] + timezone_offset)
    sunset = datetime.utcfromtimestamp(response["sys"]["sunset"] + timezone_offset)

    lat = response["coord"]["lat"]
    lon = response["coord"]["lon"]
    wind_deg = response["wind"].get("deg", 0)
    weather_main = response["weather"][0]["main"].lower()
    visibility_km = round(response.get("visibility", 0) / 1000, 2)

    data = {
        "city": response["name"],
        "country": response["sys"]["country"],
        "temperature": response["main"]["temp"],
        "feels_like": response["main"]["feels_like"],
        "temp_min": response["main"]["temp_min"],
        "temp_max": response["main"]["temp_max"],
        "humidity": response["main"]["humidity"],
        "pressure": response["main"]["pressure"],
        "visibility": visibility_km,  # km
        "visibility_miles": round(visibility_km * 0.621371, 2),
        "wind_speed": response["wind"]["speed"],
        "wind_deg": wind_deg,
        "wind_dir": deg_to_compass(wind_deg),
        "description": response["weather"][0]["description"].title(),
        "icon": response["weather"][0]["icon"],
        "local_time": local_time.strftime("%Y-%m-%d %H:%M:%S"),
        "sunrise": sunrise.strftime("%H:%M"),
        "sunset": sunset.strftime("%H:%M"),
        "sunrise_countdown": _next_countdown(sunrise, local_time),
        "sunset_countdown": _next_countdown(sunset, local_time),
        "lat": lat,
        "lon": lon,
        "weather_main": weather_main,
        "timezone_offset": timezone_offset,
        "is_day": sunrise <= local_time <= sunset,
        "uvi": uvi,
        "uvi_desc": uv_description(uvi),
        "alerts": _normalize_alerts(alerts, timezone_offset),
        "moon": moon_phase(datetime.utcnow()),
    }

    if air_res and "list" in air_res and len(air_res["list"]) > 0:
        air = air_res["list"][0]
        data["aqi"] = air["main"]["aqi"]
        data["aqi_desc"] = aqi_description(air["main"]["aqi"])
        data["pm2_5"] = air["components"]["pm2_5"]
        data["pm10"] = air["components"]["pm10"]
        data["o3"] = air["components"]["o3"]
    else:
        data["aqi"] = data["aqi_desc"] = data["pm2_5"] = data["pm10"] = data["o3"] = None

    data["dew_point"] = dew_point

    data["outfit"] = build_outfit_advice(
        temp_c=data["temperature"],
        feels_like_c=data["feels_like"],
        weather_main=data["weather_main"],
        description=data["description"],
        humidity=data["humidity"],
        wind_speed=data["wind_speed"],
        pop=None,
        aqi=data["aqi"],
        is_day=data["is_day"],
    )
    return data


def _current_from_sample(city=None):
    name, payload = _match_sample_city(city)
    if not payload:
        return None
    response = payload["weather"]
    air_res = payload.get("air")
    onecall = payload.get("onecall", {})
    dew = onecall.get("current", {}).get("dew_point")
    uvi = onecall.get("current", {}).get("uvi")
    alerts = onecall.get("alerts")
    return _build_current_from_response(response, air_res, dew, uvi=uvi, alerts=alerts)


def get_current_weather(city=None, lat=None, lon=None):
    # Offline demo mode: no key configured -> always serve sample data.
    if offline_mode():
        return _current_from_sample(city)

    if city:
        url = f"{BASE_URL}weather?q={city}&appid={API_KEY}&units=metric"
    elif lat and lon:
        url = f"{BASE_URL}weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    else:
        return None

    try:
        response = requests.get(url, timeout=8).json()
        if response.get("cod") != 200:
            return None

        lat = response["coord"]["lat"]
        lon = response["coord"]["lon"]

        air_url = f"{BASE_URL}air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
        air_res = requests.get(air_url, timeout=8).json()

        # "onecall" also carries UV index and any active severe-weather alerts.
        # Not every free-tier key has this endpoint enabled, so it's wrapped in
        # its own try/except and everything it provides is optional -- the app
        # works identically with or without it.
        onecall_url = f"{BASE_URL}onecall?lat={lat}&lon={lon}&exclude=minutely,hourly,daily&appid={API_KEY}&units=metric"
        dew, uvi, alerts = None, None, []
        try:
            onecall_res = requests.get(onecall_url, timeout=8).json()
            dew = onecall_res.get("current", {}).get("dew_point")
            uvi = onecall_res.get("current", {}).get("uvi")
            alerts = onecall_res.get("alerts", [])
        except Exception:
            pass

        return _build_current_from_response(response, air_res, dew, uvi=uvi, alerts=alerts)
    except Exception:
        # Network/API failure -> graceful fallback to bundled sample data.
        return _current_from_sample(city)


# ---------------------------------------------------------------------------
# Forecast: raw 3-hour list, plus hourly & daily/"weekly" views derived from it
# ---------------------------------------------------------------------------
def _parse_forecast(response, tz_offset=0):
    forecast_data = []
    for item in response["list"]:
        dt_utc = datetime.utcfromtimestamp(item["dt"])
        dt_local = dt_utc + timedelta(seconds=tz_offset)
        wind = item.get("wind", {}) or {}
        pop_raw = item.get("pop")
        forecast_data.append({
            "dt": item["dt"],
            "dt_local": dt_local,
            "time": dt_local.strftime('%d %b %H:%M'),
            "hour_label": dt_local.strftime('%I %p').lstrip('0'),
            "date_label": dt_local.strftime('%a %d %b'),
            "temp": item["main"]["temp"],
            "humidity": item["main"]["humidity"],
            "description": item["weather"][0]["description"].title(),
            "weather_main": _infer_weather_main(item["weather"][0]),
            "icon": item["weather"][0]["icon"],
            "wind_speed": wind.get("speed"),
            "pop": round(pop_raw * 100) if pop_raw is not None else None,
        })
    return forecast_data


def _forecast_from_sample(city=None, tz_offset=0):
    name, payload = _match_sample_city(city)
    if not payload or "forecast" not in payload:
        return None
    return _parse_forecast(payload["forecast"], tz_offset)


def get_forecast(city=None, lat=None, lon=None, tz_offset=0):
    if offline_mode():
        return _forecast_from_sample(city, tz_offset)

    if city:
        url = f"{BASE_URL}forecast?q={city}&appid={API_KEY}&units=metric"
    elif lat and lon:
        url = f"{BASE_URL}forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    else:
        return None

    try:
        response = requests.get(url, timeout=8).json()
        if str(response.get("cod")) != "200":
            return None
        return _parse_forecast(response, tz_offset)
    except Exception:
        return _forecast_from_sample(city, tz_offset)


def build_hourly(forecast_items, limit=8):
    """Next N x 3-hour slots, for the 'Hourly Forecast' strip."""
    if not forecast_items:
        return []
    return forecast_items[:limit]


def build_daily(forecast_items, max_days=6):
    """Group the 3-hour slots into per-day cards (high/low, dominant sky,
    and a day-specific outfit tip) -- effectively a 5-6 day outlook, which is
    the maximum the free 3-hour forecast endpoint (and the bundled demo data)
    can support."""
    if not forecast_items:
        return []

    days = OrderedDict()
    for item in forecast_items:
        key = item["dt_local"].date()
        days.setdefault(key, []).append(item)

    result = []
    for i, (day, items) in enumerate(days.items()):
        if i >= max_days:
            break
        temps = [it["temp"] for it in items if it.get("temp") is not None]
        humidities = [it["humidity"] for it in items if it.get("humidity") is not None]
        winds = [it["wind_speed"] for it in items if it.get("wind_speed") is not None]
        pops = [it["pop"] for it in items if it.get("pop") is not None]

        # Prefer a mid-afternoon slot as the "representative" icon/description
        midday_items = [it for it in items if 11 <= it["dt_local"].hour <= 16]
        rep = midday_items[len(midday_items) // 2] if midday_items else items[len(items) // 2]

        if i == 0:
            label = "Today"
        elif i == 1:
            label = "Tomorrow"
        else:
            label = day.strftime("%A")

        avg_wind = sum(winds) / len(winds) if winds else None
        max_pop = max(pops) if pops else None
        avg_humidity = round(sum(humidities) / len(humidities)) if humidities else None

        outfit = build_outfit_advice(
            temp_c=rep["temp"],
            feels_like_c=None,
            weather_main=rep["weather_main"],
            description=rep["description"],
            humidity=avg_humidity,
            wind_speed=avg_wind,
            pop=max_pop,
            aqi=None,
            is_day=True,
        )

        result.append({
            "label": label,
            "date": day.strftime("%d %b"),
            "weekday": day.strftime("%A"),
            "temp_min": round(min(temps), 1) if temps else None,
            "temp_max": round(max(temps), 1) if temps else None,
            "icon": rep["icon"],
            "description": rep["description"],
            "weather_main": rep["weather_main"],
            "humidity": avg_humidity,
            "pop": max_pop,
            "wind_speed": round(avg_wind, 1) if avg_wind is not None else None,
            "outfit": outfit,
        })
    return result


@app.context_processor
def inject_globals():
    return {"current_year": datetime.utcnow().year}


# ---------------------------------------------------------------------------
# This is a multi-page site (Home / Hourly / Daily / What to Wear / Compare).
# Whichever city (or GPS location) was last searched on the Home page is
# remembered in the session, so every other page automatically shows that
# same place without needing its own search box.
# ---------------------------------------------------------------------------
def _get_context_weather():
    city = session.get("last_city")
    lat = session.get("last_lat")
    lon = session.get("last_lon")

    weather = None
    if city or (lat and lon):
        weather = get_current_weather(city=city, lat=lat, lon=lon)

    if not weather:
        # Nothing searched yet (or it stopped resolving) -> fall back to the
        # default demo city so every page is always populated.
        weather = get_current_weather(city=DEFAULT_DEMO_CITY)
        city, lat, lon = DEFAULT_DEMO_CITY, None, None

    forecast = None
    if weather:
        forecast = get_forecast(city=city, lat=lat, lon=lon, tz_offset=weather.get("timezone_offset", 0))

    return weather, forecast


@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    # True only the very first time a visitor lands here (no search yet) --
    # used to offer one gentle auto "use my location" prompt instead of
    # always defaulting to the demo city.
    first_visit = "last_city" not in session and "last_lat" not in session

    if request.method == "POST":
        city = (request.form.get("city") or "").strip()
        lat = request.form.get("lat")
        lon = request.form.get("lon")

        weather = get_current_weather(city=city or None, lat=lat, lon=lon)
        if weather:
            session["last_city"] = city or None
            session["last_lat"] = lat
            session["last_lon"] = lon
            forecast = get_forecast(city=city or None, lat=lat, lon=lon, tz_offset=weather.get("timezone_offset", 0))
        else:
            error = "City not found or invalid coordinates!"
            weather, forecast = _get_context_weather()
    else:
        weather, forecast = _get_context_weather()

    hourly = build_hourly(forecast, limit=8) if forecast else None
    daily = build_daily(forecast, max_days=6) if forecast else None

    return render_template("dashboard.html", weather=weather, forecast=forecast,
                            hourly=hourly, daily=daily, first_visit=first_visit,
                            error=error, offline=offline_mode(), active_page="home",
                            map_layers_enabled=not offline_mode())


@app.route("/hourly")
def hourly_page():
    weather, forecast = _get_context_weather()
    hourly = build_hourly(forecast, limit=16) if forecast else None  # next ~48h
    return render_template("hourly.html", weather=weather, hourly=hourly,
                            offline=offline_mode(), active_page="hourly")


@app.route("/daily")
def daily_page():
    weather, forecast = _get_context_weather()
    daily = build_daily(forecast, max_days=6) if forecast else None
    return render_template("daily.html", weather=weather, daily=daily,
                            offline=offline_mode(), active_page="daily")


@app.route("/outfit")
def outfit_page():
    weather, forecast = _get_context_weather()
    daily = build_daily(forecast, max_days=6) if forecast else None
    return render_template("outfit.html", weather=weather, daily=daily,
                            offline=offline_mode(), active_page="outfit")


@app.route("/save_city", methods=["POST"])
def save_city():
    city = request.form.get("city", "").strip()
    if city:
        saved = session.get("saved_cities", [])
        if city not in saved:
            saved.append(city)
        session["saved_cities"] = saved
    return redirect(url_for("index"))


@app.route("/remove_city", methods=["POST"])
def remove_city():
    city = request.form.get("city", "").strip()
    saved = session.get("saved_cities", [])
    if city in saved:
        saved.remove(city)
    session["saved_cities"] = saved
    return redirect(url_for("index"))


_ALLOWED_TILE_LAYERS = {"clouds_new", "precipitation_new", "temp_new", "wind_new", "pressure_new"}


@app.route("/tiles/<layer>/<int:z>/<int:x>/<int:y>.png")
def weather_tile(layer, z, x, y):
    """Server-side proxy for OpenWeatherMap's map-tile layers (clouds, rain,
    temperature, wind, pressure overlays on the Leaflet map). The tile
    request needs the API key, and this app is meant to be deployed
    publicly -- proxying it here keeps the key out of the page's HTML/JS and
    off the network tab, instead of embedding it directly in a client-side
    tile URL."""
    if offline_mode() or layer not in _ALLOWED_TILE_LAYERS:
        return "", 204
    url = f"https://tile.openweathermap.org/map/{layer}/{z}/{x}/{y}.png?appid={API_KEY}"
    try:
        upstream = requests.get(url, timeout=8)
        if upstream.status_code != 200:
            return "", 204
        return Response(upstream.content, mimetype="image/png",
                         headers={"Cache-Control": "public, max-age=600"})
    except Exception:
        return "", 204


@app.route("/compare")
def compare():
    saved = session.get("saved_cities", [])
    # In offline demo mode with no saved cities yet, show the demo cities so the
    # comparison page is populated instead of empty.
    if not saved and offline_mode():
        saved = list(SAMPLES.get("cities", {}).keys())
    cities_data = []
    for city in saved:
        try:
            w = get_current_weather(city=city)
            if w:
                # get_current_weather() already attaches an 'outfit' advisory
                cities_data.append(w)
        except Exception:
            pass
    return render_template("compare.html", cities=cities_data, offline=offline_mode(), active_page="compare")


if __name__ == "__main__":
    # Locally this still just runs `python app.py` and opens on
    # http://127.0.0.1:5000 like before. When deployed (e.g. on Render), the
    # host sets PORT and a production WSGI server (gunicorn, see Procfile)
    # runs this module instead of hitting this block at all -- FLASK_DEBUG
    # defaults to on for local development and should be left unset/"0" in
    # any public deployment.
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug)
