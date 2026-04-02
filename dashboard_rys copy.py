# =======================
# dashboard_rys.py
# =======================

from pyexpat.errors import messages
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
#  Ejemplo:
#  2/10/25 8:56 p. m. - Nombre: Mensaje
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
                # guardar el anterior
                if current:
                    messages.append(current)

                date_str, time_str, ampm, author, text = m.groups()
                dt_str = f"{date_str} {time_str} {ampm}"

                try:
                    dt = date_parser.parse(dt_str, dayfirst=True)
                except Exception:
                    dt = None

                current = {
                    "datetime": dt,
                    "author": author.strip(),
                    "text": text.strip()
                }

            else:
                # multilínea continua
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
        by_weekday[dt.weekday()] += 1  # 0=lunes

    dated = [m for m in messages if m["datetime"] is not None]
    dated_sorted = sorted(dated, key=lambda x: x["datetime"]) if dated else []

    first_dt = dated_sorted[0]["datetime"] if dated_sorted else None
    last_dt = dated_sorted[-1]["datetime"] if dated_sorted else None

    top_day, top_day_count = (None, 0)
    if by_day:
        top_day, top_day_count = max(by_day.items(), key=lambda x: x[1])

    # día de la semana más activo
    weekday_names = ["Lunes", "Martes", "Miércoles",
                     "Jueves", "Viernes", "Sábado", "Domingo"]
    top_weekday = None
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
        "top_weekday": top_weekday,
    }

# -------------------------------------------------
# MÉTRICAS DE MULTIMEDIA: AUDIOS, FOTOS, VIDEOS
# -------------------------------------------------

def media_stats(messages):
    """
    Detecta archivos multimedia:
    - Audios: .opus, .ogg, .m4a
    - Fotos: .jpg, .jpeg, .png, .gif
    - Videos: .mp4, .mov
    Además cuenta "<Multimedia omitido>" como genérico
    """
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

        # mensajes tipo "<Se omitió el mensaje de voz ...>"
        if "mensaje de voz" in text:
            counts["audio_total"] += 1
            counts["audio_by_author"][author] += 1
            continue

        # "<Multimedia omitido>" sin más
        if "<multimedia omitido>" in text:
            counts["other_total"] += 1
            counts["other_by_author"][author] += 1
            continue

        # nombres de archivo tipo PTT-..., IMG-..., VID-...
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
        "te extraño","le extraño",
        "mi amor",
        "amor",  "le quiero", "Amor mío","le amo"
    ]

    love_emojis = [
        "❤️", "💜", "💙", "💚", "💛", "🧡",
        "😍", "😘", "🥺", "💖", "💕", "💞", "💘"
    ]

    overall = Counter()
    by_author_phrases = defaultdict(lambda: Counter())
    te_quiero_by_author = Counter()
    first_love_message = None  # primer te quiero / te amo
    first_te_amo = None
    te_amo_by_author = Counter()

    for m in messages:
        txt = m["text"]
        low = txt.lower()
        author = m["author"]
        dt = m["datetime"]

        # frases
        for phrase in love_phrases:
            count = low.count(phrase)
            if count > 0:
                overall[phrase] += count
                by_author_phrases[author][phrase] += count

                if phrase in ("te quiero", "le quiero"):
                    te_quiero_by_author[author] += low.count("te quiero")
                    te_quiero_by_author[author] += low.count("le quiero")
                    # primer mensaje amoroso
                    if dt is not None:
                        if first_love_message is None or dt < first_love_message["datetime"]:
                            first_love_message = {
                                "datetime": dt,
                                "author": author,
                                "phrase": phrase,
                                "text": txt
                            }

                            # detectar primer "te amo"
                if phrase == "te amo":
                    if dt is not None:
                        if first_te_amo is None or dt < first_te_amo["datetime"]:
                            first_te_amo = {
                                "datetime": dt,
                                "author": author,
                                "phrase": phrase,
                                "text": txt
                            }

                if phrase in ("te amo", "le amo"):
                    te_amo_by_author[author] += count



        # emojis
        for emo in love_emojis:
            count = txt.count(emo)
            if count > 0:
                overall[emo] += count
                by_author_phrases[author][emo] += count

    return overall, by_author_phrases, te_quiero_by_author, first_love_message, first_te_amo,te_amo_by_author

# -------------------------------------------------
# MENSAJES DE MADRUGADA
# -------------------------------------------------

def night_messages(messages):
    night_total = 0
    for m in messages:
        dt = m["datetime"]
        if dt is None:
            continue
        if 0 <= dt.hour < 6:
            night_total += 1
    return night_total

# -------------------------------------------------
# TOP PALABRAS (PARA LA NUBE)
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
        "aquí","allá","alli","allí","adjunto","ptt","0","1","2","3","4","5","6","7","8","9",
        "archivo","img","stk","jpg","mensaje","webp","opus","está","qué","jajajaj","jejeje","jejej","jajaj","sebas"
    ])

    word_counter = Counter()

    for m in messages:
        text = m["text"].lower()

        # 1) eliminar completamente números grandes y palabras con números
        text = re.sub(r"\b\d+\b", " ", text)        # elimina números puros (20251115)
        text = re.sub(r"\w*\d\w*", " ", text)       # elimina tokens con números (wa0012)

        # 2) quitar símbolos
        text = re.sub(r"[^\wáéíóúñü]+", " ", text)

        for w in text.split():
            # 3) filtros
            if len(w) <= 2:
                continue
            if w in stopwords:
                continue
            if w.isdigit():
                continue

            word_counter[w] += 1

    return word_counter.most_common(top_n)


# -------------------------------------------------
# RACHA DE DÍAS SEGUIDOS HABLANDO
# -------------------------------------------------

def longest_streak(by_day_counter):
    if not by_day_counter:
        return 0, None, None

    days = sorted(by_day_counter.keys())
    best_len = 1
    cur_len = 1
    best_start = days[0]
    best_end = days[0]
    cur_start = days[0]

    for prev, curr in zip(days, days[1:]):
        if curr == prev + timedelta(days=1):
            cur_len += 1
        else:
            if cur_len > best_len:
                best_len = cur_len
                best_start = cur_start
                best_end = prev
            cur_len = 1
            cur_start = curr
    # revisar al final
    if cur_len > best_len:
        best_len = cur_len
        best_start = cur_start
        best_end = days[-1]

    return best_len, best_start, best_end

def marathon_chats(messages):
    msgs = [m for m in messages if m["datetime"]]
    msgs.sort(key=lambda x: x["datetime"])

    marathons = 0
    window = []

    for m in msgs:
        window = [x for x in window if (m["datetime"] - x["datetime"]).total_seconds() <= 3600]
        window.append(m)

        if len(window) >= 20:
            marathons += 1
            window = []  # reiniciar

    return marathons


def late_evening(messages):
    total = 0
    for m in messages:
        dt = m["datetime"]
        if not dt:
            continue
        if dt.hour >= 22 or dt.hour < 2:
            total += 1
    return total


def love_emoji_total(love_overall):
    romantic_emojis = "❤️💜💙💚💛🧡😍😘🥺💖💕💞💘"
    total = 0
    for token, count in love_overall.items():
        if any(e in token for e in romantic_emojis):
            total += count
    return total

# -------------------------------------------------
# VELOCIDAD PROMEDIO DE RESPUESTA
# -------------------------------------------------

def response_stats(messages):
    """
    Calcula promedio de tiempo de respuesta entre participantes.
    Devuelve dict:
      {
        ('A','B'): promedio segundos que A se demora en responder a B
      }
    """
    dated = [m for m in messages if m["datetime"] is not None]
    dated_sorted = sorted(dated, key=lambda x: x["datetime"])
    authors = list({m["author"] for m in dated_sorted})

    if len(authors) < 2:
        return {}

    # pares (respondedor, original)
    sums = defaultdict(int)
    counts = defaultdict(int)

    prev = None
    for m in dated_sorted:
        if prev is not None:
            if m["author"] != prev["author"]:
                delta = (m["datetime"] - prev["datetime"]).total_seconds()
                if 0 < delta < 60 * 60 * 24:  # menos de 24h, si no ya no cuenta como "respuesta"
                    key = (m["author"], prev["author"])
                    sums[key] += delta
                    counts[key] += 1
        prev = m

    averages = {}
    for k in sums:
        averages[k] = sums[k] / counts[k]

    return averages

# -------------------------------------------------
# GENERACIÓN DEL HTML
# -------------------------------------------------

def generate_html(
    output_path,
    stats,
    media,
    love_overall,
    love_by_author,
    te_quiero_by_author,
    first_love_message,
    night_total,
    top_words_list,
    streak_info,
    resp_stats,
    participants,
    love_emojis_total,
    late_evening_total,
    te_amo_by_author,   # ← AGREGADO AQUÍ
    first_te_amo,       # ← Y ESTE DESPUÉS
    marathons_total
):

    participants = list(participants)
    # ordenar por cantidad de mensajes
    participants_sorted = sorted(
        participants,
        key=lambda a: stats["by_author"][a],
        reverse=True
    )
    if len(participants_sorted) == 1:
        participants_sorted.append("Otra persona")

    author1, author2 = participants_sorted[0], participants_sorted[1]

    # Datos para gráfico mensajes por mes
    months_sorted = sorted(stats["by_month_author"].keys())
    data_author1 = [stats["by_month_author"][m].get(author1, 0) for m in months_sorted]
    data_author2 = [stats["by_month_author"][m].get(author2, 0) for m in months_sorted]

    labels_js = json.dumps(months_sorted, ensure_ascii=False)
    data_a1_js = json.dumps(data_author1)
    data_a2_js = json.dumps(data_author2)

    # Datos por hora (0-23)
    hours = list(range(24))
    hour_counts = [stats["by_hour"].get(h, 0) for h in hours]
    hours_js = json.dumps(hours)
    hour_counts_js = json.dumps(hour_counts)

    # Wordcloud data
    wordcloud_data = [{"word": w, "count": c} for w, c in top_words_list]
    wordcloud_js = json.dumps(wordcloud_data, ensure_ascii=False)

    # Amorómetro
    love_top = [item for item in love_overall.most_common(12) if item[1] > 0]
    love_list_html = ""
    if love_top:
        for token, count in love_top:
            love_list_html += f"<li><strong>{html.escape(str(token))}</strong>: {count} veces</li>\n"
    else:
        love_list_html = "<li>Su amor casi no se puede medir en palabras 😌</li>"

    # Te quiero por autor
    teq_list_html = ""
    if te_quiero_by_author:
        for auth, c in te_quiero_by_author.items():
            teq_list_html += f"<li><strong>{html.escape(auth)}</strong>: {c} × “te quiero”</li>\n"
    else:
        teq_list_html = "<li>Todavía no se han dicho “te quiero” por WhatsApp… pero igual se siente 😏</li>"

    # Te amo por persona
    tamo_list_html = ""
    if te_amo_by_author:
        for auth, c in te_amo_by_author.items():
            tamo_list_html += f"<li><strong>{html.escape(auth)}</strong>: {c} × “te amo”</li>\n"
    else:
        tamo_list_html = "<li>Todavía no se han dicho “te amo” por WhatsApp… pero seguro ya lo sienten 🥺</li>"

    # Racha
    streak_len, streak_start, streak_end = streak_info
    if streak_len <= 1 or not streak_start:
        streak_text = "Sin rachas largas (por ahora)."
    else:
        streak_text = f"{streak_len} días seguidos, de {streak_start.strftime('%d/%m/%Y')} a {streak_end.strftime('%d/%m/%Y')}."

    # Primer mensaje de amor
    if first_love_message:
        fla_date = first_love_message["datetime"].strftime("%d/%m/%Y %H:%M")
        fla_author = first_love_message["author"]
        fla_phrase = first_love_message["phrase"]
        fla_text = first_love_message["text"].replace("\n", " ")
        first_love_html = f"<strong>{html.escape(fla_author)}</strong> escribió <em>{html.escape(fla_phrase)}</em> el {fla_date}<br><small>“{html.escape(fla_text)}”</small>"
    else:
        first_love_html = "Aún no aparece un “te quiero” o “te amo” en el chat…"


        # Primer "te amo"
    if first_te_amo:
        fta_date = first_te_amo["datetime"].strftime("%d/%m/%Y %H:%M")
        fta_author = first_te_amo["author"]
        fta_phrase = first_te_amo["phrase"]
        fta_text = first_te_amo["text"].replace("\n", " ")
        first_tamo_html = (
            f"<strong>{html.escape(fta_author)}</strong> escribió "
            f"<em>{html.escape(fta_phrase)}</em> el {fta_date}<br>"
            f"<small>“{html.escape(fta_text)}”</small>"
        )
    else:
        first_tamo_html = "Aún no aparece un “te amo” en el chat…"


    # Respuesta promedio
    resp_html = ""
    if resp_stats:
        for (resp, orig), seconds in resp_stats.items():
            mins = round(seconds / 60, 1)
            resp_html += f"<li><strong>{html.escape(resp)}</strong> responde a <strong>{html.escape(orig)}</strong> en promedio en {mins} min.</li>"
    else:
        resp_html = "<li>No hay suficientes datos para calcular tiempos de respuesta.</li>"

    first_date_str = stats["first_dt"].strftime("%d/%m/%Y %H:%M") if stats["first_dt"] else "Desconocida"
    last_date_str = stats["last_dt"].strftime("%d/%m/%Y %H:%M") if stats["last_dt"] else "Desconocida"
    top_day_str = stats["top_day"].strftime("%d/%m/%Y") if stats["top_day"] else "N/A"
    top_weekday_name, top_weekday_count = stats["top_weekday"]

    total_messages = stats["total_messages"]
    messages_a1 = stats["by_author"].get(author1, 0)
    messages_a2 = stats["by_author"].get(author2, 0)

    audio_a1 = media["audio_by_author"].get(author1, 0)
    audio_a2 = media["audio_by_author"].get(author2, 0)

    # Plantilla HTML
    html_template = r"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Dashboard Rena y Sebas</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/d3-cloud/build/d3.layout.cloud.js"></script>
    <style>
        body {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: linear-gradient(135deg, #ffe6f0, #e0f0ff);
            margin: 0;
            padding: 0;
            color: #111827;
        }
        header {
            text-align: center;
            padding: 2rem 1rem 1rem 1rem;
        }
        header h1 {
            margin: 0;
            font-size: 2.4rem;
        }
        header p {
            margin: .5rem 0 0 0;
        }
        .container {
            max-width: 1100px;
            margin: 0 auto 3rem auto;
            padding: 0 1rem 2rem 1rem;
        }
        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .card {
            background: rgba(255,255,255,0.95);
            border-radius: 14px;
            padding: 1.2rem 1.5rem;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12);
        }
        .card h2 {
            margin-top: 0;
            font-size: .9rem;
            text-transform: uppercase;
            letter-spacing: .08em;
            color: #9b1c31;
        }
        .big {
            font-size: 2rem;
            font-weight: 700;
            margin: .4rem 0;
        }
        .card small {
            color: #6b7280;
        }
        .section-title {
            font-size: 1.4rem;
            margin: 2rem 0 0.5rem 0;
        }
        .section-subtitle {
            margin: 0 0 1rem 0;
            color: #4b5563;
        }
        .flex {
            display: flex;
            flex-wrap: wrap;
            gap: 2rem;
        }
        .flex > div {
            flex: 1 1 260px;
        }
        ul {
            margin: .5rem 0 0 1.2rem;
            padding: 0;
        }
        li {
            margin-bottom: 0.25rem;
        }
        footer {
            text-align: center;
            padding: 1.5rem 1rem;
            font-size: 0.8rem;
            color: #6b7280;
        }
        canvas {
            background: rgba(255,255,255,0.95);
            border-radius: 14px;
            padding: 1rem;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12);
            margin-bottom: 1.5rem;
        }


/* ========================= */
/*      SPLASH COMPLETO      */
/* ========================= */

#splash {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: white;
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 999999;      /* Asegura que quede encima de todo */
    opacity: 1;
    transition: opacity 0.6s ease;
}

/* Contenedor vertical para el corazón y el texto */
.splash-content {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}

/* ========================= */
/*       CORAZÓN SVG         */
/* ========================= */

#heart {
    width: 120px;
    height: 120px;
    background: linear-gradient(135deg, #ff7a8b, #d11a2a);
    position: relative;
    transform: rotate(-45deg);
    animation: heartbeat 1.1s infinite ease-in-out;
}

/* partes superiores del corazón */
#heart::before,
#heart::after {
    content: "";
    width: 120px;
    height: 120px;
    background: linear-gradient(135deg, #ff7a8b, #d11a2a);
    border-radius: 50%;
    position: absolute;
}

#heart::before {
    top: -60px;
    left: 0;
}

#heart::after {
    top: 0;
    left: 60px;
}

/* animación del latido */
@keyframes heartbeat {
    0%   { transform: rotate(-45deg) scale(1); }
    25%  { transform: rotate(-45deg) scale(1.15); }
    40%  { transform: rotate(-45deg) scale(1); }
    60%  { transform: rotate(-45deg) scale(1.12); }
    100% { transform: rotate(-45deg) scale(1); }
}

/* ========================= */
/*         TEXTO             */
/* ========================= */

#splash-text {
    margin-top: 22px;
    font-size: 1.8rem;
    font-weight: 700;
    color: #d11a2a; /* mismo rojo del corazón */
    opacity: 0;
    animation: fadeIn 1s ease-out forwards;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}



        #wordcloud {
            background: linear-gradient(135deg, #ffe6f0aa, #e3f2ffcc);
    backdrop-filter: blur(6px);
            border-radius: 14px;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.12);
            
        }
    </style>
    <link rel="icon" href="data:image/svg+xml,
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>
<text y='0.9em' font-size='90'>❤️</text>
</svg>">

</head>
<body>
       <div id="splash">
    <div class="splash-content">
        <div id="heart"></div>
        <div id="splash-text">Rena & Sebas</div>
    </div>
</div>


    <header>
     <h1>Rena & Sebas — Dashboard del Amor</h1>
     <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='0.9em' font-size='90'>❤️</text></svg>">
    <p>Una mirada dulce y curiosa a nuestra historia en WhatsApp.</p>
</header>


    <div class="container">
        <section class="cards">
            <div class="card">
                <h2>Total de mensajes</h2>
                <div class="big">__TOTAL_MESSAGES__</div>
                <small>Cada mensaje es un pedacito de la historia.</small>
            </div>
            <div class="card">
                <h2>Mensajes de __AUTHOR1__</h2>
                <div class="big">__COUNT_AUTHOR1__</div>
                <small>Hablar mucho también es una forma de cuidar.</small>
            </div>
            <div class="card">
                <h2>Mensajes de __AUTHOR2__</h2>
                <div class="big">__COUNT_AUTHOR2__</div>
                <small>Responder también es decir “estoy aquí”.</small>
            </div>
            <div class="card">
                <h2>Desde cuándo se escriben</h2>
                <div class="big" style="font-size:1.3rem;">__FIRST_DATE__</div>
                <small>El primer “hola” que empezó todo.</small>
            </div>
            <div class="card">
                <h2>Último mensaje</h2>
                <div class="big" style="font-size:1.3rem;">__LAST_DATE__</div>
                <small>La historia aún se está escribiendo.</small>
            </div>
            <div class="card">
                <h2>Día más intenso</h2>
                <div class="big" style="font-size:1.3rem;">__TOP_DAY__</div>
                <small>Ese día se mandaron __TOP_DAY_COUNT__ mensajes.</small>
            </div>
            <div class="card">
                <h2>Día de la semana más activo</h2>
                <div class="big" style="font-size:1.3rem;">__TOP_WEEKDAY_NAME__</div>
                <small>Con __TOP_WEEKDAY_COUNT__ mensajes en total.</small>
            </div>
            <div class="card">
                <h2>Racha más larga</h2>
                <div class="big" style="font-size:1.1rem;">__STREAK_TEXT__</div>
            </div>
            <div class="card">
                <h2>Audios en total</h2>
                <div class="big">__AUDIO_TOTAL__</div>
                <small>La voz también cuenta como “mensaje”.</small>
            </div>
            <div class="card">
                <h2>Audios por persona</h2>
                <div class="big" style="font-size:1.1rem;">
                    __AUTHOR1__: __AUDIO_A1__<br>
                    __AUTHOR2__: __AUDIO_A2__
                </div>
            </div>
            <div class="card">
                <h2>Fotos enviadas</h2>
                <div class="big">__PHOTO_TOTAL__</div>
            </div>
            <div class="card">
                <h2>Videos enviados</h2>
                <div class="big">__VIDEO_TOTAL__</div>
            </div>
            <div class="card">
                <h2>Noches de desvelo</h2>
                <div class="big">__NOCHES_DESVELO__</div>
                <small>Mensajes entre las 00:00 y las 05:59.</small>
            </div>
                        <div class="card">
                <h2>Emojis de amor</h2>
                <div class="big">__LOVE_EMOJIS_TOTAL__</div>
                <small>Corazones, caritas y besitos enviados 💕</small>
            </div>

            <div class="card">
                <h2>Charlas de la noche</h2>
                <div class="big">__TARDE_NOCHE__</div>
                <small>Mensajes entre las 22:00 y las 02:00 😏</small>
            </div>

            <div class="card">
                <h2>Maratones de charla</h2>
                <div class="big">__MARATONES__</div>
                <small>Veces que hablaron sin parar durante más de 1 hora.</small>
            </div>

        </section>

        <section>
            <h2 class="section-title">Mensajes por mes</h2>
            <p class="section-subtitle">Cómo ha ido creciendo (o estabilizándose) la conversación.</p>
            <canvas id="mensajesMesChart" height="120"></canvas>
        </section>

        <section>
            <h2 class="section-title">Mensajes por hora del día</h2>
            <p class="section-subtitle">En qué horas del día más suelen hablar.</p>
            <canvas id="mensajesHoraChart" height="120"></canvas>
        </section>

        <section class="flex">
            <div>
                <h2 class="section-title">Amorómetro</h2>
                <p class="section-subtitle">Frases y emojis románticos que más se repiten.</p>
                <ul>
                    __LOVE_LIST__
                </ul>
            </div>
            <div>
                <h2 class="section-title">“Te quiero” por persona</h2>
                <p class="section-subtitle">Quién escribe más veces la frase “te quiero”.</p>
                <ul>
                    __TEQ_LIST__
                </ul>
            </div>
       <div>
        <h2 class="section-title">“Te amo” por persona</h2>
        <p class="section-subtitle">Quién escribe más veces “te amo”.</p>
        <ul>
            __TAMO_LIST__
        </ul>
    </div>
</section>




        <section class="flex">
            <div>
                <h2 class="section-title">Primer "te quiero"</h2>
                <p class="section-subtitle">El primer “te quiero” que quedó guardado en el chat.</p>
                <p>
                    __FIRST_LOVE_HTML__
                </p>
            </div>
            <div>
                <h2 class="section-title">Tiempos de respuesta</h2>
                <p class="section-subtitle">Promedio de cuánto se demoran en responderse.</p>
                <ul>
                    __RESP_LIST__
                </ul>
            </div>
        </section>

            <div>
        <h2 class="section-title">Primer “te amo”</h2>
        <p class="section-subtitle">El primer “te amo” que apareció en el chat ❤️</p>
        <p>
            __FIRST_TAMO_HTML__
        </p>
            </div>
        </section>


        <section>
            <h2 class="section-title">Nube de palabras</h2>
            <p class="section-subtitle">Mientras más grande, más veces apareció en el chat.</p>
            <div id="wordcloud" style="width:100%; height:400px;"></div>
        </section>
    </div>

  

<style>
/* -------- CORAZÓN GARANTIZADO -------- */

#sobre-wrapper {
    max-width: 720px;
    margin: 3rem auto;
    text-align: center;
}

#sobre-texto {
    margin-top: .6rem;
    opacity: .65;
    transition: opacity .4s ease;
}

/* CORAZÓN PERFECTO SVG */
#sobre-corazon {
    width: 150px;
    height: 150px;
    margin: 0 auto;
    cursor: pointer;

    background: linear-gradient(135deg, #ff7a8b, #d11a2a);

    clip-path: path("M75 135 L10 70 A35 35 0 1 1 75 35 A35 35 0 1 1 140 70 Z");

    transition: transform .3s ease, opacity .4s ease;
    filter: drop-shadow(0 8px 25px rgba(0,0,0,0.22));
}

#sobre-corazon:hover {
    transform: translateY(-4px) scale(1.05);
}

/* -------- CARTA -------- */

#carta {
    max-width: 720px;
    margin: 1.8rem auto 3rem auto;
    display: none;
    opacity: 0;
    transform: translateY(15px);
    transition: opacity .6s ease, transform .6s ease;

    background: rgba(255, 255, 255, 0.28);
    backdrop-filter: blur(14px);
    border-radius: 18px;
    border: 1px solid rgba(255,255,255,0.45);
    box-shadow: 0 10px 35px rgba(0,0,0,.12);
    padding: 2rem 1.5rem;
}

#carta h2 {
    text-align: center;
    font-size: 1.8rem;
    margin-top: 0;
    margin-bottom: 1rem;
    font-weight: 800;
    color: #ff7a8b;
}

#carta-texto {
    font-size: 1rem;
    line-height: 1.7;
    padding: 1.2rem;
    background: rgba(255,255,255,0.55);
    border-radius: 14px;
    box-shadow: inset 0 0 10px rgba(0,0,0,0.05);
    color: #374151;
    white-space: pre-line;
}
</style>


<section id="sobre-wrapper">

    <!-- CORAZÓN -->
    <div id="sobre-corazon"></div>

    <p id="sobre-texto"></p>

    <!-- CARTA -->
    <div id="carta">
        <h2>Carta para Rena</h2>

        <p id="carta-texto">
  Gracias por llegar a mi vida y hacer que cada día sea un poquito más bonito.
Este es un detalle sencillo, pero está hecho con muchísimo cariño para ti.
Gracias por todo lo que eres y por todo lo que aportas a mi mundo. Te quiero mucho, mi Rena, mi novia, mi todo.
        </p>
    </div>

</section>


<script>
// CLICK: Desaparecer corazón + texto → mostrar carta
document.getElementById("sobre-corazon").addEventListener("click", function() {

    // Ocultar texto
    const txt = document.getElementById("sobre-texto");
    txt.style.opacity = 0;
    setTimeout(() => txt.style.display = "none", 400);

    // Ocultar corazón
    const cora = document.getElementById("sobre-corazon");
    cora.style.opacity = 0;
    setTimeout(() => cora.style.display = "none", 400);

    // Mostrar carta
    setTimeout(() => {
        const carta = document.getElementById("carta");
        carta.style.display = "block";

        setTimeout(() => {
            carta.style.opacity = 1;
            carta.style.transform = "translateY(0)";
        }, 50);

    }, 450);
});
</script>



    <footer>
    Creado por Sebas para Rena.  
    <br>Porque cada mensaje tuyo merece un lugar bonito donde guardarse.
</footer>


    <script>
        // Datos para mensajes por mes
        const labelsMes = __CHART_LABELS__;
        const dataAuthor1 = __CHART_DATA_AUTHOR1__;
        const dataAuthor2 = __CHART_DATA_AUTHOR2__;

        const ctxMes = document.getElementById('mensajesMesChart').getContext('2d');

        new Chart(ctxMes, {
            type: 'line',
            data: {
                labels: labelsMes,
                datasets: [
                    {
                        label: '__AUTHOR1__',
                        data: dataAuthor1,
                        tension: 0.3,
                        borderWidth: 2,
                        pointRadius: 3
                    },
                    {
                        label: '__AUTHOR2__',
                        data: dataAuthor2,
                        tension: 0.3,
                        borderWidth: 2,
                        pointRadius: 3
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: true },
                    tooltip: { mode: 'index', intersect: false }
                },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } }
                }
            }
        });

        // Datos para mensajes por hora
        const labelsHora = __HOURS_LABELS__;
        const dataHora = __HOURS_DATA__;
        const ctxHora = document.getElementById('mensajesHoraChart').getContext('2d');

        new Chart(ctxHora, {
            type: 'bar',
            data: {
                labels: labelsHora.map(h => h + ":00"),
                datasets: [{
                    label: 'Mensajes',
                    data: dataHora,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } }
                }
            }
        });

        // Nube de palabras
        const wordsData = __WORDCLOUD_DATA__;
        (function() {
            const container = document.getElementById("wordcloud");
            const width = container.clientWidth;
            const height = 400;

            if (!wordsData || wordsData.length === 0) return;

            const maxCount = Math.max.apply(null, wordsData.map(d => d.count));

            const layout = d3.layout.cloud()
                .size([width, height])
                .words(wordsData.map(d => ({
                    text: d.word,
                    count: d.count,
                    size: 14 + (d.count / maxCount) * 30
                })))
                .padding(4)
                .rotate(() => 0)
                .font("Arial")
                .fontSize(d => d.size)
                .on("end", draw);

            layout.start();

            function draw(words) {
                const svg = d3.select("#wordcloud")
                    .append("svg")
                    .attr("width", width)
                    .attr("height", height);

                const group = svg.append("g")
                    .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

                group.selectAll("text")
                    .data(words)
                    .enter().append("text")
                    .style("font-size", d => d.size + "px")
                    .style("fill", d => {
                            const max = Math.max(...words.map(w => w.count));
                            const intensity = d.count / max;
                            // De rosa suave a rojo fuerte
                            return d3.interpolateRgb("#fbb6ce", "#9b1c31")(intensity);
                        })
                    .attr("text-anchor", "middle")
                    .attr("transform", d => "translate(" + [d.x, d.y] + ")")
                    .text(d => d.text)
                    .on("mouseover", function(event, d) {
                        let tooltip = document.getElementById("tooltip");
                        if (!tooltip) {
                            tooltip = document.createElement("div");
                            tooltip.id = "tooltip";
                            tooltip.style.position = "fixed";
                            tooltip.style.background = "white";
                            tooltip.style.border = "1px solid #aaa";
                            tooltip.style.padding = "6px";
                            tooltip.style.borderRadius = "6px";
                            tooltip.style.boxShadow = "0 2px 5px rgba(0,0,0,.2)";
                            tooltip.style.fontSize = "0.85rem";
                            document.body.appendChild(tooltip);
                        }
                        tooltip.innerText = d.text + ": " + d.count + " veces";
                        tooltip.style.display = "block";
                    })
                    .on("mousemove", function(event) {
                        const tooltip = document.getElementById("tooltip");
                        if (!tooltip) return;
                        tooltip.style.left = (event.pageX + 10) + "px";
                        tooltip.style.top = (event.pageY + 10) + "px";
                    })
                    .on("mouseout", function() {
                        const tooltip = document.getElementById("tooltip");
                        if (tooltip) tooltip.style.display = "none";
                    });
            }
        })();
    </script>
    <script>
        window.addEventListener("load", function() {
            const splash = document.getElementById("splash");
            splash.style.opacity = 1;

            setTimeout(() => {
                splash.style.transition = "opacity 0.6s ease";
                splash.style.opacity = 0;

                setTimeout(() => {
                    splash.style.display = "none";
                }, 600);
            }, 800); // tiempo que el corazón se ve antes de desvanecerse
        });
        </script>

</body>
</html>
"""

    html_out = html_template
    html_out = html_out.replace("__TOTAL_MESSAGES__", str(total_messages))
    html_out = html_out.replace("__AUTHOR1__", html.escape(author1))
    html_out = html_out.replace("__AUTHOR2__", html.escape(author2))
    html_out = html_out.replace("__COUNT_AUTHOR1__", str(messages_a1))
    html_out = html_out.replace("__COUNT_AUTHOR2__", str(messages_a2))
    html_out = html_out.replace("__FIRST_DATE__", first_date_str)
    html_out = html_out.replace("__LAST_DATE__", last_date_str)
    html_out = html_out.replace("__TOP_DAY__", top_day_str)
    html_out = html_out.replace("__TOP_DAY_COUNT__", str(stats["top_day_count"]))
    html_out = html_out.replace("__TOP_WEEKDAY_NAME__", top_weekday_name)
    html_out = html_out.replace("__TOP_WEEKDAY_COUNT__", str(top_weekday_count))
    html_out = html_out.replace("__AUDIO_TOTAL__", str(media["audio_total"]))
    html_out = html_out.replace("__AUDIO_A1__", str(audio_a1))
    html_out = html_out.replace("__AUDIO_A2__", str(audio_a2))
    html_out = html_out.replace("__PHOTO_TOTAL__", str(media["photo_total"]))
    html_out = html_out.replace("__VIDEO_TOTAL__", str(media["video_total"]))
    html_out = html_out.replace("__NOCHES_DESVELO__", str(night_total))
    html_out = html_out.replace("__LOVE_EMOJIS_TOTAL__", str(love_emojis_total))
    html_out = html_out.replace("__TARDE_NOCHE__", str(late_evening_total))
    html_out = html_out.replace("__MARATONES__", str(marathons_total))
    html_out = html_out.replace("__LOVE_LIST__", love_list_html)
    html_out = html_out.replace("__TEQ_LIST__", teq_list_html)
    html_out = html_out.replace("__STREAK_TEXT__", html.escape(streak_text))
    html_out = html_out.replace("__FIRST_LOVE_HTML__", first_love_html)
    html_out = html_out.replace("__RESP_LIST__", resp_html)
    html_out = html_out.replace("__CHART_LABELS__", labels_js)
    html_out = html_out.replace("__CHART_DATA_AUTHOR1__", data_a1_js)
    html_out = html_out.replace("__CHART_DATA_AUTHOR2__", data_a2_js)
    html_out = html_out.replace("__HOURS_LABELS__", hours_js)
    html_out = html_out.replace("__HOURS_DATA__", hour_counts_js)
    html_out = html_out.replace("__WORDCLOUD_DATA__", wordcloud_js)
    html_out = html_out.replace("__FIRST_TAMO_HTML__", first_tamo_html)
    html_out = html_out.replace("__TAMO_LIST__", tamo_list_html)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_out)

# -------------------------------------------------
# MAIN
# -------------------------------------------------

def main():
    
    if len(sys.argv) < 2:
        print("Uso: python dashboard_rys.py <archivo_chat_whatsapp.txt>")
        sys.exit(1)

    chat_file = sys.argv[1]

    if not os.path.exists(chat_file):
        print("No se encontró el archivo:", chat_file)
        sys.exit(1)

    print("Leyendo chat desde:", chat_file)
    messages = parse_chat(chat_file)
    print("Mensajes cargados:", len(messages))

    if not messages:
        print("No se detectaron mensajes. Revisa el formato del export.")
        sys.exit(1)

    stats = basic_stats(messages)
    media = media_stats(messages)
    love_overall, love_by_author, te_quiero_by_author, first_love_message, first_te_amo,te_amo_by_author = love_stats(messages)
    love_emojis_total = love_emoji_total(love_overall)
    late_evening_total = late_evening(messages)
    marathons_total = marathon_chats(messages)
    night_total = night_messages(messages)
    top_words_list = top_words(messages, top_n=50)
    streak_info = longest_streak(stats["by_day"])
    resp_stats = response_stats(messages)

    participants = list(stats["by_author"].keys())
    if not participants:
        print("No se detectaron participantes.")
        sys.exit(1)

    output_html = "dashboard_rys.html"
    generate_html(
        output_html,
        stats,
        media,
        love_overall,
        love_by_author,
        te_quiero_by_author,
        first_love_message,
        night_total,
        top_words_list,
        streak_info,
        resp_stats,
        participants,
        love_emojis_total,
        late_evening_total,
        te_amo_by_author,
        first_te_amo,
        marathons_total
    )



    print("Dashboard generado en:", output_html)
    print("Ábrelo en tu navegador.")

if __name__ == "__main__":
    main()
