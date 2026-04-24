"""
Genereert het statische dashboard (docs/index.html) vanuit de SQLite database.
Versie 3: lichter thema, 5-weken grafiek, multi-filter op thema en bron.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "nieuws.db"

THEMA_KLEUREN = {
    "mobiliteit": "#3b82f6", "veiligheid": "#ef4444", "politiek": "#8b5cf6",
    "cultuur": "#f59e0b", "sport": "#22c55e", "natuur": "#06b6d4",
    "economie": "#a855f7", "algemeen": "#94a3b8"
}


def get_data():
    conn = sqlite3.connect(DB_PATH)
    recent = conn.execute("""
        SELECT titel, url, bron_naam, datum, thema, toegevoegd
        FROM artikels ORDER BY toegevoegd DESC LIMIT 200
    """).fetchall()
    thema_30d = conn.execute("""
        SELECT thema, COUNT(*) as aantal FROM artikels
        WHERE date(toegevoegd) >= date('now', '-30 days')
        GROUP BY thema ORDER BY aantal DESC
    """).fetchall()
    bron_30d = conn.execute("""
        SELECT bron_naam, COUNT(*) as aantal FROM artikels
        WHERE date(toegevoegd) >= date('now', '-30 days')
        GROUP BY bron_naam ORDER BY aantal DESC
    """).fetchall()
    weekly_raw = conn.execute("""
        SELECT strftime('%Y-W%W', toegevoegd) as week,
               thema, bron_naam, COUNT(*) as aantal
        FROM artikels WHERE date(toegevoegd) >= date('now', '-35 days')
        GROUP BY week, thema, bron_naam ORDER BY week
    """).fetchall()
    totaal = conn.execute("SELECT COUNT(*) FROM artikels").fetchone()[0]
    bronnen = conn.execute("SELECT DISTINCT bron_naam FROM artikels ORDER BY bron_naam").fetchall()
    conn.close()
    return recent, thema_30d, bron_30d, weekly_raw, totaal, bronnen


def build_dashboard():
    recent, thema_30d, bron_30d, weekly_raw, totaal, bronnen = get_data()
    nu = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Thema kaarten
    thema_cards = ""
    for thema, count in thema_30d:
        kleur = THEMA_KLEUREN.get(thema, "#94a3b8")
        thema_cards += (
            '<div class="thema-card" onclick="toggleFilter(\'thema\',\'' + thema + '\')" '
            'data-thema="' + thema + '" style="border-top:3px solid ' + kleur + ';">'
            '<div class="thema-count" style="color:' + kleur + ';">' + str(count) + '</div>'
            '<div class="thema-naam">' + thema.capitalize() + '</div></div>\n'
        )

    # Week data
    week_data = {}
    for row in weekly_raw:
        week, thema, bron, aantal = row
        if week not in week_data:
            week_data[week] = {"totaal": 0, "themas": {}, "bronnen": {}}
        week_data[week]["totaal"] += aantal
        week_data[week]["themas"][thema] = week_data[week]["themas"].get(thema, 0) + aantal
        week_data[week]["bronnen"][bron] = week_data[week]["bronnen"].get(bron, 0) + aantal

    week_data_json = json.dumps(week_data)
    bron_labels = json.dumps([b[0] for b in bron_30d])
    bron_values = json.dumps([b[1] for b in bron_30d])
    alle_bronnen = json.dumps([b[0] for b in bronnen])
    thema_kleuren_json = json.dumps(THEMA_KLEUREN)

    # Artikel rijen
    artikel_rijen = ""
    for a in recent:
        titel, url, bron, datum, thema, toegevoegd = a
        titel = titel.replace("'", "&#39;").replace('"', '&quot;') 
        kleur = THEMA_KLEUREN.get(thema, "#94a3b8")
        datum_str = toegevoegd[:10] if toegevoegd else ""       
        artikel_rijen += (
            '<div class="artikel-rij" data-thema="' + thema + '" data-bron="' + bron + '">'
            '<span class="thema-badge" style="background:' + kleur + ';">' + thema + '</span>'
            '<a href="' + url + '" target="_blank" class="artikel-titel">' + titel + '</a>'
            '<span class="artikel-meta">' + bron + ' &middot; ' + datum_str + '</span></div>\n'
        )

    # Bouw HTML - geen f-string voor het JS gedeelte
    html_parts = []
    html_parts.append("""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dendermonde Nieuws Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        *{box-sizing:border-box;margin:0;padding:0;}
        body{font-family:'Inter',sans-serif;background:#f0f4f8;color:#1e293b;}
        header{background:linear-gradient(135deg,#1e3a5f 0%,#2563eb 100%);padding:28px 32px;}
        .header-inner{max-width:1200px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;}
        h1{font-size:26px;font-weight:800;color:white;} h1 span{color:#93c5fd;}
        .update-info{font-size:12px;color:#bfdbfe;text-align:right;line-height:1.6;}
        .container{max-width:1200px;margin:0 auto;padding:24px 32px;}
        .stats-row{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:28px;}
        .stat-box{background:white;border-radius:14px;padding:22px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.08);border:1px solid #e2e8f0;}
        .stat-num{font-size:42px;font-weight:800;color:#2563eb;line-height:1;}
        .stat-label{font-size:11px;color:#94a3b8;margin-top:6px;text-transform:uppercase;letter-spacing:1.5px;font-weight:600;}
        .section-title{font-size:11px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:2px;margin-bottom:14px;}
        .thema-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:12px;margin-bottom:28px;}
        .thema-card{background:white;border-radius:12px;padding:16px;cursor:pointer;transition:all 0.15s;box-shadow:0 1px 4px rgba(0,0,0,0.06);border:1px solid #e2e8f0;}
        .thema-card:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,0.1);}
        .thema-card.active{background:#eff6ff;border-color:#2563eb;}
        .thema-count{font-size:28px;font-weight:800;line-height:1;}
        .thema-naam{font-size:12px;color:#64748b;margin-top:4px;font-weight:500;}
        .charts-grid{display:grid;grid-template-columns:1.5fr 1fr;gap:20px;margin-bottom:28px;}
        .chart-box{background:white;border-radius:14px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,0.08);border:1px solid #e2e8f0;}
        .chart-filters{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px;}
        .filter-chip{font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;cursor:pointer;border:1.5px solid #e2e8f0;background:white;color:#64748b;transition:all 0.1s;}
        .artikels-box{background:white;border-radius:14px;padding:24px;box-shadow:0 1px 4px rgba(0,0,0,0.08);border:1px solid #e2e8f0;}
        .search-row{display:flex;gap:10px;margin-bottom:12px;}
        .search-row input{background:#f8fafc;border:1.5px solid #e2e8f0;border-radius:8px;padding:9px 14px;color:#1e293b;font-size:13px;flex:1;font-family:inherit;}
        .search-row input:focus{outline:none;border-color:#2563eb;}
        .btn-reset{background:#f1f5f9;color:#64748b;border:none;border-radius:8px;padding:9px 16px;font-size:12px;cursor:pointer;font-weight:600;font-family:inherit;}
        .bron-filter{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;}
        .active-filters{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;}
        .active-tag{font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;color:white;display:flex;align-items:center;gap:4px;}
        .artikel-rij{display:flex;align-items:flex-start;gap:10px;padding:10px 0;border-bottom:1px solid #f1f5f9;flex-wrap:wrap;}
        .artikel-rij:last-child{border-bottom:none;}
        .thema-badge{font-size:10px;font-weight:700;color:white;padding:2px 8px;border-radius:20px;white-space:nowrap;flex-shrink:0;margin-top:2px;}
        .artikel-titel{color:#1e293b;text-decoration:none;font-size:14px;flex:1;min-width:200px;font-weight:500;}
        .artikel-titel:hover{color:#2563eb;}
        .artikel-meta{font-size:11px;color:#94a3b8;white-space:nowrap;flex-shrink:0;margin-top:2px;}
        @media(max-width:768px){.charts-grid{grid-template-columns:1fr;}.container{padding:16px;}}
    </style>
</head>
<body>
<header>
    <div class="header-inner">
        <div>
            <h1>Dendermonde <span>Nieuws</span></h1>
            <div style="color:#bfdbfe;font-size:13px;margin-top:3px;font-weight:500;">Lokaal nieuwsoverzicht</div>
        </div>
        <div class="update-info">Laatste update<br><strong>""")
    html_parts.append(nu)
    html_parts.append("""</strong></div>
    </div>
</header>
<div class="container">
    <div class="stats-row">
        <div class="stat-box"><div class="stat-num">""")
    html_parts.append(str(totaal))
    html_parts.append("""</div><div class="stat-label">Totaal artikels</div></div>
        <div class="stat-box"><div class="stat-num">""")
    html_parts.append(str(len(thema_30d)))
    html_parts.append("""</div><div class="stat-label">Themas (30d)</div></div>
        <div class="stat-box"><div class="stat-num">""")
    html_parts.append(str(len(bron_30d)))
    html_parts.append("""</div><div class="stat-label">Bronnen</div></div>
    </div>
    <div class="section-title">Themas (laatste 30 dagen) &mdash; klik om te filteren</div>
    <div class="thema-grid">""")
    html_parts.append(thema_cards)
    html_parts.append("""</div>
    <div class="charts-grid">
        <div class="chart-box">
            <div class="section-title">Artikels per week (laatste 5 weken)</div>
            <div class="chart-filters" id="weekFilters"></div>
            <canvas id="weekChart"></canvas>
        </div>
        <div class="chart-box">
            <div class="section-title">Verdeling per bron (30d)</div>
            <canvas id="bronChart"></canvas>
        </div>
    </div>
    <div class="artikels-box">
        <div class="section-title" style="margin-bottom:10px;">Recente artikels</div>
        <div class="bron-filter" id="bronFilter"></div>
        <div class="search-row">
            <input type="text" id="zoek" placeholder="Zoek in titels..." oninput="filterArtikels()">
            <button class="btn-reset" onclick="resetFilters()">Reset filters</button>
        </div>
        <div class="active-filters" id="activeFilters"></div>
        <div id="artikels-lijst">""")
    html_parts.append(artikel_rijen)
    html_parts.append("""</div>
    </div>
</div>
<script>
const WEEK_DATA = """)
    html_parts.append(week_data_json)
    html_parts.append(""";
const THEMA_KLEUREN = """)
    html_parts.append(thema_kleuren_json)
    html_parts.append(""";
const ALLE_BRONNEN = """)
    html_parts.append(alle_bronnen)
    html_parts.append(""";
let actieveThemas = new Set();
let actieveBronnen = new Set();
let weekFilter = null;

const bronFilterEl = document.getElementById('bronFilter');
ALLE_BRONNEN.forEach(bron => {
    const chip = document.createElement('span');
    chip.className = 'filter-chip';
    chip.textContent = bron;
    chip.id = 'bron_' + bron.replace(/[^a-zA-Z0-9]/g,'_');
    chip.onclick = () => toggleFilter('bron', bron);
    bronFilterEl.appendChild(chip);
});

const weekFiltersEl = document.getElementById('weekFilters');
[['Totaal', null], ...ALLE_BRONNEN.map(b => [b, b])].forEach(([label, val]) => {
    const chip = document.createElement('span');
    chip.className = 'filter-chip' + (val === null ? ' active' : '');
    chip.textContent = label;
    chip.id = 'wf_' + (val || 'totaal').replace(/[^a-zA-Z0-9]/g,'_');
    if (val === null) { chip.style.background='#2563eb'; chip.style.color='white'; chip.style.borderColor='#2563eb'; }
    chip.onclick = () => setWeekFilter(val);
    weekFiltersEl.appendChild(chip);
});

const weken = Object.keys(WEEK_DATA);
const weekChart = new Chart(document.getElementById('weekChart'), {
    type: 'bar',
    data: { labels: weken, datasets: [{ label: 'Artikels', data: weken.map(w => WEEK_DATA[w].totaal), backgroundColor: '#3b82f6', borderRadius: 5 }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { x: { ticks: { color: '#94a3b8', font: { size: 11 } }, grid: { color: '#f1f5f9' } }, y: { ticks: { color: '#94a3b8', font: { size: 11 } }, grid: { color: '#f1f5f9' }, beginAtZero: true } } }
});

new Chart(document.getElementById('bronChart'), {
    type: 'doughnut',
    data: { labels: """)
    html_parts.append(bron_labels)
    html_parts.append(""", datasets: [{ data: """)
    html_parts.append(bron_values)
    html_parts.append(""", backgroundColor: ['#3b82f6','#22c55e','#f59e0b','#ef4444'], borderWidth: 2, borderColor: 'white' }] },
    options: { responsive: true, plugins: { legend: { position: 'bottom', labels: { color: '#64748b', font: { size: 11 }, boxWidth: 12, padding: 12 } } } }
});

function setWeekFilter(filter) {
    weekFilter = filter;
    document.querySelectorAll('#weekFilters .filter-chip').forEach(c => { c.style.background='white'; c.style.color='#64748b'; c.style.borderColor='#e2e8f0'; });
    const id = 'wf_' + (filter || 'totaal').replace(/[^a-zA-Z0-9]/g,'_');
    const el = document.getElementById(id);
    if (el) { el.style.background='#2563eb'; el.style.color='white'; el.style.borderColor='#2563eb'; }
    weekChart.data.datasets[0].data = weken.map(w => filter ? (WEEK_DATA[w].bronnen[filter] || 0) : WEEK_DATA[w].totaal);
    weekChart.update();
}

function toggleFilter(type, value) {
    const set = type === 'thema' ? actieveThemas : actieveBronnen;
    const kleur = type === 'thema' ? (THEMA_KLEUREN[value] || '#2563eb') : '#475569';
    const elId = type === 'bron' ? 'bron_' + value.replace(/[^a-zA-Z0-9]/g,'_') : null;
    const cardEl = type === 'thema' ? document.querySelector('.thema-card[data-thema="' + value + '"]') : null;
    const chipEl = elId ? document.getElementById(elId) : null;
    if (set.has(value)) {
        set.delete(value);
        if (cardEl) cardEl.classList.remove('active');
        if (chipEl) { chipEl.style.background='white'; chipEl.style.color='#64748b'; chipEl.style.borderColor='#e2e8f0'; }
    } else {
        set.add(value);
        if (cardEl) cardEl.classList.add('active');
        if (chipEl) { chipEl.style.background=kleur; chipEl.style.color='white'; chipEl.style.borderColor=kleur; }
    }
    updateActiveTags();
    filterArtikels();
}

function updateActiveTags() {
    const el = document.getElementById('activeFilters');
    el.innerHTML = '';
    actieveThemas.forEach(t => { const k=THEMA_KLEUREN[t]||'#2563eb'; el.innerHTML += '<span class="active-tag" style="background:'+k+'">'+t+' <span onclick="toggleFilter(\'thema\',\''+t+'\')" style="cursor:pointer">x</span></span>'; });
    actieveBronnen.forEach(b => { el.innerHTML += '<span class="active-tag" style="background:#475569">'+b+' <span onclick="toggleFilter(\'bron\',\''+b+'\')" style="cursor:pointer">x</span></span>'; });
}

function filterArtikels() {
    const zoek = document.getElementById('zoek').value.toLowerCase();
    document.querySelectorAll('.artikel-rij').forEach(rij => {
        const ok = (!zoek || rij.querySelector('.artikel-titel').textContent.toLowerCase().includes(zoek))
            && (actieveThemas.size === 0 || actieveThemas.has(rij.dataset.thema))
            && (actieveBronnen.size === 0 || actieveBronnen.has(rij.dataset.bron));
        rij.style.display = ok ? '' : 'none';
    });
}

function resetFilters() {
    actieveThemas.clear(); actieveBronnen.clear();
    document.getElementById('zoek').value = '';
    document.querySelectorAll('.thema-card').forEach(c => c.classList.remove('active'));
    document.querySelectorAll('.bron-filter .filter-chip').forEach(c => { c.style.background='white'; c.style.color='#64748b'; c.style.borderColor='#e2e8f0'; });
    document.getElementById('activeFilters').innerHTML = '';
    document.querySelectorAll('.artikel-rij').forEach(r => r.style.display = '');
    setWeekFilter(null);
}
</script>
</body>
</html>""")

    html = ''.join(html_parts)
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("docs/index.html gegenereerd")


if __name__ == "__main__":
    build_dashboard()
