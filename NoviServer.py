from flask import Flask, jsonify, render_template_string
import datetime
import requests
import re

app = Flask(__name__)

# --- TVOJA ADRESA ---
MOJA_ADRESA = "Petra Konjovića 12D, 11090 Beograd (Rakovica), Centralna Srbija"

def get_serbian_date():
    now = datetime.datetime.now()
    dani = {"Monday": "Ponedeljak", "Tuesday": "Utorak", "Wednesday": "Sreda", "Thursday": "Četvrtak", "Friday": "Petak", "Saturday": "Subota", "Sunday": "Nedelja"}
    meseci = {"January": "januar", "February": "februar", "March": "mart", "April": "april", "May": "maj", "June": "jun", "July": "jul", "August": "avgust", "September": "septembar", "October": "oktobar", "November": "novembar", "December": "decembar"}
    return f"{dani.get(now.strftime('%A'), '')}, {now.strftime('%d')}. {meseci.get(now.strftime('%B'), '')} {now.strftime('%Y')}."

def get_weather():
    try:
        r = requests.get("https://wttr.in/Belgrade?format=%t", timeout=3)
        return re.sub(r'[^0-9°C-]', '', r.text) if r.status_code == 200 else "--°C"
    except:
        return "--°C"

@app.route('/api/data')
def api_data():
    now = datetime.datetime.now()
    return jsonify(
        time=now.strftime("%H:%M"),
        date=get_serbian_date(),
        temp="Temperatura: " + get_weather(),
        loc="Trenutna lokacija: " + MOJA_ADRESA
    )

@app.route('/')
def index():
    now = datetime.datetime.now()
    init_time = now.strftime("%H:%M")
    init_date = get_serbian_date()
    
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
                font-size:22px; 
            }
            .perm { 
                text-align:right; 
                color:#f00; 
                font-weight:bold; 
                line-height: 1.2;
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
            <div class="perm">Korišćenje lokacije: DA<br>Korišćenje kamere: NE<br>Internet konekcija: DA</div>
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
                        document.getElementById('t').innerHTML = data.time;
                        document.getElementById('l').innerHTML = data.loc;
                        document.getElementById('w').innerHTML = data.temp;
                    }
                };
                xhr.send();
            }
            setInterval(update, 10000);
            update();
        </script>
    </body>
    </html>
    """
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
