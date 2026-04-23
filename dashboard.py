"""
Genereert het statische dashboard (docs/index.html) vanuit de SQLite database.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "nieuws.db"

THEMA_KLEUREN = {
    "mobiliteit": "#2563eb", "veiligheid": "#dc2626", "politiek": "#7c3aed",
    "cultuur": "#d97706", "sport": "#16a34a", "natuur": "#0891b2",
    "economie": "#9333ea", "algemeen": "#6b7280"
}


def get_data():
    conn = sqlite3.connect(DB_PATH)
    recent = conn.execute("""
        SELECT titel, url, bron_naam, datum, thema, toegevoegd
        FROM artikels ORDER BY toegevoegd DESC LIMIT 100
    """).fetchall()
    thema_30d = conn.execute("""
        SELECT thema, COUNT(*) as aantal FROM artikels
        WHERE toegevoegd >= date('now', '-30 days')
        GROUP BY thema ORDER BY aantal DESC
    """).fetchall()
    bron_30d = conn.execute("""
        SELECT bron_naam, COUNT(*) as aantal FROM artikels
        WHERE toegevoegd >= date('now', '-30 days')
        GROUP BY bron_naam ORDER BY aantal DESC
    """).fetchall()
    weekly = conn.execute("""
        SELECT strftime('%Y-W%W', toegevoegd) as week, COUNT(*) as aantal
        FROM artikels WHERE toegevoegd >= date('now', '-56 days')
        GROUP BY week ORDER BY week
    """).fetchall()
    totaal = conn.execute("SELECT COUNT(*) FROM artikels").fetchone()[0]
    conn.close()
    return recent, thema_30d, bron_30d, weekly, totaal


def build_dashboard():
    recent, thema_30d, bron_30d, weekly, totaal = get_data()
    nu = datetime.now().strftime("%d/%m/%Y %H:%M")

    thema_cards = ""
    for thema, count in thema_30d:
        kleur = THEMA_KLEUREN.get(thema, "#6b7280")
        thema_cards += f"""
        <div class="thema-card" onclick="filterThema('{thema}')" style="border-top:3px solid {kleur};">
            <div class="thema-count" style="color:{kleur};">{count}</div>
            <div class="thema-naam">{thema.capitalize()}</div>
        </div>"""

    week_labels = json.dumps([w[0] for w in weekly])
    week_values = json.dumps([w[1] for w in weekly])
    bron_labels = json.dumps([b[0] for b in bron_30d])
    bron_values = json.dumps([b[1] for b in bron_30d])

    artikel_rijen = ""
    for a in recent:
        titel, url, bron, datum, thema, toegevoegd = a
        kleur = THEMA_KLEUREN.get(thema, "#6b7280")
        datum_str = toegevoegd[:10] if toegevoegd else ""
        artikel_rijen += f"""
        <div class="artikel-rij" data-thema="{thema}">
            <span class="thema-badge" style="background:{kleur};">{thema}</span>
            <a href="{url}" target="_blank" class="artikel-titel">{titel}</a>
            <span class="artikel-meta">{bron} &middot; {datum_str}</span>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dendermonde Nieuws Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
    <style>
        *{{box-sizing:border-box;margin:0;padding:0;}}
        body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;}}
        header{{background:linear-gradient(135deg,#1e3a5f 0%,#0f172a 100%);padding:32px 24px;border-bottom:1px solid #1e293b;}}
        .header-inner{{max-width:1100px;margin:0 auto;display:flex;justify-content:space-between;align-items:flex-end;}}
        h1{{font-size:28px;font-weight:800;color:white;}} h1 span{{color:#60a5fa;}}
        .update-info{{font-size:12px;color:#64748b;text-align:right;}}
        .container{{max-width:1100px;margin:0 auto;padding:24px;}}
        .stats-row{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:32px;}}
        .stat-box{{background:#1e293b;border-radius:12px;padding:20px;text-align:center;border:1px solid #334155;}}
        .stat-num{{font-size:40px;font-weight:800;color:#60a5fa;line-height:1;}}
        .stat-label{{font-size:12px;color:#64748b;margin-top:6px;text-transform:uppercase;letter-spacing:1px;}}
        .section-title{{font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:2px;margin-bottom:16px;}}
        .thema-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:12px;margin-bottom:32px;}}
        .thema-card{{background:#1e293b;border-radius:10px;padding:16px;cursor:pointer;transition:transform 0.15s;border:1px solid #334155;}}
        .thema-card:hover{{background:#273548;transform:translateY(-2px);}}
        .thema-card.active{{background:#273548;border-color:#60a5fa;}}
        .thema-count{{font-size:28px;font-weight:800;line-height:1;}}
        .thema-naam{{font-size:12px;color:#94a3b8;margin-top:4px;}}
        .charts-grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:32px;}}
        .chart-box{{background:#1e293b;border-radius:12px;padding:20px;border:1px solid #334155;}}
        .chart-box canvas{{max-height:220px;}}
        .artikels-box{{background:#1e293b;border-radius:12px;padding:20px;border:1px solid #334155;}}
        .filter-bar{{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;align-items:center;}}
        .filter-bar input{{background:#0f172a;border:1px solid #334155;border-radius:6px;padding:8px 12px;color:#e2e8f0;font-size:13px;flex:1;min-width:200px;}}
        .btn-reset{{background:#334155;color:#94a3b8;border:none;border-radius:6px;padding:8px 14px;font-size:12px;cursor:pointer;}}
        .artikel-rij{{display:flex;align-items:flex-start;gap:10px;padding:10px 0;border-bottom:1px solid #1e293b;flex-wrap:wrap;}}
        .artikel-rij:last-child{{border-bottom:none;}}
        .thema-badge{{font-size:10px;font-weight:700;color:white;padding:2px 8px;border-radius:20px;white-space:nowrap;flex-shrink:0;margin-top:2px;}}
        .artikel-titel{{color:#e2e8f0;text-decoration:none;font-size:14px;flex:1;min-width:200px;}}
        .artikel-titel:hover{{color:#60a5fa;}}
        .artikel-meta{{font-size:11px;color:#475569;white-space:nowrap;flex-shrink:0;margin-top:2px;}}
        @media(max-width:640px){{.charts-grid{{grid-template-columns:1fr;}}}}
    </style>
</head>
<body>
<header>
    <div class="header-inner">
        <div>
            <h1>Dendermonde <span>Nieuws</span></h1>
            <div style="color:#64748b;font-size:13px;margin-top:4px;">Lokaal nieuwsoverzicht</div>
        </div>
        <div class="update-info">Laatste update<br>{nu}</div>
    </div>
</header>
<div class="container">
    <div class="stats-row">
        <div class="stat-box"><div class="stat-num">{totaal}</div><div class="stat-label">Totaal artikels</div></div>
        <div class="stat-box"><div class="stat-num">{len(thema_30d)}</div><div class="stat-label">Themas (30d)</div></div>
        <div class="stat-box"><div class="stat-num">{len(bron_30d)}</div><div class="stat-label">Bronnen</div></div>
    </div>
    <div class="section-title">Themas (laatste 30 dagen)</div>
    <div class="thema-grid">{thema_cards}</div>
    <div class="charts-grid">
        <div class="chart-box"><div class="section-title">Artikels per week</div><canvas id="weekChart"></canvas></div>
        <div class="chart-box"><div class="section-title">Verdeling per bron (30d)</div><canvas id="bronChart"></canvas></div>
    </div>
    <div class="artikels-box">
        <div class="section-title" style="margin-bottom:12px;">Recente artikels</div>
        <div class="filter-bar">
            <input type="text" id="zoek" placeholder="Zoek in titels..." oninput="filterArtikels()">
            <button class="btn-reset" onclick="resetFilters()">Reset filters</button>
        </div>
        <div id="artikels-lijst">{artikel_rijen}</div>
    </div>
</div>
<script>
new Chart(document.getElementById('weekChart'),{{type:'bar',data:{{labels:{week_labels},datasets:[{{label:'Artikels',data:{week_values},backgroundColor:'#2563eb',borderRadius:4}}]}},options:{{responsive:true,plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{color:'#64748b'}},grid:{{color:'#1e293b'}}}},y:{{ticks:{{color:'#64748b'}},grid:{{color:'#334155'}}}}}}}}}});
new Chart(document.getElementById('bronChart'),{{type:'doughnut',data:{{labels:{bron_labels},datasets:[{{data:{bron_values},backgroundColor:['#2563eb','#16a34a','#d97706','#dc2626'],borderWidth:0}}]}},options:{{responsive:true,plugins:{{legend:{{position:'bottom',labels:{{color:'#94a3b8',font:{{size:11}},boxWidth:12}}}}}}}}}});
let actievThema=null;
function filterThema(thema){{if(actievThema===thema){{actievThema=null;document.querySelectorAll('.thema-card').forEach(c=>c.classList.remove('active'));}}else{{actievThema=thema;document.querySelectorAll('.thema-card').forEach(c=>{{c.classList.toggle('active',c.querySelector('.thema-naam').textContent.toLowerCase()===thema.toLowerCase());}});}}filterArtikels();}}
function filterArtikels(){{const zoek=document.getElementById('zoek').value.toLowerCase();document.querySelectorAll('.artikel-rij').forEach(rij=>{{const titel=rij.querySelector('.artikel-titel').textContent.toLowerCase();const thema=rij.dataset.thema;rij.style.display=(!zoek||titel.includes(zoek))&&(!actievThema||thema===actievThema)?'':'none';}});}}
function resetFilters(){{actievThema=null;document.getElementById('zoek').value='';document.querySelectorAll('.thema-card').forEach(c=>c.classList.remove('active'));document.querySelectorAll('.artikel-rij').forEach(r=>r.style.display='');}}
</script>
</body>
</html>"""

    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("docs/index.html gegenereerd")


if __name__ == "__main__":
    build_dashboard()
