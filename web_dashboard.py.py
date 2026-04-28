from flask import Flask, render_template, jsonify
import sqlite3
import plotly.graph_objs as go
import plotly.utils
import json
from config import WEB_SECRET_KEY

app = Flask(__name__)
app.secret_key = WEB_SECRET_KEY

def get_db():
    return sqlite3.connect("parti.db")

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/lig_tablosu/<int:lig_id>')
def lig_tablosu(lig_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT isim, puan, galibiyet, beraberlik, maglubiyet, atilan_gol, yenilen_gol FROM takimlar WHERE lig_id=? ORDER BY puan DESC", (lig_id,))
    rows = cur.fetchall()
    return jsonify([{"isim":r[0],"puan":r[1],"galibiyet":r[2],"beraberlik":r[3],"maglubiyet":r[4],"atilan_gol":r[5],"yenilen_gol":r[6]} for r in rows])

@app.route('/api/gol_krallari')
def gol_krallari():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT o.isim, o.gol, t.isim AS takim FROM oyuncular o JOIN takimlar t ON o.takim_id=t.takim_id ORDER BY o.gol DESC LIMIT 10")
    rows = cur.fetchall()
    return jsonify([{"isim":r[0],"gol":r[1],"takim":r[2]} for r in rows])

@app.route('/api/istatistikler')
def istatistikler():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM takimlar")
    takim_say = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM oyuncular")
    oyuncu_say = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM fikstur WHERE oynanmis=1")
    mac_say = cur.fetchone()[0]
    return jsonify({"takim_sayisi": takim_say, "oyuncu_sayisi": oyuncu_say, "mac_sayisi": mac_say})

if __name__ == '__main__':
    app.run(debug=True, port=5000)