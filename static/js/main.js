// ==========================================================================
// Weather Dashboard front-end behaviour
// ==========================================================================

// --------------------------------------------------------------------------
// Mobile nav (hamburger toggle)
// --------------------------------------------------------------------------
const navToggle = document.getElementById('navToggle');
const navLinks = document.getElementById('navLinks');
if (navToggle && navLinks) {
    navToggle.addEventListener('click', () => {
        const isOpen = navLinks.classList.toggle('open');
        navToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
    // Close the menu after picking a link, so it doesn't stay open on the next page.
    navLinks.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
        navLinks.classList.remove('open');
        navToggle.setAttribute('aria-expanded', 'false');
    }));
}

// --------------------------------------------------------------------------
// Installable app support (PWA service worker)
// --------------------------------------------------------------------------
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js').catch(() => {});
    });
}

// Show spinner on submit
const form = document.querySelector('form[action="/"]') || document.querySelector('form');
const spinner = document.getElementById('loadingSpinner');
if (form && spinner) {
    form.addEventListener('submit', () => { spinner.style.display = 'block'; });
}

// --------------------------------------------------------------------------
// Temperature unit switch (°C / °F) — applies to every element carrying a
// data-temp-c attribute, across the hero card, hourly strip, daily cards and
// details list.
// --------------------------------------------------------------------------
const celsiusBtn = document.getElementById('celsiusBtn');
const fahrenheitBtn = document.getElementById('fahrenheitBtn');
let currentUnit = localStorage.getItem('weatherUnit') || 'C';

function convertTemp(tempC) {
    return currentUnit === 'C' ? tempC : (tempC * 9 / 5 + 32);
}

function updateTemperatures() {
    document.querySelectorAll('[data-temp-c]').forEach(el => {
        const raw = parseFloat(el.dataset.tempC);
        if (isNaN(raw)) return;
        const converted = convertTemp(raw);
        const decimals = el.dataset.tempDecimals ? parseInt(el.dataset.tempDecimals, 10) : 0;
        el.innerText = converted.toFixed(decimals) + '°' + currentUnit;
    });
    document.querySelectorAll('.unit-label').forEach(el => { el.innerText = '°' + currentUnit; });
    if (celsiusBtn && fahrenheitBtn) {
        celsiusBtn.classList.toggle('btn-primary', currentUnit === 'C');
        celsiusBtn.classList.toggle('btn-outline-primary', currentUnit !== 'C');
        fahrenheitBtn.classList.toggle('btn-primary', currentUnit === 'F');
        fahrenheitBtn.classList.toggle('btn-outline-secondary', currentUnit !== 'F');
    }
}

if (celsiusBtn && fahrenheitBtn) {
    celsiusBtn.onclick = () => { currentUnit = 'C'; localStorage.setItem('weatherUnit', 'C'); updateTemperatures(); };
    fahrenheitBtn.onclick = () => { currentUnit = 'F'; localStorage.setItem('weatherUnit', 'F'); updateTemperatures(); };
}
updateTemperatures();

// --------------------------------------------------------------------------
// Recent search history (stored client-side)
// --------------------------------------------------------------------------
const historyDiv = document.getElementById('historyButtons');
const searchInput = document.querySelector('input[name="city"]');
if (historyDiv && searchInput && form) {
    let history = JSON.parse(localStorage.getItem('weatherHistory') || '[]');
    function renderHistory() {
        historyDiv.innerHTML = '';
        history.forEach(city => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-sm btn-outline-secondary me-1 mb-1';
            btn.innerText = city;
            btn.onclick = () => { searchInput.value = city; searchInput.required = true; form.submit(); };
            historyDiv.appendChild(btn);
        });
    }
    renderHistory();
    form.addEventListener('submit', () => {
        const city = searchInput.value.trim();
        if (city && !history.includes(city)) {
            history.unshift(city);
            if (history.length > 5) history.pop();
            localStorage.setItem('weatherHistory', JSON.stringify(history));
        }
        renderHistory();
    });
}

// Refresh Button
const refreshBtn = document.getElementById('refreshBtn');
if (refreshBtn && searchInput && form) {
    refreshBtn.onclick = () => { const city = searchInput.value.trim(); if (city) form.submit(); };
}

// --------------------------------------------------------------------------
// "Use my location" — browser geolocation, submits lat/lon instead of a city
// --------------------------------------------------------------------------
const locateBtn = document.getElementById('locateBtn');
const latField = document.getElementById('latField');
const lonField = document.getElementById('lonField');
if (locateBtn && latField && lonField && form) {
    locateBtn.addEventListener('click', () => {
        if (!navigator.geolocation) {
            alert('Geolocation is not supported by this browser.');
            return;
        }
        const originalText = locateBtn.innerText;
        locateBtn.disabled = true;
        locateBtn.innerText = '📍 Locating…';
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                latField.value = pos.coords.latitude;
                lonField.value = pos.coords.longitude;
                if (searchInput) { searchInput.value = ''; searchInput.required = false; }
                if (spinner) spinner.style.display = 'block';
                form.submit();
            },
            () => {
                locateBtn.disabled = false;
                locateBtn.innerText = originalText;
                alert('Could not get your location. Please allow location access and try again.');
            },
            { timeout: 10000 }
        );
    });
}

// --------------------------------------------------------------------------
// Auto-detect location on a visitor's very first load. Only fires once ever
// per browser (tracked in localStorage) so it never nags on repeat visits or
// after someone dismisses/denies it once.
// --------------------------------------------------------------------------
if (document.body.dataset.firstVisit === 'true' && locateBtn && !localStorage.getItem('weatherGeoPrompted')) {
    localStorage.setItem('weatherGeoPrompted', '1');
    if (navigator.geolocation) {
        // Small delay so the page finishes rendering before the permission
        // prompt interrupts the visitor.
        setTimeout(() => { locateBtn.click(); }, 600);
    }
}

// --------------------------------------------------------------------------
// Share the current-conditions card as a downloadable PNG image.
// Requires html2canvas to already be loaded on the page (dashboard.html
// pulls it in only where the share button exists).
// --------------------------------------------------------------------------
const shareBtn = document.getElementById('shareCardBtn');
const shareTarget = document.getElementById('heroCard');
if (shareBtn && shareTarget) {
    shareBtn.addEventListener('click', () => {
        if (typeof html2canvas !== 'function') {
            alert('Could not load the image tool. Check your connection and try again.');
            return;
        }
        const originalText = shareBtn.innerText;
        shareBtn.disabled = true;
        shareBtn.innerText = '📸 Rendering…';
        html2canvas(shareTarget, { backgroundColor: null, scale: 2 }).then(canvas => {
            canvas.toBlob(blob => {
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                const cityPart = (shareTarget.dataset.city || 'weather').toLowerCase().replace(/[^a-z0-9]+/g, '-');
                a.href = url;
                a.download = `weather-${cityPart}.png`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                setTimeout(() => URL.revokeObjectURL(url), 2000);
                shareBtn.disabled = false;
                shareBtn.innerText = originalText;
            });
        }).catch(() => {
            shareBtn.disabled = false;
            shareBtn.innerText = originalText;
            alert('Could not create the image. Please try again.');
        });
    });
}

// --------------------------------------------------------------------------
// Animated weather scene — pure CSS/JS, no external images required, so it
// works identically in offline demo mode and with live data.
// --------------------------------------------------------------------------
function buildWeatherScene(weatherMain, isDay) {
    const scene = document.getElementById('weather-scene');
    if (!scene) return;
    scene.innerHTML = '';

    const rand = (min, max) => Math.random() * (max - min) + min;

    function addClouds(count) {
        for (let i = 0; i < count; i++) {
            const cloud = document.createElement('div');
            cloud.className = 'wx-cloud';
            const w = rand(80, 180);
            const h = w * 0.4;
            cloud.style.width = w + 'px';
            cloud.style.height = h + 'px';
            cloud.style.top = rand(5, 45) + '%';
            cloud.style.opacity = rand(0.5, 0.95);
            const dur = rand(40, 90);
            cloud.style.animationDuration = dur + 's';
            cloud.style.animationDelay = '-' + rand(0, dur) + 's';
            scene.appendChild(cloud);
        }
    }

    function addRain(count) {
        for (let i = 0; i < count; i++) {
            const drop = document.createElement('div');
            drop.className = 'wx-raindrop';
            drop.style.left = rand(0, 100) + '%';
            const dur = rand(0.5, 1.1);
            drop.style.animationDuration = dur + 's';
            drop.style.animationDelay = '-' + rand(0, dur) + 's';
            drop.style.opacity = rand(0.4, 0.9);
            scene.appendChild(drop);
        }
    }

    function addSnow(count) {
        for (let i = 0; i < count; i++) {
            const flake = document.createElement('div');
            flake.className = 'wx-snowflake';
            flake.innerText = '❄';
            flake.style.left = rand(0, 100) + '%';
            flake.style.fontSize = rand(8, 18) + 'px';
            const dur = rand(6, 14);
            flake.style.animationDuration = dur + 's';
            flake.style.animationDelay = '-' + rand(0, dur) + 's';
            flake.style.opacity = rand(0.5, 1);
            scene.appendChild(flake);
        }
    }

    function addStars(count) {
        for (let i = 0; i < count; i++) {
            const star = document.createElement('div');
            star.className = 'wx-star';
            star.style.left = rand(0, 100) + '%';
            star.style.top = rand(0, 55) + '%';
            const dur = rand(2, 5);
            star.style.animationDuration = dur + 's';
            star.style.animationDelay = '-' + rand(0, dur) + 's';
            scene.appendChild(star);
        }
    }

    function addFog(count) {
        for (let i = 0; i < count; i++) {
            const band = document.createElement('div');
            band.className = 'wx-fogband';
            band.style.top = rand(15, 80) + '%';
            const dur = rand(10, 20);
            band.style.animationDuration = dur + 's';
            band.style.animationDelay = '-' + rand(0, dur) + 's';
            scene.appendChild(band);
        }
    }

    if (isDay) {
        const sun = document.createElement('div');
        sun.className = 'wx-sun';
        scene.appendChild(sun);
    } else {
        const moon = document.createElement('div');
        moon.className = 'wx-moon';
        // Shape the crescent/gibbous to match today's real moon phase
        // (computed server-side, no extra API call) instead of always
        // drawing a fixed half-moon.
        const fraction = parseFloat(document.body.dataset.moonFraction);
        if (!isNaN(fraction)) {
            const litFraction = fraction <= 0.5 ? fraction * 2 : (1 - fraction) * 2; // 0..1..0
            const waxing = fraction <= 0.5;
            const maxOffset = 26; // px -- beyond the moon's radius, so "full" hides the shadow entirely
            const offset = (1 - litFraction) * maxOffset;
            moon.style.setProperty('--moon-shadow-x', (waxing ? -offset : offset) + 'px');
        }
        scene.appendChild(moon);
        addStars(40);
    }

    if (weatherMain.includes('cloud')) {
        addClouds(5);
    } else if (weatherMain === 'clear') {
        // nothing extra — sun/moon + stars already added
    }

    if (weatherMain.includes('thunderstorm')) {
        addClouds(6);
        addRain(90);
        const flash = document.createElement('div');
        flash.className = 'wx-flash';
        scene.appendChild(flash);
    } else if (weatherMain.includes('rain') || weatherMain.includes('drizzle')) {
        addClouds(4);
        addRain(70);
    } else if (weatherMain.includes('snow')) {
        addClouds(3);
        addSnow(60);
    } else if (weatherMain.includes('mist') || weatherMain.includes('fog') || weatherMain.includes('haze') || weatherMain.includes('smoke')) {
        addFog(5);
    }
}

const sceneRoot = document.getElementById('weather-scene');
if (sceneRoot) {
    const weatherMain = (document.body.dataset.weather || 'clear').toLowerCase();
    const isDay = document.body.dataset.daytime !== 'night';
    buildWeatherScene(weatherMain, isDay);
}
