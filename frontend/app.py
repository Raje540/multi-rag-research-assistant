import sys
from pathlib import Path

# --------------------------------------------------
# PROJECT ROOT PATH
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Multi-RAG Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --------------------------------------------------
# CUSTOM STYLING
# --------------------------------------------------

st.markdown("""
<style>

    /* ---------------------------------------------
       MAIN APPLICATION
       --------------------------------------------- */

    .stApp {
        background-color: #f7f8fa;
    }


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
        color: #111827;
        margin-bottom: 4px;
    }

    .subtitle {
        font-size: 15px;
        color: #6b7280;
        margin-bottom: 30px;
    }


    /* ---------------------------------------------
       METRIC CARDS
       --------------------------------------------- */

    .metric-card {
        background-color: #ffffff;
        padding: 22px;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }

    .metric-title {
        font-size: 14px;
        color: #6b7280;
    }

    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #111827;
        margin-top: 5px;
    }


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

    .section-title {
        font-size: 21px;
        font-weight: 650;
        color: #111827;
        margin-top: 25px;
    }


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

</style>
""", unsafe_allow_html=True)


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

st.markdown(
    '<div class="main-title">Research Intelligence Dashboard</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Analyze multiple research papers, trace evidence, and validate research gaps.'
    '</div>',
    unsafe_allow_html=True
)


# --------------------------------------------------
# METRIC CARDS
# --------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.markdown("""
    <div class="metric-card">
        <div class="metric-title">Research Papers</div>
        <div class="metric-value">0</div>
    </div>
    """, unsafe_allow_html=True)


with col2:

    st.markdown("""
    <div class="metric-card">
        <div class="metric-title">Evidence Chunks</div>
        <div class="metric-value">0</div>
    </div>
    """, unsafe_allow_html=True)


with col3:

    st.markdown("""
    <div class="metric-card">
        <div class="metric-title">Research Gaps</div>
        <div class="metric-value">0</div>
    </div>
    """, unsafe_allow_html=True)


with col4:

    st.markdown("""
    <div class="metric-card">
        <div class="metric-title">Validated Gaps</div>
        <div class="metric-value">0</div>
    </div>
    """, unsafe_allow_html=True)


# --------------------------------------------------
# OVERVIEW
# --------------------------------------------------

if page == "Overview":

    st.markdown(
        '<div class="section-title">Research Workspace</div>',
        unsafe_allow_html=True
    )

    st.info(
        "Create a research project and upload multiple papers "
        "to begin evidence-based analysis."
    )


# --------------------------------------------------
# RESEARCH PROJECTS
# --------------------------------------------------

elif page == "Research Projects":

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

        if not project_name or not research_domain:

            st.warning(
                "Please enter the project name and research domain."
            )

        else:

            st.success(
                f"Research project '{project_name}' is ready to be created."
            )

            st.info(
                "Database storage will be connected in the next stage."
            )


# --------------------------------------------------
# RESEARCH PAPERS
# --------------------------------------------------

elif page == "Research Papers":

    st.markdown(
        '<div class="main-title">Research Paper Collection</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'Upload multiple research papers belonging to the selected project.'
        '</div>',
        unsafe_allow_html=True
    )

    uploaded_files = st.file_uploader(
        "Upload Research Papers",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:

        st.success(
            f"{len(uploaded_files)} research paper(s) selected."
        )

        st.markdown("#### Selected Papers")

        for index, file in enumerate(uploaded_files, start=1):

            col1, col2 = st.columns([5, 1])

            with col1:

                st.write(
                    f"📄 **{index}. {file.name}**"
                )

            with col2:

                size_kb = file.size / 1024

                st.caption(
                    f"{size_kb:.1f} KB"
                )

        st.divider()

        if st.button(
            "Process Research Papers",
            type="primary",
            use_container_width=True
        ):

            st.info(
                "Paper processing will be connected to "
                "the FastAPI backend next."
            )


# --------------------------------------------------
# RESEARCH CHAT
# --------------------------------------------------

elif page == "Research Chat":

    st.markdown(
        '<div class="main-title">Research Chat</div>',
        unsafe_allow_html=True
    )

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

elif page == "Evidence Analysis":

    st.markdown(
        '<div class="main-title">Evidence Analysis</div>',
        unsafe_allow_html=True
    )

    st.info(
        "Cross-paper evidence comparison will appear here."
    )


# --------------------------------------------------
# GAP DETECTION
# --------------------------------------------------

elif page == "Gap Detection":

    st.markdown(
        '<div class="main-title">Research Gap Detection</div>',
        unsafe_allow_html=True
    )

    st.info(
        "Potential research gaps will be identified "
        "from evidence across multiple papers."
    )


# --------------------------------------------------
# GAP VALIDATION
# --------------------------------------------------

elif page == "Gap Validation":

    st.markdown(
        '<div class="main-title">Gap Validation</div>',
        unsafe_allow_html=True
    )

    st.info(
        "Supporting and counter-evidence will be evaluated here."
    )


# --------------------------------------------------
# FINAL REPORT
# --------------------------------------------------

elif page == "Final Report":

    st.markdown(
        '<div class="main-title">Final Research Report</div>',
        unsafe_allow_html=True
    )

    st.info(
        "The final evidence-traceable research report "
        "will be generated here."
    )