import streamlit as st
import base64
import os
from PIL import Image
from utils.auth import sign_in, sign_up
from utils.predictor import predict_disease
from utils.database import save_scan_result, fetch_scan_history, init_db

# ── Constants ─────────────────────────────────────────────────────────────────

REMEDIES = {
    "Bacterial Blight": [
        ("Apply Fungicide Immediately",  "Use Streptocycline (0.5 g/L) + Copper Oxychloride (3 g/L) as a protectant spray."),
        ("Remove Infected Foliage",      "Carefully prune and destroy infected leaves to slow spread. Do not compost."),
        ("Avoid Overhead Irrigation",    "Switch to drip irrigation to keep foliage dry and reduce spread. Repeat every 10–14 days."),
    ],
    "Anthracnose": [
        ("Prune Infected Branches",      "Cut 15 cm below visible infection. Destroy removed material immediately."),
        ("Apply Mancozeb Spray",         "Use Mancozeb (2.5 g/L) or Carbendazim (1 g/L) spray during dry weather."),
        ("Improve Air Circulation",      "Ensure adequate spacing between plants to reduce humidity in the canopy."),
    ],
    "Alternaria": [
        ("Improve Field Drainage",       "Prevent waterlogging — Alternaria thrives in wet, humid conditions."),
        ("Apply Iprodione Fungicide",    "Apply Iprodione or Mancozeb at the recommended dose on dry foliage."),
        ("Remove Fallen Debris",         "Clear all fallen leaves and plant debris from around the base of the plant."),
    ],
    "Healthy": [
        ("Maintain Watering Schedule",   "Regular, consistent watering promotes strong root development."),
        ("Apply Balanced Fertilizer",    "Use balanced NPK fertilization monthly during the growing season."),
        ("Inspect Weekly",               "Early detection is key — inspect leaves weekly for any early signs of disease."),
    ],
}

DISEASE_META = {
    "Bacterial Blight": {"color": "#ffb4ab", "icon_bg": "#93000a", "icon": "🦠", "type": "Bacterial Pathogen", "severity": "High Risk",   "detected": True},
    "Anthracnose":      {"color": "#ffb4ab", "icon_bg": "#93000a", "icon": "🦠", "type": "Fungal Pathogen",    "severity": "High Risk",   "detected": True},
    "Alternaria":       {"color": "#e8b84b", "icon_bg": "#5a3a00", "icon": "🦠", "type": "Fungal Infection",   "severity": "Medium Risk", "detected": True},
    "Healthy":          {"color": "#95d4b3", "icon_bg": "#2d6a4f", "icon": "🌿", "type": "No Disease Detected","severity": "No Risk",     "detected": False},
}

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
                f'style="width:{size}px;height:{size}px;border-radius:8px;object-fit:cover;">')
    return "🌿"

def _nav_btn(label: str, key: str, page: str):
    if st.session_state.page == page:
        st.markdown('<span class="nav-hint"></span>', unsafe_allow_html=True)
    if st.button(label, key=key, use_container_width=True):
        st.session_state.page = page
        st.rerun()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="KrushiAI",
        layout="wide",
        page_icon="🌿",
        initial_sidebar_state="expanded",
    )
    init_db()
    _load_css()

    st.session_state.setdefault("user",        None)
    st.session_state.setdefault("page",        "scanner")
    st.session_state.setdefault("last_result", None)
    st.session_state.setdefault("auth_tab",    "login")

    if not st.session_state.user:
        _page_login()
    else:
        _page_dashboard()

# ── Login ─────────────────────────────────────────────────────────────────────

def _page_login():
    st.markdown("""<style>
    [data-testid="stSidebar"]{display:none!important}
    [data-testid="stSidebarCollapseButton"]{display:none!important}
    [data-testid="collapsedControl"]{display:none!important}
    </style>""", unsafe_allow_html=True)

    bg = "assets/images/login_bg.jpg"
    if os.path.exists(bg):
        st.markdown(f"""<style>
        [data-testid="stAppViewContainer"]{{
            background: url("data:image/jpg;base64,{_b64(bg)}") center/cover fixed;
        }}
        [data-testid="stAppViewContainer"]::before{{
            content:'';position:fixed;inset:0;
            background:rgba(15,20,27,0.80);
            backdrop-filter:blur(2px);z-index:0;
        }}
        [data-testid="stMain"]{{position:relative;z-index:1;}}
        </style>""", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.05, 1])
    with col:
        logo = _logo_tag(64)
        st.markdown(f"""
        <div class="auth-card">
            <div class="auth-brand">
                {logo}
                <h1 class="auth-title">KrushiAI</h1>
                <p class="auth-sub">Plant Disease Intelligence Platform</p>
            </div>""", unsafe_allow_html=True)

        if st.session_state.auth_tab == "login":
            st.markdown('<label class="field-label">Email Address</label>', unsafe_allow_html=True)
            email = st.text_input("_e1", placeholder="Enter your email",    key="li_email", label_visibility="collapsed")
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown('<label class="field-label">Password</label>', unsafe_allow_html=True)
            with c2:
                st.markdown('<span class="forgot-link">Forgot?</span>', unsafe_allow_html=True)
            pwd = st.text_input("_p1", type="password", placeholder="Enter your password", key="li_pwd", label_visibility="collapsed")

            if st.button("Sign In", use_container_width=True, key="btn_login"):
                if not email or not pwd:
                    st.warning("Please fill in both fields.")
                else:
                    with st.spinner("Signing in…"):
                        result = sign_in(email, pwd)
                    if result:
                        st.session_state.user        = result.user
                        st.session_state.page        = "scanner"
                        st.session_state.last_result = None
                        st.rerun()

            if st.button("Create Account", use_container_width=True, key="btn_go_signup"):
                st.session_state.auth_tab = "signup"
                st.rerun()

        else:
            st.markdown('<label class="field-label">Full Name</label>',     unsafe_allow_html=True)
            name  = st.text_input("_n2", placeholder="Your full name",    key="su_name",  label_visibility="collapsed")
            st.markdown('<label class="field-label">Email Address</label>', unsafe_allow_html=True)
            email = st.text_input("_e2", placeholder="Enter your email",   key="su_email", label_visibility="collapsed")
            st.markdown('<label class="field-label">Password</label>',      unsafe_allow_html=True)
            pwd   = st.text_input("_p2", type="password", placeholder="Min. 6 characters", key="su_pwd", label_visibility="collapsed")

            if st.button("Create Account", use_container_width=True, key="btn_signup"):
                if not name or not email or not pwd:
                    st.warning("Please fill in all fields.")
                elif len(pwd) < 6:
                    st.warning("Password must be at least 6 characters.")
                else:
                    with st.spinner("Creating account…"):
                        ok = sign_up(email, pwd, name)
                    if ok:
                        st.success("Account created! Please sign in.")
                        st.session_state.auth_tab = "login"
                        st.rerun()

            if st.button("Back to Sign In", use_container_width=True, key="btn_go_login"):
                st.session_state.auth_tab = "login"
                st.rerun()

        st.markdown("""
            <p class="auth-terms">
                By signing in, you agree to our
                <a href="#" class="auth-link">Terms of Service</a> and
                <a href="#" class="auth-link">Privacy Policy</a>.
            </p>
        </div>""", unsafe_allow_html=True)

# ── Dashboard ─────────────────────────────────────────────────────────────────

def _page_dashboard():
    # Force sidebar open via JS (handles localStorage-persisted collapsed state)
    import streamlit.components.v1 as components
    components.html("""<script>
    (function() {
        function tryOpen() {
            var btn = window.parent.document.querySelector('[data-testid="collapsedControl"]');
            if (btn) { btn.click(); return; }
        }
        setTimeout(tryOpen, 200);
        setTimeout(tryOpen, 600);
    })();
    </script>""", height=0)

    user    = st.session_state.user
    name    = user.email.split("@")[0].title()
    initial = name[0].upper()

    with st.sidebar:
        logo = _logo_tag(38)
        st.markdown(f"""
        <div class="sb-brand">
            <div class="sb-logo-wrap">{logo}</div>
            <div>
                <div class="sb-name">KrushiAI</div>
                <div class="sb-sub">Plant Intelligence</div>
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div class="new-scan-wrap">', unsafe_allow_html=True)
        if st.button("+ New Scan", key="btn_new_scan", use_container_width=True):
            st.session_state.last_result = None
            st.session_state.page        = "scanner"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="nav-section">', unsafe_allow_html=True)
        _nav_btn("AI Scanner",   "nav_scanner", "scanner")
        _nav_btn("Scan History", "nav_history",  "history")
        _nav_btn("Profile",      "nav_profile",  "profile")
        _nav_btn("Support",      "nav_support",  "support")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sb-spacer"></div>', unsafe_allow_html=True)
        st.markdown('<div class="logout-wrap">', unsafe_allow_html=True)
        if st.button("Logout", key="btn_logout", use_container_width=True):
            st.session_state.user        = None
            st.session_state.last_result = None
            st.session_state.page        = "scanner"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Top app bar
    st.markdown(f"""
    <header class="top-bar">
        <span class="top-brand">KrushiAI</span>
        <div class="top-user">
            <div class="top-avatar">{initial}</div>
            <span class="top-name">{name}</span>
        </div>
    </header>""", unsafe_allow_html=True)

    page = st.session_state.page
    if   page == "scanner": _tab_scanner()
    elif page == "history": _tab_history()
    elif page == "profile": _tab_profile()
    elif page == "support": _tab_support()

# ── Scanner ───────────────────────────────────────────────────────────────────

def _tab_scanner():
    st.markdown("""
    <div class="page-head">
        <h1 class="page-title">Diagnostic Scanner</h1>
        <p class="page-sub">Upload or capture an image of a leaf to identify potential pathogens.</p>
    </div>""", unsafe_allow_html=True)

    left, right = st.columns(2, gap="medium")

    with left:
        uploaded = st.file_uploader("leaf", type=["jpg","jpeg","png"], label_visibility="collapsed")
        if not uploaded:
            st.markdown("""
            <div class="upload-zone">
                <span class="upload-icon material-icons">eco</span>
                <p class="upload-title">Upload Leaf Image</p>
                <p class="upload-hint">Drag and drop, or click to browse. Ensure good lighting and clear focus on the affected area.</p>
            </div>""", unsafe_allow_html=True)
        else:
            img = Image.open(uploaded)
            st.image(img, use_container_width=True)
            if st.button("Analyze Leaf", key="btn_analyze", use_container_width=True):
                with st.spinner("Analyzing…"):
                    label, conf = predict_disease(img)
                save_scan_result(st.session_state.user.id, label, conf)
                st.session_state.last_result = {"label": label, "conf": conf}
                st.rerun()

    with right:
        res = st.session_state.get("last_result")
        if not res:
            st.markdown("""
            <div class="result-empty">
                <p class="re-title">No Analysis Yet</p>
                <p class="re-sub">Upload a leaf image and click Analyze Leaf to see the AI diagnosis here.</p>
            </div>""", unsafe_allow_html=True)
        else:
            label = res["label"]
            conf  = res["conf"]
            meta  = DISEASE_META.get(label, {"color":"#bfc9c1","icon_bg":"#30353d","icon":"🌿","type":"Unknown","severity":"Unknown","detected":False})
            steps = REMEDIES.get(label, [])

            if meta["detected"]:
                badge_html = '<div class="badge-disease"><span>⚠</span> DISEASE DETECTED</div>'
                conf_color = "var(--error)"
            else:
                badge_html = '<div class="badge-healthy"><span>✓</span> HEALTHY PLANT</div>'
                conf_color = "var(--primary)"

            treat_items = "".join(
                f'<li class="treat-item">'
                f'<span class="treat-icon">✓</span>'
                f'<div><strong class="treat-title">{t}</strong>'
                f'<span class="treat-desc">{d}</span></div>'
                f'</li>'
                for t, d in steps
            )

            st.markdown(f"""
            <div class="result-card">
                <div class="result-header">
                    <div>
                        {badge_html}
                        <h2 class="result-name">{label}</h2>
                        <p class="result-type">{meta['type']}</p>
                    </div>
                    <div class="conf-block">
                        <span class="conf-pct" style="color:{conf_color}">{conf:.0f}%</span>
                        <span class="conf-lbl">CONFIDENCE</span>
                        <div class="conf-bar-track">
                            <div class="conf-bar-fill" style="width:{conf:.0f}%;background:{conf_color}"></div>
                        </div>
                    </div>
                </div>
                <div class="result-meta">
                    <span class="meta-key">Severity:</span>
                    <span class="meta-val" style="color:{meta['color']}">{meta['severity']}</span>
                </div>
                <div class="treat-box">
                    <h3 class="treat-head">Treatment Plan</h3>
                    <ul class="treat-list">{treat_items}</ul>
                </div>
            </div>""", unsafe_allow_html=True)

# ── History ───────────────────────────────────────────────────────────────────

def _tab_history():
    st.markdown("""
    <div class="page-head">
        <h1 class="page-title">Scan History</h1>
        <p class="page-sub">Review your recent plant diagnostics and field analyses.</p>
    </div>""", unsafe_allow_html=True)

    history  = fetch_scan_history(st.session_state.user.id)
    total    = len(history)
    healthy  = sum(1 for s in history if s["disease_type"] == "Healthy")
    diseased = total - healthy

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        st.markdown(f"""<div class="stat-card">
            <p class="stat-label">TOTAL SCANS</p>
            <p class="stat-num">{total}</p>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="stat-card stat-ok">
            <p class="stat-label">HEALTHY</p>
            <p class="stat-num" style="color:var(--primary)">{healthy}</p>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="stat-card stat-bad">
            <p class="stat-label">DISEASED</p>
            <p class="stat-num" style="color:var(--error)">{diseased}</p>
        </div>""", unsafe_allow_html=True)

    if not history:
        st.markdown("""
        <div class="empty-state">
            <p class="empty-title">No scans yet</p>
            <p class="empty-sub">Your scan history will appear here after your first analysis.</p>
        </div>""", unsafe_allow_html=True)
        return

    rows = ""
    for s in history:
        lbl  = s["disease_type"]
        conf = s["confidence"]
        date = str(s["created_at"])[5:16]
        meta = DISEASE_META.get(lbl, {"color":"#95d4b3","icon_bg":"#2d6a4f","icon":"🌿","type":"Unknown","detected":False})
        rows += f"""
        <div class="hist-row">
            <div class="hist-icon" style="background:{meta['icon_bg']}">{meta['icon']}</div>
            <div class="hist-info">
                <p class="hist-name">{lbl}</p>
                <div class="hist-meta">
                    <span>{meta['type']}</span>
                    <span class="hist-dot"></span>
                    <span>{date}</span>
                </div>
            </div>
            <div class="hist-right">
                <p class="hist-pct" style="color:{meta['color']}">{conf:.0f}%</p>
                <p class="hist-pct-lbl">Confidence</p>
            </div>
        </div>"""
    st.markdown(f'<div class="hist-list">{rows}</div>', unsafe_allow_html=True)

# ── Profile ───────────────────────────────────────────────────────────────────

def _tab_profile():
    user    = st.session_state.user
    email   = user.email
    name    = email.split("@")[0].title()
    initial = name[0].upper()
    joined  = str(getattr(user, "created_at", "—"))[:10]
    history = fetch_scan_history(user.id)
    total   = len(history)
    healthy = sum(1 for s in history if s["disease_type"] == "Healthy")

    st.markdown("""
    <div class="page-head">
        <h1 class="page-title">Profile Settings</h1>
        <p class="page-sub">Manage your personal information and application preferences.</p>
    </div>""", unsafe_allow_html=True)

    # Profile hero
    st.markdown(f"""
    <div class="profile-hero">
        <div class="prof-avatar">{initial}</div>
        <div class="prof-hero-info">
            <p class="prof-name">{name}</p>
            <p class="prof-role">KrushiAI Farmer</p>
        </div>
    </div>""", unsafe_allow_html=True)

    left, right = st.columns([3, 2], gap="medium")
    with left:
        st.markdown('<div class="settings-card"><p class="sc-title">User Information</p>', unsafe_allow_html=True)
        st.text_input("Email Address",  value=email,                  disabled=True, key="p_email")
        st.text_input("Member Since",   value=joined,                 disabled=True, key="p_joined")
        st.text_input("Institution",    value="Sanjivani University",  disabled=True, key="p_inst")
        st.markdown(f"""
        <div class="prof-stats">
            <div class="ps"><p class="ps-n">{total}</p><p class="ps-l">Total Scans</p></div>
            <div class="ps"><p class="ps-n" style="color:var(--primary)">{healthy}</p><p class="ps-l">Healthy</p></div>
            <div class="ps"><p class="ps-n" style="color:var(--error)">{total-healthy}</p><p class="ps-l">Diseased</p></div>
        </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown("""
        <div class="settings-card">
            <p class="sc-title">Preferences</p>
            <div class="pref-row">
                <div><p class="pref-name">Push Notifications</p><p class="pref-sub">Alerts for scan results</p></div>
                <div class="toggle on"></div>
            </div>
            <div class="pref-row" style="border:none">
                <div><p class="pref-name">Weekly Reports</p><p class="pref-sub">Email summary</p></div>
                <div class="toggle off"></div>
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div class="settings-card" style="margin-top:16px"><p class="sc-title">Security</p>', unsafe_allow_html=True)
        if st.button("Change Password", key="btn_pwd", use_container_width=True):
            st.info("Coming soon.")
        st.markdown('<button class="danger-btn">Delete Account</button></div>', unsafe_allow_html=True)

# ── Support ───────────────────────────────────────────────────────────────────

def _tab_support():
    st.markdown("""
    <div class="page-head" style="text-align:center">
        <h1 class="page-title">Help &amp; Support</h1>
        <p class="page-sub">How can we assist you today? Search our knowledge base or browse categories below.</p>
    </div>""", unsafe_allow_html=True)

    st.text_input("support_q", placeholder="Search for guides, diagnostic help, billing...", key="sq", label_visibility="collapsed")
    st.markdown('<p class="section-title">Browse Topics</p>', unsafe_allow_html=True)

    left, right = st.columns([2.2, 1], gap="medium")
    topics = [
        ("🚀", "Getting Started",   "Learn the basics of setting up your account and taking your first plant scan."),
        ("🔬", "AI Scanner Tips",   "Best practices for lighting, angles, and capturing clear images for accurate results."),
        ("🌿", "Field Diagnostics", "Understanding your results, confidence scores, and treatment recommendations."),
        ("⚙️", "Account & Billing", "Manage your subscription, invoices, and update payment methods."),
    ]
    with left:
        r1, r2 = st.columns(2, gap="medium")
        cols = [r1, r2, r1, r2]
        for (icon, title, desc), col in zip(topics, cols):
            with col:
                st.markdown(f"""
                <div class="topic-card">
                    <p class="tc-icon">{icon}</p>
                    <p class="tc-title">{title}</p>
                    <p class="tc-desc">{desc}</p>
                </div>""", unsafe_allow_html=True)

    with right:
        st.markdown("""
        <div class="help-card">
            <p class="hc-title">Still need help?</p>
            <p class="hc-sub">Our agronomists and technical support team are here to assist you.</p>
            <div class="hc-row"><span>💬</span><div><p class="hci-name">Live Chat</p><p class="hci-sub">Typically replies in 5 mins</p></div></div>
            <div class="hc-row"><span>✉️</span><div><p class="hci-name">Send an Email</p><p class="hci-sub">support@krushiai.com</p></div></div>
            <div class="hc-row"><span>📖</span><div><p class="hci-name">Read Documentation</p><p class="hci-sub">Detailed technical guides</p></div></div>
        </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
