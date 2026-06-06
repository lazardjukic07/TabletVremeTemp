from flask import Flask, jsonify, request, redirect
import time
import datetime
import requests
import math
import re

app = Flask(__name__)

# --- TVOJA ADRESA ---
MOJA_ADRESA = "Petra Konjovića 12D, 11090 Beograd (Rakovica), Centralna Srbija"

# --- BEOGRAD PLUS PODEŠAVANJA ---
ANNOUNCEMENT_URL = "https://online.bgnaplata.rs/sr/announcement_arrival/"

ANNOUNCEMENT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "sr,en;q=0.9,sr-RS;q=0.8,en-US;q=0.7",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://online.bgnaplata.rs",
    "X-Requested-With": "XMLHttpRequest",
}

ANNOUNCEMENT_BASE_DATA = {
    "b": "TS001831",
    "d": "2",
    "c": "1498",
    "s": "1",
}

# Stajališta koja se smenjuju u Beograd Plus prozoru
BUS_STATION_IDS = ["20867", "20868", "20939", "22365", "22910"]

STATIONS = {
    "20867": "Kanarevo brdo (867)",
    "20939": "OŠ Đura Jakšić (939)",
    "22365": "Miljakovac /Pijaca/ (2365)",
    "20040": "Vareška",
    "22909": "Vareška",
    "22910": "Vareška (2910)",
    "20868": "Kanarevo brdo",
}

current_message = {
    "text": "",
    "expires": 0,
    "received": ""
}

bus_cache = {}

air_cache = {
    "time": 0,
    "text": "Kvalitet vazduha: Učitavanje..."
}

def get_serbian_date():
    now = datetime.datetime.now()

    dani = {
        "Monday": "Ponedeljak",
        "Tuesday": "Utorak",
        "Wednesday": "Sreda",
        "Thursday": "Četvrtak",
        "Friday": "Petak",
        "Saturday": "Subota",
        "Sunday": "Nedelja"
    }

    meseci = {
        "January": "januar",
        "February": "februar",
        "March": "mart",
        "April": "april",
        "May": "maj",
        "June": "jun",
        "July": "jul",
        "August": "avgust",
        "September": "septembar",
        "October": "oktobar",
        "November": "novembar",
        "December": "decembar"
    }

    return f"{dani.get(now.strftime('%A'), '')}, {now.strftime('%d')}. {meseci.get(now.strftime('%B'), '')} {now.strftime('%Y')}."

def get_message_time():
    now = datetime.datetime.now()
    return f"{get_serbian_date()} u {now.strftime('%H:%M:%S')}"

def get_greeting():
    hour = datetime.datetime.now().hour

    if 0 <= hour < 12:
        return "Dobro jutro."
    elif 12 <= hour < 18:
        return "Dobar dan."
    elif 18 <= hour < 23:
        return "Dobro veče."
    else:
        return "Laku noć."

def get_weather():
    try:
        r = requests.get("https://wttr.in/Belgrade?format=%t %c", timeout=3)
        return re.sub(r'[^0-9°C-]', '', r.text) if r.status_code == 200 else "--°C"
    except:
        return "🌡️ --°C"

def describe_air_quality(aqi):
    try:
        aqi = int(aqi)

        if aqi <= 20:
            return "Dobar"
        elif aqi <= 40:
            return "Prilično dobar"
        elif aqi <= 60:
            return "Umeren"
        elif aqi <= 80:
            return "Loš"
        elif aqi <= 100:
            return "Veoma loš"
        else:
            return "Izuzetno loš"
    except:
        return "Nepoznato"

def get_air_quality():
    global air_cache

    now = time.time()

    # Keš 10 minuta
    if now - air_cache["time"] < 600:
        return air_cache["text"]

    try:
        url = "https://air-quality-api.open-meteo.com/v1/air-quality"

        params = {
            "latitude": 44.7866,
            "longitude": 20.4489,
            "current": "european_aqi,pm10,pm2_5"
        }

        r = requests.get(url, params=params, timeout=5)

        if r.status_code != 200:
            return "Kvalitet vazduha: --"

        data = r.json()
        current = data.get("current", {})

        aqi = current.get("european_aqi")
        pm25 = current.get("pm2_5")
        pm10 = current.get("pm10")

        if aqi is None:
            text = "Kvalitet vazduha: --"
        else:
            opis = describe_air_quality(aqi)
            text = f"Kvalitet vazduha: {opis} | AQI: {aqi} | PM2.5: {pm25} | PM10: {pm10}"

        air_cache["time"] = now
        air_cache["text"] = text

        return text

    except:
        return "Kvalitet vazduha: --"

def fetch_bus_arrivals(station_uid):
    headers = ANNOUNCEMENT_HEADERS.copy()
    headers["Referer"] = f"https://online.bgnaplata.rs/sr/announcement_arrival/{station_uid}"

    data = ANNOUNCEMENT_BASE_DATA.copy()
    data["r"] = str(station_uid)

    r = requests.post(
        ANNOUNCEMENT_URL,
        headers=headers,
        data=data,
        timeout=10
    )

    r.raise_for_status()
    return r.json()

def build_bus_arrivals(api_raw_data):
    try:
        vehicles = api_raw_data

        if not isinstance(vehicles, list) or len(vehicles) == 0:
            return []

        valid_vehicles = []

        for v in vehicles:
            try:
                seconds = int(v.get("seconds_left", 0))
            except:
                seconds = 0

            if seconds > 0:
                valid_vehicles.append(v)

        if not valid_vehicles:
            return []

        valid_vehicles.sort(key=lambda v: int(v.get("seconds_left", 99999)))

        zamene = {}

        arrivals = []

        for v in valid_vehicles[:5]:
            line = str(v.get("line_number", "??"))

            dest = v.get("main_line_title", "")

            if "-" in dest:
                dest = dest.split("-")[-1].strip()

            if not dest:
                dest = v.get("to_price", "")

            if not dest:
                dest = v.get("line_title", "")

            for stara, nova in zamene.items():
                dest = dest.replace(stara, nova)

            try:
                seconds = int(v.get("seconds_left", 0))
            except:
                seconds = 0

            # Isto kao na tvom displeju
            minutes = max(1, math.ceil(seconds / 60) - 1)

            arrivals.append({
                "main": f"{line} {dest}".strip(),
                "time": f"{minutes} min"
            })

        return arrivals

    except:
        return []

@app.route('/api/data')
def api_data():
    now = datetime.datetime.now()

    return jsonify(
        time=now.strftime("%H:%M"),
        date=get_serbian_date(),
        greeting=get_greeting(),
        temp="Temperatura: " + get_weather(),
        air=get_air_quality(),
        loc="Trenutna lokacija: " + MOJA_ADRESA
    )

@app.route('/api/arrivals')
def api_arrivals():
    global bus_cache

    station_uid = request.args.get("station", BUS_STATION_IDS[0])

    if station_uid not in BUS_STATION_IDS:
        station_uid = BUS_STATION_IDS[0]

    now = time.time()
    station_name = STATIONS.get(station_uid, station_uid)

    cached = bus_cache.get(station_uid)

    # Keš 15 sekundi po stajalištu
    if cached and now - cached["time"] < 15:
        return jsonify(
            ok=True,
            station_id=station_uid,
            station=cached["station"],
            arrivals=cached["data"],
            error=cached["error"]
        )

    try:
        raw = fetch_bus_arrivals(station_uid)
        arrivals = build_bus_arrivals(raw)

        if not arrivals:
            bus_cache[station_uid] = {
                "time": now,
                "data": [],
                "station": station_name,
                "error": "Trenutno nema dolazaka."
            }
        else:
            bus_cache[station_uid] = {
                "time": now,
                "data": arrivals,
                "station": station_name,
                "error": ""
            }

        return jsonify(
            ok=True,
            station_id=station_uid,
            station=bus_cache[station_uid]["station"],
            arrivals=bus_cache[station_uid]["data"],
            error=bus_cache[station_uid]["error"]
        )

    except Exception as e:
        bus_cache[station_uid] = {
            "time": now,
            "data": [],
            "station": station_name,
            "error": "Greška pri učitavanju dolazaka."
        }

        return jsonify(
            ok=False,
            station_id=station_uid,
            station=station_name,
            arrivals=[],
            error="Greška pri učitavanju dolazaka."
        )

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    global current_message

    if request.method == 'POST':
        msg = request.form.get('message', '').strip()

        try:
            duration = int(request.form.get('duration', '15'))
        except:
            duration = 15

        if msg:
            current_message["text"] = msg
            current_message["expires"] = time.time() + duration
            current_message["received"] = get_message_time()

        return redirect('/admin')

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Pošalji poruku</title>
        <style>
            body {
                background: #111;
                color: white;
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }

            .box {
                width: 520px;
                background: #1e1e1e;
                padding: 30px;
                border-radius: 20px;
                box-shadow: 0 0 30px #000;
            }

            textarea {
                width: 100%;
                height: 160px;
                font-size: 26px;
                padding: 15px;
                box-sizing: border-box;
                border-radius: 10px;
                border: none;
                margin-bottom: 20px;
                resize: none;
                font-family: Arial, sans-serif;
            }

            select {
                width: 100%;
                font-size: 22px;
                padding: 12px;
                box-sizing: border-box;
                border-radius: 10px;
                border: none;
                margin-bottom: 20px;
            }

            button {
                width: 100%;
                font-size: 24px;
                padding: 15px;
                background: #0f0;
                color: #000;
                font-weight: bold;
                border: none;
                border-radius: 10px;
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <div class="box">
            <h1>Pošalji poruku na ekran</h1>

            <form method="POST">
                <textarea name="message" placeholder="Unesi poruku..." autofocus></textarea>

                <select name="duration">
                    <option value="5">5 sekundi</option>
                    <option value="10">10 sekundi</option>
                    <option value="15" selected>15 sekundi</option>
                    <option value="30">30 sekundi</option>
                    <option value="60">60 sekundi</option>
                </select>

                <button type="submit">Prikaži poruku</button>
            </form>
        </div>
    </body>
    </html>
    """

@app.route('/api/message')
def api_message():
    if current_message["text"] and time.time() < current_message["expires"]:
        return jsonify(
            show=True,
            text=current_message["text"],
            received=current_message["received"]
        )
    else:
        return jsonify(show=False, text="", received="")

@app.route('/api/clear-message', methods=['POST'])
def clear_message():
    current_message["text"] = ""
    current_message["expires"] = 0
    current_message["received"] = ""
    return jsonify(ok=True)

@app.route('/')
def index():
    now = datetime.datetime.now()
    init_time = now.strftime("%H:%M")
    init_date = get_serbian_date()
    init_greeting = get_greeting()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <style>
            body { 
                background:#000; 
                color:#fff; 
                font-family:Arial,sans-serif; 
                height:100vh; 
                margin:0; 
                overflow:hidden; 
                position: relative;
            }

            .header { 
                position: absolute;
                top: 40px;
                left: 40px;
                right: 40px;
                display:flex; 
                justify-content:space-between; 
                align-items:flex-start;
                font-size:22px; 
            }

            .left-header {
                display: flex;
                flex-direction: column;
                align-items: flex-start;
            }

            #d {
                font-size: 32px;
            }

            .beograd-plus {
                margin-top: 8px;
                font-size: 26px;
                color: #ff8c00;
                cursor: pointer;
                font-weight: bold;
                user-select: none;
            }

            .beograd-plus:active {
                transform: scale(0.97);
            }

            .greeting-right {
                text-align:right;
                color:#ff0303;
                font-size:32px;
            }

            .clock { 
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size:200px; 
                font-weight:bold; 
                color:#0f0; 
                margin:0;
            }

            .footer { 
                position: absolute;
                bottom: 35px;
                left: 0;
                right: 0;
                text-align:center; 
                font-size:24px; 
                line-height:1.5; 
            }

            #aq {
                font-size: 22px;
                color: #ccc;
            }

            .message-overlay,
            .arrivals-overlay {
                display: none;
                position: fixed;
                inset: 0;
                background: rgba(0, 0, 0, 0.96);
                color: white;
                z-index: 9999;
                justify-content: center;
                align-items: center;
                text-align: center;
                padding: 50px;
                box-sizing: border-box;
                flex-direction: column;
            }

            .message-header,
            .arrivals-header {
                position: absolute;
                top: 35px;
                left: 50px;
                right: 50px;
                text-align: center;
            }

            #msgTitle,
            #arrivalsTitle {
                font-size: 32px;
                font-weight: bold;
                color: white;
            }

            #msgReceived,
            #arrivalsSubtitle {
                margin-top: 8px;
                font-size: 24px;
                color: #ccc;
            }

            #msgText {
                font-size: 70px;
                font-weight: bold;
                color: white;
                max-width: 90%;
                word-break: break-word;
                white-space: pre-wrap;
                text-shadow: none;
            }

            .close-msg,
            .close-arrivals {
                position: absolute;
                top: 25px;
                right: 35px;
                font-size: 45px;
                background: none;
                border: none;
                color: white;
                cursor: pointer;
                z-index: 10000;
            }

            .arrivals-box {
                width: min(900px, 92vw);
                margin-top: 90px;
            }

            .arrival-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 30px;
                padding: 13px 0;
                border-bottom: 1px solid rgba(255, 140, 0, 0.25);
                color: #ff8c00;
                font-size: 42px;
                font-weight: bold;
                text-align: left;
            }

            .arrival-main {
                overflow: hidden;
                white-space: nowrap;
                text-overflow: ellipsis;
            }

            .arrival-time {
                min-width: 150px;
                text-align: right;
                white-space: nowrap;
            }

            .arrivals-error {
                color: #ff8c00;
                font-size: 42px;
                font-weight: bold;
            }

            .sound-enable {
                position: fixed;
                bottom: 25px;
                right: 25px;
                z-index: 10001;
                font-size: 20px;
                padding: 12px 18px;
                border-radius: 12px;
                border: none;
                background: #0f0;
                color: #000;
                font-weight: bold;
                cursor: pointer;
            }
        </style>
    </head>

    <body>
        <button id="soundBtn" class="sound-enable" onclick="enableSound()">Omogući zvuk</button>

        <div id="msgOverlay" class="message-overlay">
            <button class="close-msg" onclick="closeMessage()">×</button>

            <div class="message-header">
                <div id="msgTitle">Nova poruka</div>
                <div id="msgReceived"></div>
            </div>

            <div id="msgText"></div>
        </div>

        <div id="arrivalsOverlay" class="arrivals-overlay">
            <button class="close-arrivals" onclick="closeArrivals()">×</button>

            <div class="arrivals-header">
                <div id="arrivalsTitle">Dolazak vozila na stajalište</div>
                <div id="arrivalsSubtitle">Učitavanje dolazaka...</div>
            </div>

            <div id="arrivalsList" class="arrivals-box"></div>
        </div>

        <div class="header">
            <div class="left-header">
                <div id="d">""" + init_date + """</div>
                <div id="bpLink" class="beograd-plus" onclick="openArrivals()">Beograd Plus (klikni da otvoriš informacije o dolascima)</div>
            </div>

            <div id="g" class="greeting-right">""" + init_greeting + """</div>
        </div>

        <div id="t" class="clock">""" + init_time + """</div>

        <div class="footer">
            <div id="l">Trenutna lokacija: """ + MOJA_ADRESA + """</div>
            <div id="w">Temperatura: Učitavanje...</div>
            <div id="aq">Kvalitet vazduha: Učitavanje...</div>
        </div>

        <script>
            var audioCtx = null;
            var soundEnabled = false;
            var lastMessageKey = "";
            var arrivalsTimer = null;

            var stationPages = ["20867", "20939", "22365", "22910"];
            var stationIndex = 0;

            function enableSound() {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                audioCtx.resume();

                soundEnabled = true;
                document.getElementById('soundBtn').style.display = 'none';

                playMessageSound();
            }

            function beep(freq, start, duration) {
                if (!audioCtx) return;

                var osc = audioCtx.createOscillator();
                var gain = audioCtx.createGain();

                osc.type = "sine";
                osc.frequency.setValueAtTime(freq, start);

                gain.gain.setValueAtTime(0.0001, start);
                gain.gain.exponentialRampToValueAtTime(0.6, start + 0.02);
                gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);

                osc.connect(gain);
                gain.connect(audioCtx.destination);

                osc.start(start);
                osc.stop(start + duration);
            }

            function playMessageSound() {
                if (!soundEnabled || !audioCtx) return;

                var now = audioCtx.currentTime;

                beep(1040, now, 0.08);
                beep(1320, now + 0.10, 0.08);
                beep(1560, now + 0.20, 0.12);
            }

            function update() {
                var xhr = new XMLHttpRequest();
                xhr.open('GET', '/api/data', true);

                xhr.onreadystatechange = function() {
                    if (xhr.readyState == 4 && xhr.status == 200) {
                        var data = JSON.parse(xhr.responseText);

                        document.getElementById('d').textContent = data.date;
                        document.getElementById('g').textContent = data.greeting;
                        document.getElementById('t').textContent = data.time;
                        document.getElementById('l').textContent = data.loc;
                        document.getElementById('w').textContent = data.temp;
                        document.getElementById('aq').textContent = data.air;
                    }
                };

                xhr.send();
            }

            function checkMessage() {
                fetch('/api/message')
                    .then(response => response.json())
                    .then(data => {
                        var overlay = document.getElementById('msgOverlay');
                        var text = document.getElementById('msgText');
                        var received = document.getElementById('msgReceived');

                        if (data.show) {
                            var messageKey = data.text + "|" + data.received;

                            text.textContent = data.text;
                            received.textContent = data.received;
                            overlay.style.display = 'flex';

                            if (messageKey !== lastMessageKey) {
                                playMessageSound();
                                lastMessageKey = messageKey;
                            }
                        } else {
                            overlay.style.display = 'none';
                            lastMessageKey = "";
                        }
                    });
            }

            function closeMessage() {
                fetch('/api/clear-message', {
                    method: 'POST'
                });

                document.getElementById('msgOverlay').style.display = 'none';
                lastMessageKey = "";
            }

            function openArrivals() {
                document.getElementById('arrivalsOverlay').style.display = 'flex';

                stationIndex = 0;
                loadArrivals();

                if (arrivalsTimer) {
                    clearInterval(arrivalsTimer);
                }

                arrivalsTimer = setInterval(function() {
                    stationIndex = (stationIndex + 1) % stationPages.length;
                    loadArrivals();
                }, 7000);
            }

            function closeArrivals() {
                document.getElementById('arrivalsOverlay').style.display = 'none';

                if (arrivalsTimer) {
                    clearInterval(arrivalsTimer);
                    arrivalsTimer = null;
                }
            }

            function loadArrivals() {
                var subtitle = document.getElementById('arrivalsSubtitle');
                var title = document.getElementById('arrivalsTitle');
                var list = document.getElementById('arrivalsList');

                var stationId = stationPages[stationIndex];

                subtitle.textContent = "Učitavanje dolazaka...";
                list.innerHTML = "";

                fetch('/api/arrivals?station=' + stationId)
                    .then(response => response.json())
                    .then(data => {
                        list.innerHTML = "";

                        var now = new Date();
                        var hh = String(now.getHours()).padStart(2, '0');
                        var mm = String(now.getMinutes()).padStart(2, '0');
                        var ss = String(now.getSeconds()).padStart(2, '0');

                        title.textContent = "Dolazak vozila na stajalište: " + data.station;
                        subtitle.textContent = "Strana " + (stationIndex + 1) + "/" + stationPages.length + " | Ažurirano: " + hh + ":" + mm + ":" + ss;

                        if (!data.arrivals || data.arrivals.length === 0) {
                            var err = document.createElement('div');
                            err.className = 'arrivals-error';
                            err.textContent = data.error || "Trenutno nema dolazaka.";
                            list.appendChild(err);
                            return;
                        }

                        data.arrivals.forEach(function(item) {
                            var row = document.createElement('div');
                            row.className = 'arrival-row';

                            var main = document.createElement('div');
                            main.className = 'arrival-main';
                            main.textContent = item.main;

                            var time = document.createElement('div');
                            time.className = 'arrival-time';
                            time.textContent = item.time;

                            row.appendChild(main);
                            row.appendChild(time);
                            list.appendChild(row);
                        });
                    })
                    .catch(() => {
                        title.textContent = "Beograd Plus";
                        subtitle.textContent = "Greška";
                        list.innerHTML = "";

                        var err = document.createElement('div');
                        err.className = 'arrivals-error';
                        err.textContent = "Greška pri učitavanju dolazaka.";
                        list.appendChild(err);
                    });
            }

            setInterval(checkMessage, 1000);
            checkMessage();

            setInterval(update, 7000);
            update();
        </script>
    </body>
    </html>
    """

    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
