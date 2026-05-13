import streamlit as st
import base64
import os
from PIL import Image
from utils.auth import sign_in, sign_up, change_password, update_profile_name
from utils.predictor import predict_disease, LABELS as MODEL_LABELS
from utils.database import save_scan_result, fetch_scan_history, delete_scan, get_user_stats, init_db

# ── Disease data ───────────────────────────────────────────────────────────────

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
    ("🏠", "Dashboard",    "dashboard"),
    ("🔬", "AI Scanner",   "scanner"),
    ("📋", "Scan History", "history"),
    ("👤", "Profile",      "profile"),
    ("💬", "Support",      "support"),
]

# ── Helpers ───────────────────────────────────────────────────────────────────

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

def _nav_btn(icon: str, label: str, key: str, page: str):
    if st.session_state.page == page:
        st.markdown('<span class="nav-hint"></span>', unsafe_allow_html=True)
    if st.button(f"{icon}  {label}", key=key, use_container_width=True):
        st.session_state.page = page
        st.rerun()

def _severity_badge(severity: str, color: str) -> str:
    return (f'<span class="sev-badge" style="color:{color};'
            f'background:rgba({_hex_to_rgb(color)},0.12);'
            f'border-color:rgba({_hex_to_rgb(color)},0.25)">{severity}</span>')

def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"

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

    st.session_state.setdefault("user",        None)
    st.session_state.setdefault("page",        "dashboard")
    st.session_state.setdefault("last_result", None)
    st.session_state.setdefault("auth_tab",    "login")

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
            st.markdown('<p class="auth-form-title">Welcome back</p>', unsafe_allow_html=True)
            st.markdown('<label class="field-label">Email Address</label>', unsafe_allow_html=True)
            email = st.text_input("e1", placeholder="you@example.com", key="li_email", label_visibility="collapsed")
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown('<label class="field-label">Password</label>', unsafe_allow_html=True)
            with c2:
                st.markdown('<span class="forgot-link">Forgot?</span>', unsafe_allow_html=True)
            pwd = st.text_input("p1", type="password", placeholder="••••••••", key="li_pwd", label_visibility="collapsed")

            if st.button("Sign In →", use_container_width=True, key="btn_login"):
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

            st.markdown('<p class="auth-switch">Don\'t have an account?</p>', unsafe_allow_html=True)
            if st.button("Create free account", use_container_width=True, key="btn_go_signup"):
                st.session_state.auth_tab = "signup"
                st.rerun()

        else:
            st.markdown('<p class="auth-form-title">Create your account</p>', unsafe_allow_html=True)
            st.markdown('<label class="field-label">Full Name</label>', unsafe_allow_html=True)
            name  = st.text_input("n2", placeholder="Your full name",     key="su_name",  label_visibility="collapsed")
            st.markdown('<label class="field-label">Email Address</label>', unsafe_allow_html=True)
            email = st.text_input("e2", placeholder="you@example.com",    key="su_email", label_visibility="collapsed")
            st.markdown('<label class="field-label">Password</label>', unsafe_allow_html=True)
            pwd   = st.text_input("p2", type="password", placeholder="Min. 6 characters", key="su_pwd", label_visibility="collapsed")

            if st.button("Create Account →", use_container_width=True, key="btn_signup"):
                if not name or not email or not pwd:
                    st.warning("Please fill in all fields.")
                else:
                    with st.spinner("Creating account…"):
                        ok = sign_up(email, pwd, name)
                    if ok:
                        st.success("Account created! Please sign in.")
                        st.session_state.auth_tab = "login"
                        st.rerun()

            st.markdown('<p class="auth-switch">Already have an account?</p>', unsafe_allow_html=True)
            if st.button("Sign in instead", use_container_width=True, key="btn_go_login"):
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
                <span class="sb-sub">Plant Intelligence</span>
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
        st.markdown('<p class="sb-section-label">MAIN MENU</p>', unsafe_allow_html=True)

        st.markdown('<div class="nav-section">', unsafe_allow_html=True)
        for icon, label, page in NAV:
            _nav_btn(icon, label, f"nav_{page}", page)
        st.markdown('</div>', unsafe_allow_html=True)

        # User card at bottom
        st.markdown(f"""
        <div class="sb-user-card">
            <div class="sb-user-avatar">{initial}</div>
            <div class="sb-user-info">
                <p class="sb-user-name">{name}</p>
                <p class="sb-user-email">{user.email}</p>
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div class="logout-wrap">', unsafe_allow_html=True)
        if st.button("↩  Sign Out", key="btn_logout", use_container_width=True):
            for k in ["user", "last_result", "page", "auth_tab"]:
                st.session_state.pop(k, None)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Top bar ────────────────────────────────────────────────────────────────
    page_titles = {
        "dashboard": ("🏠", "Dashboard"),
        "scanner":   ("🔬", "AI Scanner"),
        "history":   ("📋", "Scan History"),
        "profile":   ("👤", "Profile"),
        "support":   ("💬", "Support"),
    }
    page = st.session_state.page
    p_icon, p_title = page_titles.get(page, ("", page.title()))

    st.markdown(f"""
    <header class="top-bar">
        <div class="top-breadcrumb">
            <span class="top-app-name">KrushiAI</span>
            <span class="top-sep">/</span>
            <span class="top-page">{p_icon} {p_title}</span>
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
    elif page == "profile":   _tab_profile()
    elif page == "support":   _tab_support()

# ── Dashboard ─────────────────────────────────────────────────────────────────

def _tab_dashboard():
    user    = st.session_state.user
    name    = getattr(user, "name", "").strip() or user.email.split("@")[0].title()
    stats   = get_user_stats(user.id)
    history = fetch_scan_history(user.id)
    recent  = history[:3]

    # Hero
    st.markdown(f"""
    <div class="page-hero">
        <div class="hero-text">
            <p class="hero-greeting">Good day, {name} 👋</p>
            <h1 class="hero-title">Plant Health Overview</h1>
            <p class="hero-sub">Here's a summary of your field diagnostics and recent activity.</p>
        </div>
    </div>""", unsafe_allow_html=True)

    # Stat cards
    total    = stats["total"] or 0
    healthy  = stats["healthy"] or 0
    diseased = stats["diseased"] or 0
    avg_conf = stats["avg_confidence"] or 0
    health_rate = round((healthy / total * 100)) if total else 0

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    cards = [
        (c1, "Total Scans",    str(total),           "#60a5fa", "🔬"),
        (c2, "Healthy",        str(healthy),          "#10b981", "🌿"),
        (c3, "Diseased",       str(diseased),         "#f87171", "⚠️"),
        (c4, "Health Rate",    f"{health_rate}%",     "#a78bfa", "📊"),
    ]
    for col, label, val, color, icon in cards:
        with col:
            st.markdown(f"""
            <div class="dash-stat-card">
                <div class="dsc-top">
                    <span class="dsc-icon">{icon}</span>
                    <span class="dsc-label">{label}</span>
                </div>
                <p class="dsc-value" style="color:{color}">{val}</p>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)

    left, right = st.columns([3, 2], gap="medium")

    with left:
        st.markdown('<p class="section-label">Recent Scans</p>', unsafe_allow_html=True)
        if not recent:
            st.markdown("""
            <div class="empty-card">
                <p class="empty-icon">🔬</p>
                <p class="empty-title">No scans yet</p>
                <p class="empty-sub">Run your first leaf scan to see results here.</p>
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
        st.markdown('<p class="section-label">Quick Actions</p>', unsafe_allow_html=True)
        st.markdown("""
        <div class="qa-card">
            <div class="qa-icon">🔬</div>
            <div>
                <p class="qa-title">New Scan</p>
                <p class="qa-sub">Diagnose a leaf image with AI</p>
            </div>
        </div>""", unsafe_allow_html=True)
        if st.button("Start Scanning →", key="dash_scan", use_container_width=True):
            st.session_state.last_result = None
            st.session_state.page = "scanner"
            st.rerun()

        st.markdown("""
        <div class="qa-card" style="margin-top:10px">
            <div class="qa-icon">📋</div>
            <div>
                <p class="qa-title">View History</p>
                <p class="qa-sub">Review past diagnostics & trends</p>
            </div>
        </div>""", unsafe_allow_html=True)
        if st.button("Open History →", key="dash_hist", use_container_width=True):
            st.session_state.page = "history"
            st.rerun()

# ── Scanner ───────────────────────────────────────────────────────────────────

def _tab_scanner():
    st.markdown("""
    <div class="page-hero">
        <div class="hero-text">
            <h1 class="hero-title">AI Diagnostic Scanner</h1>
            <p class="hero-sub">Upload or capture a leaf image. Our CNN model identifies diseases with high accuracy.</p>
        </div>
    </div>""", unsafe_allow_html=True)

    left, right = st.columns(2, gap="large")

    with left:
        st.markdown('<p class="section-label">Image Input</p>', unsafe_allow_html=True)
        tab_upload, tab_camera = st.tabs(["📁  Upload File", "📷  Camera"])

        img = None; img_source = None

        with tab_upload:
            uploaded = st.file_uploader("leaf", type=["jpg","jpeg","png"], label_visibility="collapsed")
            if uploaded:
                img = Image.open(uploaded); img_source = uploaded.name
                st.image(img, use_container_width=True)
            else:
                st.markdown("""
                <div class="upload-zone">
                    <div class="uz-icon">🌿</div>
                    <p class="uz-title">Drop your leaf image here</p>
                    <p class="uz-hint">Supports JPG, JPEG, PNG · Max 200MB</p>
                    <p class="uz-hint">Ensure clear focus and good lighting</p>
                </div>""", unsafe_allow_html=True)

        with tab_camera:
            shot = st.camera_input("capture", label_visibility="collapsed")
            if shot:
                img = Image.open(shot); img_source = "camera"
                st.image(img, use_container_width=True)
            else:
                st.markdown("""
                <div class="upload-zone">
                    <div class="uz-icon">📷</div>
                    <p class="uz-title">Allow camera access</p>
                    <p class="uz-hint">Point camera at the leaf, ensure clear focus</p>
                </div>""", unsafe_allow_html=True)

        if img:
            if st.button("🔬  Analyze Leaf", key="btn_analyze", use_container_width=True):
                with st.spinner("Running AI analysis…"):
                    label, conf = predict_disease(img)
                    # get all class probabilities
                    import tensorflow as tf, numpy as np
                    model = tf.keras.models.load_model("models/pomegranate_model.h5")
                    arr   = np.expand_dims(np.array(img.convert("RGB").resize((224,224)),dtype=np.float32)/255.0, 0)
                    probs = model.predict(arr, verbose=0)[0]
                save_scan_result(user_id=st.session_state.user.id,
                                 disease_name=label, confidence=conf, image_name=img_source)
                st.session_state.last_result = {
                    "label": label, "conf": conf,
                    "probs": {l: float(p*100) for l, p in zip(MODEL_LABELS, probs)}
                }
                st.rerun()

    with right:
        st.markdown('<p class="section-label">Analysis Result</p>', unsafe_allow_html=True)
        res = st.session_state.get("last_result")

        if not res:
            st.markdown("""
            <div class="result-empty">
                <div class="re-icon">🔍</div>
                <p class="re-title">Awaiting Analysis</p>
                <p class="re-sub">Upload a leaf image and click<br><strong>Analyze Leaf</strong> to see results.</p>
            </div>""", unsafe_allow_html=True)
        else:
            label = res["label"]
            conf  = res["conf"]
            probs = res.get("probs", {})
            meta  = DISEASE_META.get(label, DISEASE_META["Invalid Image"])
            steps = REMEDIES.get(label, [])

            # Build badge
            if meta["detected"]:
                badge = '<span class="badge-disease">&#9888; DISEASE DETECTED</span>'
            else:
                badge = '<span class="badge-healthy">&#10003; HEALTHY PLANT</span>'

            # Build treatment items
            treat_parts = []
            for t, d in steps:
                treat_parts.append(
                    '<div class="treat-item">'
                    '<span class="treat-dot" style="background:' + meta["color"] + '"></span>'
                    '<div><p class="treat-title">' + t + '</p>'
                    '<p class="treat-desc">' + d + '</p></div>'
                    '</div>'
                )
            treat_html = "".join(treat_parts)

            # Build probability bars
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
                '<div class="probs-box">'
                '<p class="probs-title">Class Probabilities</p>'
                + "".join(probs_parts) +
                '</div>'
            ) if probs_parts else ""

            # Assemble full card HTML as a plain string (no nested f-strings)
            card_html = (
                '<div class="result-card">'

                '<div class="rc-header">'
                '<div class="rc-icon-wrap" style="background:' + meta["icon_bg"] + '">' + meta["icon"] + '</div>'
                '<div class="rc-title-block">'
                + badge +
                '<h2 class="rc-name">' + label + '</h2>'
                '<p class="rc-type">' + meta["type"] + '</p>'
                '</div>'
                '<div class="rc-conf">'
                '<p class="rc-conf-num" style="color:' + meta["color"] + '">' + str(round(conf)) + '%</p>'
                '<p class="rc-conf-lbl">confidence</p>'
                '</div>'
                '</div>'

                '<div class="rc-severity">'
                '<span class="sev-key">Severity</span>'
                '<span class="sev-val" style="color:' + meta["sev_color"] + '">' + meta["severity"] + '</span>'
                '</div>'

                + probs_section +

                '<div class="treat-box">'
                '<p class="treat-head">Treatment Plan</p>'
                + treat_html +
                '</div>'

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
        st.markdown('<p class="section-label">Disease Breakdown</p>', unsafe_allow_html=True)
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
            margin=dict(t=8,b=8,l=8,r=8), height=240,
            showlegend=True,
            legend=dict(font=dict(family=FONT,size=11,color=TEXT),bgcolor="rgba(0,0,0,0)",x=1,y=0.5),
            annotations=[dict(text=f"<b>{len(history)}</b><br>total",x=0.5,y=0.5,showarrow=False,
                              font=dict(family=FONT,size=15,color=TEXT))],
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with cr:
        st.markdown('<p class="section-label">Scans Over Time</p>', unsafe_allow_html=True)
        date_counts: dict = {}
        for s in history:
            d = str(s["created_at"])[:10]
            date_counts[d] = date_counts.get(d,0) + 1
        if date_counts:
            xs = sorted(date_counts); ys = [date_counts[d] for d in xs]
            fig2 = go.Figure(go.Scatter(
                x=xs, y=ys, mode="lines+markers",
                line=dict(color="#10b981",width=2.5,shape="spline"),
                marker=dict(color="#10b981",size=6,line=dict(color=BG,width=1.5)),
                fill="tozeroy", fillcolor="rgba(16,185,129,0.08)",
                hovertemplate="<b>%{x}</b><br>%{y} scan(s)<extra></extra>",
            ))
            fig2.update_layout(
                paper_bgcolor=BG, plot_bgcolor=BG,
                margin=dict(t=8,b=8,l=8,r=8), height=240,
                xaxis=dict(showgrid=False,zeroline=False,tickfont=dict(family=FONT,size=10,color=TEXT),tickangle=-30),
                yaxis=dict(showgrid=True,gridcolor=GRID,zeroline=False,tickfont=dict(family=FONT,size=10,color=TEXT),dtick=1),
                hoverlabel=dict(bgcolor="#1e293b",font=dict(family=FONT,size=12,color=TEXT)),
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})

def _tab_history():
    st.markdown("""
    <div class="page-hero">
        <div class="hero-text">
            <h1 class="hero-title">Scan History</h1>
            <p class="hero-sub">Review past diagnostics, track disease trends, and monitor field health over time.</p>
        </div>
    </div>""", unsafe_allow_html=True)

    user_id = st.session_state.user.id
    stats   = get_user_stats(user_id)
    history = fetch_scan_history(user_id)

    # Stat row
    c1,c2,c3,c4 = st.columns(4, gap="medium")
    for col, label, val, color in [
        (c1, "Total Scans",      stats["total"] or 0,           "#60a5fa"),
        (c2, "Healthy",          stats["healthy"] or 0,         "#10b981"),
        (c3, "Diseased",         stats["diseased"] or 0,        "#f87171"),
        (c4, "Avg Confidence",   f"{stats['avg_confidence'] or 0:.0f}%", "#a78bfa"),
    ]:
        with col:
            st.markdown(f"""
            <div class="dash-stat-card">
                <p class="dsc-label">{label}</p>
                <p class="dsc-value" style="color:{color}">{val}</p>
            </div>""", unsafe_allow_html=True)

    if not history:
        st.markdown("""
        <div class="empty-card" style="margin-top:24px">
            <p class="empty-icon">📋</p>
            <p class="empty-title">No scans yet</p>
            <p class="empty-sub">Your scan history will appear here after your first analysis.</p>
        </div>""", unsafe_allow_html=True)
        return

    st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
    _render_charts(history)

    # Search
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
    st.markdown('<p class="section-label">Scan Records</p>', unsafe_allow_html=True)
    search = st.text_input("search", placeholder="🔍  Search by disease name…", label_visibility="collapsed", key="hist_search")
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
                    <p class="hr-conf-lbl">confidence</p>
                </div>
            </div>""", unsafe_allow_html=True)
        with col_del:
            if st.button("🗑", key=f"del_{sid}", help="Delete scan"):
                delete_scan(sid, user_id); st.rerun()

# ── Profile ───────────────────────────────────────────────────────────────────

def _tab_profile():
    user    = st.session_state.user
    email   = user.email
    name    = getattr(user,"name","").strip() or email.split("@")[0].title()
    initial = name[0].upper()
    joined  = str(getattr(user,"created_at","—"))[:10]
    stats   = get_user_stats(user.id)

    st.markdown("""
    <div class="page-hero">
        <div class="hero-text">
            <h1 class="hero-title">Profile & Settings</h1>
            <p class="hero-sub">Manage your account information, security, and application preferences.</p>
        </div>
    </div>""", unsafe_allow_html=True)

    # Profile hero card
    st.markdown(f"""
    <div class="profile-hero-card">
        <div class="phc-avatar">{initial}</div>
        <div class="phc-info">
            <h2 class="phc-name">{name}</h2>
            <p class="phc-email">{email}</p>
            <p class="phc-role">🌾 KrushiAI Farmer · Member since {joined}</p>
        </div>
        <div class="phc-stats">
            <div class="phcs"><p class="phcs-n" style="color:#60a5fa">{stats['total'] or 0}</p><p class="phcs-l">Scans</p></div>
            <div class="phcs"><p class="phcs-n" style="color:#10b981">{stats['healthy'] or 0}</p><p class="phcs-l">Healthy</p></div>
            <div class="phcs"><p class="phcs-n" style="color:#f87171">{stats['diseased'] or 0}</p><p class="phcs-l">Diseased</p></div>
        </div>
    </div>""", unsafe_allow_html=True)

    left, right = st.columns([3,2], gap="medium")

    with left:
        st.markdown('<div class="settings-card"><p class="sc-title">Account Information</p>', unsafe_allow_html=True)
        new_name = st.text_input("Full Name", value=name, key="p_name")
        st.text_input("Email Address", value=email, disabled=True, key="p_email")
        st.text_input("Member Since",  value=joined, disabled=True, key="p_joined")
        if st.button("Save Changes", key="btn_update_name", use_container_width=True):
            if update_profile_name(user.id, new_name):
                user.name = new_name.strip()
                st.session_state.user = user
                st.success("Profile updated!")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="settings-card"><p class="sc-title">Security</p>', unsafe_allow_html=True)
        with st.expander("🔒 Change Password"):
            old  = st.text_input("Current Password", type="password", key="cp_old")
            new1 = st.text_input("New Password",     type="password", key="cp_new",  placeholder="Min. 6 characters")
            new2 = st.text_input("Confirm Password", type="password", key="cp_new2")
            if st.button("Update Password", key="btn_save_pwd", use_container_width=True):
                if not old or not new1:
                    st.error("Please fill in all fields.")
                elif new1 != new2:
                    st.error("Passwords do not match.")
                elif change_password(user.id, old, new1):
                    st.success("Password updated successfully!")
                else:
                    st.error("Current password is incorrect.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="settings-card" style="margin-top:14px">
            <p class="sc-title">Preferences</p>
            <div class="pref-row">
                <div><p class="pref-name">Email Notifications</p><p class="pref-sub">Scan result alerts</p></div>
                <div class="toggle on"></div>
            </div>
            <div class="pref-row" style="border:none;padding-bottom:0">
                <div><p class="pref-name">Weekly Reports</p><p class="pref-sub">Field health summary</p></div>
                <div class="toggle off"></div>
            </div>
        </div>""", unsafe_allow_html=True)

# ── Support ───────────────────────────────────────────────────────────────────

def _tab_support():
    st.markdown("""
    <div class="page-hero" style="text-align:center">
        <div class="hero-text">
            <h1 class="hero-title">Help & Support</h1>
            <p class="hero-sub">Find answers, guides, and get in touch with our agricultural experts.</p>
        </div>
    </div>""", unsafe_allow_html=True)

    _, sc, _ = st.columns([1,3,1])
    with sc:
        st.text_input("sq", placeholder="🔍  Search the knowledge base…", key="support_q", label_visibility="collapsed")

    st.markdown('<p class="section-label" style="margin-top:28px">Browse Topics</p>', unsafe_allow_html=True)

    topics = [
        ("🚀","Getting Started",   "Learn account setup, first scan, and platform basics."),
        ("🔬","Scanner Tips",      "Best practices for lighting, angles, and clear images."),
        ("🌿","Field Diagnostics", "Understanding results, confidence scores, and treatments."),
        ("⚙️","Account & Billing", "Manage subscriptions, invoices, and payment methods."),
        ("🤖","AI & Model Info",   "How the CNN model works and what diseases it detects."),
        ("📞","Contact Support",   "Reach our team via live chat, email, or phone."),
    ]

    left, right = st.columns([2, 1], gap="medium")
    with left:
        r1, r2 = st.columns(2, gap="medium")
        for i, (icon, title, desc) in enumerate(topics):
            with (r1 if i % 2 == 0 else r2):
                st.markdown(f"""
                <div class="topic-card">
                    <span class="tc-icon">{icon}</span>
                    <p class="tc-title">{title}</p>
                    <p class="tc-desc">{desc}</p>
                </div>""", unsafe_allow_html=True)

    with right:
        st.markdown("""
        <div class="help-card">
            <p class="hc-title">Still need help?</p>
            <p class="hc-sub">Our agronomists and support team are ready to assist.</p>
            <div class="hc-row"><span>💬</span>
                <div><p class="hci-name">Live Chat</p><p class="hci-sub">Replies in ~5 minutes</p></div>
            </div>
            <div class="hc-row"><span>✉️</span>
                <div><p class="hci-name">Email Us</p><p class="hci-sub">support@krushiai.com</p></div>
            </div>
            <div class="hc-row"><span>📖</span>
                <div><p class="hci-name">Documentation</p><p class="hci-sub">Detailed technical guides</p></div>
            </div>
        </div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
