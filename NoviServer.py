from flask import Flask, jsonify
import datetime
import requests
import re

app = Flask(__name__)

# --- TVOJA ADRESA ---
MOJA_ADRESA = "Petra Konjovića 12D, 11090 Beograd (Rakovica), Centralna Srbija"

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
        return r.text.strip().replace("+", "") if r.status_code == 200 else "--°C"
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
                color:#4d83f0;
                font-size:32px;
            }

            /* FIKSIRAN SAT TAČNO U CENTRU */
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
        </style>
    </head>
    <body>
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
            function update() {
                var xhr = new XMLHttpRequest();
                xhr.open('GET', '/api/data', true);
                xhr.onreadystatechange = function() {
                    if (xhr.readyState == 4 && xhr.status == 200) {
                        var data = JSON.parse(xhr.responseText);
                        document.getElementById('d').innerHTML = data.date;
                        document.getElementById('g').innerHTML = data.greeting;
                        document.getElementById('t').innerHTML = data.time;
                        document.getElementById('l').innerHTML = data.loc;
                        document.getElementById('w').innerHTML = data.temp;
                    }
                };
                xhr.send();
            }

            setInterval(update, 7000);
            update();
        </script>
    </body>
    </html>
    """
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
