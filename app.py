import streamlit as st
import base64
import os
from PIL import Image

from utils.auth         import sign_in, sign_up, change_password, update_profile_name
from utils.predictor    import predict_disease, LABELS as MODEL_LABELS
from utils.database     import save_scan_result, fetch_scan_history, delete_scan, get_user_stats, init_db
from utils.i18n         import t, LANGUAGE_OPTIONS
from utils.weather      import get_weather, get_disease_risk
from utils.crop_advisor import get_crop_recommendations, SOIL_OPTIONS, SEASON_OPTIONS, REGION_OPTIONS, WATER_OPTIONS
from utils.schemes      import search_schemes, CATEGORIES
from utils.news         import fetch_agri_news, get_tip_of_day, get_all_tips

# ── Disease metadata ──────────────────────────────────────────────────────────

REMEDIES = {
    "Bacterial Blight": [
        ("Apply Fungicide Immediately",  "Use Streptocycline (0.5 g/L) + Copper Oxychloride (3 g/L) as a protectant spray."),
        ("Remove Infected Foliage",      "Carefully prune and destroy infected leaves to slow spread. Do not compost."),
        ("Avoid Overhead Irrigation",    "Switch to drip irrigation to keep foliage dry. Repeat treatment every 10–14 days."),
    ],
    "Anthracnose": [
        ("Prune Infected Branches",      "Cut 15 cm below visible infection. Destroy removed material immediately."),
        ("Apply Mancozeb Spray",         "Use Mancozeb (2.5 g/L) or Carbendazim (1 g/L) spray during dry weather."),
        ("Improve Air Circulation",      "Ensure adequate spacing between plants to reduce humidity in the canopy."),
    ],
    "Alternaria": [
        ("Improve Field Drainage",       "Prevent waterlogging — Alternaria thrives in wet, humid conditions."),
        ("Apply Iprodione Fungicide",    "Apply Iprodione or Mancozeb at recommended dose on dry foliage."),
        ("Remove Fallen Debris",         "Clear all fallen leaves and plant debris from around the base of the plant."),
    ],
    "Cercospora": [
        ("Apply Copper-Based Fungicide", "Spray Copper Oxychloride (3 g/L) every 10–14 days during humid periods."),
        ("Increase Plant Spacing",       "Improve air circulation by thinning dense canopy to reduce leaf wetness."),
        ("Remove Infected Leaves",       "Prune and destroy leaves showing circular brown spots immediately."),
    ],
    "Healthy": [
        ("Maintain Watering Schedule",   "Regular, consistent watering promotes strong root development."),
        ("Apply Balanced Fertilizer",    "Use balanced NPK fertilization monthly during the growing season."),
        ("Inspect Weekly",               "Early detection is key — inspect leaves weekly for early signs of disease."),
    ],
}

DISEASE_META = {
    "Bacterial Blight": {"color": "#f87171", "icon_bg": "rgba(248,113,113,0.12)", "icon": "🦠", "type": "Bacterial Pathogen",  "severity": "High Risk",   "sev_color": "#f87171", "detected": True},
    "Anthracnose":      {"color": "#f87171", "icon_bg": "rgba(248,113,113,0.12)", "icon": "🍄", "type": "Fungal Pathogen",     "severity": "High Risk",   "sev_color": "#f87171", "detected": True},
    "Alternaria":       {"color": "#fbbf24", "icon_bg": "rgba(251,191,36,0.12)",  "icon": "🌫", "type": "Fungal Infection",    "severity": "Medium Risk", "sev_color": "#fbbf24", "detected": True},
    "Cercospora":       {"color": "#fbbf24", "icon_bg": "rgba(251,191,36,0.12)",  "icon": "🔵", "type": "Fungal Leaf Spot",    "severity": "Medium Risk", "sev_color": "#fbbf24", "detected": True},
    "Healthy":          {"color": "#10b981", "icon_bg": "rgba(16,185,129,0.12)",  "icon": "🌿", "type": "No Disease Detected", "severity": "No Risk",     "sev_color": "#10b981", "detected": False},
    "Invalid Image":    {"color": "#64748b", "icon_bg": "rgba(100,116,139,0.12)", "icon": "❓", "type": "Unrecognized Image",  "severity": "—",           "sev_color": "#64748b", "detected": False},
}

NAV = [
    ("🏠", "nav_dashboard", "dashboard"),
    ("🔬", "nav_scanner",   "scanner"),
    ("📋", "nav_history",   "history"),
    ("🌦️", "nav_weather",   "weather"),
    ("📰", "nav_news",      "news"),
    ("🏛️", "nav_schemes",   "schemes"),
    ("🌱", "nav_crops",     "crops"),
    ("👤", "nav_profile",   "profile"),
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _t(key: str) -> str:
    """Translate key using current session language."""
    return t(key, st.session_state.get("lang", "en"))

@st.cache_data(show_spinner=False)
def _b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def _load_css():
    path = "assets/css/style.css"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def _logo_tag(size: int = 40) -> str:
    path = "assets/images/logo.png"
    if os.path.exists(path):
        return (f'<img src="data:image/png;base64,{_b64(path)}" '
                f'style="width:{size}px;height:{size}px;border-radius:10px;object-fit:cover;">')
    return "🌿"

def _nav_btn(icon: str, label_key: str, key: str, page: str):
    label = _t(label_key)
    if st.session_state.page == page:
        st.markdown('<span class="nav-hint"></span>', unsafe_allow_html=True)
    if st.button(f"{icon}  {label}", key=key, use_container_width=True):
        st.session_state.page = page
        st.rerun()

def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="KrushiAI — Plant Disease Intelligence",
        layout="wide",
        page_icon="🌿",
        initial_sidebar_state="expanded",
    )
    init_db()
    _load_css()

    st.session_state.setdefault("user",         None)
    st.session_state.setdefault("page",         "dashboard")
    st.session_state.setdefault("last_result",  None)
    st.session_state.setdefault("auth_tab",     "login")
    st.session_state.setdefault("lang",         "en")
    st.session_state.setdefault("weather_data", None)

    if not st.session_state.user:
        _page_login()
    else:
        _page_app()

# ── Login ─────────────────────────────────────────────────────────────────────

def _page_login():
    st.markdown("""<style>
    [data-testid="stSidebar"],[data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"]{display:none!important}
    </style>""", unsafe_allow_html=True)

    bg = "assets/images/login_bg.jpg"
    if os.path.exists(bg):
        st.markdown(f"""<style>
        [data-testid="stAppViewContainer"]{{
            background:url("data:image/jpg;base64,{_b64(bg)}")center/cover fixed;
        }}
        [data-testid="stAppViewContainer"]::before{{
            content:'';position:fixed;inset:0;
            background:rgba(4,8,15,0.82);backdrop-filter:blur(3px);z-index:0;
        }}
        [data-testid="stMain"]{{position:relative;z-index:1;}}
        </style>""", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        logo = _logo_tag(56)
        st.markdown(f"""
        <div class="auth-card">
            <div class="auth-brand">
                {logo}
                <div class="auth-brand-text">
                    <h1 class="auth-title">KrushiAI</h1>
                    <p class="auth-sub">Plant Disease Intelligence Platform</p>
                </div>
            </div>
            <div class="auth-divider"></div>""", unsafe_allow_html=True)

        if st.session_state.auth_tab == "login":
            st.markdown(f'<p class="auth-form-title">{_t("welcome_back")}</p>', unsafe_allow_html=True)
            st.markdown(f'<label class="field-label">{_t("email")}</label>', unsafe_allow_html=True)
            email = st.text_input("e1", placeholder="you@example.com", key="li_email", label_visibility="collapsed")
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f'<label class="field-label">{_t("password")}</label>', unsafe_allow_html=True)
            with c2:
                st.markdown('<span class="forgot-link">Forgot?</span>', unsafe_allow_html=True)
            pwd = st.text_input("p1", type="password", placeholder="••••••••", key="li_pwd", label_visibility="collapsed")

            if st.button(_t("sign_in"), use_container_width=True, key="btn_login"):
                if not email or not pwd:
                    st.warning("Please fill in both fields.")
                else:
                    with st.spinner("Signing in…"):
                        res = sign_in(email, pwd)
                    if res:
                        st.session_state.user        = res.user
                        st.session_state.page        = "dashboard"
                        st.session_state.last_result = None
                        st.rerun()

            st.markdown(f'<p class="auth-switch">{_t("no_account")}</p>', unsafe_allow_html=True)
            if st.button(_t("create_free"), use_container_width=True, key="btn_go_signup"):
                st.session_state.auth_tab = "signup"
                st.rerun()

        else:
            st.markdown(f'<p class="auth-form-title">{_t("create_account")}</p>', unsafe_allow_html=True)
            st.markdown(f'<label class="field-label">{_t("full_name")}</label>', unsafe_allow_html=True)
            name  = st.text_input("n2", placeholder="Your full name",     key="su_name",  label_visibility="collapsed")
            st.markdown(f'<label class="field-label">{_t("email")}</label>', unsafe_allow_html=True)
            email = st.text_input("e2", placeholder="you@example.com",    key="su_email", label_visibility="collapsed")
            st.markdown(f'<label class="field-label">{_t("password")}</label>', unsafe_allow_html=True)
            pwd   = st.text_input("p2", type="password", placeholder="Min. 8 characters", key="su_pwd", label_visibility="collapsed")

            if st.button(_t("sign_up"), use_container_width=True, key="btn_signup"):
                if not name or not email or not pwd:
                    st.warning("Please fill in all fields.")
                else:
                    with st.spinner("Creating account…"):
                        ok = sign_up(email, pwd, name)
                    if ok:
                        st.success("Account created! Please sign in.")
                        st.session_state.auth_tab = "login"
                        st.rerun()

            st.markdown(f'<p class="auth-switch">{_t("have_account")}</p>', unsafe_allow_html=True)
            if st.button(_t("sign_in_instead"), use_container_width=True, key="btn_go_login"):
                st.session_state.auth_tab = "login"
                st.rerun()

        st.markdown("""
            <p class="auth-terms">
                By continuing, you agree to our
                <a href="#" class="auth-link">Terms of Service</a> and
                <a href="#" class="auth-link">Privacy Policy</a>.
            </p>
        </div>""", unsafe_allow_html=True)

# ── App shell ─────────────────────────────────────────────────────────────────

def _page_app():
    import streamlit.components.v1 as components
    components.html("""<script>
    (function(){
        function tryOpen(){
            var b=window.parent.document.querySelector('[data-testid="collapsedControl"]');
            if(b)b.click();
        }
        setTimeout(tryOpen,200);setTimeout(tryOpen,700);
    })();
    </script>""", height=0)

    user    = st.session_state.user
    name    = getattr(user, "name", "").strip() or user.email.split("@")[0].title()
    initial = name[0].upper()

    # ── Sidebar ────────────────────────────────────────────────────────────────
    with st.sidebar:
        logo = _logo_tag(36)
        st.markdown(f"""
        <div class="sb-brand">
            {logo}
            <div class="sb-brand-text">
                <span class="sb-name">KrushiAI</span>
                <span class="sb-sub">{_t("tagline")}</span>
            </div>
        </div>""", unsafe_allow_html=True)

        # Language selector
        st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
        lang_labels = list(LANGUAGE_OPTIONS.values())
        lang_keys   = list(LANGUAGE_OPTIONS.keys())
        cur_idx     = lang_keys.index(st.session_state.get("lang", "en"))
        chosen      = st.selectbox(
            _t("language"), lang_labels,
            index=cur_idx, key="lang_select", label_visibility="collapsed"
        )
        new_lang = lang_keys[lang_labels.index(chosen)]
        if new_lang != st.session_state.lang:
            st.session_state.lang = new_lang
            st.rerun()

        st.markdown(f'<p class="sb-section-label">{_t("main_menu")}</p>', unsafe_allow_html=True)
        st.markdown('<div class="nav-section">', unsafe_allow_html=True)
        for icon, label_key, page in NAV:
            _nav_btn(icon, label_key, f"nav_{page}", page)
        st.markdown('</div>', unsafe_allow_html=True)

        # User card
        st.markdown(f"""
        <div class="sb-user-card">
            <div class="sb-user-avatar">{initial}</div>
            <div class="sb-user-info">
                <p class="sb-user-name">{name}</p>
                <p class="sb-user-email">{user.email}</p>
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div class="logout-wrap">', unsafe_allow_html=True)
        if st.button(_t("sign_out"), key="btn_logout", use_container_width=True):
            for k in ["user", "last_result", "page", "auth_tab", "weather_data"]:
                st.session_state.pop(k, None)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Top bar ────────────────────────────────────────────────────────────────
    page = st.session_state.page
    nav_map = {p: (ic, lk) for ic, lk, p in NAV}
    p_icon, p_lkey = nav_map.get(page, ("", "nav_dashboard"))

    st.markdown(f"""
    <header class="top-bar">
        <div class="top-breadcrumb">
            <span class="top-app-name">KrushiAI</span>
            <span class="top-sep">/</span>
            <span class="top-page">{p_icon} {_t(p_lkey)}</span>
        </div>
        <div class="top-right">
            <div class="top-avatar-wrap">
                <div class="top-avatar">{initial}</div>
                <span class="top-name">{name}</span>
            </div>
        </div>
    </header>""", unsafe_allow_html=True)

    # ── Route ──────────────────────────────────────────────────────────────────
    if   page == "dashboard": _tab_dashboard()
    elif page == "scanner":   _tab_scanner()
    elif page == "history":   _tab_history()
    elif page == "weather":   _tab_weather()
    elif page == "news":      _tab_news()
    elif page == "schemes":   _tab_schemes()
    elif page == "crops":     _tab_crops()
    elif page == "profile":   _tab_profile()

# ── Dashboard ─────────────────────────────────────────────────────────────────

def _tab_dashboard():
    user    = st.session_state.user
    name    = getattr(user, "name", "").strip() or user.email.split("@")[0].title()
    stats   = get_user_stats(user.id)
    history = fetch_scan_history(user.id)
    recent  = history[:3]

    st.markdown(f"""
    <div class="page-hero">
        <div class="hero-text">
            <p class="hero-greeting">{_t("good_day")}, {name} 👋</p>
            <h1 class="hero-title">{_t("plant_health_overview")}</h1>
            <p class="hero-sub">{_t("dashboard_sub")}</p>
        </div>
    </div>""", unsafe_allow_html=True)

    total    = stats["total"] or 0
    healthy  = stats["healthy"] or 0
    diseased = stats["diseased"] or 0
    avg_conf = stats["avg_confidence"] or 0
    health_rate = round((healthy / total * 100)) if total else 0

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    for col, label_key, val, color, icon in [
        (c1, "total_scans", str(total),         "#60a5fa", "🔬"),
        (c2, "healthy",     str(healthy),        "#10b981", "🌿"),
        (c3, "diseased",    str(diseased),        "#f87171", "⚠️"),
        (c4, "health_rate", f"{health_rate}%",   "#a78bfa", "📊"),
    ]:
        with col:
            st.markdown(f"""
            <div class="dash-stat-card">
                <div class="dsc-top">
                    <span class="dsc-icon">{icon}</span>
                    <span class="dsc-label">{_t(label_key)}</span>
                </div>
                <p class="dsc-value" style="color:{color}">{val}</p>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
    left, right = st.columns([3, 2], gap="medium")

    with left:
        st.markdown(f'<p class="section-label">{_t("recent_scans")}</p>', unsafe_allow_html=True)
        if not recent:
            st.markdown(f"""
            <div class="empty-card">
                <p class="empty-icon">🔬</p>
                <p class="empty-title">{_t("no_scans_yet")}</p>
                <p class="empty-sub">{_t("no_scans_sub")}</p>
            </div>""", unsafe_allow_html=True)
        else:
            for s in recent:
                lbl  = s["disease_type"]
                conf = s["confidence"]
                date = str(s["created_at"])[5:16]
                meta = DISEASE_META.get(lbl, DISEASE_META["Invalid Image"])
                st.markdown(f"""
                <div class="recent-row">
                    <div class="rr-icon" style="background:{meta['icon_bg']}">{meta['icon']}</div>
                    <div class="rr-info">
                        <p class="rr-name">{lbl}</p>
                        <p class="rr-meta">{meta['type']} · {date}</p>
                    </div>
                    <div class="rr-conf" style="color:{meta['color']}">{conf:.0f}%</div>
                </div>""", unsafe_allow_html=True)

    with right:
        st.markdown(f'<p class="section-label">{_t("quick_actions")}</p>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="qa-card">
            <div class="qa-icon">🔬</div>
            <div>
                <p class="qa-title">{_t("new_scan")}</p>
                <p class="qa-sub">{_t("new_scan_sub")}</p>
            </div>
        </div>""", unsafe_allow_html=True)
        if st.button(_t("start_scanning"), key="dash_scan", use_container_width=True):
            st.session_state.last_result = None
            st.session_state.page = "scanner"
            st.rerun()

        st.markdown(f"""
        <div class="qa-card" style="margin-top:10px">
            <div class="qa-icon">📋</div>
            <div>
                <p class="qa-title">{_t("view_history")}</p>
                <p class="qa-sub">{_t("view_history_sub")}</p>
            </div>
        </div>""", unsafe_allow_html=True)
        if st.button(_t("open_history"), key="dash_hist", use_container_width=True):
            st.session_state.page = "history"
            st.rerun()

# ── Scanner ───────────────────────────────────────────────────────────────────

def _tab_scanner():
    st.markdown(f"""
    <div class="page-hero">
        <div class="hero-text">
            <h1 class="hero-title">{_t("ai_scanner")}</h1>
            <p class="hero-sub">{_t("scanner_sub")}</p>
        </div>
    </div>""", unsafe_allow_html=True)

    left, right = st.columns(2, gap="large")

    with left:
        st.markdown(f'<p class="section-label">{_t("image_input")}</p>', unsafe_allow_html=True)
        tab_upload, tab_camera = st.tabs([_t("upload_file"), _t("camera")])

        img = None; img_source = None

        with tab_upload:
            uploaded = st.file_uploader("leaf", type=["jpg","jpeg","png"], label_visibility="collapsed")
            if uploaded:
                img = Image.open(uploaded); img_source = uploaded.name
                st.image(img, use_container_width=True)
            else:
                st.markdown(f"""
                <div class="upload-zone">
                    <div class="uz-icon">🌿</div>
                    <p class="uz-title">{_t("drop_image")}</p>
                    <p class="uz-hint">{_t("supports")}</p>
                    <p class="uz-hint">{_t("good_lighting")}</p>
                </div>""", unsafe_allow_html=True)

        with tab_camera:
            shot = st.camera_input("capture", label_visibility="collapsed")
            if shot:
                img = Image.open(shot); img_source = "camera"
                st.image(img, use_container_width=True)
            else:
                st.markdown(f"""
                <div class="upload-zone">
                    <div class="uz-icon">📷</div>
                    <p class="uz-title">{_t("allow_camera")}</p>
                    <p class="uz-hint">{_t("camera_hint")}</p>
                </div>""", unsafe_allow_html=True)

        if img:
            if st.button(f"🔬  {_t('analyze_leaf')}", key="btn_analyze", use_container_width=True):
                with st.spinner("Running AI analysis…"):
                    label, conf = predict_disease(img)
                    # Only fetch all-class probs for valid predictions
                    if label != "Invalid Image":
                        from utils.predictor import get_all_probs
                        probs_dict = get_all_probs(img) or {}
                    else:
                        probs_dict = {}
                # Only save valid scans to history
                if label != "Invalid Image":
                    save_scan_result(user_id=st.session_state.user.id,
                                     disease_name=label, confidence=conf, image_name=img_source)
                st.session_state.last_result = {
                    "label": label, "conf": conf,
                    "probs": probs_dict,
                }
                st.rerun()

    with right:
        st.markdown(f'<p class="section-label">{_t("analysis_result")}</p>', unsafe_allow_html=True)
        res = st.session_state.get("last_result")

        if not res:
            st.markdown(f"""
            <div class="result-empty">
                <div class="re-icon">🔍</div>
                <p class="re-title">{_t("awaiting_analysis")}</p>
                <p class="re-sub">{_t("awaiting_sub")}</p>
            </div>""", unsafe_allow_html=True)
        else:
            label = res["label"]
            conf  = res["conf"]
            probs = res.get("probs", {})
            meta  = DISEASE_META.get(label, DISEASE_META["Invalid Image"])
            steps = REMEDIES.get(label, [])

            # ── Show rejection card for invalid images ─────────────────────
            if label == "Invalid Image":
                st.markdown("""
                <div class="result-card" style="border-color:rgba(100,116,139,0.25)">
                    <div class="rc-header">
                        <div class="rc-icon-wrap" style="background:rgba(100,116,139,0.12);font-size:1.8rem">❌</div>
                        <div class="rc-title-block">
                            <span class="badge-disease" style="background:rgba(100,116,139,0.15);
                                color:#94a3b8;border-color:rgba(100,116,139,0.3)">
                                &#9888; NOT A POMEGRANATE LEAF
                            </span>
                            <h2 class="rc-name" style="color:#94a3b8">Image Rejected</h2>
                            <p class="rc-type">Invalid or unrecognised image</p>
                        </div>
                    </div>
                    <div style="margin-top:16px;padding:16px;background:rgba(100,116,139,0.08);
                         border-radius:10px;border:1px solid rgba(100,116,139,0.15)">
                        <p style="color:#94a3b8;font-size:0.88rem;margin:0 0 12px;font-weight:600">
                            Why was this rejected?
                        </p>
                        <div class="treat-item">
                            <span class="treat-dot" style="background:#64748b"></span>
                            <div><p class="treat-desc" style="margin:0">
                                The image validation system detected that this image
                                is likely <strong>not a pomegranate leaf</strong>.
                                This can happen when the image shows a different object
                                (car, person, food, building, etc.) or uses the wrong
                                plant species.
                            </p></div>
                        </div>
                        <div class="treat-item" style="margin-top:10px">
                            <span class="treat-dot" style="background:#64748b"></span>
                            <div><p class="treat-desc" style="margin:0">
                                <strong>Tips for a good scan:</strong> Use natural daylight,
                                hold the camera 15–20 cm from the leaf, ensure the leaf
                                fills most of the frame, and avoid blurry or dark images.
                            </p></div>
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)
                # Stop here — don't render the normal result card
                return

            badge = (
                '<span class="badge-disease">&#9888; DISEASE DETECTED</span>'
                if meta["detected"] else
                '<span class="badge-healthy">&#10003; HEALTHY PLANT</span>'
            )

            treat_parts = []
            for tx, dx in steps:
                treat_parts.append(
                    '<div class="treat-item">'
                    '<span class="treat-dot" style="background:' + meta["color"] + '"></span>'
                    '<div><p class="treat-title">' + tx + '</p>'
                    '<p class="treat-desc">' + dx + '</p></div>'
                    '</div>'
                )

            probs_parts = []
            if probs:
                for lbl, pct in sorted(probs.items(), key=lambda x: -x[1]):
                    c = DISEASE_META.get(lbl, DISEASE_META["Invalid Image"])["color"]
                    probs_parts.append(
                        '<div class="prob-row">'
                        '<span class="prob-label">' + lbl + '</span>'
                        '<div class="prob-track"><div class="prob-fill" style="width:' +
                        str(round(pct, 1)) + '%;background:' + c + '"></div></div>'
                        '<span class="prob-pct">' + str(round(pct, 1)) + '%</span>'
                        '</div>'
                    )
            probs_section = (
                '<div class="probs-box"><p class="probs-title">' + _t("class_probabilities") + '</p>'
                + "".join(probs_parts) + '</div>'
            ) if probs_parts else ""

            card_html = (
                '<div class="result-card">'
                '<div class="rc-header">'
                '<div class="rc-icon-wrap" style="background:' + meta["icon_bg"] + '">' + meta["icon"] + '</div>'
                '<div class="rc-title-block">' + badge +
                '<h2 class="rc-name">' + label + '</h2>'
                '<p class="rc-type">' + meta["type"] + '</p>'
                '</div>'
                '<div class="rc-conf">'
                '<p class="rc-conf-num" style="color:' + meta["color"] + '">' + str(round(conf)) + '%</p>'
                '<p class="rc-conf-lbl">' + _t("confidence") + '</p>'
                '</div></div>'
                '<div class="rc-severity">'
                '<span class="sev-key">' + _t("severity") + '</span>'
                '<span class="sev-val" style="color:' + meta["sev_color"] + '">' + meta["severity"] + '</span>'
                '</div>'
                + probs_section +
                '<div class="treat-box"><p class="treat-head">' + _t("treatment_plan") + '</p>'
                + "".join(treat_parts) + '</div>'
                '</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

# ── History ───────────────────────────────────────────────────────────────────

def _render_charts(history: list):
    import plotly.graph_objects as go
    from collections import Counter

    PALETTE = {
        "Healthy":"#10b981","Bacterial Blight":"#f87171",
        "Anthracnose":"#fb923c","Alternaria":"#fbbf24",
        "Cercospora":"#60a5fa","Invalid Image":"#64748b",
    }
    BG = "#0d1424"; GRID = "rgba(255,255,255,0.06)"; TEXT = "#8b9ab0"
    FONT = "Inter, system-ui, sans-serif"

    cl, cr = st.columns(2, gap="medium")

    with cl:
        st.markdown(f'<p class="section-label">{_t("disease_breakdown")}</p>', unsafe_allow_html=True)
        counts = Counter(s["disease_type"] for s in history)
        labels = list(counts.keys()); vals = list(counts.values())
        colors = [PALETTE.get(l, "#64748b") for l in labels]
        fig = go.Figure(go.Pie(
            labels=labels, values=vals, hole=0.6,
            marker=dict(colors=colors, line=dict(color=BG, width=2)),
            textinfo="percent",
            textfont=dict(family=FONT, size=12, color="#fff"),
            hovertemplate="<b>%{label}</b><br>%{value} scans (%{percent})<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor=BG, plot_bgcolor=BG,
            margin=dict(t=8,b=8,l=8,r=8), height=240, showlegend=True,
            legend=dict(font=dict(family=FONT,size=11,color=TEXT),bgcolor="rgba(0,0,0,0)",x=1,y=0.5),
            annotations=[dict(text=f"<b>{len(history)}</b><br>total",x=0.5,y=0.5,
                              showarrow=False,font=dict(family=FONT,size=15,color=TEXT))],
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with cr:
        st.markdown(f'<p class="section-label">{_t("scans_over_time")}</p>', unsafe_allow_html=True)
        date_counts: dict = {}
        for s in history:
            d = str(s["created_at"])[:10]
            date_counts[d] = date_counts.get(d, 0) + 1
        if date_counts:
            xs = sorted(date_counts); ys = [date_counts[d] for d in xs]
            fig2 = go.Figure(go.Scatter(
                x=xs, y=ys, mode="lines+markers",
                line=dict(color="#10b981", width=2.5, shape="spline"),
                marker=dict(color="#10b981", size=6, line=dict(color=BG, width=1.5)),
                fill="tozeroy", fillcolor="rgba(16,185,129,0.08)",
                hovertemplate="<b>%{x}</b><br>%{y} scan(s)<extra></extra>",
            ))
            fig2.update_layout(
                paper_bgcolor=BG, plot_bgcolor=BG,
                margin=dict(t=8,b=8,l=8,r=8), height=240,
                xaxis=dict(showgrid=False,zeroline=False,tickfont=dict(family=FONT,size=10,color=TEXT),tickangle=-30),
                yaxis=dict(showgrid=True,gridcolor=GRID,zeroline=False,tickfont=dict(family=FONT,size=10,color=TEXT),dtick=1),
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})

def _tab_history():
    st.markdown(f"""
    <div class="page-hero">
        <div class="hero-text">
            <h1 class="hero-title">{_t("scan_history")}</h1>
            <p class="hero-sub">{_t("history_sub")}</p>
        </div>
    </div>""", unsafe_allow_html=True)

    user_id = st.session_state.user.id
    stats   = get_user_stats(user_id)
    history = fetch_scan_history(user_id)

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    for col, lkey, val, color in [
        (c1, "total_scans",   stats["total"] or 0,                    "#60a5fa"),
        (c2, "healthy",       stats["healthy"] or 0,                  "#10b981"),
        (c3, "diseased",      stats["diseased"] or 0,                 "#f87171"),
        (c4, "avg_confidence",f"{stats['avg_confidence'] or 0:.0f}%", "#a78bfa"),
    ]:
        with col:
            st.markdown(f"""
            <div class="dash-stat-card">
                <p class="dsc-label">{_t(lkey)}</p>
                <p class="dsc-value" style="color:{color}">{val}</p>
            </div>""", unsafe_allow_html=True)

    if not history:
        st.markdown(f"""
        <div class="empty-card" style="margin-top:24px">
            <p class="empty-icon">📋</p>
            <p class="empty-title">{_t("no_history")}</p>
            <p class="empty-sub">{_t("no_history_sub")}</p>
        </div>""", unsafe_allow_html=True)
        return

    st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
    _render_charts(history)

    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
    st.markdown(f'<p class="section-label">{_t("scan_records")}</p>', unsafe_allow_html=True)
    search   = st.text_input("search", placeholder=_t("search_placeholder"),
                             label_visibility="collapsed", key="hist_search")
    filtered = [s for s in history if search.lower() in s["disease_type"].lower()] if search else history

    for s in filtered:
        lbl  = s["disease_type"]
        conf = s["confidence"]
        date = str(s["created_at"])[5:16]
        sid  = s["id"]
        meta = DISEASE_META.get(lbl, DISEASE_META["Invalid Image"])

        col_row, col_del = st.columns([12, 1], gap="small")
        with col_row:
            st.markdown(f"""
            <div class="hist-row">
                <div class="hr-icon" style="background:{meta['icon_bg']}">{meta['icon']}</div>
                <div class="hr-info">
                    <p class="hr-name">{lbl}</p>
                    <p class="hr-meta">{meta['type']} · {date}</p>
                </div>
                <div class="hr-right">
                    <p class="hr-conf" style="color:{meta['color']}">{conf:.0f}%</p>
                    <p class="hr-conf-lbl">{_t("confidence")}</p>
                </div>
            </div>""", unsafe_allow_html=True)
        with col_del:
            if st.button("🗑", key=f"del_{sid}", help="Delete scan"):
                delete_scan(sid, user_id); st.rerun()

# ── Weather ───────────────────────────────────────────────────────────────────

def _tab_weather():
    st.markdown(f"""
    <div class="page-hero">
        <div class="hero-text">
            <h1 class="hero-title">{_t("weather")}</h1>
            <p class="hero-sub">{_t("weather_sub")}</p>
        </div>
    </div>""", unsafe_allow_html=True)

    col_in, col_btn = st.columns([4, 1], gap="small")
    with col_in:
        city = st.text_input("city", placeholder=_t("city_placeholder"),
                             label_visibility="collapsed", key="weather_city")
    with col_btn:
        fetch = st.button(_t("get_weather"), use_container_width=True, key="btn_weather")

    if fetch and city:
        with st.spinner("Fetching weather…"):
            data = get_weather(city)
        if data:
            st.session_state.weather_data = data
        else:
            st.error("City not found or API error. Please check the city name and try again.")
            st.session_state.weather_data = None

    w = st.session_state.get("weather_data")
    if not w:
        st.markdown("""
        <div class="empty-card" style="margin-top:32px">
            <p class="empty-icon">🌦️</p>
            <p class="empty-title">Enter a city to get started</p>
            <p class="empty-sub">Type your city name above and click Get Weather to see live conditions and disease risk.</p>
        </div>""", unsafe_allow_html=True)
        return

    risk = get_disease_risk(w)

    st.markdown(f'<p class="section-label" style="margin-top:24px">{_t("current_weather_in")} {w["city"]}, {w["country"]}</p>',
                unsafe_allow_html=True)

    # Weather metric cards
    c1, c2, c3, c4 = st.columns(4, gap="medium")
    for col, icon, label_key, value, color in [
        (c1, "🌡️", "temperature",  f'{w["temp"]}°C',         "#60a5fa"),
        (c2, "💧", "humidity",     f'{w["humidity"]}%',       "#34d399"),
        (c3, "💨", "wind_speed",   f'{w["wind_kmh"]} km/h',   "#a78bfa"),
        (c4, "🌤️", "condition",    w["condition"],            "#fbbf24"),
    ]:
        with col:
            st.markdown(f"""
            <div class="dash-stat-card">
                <div class="dsc-top">
                    <span class="dsc-icon">{icon}</span>
                    <span class="dsc-label">{_t(label_key)}</span>
                </div>
                <p class="dsc-value" style="color:{color};font-size:1.3rem">{value}</p>
            </div>""", unsafe_allow_html=True)

    st.markdown(f'<p class="dsc-label" style="margin:8px 0 20px;color:#8b9ab0">'
                f'{_t("feels_like")}: {w["feels_like"]}°C</p>', unsafe_allow_html=True)

    # Disease risk + advisory
    left, right = st.columns([1, 2], gap="medium")

    with left:
        st.markdown(f"""
        <div class="dash-stat-card" style="text-align:center;padding:28px 20px">
            <p style="font-size:2.5rem;margin:0">{risk["icon"]}</p>
            <p class="section-label" style="margin:10px 0 6px">{_t("disease_risk")}</p>
            <p style="font-size:1.6rem;font-weight:700;color:{risk["color"]};margin:0">
                {_t("risk_" + risk["level"].lower())}
            </p>
            <p style="font-size:0.78rem;color:#8b9ab0;margin-top:8px">
                Humidity {w["humidity"]}% · {w["temp"]}°C
            </p>
        </div>""", unsafe_allow_html=True)

    with right:
        st.markdown(f'<p class="section-label">{_t("risk_advice")}</p>', unsafe_allow_html=True)
        advice_html = "".join(
            f'<div class="treat-item">'
            f'<span class="treat-dot" style="background:{risk["color"]}"></span>'
            f'<div><p class="treat-desc" style="margin:0">{a}</p></div></div>'
            for a in risk["advice"]
        )
        st.markdown(
            '<div class="treat-box" style="margin-top:0">' + advice_html + '</div>',
            unsafe_allow_html=True
        )

# ── Agri Hub (News + Tips) ────────────────────────────────────────────────────

def _tab_news():
    st.markdown(f"""
    <div class="page-hero">
        <div class="hero-text">
            <h1 class="hero-title">{_t("agri_hub")}</h1>
            <p class="hero-sub">{_t("agri_hub_sub")}</p>
        </div>
    </div>""", unsafe_allow_html=True)

    # Tip of the day
    tip_icon, tip_title, tip_body = get_tip_of_day()
    st.markdown(f"""
    <div class="dash-stat-card" style="padding:20px 24px;margin-bottom:24px;
         border-left:3px solid #10b981;display:flex;gap:16px;align-items:flex-start">
        <span style="font-size:2rem">{tip_icon}</span>
        <div>
            <p class="section-label" style="margin:0 0 4px">💡 {_t("tip_of_day")} — {tip_title}</p>
            <p style="color:#cbd5e1;font-size:0.9rem;margin:0;line-height:1.6">{tip_body}</p>
        </div>
    </div>""", unsafe_allow_html=True)

    # News
    st.markdown(f'<p class="section-label">{_t("latest_news")}</p>', unsafe_allow_html=True)
    with st.spinner(_t("agri_hub_sub")):
        articles = fetch_agri_news("agriculture India farming pomegranate crop")

    if not articles:
        st.markdown(f"""
        <div class="empty-card">
            <p class="empty-icon">📰</p>
            <p class="empty-title">{_t("no_news")}</p>
        </div>""", unsafe_allow_html=True)
        return

    # 2-column news grid
    col1, col2 = st.columns(2, gap="medium")
    for i, a in enumerate(articles):
        col = col1 if i % 2 == 0 else col2
        with col:
            desc = a["description"][:160] + "…" if len(a["description"]) > 160 else a["description"]
            st.markdown(
                '<div class="news-card">'
                '<div class="nc-meta">'
                '<span class="nc-source">' + a["source"] + '</span>'
                '<span class="nc-date">' + a["published"] + '</span>'
                '</div>'
                '<p class="nc-title">' + a["title"] + '</p>'
                '<p class="nc-desc">' + desc + '</p>'
                '<a class="nc-link" href="' + a["url"] + '" target="_blank">' + _t("read_more") + '</a>'
                '</div>',
                unsafe_allow_html=True
            )

    # All tips section
    st.markdown(f'<p class="section-label" style="margin-top:32px">{_t("tip_of_day")}</p>',
                unsafe_allow_html=True)
    t1, t2, t3 = st.columns(3, gap="medium")
    tips = get_all_tips()
    for i, (ico, title, body) in enumerate(tips):
        col = [t1, t2, t3][i % 3]
        with col:
            st.markdown(
                '<div class="topic-card">'
                '<span class="tc-icon">' + ico + '</span>'
                '<p class="tc-title">' + title + '</p>'
                '<p class="tc-desc">' + body[:120] + '…' + '</p>'
                '</div>',
                unsafe_allow_html=True
            )

# ── Government Schemes ────────────────────────────────────────────────────────

def _tab_schemes():
    st.markdown(f"""
    <div class="page-hero">
        <div class="hero-text">
            <h1 class="hero-title">{_t("gov_schemes")}</h1>
            <p class="hero-sub">{_t("schemes_sub")}</p>
        </div>
    </div>""", unsafe_allow_html=True)

    col_s, col_c = st.columns([3, 1], gap="medium")
    with col_s:
        query = st.text_input("sq", placeholder=_t("search_schemes"),
                              label_visibility="collapsed", key="scheme_query")
    with col_c:
        cat = st.selectbox("sc", CATEGORIES, label_visibility="collapsed", key="scheme_cat")

    results = search_schemes(query, cat)

    st.markdown(f'<p style="color:#8b9ab0;font-size:0.82rem;margin:12px 0 16px">'
                f'{len(results)} scheme(s) found</p>', unsafe_allow_html=True)

    for s in results:
        with st.expander(f'{s["emoji"]}  {s["name"]}  ·  {s["category"]}'):
            c1, c2 = st.columns([3, 1], gap="medium")
            with c1:
                st.markdown(f'**Description:** {s["description"]}')
                st.markdown(f'**{_t("eligibility")}:** {s["eligibility"]}')
                st.markdown(f'**{_t("benefits")}:** {s["benefits"]}')
                st.markdown(f'**{_t("apply_now")}:** {s["how_to_apply"]}')
            with c2:
                st.markdown(f"""
                <div style="background:#0d1424;border-radius:10px;padding:16px;font-size:0.83rem">
                    <p style="color:#8b9ab0;margin:0 0 6px">{_t("ministry")}</p>
                    <p style="color:#f0f4f8;margin:0 0 14px;line-height:1.4">{s["ministry"]}</p>
                    <a href="{s["website"]}" target="_blank" style="color:#10b981;
                       text-decoration:none;font-weight:600">{_t("visit_website")}</a>
                </div>""", unsafe_allow_html=True)

# ── Crop Advisor ──────────────────────────────────────────────────────────────

def _tab_crops():
    st.markdown(f"""
    <div class="page-hero">
        <div class="hero-text">
            <h1 class="hero-title">{_t("crop_advisor")}</h1>
            <p class="hero-sub">{_t("crop_advisor_sub")}</p>
        </div>
    </div>""", unsafe_allow_html=True)

    left, right = st.columns([1, 2], gap="large")

    with left:
        st.markdown('<div class="settings-card">', unsafe_allow_html=True)
        st.markdown(f'<p class="sc-title">🌾 {_t("crop_advisor")}</p>', unsafe_allow_html=True)
        soil   = st.selectbox(_t("soil_type"),          SOIL_OPTIONS,   key="ca_soil")
        season = st.selectbox(_t("season"),             SEASON_OPTIONS, key="ca_season")
        region = st.selectbox(_t("region"),             REGION_OPTIONS, key="ca_region")
        water  = st.selectbox(_t("water_availability"), WATER_OPTIONS,  key="ca_water")
        run    = st.button(_t("get_recommendations"), use_container_width=True, key="btn_crops")
        st.markdown('</div>', unsafe_allow_html=True)

        # Auto-run on first load
        if "crop_results" not in st.session_state:
            st.session_state.crop_results = get_crop_recommendations(soil, season, region, water)

        if run:
            st.session_state.crop_results = get_crop_recommendations(soil, season, region, water)
            st.rerun()

    with right:
        st.markdown(f'<p class="section-label">{_t("recommended_crops")}</p>', unsafe_allow_html=True)
        results = st.session_state.get("crop_results", [])

        if not results:
            st.markdown(f"""
            <div class="empty-card">
                <p class="empty-icon">🌱</p>
                <p class="empty-title">{_t("no_crops")}</p>
            </div>""", unsafe_allow_html=True)
        else:
            for i, crop in enumerate(results):
                badge_color = ["#10b981", "#60a5fa", "#a78bfa", "#fbbf24", "#fb923c"][i % 5]
                st.markdown(
                    '<div class="dash-stat-card" style="padding:20px 24px;margin-bottom:12px">'
                    '<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                    '<div style="display:flex;gap:14px;align-items:center">'
                    '<span style="font-size:2rem">' + crop["emoji"] + '</span>'
                    '<div>'
                    '<p style="font-weight:700;font-size:1.05rem;color:#f0f4f8;margin:0">'
                    + crop["name"] + '</p>'
                    '<p style="color:#8b9ab0;font-size:0.8rem;margin:2px 0 0">'
                    + crop["best_for"] + '</p>'
                    '</div></div>'
                    '<span style="background:' + badge_color + '22;color:' + badge_color +
                    ';padding:3px 10px;border-radius:20px;font-size:0.75rem;font-weight:600">'
                    '#' + str(i+1) + ' Pick</span>'
                    '</div>'
                    '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:16px">'
                    '<div><p style="color:#8b9ab0;font-size:0.75rem;margin:0">' + _t("growing_period") + '</p>'
                    '<p style="color:#cbd5e1;font-size:0.85rem;margin:2px 0 0;font-weight:600">' + crop["period"] + '</p></div>'
                    '<div><p style="color:#8b9ab0;font-size:0.75rem;margin:0">' + _t("water_need") + '</p>'
                    '<p style="color:#cbd5e1;font-size:0.85rem;margin:2px 0 0;font-weight:600">' + crop["water_need"] + '</p></div>'
                    '<div><p style="color:#8b9ab0;font-size:0.75rem;margin:0">' + _t("yield_potential") + '</p>'
                    '<p style="color:#cbd5e1;font-size:0.85rem;margin:2px 0 0;font-weight:600">' + crop["yield"] + '</p></div>'
                    '</div>'
                    '<div style="margin-top:14px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.06)">'
                    '<p style="color:#8b9ab0;font-size:0.75rem;margin:0 0 4px">💡 ' + _t("pro_tip") + '</p>'
                    '<p style="color:#94a3b8;font-size:0.82rem;margin:0;line-height:1.5">' + crop["tip"] + '</p>'
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True
                )

# ── Profile ───────────────────────────────────────────────────────────────────

def _tab_profile():
    user    = st.session_state.user
    email   = user.email
    name    = getattr(user, "name", "").strip() or email.split("@")[0].title()
    initial = name[0].upper()
    joined  = str(getattr(user, "created_at", "—"))[:10]
    stats   = get_user_stats(user.id)

    st.markdown(f"""
    <div class="page-hero">
        <div class="hero-text">
            <h1 class="hero-title">{_t("profile")}</h1>
            <p class="hero-sub">{_t("profile_sub")}</p>
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="profile-hero-card">
        <div class="phc-avatar">{initial}</div>
        <div class="phc-info">
            <h2 class="phc-name">{name}</h2>
            <p class="phc-email">{email}</p>
            <p class="phc-role">🌾 KrushiAI Farmer · {_t("member_since")} {joined}</p>
        </div>
        <div class="phc-stats">
            <div class="phcs"><p class="phcs-n" style="color:#60a5fa">{stats['total'] or 0}</p>
                <p class="phcs-l">{_t("total_scans")}</p></div>
            <div class="phcs"><p class="phcs-n" style="color:#10b981">{stats['healthy'] or 0}</p>
                <p class="phcs-l">{_t("healthy")}</p></div>
            <div class="phcs"><p class="phcs-n" style="color:#f87171">{stats['diseased'] or 0}</p>
                <p class="phcs-l">{_t("diseased")}</p></div>
        </div>
    </div>""", unsafe_allow_html=True)

    left, right = st.columns([3, 2], gap="medium")

    with left:
        st.markdown(f'<div class="settings-card"><p class="sc-title">{_t("account_info")}</p>',
                    unsafe_allow_html=True)
        new_name = st.text_input(_t("full_name"), value=name, key="p_name")
        st.text_input("Email", value=email, disabled=True, key="p_email")
        st.text_input(_t("member_since"), value=joined, disabled=True, key="p_joined")
        if st.button(_t("save_changes"), key="btn_update_name", use_container_width=True):
            if update_profile_name(user.id, new_name):
                user.name = new_name.strip()
                st.session_state.user = user
                st.success("Profile updated!")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown(f'<div class="settings-card"><p class="sc-title">{_t("security")}</p>',
                    unsafe_allow_html=True)
        with st.expander(_t("change_password")):
            old  = st.text_input(_t("current_password"), type="password", key="cp_old")
            new1 = st.text_input(_t("new_password"),     type="password", key="cp_new")
            new2 = st.text_input(_t("confirm_password"), type="password", key="cp_new2")
            if st.button(_t("update_password"), key="btn_save_pwd", use_container_width=True):
                if not old or not new1:
                    st.error("Please fill in all fields.")
                elif new1 != new2:
                    st.error("Passwords do not match.")
                elif change_password(user.id, old, new1):
                    st.success("Password updated successfully!")
                else:
                    st.error("Current password is incorrect.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(f"""
        <div class="settings-card" style="margin-top:14px">
            <p class="sc-title">{_t("language")}</p>
            <p style="color:#8b9ab0;font-size:0.85rem;margin:0">
                Language is also accessible from the sidebar selector.
            </p>
        </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
