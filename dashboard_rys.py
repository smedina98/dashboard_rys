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
    r'^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s+'
    r'(\d{1,2}:\d{2}:\d{2})\]\s+'
    r'([^:]+):\s+(.*)$'
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

            # limpiar caracteres invisibles de WhatsApp
            line = line.replace("\u200e", "").strip()

            m = MESSAGE_REGEX.match(line)
            if m:
                # guardar el anterior
                if current:
                    messages.append(current)

                date_str, time_str, author, text = m.groups()

                try:
                    dt_str = f"{date_str} {time_str}"
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

def media_stats(messages):
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

        # limpiar caracteres invisibles
        text = text.replace("\u200e", "").strip()

        # -------------------
        # AUDIOS
        # -------------------
        if "audio omitido" in text or "audio omitted" in text:
            counts["audio_total"] += 1
            counts["audio_by_author"][author] += 1
            continue

        # -------------------
        # IMÁGENES
        # -------------------
        if "imagen omitida" in text or "image omitted" in text:
            counts["photo_total"] += 1
            counts["photo_by_author"][author] += 1
            continue

        # -------------------
        # VIDEOS
        # -------------------
        if "video omitido" in text or "video omitted" in text:
            counts["video_total"] += 1
            counts["video_by_author"][author] += 1
            continue

        # -------------------
        # OTROS
        # -------------------
        if "multimedia omitido" in text or "media omitted" in text:
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
            gap: 1.1rem;
            margin-bottom: 2.4rem;
        }

        .card {
            position: relative;
            overflow: hidden;
            background: rgba(255, 255, 255, 0.82);
            border-radius: 18px;
            border: 1px solid rgba(255, 255, 255, 0.9);
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.16);
            padding: 1.3rem 1.4rem 1.1rem;
            backdrop-filter: blur(10px);
            transition: transform .18s ease, box-shadow .18s ease;
        }

        /* degradado suave tipo “marco” como el header */
        .card::before {
            content: "";
            position: absolute;
            inset: 0;
            background: radial-gradient(circle at top left, rgba(248, 113, 150, 0.26), transparent 55%),
                        radial-gradient(circle at bottom right, rgba(59, 130, 246, 0.18), transparent 55%);
            opacity: 0.8;
            pointer-events: none;
        }

        /* mini línea decorativa arriba */
        .card::after {
            content: "";
            position: absolute;
            top: 0;
            left: 18px;
            right: 18px;
            height: 3px;
            border-radius: 999px;
            background: linear-gradient(90deg, #fbb6ce, #9b1c31);
            opacity: 0.7;
        }

        /* contenido por encima del degradado */
        .card > * {
            position: relative;
            z-index: 1;
        }

        .card:hover {
            transform: translateY(-3px);
            box-shadow: 0 22px 55px rgba(15, 23, 42, 0.22);
        }

        .card h2 {
            margin: 0 0 .35rem 0;
            font-size: .8rem;
            text-transform: uppercase;
            letter-spacing: .16em;
            color: #9b1c31;
            opacity: 0.92;
        }

        .big {
            font-size: 2rem;
            font-weight: 700;
            margin: .2rem 0 .4rem;
        }

        .card small {
            color: #6b7280;
            font-size: .85rem;
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


    <header class="hero">
    <div class="hero-inner">
        <div class="hero-pill">
            <span>Dashboard de amor</span>
        </div>

        <div class="hero-title-row">
            <h1 class="hero-names">Rena &amp; Sebas</h1>
            <span class="hero-heart">❤️</span>
        </div>

        <p class="hero-subtitle">
            Una mirada dulce y curiosa a nuestra historia en WhatsApp.
        </p>

        <div class="hero-meta">
            <span>WhatsApp</span>
            <span class="hero-dot">•</span>
            <span>Desde __FIRST_DATE__ hasta __LAST_DATE__</span>
        </div>
    </div>
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

                <!-- ============================ -->
        <!--   SECCIONES DE AMOR / GRÁFICOS -->
        <!-- ============================ -->

        <section>
            <h2 class="section-title">Nuestra historia mes a mes</h2>
            <p class="section-subtitle">
                Mensajes enviados cada mes desde que empezó nuestro chat.
            </p>
            <canvas id="mensajesMesChart" height="120"></canvas>
        </section>

      

        <section class="flex">
            <div>
                <h2 class="section-title">Amorómetro</h2>
                <p class="section-subtitle">
                    Palabras y emojis que más usan cuando se ponen cursis.
                </p>
                <ul>
                    __LOVE_LIST__
                </ul>
            </div>

            <div>
                <h2 class="section-title">Quién dice más “te quiero”</h2>
                <p class="section-subtitle">
                    Conteo de los “te quiero” que ha enviado cada uno en el chat.
                </p>
                <ul>
                    __TEQ_LIST__
                </ul>
            </div>

            <div>
                <h2 class="section-title">Quién dice más “te amo”</h2>
                <p class="section-subtitle">
                    Cuántos “te amo” ha dicho cada uno.
                </p>
                <ul>
                    __TAMO_LIST__
                </ul>
            </div>
        </section>

        <section class="flex">
            <div>
                <h2 class="section-title">Nuestro primer “te quiero”</h2>
                <p class="section-subtitle">
                    El primer “te quiero” que quedó guardado en el chat.
                </p>
                <p>
                    __FIRST_LOVE_HTML__
                </p>
            </div>

            <div>
                <h2 class="section-title">Cuánto nos demoramos en responder</h2>
                <p class="section-subtitle">
                    Promedio de tiempo que se toma cada uno en contestar los mensajes.
                </p>
                <ul>
                    __RESP_LIST__
                </ul>
            </div>
        </section>

        <section>
            <h2 class="section-title">Nuestro primer “te amo”</h2>
            <p class="section-subtitle">
                El primer “te amo” que apareció en el chat ❤️
            </p>
            <p>
                __FIRST_TAMO_HTML__
            </p>
        </section>

          <section>
            <h2 class="section-title">¿A qué hora hablamos más?</h2>
            <p class="section-subtitle">
                Distribución de mensajes según la hora del día. Ideal para saber si son más de madrugada o de mañanita.
            </p>
            <canvas id="mensajesHoraChart" height="120"></canvas>
        </section>

  
<style>
:root {
    --bg-gradient-from: #ffe6f0;
    --bg-gradient-to:   #e0f0ff;
    --card-bg:          rgba(255,255,255,0.95);
    --card-radius:      14px;
    --shadow-soft:      0 12px 30px rgba(15, 23, 42, 0.12);
    --primary:          #9b1c31;
    --primary-soft:     #fbb6ce;
    --text-main:        #111827;
    --text-muted:       #6b7280;
    --border-subtle:    rgba(255,255,255,0.55);
}

*,
*::before,
*::after {
    box-sizing: border-box;
}

html, body {
    margin: 0;
    padding: 0;
}

body {
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: linear-gradient(135deg, var(--bg-gradient-from), var(--bg-gradient-to));
    color: var(--text-main);
}

/* HEADER */

/* ===== HERO DEL TÍTULO ===== */

header.hero {
    display: flex;
    justify-content: center;
    padding: 2.8rem 1.4rem 1.8rem;
}

.hero-inner {
    max-width: 820px;
    width: 100%;
    background: rgba(255, 255, 255, 0.78);
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.9);
    box-shadow: 0 22px 55px rgba(15, 23, 42, 0.22);
    padding: 1.7rem 1.9rem 1.6rem;
    text-align: left;
    position: relative;
    overflow: hidden;
}

/* Detalle decorativo arriba */

.hero-inner::before {
    content: "";
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at top left, rgba(248, 113, 150, 0.28), transparent 55%),
                radial-gradient(circle at bottom right, rgba(59, 130, 246, 0.22), transparent 55%);
    opacity: 0.7;
    pointer-events: none;
}

.hero-inner > * {
    position: relative;
    z-index: 1;
}

/* Pastilla "Dashboard del amor" */

.hero-pill {
    display: inline-flex;
    align-items: center;
    padding: 0.35rem 0.9rem;
    border-radius: 999px;
    background: rgba(248, 250, 252, 0.95);
    border: 1px solid rgba(148, 163, 184, 0.35);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    color: #9b1c31;
    margin-bottom: 0.9rem;
}

/* Fila del título */

.hero-title-row {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.55rem 0.9rem;
}

.hero-names {
    margin: 0;
    font-size: clamp(2.2rem, 4.8vw, 2.9rem);
    font-weight: 800;
    color: #111827;
}

.hero-heart {
    font-size: 1.9rem;
    filter: drop-shadow(0 7px 18px rgba(220, 38, 38, 0.6));
    transform-origin: center;
    animation: heroBeat 1.3s infinite ease-in-out;
}

/* Subtítulo */

.hero-subtitle {
    margin: 0.4rem 0 0.2rem;
    font-size: 0.98rem;
    color: #4b5563;
}

/* Metadatos (WhatsApp, fechas) */

.hero-meta {
    margin-top: 0.55rem;
    font-size: 0.82rem;
    color: #9ca3af;
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem 0.6rem;
    align-items: center;
}

.hero-dot {
    opacity: 0.6;
}

/* Animación corazón */

@keyframes heroBeat {
    0%   { transform: scale(1); }
    25%  { transform: scale(1.15); }
    40%  { transform: scale(1); }
    60%  { transform: scale(1.12); }
    100% { transform: scale(1); }
}

/* Responsive */

@media (max-width: 768px) {
    header.hero {
        padding: 2.2rem 1rem 1.6rem;
    }

    .hero-inner {
        padding: 1.4rem 1.2rem 1.4rem;
        text-align: center;
    }

    .hero-title-row {
        justify-content: center;
    }

    .hero-meta {
        justify-content: center;
    }
}


/* LAYOUT GENERAL */

.container {
    max-width: 1100px;
    margin: 0 auto 3rem auto;
    padding: 0 1.25rem 2.5rem;
}

/* CARDS */

.cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 1rem;
    margin-bottom: 2.5rem;
}

.card {
    background: var(--card-bg);
    border-radius: var(--card-radius);
    padding: 1.2rem 1.4rem;
    box-shadow: var(--shadow-soft);
    transition: transform .15s ease, box-shadow .15s ease;
}

.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 16px 40px rgba(15,23,42,0.16);
}

.card h2 {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    margin: 0 0 .6rem 0;
    padding: 0.25rem 0.95rem 0.25rem 0.75rem;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: #9b1c31;
    background: rgba(248, 250, 252, 0.95);
    border-radius: 999px;
    border: 1px solid rgba(248, 113, 150, 0.4);
    box-shadow: 0 6px 14px rgba(248, 113, 150, 0.25);
}

/* bolita decorativa antes del título */
.card h2::before {
    content: "";
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: radial-gradient(circle at 30% 30%, #fee2e2, #fb7185);
    box-shadow: 0 0 0 4px rgba(251, 113, 133, 0.22);
}

/* un poco más compacto en móvil */
@media (max-width: 768px) {
    .card h2 {
        padding: 0.22rem 0.8rem 0.22rem 0.65rem;
        font-size: 0.7rem;
        letter-spacing: 0.14em;
        margin-bottom: 0.5rem;
    }
}


.big {
    font-size: 2rem;
    font-weight: 700;
    margin: .4rem 0;
}

.card small {
    color: var(--text-muted);
}

/* SECCIONES Y TITULOS */

.section-title {
    font-size: 1.4rem;
    margin: 2rem 0 0.4rem 0;
}

.section-subtitle {
    margin: 0 0 1rem 0;
    color: var(--text-muted);
}

/* FLEX LAYOUT */

.flex {
    display: flex;
    flex-wrap: wrap;
    gap: 2rem;
    margin-bottom: 2rem;
}

.flex > div {
    flex: 1 1 260px;
}

/* LISTAS */

ul {
    margin: .5rem 0 0 1.2rem;
    padding: 0;
}

li {
    margin-bottom: 0.25rem;
}

/* GRAFICOS */

canvas {
    background: var(--card-bg);
    border-radius: var(--card-radius);
    padding: 1rem;
    box-shadow: var(--shadow-soft);
    margin-bottom: 1.5rem;
}

/* WORDCLOUD */

#wordcloud {
    background: linear-gradient(135deg, #ffe6f0aa, #e3f2ffcc);
    backdrop-filter: blur(6px);
    border-radius: var(--card-radius);
    box-shadow: var(--shadow-soft);
    width: 100%;
    height: 400px;
}

/* FOOTER */

footer {
    text-align: center;
    padding: 1.8rem 1rem 2.2rem;
    font-size: 0.8rem;
    color: var(--text-muted);
    
}

.footer-rys {
    margin-top: 0.9rem;
    display: flex;
    justify-content: center;
}

.rys-logo {
    display: block;
    filter: drop-shadow(0 8px 20px rgba(15, 23, 42, 0.25));
}

/* estilo de las letras dentro del SVG */
.rys-logo text {
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 20px;
    font-weight: 700;
    fill: white;
}

/* corazón del centro */
.rys-heart {
    fill: #fef2f2;
    stroke: #fee2e2;
    stroke-width: 1;
}


/* ========= SPLASH ========= */

#splash {
    position: fixed;
    inset: 0;
    background: white;
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 999999;
    opacity: 1;
    transition: opacity 0.6s ease;
}

.splash-content {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}

#heart {
    width: 120px;
    height: 120px;
    background: linear-gradient(135deg, #ff7a8b, #d11a2a);
    position: relative;
    transform: rotate(-45deg);
    animation: heartbeat 1.1s infinite ease-in-out;
}

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

@keyframes heartbeat {
    0%   { transform: rotate(-45deg) scale(1); }
    25%  { transform: rotate(-45deg) scale(1.15); }
    40%  { transform: rotate(-45deg) scale(1); }
    60%  { transform: rotate(-45deg) scale(1.12); }
    100% { transform: rotate(-45deg) scale(1); }
}

#splash-text {
    margin-top: 22px;
    font-size: 1.8rem;
    font-weight: 700;
    color: #d11a2a;
    opacity: 0;
    animation: fadeIn 1s ease-out forwards;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}


/* ========= CORAZÓN / CARTA ========= */

#carta-section {
    margin-top: 2.5rem;
}

#sobre-wrapper {
    max-width: 720px;
    margin: 0 auto 1.5rem auto;
    text-align: center;
}

#sobre-texto {
    margin-top: .4rem;
    opacity: .7;
    transition: opacity .4s ease, transform .3s ease;
}

/* Corazón (se queda igual, solo afinado) */

#sobre-corazon {
    margin: 1.5rem auto 0;
    width: 150px;
    height: 150px;
    border: none;
    padding: 0;
    background: linear-gradient(135deg, #ff7a8b, #d11a2a);
    cursor: pointer;
    clip-path: path("M75 135 L10 70 A35 35 0 1 1 75 35 A35 35 0 1 1 140 70 Z");
    transition: transform .25s ease, opacity .3s ease, box-shadow .25s ease;
    filter: drop-shadow(0 8px 25px rgba(0,0,0,0.22));
}

#sobre-corazon:hover {
    transform: translateY(-3px) scale(1.05);
    box-shadow: 0 12px 30px rgba(0,0,0,0.28);
}

#sobre-corazon:active {
    transform: translateY(0) scale(0.98);
}

#sobre-corazon:focus-visible {
    outline: 3px solid #fbb6ce;
    outline-offset: 6px;
}

/* Contenedor de la carta (debajo del corazón) */

#carta {
    max-width: 720px;
    margin: 1.2rem auto 3rem auto;
    display: none;               /* se activa con JS */
    opacity: 0;
    transform: translateY(12px);
    transition: opacity .45s ease, transform .45s ease;
}

/* Estado visible (clase que pone JS) */

#carta.carta-visible {
    display: block;
    opacity: 1;
    transform: translateY(0);
}

/* Hoja de la carta */

.carta-paper {
    background: linear-gradient(180deg, #fdfdfd, #f9fafb);
    border-radius: 18px;
    border: 1px solid rgba(209, 213, 219, 0.8);
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.18);
    padding: 1.4rem 1.4rem 1.2rem;
    position: relative;
}

/* pequeña línea decorativa arriba */

.carta-paper::before {
    content: "";
    position: absolute;
    top: 10px;
    left: 18px;
    right: 18px;
    height: 2px;
    border-radius: 999px;
    background: linear-gradient(90deg, #fecaca, #f9a8d4);
    opacity: 0.9;
}

.carta-saludo,
.carta-firma,
#carta-texto {
    position: relative;
    z-index: 1;
}

.carta-saludo {
    margin: 0 0 0.6rem 0;
    font-weight: 600;
    color: #9b1c31;
}

#carta-texto {
    font-size: 0.98rem;
    line-height: 1.7;
    color: #374151;
    white-space: pre-line;
    margin: 0;
}

.carta-firma {
    margin-top: 1.1rem;
    font-size: 0.95rem;
    color: #6b7280;
}

/* Botón de cerrar carta */

.carta-close-text {
    margin-top: 0.8rem;
    border: none;
    background: transparent;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    cursor: pointer;
    color: #9b1c31;
    padding: 0;
    opacity: 0.8;
}

.carta-close-text:hover {
    opacity: 1;
}

/* Responsive */

@media (max-width: 768px) {
    #sobre-corazon {
        width: 130px;
        height: 130px;
    }

    #carta {
        margin: 1rem 0.4rem 2.5rem;
    }

    .carta-paper {
        padding: 1.2rem 1.1rem 1.1rem;
    }
}


/* Responsive */

@media (max-width: 768px) {
    #sobre-corazon {
        width: 130px;
        height: 130px;
    }

    #carta {
        margin: 1.6rem 0.4rem 0;
        padding: 1.3rem 1rem 1.4rem;
    }

    #carta-texto {
        max-height: 230px;
    }
}

/* ========= RESPONSIVE ========= */

@media (max-width: 768px) {
    header {
        padding-top: 2rem;
    }

    .section-title {
        margin-top: 1.6rem;
        font-size: 1.25rem;
    }

    canvas {
        padding: .7rem;
    }

    #wordcloud {
        height: 320px;
    }

    #carta {
        margin: 1.5rem 1rem 2.5rem;
    }
}
</style>


<section id="carta-section">
    <div id="sobre-wrapper">
        <h2 class="section-title">Una carta para Rena</h2>
        <p class="section-subtitle" id="sobre-texto">
            Toca el corazón cuando estés lista para leer tu carta 💌
        </p>

        <button id="sobre-corazon" aria-label="Abrir carta para Rena"></button>
    </div>

    <div id="carta" aria-hidden="true">
        <div class="carta-paper">
            <p class="carta-saludo">Querida Rena,</p>

            <p id="carta-texto">
No sé en qué momento todo empezó a sentirse diferente, pero desde que llegaste, algo en mí cambió para bien. Mi mundo se volvió más tranquilo, más bonito, más lleno de sentido… y todo eso tiene tu nombre.

A veces me quedo pensando en lo afortunado que soy de tenerte, porque no solo eres mi novia, eres ese lugar donde encuentro paz, donde puedo ser yo sin miedo y donde todo se siente correcto. Tu forma de ser, de querer, de entender… todo en ti suma a mi vida de una manera que no puedo explicar del todo, pero que siento profundamente.

No necesito grandes momentos para saber que soy feliz contigo. Me basta con una conversación contigo, con una risa, con tu compañía en silencio… porque incluso en lo simple, contigo todo se vuelve especial.

Quiero que sepas que te amo de verdad, con todo lo que soy. Amo tu esencia, tu forma de ver la vida y la manera en la que haces que todo sea más fácil y más bonito para mí.

Renata Valentina, gracias por estar, por quedarte, por elegirme cada día. Eres una parte fundamental de mi vida, y sinceramente, no la imagino sin ti.
            </p>

            <p class="carta-firma">
                Con amor,<br>
                Sebas
            </p>

            <button id="cerrar-carta" class="carta-close-text" type="button">
                Cerrar carta
            </button>
        </div>
    </div>
</section>




<script>
document.addEventListener("DOMContentLoaded", function () {
    const heart = document.getElementById("sobre-corazon");
    const carta = document.getElementById("carta");
    const cerrar = document.getElementById("cerrar-carta");
    const texto = document.getElementById("sobre-texto");

    if (!heart || !carta) return;

    function abrirCarta() {
        // Oculta el corazón con animación
        heart.style.opacity = "0";
        heart.style.transform = "translateY(-8px) scale(0.9)";
        texto.style.opacity = "0.4";
        texto.textContent = "Gracias por leerla ✨";

        setTimeout(() => {
            heart.style.display = "none";
        }, 260);

        // Muestra la carta
        carta.style.display = "block";
        requestAnimationFrame(() => {
            carta.classList.add("carta-visible");
        });

        carta.setAttribute("aria-hidden", "false");
    }

    function cerrarCarta() {
        // Vuelve a mostrar el corazón
        heart.style.display = "block";
        requestAnimationFrame(() => {
            heart.style.opacity = "1";
            heart.style.transform = "translateY(0) scale(1)";
        });

        texto.style.opacity = "0.7";
        texto.textContent = "Toca el corazón cuando estés lista para leer tu carta 💌";

        // Oculta la carta
        carta.classList.remove("carta-visible");
        carta.setAttribute("aria-hidden", "true");
        setTimeout(() => {
            carta.style.display = "none";
        }, 260);
    }

    heart.addEventListener("click", abrirCarta);
    heart.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            abrirCarta();
        }
    });

    if (cerrar) {
        cerrar.addEventListener("click", cerrarCarta);
    }
});
</script>




    <footer>
        <div>
            Creado por Sebas para Rena.  
            <br>Porque cada mensaje tuyo merece un lugar bonito donde guardarse.
        </div>

        <div class="footer-rys">
            <svg class="rys-logo" width="140" height="48" viewBox="0 0 140 48" xmlns="http://www.w3.org/2000/svg" aria-label="R y S unidos">
                <defs>
                    <linearGradient id="rysBg" x1="0" y1="0" x2="1" y2="1">
                        <stop offset="0%" stop-color="#f9a8d4"/>
                        <stop offset="100%" stop-color="#ec4899"/>
                    </linearGradient>
                </defs>

                <!-- pastilla de fondo -->
                <rect x="1" y="1" width="138" height="46" rx="23" fill="url(#rysBg)" />

                <!-- borde suave -->
                <rect x="1" y="1" width="138" height="46" rx="23"
                      fill="none" stroke="rgba(255,255,255,0.7)" stroke-width="1.2"/>

                <!-- letras R y S -->
                <text x="38" y="30" text-anchor="middle">R</text>
                <text x="102" y="30" text-anchor="middle">S</text>

                <!-- corazoncito delante de la y -->
                <path d="M67 22
                         C 65 19, 61 19, 60 22
                         C 59 25, 62 28, 67 31
                         C 72 28, 75 25, 74 22
                         C 73 19, 69 19, 67 22 Z"
                      class="rys-heart" />
            </svg>
        </div>
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
        const canvasHora = document.getElementById('mensajesHoraChart');

        if (canvasHora) {
            const ctxHora = canvasHora.getContext('2d');

            // Degradado vertical para las barras
            const gradientHora = ctxHora.createLinearGradient(0, 0, 0, canvasHora.height || 200);
            gradientHora.addColorStop(0, 'rgba(248, 113, 150, 0.95)');
            gradientHora.addColorStop(1, 'rgba(244, 114, 182, 0.45)');

            new Chart(ctxHora, {
                type: 'bar',
                data: {
                    labels: labelsHora.map(h => h + ":00"),
                    datasets: [{
                        label: 'Mensajes por hora',
                        data: dataHora,
                        backgroundColor: gradientHora,
                        hoverBackgroundColor: gradientHora,
                        borderWidth: 0,
                        maxBarThickness: 26
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                title: function(items) {
                                    return 'Hora: ' + items[0].label;
                                },
                                label: function(item) {
                                    return 'Mensajes: ' + item.formattedValue;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: {
                                maxRotation: 0,
                                autoSkip: true,
                                autoSkipPadding: 8
                            }
                        },
                        y: {
                            beginAtZero: true,
                            ticks: { precision: 0 },
                            grid: {
                                color: 'rgba(148, 163, 184, 0.35)',
                                drawBorder: false
                            }
                        }
                    },
                    layout: {
                        padding: { top: 8, right: 4, bottom: 0, left: 0 }
                    }
                }
            });
        }



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
