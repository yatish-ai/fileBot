"""
app.py  (v2)
FileBOT — Your Smart File Assistant
Upload → Process → Chat  |  Add more files anytime  |  Reset to start fresh
v2: Conversational memory · Query rewriting · Hybrid retrieval · Re-ranking
"""

import streamlit as st
import os

st.set_page_config(
    page_title="FileBOT — Your Smart File Assistant",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── CSS ──────────────────────────────────────────────────────────────────────
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
    --green:         #22c55e;
    --green-dim:     #0d3d1a;
    --orange:        #f59e0b;
    --text-primary:  #e8f0fe;
    --text-secondary:#7a9cc4;
    --text-muted:    #3a5170;
    --font-display:  'Exo 2', sans-serif;
    --font-mono:     'JetBrains Mono', monospace;
}

html, body, [class*="css"] { font-family: var(--font-display) !important; background: var(--bg-deep) !important; color: var(--text-primary) !important; }
#MainMenu, footer, header { visibility: hidden !important; }
.block-container { padding-top: 0 !important; max-width: 820px !important; }
section[data-testid="stSidebar"] { display: none; }

/* HEADER */
.fb-header { position: relative; padding: 2.8rem 0 2rem; text-align: center; overflow: hidden; }
.fb-header::before { content: ''; position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 600px; height: 2px; background: linear-gradient(90deg, transparent, var(--blue-bright), transparent); }
.fb-logo-row { display: flex; align-items: center; justify-content: center; gap: 14px; margin-bottom: 6px; }
.fb-eye { width: 12px; height: 12px; background: var(--red-eye); border-radius: 2px; box-shadow: 0 0 12px var(--red-eye), 0 0 24px rgba(255,68,68,0.4); animation: eyePulse 2.5s ease-in-out infinite; display: inline-block; }
.fb-eye:nth-child(2) { animation-delay: 0.3s; }
@keyframes eyePulse { 0%,100% { opacity:1; box-shadow: 0 0 10px var(--red-eye), 0 0 20px rgba(255,68,68,0.4); } 50% { opacity:0.6; box-shadow: 0 0 4px var(--red-eye); } }
.fb-title { font-family: var(--font-display); font-size: 2.6rem; font-weight: 800; color: var(--text-primary); letter-spacing: -1px; line-height: 1; }
.fb-title span { color: var(--blue-bright); }
.fb-subtitle { font-size: 0.88rem; color: var(--text-secondary); font-weight: 400; letter-spacing: 2px; text-transform: uppercase; margin-top: 4px; }
.fb-tagline { font-size: 0.82rem; color: var(--text-muted); margin-top: 8px; font-family: var(--font-mono); }

/* STEP HEADER */
.step-header { display: flex; align-items: center; gap: 10px; margin: 1.6rem 0 0.8rem; }
.step-number { width: 26px; height: 26px; border-radius: 50%; background: var(--blue-dim); border: 1.5px solid var(--blue-mid); display: flex; align-items: center; justify-content: center; font-family: var(--font-mono); font-size: 0.72rem; font-weight: 600; color: var(--blue-bright); flex-shrink: 0; }
.step-number.done { background: var(--green-dim); border-color: var(--green); color: var(--green); }
.step-label { font-family: var(--font-mono); font-size: 0.72rem; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; color: var(--text-secondary); }
.step-connector { flex: 1; height: 1px; background: linear-gradient(90deg, var(--border), transparent); }

/* UPLOAD */
[data-testid="stFileUploader"] { background: var(--bg-card) !important; border: 1.5px dashed var(--border-glow) !important; border-radius: 10px !important; transition: border-color 0.2s !important; }
[data-testid="stFileUploader"]:hover { border-color: var(--blue-bright) !important; }
[data-testid="stFileUploader"] label { color: var(--text-secondary) !important; }

/* FILE CHIPS */
.file-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.file-chip { background: var(--bg-card); border: 1px solid var(--border-glow); border-radius: 20px; padding: 4px 12px; font-family: var(--font-mono); font-size: 0.75rem; color: var(--blue-bright); display: flex; align-items: center; gap: 6px; }
.file-chip.already { border-color: #166534; color: #4ade80; background: var(--green-dim); }
.file-chip.new-file { border-color: var(--orange); color: var(--orange); background: #1a1000; }
.chip-ext { background: var(--blue-dim); border-radius: 4px; padding: 1px 5px; font-size: 0.65rem; text-transform: uppercase; color: var(--blue-bright); }
.chip-ext.already { background: #0d3d1a; color: #4ade80; }
.chip-ext.new-file { background: #2a1a00; color: var(--orange); }

/* INDEXED FILES PANEL */
.indexed-panel { background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 12px 16px; margin-top: 10px; }
.indexed-panel .panel-title { font-family: var(--font-mono); font-size: 0.68rem; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px; }
.indexed-file-row { display: flex; align-items: center; gap: 8px; padding: 4px 0; border-bottom: 1px solid var(--border); font-family: var(--font-mono); font-size: 0.76rem; color: var(--text-secondary); }
.indexed-file-row:last-child { border-bottom: none; }
.indexed-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--green); flex-shrink: 0; box-shadow: 0 0 6px var(--green); }

/* BUTTONS */
.stButton > button { background: linear-gradient(135deg, var(--blue-mid), var(--blue-bright)) !important; color: #fff !important; border: none !important; border-radius: 8px !important; font-family: var(--font-mono) !important; font-size: 0.84rem !important; font-weight: 600 !important; letter-spacing: 1px !important; padding: 0.55rem 2rem !important; text-transform: uppercase !important; transition: all 0.2s ease !important; box-shadow: 0 0 20px rgba(59,158,255,0.3) !important; }
.stButton > button:hover { box-shadow: 0 0 30px rgba(59,158,255,0.55) !important; transform: translateY(-2px) !important; }
.stButton > button:disabled { background: var(--bg-raised) !important; color: var(--text-muted) !important; box-shadow: none !important; transform: none !important; }

/* STATUS BADGE */
.status-badge { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 8px; font-family: var(--font-mono); font-size: 0.78rem; font-weight: 500; margin-top: 6px; }
.status-ready   { background: #0b2418; border: 1px solid #166534; color: #4ade80; }
.status-waiting { background: var(--bg-card); border: 1px solid var(--border); color: var(--text-muted); }
.status-error   { background: #2d0b0b; border: 1px solid #7f1d1d; color: #f87171; }
.status-adding  { background: #1a1000; border: 1px solid #92400e; color: var(--orange); }

/* PROGRESS */
[data-testid="stProgress"] > div { background: var(--bg-raised) !important; border-radius: 4px !important; }
[data-testid="stProgress"] > div > div { background: linear-gradient(90deg, var(--blue-mid), var(--blue-bright)) !important; border-radius: 4px !important; }

/* DIVIDER */
.fb-divider { border: none; border-top: 1px solid var(--border); margin: 1.2rem 0; }

/* CHAT */
.chat-scroll { max-height: 520px; overflow-y: auto; padding: 4px 0; scrollbar-width: thin; scrollbar-color: var(--border-glow) var(--bg-card); }
.chat-scroll::-webkit-scrollbar { width: 4px; }
.chat-scroll::-webkit-scrollbar-track { background: var(--bg-card); }
.chat-scroll::-webkit-scrollbar-thumb { background: var(--border-glow); border-radius: 2px; }
.chat-bubble { display: flex; gap: 12px; margin-bottom: 14px; animation: bubbleIn 0.2s ease; }
@keyframes bubbleIn { from { opacity:0; transform: translateY(6px); } to { opacity:1; transform: translateY(0); } }
.chat-avatar { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 0.9rem; flex-shrink: 0; margin-top: 2px; }
.avatar-user { background: var(--blue-dim); border: 1px solid var(--blue-mid); }
.avatar-bot  { background: #0d1f12; border: 1px solid #166534; }
.chat-content { flex: 1; min-width: 0; }
.chat-name { font-family: var(--font-mono); font-size: 0.68rem; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 5px; }
.chat-name-user { color: var(--blue-bright); }
.chat-name-bot  { color: #4ade80; }
.chat-text { background: var(--bg-card); border: 1px solid var(--border); border-radius: 0 10px 10px 10px; padding: 10px 14px; font-size: 0.9rem; line-height: 1.65; color: var(--text-primary); white-space: pre-wrap; }
.chat-text-user { border-color: var(--blue-dim); background: #0a1628; }
.chat-text-bot  { border-color: #1a3d28; background: #0a1a11; }
.sources-bar { margin-top: 6px; padding: 5px 10px; background: var(--bg-deep); border: 1px solid var(--border); border-radius: 6px; font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted); display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.src-tag { background: var(--bg-card); border: 1px solid var(--border-glow); border-radius: 4px; padding: 2px 8px; color: var(--blue-bright); font-size: 0.68rem; }
.intent-tag { background: #0d1a2d; border: 1px solid var(--blue-dim); border-radius: 4px; padding: 2px 8px; color: var(--text-muted); font-size: 0.65rem; font-style: italic; }

/* CHAT INPUT */
[data-testid="stChatInput"] { background: var(--bg-card) !important; border: 1.5px solid var(--border-glow) !important; border-radius: 10px !important; }
[data-testid="stChatInput"]:focus-within { border-color: var(--blue-bright) !important; box-shadow: 0 0 0 3px rgba(59,158,255,0.12) !important; }
[data-testid="stChatInput"] textarea { background: transparent !important; color: var(--text-primary) !important; font-family: var(--font-display) !important; font-size: 0.9rem !important; }
[data-testid="stChatInput"] button { background: var(--blue-mid) !important; border-radius: 6px !important; }

/* MISC */
.stSpinner > div { color: var(--blue-bright) !important; }
.stAlert { border-radius: 8px !important; font-size: 0.88rem !important; }
.api-warn { background: #1a1000; border: 1px solid #78350f; border-radius: 8px; padding: 10px 14px; font-size: 0.84rem; color: #fbbf24; margin-bottom: 12px; font-family: var(--font-mono); }
.chat-empty { text-align: center; padding: 2.5rem 1rem; color: var(--text-muted); }
.chat-empty .bot-icon { font-size: 2.5rem; margin-bottom: 10px; display: block; opacity: 0.4; }
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────────────────
from memory_manager import MemoryManager

if "vector_store"      not in st.session_state: st.session_state.vector_store      = None
if "processing_done"   not in st.session_state: st.session_state.processing_done   = False
if "chat_history"      not in st.session_state: st.session_state.chat_history      = []
if "doc_stats"         not in st.session_state: st.session_state.doc_stats         = {}
if "indexed_files"     not in st.session_state: st.session_state.indexed_files     = []
if "processing_error"  not in st.session_state: st.session_state.processing_error  = None
if "memory"            not in st.session_state: st.session_state.memory            = MemoryManager(max_turns=6)

is_ready = st.session_state.processing_done and st.session_state.vector_store is not None

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="fb-header">
    <div class="fb-logo-row">
        <span class="fb-eye"></span>
        <span class="fb-title">File<span>BOT</span></span>
        <span class="fb-eye"></span>
    </div>
    <div class="fb-subtitle">Your Smart File Assistant</div>
    <div class="fb-tagline">v2 · Hybrid RAG · Conversational Memory · Query Rewriting</div>
</div>
""", unsafe_allow_html=True)

# ── GROQ key warning ──────────────────────────────────────────────────────────
if not os.environ.get("GROQ_API_KEY", "").strip():
    st.markdown(
        '<div class="api-warn">⚠️ GROQ_API_KEY not set. '
        'Add it in Settings → Secrets before chatting.</div>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# STEP 01 — UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
step1_done = "done" if is_ready else ""
st.markdown(f"""
<div class="step-header">
    <div class="step-number {step1_done}">{'✓' if is_ready else '01'}</div>
    <div class="step-label">Upload Documents</div>
    <div class="step-connector"></div>
</div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader(
    "Drop PDF, TXT, or DOCX files here",
    type=["pdf", "txt", "docx"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

already_indexed = set(st.session_state.indexed_files)
new_uploads, already_uploads = [], []
if uploaded:
    for f in uploaded:
        (already_uploads if f.name in already_indexed else new_uploads).append(f)

    if uploaded:
        chips_html = '<div class="file-chips">'
        for f in already_uploads:
            ext = f.name.rsplit(".", 1)[-1].upper()
            chips_html += f'<div class="file-chip already"><span class="chip-ext already">{ext}</span>{f.name} ✓</div>'
        for f in new_uploads:
            ext = f.name.rsplit(".", 1)[-1].upper()
            chips_html += f'<div class="file-chip new-file"><span class="chip-ext new-file">{ext}</span>{f.name} ★</div>'
        chips_html += '</div>'
        st.markdown(chips_html, unsafe_allow_html=True)

if st.session_state.indexed_files:
    rows = "".join(
        f'<div class="indexed-file-row"><span class="indexed-dot"></span>{fn}</div>'
        for fn in st.session_state.indexed_files
    )
    stats = st.session_state.doc_stats
    st.markdown(
        f'<div class="indexed-panel"><div class="panel-title">📚 Indexed — '
        f'{stats.get("files",0)} file(s) · {stats.get("chunks",0):,} chunks</div>'
        f'{rows}</div>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# STEP 02 — PROCESS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<hr class="fb-divider">', unsafe_allow_html=True)
st.markdown(f"""
<div class="step-header">
    <div class="step-number {'done' if is_ready else ''}">{'✓' if is_ready else '02'}</div>
    <div class="step-label">Process Documents</div>
    <div class="step-connector"></div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])
with col1:
    btn_label     = "➕ Add Files" if (is_ready and new_uploads) else "⚡ Process Files"
    process_clicked = st.button(
        btn_label,
        disabled=not new_uploads,
        use_container_width=True,
    )
with col2:
    reset_clicked = st.button("🔄 Reset", use_container_width=True)

# Status badge
if is_ready:
    s = st.session_state.doc_stats
    badge_class, badge_icon, badge_msg = (
        ("status-adding", "🔄", f"Adding {len(new_uploads)} file(s)…")
        if new_uploads else
        ("status-ready",  "●",  f"Ready · {s.get('files',0)} file(s) · {s.get('chunks',0):,} chunks")
    )
elif st.session_state.processing_error:
    badge_class, badge_icon, badge_msg = "status-error", "✕", f"Error: {st.session_state.processing_error[:60]}"
else:
    badge_class, badge_icon, badge_msg = "status-waiting", "○", "Waiting for documents…"

st.markdown(
    f'<div class="status-badge {badge_class}">'
    f'<span>{badge_icon}</span><span>{badge_msg}</span></div>',
    unsafe_allow_html=True,
)

# ── Reset ─────────────────────────────────────────────────────────────────────
if reset_clicked:
    st.session_state.vector_store      = None
    st.session_state.processing_done   = False
    st.session_state.chat_history      = []
    st.session_state.doc_stats         = {}
    st.session_state.indexed_files     = []
    st.session_state.processing_error  = None
    st.session_state.memory            = MemoryManager(max_turns=6)
    st.success("✓ FileBOT has been reset. Upload new documents to start fresh.")
    st.rerun()

# ── Process / Add ─────────────────────────────────────────────────────────────
if process_clicked and new_uploads:
    st.session_state.processing_error = None
    progress_bar = st.progress(0, text="Initializing…")

    try:
        from rag_pipeline import process_documents

        progress_bar.progress(10, text="Reading files…")
        files_data = []
        for i, f in enumerate(new_uploads):
            files_data.append({"name": f.name, "bytes": f.read()})
            progress_bar.progress(10 + int(28 * (i + 1) / len(new_uploads)), text=f"Loaded: {f.name}")

        progress_bar.progress(40, text="Chunking & embedding…")
        existing_store = st.session_state.vector_store

        with st.spinner("Generating embeddings — first run downloads ~90MB model…"):
            store, new_added, total_chunks = process_documents(files_data, existing_store)

        progress_bar.progress(90, text="Updating FAISS index…")

        st.session_state.vector_store    = store
        st.session_state.processing_done = True
        st.session_state.indexed_files   = store.indexed_files()
        st.session_state.doc_stats       = {
            "files":  len(st.session_state.indexed_files),
            "chunks": total_chunks,
        }
        progress_bar.progress(100, text="Done!")

        if existing_store is None:
            st.success(f"✓ Indexed {len(new_uploads)} file(s) · {new_added:,} chunks. FileBOT v2 is ready!")
        else:
            st.success(f"✓ Added {new_added:,} new chunks. Total: {total_chunks:,} across {len(st.session_state.indexed_files)} file(s).")

        st.rerun()

    except Exception as e:
        err = str(e)[:160]
        st.session_state.processing_error = err
        st.error(f"Processing failed: {err}")
        progress_bar.empty()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 03 — CHAT
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<hr class="fb-divider">', unsafe_allow_html=True)
st.markdown("""
<div class="step-header">
    <div class="step-number">03</div>
    <div class="step-label">Ask FileBOT</div>
    <div class="step-connector"></div>
</div>
""", unsafe_allow_html=True)

# Render chat history
if st.session_state.chat_history:
    chat_html = '<div class="chat-scroll">'
    for msg in st.session_state.chat_history:
        role    = msg["role"]
        content = msg["content"]
        sources = msg.get("sources", [])
        intent  = msg.get("intent", "")
        rewritten = msg.get("rewritten_query", "")

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
                for sname, spage in sorted(unique):
                    short = sname if len(sname) <= 24 else sname[:21] + "…"
                    src_html += f'<span class="src-tag">{short} · p{spage}</span>'
                if intent:
                    src_html += f'<span class="intent-tag">intent: {intent}</span>'
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
    msg = (
        "FileBOT v2 is ready. Ask anything — I remember the conversation!"
        if is_ready
        else "Upload and process documents to activate FileBOT."
    )
    st.markdown(
        f'<div class="chat-empty"><span class="bot-icon">🤖</span><p>{msg}</p></div>',
        unsafe_allow_html=True,
    )

# Chat input
if not is_ready:
    st.chat_input("Process your documents first to start chatting…", disabled=True)
else:
    user_input = st.chat_input("Ask FileBOT about your documents…")
    if user_input and user_input.strip():
        question = user_input.strip()

        with st.spinner("FileBOT is thinking…"):
            try:
                from rag_pipeline import answer_question
                result = answer_question(
                    question,
                    st.session_state.vector_store,
                    memory=st.session_state.memory,
                )
                answer   = result["answer"]
                sources  = result["sources"]
                intent   = result.get("intent", "general")
                rewritten = result.get("rewritten_query", question)
            except Exception as e:
                answer    = f"⚠️ Unexpected error: {str(e)[:200]}"
                sources   = []
                intent    = "general"
                rewritten = question

        st.session_state.chat_history.append({"role": "user", "content": question})
        st.session_state.chat_history.append({
            "role":             "assistant",
            "content":          answer,
            "sources":          sources,
            "intent":           intent,
            "rewritten_query":  rewritten,
        })
        st.rerun()


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:2rem 0 0.5rem;font-family:'JetBrains Mono',monospace;
            font-size:0.7rem;color:#3a5170;letter-spacing:1px;">
    FileBOT v2 · MiniLM-L6-v2 · FAISS · Hybrid Retrieval · Groq LLaMA3.1-8B
</div>
""", unsafe_allow_html=True)
