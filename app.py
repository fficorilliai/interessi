import html
import io
import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import streamlit as st
from PIL import Image, ImageOps
from supabase import create_client

# ---------------------------------------------------------------- config
APP_TITLE = "Interessi"  # cambia qui il nome dell'app
APP_ICON = "📌"  # icona della scheda del browser

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="centered")

WHO = ["Emma", "Fede", "Entrambi"]
WHO_ICON = {"Emma": "💗", "Fede": "💙", "Entrambi": "💜"}
WHO_COLOR = {"Emma": "#c2456b", "Fede": "#3a6ea5", "Entrambi": "#6b4fb3"}
BUCKET = "photos"

TZ = ZoneInfo("Europe/Rome")  # tutti gli orari degli eventi sono ora italiana
ICS_FILE = "interessi.ics"
ALERTS = [("-P1D", "Tra 24 ore"), ("-PT1H", "Tra 1 ora")]  # avvisi nel calendario
DAYS_IT = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
MONTHS_IT = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
             "agosto", "settembre", "ottobre", "novembre", "dicembre"]

# Metti True per riattivare le foto sugli elementi (le categorie le hanno sempre)
SHOW_ITEM_PHOTOS = False

CSS = """
<style>
.stApp { background:#faf6f0; }
.block-container { padding: 4rem 0.9rem 4rem; max-width: 640px; }
h1, h2, h3 { letter-spacing: -0.02em; }
div.stButton > button {
    width: 100%; text-align: left; justify-content: flex-start;
    background:#fffdf9; border:1px solid #e0d5c5; border-radius:14px;
    padding: .85rem 1rem; color:#2b2622; min-height: 3.2rem;
}
div.stButton > button:hover { border-color:#c8553d; color:#c8553d; }
div[data-testid="stImage"] img { border-radius:12px; object-fit:cover; }
div[data-testid="stColumn"] div[data-testid="stImage"] img {
    width:100%; height:auto; aspect-ratio:1/1; object-fit:cover;
}
/* righe delle categorie in home: sempre affiancate, anche su telefono */
.st-key-catlist [data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important; gap: .75rem !important; align-items: center;
}
.st-key-catlist [data-testid="stColumn"] { min-width: 0 !important; }
.st-key-catlist [data-testid="stColumn"]:first-child { flex: 0 0 64px !important; width: 64px !important; }
.st-key-catlist [data-testid="stColumn"]:last-child { flex: 1 1 auto !important; width: auto !important; }
/* lista pulita degli elementi */
.st-key-itemlist [data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important; gap: .5rem !important;
    align-items: center; border-top: 1px solid #e8dfd2;
}
.st-key-itemlist [data-testid="stColumn"] { min-width: 0 !important; }
.st-key-itemlist [data-testid="stColumn"] [data-testid="stVerticalBlock"] { gap: 0 !important; }
.st-key-itemlist, .st-key-eventlist { gap: 0 !important; }
.st-key-itemlist [data-testid="stMarkdownContainer"], .st-key-eventlist [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
.st-key-itemlist [data-testid="stColumn"]:first-child { flex: 1 1 auto !important; width: auto !important; }
.st-key-itemlist [data-testid="stColumn"]:last-child { flex: 0 0 auto !important; width: auto !important; }
.st-key-itemlist div.stButton > button {
    background: transparent; border: none; border-radius: 0;
    padding: .8rem 0; min-height: 0; font-size: 1rem;
}
.st-key-itemlist div.stButton > button:hover { color:#c8553d; background: transparent; }
/* interruttore Liste / Programma a tutta larghezza */
.st-key-sectionbar [data-testid="stElementContainer"],
.st-key-sectionbar [data-testid="stButtonGroup"],
.st-key-sectionbar [data-testid="stButtonGroup"] > div { width: 100% !important; max-width: none !important; }
.st-key-sectionbar [data-testid="stButtonGroup"] > div { display: flex; }
.st-key-sectionbar button { flex: 1 1 0 !important; justify-content: center; padding: .55rem 0; }
.st-key-sectionbar button[aria-checked="true"] { background:#c8553d !important; color:#fff; border-color:#c8553d !important; }
.st-key-sectionbar button[aria-checked="true"] * { color:#fff !important; }
/* ora di inizio e fine sempre affiancate */
[class*="st-key-timepair"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .6rem !important; }
[class*="st-key-timepair"] [data-testid="stColumn"] { min-width: 0 !important; }
/* lista del programma: ora | titolo | etichetta */
.st-key-eventlist [data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important; gap: .6rem !important;
    align-items: center; border-top: 1px solid #e8dfd2; padding: .25rem 0;
}
.st-key-eventlist [data-testid="stColumn"] { min-width: 0 !important; }
.st-key-eventlist [data-testid="stColumn"]:first-child { flex: 0 0 3.4rem !important; width: 3.4rem !important; }
.st-key-eventlist [data-testid="stColumn"]:nth-child(2) { flex: 1 1 0 !important; width: auto !important; }
.st-key-eventlist [data-testid="stColumn"]:last-child { flex: 0 0 auto !important; width: auto !important; }
.st-key-eventlist div.stButton > button {
    background: transparent; border: none; border-radius: 0;
    padding: .5rem 0 .1rem; min-height: 0; font-size: 1rem;
}
.st-key-eventlist div.stButton > button:hover { color:#c8553d; background: transparent; }
.st-key-eventlist [data-testid="stColumn"] [data-testid="stVerticalBlock"] { gap: 0 !important; }
.evtime { font-size:.85rem; line-height:1.35; color:#2b2622; }
.evtime span { color:#8a7f73; }
.place { color:#8a7f73; font-size:.8rem; margin-top:-.1rem; padding-bottom:.5rem; }
.dayhead { color:#8a7f73; font-size:.8rem; margin:1.1rem 0 .2rem; }
.tag { font-size:.85rem; white-space:nowrap; text-align:right; }
.count { color:#8a7f73; font-size:.9rem; margin:-0.4rem 0 .8rem; }
.badge { display:inline-block; padding:.15rem .6rem; border-radius:999px;
         font-size:.8rem; background:#efe6d8; color:#5a4f44; }
.muted { color:#8a7f73; font-size:.85rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def esc(text) -> str:
    """Protegge il simbolo $ (altrimenti Streamlit lo legge come formula LaTeX)."""
    return str(text or "").replace("$", "\\$")


# ---------------------------------------------------------------- password
def check_password() -> bool:
    pwd = st.secrets.get("APP_PASSWORD")
    if not pwd or st.session_state.get("auth"):
        return True
    st.title(APP_TITLE)
    entered = st.text_input("Password", type="password")
    if entered:
        if entered == pwd:
            st.session_state["auth"] = True
            st.rerun()
        else:
            st.error("Password sbagliata")
    return False


if not check_password():
    st.stop()


# ---------------------------------------------------------------- database
@st.cache_resource
def get_client():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


# Le funzioni cache NON catturano gli errori: se Supabase fallisce, l'errore
# non viene memorizzato e al prossimo tentativo si riprova da capo.
@st.cache_data(ttl=300, show_spinner=False)
def load_categories():
    return get_client().table("categories").select("*").order("name").execute().data


@st.cache_data(ttl=300, show_spinner=False)
def load_items():
    return (
        get_client().table("items").select("*").order("created_at", desc=True).execute().data
    )


@st.cache_data(ttl=300, show_spinner=False)
def load_events():
    return (
        get_client().table("events").select("*")
        .order("event_date").order("start_time").execute().data
    )


def refresh():
    load_categories.clear()
    load_items.clear()
    load_events.clear()


def safe_load():
    try:
        return load_categories(), load_items()
    except Exception as e:  # mostrato qui, fuori dalla cache
        st.error(f"Non riesco a collegarmi al database: {e}")
        if st.button("Riprova"):
            st.rerun()
        st.stop()


def prepare_photo(uploaded) -> bytes:
    """Ridimensiona e comprime la foto (max 1200px, JPEG)."""
    img = Image.open(uploaded)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((1200, 1200))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=82, optimize=True)
    return buf.getvalue()


def upload_photo(uploaded, folder: str):
    """Ritorna (url, path) oppure (None, None)."""
    if uploaded is None:
        return None, None
    path = f"{folder}/{uuid.uuid4().hex}.jpg"
    store = get_client().storage.from_(BUCKET)
    store.upload(path, prepare_photo(uploaded), {"content-type": "image/jpeg"})
    return store.get_public_url(path), path


def remove_photo(path):
    if path:
        try:
            get_client().storage.from_(BUCKET).remove([path])
        except Exception:
            pass


# ---------------------------------------------------------------- stato
st.session_state.setdefault("cat_id", None)
st.session_state.setdefault("who_pill", "Tutti")

categories, items = safe_load()
cat_by_id = {c["id"]: c for c in categories}


# ---------------------------------------------------------------- dialog elemento
@st.dialog("Dettaglio")
def item_dialog(item_id: int):
    item = next((i for i in load_items() if i["id"] == item_id), None)
    if not item:
        st.info("Elemento non trovato.")
        return
    if SHOW_ITEM_PHOTOS and item.get("photo_url"):
        st.image(item["photo_url"], use_container_width=True)
    st.subheader(esc(item["name"]))
    st.markdown(
        f'<span class="badge">{WHO_ICON[item["liked_by"]]} {item["liked_by"]}</span>',
        unsafe_allow_html=True,
    )
    if item.get("notes"):
        st.markdown(esc(item["notes"]))

    with st.expander("✏️ Modifica"):
        with st.form(f"edit_{item_id}"):
            name = st.text_input("Nome", item["name"])
            who = st.radio(
                "A chi piace?", WHO, index=WHO.index(item["liked_by"]), horizontal=True
            )
            notes = st.text_area("Note", item.get("notes") or "")
            new_photo, drop_photo = None, False
            if SHOW_ITEM_PHOTOS:
                new_photo = st.file_uploader("Cambia foto", type=["jpg", "jpeg", "png", "webp"])
                if item.get("photo_url"):
                    drop_photo = st.checkbox("Rimuovi la foto attuale")
            if st.form_submit_button("Salva", use_container_width=True):
                try:
                    data = {"name": name.strip(), "liked_by": who, "notes": notes.strip()}
                    if new_photo:
                        url, path = upload_photo(new_photo, "items")
                        remove_photo(item.get("photo_path"))
                        data.update(photo_url=url, photo_path=path)
                    elif drop_photo:
                        remove_photo(item.get("photo_path"))
                        data.update(photo_url=None, photo_path=None)
                    get_client().table("items").update(data).eq("id", item_id).execute()
                    refresh()
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore nel salvataggio: {e}")

    confirm = st.checkbox("Sì, voglio eliminarlo", key=f"del_ok_{item_id}")
    if st.button("🗑️ Elimina", disabled=not confirm, key=f"del_{item_id}"):
        try:
            remove_photo(item.get("photo_path"))
            get_client().table("items").delete().eq("id", item_id).execute()
            refresh()
            st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")


# ---------------------------------------------------------------- HOME
def home():
    with st.expander("➕ Nuova categoria"):
        with st.form("new_cat", clear_on_submit=True):
            c1, c2 = st.columns([1, 3])
            emoji = c1.text_input("Emoji", "🎬", max_chars=4)
            name = c2.text_input("Nome (es. Film, Vini, Cartoni)")
            cover = st.file_uploader("Foto copertina (facoltativa)", type=["jpg", "jpeg", "png", "webp"])
            if st.form_submit_button("Crea categoria", use_container_width=True):
                if not name.strip():
                    st.warning("Serve un nome.")
                else:
                    try:
                        url, path = upload_photo(cover, "categories")
                        get_client().table("categories").insert(
                            {"name": name.strip(), "emoji": emoji.strip() or "📁",
                             "cover_url": url, "cover_path": path}
                        ).execute()
                        refresh()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Non sono riuscito a creare la categoria: {e}")

    if not categories:
        st.info("Nessuna categoria ancora. Creane una qui sopra!")
        return

    with st.container(key="catlist"):
        for c in categories:
            n = sum(1 for i in items if i["category_id"] == c["id"])
            col_img, col_btn = st.columns([1, 4], vertical_alignment="center")
            if c.get("cover_url"):
                col_img.image(c["cover_url"], use_container_width=True)
            else:
                col_img.markdown(f"<div style='font-size:2.2rem;text-align:center'>{c['emoji']}</div>",
                                 unsafe_allow_html=True)
            if col_btn.button(f"{esc(c['name'])}  ·  {n}", key=f"cat_{c['id']}"):
                st.session_state.cat_id = c["id"]
                st.session_state["who_pill"] = "Tutti"
                st.rerun()


# ---------------------------------------------------------------- CATEGORIA
def category_page(cat):
    if st.button("← Tutte le categorie", key="back"):
        st.session_state.cat_id = None
        st.rerun()

    in_cat = [i for i in items if i["category_id"] == cat["id"]]
    st.title(f"{cat['emoji']} {esc(cat['name'])}")
    st.markdown(f'<div class="count">{len(in_cat)} elementi</div>', unsafe_allow_html=True)

    with st.expander("➕ Aggiungi elemento"):
        with st.form("new_item", clear_on_submit=True):
            name = st.text_input("Nome")
            who = st.radio("A chi piace?", WHO, horizontal=True)
            notes = st.text_area("Note (facoltative)", height=80)
            photo = None
            if SHOW_ITEM_PHOTOS:
                photo = st.file_uploader("Foto (facoltativa)", type=["jpg", "jpeg", "png", "webp"])
            if st.form_submit_button("Aggiungi", use_container_width=True):
                if not name.strip():
                    st.warning("Serve un nome.")
                else:
                    try:
                        url, path = upload_photo(photo, "items")
                        get_client().table("items").insert(
                            {"category_id": cat["id"], "name": name.strip(), "liked_by": who,
                             "notes": notes.strip(), "photo_url": url, "photo_path": path}
                        ).execute()
                        refresh()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Non sono riuscito a salvare: {e}")

    choice = st.pills("Filtra", ["Tutti"] + WHO, key="who_pill",
                      selection_mode="single", label_visibility="collapsed") or "Tutti"

    rows = in_cat if choice == "Tutti" else [i for i in in_cat if i["liked_by"] == choice]

    if not rows:
        st.info("Niente qui per ora.")
    with st.container(key="itemlist"):
        for i in rows:
            col_name, col_tag = st.columns([5, 2], vertical_alignment="center")
            if col_name.button(esc(i["name"]), key=f"it_{i['id']}"):
                item_dialog(i["id"])
            col_tag.markdown(
                f'<div class="tag" style="color:{WHO_COLOR[i["liked_by"]]}">{i["liked_by"]}</div>',
                unsafe_allow_html=True,
            )

    st.divider()
    with st.expander("⚙️ Impostazioni categoria"):
        with st.form("edit_cat"):
            c1, c2 = st.columns([1, 3])
            new_emoji = c1.text_input("Emoji", cat["emoji"], max_chars=4)
            new_name = c2.text_input("Nome", cat["name"])
            if cat.get("cover_url"):
                st.image(cat["cover_url"], width=120)
            new_cover = st.file_uploader("Cambia foto copertina", type=["jpg", "jpeg", "png", "webp"])
            drop_cover = False
            if cat.get("cover_url"):
                drop_cover = st.checkbox("Rimuovi la foto di copertina")
            if st.form_submit_button("Salva modifiche", use_container_width=True):
                if not new_name.strip():
                    st.warning("Serve un nome.")
                else:
                    try:
                        data = {"name": new_name.strip(), "emoji": new_emoji.strip() or "📁"}
                        if new_cover:
                            url, path = upload_photo(new_cover, "categories")
                            remove_photo(cat.get("cover_path"))
                            data.update(cover_url=url, cover_path=path)
                        elif drop_cover:
                            remove_photo(cat.get("cover_path"))
                            data.update(cover_url=None, cover_path=None)
                        get_client().table("categories").update(data).eq("id", cat["id"]).execute()
                        refresh()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Non sono riuscito a salvare: {e}")

        confirm = st.checkbox("Elimina questa categoria e tutto quello che contiene", key="cat_del_ok")
        if st.button("🗑️ Elimina categoria", disabled=not confirm):
            try:
                for i in in_cat:
                    remove_photo(i.get("photo_path"))
                remove_photo(cat.get("cover_path"))
                get_client().table("categories").delete().eq("id", cat["id"]).execute()
                st.session_state.cat_id = None
                refresh()
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")


# ---------------------------------------------------------------- PROGRAMMA
VTIMEZONE = [
    "BEGIN:VTIMEZONE", "TZID:Europe/Rome",
    "BEGIN:DAYLIGHT", "TZOFFSETFROM:+0100", "TZOFFSETTO:+0200", "TZNAME:CEST",
    "DTSTART:19700329T020000", "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU", "END:DAYLIGHT",
    "BEGIN:STANDARD", "TZOFFSETFROM:+0200", "TZOFFSETTO:+0100", "TZNAME:CET",
    "DTSTART:19701025T030000", "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU", "END:STANDARD",
    "END:VTIMEZONE",
]


def ev_start(e) -> datetime:
    return datetime.combine(date.fromisoformat(e["event_date"]),
                            time.fromisoformat(e["start_time"]), tzinfo=TZ)


def ev_end(e) -> datetime:
    return datetime.combine(date.fromisoformat(e["event_date"]),
                            time.fromisoformat(e["end_time"]), tzinfo=TZ)


def future_events(events):
    """Solo gli eventi non ancora finiti (l'ora attuale è calcolata ogni volta)."""
    now = datetime.now(TZ)
    return [e for e in events if ev_end(e) >= now]


def fmt_day(d: date) -> str:
    return f"{DAYS_IT[d.weekday()]} {d.day} {MONTHS_IT[d.month - 1]}"


def _ics_escape(text) -> str:
    return (str(text or "").replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\r", "").replace("\n", "\\n"))


def _ics_fold(line: str) -> bytes:
    """Le righe di un file .ics non possono superare 75 byte: vanno spezzate."""
    raw = line.encode("utf-8")
    out = []
    while len(raw) > 75:
        cut = 75
        while cut > 0 and (raw[cut] & 0xC0) == 0x80:  # non spezzare un carattere
            cut -= 1
        out.append(raw[:cut])
        raw = b" " + raw[cut:]
    out.append(raw)
    return b"\r\n".join(out)


def _parse_ts(value) -> datetime:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def build_ics(events) -> bytes:
    """File calendario con tutti gli eventi. L'UID fisso permette al calendario di
    aggiornare un evento già importato invece di duplicarlo; SEQUENCE cresce
    solo quando l'evento viene modificato."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Interessi//IT",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH", *VTIMEZONE]
    for e in events:
        upd = _parse_ts(e.get("updated_at") or e.get("created_at"))
        lines += [
            "BEGIN:VEVENT",
            f"UID:{e['uid']}@interessi",
            f"DTSTAMP:{stamp}",
            f"LAST-MODIFIED:{upd.strftime('%Y%m%dT%H%M%SZ')}",
            f"SEQUENCE:{int(upd.timestamp())}",
            f"DTSTART;TZID=Europe/Rome:{ev_start(e).strftime('%Y%m%dT%H%M%S')}",
            f"DTEND;TZID=Europe/Rome:{ev_end(e).strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{_ics_escape(e['title'])}",
        ]
        if e.get("place"):
            lines.append(f"LOCATION:{_ics_escape(e['place'])}")
        lines.append(f"DESCRIPTION:{_ics_escape('Per: ' + e['who'])}")
        for trigger, label in ALERTS:
            lines += ["BEGIN:VALARM", "ACTION:DISPLAY",
                      f"DESCRIPTION:{_ics_escape(label + ': ' + e['title'])}",
                      f"TRIGGER:{trigger}", "END:VALARM"]
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return b"\r\n".join(_ics_fold(line) for line in lines) + b"\r\n"


def event_fields(prefix: str, ev=None):
    title = st.text_input("Titolo", ev["title"] if ev else "", key=f"{prefix}_title")
    day = st.date_input("Data", date.fromisoformat(ev["event_date"]) if ev else datetime.now(TZ).date(),
                        format="DD/MM/YYYY", key=f"{prefix}_day")
    with st.container(key=f"timepair_{prefix}"):
        c1, c2 = st.columns(2)
        start = c1.time_input("Inizio", time.fromisoformat(ev["start_time"]) if ev else time(19, 0),
                              step=900, key=f"{prefix}_start")
        end = c2.time_input("Fine", time.fromisoformat(ev["end_time"]) if ev else time(21, 0),
                            step=900, key=f"{prefix}_end")
    place = st.text_input("Luogo (facoltativo)", (ev.get("place") or "") if ev else "",
                          key=f"{prefix}_place")
    who = st.radio("A chi riguarda", WHO, index=WHO.index(ev["who"]) if ev else 2,
                   horizontal=True, key=f"{prefix}_who")
    return title, day, start, end, place, who


def event_error(title, start, end):
    if not title.strip():
        return "Serve un titolo."
    if end <= start:
        return "L'ora di fine deve essere dopo quella di inizio."
    return None


def event_payload(title, day, start, end, place, who) -> dict:
    return {"title": title.strip(), "event_date": day.isoformat(),
            "start_time": start.strftime("%H:%M:%S"), "end_time": end.strftime("%H:%M:%S"),
            "place": place.strip() or None, "who": who}


@st.dialog("Evento")
def event_dialog(event_id: int):
    ev = next((e for e in load_events() if e["id"] == event_id), None)
    if not ev:
        st.info("Evento non trovato.")
        return
    s, f = ev_start(ev), ev_end(ev)
    st.subheader(esc(ev["title"]))
    st.markdown(f"{fmt_day(s.date())}, {s:%H:%M}–{f:%H:%M}")
    if ev.get("place"):
        st.markdown(esc(ev["place"]))
    st.markdown(f'<span class="badge">{WHO_ICON[ev["who"]]} {ev["who"]}</span>',
                unsafe_allow_html=True)

    with st.expander("✏️ Modifica"):
        with st.form(f"evedit_{event_id}"):
            vals = event_fields(f"evedit{event_id}", ev)
            if st.form_submit_button("Salva", use_container_width=True):
                err = event_error(vals[0], vals[2], vals[3])
                if err:
                    st.warning(err)
                else:
                    try:
                        data = event_payload(*vals)
                        data["updated_at"] = datetime.now(timezone.utc).isoformat()
                        get_client().table("events").update(data).eq("id", event_id).execute()
                        refresh()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore nel salvataggio: {e}")

    confirm = st.checkbox("Sì, voglio eliminarlo", key=f"evdel_ok_{event_id}")
    if st.button("🗑️ Elimina", disabled=not confirm, key=f"evdel_{event_id}"):
        try:
            get_client().table("events").delete().eq("id", event_id).execute()
            refresh()
            st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")


def programma():
    try:
        events = load_events()
    except Exception as e:  # tabella mancante o database non raggiungibile
        st.error("Non riesco a leggere gli eventi. Hai eseguito `setup_eventi.sql` su Supabase?")
        st.caption(str(e))
        return

    upcoming = future_events(events)
    if upcoming:
        # Si sceglie una persona: nel file vanno i suoi eventi + quelli "Entrambi".
        # Con l'indirizzo dell'app seguito da ?chi=Emma parte già su Emma.
        start = st.query_params.get("chi", "Fede")
        start = start if start in ("Emma", "Fede") else "Fede"
        chosen = st.pills("Scarica gli eventi di", ["Fede", "Emma"], selection_mode="single",
                          default=start, key="export_who")
        to_export = [e for e in upcoming if e["who"] in (chosen, "Entrambi")] if chosen else []
        if to_export:
            st.download_button("Aggiungi al calendario", data=build_ics(to_export),
                               file_name=ICS_FILE, mime="text/calendar",
                               type="primary", use_container_width=True)
            k, n = len(to_export), len(upcoming)
            word = "evento" if k == 1 else "eventi"
            note = (f"{k} {word} nel file: quelli di {chosen} e quelli di Entrambi"
                    + (f" (su {n} in programma)" if k != n else ""))
        elif chosen:
            note = f"Nessun evento di {chosen} o di Entrambi in programma."
        else:
            note = "Scegli Fede o Emma per scaricare gli eventi."
        st.markdown(f'<div class="count" style="text-align:center;margin-top:.4rem">{note}</div>',
                    unsafe_allow_html=True)
    else:
        st.info("Nessun evento in programma.")

    n_form = st.session_state.setdefault("ev_n", 0)
    with st.expander("➕ Nuovo evento"):
        with st.form("new_event"):
            vals = event_fields(f"new{n_form}")
            if st.form_submit_button("Aggiungi", use_container_width=True, type="primary"):
                err = event_error(vals[0], vals[2], vals[3])
                if err:
                    st.warning(err)
                else:
                    try:
                        get_client().table("events").insert(event_payload(*vals)).execute()
                        st.session_state["ev_n"] = n_form + 1  # svuota il modulo
                        refresh()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Non sono riuscito a salvare: {e}")

    days = {}
    for e in upcoming:
        days.setdefault(e["event_date"], []).append(e)
    with st.container(key="eventlist"):
        for d, evs in days.items():
            st.markdown(f'<div class="dayhead">{fmt_day(date.fromisoformat(d))}</div>',
                        unsafe_allow_html=True)
            for e in evs:
                c_time, c_title, c_tag = st.columns([1, 4, 2], vertical_alignment="center")
                c_time.markdown(
                    f'<div class="evtime">{ev_start(e):%H:%M}<br><span>{ev_end(e):%H:%M}</span></div>',
                    unsafe_allow_html=True)
                if c_title.button(esc(e["title"]), key=f"ev_{e['id']}"):
                    event_dialog(e["id"])
                if e.get("place"):
                    c_title.markdown(f'<div class="place">{html.escape(e["place"])}</div>',
                                     unsafe_allow_html=True)
                c_tag.markdown(
                    f'<div class="tag" style="color:{WHO_COLOR[e["who"]]}">{e["who"]}</div>',
                    unsafe_allow_html=True)


# ---------------------------------------------------------------- routing
def top_bar() -> str:
    st.title(APP_TITLE)
    with st.container(key="sectionbar"):
        section = st.segmented_control("Sezione", ["Liste", "Programma"], key="section",
                                       default="Liste", selection_mode="single",
                                       label_visibility="collapsed")
    return section or "Liste"


current_cat = cat_by_id.get(st.session_state.cat_id)
if current_cat:
    category_page(current_cat)
else:
    st.session_state.cat_id = None
    if top_bar() == "Programma":
        programma()
    else:
        home()
