# Weather Dashboard

A Flask web app that fetches live weather data for any city in the world, displays detailed conditions including air quality, an hourly and multi-day outlook, and a "what to wear" outfit/outing advisor, lets you save favourite cities to a session list, and compares multiple cities side by side — all powered by the free OpenWeatherMap API.

> **Quick start:** Get a free API key from openweathermap.org, add it to a `.env` file, install dependencies, and run `python app.py` to open the dashboard at http://127.0.0.1:5000

---

## ✨ What's new in this version

- **🧥 "What to Wear" advisor** — a rule-based recommendation engine that looks at temperature, feels-like, sky condition, rain probability, wind and air quality, then suggests clothing, accessories (umbrella, sunscreen, mask, etc.), plain-English tips, and a colour-coded verdict from "Great for Outing!" down to "Best to Stay Indoors". Shown for the current conditions, for every day in the outlook, and on the Compare page.
- **⏰ Hourly forecast strip** — the next 24 hours in 3-hour steps, with temperature and rain chance.
- **📅 Daily / multi-day outlook** — the 3-hour forecast data grouped into per-day cards with high/low, dominant sky condition and rain chance (up to 6 days — the maximum the free forecast endpoint provides).
- **🎨 Animated, weather-aware backgrounds** — a lightweight canvas-free CSS/JS "scene" (sun, moon & stars, drifting clouds, falling rain, snowfall, fog, lightning flashes) that reacts to the current condition and day/night, with no extra images or API calls needed — it works in offline demo mode too.
- **📍 Use My Location** — one click to fetch weather (and the full hourly/daily/outfit breakdown) for your current GPS position via the browser's geolocation.
- **🌡️ Smarter unit toggle** — °C/°F now applies everywhere (hero card, hourly strip, daily cards, details) and remembers your choice between visits.
- **🧭 Multi-page site** — a shared nav bar links Home / Hourly / Daily-Weekly / What to Wear / Compare, with a mobile hamburger menu on small screens. Whichever city (or GPS location) you last searched is remembered in your session and carries across every page automatically.
- **⚠️ Severe weather alerts** — active advisories (storms, heavy rain, heat, etc.) show as a banner across every page, when your API plan and location have one.
- **☀️ UV index** — a colour-coded badge (Low → Extreme) on the current-conditions card.
- **🌙 Real moon phase** — computed locally (no API call), shown on the current-conditions card and shaping the animated night-sky moon to match tonight's actual phase.
- **🧭 Wind compass** — an animated needle showing wind direction at a glance, next to the existing text reading.
- **🗺️ Live map overlays** — toggle clouds, precipitation, temperature and wind layers on the city map (needs a live API key). The map tiles are proxied through the Flask app itself (`/tiles/...`) so your API key is never exposed in the page or network requests — important now that this app can be deployed publicly.
- **📸 Share as image** — a "Share as Image" button on the current-conditions card renders it to a downloadable PNG (via html2canvas) so you can send someone a quick weather snapshot.
- **📍 Auto-location on first visit** — the very first time someone opens the site, it offers to use their location automatically instead of only showing the demo city (asks once, never nags again).
- **📱 Installable as a phone app (PWA)** — a web app manifest and service worker mean you can "Add to Home Screen" on a phone and it opens full-screen like a native app, with its own icon.
- **🚀 Deployment-ready** — a `Procfile`, `render.yaml`, and environment-driven host/port/debug settings mean this can go from `localhost` to a real public URL (see **Deploying to the web**, below).
- Bug fixes: the footer copyright year and the visibility-in-miles figure now actually render (both were silently broken before).

---

## Quick Start (one command, works offline)

This project ships with an **offline demo mode**, so you can run it immediately with **no API key and no internet**.

**Windows:**

```bat
setup.bat
```

That single command creates a virtual environment, installs dependencies, copies `.env.example` to `.env` if needed, and starts the app at **http://127.0.0.1:5000**.

> Requires **Python 3.10 or 3.11** on your PATH.

**macOS / Linux (manual):**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

### What you should see on first launch

With **no API key configured**, the app starts in **offline demo mode** and the landing page is already populated — you do not get an empty screen or an error:

- A populated dashboard for the default demo city (**London**): temperature, conditions, humidity, wind, pressure, air quality, sunrise/sunset.
- A **5-Day / 3-Hour Forecast** strip with the temperature/humidity chart.
- The **Compare** page (`/compare`) pre-filled with the bundled demo cities (London, Tokyo, New York).
- Searching for **Tokyo** or **New York** shows their bundled sample data; any other city gracefully falls back to the demo city.

The sample data lives in `samples/sample_weather.json` and matches the exact OpenWeatherMap response shape, so templates render identically to live mode.

### Switching to live data

To fetch real, live weather for any city:

1. Get a free API key at <https://openweathermap.org/api>.
2. Open the `.env` file and set:

   ```
   OPENWEATHER_API_KEY=your_key_here
   ```

3. Restart the app (`setup.bat` or `python app.py`).

When a key is present the app uses the live OpenWeatherMap API; if a live request fails (e.g. no network), it automatically falls back to the bundled sample data so the page still renders.

---

## Table of Contents

- [What it can do](#what-it-can-do)
- [How it works (in plain words)](#how-it-works-in-plain-words)
- [What's inside the project](#whats-inside-the-project)
- [Before you start (prerequisites)](#before-you-start-prerequisites)
- [Step 1 — Clone the project](#step-1--clone-the-project)
- [Step 2 — Create and activate a virtual environment](#step-2--create-and-activate-a-virtual-environment)
- [Step 3 — Get a free OpenWeatherMap API key](#step-3--get-a-free-openweathermap-api-key)
- [Step 4 — Create your .env file](#step-4--create-your-env-file)
- [Step 5 — Install dependencies](#step-5--install-dependencies)
- [Step 6 — Start the server](#step-6--start-the-server)
- [Using the app](#using-the-app)
- [Troubleshooting](#troubleshooting)
- [Tech stack](#tech-stack)

---

## What it can do

- Search for current weather conditions by city name or by GPS coordinates
- Display temperature, feels-like temperature, daily high and low, humidity, pressure, and visibility
- Show wind speed and wind direction converted to a compass bearing (N, NNE, NE, etc.)
- Display local time for the searched city, adjusted to that city's timezone
- Show sunrise and sunset times with countdown timers
- Fetch Air Quality Index (AQI) with a plain-English label (Good, Fair, Moderate, Poor, Very Poor) and pollutant levels for PM2.5, PM10, and ozone
- Show a 5-day / 3-hour weather forecast with temperature and description for each time slot
- Save cities to a session-based favourites list with a single button click
- Remove cities from the saved list
- Compare all saved cities on one page — temperatures, humidity, and conditions shown in a table side by side

---

## How it works (in plain words)

```
User types a city name and submits the form
              |
              v
Flask route (app.py / index)
              |
              +-- get_current_weather(city)
              |         |
              |         +--> OpenWeatherMap /weather endpoint  --> temperature, wind, sunrise/sunset
              |         +--> OpenWeatherMap /air_pollution     --> AQI and pollutant data
              |         +--> OpenWeatherMap /onecall           --> dew point
              |
              +-- get_forecast(city)
                        |
                        +--> OpenWeatherMap /forecast          --> 40 three-hour forecast slots
              |
              v
Flask renders dashboard.html with all data injected
              |
              v
User sees full weather dashboard in the browser
```

The app is a small multi-page site (not one long scrolling page) — a shared nav bar links Home, Hourly, Daily/Weekly, What to Wear and Compare. Whichever city (or GPS location) you last searched on Home is remembered in your session, so the other pages automatically show that same place.

| Route | What it does |
|---|---|
| `GET/POST /` | Home — search form, current conditions, air quality, chart and map |
| `GET /hourly` | Next ~48 hours in 3-hour steps for the last-searched city |
| `GET /daily` | Multi-day outlook (up to 6 days) grouped from the forecast data |
| `GET /outfit` | The "What to Wear" advisor — today's advice plus a daily outlook |
| `POST /save_city` | Adds a city to the session saved list |
| `POST /remove_city` | Removes a city from the session saved list |
| `GET /compare` | Fetches live data for all saved cities and shows them side by side |
| `GET /tiles/<layer>/<z>/<x>/<y>.png` | Server-side proxy for the live map overlay tiles (keeps the API key off the client) |

---

## What's inside the project

```
Weather-Dashboard/
├── app.py                  # Entire Flask application: routes, API calls, outfit-advice engine
├── requirements.txt        # Python package dependencies
├── Procfile                 # Tells a host (e.g. Render) how to run this in production
├── render.yaml               # Optional one-click deploy config for Render.com
├── static/
│   ├── css/
│   │   └── style.css       # Theme, nav, cards, and the animated weather-scene backgrounds
│   ├── js/
│   │   └── main.js         # Front-end JavaScript (geolocation, unit toggle, weather scene, PWA)
│   ├── icons/               # App icons used by the installable web app (PWA)
│   ├── manifest.json         # Web app manifest -- lets phones "install" this as an app
│   └── sw.js                 # Service worker -- caches the static shell for the PWA
└── templates/
    ├── base.html            # Shared page shell: nav bar, weather-scene layer, alert banner, footer
    ├── dashboard.html       # Home: search, current conditions, AQI, chart, map
    ├── hourly.html          # Hourly Forecast page
    ├── daily.html           # Daily / Weekly Outlook page
    ├── outfit.html          # What to Wear page
    ├── compare.html         # Side-by-side city comparison
    └── _context_banner.html # "You're viewing <city>" strip shown on the non-Home pages
```

---

## Before you start (prerequisites)

1. **Python 3.8 or newer** — download from [python.org](https://python.org)
2. **A free OpenWeatherMap account** — sign up at [openweathermap.org](https://openweathermap.org/api); the free tier is all you need
3. **Git** — to clone the repository

---

## Step 1 — Clone the project

**Windows (PowerShell) and macOS/Linux:**
```bash
git clone <repository-url>
cd Weather-Dashboard
```

---

## Step 2 — Create and activate a virtual environment

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Step 3 — Get a free OpenWeatherMap API key

1. Go to [openweathermap.org](https://openweathermap.org) and click **Sign Up**
2. After signing in, go to your account menu and select **My API Keys**
3. Copy the default key (or generate a new one)
4. Note: new keys can take up to 10 minutes to activate

---

## Step 4 — Create your .env file

Create a file called `.env` in the project root (the same folder as `app.py`) with the following content:

```
OPENWEATHER_API_KEY=your_key_here
```

Replace `your_key_here` with the key you copied in the previous step. This file is listed in `.gitignore` so it will never be accidentally committed to version control.

> **Note:** The current `app.py` has an API key hardcoded for convenience. Replacing it with an environment variable via `.env` and `python-dotenv` is the recommended approach for any shared or deployed environment.

---

## Step 5 — Install dependencies

**Windows:**
```powershell
pip install -r requirements.txt
```

**macOS/Linux:**
```bash
pip3 install -r requirements.txt
```

---

## Step 6 — Start the server

**Windows:**
```powershell
python app.py
```

**macOS/Linux:**
```bash
python3 app.py
```

Or with the Flask CLI:
```bash
flask run
```

Open your browser and go to **http://127.0.0.1:5000**

---

## Using the app

**Searching for a city**
Type any city name into the search box on the main page and click the search button (or press Enter). The dashboard will load current conditions below the search bar.

**Reading the weather cards**
The dashboard shows several cards:
- **Current conditions** — temperature, feels-like, today's high/low, description, and weather icon
- **Wind** — speed in m/s and direction as a compass bearing
- **Sun** — sunrise and sunset times in local city time, with time remaining until each
- **Air Quality** — AQI number with a colour-coded label, plus PM2.5, PM10, and ozone readings
- **Forecast** — a scrollable row of 3-hour forecast cards covering the next 5 days

**Saving a city**
After searching for a city, click the "Save City" button that appears below the current conditions. The city is added to your Saved Cities list, which appears at the bottom of the dashboard.

**Removing a saved city**
In the Saved Cities list, click the "Remove" button next to any city to take it off the list.

**Comparing saved cities**
Click the "Compare Cities" link in the navbar (or the button at the bottom of the page). This opens a table with one column per saved city, showing temperature, humidity, wind speed, and conditions for each, fetched live at the moment you open the page.

**Using your location**
If your browser asks for location permission, you can allow it to automatically search for weather at your current GPS coordinates.

---

## Troubleshooting

**`City not found or invalid coordinates!` error**
The city name was not recognised by the API. Check the spelling — try including the country code for ambiguous names (for example, `London, GB` instead of just `London`).

**Weather loads but air quality shows blank**
The Air Pollution API endpoint requires coordinates, which are derived from the weather response. If the weather loaded successfully but AQI is blank, OpenWeatherMap may not have air quality data for that location.

**`requests.exceptions.ConnectionError`**
Your machine cannot reach the OpenWeatherMap API. Check your internet connection. If you are behind a corporate proxy, you may need to configure proxy settings in the `requests` calls in `app.py`.

**All values show as `None` or the page is empty**
The API key in `app.py` may be invalid or not yet activated. New OpenWeatherMap keys take up to 10 minutes to activate after registration. Double-check the key and wait a few minutes before retrying.

**`ModuleNotFoundError: No module named 'flask'`**
The virtual environment is not activated, or dependencies were not installed. Make sure you ran `pip install -r requirements.txt` inside the activated virtual environment.

**The Compare page shows no cities**
You have not saved any cities yet. Search for at least one city on the main dashboard and click "Save City" before using the Compare page.

---

## Pushing this to GitHub

This folder is already a git repository. Before pushing, check whose remote it currently points to — if it was originally cloned from someone else's repository, push to your **own** repo instead of theirs:

```bash
git remote -v
```

If `origin` isn't a repository you own, create a new empty repository on GitHub (github.com → "New repository" — don't initialize it with a README), then point this project at it and push:

```bash
git remote set-url origin https://github.com/<your-username>/<your-repo-name>.git
git add .
git commit -m "Add live forecast, outfit advisor, alerts, UV, moon phase, PWA support"
git push -u origin main
```

(If your default branch is called `master` instead of `main`, use that name instead.) Git will ask you to sign in the first time — either through a browser popup or a personal access token, depending on how your GitHub credential helper is set up.

Because `.env` is listed in `.gitignore`, your API key will **not** be pushed to GitHub — only `.env.example` (the blank template) goes up. That's exactly what you want for a public repo.

---

## Deploying to the web (a real URL, not just localhost)

This project is ready to deploy as-is — it already has a `Procfile`, a `render.yaml`, and reads `PORT`/`FLASK_DEBUG` from the environment so it behaves correctly both locally and hosted. **Render.com** is a solid free option for a small Flask app like this (no credit card required for the free tier):

1. Push the project to GitHub first (see above).
2. Go to render.com and sign up (free) — you can sign up directly with your GitHub account, which also makes connecting the repo a one-click step.
3. From the Render dashboard: **New +** → **Web Service** → pick your `Weather-Dashboard` GitHub repo. Render should detect `render.yaml` and pre-fill the settings; if not, set them manually:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Instance Type:** Free
4. Under the **Environment** tab, add a variable: `OPENWEATHER_API_KEY` = your key. This is how the live site gets your key instead of a `.env` file (Render doesn't read `.env` files — environment variables are set in its dashboard instead).
5. Click **Create Web Service**. The first deploy takes a couple of minutes; afterwards you get a public URL like `https://weather-dashboard-xxxx.onrender.com` that works from any device with internet, phone included.

A couple of things worth knowing about Render's free tier: the app goes to sleep after a period of no traffic and takes ~30-50 seconds to wake up on the next visit (fine for personal use, noticeable if you're demoing it live), and the free plan doesn't include a custom domain (you get the `.onrender.com` one). Both are easy to upgrade later if this project outgrows them.

---

## Tech stack

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.8+ | Core programming language |
| Flask | 2.2.5 | Web framework, routing, and templating |
| Requests | 2.31.0 | HTTP calls to the OpenWeatherMap API |
| python-dotenv | 1.0.0 | Loads API key from the `.env` file |
| gunicorn | 21.2.0 | Production WSGI server (used when deployed, e.g. on Render) |
| OpenWeatherMap API | Free tier | Live weather, forecast, air quality, UV index and alerts |
| Jinja2 | (bundled with Flask) | HTML templating engine |
| Bootstrap | 5 (CDN) | Responsive layout and card styling |
| html2canvas | 1.4.1 (CDN) | Renders the weather card to a shareable PNG |
| Web App Manifest + Service Worker | — | Makes the site installable as a phone app (PWA) |
