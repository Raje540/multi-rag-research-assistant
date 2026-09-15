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

    /* Main background */
    .stApp {
        background-color: #f7f8fa;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #111827;
    }

    section[data-testid="stSidebar"] * {
        color: #f9fafb;
    }

    /* Main title */
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

    /* Cards */
    .metric-card {
        background-color: white;
        padding: 22px;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
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

    /* Upload area */
    .upload-card {
        background-color: white;
        padding: 28px;
        border-radius: 14px;
        border: 1px solid #e5e7eb;
        margin-top: 20px;
    }

    /* Section headings */
    .section-title {
        font-size: 21px;
        font-weight: 650;
        color: #111827;
        margin-top: 25px;
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
# PAGE CONTENT
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
        placeholder=(
            "Describe the research problem or objective..."
        ),
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
                f"Research project '{project_name}' "
                "is ready to be created."
            )

            st.info(
                "Database storage will be connected in the next stage."
            )

#RESEARCH PAPER

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
                st.caption(f"{size_kb:.1f} KB")

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

# RESEARCH CHAT

elif page == "Research Chat":

    st.markdown(
        '<div class="main-title">Research Chat</div>',
        unsafe_allow_html=True
    )

    st.info(
        "Ask questions across all uploaded research papers."
    )


elif page == "Evidence Analysis":

    st.markdown(
        '<div class="main-title">Evidence Analysis</div>',
        unsafe_allow_html=True
    )

    st.info(
        "Cross-paper evidence comparison will appear here."
    )


elif page == "Gap Detection":

    st.markdown(
        '<div class="main-title">Research Gap Detection</div>',
        unsafe_allow_html=True
    )

    st.info(
        "Potential research gaps will be identified "
        "from evidence across multiple papers."
    )


elif page == "Gap Validation":

    st.markdown(
        '<div class="main-title">Gap Validation</div>',
        unsafe_allow_html=True
    )

    st.info(
        "Supporting and counter-evidence will be evaluated here."
    )


elif page == "Final Report":

    st.markdown(
        '<div class="main-title">Final Research Report</div>',
        unsafe_allow_html=True
    )

    st.info(
        "The final evidence-traceable research report "
        "will be generated here."
    )

