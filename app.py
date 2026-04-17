"""
app.py
FileBOT — Your Smart File Assistant
Streamlit RAG Application · Upload → Process → Chat
"""

import streamlit as st
import os

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FileBOT — Your Smart File Assistant",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── CSS: FileBOT Brand Identity ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --bg-deep:       #070b12;
    --bg-card:       #0d1420;
    --bg-raised:     #111827;
    --border:        #1e2d45;
    --border-glow:   #1a4a8a;
    --blue-bright:   #3b9eff;
    --blue-mid:      #1a6fc4;
    --blue-dim:      #0d3d7a;
    --red-eye:       #ff4444;
    --text-primary:  #e8f0fe;
    --text-secondary:#7a9cc4;
    --text-muted:    #3a5170;
    --success:       #22c55e;
    --warning:       #f59e0b;
    --font-display:  'Exo 2', sans-serif;
    --font-mono:     'JetBrains Mono', monospace;
}

html, body, [class*="css"] {
    font-family: var(--font-display) !important;
    background: var(--bg-deep) !important;
    color: var(--text-primary) !important;
}

/* ── Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden !important; }
.block-container {
    padding-top: 0 !important;
    max-width: 820px !important;
}
section[data-testid="stSidebar"] { display: none; }

/* ── HEADER ── */
.fb-header {
    position: relative;
    padding: 2.8rem 0 2rem;
    text-align: center;
    overflow: hidden;
}
.fb-header::before {
    content: '';
    position: absolute;
    top: 0; left: 50%;
    transform: translateX(-50%);
    width: 600px; height: 2px;
    background: linear-gradient(90deg, transparent, var(--blue-bright), transparent);
}
.fb-logo-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 14px;
    margin-bottom: 6px;
}
.fb-eye {
    width: 12px; height: 12px;
    background: var(--red-eye);
    border-radius: 2px;
    box-shadow: 0 0 12px var(--red-eye), 0 0 24px rgba(255,68,68,0.4);
    animation: eyePulse 2.5s ease-in-out infinite;
    display: inline-block;
}
.fb-eye:nth-child(2) { animation-delay: 0.3s; }
@keyframes eyePulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 10px var(--red-eye), 0 0 20px rgba(255,68,68,0.4); }
    50%       { opacity: 0.6; box-shadow: 0 0 4px var(--red-eye); }
}
.fb-title {
    font-family: var(--font-display);
    font-size: 2.6rem;
    font-weight: 800;
    color: var(--text-primary);
    letter-spacing: -1px;
    line-height: 1;
}
.fb-title span { color: var(--blue-bright); }
.fb-subtitle {
    font-size: 0.88rem;
    color: var(--text-secondary);
    font-weight: 400;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 4px;
}
.fb-tagline {
    font-size: 0.82rem;
    color: var(--text-muted);
    margin-top: 8px;
    font-family: var(--font-mono);
}

/* ── STEP HEADER ── */
.step-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 1.6rem 0 0.8rem;
}
.step-number {
    width: 26px; height: 26px;
    border-radius: 50%;
    background: var(--blue-dim);
    border: 1.5px solid var(--blue-mid);
    display: flex; align-items: center; justify-content: center;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--blue-bright);
    flex-shrink: 0;
}
.step-number.done {
    background: #0d3d1a;
    border-color: var(--success);
    color: var(--success);
}
.step-label {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--text-secondary);
}
.step-connector {
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, var(--border), transparent);
}

/* ── UPLOAD ZONE ── */
[data-testid="stFileUploader"] {
    background: var(--bg-card) !important;
    border: 1.5px dashed var(--border-glow) !important;
    border-radius: 10px !important;
    transition: border-color 0.2s !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--blue-bright) !important;
}
[data-testid="stFileUploader"] label { color: var(--text-secondary) !important; }
[data-testid="stFileDropzoneInstructions"] { color: var(--text-muted) !important; }

/* ── FILE CHIPS ── */
.file-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
}
.file-chip {
    background: var(--bg-card);
    border: 1px solid var(--border-glow);
    border-radius: 20px;
    padding: 4px 12px;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--blue-bright);
    display: flex;
    align-items: center;
    gap: 6px;
}
.file-chip .chip-ext {
    background: var(--blue-dim);
    border-radius: 4px;
    padding: 1px 5px;
    font-size: 0.65rem;
    text-transform: uppercase;
    color: var(--blue-bright);
}

/* ── PROCESS BUTTON ── */
.stButton > button {
    background: linear-gradient(135deg, var(--blue-mid), var(--blue-bright)) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: var(--font-mono) !important;
    font-size: 0.84rem !important;
    font-weight: 600 !important;
    letter-spacing: 1px !important;
    padding: 0.55rem 2rem !important;
    text-transform: uppercase !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 0 20px rgba(59, 158, 255, 0.3) !important;
}
.stButton > button:hover {
    box-shadow: 0 0 30px rgba(59, 158, 255, 0.55) !important;
    transform: translateY(-2px) !important;
}
.stButton > button:disabled {
    background: var(--bg-raised) !important;
    color: var(--text-muted) !important;
    box-shadow: none !important;
    transform: none !important;
}

/* ── STATUS BADGE ── */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    border-radius: 8px;
    font-family: var(--font-mono);
    font-size: 0.78rem;
    font-weight: 500;
    margin-top: 6px;
}
.status-ready   { background: #0b2418; border: 1px solid #166534; color: #4ade80; }
.status-waiting { background: var(--bg-card); border: 1px solid var(--border); color: var(--text-muted); }
.status-error   { background: #2d0b0b; border: 1px solid #7f1d1d; color: #f87171; }

/* ── PROGRESS BAR ── */
[data-testid="stProgress"] > div { background: var(--bg-raised) !important; border-radius: 4px !important; }
[data-testid="stProgress"] > div > div { background: linear-gradient(90deg, var(--blue-mid), var(--blue-bright)) !important; border-radius: 4px !important; }

/* ── DIVIDER ── */
.fb-divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 1.2rem 0;
}

/* ── CHAT AREA ── */
.chat-scroll {
    max-height: 480px;
    overflow-y: auto;
    padding: 4px 0;
    scrollbar-width: thin;
    scrollbar-color: var(--border-glow) var(--bg-card);
}
.chat-scroll::-webkit-scrollbar { width: 4px; }
.chat-scroll::-webkit-scrollbar-track { background: var(--bg-card); }
.chat-scroll::-webkit-scrollbar-thumb { background: var(--border-glow); border-radius: 2px; }

.chat-bubble {
    display: flex;
    gap: 12px;
    margin-bottom: 14px;
    animation: bubbleIn 0.2s ease;
}
@keyframes bubbleIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}
.chat-avatar {
    width: 32px; height: 32px;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.9rem;
    flex-shrink: 0;
    margin-top: 2px;
}
.avatar-user { background: var(--blue-dim); border: 1px solid var(--blue-mid); }
.avatar-bot  { background: #0d1f12; border: 1px solid #166534; }

.chat-content { flex: 1; min-width: 0; }
.chat-name {
    font-family: var(--font-mono);
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 5px;
}
.chat-name-user { color: var(--blue-bright); }
.chat-name-bot  { color: #4ade80; }

.chat-text {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 0 10px 10px 10px;
    padding: 10px 14px;
    font-size: 0.9rem;
    line-height: 1.65;
    color: var(--text-primary);
}
.chat-text-user {
    border-color: var(--blue-dim);
    background: #0a1628;
}
.chat-text-bot {
    border-color: #1a3d28;
    background: #0a1a11;
}

.sources-bar {
    margin-top: 6px;
    padding: 5px 10px;
    background: var(--bg-deep);
    border: 1px solid var(--border);
    border-radius: 6px;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--text-muted);
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
}
.src-tag {
    background: var(--bg-card);
    border: 1px solid var(--border-glow);
    border-radius: 4px;
    padding: 2px 8px;
    color: var(--blue-bright);
    font-size: 0.68rem;
}

/* ── CHAT INPUT ── */
[data-testid="stChatInput"] {
    background: var(--bg-card) !important;
    border: 1.5px solid var(--border-glow) !important;
    border-radius: 10px !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: var(--blue-bright) !important;
    box-shadow: 0 0 0 3px rgba(59,158,255,0.12) !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: var(--text-primary) !important;
    font-family: var(--font-display) !important;
    font-size: 0.9rem !important;
}
[data-testid="stChatInput"] button {
    background: var(--blue-mid) !important;
    border-radius: 6px !important;
}

/* ── ALERTS ── */
.stAlert { border-radius: 8px !important; font-size: 0.88rem !important; }

/* ── SPINNER ── */
.stSpinner > div { color: var(--blue-bright) !important; }

/* ── STATS STRIP ── */
.stats-strip {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 10px;
}
.stat-box {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 14px;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--text-secondary);
    display: flex;
    flex-direction: column;
    gap: 2px;
}
.stat-box .stat-val {
    font-size: 1.3rem;
    font-weight: 700;
    color: var(--blue-bright);
    line-height: 1;
}

/* ── API WARNING ── */
.api-warn {
    background: #1a1000;
    border: 1px solid #78350f;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.84rem;
    color: #fbbf24;
    margin-bottom: 12px;
    font-family: var(--font-mono);
}

/* ── EMPTY CHAT STATE ── */
.chat-empty {
    text-align: center;
    padding: 2.5rem 1rem;
    color: var(--text-muted);
}
.chat-empty .bot-icon {
    font-size: 2.5rem;
    margin-bottom: 10px;
    display: block;
    opacity: 0.4;
}
.chat-empty p {
    font-size: 0.85rem;
    font-family: var(--font-mono);
    margin: 0;
}
</style>
""", unsafe_allow_html=True)


# ── Session state init ───────────────────────────────────────────────────────
def init_session():
    defaults = {
        "vector_store": None,
        "chat_history": [],
        "processing_done": False,
        "doc_stats": {"files": 0, "chunks": 0},
        "processing_error": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


# ── HEADER ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="fb-header">
    <div class="fb-logo-row">
        <span class="fb-eye"></span>
        <span class="fb-eye"></span>
    </div>
    <div class="fb-title">File<span>BOT</span></div>
    <div class="fb-subtitle">Your Smart File Assistant</div>
    <div class="fb-tagline">// RAG · sentence-transformers · FAISS · Groq LLaMA3</div>
</div>
""", unsafe_allow_html=True)


# ── API Key check ────────────────────────────────────────────────────────────
api_key = os.environ.get("GROQ_API_KEY", "").strip()
if not api_key:
    st.markdown("""
    <div class="api-warn">
        ⚠ &nbsp;<strong>GROQ_API_KEY not configured.</strong>
        Add it to your environment variables or Streamlit secrets to enable chat.
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# STEP 01 — UPLOAD
# ══════════════════════════════════════════════════════════════
step1_done = st.session_state.processing_done
st.markdown(f"""
<div class="step-header">
    <div class="step-number {'done' if step1_done else ''}">{'✓' if step1_done else '01'}</div>
    <div class="step-label">Upload Documents</div>
    <div class="step-connector"></div>
</div>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Drop files here",
    type=["pdf", "txt", "docx"],
    accept_multiple_files=True,
    label_visibility="collapsed",
    help="Supported: PDF, TXT, DOCX"
)

if uploaded_files:
    chips_html = '<div class="file-chips">'
    for f in uploaded_files:
        ext = f.name.rsplit(".", 1)[-1].upper() if "." in f.name else "FILE"
        short = f.name if len(f.name) <= 28 else f.name[:25] + "…"
        chips_html += f'<div class="file-chip"><span class="chip-ext">{ext}</span>{short}</div>'
    chips_html += "</div>"
    st.markdown(chips_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# STEP 02 — PROCESS
# ══════════════════════════════════════════════════════════════
st.markdown('<hr class="fb-divider">', unsafe_allow_html=True)
st.markdown(f"""
<div class="step-header">
    <div class="step-number {'done' if step1_done else '02'}">{'✓' if step1_done else '02'}</div>
    <div class="step-label">Process & Index</div>
    <div class="step-connector"></div>
</div>
""", unsafe_allow_html=True)

col_btn, col_status = st.columns([1, 3])

with col_btn:
    process_clicked = st.button(
        "⚙  PROCESS",
        disabled=not bool(uploaded_files),
        use_container_width=True
    )

with col_status:
    if st.session_state.processing_done:
        stats = st.session_state.doc_stats
        st.markdown(
            f'<div class="status-badge status-ready">'
            f'✓ &nbsp;INDEXED — {stats["files"]} file{"s" if stats["files"]!=1 else ""} · {stats["chunks"]:,} chunks'
            f'</div>',
            unsafe_allow_html=True
        )
    elif st.session_state.processing_error:
        short_err = str(st.session_state.processing_error)[:80]
        st.markdown(
            f'<div class="status-badge status-error">✗ &nbsp;{short_err}</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="status-badge status-waiting">○ &nbsp;Awaiting processing</div>',
            unsafe_allow_html=True
        )


if process_clicked and uploaded_files:
    st.session_state.processing_error = None
    st.session_state.processing_done = False
    st.session_state.chat_history = []
    st.session_state.vector_store = None

    progress_bar = st.progress(0, text="Initializing FileBOT…")

    try:
        from rag_pipeline import process_documents

        progress_bar.progress(10, text="Reading files…")
        files_data = []
        for i, f in enumerate(uploaded_files):
            files_data.append({"name": f.name, "bytes": f.read()})
            pct = 10 + int(25 * (i + 1) / len(uploaded_files))
            progress_bar.progress(pct, text=f"Loaded: {f.name}")

        progress_bar.progress(38, text="Chunking documents…")

        with st.spinner("Generating embeddings — first run downloads ~90MB model…"):
            store, chunk_count = process_documents(files_data)

        progress_bar.progress(90, text="Building FAISS index…")
        st.session_state.vector_store = store
        st.session_state.processing_done = True
        st.session_state.doc_stats = {"files": len(uploaded_files), "chunks": chunk_count}

        progress_bar.progress(100, text="FileBOT is ready!")
        st.success(f"✓ Indexed {len(uploaded_files)} file(s) into {chunk_count:,} chunks. FileBOT is ready to answer questions.")

    except Exception as e:
        err = str(e)[:160]
        st.session_state.processing_error = err
        st.error(f"Processing failed: {err}")
        progress_bar.empty()


# ══════════════════════════════════════════════════════════════
# STEP 03 — CHAT
# ══════════════════════════════════════════════════════════════
st.markdown('<hr class="fb-divider">', unsafe_allow_html=True)
st.markdown(f"""
<div class="step-header">
    <div class="step-number">03</div>
    <div class="step-label">Ask FileBOT</div>
    <div class="step-connector"></div>
</div>
""", unsafe_allow_html=True)

# ── Render chat history ──────────────────────────────────────
if st.session_state.chat_history:
    chat_html = '<div class="chat-scroll">'
    for msg in st.session_state.chat_history:
        role = msg["role"]
        content = msg["content"]
        sources = msg.get("sources", [])

        if role == "user":
            chat_html += f"""
            <div class="chat-bubble">
                <div class="chat-avatar avatar-user">👤</div>
                <div class="chat-content">
                    <div class="chat-name chat-name-user">YOU</div>
                    <div class="chat-text chat-text-user">{content}</div>
                </div>
            </div>"""
        else:
            src_html = ""
            if sources:
                unique = list({(s["source"], s["page"]) for s in sources})
                src_html = '<div class="sources-bar">📎 '
                for sname, spage in unique:
                    short = sname if len(sname) <= 22 else sname[:19] + "…"
                    src_html += f'<span class="src-tag">{short} · p{spage}</span>'
                src_html += '</div>'

            chat_html += f"""
            <div class="chat-bubble">
                <div class="chat-avatar avatar-bot">🤖</div>
                <div class="chat-content">
                    <div class="chat-name chat-name-bot">FILEBOT</div>
                    <div class="chat-text chat-text-bot">{content}</div>
                    {src_html}
                </div>
            </div>"""

    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)
else:
    if st.session_state.processing_done:
        st.markdown("""
        <div class="chat-empty">
            <span class="bot-icon">🤖</span>
            <p>FileBOT is ready. Ask anything about your documents.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="chat-empty">
            <span class="bot-icon">🤖</span>
            <p>Upload and process documents to activate FileBOT.</p>
        </div>
        """, unsafe_allow_html=True)

# ── Chat input ───────────────────────────────────────────────
chat_disabled = not st.session_state.processing_done

if chat_disabled:
    st.chat_input("Process your documents first to start chatting…", disabled=True)
else:
    user_input = st.chat_input("Ask FileBOT about your documents…")

    if user_input and user_input.strip():
        question = user_input.strip()
        st.session_state.chat_history.append({"role": "user", "content": question})

        with st.spinner("FileBOT is thinking…"):
            try:
                from rag_pipeline import answer_question
                result = answer_question(question, st.session_state.vector_store)
                answer = result["answer"]
                sources = result["sources"]
            except Exception as e:
                answer = f"⚠️ Unexpected error: {str(e)[:200]}"
                sources = []

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": answer,
            "sources": sources
        })
        st.rerun()


# ── Footer ───────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:2rem 0 0.5rem;font-family:var(--font-mono);
            font-size:0.7rem;color:var(--text-muted);letter-spacing:1px;">
    FileBOT · all-MiniLM-L6-v2 · FAISS · Groq LLaMA3-8B
</div>
""", unsafe_allow_html=True)