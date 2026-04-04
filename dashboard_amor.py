# =======================
# Dashboard del Amor - Rena & Sebas
# Historial de una historia de amor
# =======================

import sys
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import html
import json

MESSAGE_REGEX = re.compile(
    r'^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s+'
    r'(\d{1,2}:\d{2}:\d{2})\]\s+'
    r'([^:]+):\s+(.*)$'
)

def parse_chat(file_path):
    messages = []
    current = None

    with open(file_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            line = line.replace("\u200e", "").strip()

            m = MESSAGE_REGEX.match(line)
            if m:
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
                if current:
                    current["text"] += "\n" + line

    if current:
        messages.append(current)

    return messages


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

    weekday_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    top_weekday = ("N/A", 0)
    if by_weekday:
        wd_idx, wd_count = max(by_weekday.items(), key=lambda x: x[1])
        top_weekday = (weekday_names[wd_idx], wd_count)

    return {
        "total_messages": total,
        "by_author": by_author,
        "by_day": by_day,
        "by_month_author": by_month_author,
        "by_hour": by_hour,
        "by_weekday": by_weekday,
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
        text = text.replace("\u200e", "").strip()

        if "audio omitido" in text or "audio omitted" in text:
            counts["audio_total"] += 1
            counts["audio_by_author"][author] += 1
            continue

        if "imagen omitida" in text or "image omitted" in text:
            counts["photo_total"] += 1
            counts["photo_by_author"][author] += 1
            continue

        if "video omitido" in text or "video omitted" in text:
            counts["video_total"] += 1
            counts["video_by_author"][author] += 1
            continue

        if "multimedia omitido" in text or "media omitted" in text or "sticker omitido" in text:
            counts["other_total"] += 1
            counts["other_by_author"][author] += 1

    return counts


def love_stats(messages):
    love_phrases = [
        "te quiero", "te amo", "te adoro", "te extraño", "le extraño",
        "mi amor", "amor", "le quiero", "amor mío", "le amo", "te quiero mucho",
        "te adoro", "me gustas", "me encantas", "eres lo maximo", "lo máximo",
        "eres especial", "me haces feliz", "eres genial", "gracias por",
        "me alegra", "me encanta", "qué lindo", "qué bonito"
    ]

    love_emojis = [
        "❤️", "💜", "💙", "💚", "💛", "🧡", "😍", "😘", "🥺", "💖", "💕",
        "💞", "💘", "😊", "☺️", "🥰", "😗", "😚", "🤗", "✨", "🙈", "💑"
    ]

    kisses_emojis = ["😘", "💋", "😗", "😚"]

    overall = Counter()
    by_author_phrases = defaultdict(lambda: Counter())
    te_quiero_by_author = Counter()
    te_amo_by_author = Counter()
    first_love_message = None
    first_te_amo = None

    for m in messages:
        txt = m["text"]
        low = txt.lower()
        author = m["author"]
        dt = m["datetime"]

        for phrase in love_phrases:
            count = low.count(phrase)
            if count > 0:
                overall[phrase] += count
                by_author_phrases[author][phrase] += count

                if phrase in ("te quiero", "le quiero", "te quiero mucho"):
                    te_quiero_by_author[author] += low.count("te quiero")
                    te_quiero_by_author[author] += low.count("le quiero")

                if phrase in ("te amo", "le amo"):
                    te_amo_by_author[author] += count

                if dt is not None:
                    if first_love_message is None or dt < first_love_message["datetime"]:
                        if phrase in ("te quiero", "te amo", "le quiero", "le amo", "me gustas", "me encantas"):
                            first_love_message = {
                                "datetime": dt,
                                "author": author,
                                "phrase": phrase,
                                "text": txt
                            }

                if phrase == "te amo" or phrase == "le amo":
                    if dt is not None:
                        if first_te_amo is None or dt < first_te_amo["datetime"]:
                            first_te_amo = {
                                "datetime": dt,
                                "author": author,
                                "phrase": phrase,
                                "text": txt
                            }

        for emo in love_emojis:
            count = txt.count(emo)
            if count > 0:
                overall[emo] += count
                by_author_phrases[author][emo] += count

    return overall, by_author_phrases, te_quiero_by_author, first_love_message, first_te_amo, te_amo_by_author


def greetings_stats(messages):
    good_morning_phrases = [
        "buenos días", "buenas tardes", "buenas noches", "buen día",
        "buena noche", "buen día", "hola buenos", "hola buenas"
    ]
    
    morning_by_author = Counter()
    night_by_author = Counter()
    first_greeting = {}
    
    for m in messages:
        txt = m["text"].lower()
        author = m["author"]
        dt = m["datetime"]
        
        if dt:
            for phrase in good_morning_phrases:
                if phrase in txt:
                    if "tardes" in phrase or "tarde" in txt:
                        morning_by_author[author] += 1
                    elif "noches" in phrase or "noche" in txt:
                        night_by_author[author] += 1
                    else:
                        morning_by_author[author] += 1
                    
                    key = author
                    if key not in first_greeting:
                        first_greeting[key] = {"datetime": dt, "text": m["text"]}
                    elif dt < first_greeting[key]["datetime"]:
                        first_greeting[key] = {"datetime": dt, "text": m["text"]}
                    break
    
    return morning_by_author, night_by_author, first_greeting


def care_stats(messages):
    care_phrases = [
        "cuidado", "cuídate", "con cuidado", "por favor", "te wish",
        "descansa", "que descanses", "que duermas", "que te vaya bien",
        "que tengas", "mucho ánimo", "ánimo", "tú puedes", "tu puedes",
        "te mando", "un abrazo", "abrazos", "fuerza", "me preocupa",
        "estas bien", "estás bien", "no trabajes", "no te esfuerces"
    ]
    
    care_by_author = Counter()
    care_by_type = Counter()
    
    for m in messages:
        txt = m["text"].lower()
        author = m["author"]
        
        for phrase in care_phrases:
            if phrase in txt:
                care_by_author[author] += 1
                care_by_type[phrase] += 1
    
    return care_by_author, care_by_type


def excitement_stats(messages):
    excitement_words = [
        "genial", "increíble", "maravilloso", "hermoso", "hermosa",
        "lindo", "linda", "bonito", "bonita", "perfecto", "perfecta",
        "fenomenal", "espectacular", "divino", "divina", "wow", "uau",
        "al pelo", "alOOT", "genial", "que emoción", "qué emoción",
        "estoy feliz", "estoy contenta", "estoy contento", "qué bien",
        "me alegro", "me alegra", "qué alegría", "qué chévere"
    ]
    
    excitement_by_author = Counter()
    excited_messages = []
    
    for m in messages:
        txt = m["text"].lower()
        author = m["author"]
        dt = m["datetime"]
        
        for word in excitement_words:
            if word in txt:
                excitement_by_author[author] += 1
                if dt and len(excited_messages) < 5:
                    excited_messages.append({
                        "datetime": dt,
                        "author": author,
                        "text": m["text"][:100]
                    })
                break
    
    return excitement_by_author, excited_messages


def laugh_stats(messages):
    laugh_patterns = [
        ("jajajajaj", "jajajaja"),
        ("jajaja", "jajaj"),
        ("jeje", "jeje"),
        ("jajaj", "jajaja"),
        ("jaja", "jaja"),
        ("jajajaja", "jajajaj"),
    ]
    
    laugh_by_author = Counter()
    
    for m in messages:
        txt = m["text"].lower()
        author = m["author"]
        
        for pattern, _ in laugh_patterns:
            count = txt.count(pattern)
            laugh_by_author[author] += count
    
    return laugh_by_author


def sweet_words_stats(messages):
    sweet_words = [
        "hermosa", "hermoso", "linda", "lindo", "bonita", "bonito",
        "guapa", "guapo", "preciosa", "precioso", "adorable",
        "bebé", "bebe", "cariño", "corazón", "princesa", "mi vida",
        "mi cielo", "querida", "querido", "mi reina", "rey", "rey mío",
        "preciado", "preciada", "tesoro", "chiquitita", "chiquito"
    ]
    
    sweet_by_author = Counter()
    sweet_words_found = Counter()
    
    for m in messages:
        txt = m["text"].lower()
        author = m["author"]
        
        for word in sweet_words:
            count = txt.count(word)
            if count > 0:
                sweet_by_author[author] += count
                sweet_words_found[word] += count
    
    return sweet_by_author, sweet_words_found


def dates_planned_stats(messages):
    planning_phrases = [
        "nos vemos", "vamos a", "podemos ir", "quiero verte",
        "quería verte", "vámonos", "vamos por", "encontrarnos",
        "quedamos en", "organizamos", "planeamos", "coordina",
        "a las", "me pasas", "paso por ti", "recoger", "junten",
        "juntemos", "salgamos", "salir juntos"
    ]
    
    planned_dates = []
    
    for m in messages:
        txt = m["text"].lower()
        author = m["author"]
        dt = m["datetime"]
        
        for phrase in planning_phrases:
            if phrase in txt:
                planned_dates.append({
                    "datetime": dt,
                    "author": author,
                    "text": m["text"][:150]
                })
                break
    
    return len(planned_dates), planned_dates[:10]


def first_meet_stats(messages):
    meet_keywords = [
        "llegaste", "llegué", "te vi", "me vi", "encontramos",
        "nos vimos", "quedamos", "viste", "primera vez", "por primera",
        "cuando nos", "ya salimos", "salimos juntos", "nuestra primera"
    ]
    
    first_meet = None
    
    for m in messages:
        txt = m["text"].lower()
        dt = m["datetime"]
        
        for keyword in meet_keywords:
            if keyword in txt:
                if dt and (first_meet is None or dt < first_meet["datetime"]):
                    first_meet = {
                        "datetime": dt,
                        "author": m["author"],
                        "text": m["text"][:200]
                    }
                break
    
    return first_meet


def compliments_stats(messages):
    compliment_words = [
        "te queda", "qué linda", "qué bonito", "qué guapa", "qué hermosa",
        "qué bien", "estás bonita", "estás linda", "me gusta cómo",
        "quedó bien", "te ves", "se te ve", "estás genial",
        "te ves increíble", "estás marav", "te ves herm", "wow",
        "uau", "qué cool", "cool", "awesome"
    ]
    
    compliments_by_author = Counter()
    
    for m in messages:
        txt = m["text"].lower()
        author = m["author"]
        
        for phrase in compliment_words:
            if phrase in txt:
                compliments_by_author[author] += 1
                break
    
    return compliments_by_author


def support_emoji_stats(messages):
    support_emojis = ["💪", "🙏", "🙌", "✨", "⭐", "🌟", "💫", "🦋", "🌈", "💝"]
    
    support_by_author = Counter()
    
    for m in messages:
        txt = m["text"]
        author = m["author"]
        
        for emo in support_emojis:
            count = txt.count(emo)
            if count > 0:
                support_by_author[author] += count
    
    return support_by_author


def night_messages(messages):
    night_total = 0
    night_by_author = Counter()
    
    for m in messages:
        dt = m["datetime"]
        if dt is None:
            continue
        if 0 <= dt.hour < 6:
            night_total += 1
            night_by_author[m["author"]] += 1
    
    return night_total, night_by_author


def late_evening(messages):
    total = 0
    by_author = Counter()
    
    for m in messages:
        dt = m["datetime"]
        if not dt:
            continue
        if dt.hour >= 22 or dt.hour < 2:
            total += 1
            by_author[m["author"]] += 1
    
    return total, by_author


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
        "archivo","img","stk","jpg","mensaje","webp","opus","está","qué","jajajaj","jejeje",
        "sebas","jajaj","jejej","buenos","buenas","gracias","saludos"
    ])

    word_counter = Counter()

    for m in messages:
        text = m["text"].lower()
        text = re.sub(r"\b\d+\b", " ", text)
        text = re.sub(r"\w*\d\w*", " ", text)
        text = re.sub(r"[^\wáéíóúñü]+", " ", text)

        for w in text.split():
            if len(w) <= 2:
                continue
            if w in stopwords:
                continue
            if w.isdigit():
                continue
            word_counter[w] += 1

    return word_counter.most_common(top_n)


def longest_streak(by_day_counter):
    if not by_day_counter:
        return 0, None, None

    days = sorted(by_day_counter.keys())
    best_len = cur_len = 1
    best_start = cur_start = days[0]
    best_end = days[0]

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
            window = []

    return marathons


def response_stats(messages):
    dated = [m for m in messages if m["datetime"]]
    dated_sorted = sorted(dated, key=lambda x: x["datetime"])
    authors = list({m["author"] for m in dated_sorted})

    if len(authors) < 2:
        return {}

    sums = defaultdict(int)
    counts = defaultdict(int)
    prev = None

    for m in dated_sorted:
        if prev is not None:
            if m["author"] != prev["author"]:
                delta = (m["datetime"] - prev["datetime"]).total_seconds()
                if 0 < delta < 60 * 60 * 24:
                    key = (m["author"], prev["author"])
                    sums[key] += delta
                    counts[key] += 1
        prev = m

    averages = {}
    for k in sums:
        averages[k] = sums[k] / counts[k]

    return averages


def love_emoji_total(love_overall):
    romantic_emojis = "❤️💜💙💚💛🧡😍😘🥺💖💕💞💘😊☺️🥰"
    total = 0
    for token, count in love_overall.items():
        if any(e in token for e in romantic_emojis):
            total += count
    return total


def calculate_love_score(stats, love_stats, media, care_stats):
    score = 0
    
    total = stats["total_messages"]
    score += min(total // 10, 30)
    
    love_overall = love_stats[0]
    love_count = sum(love_overall.values())
    score += min(love_count * 2, 40)
    
    audio_total = media["audio_total"]
    score += min(audio_total // 2, 20)
    
    care_by_author = care_stats[0]
    care_count = sum(care_by_author.values())
    score += min(care_count, 10)
    
    return min(score, 100)


def generate_html(output_path, stats, media, love_data, greetings_data, care_data, 
                  excitement_data, laugh_data, sweet_data, dates_data, meet_data,
                  compliments_data, support_data, night_data, late_data,
                  top_words_list, streak_info, resp_stats, participants):
    
    love_overall, love_by_author, te_quiero_by_author, first_love_message, first_te_amo, te_amo_by_author = love_data
    morning_by_author, night_greetings_by_author, first_greeting = greetings_data
    care_by_author, care_by_type = care_data
    excitement_by_author, excited_messages = excitement_data
    laugh_by_author = laugh_data
    sweet_by_author, sweet_words_found = sweet_data
    dates_planned_count, dates_planned_list = dates_data
    first_meet = meet_data
    compliments_by_author = compliments_data
    support_by_author = support_data
    night_total, night_by_author = night_data
    late_evening_total, late_by_author = late_data
    
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

    total_messages = stats["total_messages"]
    messages_a1 = stats["by_author"].get(author1, 0)
    messages_a2 = stats["by_author"].get(author2, 0)
    audio_a1 = media["audio_by_author"].get(author1, 0)
    audio_a2 = media["audio_by_author"].get(author2, 0)

    first_date_str = stats["first_dt"].strftime("%d/%m/%Y") if stats["first_dt"] else "Desconocida"
    last_date_str = stats["last_dt"].strftime("%d/%m/%Y") if stats["last_dt"] else "Desconocida"
    top_day_str = stats["top_day"].strftime("%d/%m/%Y") if stats["top_day"] else "N/A"
    top_weekday_name, top_weekday_count = stats["top_weekday"]

    streak_len, streak_start, streak_end = streak_info
    if streak_len <= 1 or not streak_start:
        streak_text = "Construyendo su historia día a día"
    else:
        streak_text = f"{streak_len} días seguidos juntos"

    love_top = [item for item in love_overall.most_common(10) if item[1] > 0]
    love_list_html = ""
    for token, count in love_top:
        love_list_html += f'<li><span class="emoji-love">❤️</span> <strong>{html.escape(str(token))}</strong>: <em>{count}</em> veces</li>\n'
    if not love_list_html:
        love_list_html = "<li>El amor está en cada mensaje 💕</li>"

    teq_list_html = ""
    for auth, c in te_quiero_by_author.items():
        teq_list_html += f'<li><strong>{html.escape(auth)}</strong>: {c} veces "te quiero"</li>\n'
    if not teq_list_html:
        teq_list_html = "<li>Pronto llegarán los te quiero 💕</li>"

    tamo_list_html = ""
    for auth, c in te_amo_by_author.items():
        tamo_list_html += f'<li><strong>{html.escape(auth)}</strong>: {c} veces "te amo"</li>\n'
    if not tamo_list_html:
        tamo_list_html = "<li>El primer te amo será inolvidable ❤️</li>"

    morning_list_html = ""
    for auth, c in morning_by_author.most_common():
        morning_list_html += f'<li><strong>{html.escape(auth)}</strong>: {c} saludos</li>\n'

    care_list_html = ""
    for auth, c in care_by_author.most_common():
        care_list_html += f'<li><strong>{html.escape(auth)}</strong>: {c} muestras de cariño</li>\n'

    sweet_list_html = ""
    for word, c in sweet_words_found.most_common(8):
        sweet_list_html += f'<li><em>"{word}"</em>: {c} veces</li>\n'

    first_meet_html = ""
    if first_meet:
        fmeet_date = first_meet["datetime"].strftime("%d/%m/%Y %H:%M")
        fmeet_author = first_meet["author"]
        fmeet_text = first_meet["text"].replace("\n", " ")[:100]
        first_meet_html = f'<p><strong>{html.escape(fmeet_author)}</strong> escribió el {fmeet_date}:<br><em>"{html.escape(fmeet_text)}..."</em></p>'
    else:
        first_meet_html = "<p>Su historia apenas comienza...</p>"

    first_love_html = ""
    if first_love_message:
        fla_date = first_love_message["datetime"].strftime("%d/%m/%Y %H:%M")
        fla_author = first_love_message["author"]
        fla_phrase = first_love_message["phrase"]
        fla_text = first_love_message["text"].replace("\n", " ")[:100]
        first_love_html = f'<p><strong>{html.escape(fla_author)}</strong> dijo <em>"{html.escape(fla_phrase)}"</em> el {fla_date}<br><small>"{html.escape(fla_text)}..."</small></p>'
    else:
        first_love_html = "<p>El amor está en cada palabra 💕</p>"

    first_tamo_html = ""
    if first_te_amo:
        fta_date = first_te_amo["datetime"].strftime("%d/%m/%Y %H:%M")
        fta_author = first_te_amo["author"]
        fta_phrase = first_te_amo["phrase"]
        fta_text = first_te_amo["text"].replace("\n", " ")[:100]
        first_tamo_html = f'<p><strong>{html.escape(fta_author)}</strong> dijo <em>"{html.escape(fta_phrase)}"</em> el {fta_date}<br><small>"{html.escape(fta_text)}..."</small></p>'
    else:
        first_tamo_html = "<p>El primer te amo será un momento mágico ✨</p>"

    resp_html = ""
    if resp_stats:
        for (resp, orig), seconds in sorted(resp_stats.items(), key=lambda x: x[1])[:5]:
            mins = round(seconds / 60, 1)
            resp_html += f'<li><strong>{html.escape(resp)}</strong> responde a <strong>{html.escape(orig)}</strong> en <em>{mins}</em> minutos</li>\n'
    else:
        resp_html = "<li>El tiempo no importa cuando se hablan 💕</li>"

    love_score = calculate_love_score(stats, love_data, media, care_data)
    score_label = "Recién nacidos en el amor" if love_score < 20 else "Pareja en crecimiento" if love_score < 40 else "Amor en pleno bloom" if love_score < 60 else "Amor verdadero" if love_score < 80 else "Amor para toda la vida"
    score_emoji = "🌱" if love_score < 20 else "🌸" if love_score < 40 else "💕" if love_score < 60 else "💖" if love_score < 80 else "💘"

    html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard del Amor - {author1} & {author2}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/d3-cloud/build/d3.layout.cloud.js"></script>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='0.9em' font-size='90'>💕</text></svg>">
    <style>
        :root {{
            --pink-light: #ffe4ec;
            --pink-medium: #ff8fab;
            --pink-dark: #e11d48;
            --purple-light: #e0e7ff;
            --purple-medium: #818cf8;
            --gradient-romantic: linear-gradient(135deg, #fce7f3 0%, #fbcfe8 25%, #f9a8d4 50%, #f472b6 75%, #ec4899 100%);
            --gradient-card: linear-gradient(145deg, rgba(255,255,255,0.9) 0%, rgba(255,245,247,0.85) 100%);
            --shadow-soft: 0 10px 40px rgba(236, 72, 153, 0.15);
            --shadow-hover: 0 20px 60px rgba(236, 72, 153, 0.25);
            --radius-lg: 24px;
            --radius-md: 16px;
            --radius-sm: 12px;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 50%, #fbcfe8 100%);
            min-height: 100vh;
            color: #1f2937;
            line-height: 1.6;
        }}

        /* Splash Screen */
        #splash {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: white;
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 999999;
            transition: opacity 0.8s ease;
        }}

        .splash-content {{
            text-align: center;
        }}

        .heart-container {{
            position: relative;
            width: 140px;
            height: 140px;
            margin: 0 auto;
        }}

        .heart-big {{
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #ff7a8b, #e11d48);
            position: relative;
            transform: rotate(-45deg);
            animation: heartbeat 1.2s infinite ease-in-out;
            border-radius: 8px;
        }}

        .heart-big::before,
        .heart-big::after {{
            content: "";
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #ff7a8b, #e11d48);
            border-radius: 50%;
            position: absolute;
        }}

        .heart-big::before {{
            top: -50%;
            left: 0;
        }}

        .heart-big::after {{
            top: 0;
            left: 50%;
        }}

        @keyframes heartbeat {{
            0%, 100% {{ transform: rotate(-45deg) scale(1); }}
            15% {{ transform: rotate(-45deg) scale(1.15); }}
            30% {{ transform: rotate(-45deg) scale(1); }}
            45% {{ transform: rotate(-45deg) scale(1.1); }}
        }}

        .splash-text {{
            margin-top: 30px;
            font-size: 2rem;
            font-weight: 700;
            color: #e11d48;
            opacity: 0;
            animation: fadeInUp 1s ease-out 0.3s forwards;
        }}

        .splash-names {{
            font-size: 1.2rem;
            color: #ec4899;
            margin-top: 10px;
            opacity: 0;
            animation: fadeInUp 1s ease-out 0.6s forwards;
        }}

        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* Header */
        .hero {{
            text-align: center;
            padding: 3rem 1rem 2rem;
            background: var(--gradient-romantic);
            margin-bottom: 2rem;
            box-shadow: 0 4px 20px rgba(236, 72, 153, 0.2);
        }}

        .hero-badge {{
            display: inline-block;
            padding: 0.5rem 1.5rem;
            background: rgba(255,255,255,0.9);
            border-radius: 50px;
            font-size: 0.85rem;
            font-weight: 600;
            color: #e11d48;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 1rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}

        .hero-title {{
            font-size: clamp(2.5rem, 6vw, 4rem);
            font-weight: 800;
            background: linear-gradient(to right, #be185d, #db2777, #ec4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
        }}

        .hero-heart {{
            font-size: 3rem;
            animation: pulse 2s infinite;
            display: inline-block;
        }}

        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.2); }}
        }}

        .hero-subtitle {{
            font-size: 1.1rem;
            color: #9d174d;
            opacity: 0.9;
            max-width: 600px;
            margin: 0 auto;
        }}

        .hero-meta {{
            display: flex;
            justify-content: center;
            gap: 1rem;
            margin-top: 1.5rem;
            flex-wrap: wrap;
        }}

        .hero-meta span {{
            background: rgba(255,255,255,0.5);
            padding: 0.4rem 1rem;
            border-radius: 20px;
            font-size: 0.85rem;
            color: #be185d;
        }}

        /* Container */
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 1.5rem 3rem;
        }}

        /* Love Score Section */
        .love-score-section {{
            background: var(--gradient-card);
            border-radius: var(--radius-lg);
            padding: 2.5rem;
            text-align: center;
            margin-bottom: 2rem;
            box-shadow: var(--shadow-soft);
            border: 2px solid rgba(236, 72, 153, 0.2);
        }}

        .love-score-emoji {{
            font-size: 4rem;
            margin-bottom: 1rem;
        }}

        .love-score-number {{
            font-size: 4rem;
            font-weight: 800;
            background: linear-gradient(to right, #ec4899, #f472b6, #fb7185);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .love-score-label {{
            font-size: 1.5rem;
            color: #be185d;
            font-weight: 600;
            margin-top: 0.5rem;
        }}

        .love-score-bar {{
            max-width: 400px;
            height: 12px;
            background: #fce7f3;
            border-radius: 10px;
            margin: 1.5rem auto 0;
            overflow: hidden;
        }}

        .love-score-fill {{
            height: 100%;
            background: linear-gradient(90deg, #f472b6, #ec4899, #db2777);
            border-radius: 10px;
            transition: width 1s ease;
        }}

        /* Cards Grid */
        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }}

        .card {{
            background: var(--gradient-card);
            border-radius: var(--radius-md);
            padding: 1.5rem;
            box-shadow: var(--shadow-soft);
            transition: all 0.3s ease;
            border: 1px solid rgba(255,255,255,0.8);
            position: relative;
            overflow: hidden;
        }}

        .card::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #f472b6, #ec4899);
            opacity: 0.7;
        }}

        .card:hover {{
            transform: translateY(-5px);
            box-shadow: var(--shadow-hover);
        }}

        .card-icon {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}

        .card h2 {{
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #be185d;
            margin-bottom: 0.5rem;
            font-weight: 600;
        }}

        .card .big {{
            font-size: 2.2rem;
            font-weight: 800;
            color: #1f2937;
            margin: 0.3rem 0;
        }}

        .card small {{
            color: #6b7280;
            font-size: 0.85rem;
        }}

        .card .detail {{
            font-size: 1rem;
            color: #4b5563;
            margin-top: 0.3rem;
        }}

        /* Section Styles */
        .section {{
            margin-bottom: 3rem;
        }}

        .section-header {{
            text-align: center;
            margin-bottom: 2rem;
        }}

        .section-title {{
            font-size: 2rem;
            font-weight: 700;
            color: #be185d;
            margin-bottom: 0.5rem;
        }}

        .section-subtitle {{
            color: #6b7280;
            font-size: 1.1rem;
        }}

        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
        }}

        .stat-card {{
            background: white;
            border-radius: var(--radius-md);
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05);
            border-left: 4px solid #ec4899;
        }}

        .stat-card h3 {{
            font-size: 1.1rem;
            color: #be185d;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .stat-card ul {{
            list-style: none;
            padding: 0;
        }}

        .stat-card li {{
            padding: 0.5rem 0;
            border-bottom: 1px solid #f3f4f6;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .stat-card li:last-child {{
            border-bottom: none;
        }}

        .stat-card .highlight {{
            color: #ec4899;
            font-weight: 600;
        }}

        /* Charts */
        canvas {{
            background: white;
            border-radius: var(--radius-md);
            padding: 1.5rem;
            box-shadow: var(--shadow-soft);
            margin-bottom: 2rem;
        }}

        /* Word Cloud */
        #wordcloud {{
            background: linear-gradient(135deg, #fdf2f8, #fce7f3);
            border-radius: var(--radius-lg);
            padding: 2rem;
            box-shadow: var(--shadow-soft);
            min-height: 400px;
        }}

        /* Love Timeline */
        .timeline {{
            position: relative;
            max-width: 800px;
            margin: 0 auto;
        }}

        .timeline::before {{
            content: "";
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            width: 4px;
            height: 100%;
            background: linear-gradient(to bottom, #f472b6, #ec4899);
            border-radius: 2px;
        }}

        .timeline-item {{
            background: white;
            border-radius: var(--radius-md);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: var(--shadow-soft);
            position: relative;
            width: calc(50% - 2rem);
        }}

        .timeline-item:nth-child(odd) {{
            margin-left: auto;
        }}

        .timeline-item::before {{
            content: "💕";
            position: absolute;
            width: 40px;
            height: 40px;
            background: #fce7f3;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            top: -10px;
        }}

        .timeline-item:nth-child(odd)::before {{
            left: -25px;
        }}

        .timeline-item:nth-child(even)::before {{
            right: -25px;
        }}

        .timeline-date {{
            font-size: 0.85rem;
            color: #ec4899;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}

        .timeline-author {{
            font-weight: 700;
            color: #be185d;
            margin-bottom: 0.3rem;
        }}

        .timeline-text {{
            color: #4b5563;
            font-size: 0.95rem;
        }}

        /* Footer */
        footer {{
            text-align: center;
            padding: 3rem 1rem;
            background: linear-gradient(to bottom, transparent, #fdf2f8);
        }}

        .footer-hearts {{
            font-size: 2rem;
            margin-bottom: 1rem;
        }}

        .footer-text {{
            color: #be185d;
            font-size: 1.1rem;
            margin-bottom: 0.5rem;
        }}

        .footer-subtext {{
            color: #6b7280;
            font-size: 0.9rem;
        }}

        /* Letter Section */
        .letter-section {{
            margin-top: 3rem;
            text-align: center;
        }}

        .letter-heart {{
            width: 120px;
            height: 120px;
            background: linear-gradient(135deg, #ff7a8b, #e11d48);
            margin: 2rem auto;
            cursor: pointer;
            clip-path: path('M60 105 L10 55 A25 25 0 1 1 60 30 A25 25 0 1 1 110 55 Z');
            transition: transform 0.3s ease, filter 0.3s ease;
            filter: drop-shadow(0 10px 30px rgba(220, 38, 38, 0.4));
        }}

        .letter-heart:hover {{
            transform: scale(1.1);
            filter: drop-shadow(0 15px 40px rgba(220, 38, 38, 0.5));
        }}

        .letter-content {{
            display: none;
            background: white;
            border-radius: var(--radius-lg);
            padding: 2.5rem;
            max-width: 600px;
            margin: 2rem auto;
            box-shadow: var(--shadow-soft);
            text-align: left;
        }}

        .letter-content.show {{
            display: block;
            animation: fadeIn 0.5s ease;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .letter-greeting {{
            font-size: 1.3rem;
            color: #be185d;
            font-weight: 600;
            margin-bottom: 1rem;
        }}

        .letter-text {{
            color: #4b5563;
            line-height: 1.8;
            font-size: 1rem;
        }}

        .letter-signature {{
            margin-top: 1.5rem;
            text-align: right;
            color: #ec4899;
            font-style: italic;
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .hero {{ padding: 2rem 1rem; }}
            .hero-title {{ font-size: 2rem; }}
            .cards {{ grid-template-columns: 1fr; }}
            .stats-grid {{ grid-template-columns: 1fr; }}
            .timeline::before {{ left: 20px; }}
            .timeline-item {{
                width: calc(100% - 3rem);
                margin-left: 3rem !important;
            }}
            .timeline-item::before {{
                left: -15px !important;
                right: auto !important;
            }}
        }}

        /* Emoji styles */
        .emoji-love {{ font-size: 1.2rem; }}
        .emoji-highlight {{ color: #ec4899; }}

        /* Special moments styling */
        .moment-card {{
            background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 100%);
            border: 2px solid #f9a8d4;
        }}

        .moment-card .big {{
            color: #ec4899;
        }}
    </style>
</head>
<body>
    <!-- Splash Screen -->
    <div id="splash">
        <div class="splash-content">
            <div class="heart-container">
                <div class="heart-big"></div>
            </div>
            <div class="splash-text">Dashboard del Amor</div>
            <div class="splash-names">{author1} & {author2} 💕</div>
        </div>
    </div>

    <!-- Hero Section -->
    <header class="hero">
        <div class="hero-badge">✨ Historia de Amor ✨</div>
        <h1 class="hero-title">{author1} & {author2}</h1>
        <div class="hero-heart">💕</div>
        <p class="hero-subtitle">
            Cada mensaje es una prueba de amor. Cada risa, un momento compartido. 
            Esta es la historia de dos corazones que se encontraron.
        </p>
        <div class="hero-meta">
            <span>💬 {total_messages} mensajes de amor</span>
            <span>📅 Desde {first_date_str}</span>
            <span>❤️ Construyendo juntos</span>
        </div>
    </header>

    <div class="container">
        <!-- Love Score -->
        <section class="love-score-section">
            <div class="love-score-emoji">{score_emoji}</div>
            <div class="love-score-number">{love_score}/100</div>
            <div class="love-score-label">{score_label}</div>
            <div class="love-score-bar">
                <div class="love-score-fill" style="width: {love_score}%"></div>
            </div>
        </section>

        <!-- Main Stats Cards -->
        <section class="cards">
            <div class="card moment-card">
                <div class="card-icon">💬</div>
                <h2>Mensajes Totales</h2>
                <div class="big">{total_messages}</div>
                <small>Cada uno cuenta una historia de amor</small>
            </div>
            <div class="card">
                <div class="card-icon">👩</div>
                <h2>Mensajes de {author1}</h2>
                <div class="big">{messages_a1}</div>
                <small>Su voz en esta historia</small>
            </div>
            <div class="card">
                <div class="card-icon">👨</div>
                <h2>Mensajes de {author2}</h2>
                <div class="big">{messages_a2}</div>
                <small>Su voz en esta historia</small>
            </div>
            <div class="card">
                <div class="card-icon">📅</div>
                <h2>Comenzó el</h2>
                <div class="big" style="font-size: 1.5rem;">{first_date_str}</div>
                <small>El día que todo comenzó 💕</small>
            </div>
            <div class="card">
                <div class="card-icon">🎯</div>
                <h2>Día más especial</h2>
                <div class="big" style="font-size: 1.5rem;">{top_day_str}</div>
                <small>{stats["top_day_count"]} mensajes de amor ese día</small>
            </div>
            <div class="card">
                <div class="card-icon">🔥</div>
                <h2>Racha de amor</h2>
                <div class="big">{streak_text}</div>
                <small>Días sin dejar de hablarse</small>
            </div>
            <div class="card">
                <div class="card-icon">🎙️</div>
                <h2>Voces compartidas</h2>
                <div class="big">{media["audio_total"]}</div>
                <small>{author1}: {audio_a1} | {author2}: {audio_a2}</small>
            </div>
            <div class="card">
                <div class="card-icon">📸</div>
                <h2>Fotos compartidas</h2>
                <div class="big">{media["photo_total"]}</div>
                <small>Momentos capturados juntos</small>
            </div>
            <div class="card">
                <div class="card-icon">🌙</div>
                <h2>Noches de desvelo</h2>
                <div class="big">{night_total}</div>
                <small>Mensajes entre medianoche y dawn</small>
            </div>
            <div class="card">
                <div class="card-icon">😂</div>
                <h2>Risas compartidas</h2>
                <div class="big">{sum(laugh_by_author.values())}</div>
                <small>{author1}: {laugh_by_author.get(author1, 0)} | {author2}: {laugh_by_author.get(author2, 0)}</small>
            </div>
        </section>

        <!-- Love Stats Section -->
        <section class="section">
            <div class="section-header">
                <h2 class="section-title">💕 Palabras de Amor</h2>
                <p class="section-subtitle">Las expresiones de cariño más usadas en su historia</p>
            </div>
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>❤️ Amorómetro</h3>
                    <ul>
                        {love_list_html}
                    </ul>
                </div>
                <div class="stat-card">
                    <h3>💌 "Te Quiero"</h3>
                    <ul>
                        {teq_list_html}
                    </ul>
                </div>
                <div class="stat-card">
                    <h3>💖 "Te Amo"</h3>
                    <ul>
                        {tamo_list_html}
                    </ul>
                </div>
                <div class="stat-card">
                    <h3>🌟 Palabras Dulces</h3>
                    <ul>
                        {sweet_list_html}
                    </ul>
                </div>
            </div>
        </section>

        <!-- Special Moments -->
        <section class="section">
            <div class="section-header">
                <h2 class="section-title">✨ Momentos Especiales</h2>
                <p class="section-subtitle">Hitos importantes en su historia de amor</p>
            </div>
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>💕 Primer "Te Quiero"</h3>
                    {first_love_html}
                </div>
                <div class="stat-card">
                    <h3>❤️ Primer "Te Amo"</h3>
                    {first_tamo_html}
                </div>
                <div class="stat-card">
                    <h3>🌹 Primer Momento Especial</h3>
                    {first_meet_html}
                </div>
                <div class="stat-card">
                    <h3>💪 Muestras de Cuidado</h3>
                    <ul>
                        {care_list_html}
                    </ul>
                </div>
            </div>
        </section>

        <!-- Charts -->
        <section class="section">
            <div class="section-header">
                <h2 class="section-title">📊 Evolución de su Historia</h2>
                <p class="section-subtitle">Cómo ha crecido su amor mes a mes</p>
            </div>
            <canvas id="mensajesMesChart" height="100"></canvas>
        </section>

        <section class="section">
            <div class="section-header">
                <h2 class="section-title">⏰ Ritmo del Amor</h2>
                <p class="section-subtitle">Las horas en que más se buscan</p>
            </div>
            <canvas id="mensajesHoraChart" height="100"></canvas>
        </section>

        <!-- Word Cloud -->
        <section class="section">
            <div class="section-header">
                <h2 class="section-title">💭 Su Diccionario del Amor</h2>
                <p class="section-subtitle">Las palabras que más usan cuando están juntos</p>
            </div>
            <div id="wordcloud"></div>
        </section>

        <!-- Response Time -->
        <section class="section">
            <div class="section-header">
                <h2 class="section-title">💫 Tiempo de Respuesta</h2>
                <p class="section-subtitle">Lo rápido que se buscan el uno al otro</p>
            </div>
            <div class="stats-grid">
                <div class="stat-card" style="grid-column: 1 / -1;">
                    <ul>
                        {resp_html}
                    </ul>
                </div>
            </div>
        </section>

        <!-- Letter Section -->
        <section class="letter-section">
            <div class="section-header">
                <h2 class="section-title">💌 Una Carta de Amor</h2>
                <p class="section-subtitle">Toca el corazón para leer una carta especial</p>
            </div>
            <div class="letter-heart" id="letterTrigger" onclick="toggleLetter()"></div>
            <div class="letter-content" id="letterContent">
                <p class="letter-greeting">Querida {author1},</p>
                <p class="letter-text">
                    Desde que nuestros caminos se cruzaron, cada día se ha llenado de momentos que no sabía que necesitaba. 
                    Tu risa es mi melodía favorita, tus mensajes mi mejor礼物, y tu presencia el lugar donde encuentro paz.
                    <br><br>
                    No importa cuántas palabras use, nunca serán suficientes para describir lo que siento. 
                    Solo sé que cada "buenos días" tuyo ilumina mi mañana, y cada "buenas noches" me llena de sueños bonitos.
                    <br><br>
                    Gracias por ser tú, por quedarte, por elegirme cada día. 
                    Este dashboard es solo una pequeña muestra de todo el amor que se esconde en cada mensaje que intercambiamos.
                    <br><br>
                    Te amo más de lo que las palabras pueden decir. 💕
                </p>
                <p class="letter-signature">
                    Con todo mi amor,<br>
                    {author2} ❤️
                </p>
            </div>
        </section>
    </div>

    <footer>
        <div class="footer-hearts">💕 💖 💗 💝 💘</div>
        <p class="footer-text">Hecho con amor para {author1} & {author2}</p>
        <p class="footer-subtext">Porque cada mensaje es una prueba de amor</p>
    </footer>

    <script>
        // Hide splash after 2.5 seconds
        setTimeout(() => {{
            const splash = document.getElementById('splash');
            splash.style.opacity = '0';
            setTimeout(() => splash.style.display = 'none', 800);
        }}, 2500);

        // Toggle letter
        function toggleLetter() {{
            const letter = document.getElementById('letterContent');
            letter.classList.toggle('show');
        }}

        // Messages per month chart
        const labelsMes = {labels_js};
        const dataAuthor1 = {data_a1_js};
        const dataAuthor2 = {data_a2_js};

        new Chart(document.getElementById('mensajesMesChart'), {{
            type: 'line',
            data: {{
                labels: labelsMes,
                datasets: [
                    {{
                        label: '{author1}',
                        data: dataAuthor1,
                        borderColor: '#ec4899',
                        backgroundColor: 'rgba(236, 72, 153, 0.1)',
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 8
                    }},
                    {{
                        label: '{author2}',
                        data: dataAuthor2,
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        tension: 0.4,
                        fill: true,
                        pointRadius: 5,
                        pointHoverRadius: 8
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: true, position: 'top' }},
                }},
                scales: {{
                    y: {{ beginAtZero: true }}
                }}
            }}
        }});

        // Messages per hour chart
        const labelsHora = {hours_js};
        const dataHora = {hour_counts_js};

        new Chart(document.getElementById('mensajesHoraChart'), {{
            type: 'bar',
            data: {{
                labels: labelsHora.map(h => h + ':00'),
                datasets: [{{
                    label: 'Mensajes',
                    data: dataHora,
                    backgroundColor: (context) => {{
                        const gradient = context.chart.ctx.createLinearGradient(0, 0, 0, 300);
                        gradient.addColorStop(0, 'rgba(236, 72, 153, 0.8)');
                        gradient.addColorStop(1, 'rgba(244, 114, 182, 0.3)');
                        return gradient;
                    }},
                    borderRadius: 8,
                    borderSkipped: false
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{ beginAtZero: true }}
                }}
            }}
        }});

        // Word Cloud
        const wcData = {wordcloud_js};
        (function() {{
            const el = document.getElementById("wordcloud");
            if (!el || !wcData.length) return;
            
            const w = el.clientWidth || 800;
            const h = 400;
            const max = Math.max(...wcData.map(x => x.count));

            d3.layout.cloud()
                .size([w, h])
                .words(wcData.map(d => ({{
                    text: d.word,
                    size: 14 + (d.count / max) * 36,
                    count: d.count
                }})))
                .padding(5)
                .rotate(() => Math.random() > 0.7 ? 90 : 0)
                .font("Segoe UI")
                .fontSize(d => d.size)
                .on("end", draw)
                .start();

            function draw(words) {{
                const svg = d3.select("#wordcloud")
                    .append("svg")
                    .attr("width", w)
                    .attr("height", h)
                    .append("g")
                    .attr("transform", `translate(${{w/2}},${{h/2}})`);

                svg.selectAll("text")
                    .data(words)
                    .enter()
                    .append("text")
                    .style("font-size", d => d.size + "px")
                    .style("font-weight", "600")
                    .style("fill", (d, i) => ['#ec4899', '#db2777', '#be185d', '#8b5cf6', '#7c3aed'][i % 5])
                    .style("cursor", "pointer")
                    .style("transition", "transform 0.2s")
                    .attr("text-anchor", "middle")
                    .attr("transform", d => `translate(${{d.x}},${{d.y}}) rotate(${{d.rotate}})`)
                    .text(d => d.text)
                    .on("mouseover", function() {{
                        d3.select(this).style("transform", "scale(1.2)");
                    }})
                    .on("mouseout", function() {{
                        d3.select(this).style("transform", "scale(1)");
                    }});
            }}
        }})();
    </script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_template)


def main():
    if len(sys.argv) < 2:
        print("💕 Dashboard del Amor - Rena & Sebas")
        print("Uso: python dashboard_amor.py chat.txt")
        print("")
        print("Genera un dashboard HTML con análisis romántico del chat")
        sys.exit(1)

    chat_file = sys.argv[1]

    if not os.path.exists(chat_file):
        print(f"❌ Archivo no encontrado: {chat_file}")
        sys.exit(1)

    print("💕 Cargando mensajes de amor...")
    messages = parse_chat(chat_file)
    print(f"   {len(messages)} mensajes de amor cargados 💕")

    print("📊 Calculando estadísticas...")
    stats = basic_stats(messages)
    media = media_stats(messages)
    love_data = love_stats(messages)
    greetings_data = greetings_stats(messages)
    care_data = care_stats(messages)
    excitement_data = excitement_stats(messages)
    laugh_data = laugh_stats(messages)
    sweet_data = sweet_words_stats(messages)
    dates_data = dates_planned_stats(messages)
    meet_data = first_meet_stats(messages)
    compliments_data = compliments_stats(messages)
    support_data = support_emoji_stats(messages)
    night_data = night_messages(messages)
    late_data = late_evening(messages)
    top_words_list = top_words(messages)
    streak_info = longest_streak(stats["by_day"])
    resp_stats = response_stats(messages)
    participants = stats["by_author"].keys()

    output_html = "dashboard_amor_historia.html"
    
    print("💕 Generando dashboard del amor...")
    generate_html(
        output_html, stats, media, love_data, greetings_data, care_data,
        excitement_data, laugh_data, sweet_data, dates_data, meet_data,
        compliments_data, support_data, night_data, late_data,
        top_words_list, streak_info, resp_stats, participants
    )

    print("")
    print("✨ ¡Dashboard del amor generado! ✨")
    print(f"   📁 Archivo: {output_html}")
    print("")
    print("💕 Ábrelo en tu navegador para ver su historia de amor 💕")
    print("")
    
    love_score = calculate_love_score(stats, love_data, media, care_data)
    print(f"📈 Puntuación de amor: {love_score}/100")
    print(f"   {stats['total_messages']} mensajes de amor")
    print(f"   {sum(love_data[0].values())} palabras de cariño")


if __name__ == "__main__":
    main()
