import io
import uuid

import streamlit as st
from PIL import Image, ImageOps
from supabase import create_client

# ---------------------------------------------------------------- config
st.set_page_config(page_title="Interessi", page_icon="💜", layout="centered")

WHO = ["Emma", "Fede", "Entrambi"]
WHO_ICON = {"Emma": "💗", "Fede": "💙", "Entrambi": "💜"}
BUCKET = "photos"

CSS = """
<style>
.stApp { background:#0e1117; }
.block-container { padding: 1rem 0.9rem 4rem; max-width: 640px; }
h1, h2, h3 { letter-spacing: -0.02em; }
div.stButton > button {
    width: 100%; text-align: left; justify-content: flex-start;
    background:#171b24; border:1px solid #262c3a; border-radius:14px;
    padding: .85rem 1rem; color:#e8eaf0; min-height: 3.2rem;
}
div.stButton > button:hover { border-color:#7c6cf0; color:#fff; }
div[data-testid="stImage"] img { border-radius:12px; object-fit:cover; }
.badge { display:inline-block; padding:.15rem .6rem; border-radius:999px;
         font-size:.8rem; background:#232838; color:#cfd3e0; }
.muted { color:#8b92a5; font-size:.85rem; }
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
    st.title("💜 Interessi")
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


def refresh():
    load_categories.clear()
    load_items.clear()


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
st.session_state.setdefault("who_filter", "Tutti")

categories, items = safe_load()
cat_by_id = {c["id"]: c for c in categories}


# ---------------------------------------------------------------- dialog elemento
@st.dialog("Dettaglio")
def item_dialog(item_id: int):
    item = next((i for i in load_items() if i["id"] == item_id), None)
    if not item:
        st.info("Elemento non trovato.")
        return
    if item.get("photo_url"):
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
            new_photo = st.file_uploader("Cambia foto", type=["jpg", "jpeg", "png", "webp"])
            drop_photo = False
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
    st.title("💜 Interessi")
    st.caption("Le nostre liste: film, vini, cibi e tutto quello che ci piace.")

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
            st.session_state.who_filter = "Tutti"
            st.rerun()


# ---------------------------------------------------------------- CATEGORIA
def category_page(cat):
    if st.button("← Tutte le categorie", key="back"):
        st.session_state.cat_id = None
        st.rerun()

    st.title(f"{cat['emoji']} {esc(cat['name'])}")

    with st.expander("➕ Aggiungi elemento"):
        with st.form("new_item", clear_on_submit=True):
            name = st.text_input("Nome")
            who = st.radio("A chi piace?", WHO, horizontal=True)
            notes = st.text_area("Note (facoltative)")
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

    options = ["Tutti"] + [f"{WHO_ICON[w]} {w}" for w in WHO]
    current = st.session_state.who_filter
    choice = st.radio("Filtra", options, horizontal=True,
                      index=options.index(current) if current in options else 0,
                      label_visibility="collapsed")
    st.session_state.who_filter = choice

    rows = [i for i in items if i["category_id"] == cat["id"]]
    if choice != "Tutti":
        wanted = choice.split(" ", 1)[1]
        rows = [i for i in rows if i["liked_by"] == wanted]

    if not rows:
        st.info("Niente qui per ora.")
    for i in rows:
        col_img, col_btn = st.columns([1, 4], vertical_alignment="center")
        if i.get("photo_url"):
            col_img.image(i["photo_url"], use_container_width=True)
        else:
            col_img.markdown("<div style='font-size:1.8rem;text-align:center'>🖼️</div>",
                             unsafe_allow_html=True)
        if col_btn.button(f"{esc(i['name'])}  ·  {WHO_ICON[i['liked_by']]} {i['liked_by']}",
                          key=f"it_{i['id']}"):
            item_dialog(i["id"])

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
                for i in rows if choice == "Tutti" else [x for x in items if x["category_id"] == cat["id"]]:
                    remove_photo(i.get("photo_path"))
                remove_photo(cat.get("cover_path"))
                get_client().table("categories").delete().eq("id", cat["id"]).execute()
                st.session_state.cat_id = None
                refresh()
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")


# ---------------------------------------------------------------- routing
current_cat = cat_by_id.get(st.session_state.cat_id)
if current_cat:
    category_page(current_cat)
else:
    st.session_state.cat_id = None
    home()
