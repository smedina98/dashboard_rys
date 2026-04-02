# =======================
# dashboard_rys.py
# =======================

import sys
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import html
import json

# -------------------------------------------------
#  REGEX PARA TU FORMATO REAL DE WHATSAPP
# -------------------------------------------------

MESSAGE_REGEX = re.compile(
    r'^(\d{1,2}/\d{1,2}/\d{2,4})\s+'
    r'(\d{1,2}:\d{2})\s*'
    r'([ap]\.?[\s\u202f]*m\.?)\s+-\s+'
    r'([^:]+):\s+(.*)$',
    re.IGNORECASE
)

# -------------------------------------------------
# PARSEADOR DEL CHAT
# -------------------------------------------------

def parse_chat(file_path):
    messages = []
    current = None

    with open(file_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")

            m = MESSAGE_REGEX.match(line)
            if m:
                if current:
                    messages.append(current)

                date_str, time_str, ampm, author, text = m.groups()
                dt_str = f"{date_str} {time_str} {ampm}"

                try:
                    dt = date_parser.parse(dt_str, dayfirst=True)
                except:
                    dt = None

                current = {
                    "datetime": dt,
                    "author": author.strip(),
                    "text": text.strip()
                }

            else:
                if current:
                    current["text"] += "\n" + line

    if current:
        messages.append(current)

    return messages

# -------------------------------------------------
# MÉTRICAS BÁSICAS
# -------------------------------------------------

def basic_stats(messages):
    total = len(messages)
    by_author = Counter(m["author"] for m in messages)

    by_day = Counter()
    by_month_author = defaultdict(lambda: Counter())
    by_hour = Counter()
    by_weekday = Counter()

    for m in messages:
        dt = m["datetime"]
        if dt is None:
            continue

        by_day[dt.date()] += 1

        month_key = dt.strftime("%Y-%m")
        by_month_author[month_key][m["author"]] += 1

        by_hour[dt.hour] += 1
        by_weekday[dt.weekday()] += 1

    dated = [m for m in messages if m["datetime"] is not None]
    dated_sorted = sorted(dated, key=lambda x: x["datetime"]) if dated else []

    first_dt = dated_sorted[0]["datetime"] if dated_sorted else None
    last_dt = dated_sorted[-1]["datetime"] if dated_sorted else None

    top_day, top_day_count = (None, 0)
    if by_day:
        top_day, top_day_count = max(by_day.items(), key=lambda x: x[1])

    weekday_names = ["Lunes", "Martes", "Miércoles",
                     "Jueves", "Viernes", "Sábado", "Domingo"]

    if by_weekday:
        wd_idx, wd_count = max(by_weekday.items(), key=lambda x: x[1])
        top_weekday = (weekday_names[wd_idx], wd_count)
    else:
        top_weekday = ("N/A", 0)

    return {
        "total_messages": total,
        "by_author": by_author,
        "by_day": by_day,
        "by_month_author": by_month_author,
        "by_hour": by_hour,
        "first_dt": first_dt,
        "last_dt": last_dt,
        "top_day": top_day,
        "top_day_count": top_day_count,
        "top_weekday": top_weekday
    }

# -------------------------------------------------
# DETECCIÓN DE MULTIMEDIA
# -------------------------------------------------

def media_stats(messages):

    audio_ext = (".opus", ".ogg", ".m4a")
    photo_ext = (".jpg", ".jpeg", ".png", ".gif")
    video_ext = (".mp4", ".mov")

    counts = {
        "audio_total": 0,
        "photo_total": 0,
        "video_total": 0,
        "other_total": 0,
        "audio_by_author": Counter(),
        "photo_by_author": Counter(),
        "video_by_author": Counter(),
        "other_by_author": Counter()
    }

    for m in messages:
        text = m["text"].lower()
        author = m["author"]

        if "mensaje de voz" in text:
            counts["audio_total"] += 1
            counts["audio_by_author"][author] += 1
            continue

        if "<multimedia omitido>" in text:
            counts["other_total"] += 1
            counts["other_by_author"][author] += 1
            continue

        match = re.search(r"([a-z0-9_\-]+\.[a-z0-9]+)", text)
        if match:
            filename = match.group(1)

            if filename.endswith(audio_ext):
                counts["audio_total"] += 1
                counts["audio_by_author"][author] += 1
            elif filename.endswith(photo_ext):
                counts["photo_total"] += 1
                counts["photo_by_author"][author] += 1
            elif filename.endswith(video_ext):
                counts["video_total"] += 1
                counts["video_by_author"][author] += 1
            else:
                counts["other_total"] += 1
                counts["other_by_author"][author] += 1

    return counts

# -------------------------------------------------
# MÉTRICAS ROMÁNTICAS
# -------------------------------------------------

def love_stats(messages):
    love_phrases = [
        "te quiero",
        "te amo",
        "te adoro",
        "te extraño",
        "mi amor",
        "amor",
    ]

    love_emojis = [
        "❤️","💜","💙","💚","💛","🧡",
        "😍","😘","🥺","💖","💕","💞","💘"
    ]

    overall = Counter()
    by_author_phrases = defaultdict(lambda: Counter())
    teq_by_author = Counter()
    first_love_message = None

    for m in messages:
        txt = m["text"]
        low = txt.lower()
        author = m["author"]
        dt = m["datetime"]

        for phrase in love_phrases:
            c = low.count(phrase)
            if c > 0:
                overall[phrase] += c
                by_author_phrases[author][phrase] += c

                if phrase == "te quiero":
                    teq_by_author[author] += c

                if dt and (first_love_message is None or dt < first_love_message["datetime"]):
                    if phrase in ("te quiero","te amo"):
                        first_love_message = {
                            "datetime": dt,
                            "author": author,
                            "phrase": phrase,
                            "text": txt
                        }

        for emo in love_emojis:
            c = txt.count(emo)
            if c > 0:
                overall[emo] += c
                by_author_phrases[author][emo] += c

    return overall, by_author_phrases, teq_by_author, first_love_message

# -------------------------------------------------
# MADRUGADA
# -------------------------------------------------

def night_messages(messages):
    c = 0
    for m in messages:
        dt = m["datetime"]
        if dt and 0 <= dt.hour < 6:
            c += 1
    return c

# -------------------------------------------------
# NUBE DE PALABRAS
# -------------------------------------------------

def top_words(messages, top_n=50):
    stopwords = set([
        "de","la","que","el","en","y","a","los","se","del","las",
        "un","por","con","no","una","su","para","es","al","lo","como",
        "más","o","pero","sus","le","ya","si","sí","porque","esta",
        "entre","cuando","muy","sin","sobre","también","me","te","yo",
        "tu","tú","mi","mis","ti","ni","son","era","fue","este","esta",
        "ese","esa","eso","eh","ah","pues","hay","jaja","jajaja","jeje",
        "jajajaja","aja","mmm","que","el","la","es","un","una","de",
        "ya","bien","más","muy","pero","entonces","solo","solo","aqui",
        "aquí","allá","alli","allí","adjunto","ptt","archivo","img","stk",
        "mensaje","webp","opus","está","qué"
    ])

    wc = Counter()

    for m in messages:
        text = m["text"].lower()

        text = re.sub(r"\b\d+\b", " ", text)
        text = re.sub(r"\w*\d\w*", " ", text)
        text = re.sub(r"[^\wáéíóúñü]+", " ", text)

        for w in text.split():
            if len(w) <= 2: continue
            if w in stopwords: continue
            if w.isdigit(): continue
            wc[w] += 1

    return wc.most_common(top_n)

# -------------------------------------------------
# RACHA
# -------------------------------------------------

def longest_streak(by_day):
    if not by_day:
        return 0, None, None

    days = sorted(by_day.keys())
    best = cur = 1
    start = days[0]
    cur_start = days[0]
    best_start = days[0]
    best_end = days[0]

    for prev, curr in zip(days, days[1:]):
        if curr == prev + timedelta(days=1):
            cur += 1
        else:
            if cur > best:
                best = cur
                best_start = cur_start
                best_end = prev
            cur = 1
            cur_start = curr

    if cur > best:
        best = cur
        best_start = cur_start
        best_end = days[-1]

    return best, best_start, best_end

# -------------------------------------------------
# TIEMPOS DE RESPUESTA
# -------------------------------------------------

def response_stats(messages):
    msgs = [m for m in messages if m["datetime"]]
    msgs.sort(key=lambda x: x["datetime"])

    sums = defaultdict(int)
    counts = defaultdict(int)

    prev = None
    for m in msgs:
        if prev and prev["author"] != m["author"]:
            delta = (m["datetime"] - prev["datetime"]).total_seconds()
            if 0 < delta < 86400:
                sums[(m["author"], prev["author"])] += delta
                counts[(m["author"], prev["author"])] += 1
        prev = m

    avg = {}
    for k in sums:
        avg[k] = sums[k] / counts[k]

    return avg

# -------------------------------------------------
# HTML MODERNO Y RESPONSIVE
# -------------------------------------------------

def generate_html(output_path, stats, media, love_overall, love_by_author,
                  teq_by_author, first_love_message, night_total,
                  top_words_list, streak_info, resp_stats, participants):

    participants = list(participants)
    participants.sort(key=lambda a: stats["by_author"][a], reverse=True)

    if len(participants) == 1:
        participants.append("Otra persona")

    author1, author2 = participants[0], participants[1]

    months_sorted = sorted(stats["by_month_author"].keys())
    data_author1 = [stats["by_month_author"][m].get(author1, 0) for m in months_sorted]
    data_author2 = [stats["by_month_author"][m].get(author2, 0) for m in months_sorted]

    labels_js = json.dumps(months_sorted, ensure_ascii=False)
    data_a1_js = json.dumps(data_author1)
    data_a2_js = json.dumps(data_author2)

    hours = list(range(24))
    hour_counts = [stats["by_hour"].get(h, 0) for h in hours]
    hours_js = json.dumps(hours)
    hour_counts_js = json.dumps(hour_counts)

    wordcloud_data = [{"word": w, "count": c} for w, c in top_words_list]
    wordcloud_js = json.dumps(wordcloud_data, ensure_ascii=False)

    love_html = ""
    for t, c in love_overall.most_common(12):
        love_html += f"<li><strong>{html.escape(str(t))}</strong>: {c}</li>"

    teq_html = ""
    for a, c in teq_by_author.items():
        teq_html += f"<li><strong>{html.escape(a)}</strong>: {c} ×</li>"

    streak_len, s_start, s_end = streak_info
    if streak_len <= 1 or not s_start:
        streak_text = "Sin rachas largas."
    else:
        streak_text = f"{streak_len} días seguidos ({s_start} → {s_end})"

    if first_love_message:
        fdt = first_love_message["datetime"].strftime("%d/%m/%Y %H:%M")
        fla = first_love_message["author"]
        phr = first_love_message["phrase"]
        tx = first_love_message["text"].replace("\n"," ")
        first_love_html = f"<strong>{html.escape(fla)}</strong> dijo <em>{phr}</em> el {fdt}<br><small>“{html.escape(tx)}”</small>"
    else:
        first_love_html = "Aún no aparece un mensaje de 'te quiero' o 'te amo'."

    resp_html = ""
    for (resp, orig), s in resp_stats.items():
        resp_html += f"<li><strong>{resp}</strong> responde a <strong>{orig}</strong> en {round(s/60,1)} min</li>"

    total = stats["total_messages"]
    messages_a1 = stats["by_author"][author1]
    messages_a2 = stats["by_author"][author2]

    audio_a1 = media["audio_by_author"][author1]
    audio_a2 = media["audio_by_author"][author2]

    first_dt_str = stats["first_dt"].strftime("%d/%m/%Y %H:%M") if stats["first_dt"] else "?"
    last_dt_str = stats["last_dt"].strftime("%d/%m/%Y %H:%M") if stats["last_dt"] else "?"
    top_day_str = stats["top_day"].strftime("%d/%m/%Y") if stats["top_day"] else "N/A"
    top_weekday_name, top_weekday_count = stats["top_weekday"]

    # -----------------------------------------
    # 🎨 HTML COMPLETO MODERNO Y RESPONSIVE
    # -----------------------------------------

    html_code = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Dashboard Rena y Sebas</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/d3-cloud/build/d3.layout.cloud.js"></script>

<style>
{open("style_full.txt","w").write("") if False else ""}

/* ----------- ESTILOS PREMIUM RESPONSIVE ----------- */

body {{
    font-family: "Inter", system-ui, sans-serif;
    background: linear-gradient(135deg, #ffd8e4, #dbe8ff);
    margin: 0;
    padding: 0;
    color: #1f2937;
}}

header {{
    text-align: center;
    padding: 3rem 1rem 1rem;
}}

header h1 {{
    margin: 0;
    font-size: 2.7rem;
    font-weight: 800;
    background: linear-gradient(to right, #e11d48, #9d1bb2);
    -webkit-background-clip: text;
    color: transparent;
}}

header p {{
    margin-top: .5rem;
    font-size: 1.1rem;
    opacity: .8;
}}

.container {{
    max-width: 1100px;
    margin: auto;
    padding: 1rem;
}}

.cards {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px,1fr));
    gap: 1.3rem;
    margin-bottom: 2.5rem;
}}

.card {{
    background: rgba(255,255,255,0.28);
    border-radius: 18px;
    padding: 1.4rem;
    backdrop-filter: blur(14px);
    border: 1px solid rgba(255,255,255,0.4);
    box-shadow: 0 10px 35px rgba(0,0,0,.12);
    transition: .25s;
}}
.card:hover {{
    transform: translateY(-4px) scale(1.02);
}}

.card h2 {{
    margin-top: 0;
    font-size: .9rem;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: #b91c1c;
}}

.big {{
    font-size: 2rem;
    font-weight: 800;
}}

.section-title {{
    font-size: 1.8rem;
    margin-top: 2rem;
}}

.section-subtitle {{
    font-size: 1rem;
    opacity: .8;
}}

canvas {{
    background: rgba(255,255,255,0.25);
    border-radius: 18px;
    padding: 1rem;
    margin-bottom: 2rem;
    backdrop-filter: blur(8px);
}}

#wordcloud {{
    background: linear-gradient(135deg,#ffe0ebbb,#eaf2ffcc);
    border-radius: 18px;
    padding: 1rem;
    backdrop-filter: blur(10px);
    margin-bottom: 3rem;
}}

@media(max-width: 600px){{
    header h1 {{ font-size: 2.1rem; }}
    .big {{ font-size: 1.6rem; }}
    .section-title {{ font-size: 1.5rem; }}
}}
</style>
</head>

<body>

<header>
    <h1>Dashboard Rena y Sebas</h1>
    <p>Una radiografía hermosa del chat que están construyendo juntos ❤</p>
</header>

<div class="container">

<section class="cards">
    <div class="card"><h2>Total de mensajes</h2><div class="big">{total}</div></div>
    <div class="card"><h2>Mensajes de {author1}</h2><div class="big">{messages_a1}</div></div>
    <div class="card"><h2>Mensajes de {author2}</h2><div class="big">{messages_a2}</div></div>
    <div class="card"><h2>Desde cuándo</h2><div class="big">{first_dt_str}</div></div>
    <div class="card"><h2>Último mensaje</h2><div class="big">{last_dt_str}</div></div>
    <div class="card"><h2>Día más intenso</h2><div class="big">{top_day_str}</div></div>
    <div class="card"><h2>Día de la semana top</h2><div class="big">{top_weekday_name} ({top_weekday_count})</div></div>
    <div class="card"><h2>Racha</h2><div class="big">{streak_text}</div></div>
    <div class="card"><h2>Audios</h2><div class="big">{media["audio_total"]}</div></div>
    <div class="card"><h2>Fotos</h2><div class="big">{media["photo_total"]}</div></div>
    <div class="card"><h2>Videos</h2><div class="big">{media["video_total"]}</div></div>
    <div class="card"><h2>Noches despiertos</h2><div class="big">{night_total}</div></div>
</section>

<h2 class="section-title">Mensajes por mes</h2>
<p class="section-subtitle">Cómo evoluciona su comunicación</p>
<canvas id="mensajesMesChart"></canvas>

<h2 class="section-title">Mensajes por hora</h2>
<p class="section-subtitle">Patrones diarios</p>
<canvas id="mensajesHoraChart"></canvas>

<h2 class="section-title">Amorómetro</h2>
<ul>{love_html}</ul>

<h2 class="section-title">“Te quiero” por persona</h2>
<ul>{teq_html}</ul>

<h2 class="section-title">Primer mensaje de amor</h2>
<p>{first_love_html}</p>

<h2 class="section-title">Tiempo de respuesta</h2>
<ul>{resp_html}</ul>

<h2 class="section-title">Nube de palabras</h2>
<div id="wordcloud"></div>

</div>

<script>
// Charts
new Chart(document.getElementById('mensajesMesChart'), {{
    type: 'line',
    data: {{
        labels: {labels_js},
        datasets: [
            {{ label: "{author1}", data: {data_a1_js}, borderWidth: 2, tension: .3 }},
            {{ label: "{author2}", data: {data_a2_js}, borderWidth: 2, tension: .3 }}
        ]
    }}
}};

new Chart(document.getElementById('mensajesHoraChart'), {{
    type: 'bar',
    data: {{
        labels: {hours_js}.map(h => h + ":00"),
        datasets: [{{ data: {hour_counts_js}, borderWidth: 1 }}]
    }}
}});

// Wordcloud
const wcData = {wordcloud_js};
(function(){{
    const el = document.getElementById("wordcloud");
    const w = el.clientWidth;
    const h = 400;

    if(!wcData.length) return;

    const max = Math.max(...wcData.map(x=>x.count));

    const layout = d3.layout.cloud()
    .size([w,h])
    .words(wcData.map(d => ({{
        text: d.word,
        size: 14 + (d.count/max)*30,
        count: d.count
    }})))
    .padding(4)
    .rotate(() => 0)
    .font("Inter")
    .fontSize(d => d.size)
    .on("end", draw)
    .start();

    function draw(words){{
        const svg = d3.select("#wordcloud").append("svg")
            .attr("width", w)
            .attr("height", h);

        const g = svg.append("g")
            .attr("transform", `translate(${w/2},${h/2})`);

        g.selectAll("text")
        .data(words)
        .enter()
        .append("text")
        .style("font-size", d => d.size+"px")
        .style("font-weight","600")
        .style("fill", d => {{
            const k = d.count/max;
            return d3.interpolateRgb("#ffbcd0","#d61b53")(k);
        }})
        .attr("text-anchor","middle")
        .attr("transform", d => `translate(${d.x},${d.y})`)
        .text(d => d.text);
    }}
}})();
</script>

</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_code)

# -------------------------------------------------
# MAIN
# -------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Uso: python dashboard_rys.py chat.txt")
        sys.exit(1)

    chat_file = sys.argv[1]

    if not os.path.exists(chat_file):
        print("Archivo no encontrado:", chat_file)
        sys.exit(1)

    messages = parse_chat(chat_file)
    print("Mensajes cargados:", len(messages))

    stats = basic_stats(messages)
    media = media_stats(messages)
    love_overall, love_by_author, teq_by_author, first_love_message = love_stats(messages)
    night_total = night_messages(messages)
    top_words_list = top_words(messages)
    streak_info = longest_streak(stats["by_day"])
    resp_stats = response_stats(messages)
    participants = stats["by_author"].keys()

    output_html = "dashboard_rys.html"
    generate_html(
        output_html, stats, media, love_overall, love_by_author,
        teq_by_author, first_love_message, night_total,
        top_words_list, streak_info, resp_stats, participants
    )

    print("Dashboard generado:", output_html)
    print("Ábrelo en tu navegador")

if __name__ == "__main__":
    main()
