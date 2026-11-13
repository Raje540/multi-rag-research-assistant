<<<<<<< HEAD
import sys
from pathlib import Path

# --------------------------------------------------
# PROJECT ROOT PATH
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

=======
import html
>>>>>>> 017eb04 (Updated Multi-RAG Research Assistant)
import streamlit as st
import requests


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Multi-RAG Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

<<<<<<< HEAD
=======
# API Endpoint Base URL
API_URL = "http://localhost:8000/api"
>>>>>>> 017eb04 (Updated Multi-RAG Research Assistant)

# --------------------------------------------------
# CUSTOM STYLING
# --------------------------------------------------

_CSS = """
<style>
<<<<<<< HEAD

    /* ---------------------------------------------
       MAIN APPLICATION
       --------------------------------------------- */

    .stApp {
        background-color: #f7f8fa;
    }
=======
    /* Main background (only forced in light mode, see theme detection below) */
    __APP_BG_RULE__
>>>>>>> 017eb04 (Updated Multi-RAG Research Assistant)


    /* ---------------------------------------------
       SIDEBAR
       --------------------------------------------- */

    section[data-testid="stSidebar"] {
        background-color: #111827;
    }

    section[data-testid="stSidebar"] * {
        color: #f9fafb;
    }


    /* ---------------------------------------------
       MAIN TITLE
       --------------------------------------------- */

    .main-title {
        font-size: 32px;
        font-weight: 700;
        color: __TITLE__;
        margin-bottom: 4px;
    }

    .subtitle {
        font-size: 15px;
        color: __SUBTITLE__;
        margin-bottom: 30px;
    }


    /* ---------------------------------------------
       METRIC CARDS
       --------------------------------------------- */

    .metric-card {
<<<<<<< HEAD
        background-color: #ffffff;
        padding: 22px;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
=======
        background-color: __CARD_BG__;
        padding: 22px;
        border-radius: 12px;
        border: 1px solid __CARD_BORDER__;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
>>>>>>> 017eb04 (Updated Multi-RAG Research Assistant)
    }

    .metric-title {
        font-size: 14px;
        color: __SUBTITLE__;
    }

    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: __TITLE__;
        margin-top: 5px;
    }

<<<<<<< HEAD

    /* ---------------------------------------------
       UPLOAD CARD
       --------------------------------------------- */

    .upload-card {
        background-color: #ffffff;
        padding: 28px;
        border-radius: 14px;
        border: 1px solid #e5e7eb;
        margin-top: 20px;
    }


    /* ---------------------------------------------
       SECTION HEADINGS
       --------------------------------------------- */

=======
    /* Section headings */
>>>>>>> 017eb04 (Updated Multi-RAG Research Assistant)
    .section-title {
        font-size: 21px;
        font-weight: 650;
        color: __TITLE__;
        margin-top: 25px;
    }
<<<<<<< HEAD


    /* ---------------------------------------------
       EVIDENCE EXPANDERS
       --------------------------------------------- */

    div[data-testid="stExpander"] {
        background-color: #ffffff !important;
        border: 1px solid #d1d5db !important;
        border-radius: 10px !important;
        margin-bottom: 12px !important;
        overflow: hidden !important;
    }


    /* Evidence expander header */

    div[data-testid="stExpander"] details {
        background-color: #ffffff !important;
    }

    div[data-testid="stExpander"] details summary {
        background-color: #ffffff !important;
        color: #111827 !important;
        padding: 14px 16px !important;
    }


    /* Evidence header text */

    div[data-testid="stExpander"] details summary p {
        color: #111827 !important;
        font-weight: 600 !important;
        font-size: 15px !important;
    }


    /* Evidence header hover */

    div[data-testid="stExpander"] details summary:hover {
        background-color: #f3f4f6 !important;
    }


    /* Evidence body */

    div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] {
        background-color: #ffffff !important;
    }

    div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] p {
        color: #111827 !important;
        font-size: 15px !important;
        line-height: 1.7 !important;
    }


    /* Evidence metadata */

    div[data-testid="stExpander"] div[data-testid="stCaptionContainer"] {
        color: #6b7280 !important;
        background-color: #ffffff !important;
    }

=======
>>>>>>> 017eb04 (Updated Multi-RAG Research Assistant)
</style>
"""

# Detect the active Streamlit theme so text stays visible in dark mode.
_theme = None
try:
    _theme = st.context.theme.type          # Streamlit >= 1.46 (reflects the user's choice)
except Exception:
    try:
        _theme = st.get_option("theme.base")  # older versions: theme set in config
    except Exception:
        _theme = None

if _theme == "dark":
    _palette = {
        "__APP_BG_RULE__": "",   # let Streamlit's own dark background show
        "__TITLE__": "#f9fafb",
        "__SUBTITLE__": "#9ca3af",
        "__CARD_BG__": "#1f2937",
        "__CARD_BORDER__": "#374151",
    }
elif _theme == "light":
    _palette = {
        "__APP_BG_RULE__": ".stApp { background-color: #f7f8fa; }",
        "__TITLE__": "#111827",
        "__SUBTITLE__": "#6b7280",
        "__CARD_BG__": "white",
        "__CARD_BORDER__": "#e5e7eb",
    }
else:
    # Theme unknown: use colors that adapt to whichever theme is active
    _palette = {
        "__APP_BG_RULE__": "",
        "__TITLE__": "inherit",
        "__SUBTITLE__": "inherit; opacity: 0.7",
        "__CARD_BG__": "rgba(128, 128, 128, 0.12)",
        "__CARD_BORDER__": "rgba(128, 128, 128, 0.35)",
    }

for _key, _value in _palette.items():
    _CSS = _CSS.replace(_key, _value)

st.markdown(_CSS, unsafe_allow_html=True)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.markdown("## 🔬 Multi-RAG")
    st.caption("Research Intelligence Platform")
    st.divider()
    st.markdown("### WORKSPACE")

    page = st.radio(
        "Navigation",
        [
            "Overview",
            "Research Projects",
            "Research Papers",
            "Research Chat",
            "Evidence Analysis",
            "Gap Detection",
            "Gap Validation",
            "Final Report"
        ],
        label_visibility="collapsed"
    )

    st.divider()
    st.caption("Multi-RAG Research Assistant")
    st.caption("Evidence-Traceable Research Gap Validation")


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown('<div class="main-title">Research Intelligence Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Analyze multiple research papers, trace evidence, and validate research gaps.</div>', unsafe_allow_html=True)

# --------------------------------------------------
# FETCH LIVE METRICS (STRICT PROJECT-SPECIFIC FILTERING)
# --------------------------------------------------

papers_count = 0
chunks_count = 0
gaps_count = 0
validated_gaps_count = 0

def load_saved_gaps(project_id):
    """Gaps saved by the last detection run, so they are still there after a page refresh."""
    if not project_id or str(project_id) == "None":
        return
    if st.session_state.get("gaps_project_id") == project_id and "detected_gaps" in st.session_state:
        return
    try:
        res = requests.get(f"{API_URL}/gaps/{project_id}")
        if res.status_code == 200:
            data = res.json()
            st.session_state["detected_gaps"] = data.get("gaps", [])
            st.session_state["gaps_without"] = data.get("papers_without_gaps", [])
            st.session_state["gaps_project_id"] = project_id
    except Exception:
        pass


active_project_id = st.session_state.get("selected_project_id", None)
load_saved_gaps(active_project_id)

try:
    papers_res = requests.get(f"{API_URL}/papers/")
    if papers_res.status_code == 200:
        all_papers = papers_res.json().get("papers", [])
        
        if active_project_id is not None and str(active_project_id) != "None":
            project_papers = [
                p for p in all_papers 
                if str(p.get("project_id")) == str(active_project_id)
            ]
        else:
            project_papers = []

        papers_count = len(project_papers)

        for p in project_papers:
            if p.get("processing_status") == "EXTRACTED_AND_INDEXED":
                try:
                    chunks_res = requests.get(f"{API_URL}/papers/{p['id']}/chunks")
                    if chunks_res.status_code == 200:
                        chunks_count += chunks_res.json().get("total_chunks", 0)
                except Exception:
                    pass
except Exception:
    pass

# Update Gap Metrics if available in session state
if "detected_gaps" in st.session_state and st.session_state["detected_gaps"]:
    gaps_count = len(st.session_state["detected_gaps"])
    validated_gaps_count = len([g for g in st.session_state["detected_gaps"] if g.get("status") in ("CORROBORATED", "STANDS")])


# --------------------------------------------------
# METRIC CARDS
# --------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

with col1:
<<<<<<< HEAD

    st.markdown("""
=======
    st.markdown(f"""
>>>>>>> 017eb04 (Updated Multi-RAG Research Assistant)
    <div class="metric-card">
        <div class="metric-title">Research Papers</div>
        <div class="metric-value">{papers_count}</div>
    </div>
    """, unsafe_allow_html=True)


with col2:
<<<<<<< HEAD

    st.markdown("""
=======
    st.markdown(f"""
>>>>>>> 017eb04 (Updated Multi-RAG Research Assistant)
    <div class="metric-card">
        <div class="metric-title">Evidence Chunks</div>
        <div class="metric-value">{chunks_count}</div>
    </div>
    """, unsafe_allow_html=True)


with col3:
<<<<<<< HEAD

    st.markdown("""
=======
    st.markdown(f"""
>>>>>>> 017eb04 (Updated Multi-RAG Research Assistant)
    <div class="metric-card">
        <div class="metric-title">Research Gaps</div>
        <div class="metric-value">{gaps_count}</div>
    </div>
    """, unsafe_allow_html=True)


with col4:
<<<<<<< HEAD

    st.markdown("""
=======
    st.markdown(f"""
>>>>>>> 017eb04 (Updated Multi-RAG Research Assistant)
    <div class="metric-card">
        <div class="metric-title">Validated Gaps</div>
        <div class="metric-value">{validated_gaps_count}</div>
    </div>
    """, unsafe_allow_html=True)


# --------------------------------------------------
# OVERVIEW
# --------------------------------------------------

if page == "Overview":
    st.markdown('<div class="section-title">Research Workspace</div>', unsafe_allow_html=True)
    st.info("Create a research project and upload multiple papers to begin evidence-based analysis.")

# --------------------------------------------------
# RESEARCH PROJECTS
# --------------------------------------------------

elif page == "Research Projects":
    st.markdown('<div class="main-title">Research Projects</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Create and manage your research analysis projects.</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Create New Research Project</div>', unsafe_allow_html=True)

<<<<<<< HEAD
    st.markdown(
        '<div class="main-title">Research Projects</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'Create and manage your research analysis projects.'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-title">Create New Research Project</div>',
        unsafe_allow_html=True
    )

    project_name = st.text_input(
        "Project Name",
        placeholder="e.g. Multilingual Fake News Detection"
    )

    research_domain = st.text_input(
        "Research Domain",
        placeholder="e.g. Natural Language Processing"
    )

    project_description = st.text_area(
        "Project Description",
        placeholder="Describe the research problem or objective...",
        height=120
    )

    if st.button(
        "Create Research Project",
        type="primary",
        use_container_width=True
    ):
=======
    project_name = st.text_input("Project Name", placeholder="e.g. Multilingual Fake News Detection")
    research_domain = st.text_input("Research Domain", placeholder="e.g. Natural Language Processing")
    project_description = st.text_area("Project Description", placeholder="Describe the research problem...", height=120)
>>>>>>> 017eb04 (Updated Multi-RAG Research Assistant)

    if st.button("Create Research Project", type="primary", use_container_width=True):
        if not project_name or not research_domain:
            st.warning("Please enter the project name and research domain.")
        else:
            try:
                response = requests.post(
                    f"{API_URL}/projects/",
                    json={"project_name": project_name, "research_domain": research_domain, "description": project_description}
                )
                if response.status_code == 200:
                    data = response.json()
                    st.success(f"Project '{data.get('project_name', project_name)}' created successfully!")
                    st.rerun()
                else:
                    st.error("Failed to create project.")
            except Exception as e:
                st.error(f"Could not connect to backend: {e}")

<<<<<<< HEAD
            st.success(
                f"Research project '{project_name}' is ready to be created."
            )

            st.info(
                "Database storage will be connected in the next stage."
            )


# --------------------------------------------------
# RESEARCH PAPERS
# --------------------------------------------------
=======
    st.divider()
    st.markdown('<div class="section-title">Existing Projects</div>', unsafe_allow_html=True)

    try:
        response = requests.get(f"{API_URL}/projects/")
        if response.status_code == 200:
            projects_data = response.json()
            projects = projects_data.get("projects", []) if isinstance(projects_data, dict) else projects_data
            if not projects:
                st.info("No projects created yet.")
            else:
                for project in projects:
                    p_name = project.get("name") or project.get("project_name") or project.get("title", "Untitled Project")
                    p_domain = project.get("domain") or project.get("research_domain", "General")
                    with st.container():
                        st.markdown(f"**{p_name}** (ID: {project.get('id')})")
                        st.caption(f"Domain: {p_domain}")
                        if project.get("description"):
                            st.write(project["description"])
                        st.divider()
    except Exception as e:
        st.error(f"Could not connect to backend: {e}")
>>>>>>> 017eb04 (Updated Multi-RAG Research Assistant)

elif page == "Research Papers":
    st.markdown('<div class="main-title">Research Paper Collection</div>', unsafe_allow_html=True)
    
    projects = []
    try:
        proj_response = requests.get(f"{API_URL}/projects/")
        if proj_response.status_code == 200:
            p_data = proj_response.json()
            projects = p_data.get("projects", []) if isinstance(p_data, dict) else p_data
    except Exception:
        projects = []

    if not projects:
        st.markdown(
            """
            <div style="background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; border: 1px solid #ffeeba; font-weight: 500;">
                ⚠️ Please create a Research Project first in the 'Research Projects' tab before uploading papers.
            </div>
            """, 
            unsafe_allow_html=True
        )
    else:
        project_options = {}
        for p in projects:
            p_title = p.get("name") or p.get("project_name") or p.get("title", f"Project #{p.get('id')}")
            project_options[p_title] = p.get("id")

        dropdown_list = ["-- Select a Project --"] + list(project_options.keys())
        
        default_idx = 0
        if "selected_project_name" in st.session_state and st.session_state["selected_project_name"] in dropdown_list:
            default_idx = dropdown_list.index(st.session_state["selected_project_name"])

        selected_project_name = st.selectbox("Select Project for Upload", dropdown_list, index=default_idx)

        if selected_project_name != "-- Select a Project --":
            selected_project_id = project_options[selected_project_name]
            if st.session_state.get("selected_project_id") != selected_project_id:
                st.session_state["selected_project_id"] = selected_project_id
                st.session_state["selected_project_name"] = selected_project_name
                st.rerun()

<<<<<<< HEAD
            with col1:

                st.write(
                    f"📄 **{index}. {file.name}**"
                )

            with col2:

                size_kb = file.size / 1024

                st.caption(
                    f"{size_kb:.1f} KB"
                )
=======
            st.divider()
            uploaded_files = st.file_uploader("Upload Research Papers (PDF)", type=["pdf"], accept_multiple_files=True)

            if uploaded_files:
                st.success(f"{len(uploaded_files)} research paper(s) selected.")
                
                if st.button("Upload & Process Papers", type="primary"):
                    results_log = []
                    for file in uploaded_files:
                        with st.spinner(f"Uploading {file.name}..."):
                            files = {"file": (file.name, file.getvalue(), "application/pdf")}
                            data = {"project_id": st.session_state["selected_project_id"]}
                            
                            res = requests.post(f"{API_URL}/papers/upload", files=files, data=data)
                            
                            if res.status_code == 200:
                                paper_id = res.json()["paper_id"]
                                
                                with st.spinner(f"Extracting & Indexing vectors for {file.name}..."):
                                    ext_res = requests.get(f"{API_URL}/papers/{paper_id}/extract")
                                    
                                    if ext_res.status_code == 200:
                                        ext_data = ext_res.json()
                                        results_log.append({
                                            "filename": file.name,
                                            "paper_id": paper_id,
                                            "chunks_created": ext_data.get("total_chunks_created", 0),
                                            "sample_chunk": ext_data.get("sample_first_chunk", "")
                                        })
                                    else:
                                        st.error(f"❌ Extraction failed: {ext_res.text}")
                            else:
                                st.error(f"❌ Failed to upload {file.name}")
>>>>>>> 017eb04 (Updated Multi-RAG Research Assistant)

                    if results_log:
                        st.session_state["latest_extraction"] = results_log
                        st.rerun()

            if "latest_extraction" in st.session_state and st.session_state["latest_extraction"]:
                st.divider()
                st.markdown("### 📊 Recently Processed Papers & Evidence Chunks")
                for item in st.session_state["latest_extraction"]:
                    st.success(f"✅ **{item['filename']}** — Created and indexed **{item['chunks_created']} text chunks** into ChromaDB! (Database ID: {item['paper_id']})")
                    if item.get("sample_chunk"):
                        with st.expander(f"View Sample Evidence Chunk from {item['filename']}"):
                            st.info(item["sample_chunk"])

<<<<<<< HEAD
            st.info(
                "Paper processing will be connected to "
                "the FastAPI backend next."
            )


# --------------------------------------------------
# RESEARCH CHAT
# --------------------------------------------------
=======
            # ---- Papers already in this project, with a way to delete one (for example a duplicate upload) ----
            st.divider()
            st.markdown("### 🗂️ Papers in this project")
            try:
                _all = requests.get(f"{API_URL}/papers/", timeout=30).json().get("papers", [])
            except Exception:
                _all = []
            _mine = [p for p in _all if str(p.get("project_id")) == str(selected_project_id)]
            if not _mine:
                st.caption("No papers in this project yet.")
            else:
                for p in _mine:
                    st.write(f"**Paper #{p['id']}** · {p.get('title') or p.get('filename')} · _{p.get('filename')}_")
                with st.expander("🗑️ Delete a paper (for example a duplicate)"):
                    labels = {f"Paper #{p['id']} · {p.get('title') or p.get('filename')} ({p.get('filename')})": p["id"] for p in _mine}
                    choice = st.selectbox("Which paper do you want to delete?", list(labels.keys()), key="delete_paper_choice")
                    sure = st.checkbox("Yes, I am sure. This removes the paper and its indexed text.", key="delete_paper_sure")
                    if st.button("Delete this paper", disabled=not sure, key="delete_paper_btn"):
                        try:
                            dres = requests.delete(f"{API_URL}/papers/{labels[choice]}", timeout=60)
                            if dres.status_code == 200:
                                # old gap results no longer match the papers
                                for k in ("detected_gaps", "gaps_without", "gaps_project_id", "final_report"):
                                    st.session_state.pop(k, None)
                                st.success("Deleted. Run Gap Detection and Gap Validation again so the gaps match your papers.")
                                st.rerun()
                            else:
                                st.error(f"Could not delete: {dres.text}")
                        except Exception as e:
                            st.error(f"Could not connect to backend: {e}")
        else:
            st.info("Please select a valid project from the dropdown above to display the PDF upload zone.")
>>>>>>> 017eb04 (Updated Multi-RAG Research Assistant)

elif page == "Research Chat":
    st.markdown('<div class="main-title">Research Chat & Evidence Q&A</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Ask questions about your uploaded paper and receive evidence-grounded answers.</div>', unsafe_allow_html=True)

    try:
        proj_res = requests.get(f"{API_URL}/projects/")
        if proj_res.status_code == 200:
            p_data = proj_res.json()
            projects = p_data.get("projects", []) if isinstance(p_data, dict) else p_data
        else:
            projects = []
    except Exception:
        projects = []

<<<<<<< HEAD
    st.markdown(
        '<div class="subtitle">'
        'Ask questions across the research paper collection.'
        '</div>',
        unsafe_allow_html=True
    )

    query = st.text_input(
        "Research Question",
        placeholder="e.g. What methodology does this paper use?"
    )

    top_k = st.slider(
        "Number of evidence chunks",
        min_value=1,
        max_value=10,
        value=5
    )

    if st.button(
        "Search Research Evidence",
        type="primary",
        use_container_width=True
    ):

        if not query.strip():

            st.warning(
                "Please enter a research question."
            )

        else:

            try:

                from backend.services.retrieval.retrieval_service import (
                    retrieve_chunks
                )

                from backend.services.evidence.evidence_engine import (
                    build_evidence_summary
                )

                with st.spinner(
                    "Searching research evidence..."
                ):

                    chunks = retrieve_chunks(
                        query,
                        top_k=top_k
                    )

                    evidence = build_evidence_summary(
                        chunks
                    )

                st.success(
                    f"Retrieved {len(chunks)} evidence chunks "
                    f"from {evidence['total_papers']} paper(s)."
                )

                st.markdown("### Evidence")

                if not chunks:

                    st.warning(
                        "No relevant evidence found."
                    )

                else:

                    for index, chunk in enumerate(
                        chunks,
                        start=1
                    ):

                        with st.expander(
                            f"Evidence {index} — "
                            f"Paper {chunk['paper_id']} | "
                            f"Page {chunk['page_number']} | "
                            f"{chunk['category']}"
                        ):

                            st.write(
                                chunk["text"]
                            )

                            st.caption(
                                f"Paper ID: {chunk['paper_id']} | "
                                f"Page: {chunk['page_number']} | "
                                f"Category: {chunk['category']} | "
                                f"Distance: {chunk['distance']:.4f}"
                            )

            except Exception as e:

                st.error(
                    f"Error while retrieving evidence: {e}"
                )


# --------------------------------------------------
# EVIDENCE ANALYSIS
# --------------------------------------------------
=======
    if not projects:
        st.warning("⚠️ No projects found. Please create a project and upload research papers first.")
    else:
        project_options = {}
        for p in projects:
            p_title = p.get("name") or p.get("project_name") or p.get("title", f"Project #{p.get('id')}")
            project_options[p_title] = p.get("id")

        dropdown_list = ["-- Select a Project --"] + list(project_options.keys())
        
        default_idx = 0
        if "selected_project_name" in st.session_state and st.session_state["selected_project_name"] in dropdown_list:
            default_idx = dropdown_list.index(st.session_state["selected_project_name"])

        selected_proj_name = st.selectbox("Select Project for Querying", dropdown_list, index=default_idx)

        if selected_proj_name != "-- Select a Project --":
            selected_proj_id = project_options[selected_proj_name]
            if st.session_state.get("selected_project_id") != selected_proj_id:
                st.session_state["selected_project_id"] = selected_proj_id
                st.session_state["selected_project_name"] = selected_proj_name
                st.rerun()

            st.divider()

            if "chat_history" not in st.session_state:
                st.session_state["chat_history"] = []

            for message in st.session_state["chat_history"]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                    if message.get("evidence"):
                        with st.expander("📌 Source Evidence & Citations"):
                            for idx, ev in enumerate(message["evidence"], start=1):
                                st.caption(f"**Evidence #{idx}** — Paper ID: {ev['paper_id']} (Page {ev['page']})")
                                st.info(ev["text"])

            user_question = st.chat_input("Ask a question about the uploaded research paper...")

            if user_question:
                st.session_state["chat_history"].append({"role": "user", "content": user_question})
                with st.chat_message("user"):
                    st.markdown(user_question)

                with st.chat_message("assistant"):
                    with st.spinner("Retrieving evidence & synthesizing response..."):
                        try:
                            res = requests.post(
                                f"{API_URL}/chat/query",
                                json={
                                    "project_id": st.session_state["selected_project_id"],
                                    "query": user_question,
                                    "top_k": 6
                                }
                            )

                            if res.status_code == 200:
                                data = res.json()
                                answer_text = data.get("answer", "No response synthesized.")
                                evidence = data.get("evidence", [])

                                st.markdown(answer_text)

                                if evidence:
                                    with st.expander("📌 Source Evidence & Citations"):
                                        for idx, m in enumerate(evidence, start=1):
                                            st.caption(f"**Evidence #{idx}** — Paper ID: {m['paper_id']}, Page {m['page']}")
                                            st.info(m["text"])

                                st.session_state["chat_history"].append({
                                    "role": "assistant",
                                    "content": answer_text,
                                    "evidence": evidence
                                })
                            else:
                                st.error(f"Chat query failed: {res.text}")
                        except Exception as e:
                            st.error(f"Could not connect to backend: {e}")
        else:
            st.info("Please select a research project from the dropdown above to start asking questions.")
>>>>>>> 017eb04 (Updated Multi-RAG Research Assistant)

elif page == "Evidence Analysis":
    st.markdown('<div class="main-title">Evidence Analysis & Cross-Paper Comparison</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Compare findings, methodologies, and benchmarks across all uploaded papers.</div>', unsafe_allow_html=True)

    active_proj_id = st.session_state.get("selected_project_id")

    if not active_proj_id:
        st.info("Please select a project in the Research Papers or Research Chat tab first.")
    else:
        DIMENSIONS = ["Novelty", "Methodology", "Dataset", "Results", "Limitations"]

        # Indexed papers of the active project
        project_papers = []
        try:
            papers_res = requests.get(f"{API_URL}/papers/", timeout=30)
            if papers_res.status_code == 200:
                project_papers = [
                    p for p in papers_res.json().get("papers", [])
                    if str(p.get("project_id")) == str(active_proj_id)
                    and p.get("processing_status") == "EXTRACTED_AND_INDEXED"
                ]
        except Exception as e:
            st.error(f"Could not connect to backend: {e}")

        def fetch_evidence():
            try:
                r = requests.get(f"{API_URL}/evidence/{active_proj_id}", timeout=60)
                if r.status_code == 200:
                    return r.json().get("papers", [])
            except Exception:
                pass
            return []

        if not project_papers:
            st.warning("⚠️ No indexed papers in this project yet. Upload and process papers first.")
        else:
            st.caption(f"{len(project_papers)} indexed paper(s) in this project.")

            col_opt1, col_opt2 = st.columns(2)
            with col_opt1:
                use_llm = st.checkbox("Use the local LLM for summaries (slower, better wording)", value=True)
            with col_opt2:
                reanalyze = st.checkbox("Re-analyze papers that were already analyzed", value=False)

            if st.button("🔬 Run Evidence Analysis", type="primary"):
                done_ids = {item["paper_id"] for item in fetch_evidence()}
                progress = st.progress(0.0)
                for i, p in enumerate(project_papers, start=1):
                    label = p.get("title") or p.get("filename")
                    if p["id"] in done_ids and not reanalyze:
                        progress.progress(i / len(project_papers))
                        continue
                    with st.spinner(f"Analyzing {label} ({i}/{len(project_papers)}) - this can take a few minutes..."):
                        try:
                            r = requests.post(
                                f"{API_URL}/evidence/analyze/paper/{p['id']}",
                                params={"use_llm": str(use_llm).lower()},
                                timeout=900
                            )
                            if r.status_code != 200:
                                st.error(f"Analysis failed for {label}: {r.text}")
                        except Exception as e:
                            st.error(f"Could not analyze {label}: {e}")
                    progress.progress(i / len(project_papers))
                st.success("Evidence analysis finished.")

            evidence_data = fetch_evidence()

            if not evidence_data:
                st.info("No analysis yet. Click 'Run Evidence Analysis' to build the comparison table from your papers.")
            else:
                st.markdown("### 📊 Extracted Findings Matrix")
                st.caption("Built from each paper's own text. Every cell shows its source in [Paper ID, Page].")

                # Own HTML table: fixed column widths, full paper titles, no index column.
                # Colors are neutral so it stays readable in both light and dark mode.
                esc = html.escape
                head = '<th class="ev-dim">Dimension</th>' + "".join(
                    f'<th><span class="ev-id">Paper #{item["paper_id"]}</span><br>{esc(item.get("title") or "")}</th>'
                    for item in evidence_data
                )
                body = ""
                for dim in DIMENSIONS:
                    cells = ""
                    for item in evidence_data:
                        cell = item.get("dimensions", {}).get(dim, {})
                        raw = (cell.get("summary") or "").strip()
                        # "Not stated" is the backend's internal marker; show a more accurate label
                        missing = raw.lower() in ("", "not stated") or raw.lower().startswith("no relevant text")
                        summary = esc("Not found in the text" if missing else raw)
                        cite = esc(cell.get("citation") or "")
                        muted = " ev-muted" if missing else ""
                        cells += (
                            f'<td><div class="ev-text{muted}">{summary}</div>'
                            + (f'<div class="ev-cite">{cite}</div>' if cite else "")
                            + "</td>"
                        )
                    body += f'<tr><td class="ev-dim">{esc(dim)}</td>{cells}</tr>'

                n_papers = len(evidence_data)
                matrix_html = (
                    "<style>"
                    ".ev-wrap{overflow-x:auto;margin:8px 0 24px 0;}"
                    f".ev-table{{border-collapse:collapse;width:100%;table-layout:fixed;min-width:{150 + 280 * n_papers}px;}}"
                    ".ev-table th,.ev-table td{border:1px solid rgba(128,128,128,0.35);padding:12px 14px;"
                    "vertical-align:top;text-align:left;font-size:14px;line-height:1.5;"
                    "word-wrap:break-word;overflow-wrap:anywhere;}"
                    ".ev-table th{background:rgba(128,128,128,0.15);font-weight:600;}"
                    ".ev-table .ev-dim{width:150px;font-weight:700;background:rgba(128,128,128,0.10);}"
                    ".ev-id{font-size:12px;opacity:0.7;font-weight:600;}"
                    ".ev-cite{margin-top:8px;font-size:12px;opacity:0.65;}"
                    ".ev-muted{opacity:0.55;font-style:italic;}"
                    "</style>"
                    f'<div class="ev-wrap"><table class="ev-table"><thead><tr>{head}</tr></thead>'
                    f"<tbody>{body}</tbody></table></div>"
                )
                st.markdown(matrix_html, unsafe_allow_html=True)

                st.markdown("### 📌 Source Evidence")
                for item in evidence_data:
                    with st.expander(f"Paper #{item['paper_id']} — {item.get('title', '')}"):
                        for dim in DIMENSIONS:
                            cell = item.get("dimensions", {}).get(dim, {})
                            how = "LLM summary" if cell.get("method") == "llm" else "extracted sentences"
                            st.markdown(f"**{dim}** ({how})")
                            if not cell.get("from_tagged_section", True) and cell.get("evidence"):
                                st.caption("No section was tagged for this dimension, so the closest text in the paper was used.")
                            for ev in cell.get("evidence", []):
                                st.caption(f"Page {ev['page']} · section: {ev['section']}")
                                st.info(ev["text"])

# --------------------------------------------------
# GAP DETECTION
# --------------------------------------------------

elif page == "Gap Detection":
    st.markdown('<div class="main-title">Research Gap Detection Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Finds the limitations, open issues and future work that the authors themselves state, each with its page number.</div>', unsafe_allow_html=True)

    active_proj_id = st.session_state.get("selected_project_id")

    if not active_proj_id:
        st.warning("⚠️ Please select an active Research Project to scan for gaps.")
    else:
        load_saved_gaps(active_proj_id)
        if st.button("🔍 Run Gap Detection", type="primary"):
            with st.spinner("Reading the limitations and future-work sections of every paper..."):
                try:
                    res = requests.get(f"{API_URL}/gaps/detect/{active_proj_id}", timeout=600)
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state["detected_gaps"] = data.get("gaps", [])
                        st.session_state["gaps_without"] = data.get("papers_without_gaps", [])
                        st.session_state["gaps_project_id"] = active_proj_id
                        st.rerun()
                    else:
                        st.error(f"Gap detection failed: {res.text}")
                except Exception as e:
                    st.error(f"Could not connect to backend: {e}")

        gaps = st.session_state.get("detected_gaps") or []
        if gaps:
            st.success(f"{len(gaps)} gaps found. Each one is a sentence copied from the paper, so you can check it in the PDF.")
            icons = {"Future work": "🟦", "Open issue": "🟧", "Limitation": "🟥"}
            for gap in gaps:
                icon = icons.get(gap.get("type"), "🟥")
                with st.expander(f"{icon} {gap['gap_id']} · {gap.get('type', 'Gap')} — {gap['title']}", expanded=True):
                    st.write(gap["description"])
                    st.markdown(f"**Source:** {gap.get('citation', '')}  \n*{gap.get('paper_title', '')}*")
                    st.info(f"\"{gap['evidence_snippet']}\"")
                    if gap["status"] == "DETECTED":
                        st.caption("Status: DETECTED · not checked against the other papers yet (see Gap Validation)")
                    else:
                        st.caption(f"Status: {gap['status']} · {gap.get('validation', {}).get('summary', '')}")
            for pid in st.session_state.get("gaps_without") or []:
                st.caption(f"Paper #{pid}: the authors do not state any limitation or future work in the text, so no gap was taken from it.")
        elif st.session_state.get("gaps_project_id") == active_proj_id:
            st.info("No gaps were found in the text of these papers.")

# --------------------------------------------------
# GAP VALIDATION
# --------------------------------------------------

elif page == "Gap Validation":
    st.markdown('<div class="main-title">Evidence-Traceable Gap Validation</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Checks every gap against the other papers: does another paper also call it open, or say it works on it? Every answer shows the sentence and page.</div>', unsafe_allow_html=True)

    active_proj_id = st.session_state.get("selected_project_id")
    if active_proj_id:
        load_saved_gaps(active_proj_id)
    gaps = st.session_state.get("detected_gaps") or []

    if not active_proj_id:
        st.warning("⚠️ Please select an active Research Project first.")
    elif not gaps:
        st.info("No gaps detected yet. Please run Gap Detection first.")
    else:
        if st.button("✅ Validate gaps against the other papers", type="primary"):
            with st.spinner("Searching the other papers for evidence for and against each gap..."):
                try:
                    res = requests.get(f"{API_URL}/gaps/validate/{active_proj_id}", timeout=600)
                    if res.status_code == 200:
                        st.session_state["detected_gaps"] = res.json().get("gaps", [])
                        st.rerun()
                    else:
                        st.error(f"Gap validation failed: {res.text}")
                except Exception as e:
                    st.error(f"Could not connect to backend: {e}")

        badge = {
            "CORROBORATED": ("success", "✅ Supported: another paper also reports this as open"),
            "CHALLENGED": ("warning", "⚠️ Possibly addressed: another paper reports work on it (check the sentence)"),
            "MIXED": ("warning", "🔶 Mixed: evidence for and against"),
            "STANDS": ("info", "⚪ No counter-evidence found in the other papers"),
            "NO_OTHER_PAPERS": ("info", "No other paper to compare with"),
            "DETECTED": ("warning", "⏳ Not validated yet"),
        }
        groups = [("also_open", "Other papers that also describe this as open or missing"),
                  ("addresses", "Other papers that say they work on it"),
                  ("related", "Related passages (same topic, no clear statement)")]
        for gap in gaps:
            kind, text = badge.get(gap["status"], badge["DETECTED"])
            with st.expander(f"{gap['gap_id']} · {gap['title']}  —  {text}", expanded=gap["status"] != "DETECTED"):
                st.caption(f"Stated in Paper #{gap['paper_id']}, page {gap['page']}")
                st.info(f"\"{gap['evidence_snippet']}\"")
                getattr(st, kind)(text)
                evidence = (gap.get("validation") or {}).get("evidence", [])
                for rel, label in groups:
                    items = [e for e in evidence if e["relation"] == rel]
                    if not items:
                        continue
                    st.markdown(f"**{label}**")
                    for e in items:
                        st.markdown(f"{e['citation']} *{e['paper_title']}*")
                        st.write(f"\"{e['sentence']}\"")
                        st.caption(f"Why: {e['reason']} · shared words: {', '.join(e['shared_words'])} · match score {e['similarity']}")
                if gap["status"] == "STANDS":
                    st.caption("This means none of the other papers says it is solved. It does not prove that nobody solved it.")

# --------------------------------------------------
# FINAL REPORT
# --------------------------------------------------

elif page == "Final Report":
    st.markdown('<div class="main-title">Final Research Report</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Builds one report from your saved results: the paper comparison, the research gaps and their validation. Every statement shows its paper and page.</div>', unsafe_allow_html=True)

    active_proj_id = st.session_state.get("selected_project_id")
    if not active_proj_id:
        st.warning("⚠️ Please select an active Research Project first.")
    else:
        if st.button("📄 Generate Research Report", type="primary"):
            with st.spinner("Collecting the saved evidence, gaps and validation results..."):
                try:
                    res = requests.get(f"{API_URL}/report/{active_proj_id}", timeout=120)
                    if res.status_code == 200:
                        st.session_state["final_report"] = res.json()
                    else:
                        st.error(f"Could not build the report: {res.text}")
                except Exception as e:
                    st.error(f"Could not connect to backend: {e}")

<<<<<<< HEAD
    st.info(
        "The final evidence-traceable research report "
        "will be generated here."
    )
=======
        report = st.session_state.get("final_report")
        if report and report.get("project_id") == active_proj_id:
            info = report.get("info", {})
            if info.get("missing_evidence"):
                st.warning("Evidence Analysis is missing for some papers. Run it on the Evidence Analysis page, then generate the report again.")
            if info.get("not_validated"):
                st.warning(f"{info['not_validated']} gap(s) are not validated yet. Run Gap Validation, then generate the report again.")
            if info.get("gaps", 0) == 0:
                st.warning("No gaps are saved yet. Run Gap Detection and Gap Validation first.")

            d1, d2 = st.columns(2)
            with d1:
                st.download_button("⬇️ Download as Markdown (.md)", report["markdown"].encode("utf-8"),
                                   file_name="research_report.md", mime="text/markdown")
            with d2:
                st.download_button("⬇️ Download as web page (.html)", report["html"].encode("utf-8"),
                                   file_name="research_report.html", mime="text/html")
            st.caption("To get a PDF: open the .html file in your browser, press Ctrl+P, and choose 'Save as PDF'.")
            st.divider()
            st.markdown(report["markdown"])
        else:
            st.info("Click 'Generate Research Report' to build the report from your saved results.")
>>>>>>> 017eb04 (Updated Multi-RAG Research Assistant)
