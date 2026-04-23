"""
Dendermonde Nieuws - Wekelijkse Mail Agent
Genereert een AI-synthese en verstuurt een professionele HTML mail.
"""

import sqlite3
import anthropic
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from collections import Counter

DB_PATH = "nieuws.db"

THEMA_KLEUREN = {
    "mobiliteit": "#2563eb", "veiligheid": "#dc2626", "politiek": "#7c3aed",
    "cultuur": "#d97706", "sport": "#16a34a", "natuur": "#0891b2",
    "economie": "#9333ea", "algemeen": "#6b7280"
}


def get_week_data():
    conn = sqlite3.connect(DB_PATH)
    artikels = conn.execute("""
        SELECT titel, url, bron_naam, datum, thema FROM artikels
        WHERE toegevoegd >= date('now', '-7 days') ORDER BY toegevoegd DESC
    """).fetchall()
    vorige_week = conn.execute("""
        SELECT thema, COUNT(*) as aantal FROM artikels
        WHERE toegevoegd >= date('now', '-14 days') AND toegevoegd < date('now', '-7 days')
        GROUP BY thema
    """).fetchall()
    conn.close()
    thema_counts = Counter(a[4] for a in artikels)
    vorige_counts = {r[0]: r[1] for r in vorige_week}
    return artikels, thema_counts, vorige_counts


def generate_synthesis(artikels, thema_counts, vorige_counts):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    titels_text = "\n".join([f"- [{a[4]}] {a[0]} ({a[2]})" for a in artikels[:30]])
    thema_vergelijking = []
    for thema, count in thema_counts.most_common():
        vorig = vorige_counts.get(thema, 0)
        delta = count - vorig
        trend = f"+{delta}" if delta > 0 else str(delta)
        thema_vergelijking.append(f"{thema}: {count} artikels (vorige week: {vorig}, {trend})")

    prompt = f"""Je bent een lokale nieuwsredacteur voor de regio Dendermonde.
Schrijf een wekelijkse nieuwssynthese op basis van de krantenkoppen van afgelopen week.

KRANTENKOPPEN:
{titels_text}

THEMA STATISTIEKEN:
{"\n".join(thema_vergelijking)}

Schrijf een synthese van 150-200 woorden in het Nederlands die:
1. Start met de 1-2 meest opvallende themas of verhalen
2. Vergelijkt met vorige week waar relevant
3. Eindigt met een korte observatie

Schrijf in lopende tekst in 2-3 alineas, geen opsomming."""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def build_html_email(synthese, artikels, thema_counts, vorige_counts):
    week_nr = datetime.now().strftime("%V")
    datum_str = datetime.now().strftime("%d %B %Y")
    totaal = len(artikels)

    thema_html = ""
    for thema, count in thema_counts.most_common(6):
        kleur = THEMA_KLEUREN.get(thema, "#6b7280")
        vorig = vorige_counts.get(thema, 0)
        trend = " ↑" if count > vorig > 0 else (" ↓" if count < vorig else "")
        thema_html += f'<span style="display:inline-block;background:{kleur};color:white;padding:4px 12px;border-radius:20px;font-size:13px;margin:4px;font-weight:600;">{thema.capitalize()} {count}{trend}</span>'

    thema_artikels = {}
    for a in artikels:
        t = a[4]
        if t not in thema_artikels:
            thema_artikels[t] = []
        if len(thema_artikels[t]) < 4:
            thema_artikels[t].append(a)

    artikels_html = ""
    for thema, items in sorted(thema_artikels.items(), key=lambda x: -thema_counts[x[0]]):
        kleur = THEMA_KLEUREN.get(thema, "#6b7280")
        artikels_html += f'<div style="margin-bottom:24px;"><h3 style="color:{kleur};font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin:0 0 12px 0;padding-bottom:6px;border-bottom:2px solid {kleur};">{thema.capitalize()}</h3>'
        for a in items:
            titel, url, bron, datum, _ = a
            artikels_html += f'<div style="margin-bottom:10px;padding:10px 12px;background:#f9fafb;border-radius:6px;border-left:3px solid {kleur};"><a href="{url}" style="color:#111827;text-decoration:none;font-size:14px;font-weight:500;line-height:1.4;">{titel}</a><div style="color:#9ca3af;font-size:12px;margin-top:4px;">{bron}</div></div>'
        artikels_html += "</div>"

    synthese_html = synthese.replace("\n\n", "</p><p style='margin:0 0 12px 0;'>")

    return f"""<!DOCTYPE html>
<html lang="nl">
<head><meta charset="UTF-8"><title>Dendermonde Nieuws - Week {week_nr}</title></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Georgia,serif;">
<div style="background:#1e3a5f;padding:32px 24px;text-align:center;">
  <div style="font-size:11px;color:#93c5fd;letter-spacing:3px;text-transform:uppercase;margin-bottom:8px;">Weekoverzicht</div>
  <h1 style="color:white;margin:0;font-size:28px;font-weight:700;">Dendermonde Nieuws</h1>
  <div style="color:#93c5fd;margin-top:8px;font-size:14px;">Week {week_nr} &middot; {datum_str}</div>
</div>
<div style="max-width:600px;margin:0 auto;padding:24px 16px;">
  <div style="display:flex;gap:12px;margin-bottom:24px;">
    <div style="flex:1;background:white;border-radius:8px;padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
      <div style="font-size:32px;font-weight:700;color:#1e3a5f;">{totaal}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:4px;">artikels</div>
    </div>
    <div style="flex:1;background:white;border-radius:8px;padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
      <div style="font-size:32px;font-weight:700;color:#1e3a5f;">{len(thema_counts)}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:4px;">themas</div>
    </div>
  </div>
  <div style="background:white;border-radius:8px;padding:20px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
    <h2 style="font-size:13px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:1px;margin:0 0 12px 0;">Themas deze week</h2>
    {thema_html}
  </div>
  <div style="background:#1e3a5f;border-radius:8px;padding:24px;margin-bottom:24px;">
    <div style="font-size:11px;color:#93c5fd;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;">Weekanalyse</div>
    <div style="color:white;font-size:15px;line-height:1.7;"><p style="margin:0 0 12px 0;">{synthese_html}</p></div>
  </div>
  <div style="background:white;border-radius:8px;padding:20px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
    <h2 style="font-size:13px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:1px;margin:0 0 20px 0;">Artikels per thema</h2>
    {artikels_html}
  </div>
  <div style="text-align:center;padding:16px;color:#9ca3af;font-size:12px;">
    Dendermonde Nieuws &middot; Week {week_nr}<br>
    Bronnen: VRT NWS, Dender Journaal, Stad Dendermonde, HLN
  </div>
</div>
</body>
</html>"""


def send_email(html_content, week_nr):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Dendermonde Nieuws - Week {week_nr}"
    msg["From"] = os.environ["SENDGRID_FROM_EMAIL"]
    msg["To"] = os.environ["SENDGRID_TO_EMAIL"]
    msg.attach(MIMEText(html_content, "html"))
    with smtplib.SMTP("smtp.sendgrid.net", 587) as server:
        server.ehlo()
        server.starttls()
        server.login("apikey", os.environ["SENDGRID_API_KEY"])
        server.send_message(msg)
    print("Mail verstuurd!")


def run():
    print(f"\n=== Wekelijkse Mail - {datetime.now().strftime('%Y-%m-%d')} ===\n")
    artikels, thema_counts, vorige_counts = get_week_data()
    if not artikels:
        print("Geen artikels gevonden. Mail wordt niet verstuurd.")
        return
    print(f"{len(artikels)} artikels gevonden")
    synthese = generate_synthesis(artikels, thema_counts, vorige_counts)
    html = build_html_email(synthese, artikels, thema_counts, vorige_counts)
    week_nr = datetime.now().strftime("%V")
    send_email(html, week_nr)
    print("Klaar!")


if __name__ == "__main__":
    run()
