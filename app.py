"""📰 Real vs Fake News Detector — powered by a FREE LLM API """

import os
import re
import json
import time
import base64
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from openai import OpenAI

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Real vs Fake News Detector",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# BACKGROUND IMAGE (uploaded newspaper collage)
# ============================================================
# Put your image at Images/photo.png (already done for you here).
# This reads it once and base64-encodes it so it can be embedded straight
# into the CSS `background-image` rule below — no external hosting needed.
BACKGROUND_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "Images", "photo.png")

@st.cache_data
def _get_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

_bg_css = ""
if os.path.exists(BACKGROUND_IMAGE_PATH):
    _bg_b64 = _get_base64(BACKGROUND_IMAGE_PATH)
    _bg_css = f"""
    .stApp {{
        background-image:
            linear-gradient(135deg, rgba(15,23,42,0.65) 0%, rgba(30,41,59,0.55) 50%, rgba(15,23,42,0.65) 100%),
            url("data:image/jpeg;base64,{_bg_b64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    """
else:
    # Loud, not silent: tells you exactly why the background isn't showing
    # instead of quietly falling back to the plain gradient.
    st.warning(f"⚠️ Background image not found at: `{BACKGROUND_IMAGE_PATH}` — using default gradient instead.")

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown(f"""
<style>
    {_bg_css if _bg_css else '''
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    }
    '''}
    .title-wrap {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.6rem;
        flex-wrap: wrap;
    }}
    .title-icon {{
        width: clamp(2.6rem, 6vw, 4.6rem);
        height: clamp(2.6rem, 6vw, 4.6rem);
        flex-shrink: 0;
        filter: drop-shadow(0 0 20px rgba(167, 139, 250, 0.45));
    }}
    .main-title {{
    font-size: clamp(2.5rem, 5vw, 3.5rem) !important;
    font-weight: 900;
    text-align: center;
    line-height: 1.1;
    letter-spacing: -0.02em;

    background: linear-gradient(
        90deg,
        #38bdf8,
        #a78bfa,
        #f472b6,
        #a78bfa,
        #38bdf8
    );
    background-size: 300% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;

    filter: drop-shadow(0 0 25px rgba(167,139,250,.35));
    animation: shine 6s linear infinite;

    margin: 0;
    padding-bottom: 0.15em;
}}
    @keyframes shine {{
        to {{ background-position: 300% center; }}
    }}
    .subtitle {{
        text-align: center;
        color: #e2e8f0;
        font-size: 1.1rem;
        margin-top: 0;
        margin-bottom: 2rem;
    }}
    .card {{
        background: rgba(15, 23, 42, 0.55);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 16px;
        padding: 1.5rem 2rem;
        backdrop-filter: blur(10px);
        margin-bottom: 1.5rem;
    }}
    .result-real {{
        background: linear-gradient(135deg, rgba(16,185,129,0.15), rgba(16,185,129,0.05));
        border: 1px solid #10b981;
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        backdrop-filter: blur(10px);
    }}
    .result-fake {{
        background: linear-gradient(135deg, rgba(239,68,68,0.15), rgba(239,68,68,0.05));
        border: 1px solid #ef4444;
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        backdrop-filter: blur(10px);
    }}
    .result-label-real {{ color: #10b981; font-size: 2rem; font-weight: 800; }}
    .result-label-fake {{ color: #ef4444; font-size: 2rem; font-weight: 800; }}
    .explanation-box {{
        background: rgba(255,255,255,0.06);
        border-left: 3px solid #38bdf8;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        color: #cbd5e1;
        margin-top: 1rem;
        backdrop-filter: blur(10px);
    }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
    .stTabs [data-baseweb="tab"] {{
        background-color: rgba(255,255,255,0.08);
        border-radius: 8px;
        padding: 10px 20px;
        color: #cbd5e1;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: rgba(56,189,248,0.25) !important;
        color: #38bdf8 !important;
    }}
    div[data-testid="stMetric"] {{
        background: rgba(255,255,255,0.07);
        border-radius: 12px;
        padding: 10px;
        border: 1px solid rgba(255,255,255,0.1);
        backdrop-filter: blur(10px);
    }}

    /* ---------- HOME / LANDING PAGE ---------- */
    .hero-badge {{
        display: inline-block;
        background: rgba(167, 139, 250, 0.15);
        border: 1px solid rgba(167, 139, 250, 0.35);
        color: #c4b5fd;
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        padding: 0.35rem 1rem;
        border-radius: 999px;
        margin-bottom: 1.5rem;
    }}
    .hero-wrap {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }}

    .hero-desc {{
        width: 90%;
        max-width: 1100px;
        text-align: center;
        margin: 1.5rem auto 4rem auto;
        color: #e2e8f0;
        font-size: 1.25rem;
        line-height: 1.8;
    }}
    .feature-chip {{
        background: rgba(15, 23, 42, 0.5);
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 16px;
        padding: 1.6rem 1.2rem;
        text-align: center;
        height: 100%;
        transition: transform 0.2s ease, border-color 0.2s ease;
        backdrop-filter: blur(10px);
    }}
    .feature-chip:hover {{
        transform: translateY(-4px);
        border-color: rgba(167, 139, 250, 0.5);
    }}
    .feature-icon {{ font-size: 2.2rem; margin-bottom: 0.6rem; }}
    .feature-title {{ color: #f1f5f9; font-weight: 700; font-size: 1.05rem; margin-bottom: 0.3rem; }}
    .feature-text {{ color: #94a3b8; font-size: 0.9rem; line-height: 1.5; }}

    div[data-testid="stButton"] button[kind="primary"] {{
        background: linear-gradient(90deg, #38bdf8, #a78bfa, #f472b6);
        border: none;
        font-weight: 700;
        letter-spacing: 0.02em;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}
    div[data-testid="stButton"] button[kind="primary"]:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(167, 139, 250, 0.4);
    }}

    /* ---------- Developer credit ---------- */
    .dev-credit {{
        text-align: center;
        margin-top: 1.2rem;
        padding-bottom: 0.8rem;
    }}
    .dev-credit span {{
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.85rem;
        color: #cbd5e1;
        font-weight: 600;
        padding: 0.4rem 1.1rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.15);
        backdrop-filter: blur(10px);
    }}
    .dev-credit span .dev-name {{
        background: linear-gradient(90deg, #38bdf8, #a78bfa, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }}
</style>
""", unsafe_allow_html=True)

def render_dev_credit():
    """Small developer-credit badge — shown at the bottom of both the
    home page and the tool page."""
    st.markdown(
        """
        <div class="dev-credit">
            <span>👨‍💻 Developed by&nbsp;<span class="dev-name">Paramjeet Lamba</span></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("""
<div class="title-wrap">
    <svg class="title-icon" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="titleIconGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#38bdf8"/>
                <stop offset="50%" stop-color="#a78bfa"/>
                <stop offset="100%" stop-color="#f472b6"/>
            </linearGradient>
        </defs>
        <rect x="6" y="14" width="44" height="38" rx="3" fill="url(#titleIconGrad)"/>
        <path d="M50 20 H56 A2 2 0 0 1 58 22 V48 A6 6 0 0 1 52 54 H14"
              fill="none" stroke="url(#titleIconGrad)" stroke-width="3" stroke-linecap="round"/>
        <rect x="12" y="20" width="26" height="6" rx="1.5" fill="#0f172a" opacity="0.85"/>
        <rect x="12" y="30" width="32" height="3" rx="1.5" fill="#0f172a" opacity="0.65"/>
        <rect x="12" y="36" width="32" height="3" rx="1.5" fill="#0f172a" opacity="0.65"/>
        <rect x="12" y="42" width="22" height="3" rx="1.5" fill="#0f172a" opacity="0.65"/>
    </svg>
    <p class="main-title">Real vs Fake News Detector</p>
</div>
""", unsafe_allow_html=True)
st.markdown('<p class="subtitle">Paste an article, or upload one (or many) .txt files — verify live</p>', unsafe_allow_html=True)

# ============================================================
# SESSION STATE — Home page <-> Tool page navigation
# ============================================================
if "page" not in st.session_state:
    st.session_state.page = "home"

def _go_to_app():
    st.session_state.page = "app"

def _go_to_home():
    st.session_state.page = "home"

# ============================================================
# HOME PAGE
# ============================================================
if st.session_state.page == "home":
    st.markdown("""
    <div class="hero-wrap">
        <div class="hero-badge">✨ POWERED BY LIVE AI FACT-CHECKING</div>
        <p class="hero-desc">
            Paste a headline, upload a single article, or drop in a whole .txt file
            packed with multiple news items — this tool checks every single one and
            tells you exactly which are REAL and which are FAKE, with a confidence
            score and a plain-English explanation for each verdict.
            </p>
    </div>
    """, unsafe_allow_html=True)


    col1, col2, col3 = st.columns(3, gap="medium")
    with col1:
        st.markdown("""
        <div class="feature-chip">
            <div class="feature-icon">✍️</div>
            <div class="feature-title">Paste any text</div>
            <div class="feature-text">Drop in a headline or full article and get an instant verdict.</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="feature-chip">
            <div class="feature-icon">📄</div>
            <div class="feature-title">Upload .txt files</div>
            <div class="feature-text">One file, many files, or many headlines per file — every line gets analyzed.</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="feature-chip">
            <div class="feature-icon">📊</div>
            <div class="feature-title">Clear breakdown</div>
            <div class="feature-text">See Real vs Fake counts, per-item confidence, and export results as CSV.</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.write("")
    spacer_l, cta_col, spacer_r = st.columns([1, 1.2, 1])
    with cta_col:
        st.button("🚀 Start Detecting", type="primary", use_container_width=True,
                   on_click=_go_to_app, key="cta_start")

    st.markdown("---")
    st.caption(
        "⚠️ This is an AI-generated estimate, not definitive fact-checking. "
        "Always verify important news through trusted, reputable sources."
    )
    render_dev_credit()
    st.stop()

# ============================================================
# TOOL PAGE (only reached after clicking "Start Detecting")
# ============================================================
back_l, back_r = st.columns([1, 6])
with back_l:
    st.button("⬅ Home", on_click=_go_to_home, key="back_home")

# ============================================================
# PROVIDER CONFIG — pick ONE provider here (not shown to users)
# ============================================================
# Change this single line to switch providers app-wide.
ACTIVE_PROVIDER = "Groq (free)"   # options: "Groq (free)", "Gemini (free)", "OpenAI (paid)"

PROVIDERS = {
    "Groq (free)": {
        "base_url": "https://api.groq.com/openai/v1",
        # llama-3.3-70b-versatile was deprecated by Groq (announced 2026-06-17) —
        # openai/gpt-oss-120b is Groq's recommended replacement.
        "default_model": "openai/gpt-oss-120b",
        "secret_key": "GROQ_API_KEY",
    },
    "Gemini (free)": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-2.5-flash",
        "secret_key": "GEMINI_API_KEY",
    },
    "OpenAI (paid)": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "secret_key": "OPENAI_API_KEY",
    },
}

provider_cfg = PROVIDERS[ACTIVE_PROVIDER]

def _load_model_name() -> str:
    """
    Model name, with an optional override so a provider deprecating/renaming
    a model (as Groq did with llama-3.3-70b-versatile) doesn't require a
    code change — just set MODEL_NAME in Secrets or as an env var.
    Falls back to each provider's default_model above.
    """
    try:
        if "MODEL_NAME" in st.secrets:
            return st.secrets["MODEL_NAME"]
    except Exception:
        pass
    return os.environ.get("MODEL_NAME", provider_cfg["default_model"])

model_name = _load_model_name()

def _load_api_key() -> str:
    """
    Load the key server-side only — never rendered in any widget.
    Priority: Streamlit secrets (st.secrets) -> environment variable.
    Locally: put it in .streamlit/secrets.toml (gitignored).
    On Streamlit Community Cloud: paste it into the app's
    Settings -> Secrets panel (only you, the app owner, can see/edit it).
    """
    key_name = provider_cfg["secret_key"]
    try:
        if key_name in st.secrets:
            return st.secrets[key_name]
    except Exception:
        pass
    return os.environ.get(key_name, "")

api_key_input = _load_api_key()

with st.sidebar:
    st.markdown("### 🧭 How to use")
    st.write(
        "1. Go to **Paste Text** or **Upload Article File(s)**\n"
        "2. Click **Analyze**\n"
        "3. Review Real/Fake, confidence & explanation\n"
        "4. Download the results as CSV"
    )
    st.markdown("---")
    st.caption("Built with Streamlit · LLM API · Plotly")

# ============================================================
# LLM CALL — the core "Send article to LLM API" step
# ============================================================
SYSTEM_PROMPT = (
    "You are a fact-checking assistant that evaluates whether a piece of "
    "news text is REAL (credible, factual reporting) or FAKE (misinformation, "
    "hoax, satire presented as fact, or fabricated claims). "
    "Base your judgment on writing style, sensationalism, factual plausibility, "
    "internal consistency, and known misinformation patterns. "
    "Always respond with STRICT JSON only, no markdown, no extra text, in "
    "exactly this format: "
    '{"verdict": "REAL" or "FAKE", "confidence": integer 0-100, '
    '"explanation": "2-3 sentence explanation of the reasoning"}'
)

def get_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=provider_cfg["base_url"])

def classify_article(client: OpenAI, model: str, article_text: str, retries: int = 2):
    """Send one article to the LLM API and parse REAL/FAKE, confidence, explanation."""
    article_text = (article_text or "").strip()
    if not article_text:
        return {"verdict": "UNKNOWN", "confidence": 0, "explanation": "Empty article text."}

    # Guard against extremely long articles blowing up token usage/cost
    trimmed = article_text[:6000]

    last_error = None
    for attempt in range(retries + 1):
        try:
            try:
                # Most providers (Groq, OpenAI, Gemini's OpenAI-compat layer)
                # support forcing strict JSON output this way.
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Analyze this news article:\n\n{trimmed}"},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0,
                )
            except Exception:
                # Fallback for models/providers that reject response_format
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Analyze this news article:\n\n{trimmed}"},
                    ],
                    temperature=0,
                )
            raw = response.choices[0].message.content

            # Extract the JSON object even if the model wrapped it in text/markdown
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            data = json.loads(match.group(0) if match else raw)

            verdict = str(data.get("verdict", "UNKNOWN")).upper().strip()
            if verdict not in ("REAL", "FAKE"):
                verdict = "UNKNOWN"
            confidence = data.get("confidence", 0)
            try:
                confidence = max(0, min(100, float(confidence)))
            except (ValueError, TypeError):
                confidence = 0
            explanation = str(data.get("explanation", "")).strip() or "No explanation returned."

            return {"verdict": verdict, "confidence": confidence, "explanation": explanation}

        except Exception as e:
            last_error = e
            time.sleep(1.5 * (attempt + 1))  # simple backoff before retrying

    return {"verdict": "ERROR", "confidence": 0, "explanation": f"API error: {last_error}"}

def confidence_gauge(confidence: float, label: str):
    color = "#10b981" if label == "REAL" else ("#ef4444" if label == "FAKE" else "#64748b")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=confidence,
        number={"suffix": "%", "font": {"color": color, "size": 36}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#94a3b8"},
            "bar": {"color": color},
            "bgcolor": "rgba(255,255,255,0.05)",
            "borderwidth": 0,
        },
        domain={"x": [0, 1], "y": [0, 1]},
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e2e8f0"},
    )
    return fig

def render_result_card(result: dict):
    verdict = result["verdict"]
    confidence = result["confidence"]
    explanation = result["explanation"]

    if verdict == "REAL":
        css_class, label_class, icon = "result-real", "result-label-real", "✅"
    elif verdict == "FAKE":
        css_class, label_class, icon = "result-fake", "result-label-fake", "🚫"
    else:
        css_class, label_class, icon = "card", "result-label-real", "⚠️"

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(f"""
            <div class="{css_class}">
                <div style="font-size:2.5rem;">{icon}</div>
                <div class="{label_class}">{verdict} NEWS</div>
                <div style="color:#94a3b8;">Model confidence: {confidence}%</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.plotly_chart(confidence_gauge(confidence, verdict), use_container_width=True)

    st.markdown(f'<div class="explanation-box"><b>💡 Explanation:</b><br>{explanation}</div>', unsafe_allow_html=True)

# ============================================================
# SHARED BATCH-ANALYSIS ENGINE
# Used by BOTH tabs: pastes multiple items in Tab 1, or files in Tab 2,
# get the exact same treatment — per-item verdicts, counts, pie chart,
# table, and CSV export.
# ============================================================
def run_batch_analysis(articles, api_key: str, csv_filename: str, source_note: str = ""):
    """
    articles: list of (label, text) tuples — one per news item.
    Analyzes every item, then renders the full breakdown UI.
    Handles the 0 / 1 / many cases identically wherever it's called from.
    """
    if not articles:
        st.warning("No article text found.")
        return

    client = get_client(api_key)

    # ---- Exactly one article: show the simple single-result card ----
    if len(articles) == 1:
        label, text = articles[0]
        with st.spinner("Sending article to the LLM API..."):
            result = classify_article(client, model_name, text)
        if result["verdict"] == "ERROR":
            st.error(result["explanation"])
        else:
            render_result_card(result)
        return

    # ---- Multiple articles: analyze EVERY item, then show full batch results ----
    labels, previews, verdicts, confidences, explanations = [], [], [], [], []
    progress = st.progress(0.0, text="Starting analysis...")

    for i, (label, text) in enumerate(articles):
        result = classify_article(client, model_name, text)
        labels.append(label)
        previews.append(text[:120] + ("..." if len(text) > 120 else ""))
        verdicts.append(result["verdict"])
        confidences.append(result["confidence"])
        explanations.append(result["explanation"])
        progress.progress(
            (i + 1) / len(articles),
            text=f"Analyzed {i + 1}/{len(articles)} news items..."
        )

    progress.empty()

    df_results = pd.DataFrame({
        "source": labels,
        "news_text": previews,
        "verdict": verdicts,
        "confidence_%": confidences,
        "explanation": explanations,
    })

    success_msg = f"Analyzed {len(df_results)} news items"
    if source_note:
        success_msg += f" {source_note}"
    st.success(success_msg + ".")

    # ---- Display results: counts ----
    real_count = (df_results["verdict"] == "REAL").sum()
    fake_count = (df_results["verdict"] == "FAKE").sum()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total News Items", len(df_results))
    col2.metric("✅ Real", int(real_count))
    col3.metric("🚫 Fake", int(fake_count))

    # ---- Display results: pie chart ----
    pie = go.Figure(data=[go.Pie(
        labels=["Real", "Fake"],
        values=[real_count, fake_count],
        hole=0.55,
        marker=dict(colors=["#10b981", "#ef4444"]),
    )])
    pie.update_layout(
        height=300, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", font={"color": "#e2e8f0"},
        legend=dict(orientation="h", y=-0.1),
    )
    st.plotly_chart(pie, use_container_width=True)

    # ---- Display results: which specific news item is real vs fake ----
    st.markdown("#### 📋 Per-item results")
    st.dataframe(
        df_results, use_container_width=True, height=400,
        column_config={
            "source": "Source",
            "news_text": "News text",
            "verdict": "Verdict",
            "confidence_%": st.column_config.NumberColumn("Confidence %", format="%.1f%%"),
            "explanation": "Explanation",
        },
    )

    # ---- Download CSV ----
    csv_out = df_results.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Results as CSV",
        data=csv_out,
        file_name=csv_filename,
        mime="text/csv",
        use_container_width=True,
        key=f"download_{csv_filename}",
    )

# ============================================================
# MAIN TABS
# ============================================================
tab1, tab2 = st.tabs(["✍️ Paste Text", "📄 Upload Article File(s)"])

# ---------------- TAB 1: Paste text — one item OR many (one per line) ----------------
with tab1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Paste a news article")
    st.caption(
        "Paste a single headline/article, or paste **multiple news items — one per "
        "line** — and every line will be analyzed individually with a full Real vs "
        "Fake breakdown, just like the file upload tab."
    )
    article_text = st.text_area(
        "Article text", height=250,
        placeholder="Paste a single article, or multiple headlines/articles (one per line)...",
        label_visibility="collapsed",
    )
    max_items_paste = st.slider(
        "Max news items to analyze (protects against huge API bills)",
        1, 300, 50, key="max_items_paste"
    )
    analyze_clicked = st.button("🔍 Analyze", type="primary", use_container_width=True, key="btn_text")
    st.markdown('</div>', unsafe_allow_html=True)

    if analyze_clicked:
        if not api_key_input:
            st.error("This app is not configured yet — the app owner needs to add an API key in Secrets. Contact the app owner.")
        elif not article_text.strip():
            st.warning("Please paste some article text first.")
        else:
            # Split into one article per non-empty line, same rule Tab 2 uses.
            lines = [ln.strip() for ln in article_text.splitlines() if ln.strip()]
            if len(lines) <= 1:
                articles = [("Pasted text", article_text.strip())]
            else:
                articles = [(f"Line {idx}", ln) for idx, ln in enumerate(lines, start=1)]

            articles = articles[:max_items_paste]
            run_batch_analysis(articles, api_key_input, csv_filename="news_predictions_pasted.csv")

# ---------------- TAB 2: Upload file(s) — every news line is analyzed ----------------
with tab2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Upload news article file(s) (.txt)")
    st.caption(
        "Upload one or more .txt files. If a file contains **multiple news items "
        "(one per line)**, every line is treated as a separate article and analyzed "
        "individually — not just the first line or the file as a whole."
    )
    uploaded_files = st.file_uploader(
        "Choose .txt file(s)", type=["txt"], key="multi_file",
        accept_multiple_files=True,
    )
    max_items = st.slider("Max news items to analyze (protects against huge API bills)", 1, 300, 50, key="max_items_file")
    analyze_file_clicked = st.button("🔍 Analyze File(s)", type="primary", use_container_width=True, key="btn_file")
    st.markdown('</div>', unsafe_allow_html=True)

    if analyze_file_clicked:
        if not api_key_input:
            st.error("This app is not configured yet — the app owner needs to add an API key in Secrets. Contact the app owner.")
        elif not uploaded_files:
            st.warning("Please upload at least one .txt file first.")
        else:
            # ---- Read every file, split into one article per non-empty line ----
            articles = []  # list of (label, text)
            for f in uploaded_files:
                content = f.read().decode("utf-8", errors="ignore")
                lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
                if not lines:
                    continue
                if len(lines) == 1:
                    articles.append((f.name, lines[0]))
                else:
                    for idx, ln in enumerate(lines, start=1):
                        articles.append((f"{f.name} (line {idx})", ln))

            articles = articles[:max_items]

            if len(articles) == 1:
                label, text = articles[0]
                with st.expander("📄 Preview uploaded text"):
                    st.write(text[:2000] + ("..." if len(text) > 2000 else ""))

            run_batch_analysis(
                articles, api_key_input,
                csv_filename="news_predictions_uploaded.csv",
                source_note=f"across {len(uploaded_files)} file(s)",
            )

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.caption(
    "⚠️ Verdicts are generated live by an LLM and are estimates, not definitive "
    "fact-checking. Always verify important news through trusted, reputable sources. "
    "API calls incur cost/rate-limit usage on your provider account — both tabs let you cap the number of items analyzed."
)
render_dev_credit()
