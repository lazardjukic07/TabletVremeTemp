from flask import Flask, jsonify, render_template_string, request, redirect
import time
import datetime
import requests
import re

app = Flask(__name__)

# --- TVOJA ADRESA ---
MOJA_ADRESA = "Petra Konjovića 12D, 11090 Beograd (Rakovica), Centralna Srbija"

current_message = {
    "text": "",
    "expires": 0,
    "received": ""
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

@app.route('/api/data')
def api_data():
    now = datetime.datetime.now()
    return jsonify(
        time=now.strftime("%H:%M"),
        date=get_serbian_date(),
        greeting=get_greeting(),
        temp="Temperatura: " + get_weather(),
        loc="Trenutna lokacija: " + MOJA_ADRESA
    )

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    global current_message

    if request.method == 'POST':
        msg = request.form.get('message', '').strip()

        if msg:
            current_message["text"] = msg
            current_message["expires"] = time.time() + 60
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
                width: 500px;
                background: #1e1e1e;
                padding: 30px;
                border-radius: 20px;
                box-shadow: 0 0 30px #000;
            }

            input {
                width: 100%;
                font-size: 26px;
                padding: 15px;
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
                <input name="message" placeholder="Unesi poruku..." autofocus>
                <button type="submit">Pošalji poruku na uređaje</button>
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

            #d {
                font-size: 32px;
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
                bottom: 40px;
                left: 0;
                right: 0;
                text-align:center; 
                font-size:24px; 
                line-height:1.5; 
            }

            .message-overlay {
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

            .message-header {
                position: absolute;
                top: 35px;
                left: 50px;
                right: 50px;
                text-align: center;
            }

            #msgTitle {
                font-size: 42px;
                font-weight: bold;
                color: white;
            }

            #msgReceived {
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
                text-shadow: none;
            }

            .close-msg {
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

        <div class="header">
            <div id="d">""" + init_date + """</div>
            <div id="g" class="greeting-right">""" + init_greeting + """</div>
        </div>

        <div id="t" class="clock">""" + init_time + """</div>

        <div class="footer">
            <div id="l">Trenutna lokacija: """ + MOJA_ADRESA + """</div>
            <div id="w">Temperatura: Učitavanje...</div>
        </div>

        <script>
            var audioCtx = null;
            var soundEnabled = false;
            var lastMessageKey = "";

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
                gain.gain.exponentialRampToValueAtTime(0.35, start + 0.02);
                gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);

                osc.connect(gain);
                gain.connect(audioCtx.destination);

                osc.start(start);
                osc.stop(start + duration);
            }

            function playMessageSound() {
                if (!soundEnabled || !audioCtx) return;

                var now = audioCtx.currentTime;

                beep(880, now, 0.12);
                beep(1175, now + 0.14, 0.18);
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
