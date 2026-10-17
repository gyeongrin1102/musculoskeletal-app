import streamlit as st


THEME_CSS = """
<style>
:root {
    --ehs-primary: #05507D;
    --ehs-navy: #07344F;
    --ehs-accent: #0E8B9C;
    --ehs-background: #F3F7FA;
    --ehs-surface: #FFFFFF;
    --ehs-border: #DFE8EF;
    --ehs-text: #18384C;
    --ehs-muted: #657C8B;
}
html, body, [data-testid="stAppViewContainer"] {
    font-family: "Pretendard", "Noto Sans KR", "Apple SD Gothic Neo", sans-serif;
    color: var(--ehs-text);
}
[data-testid="stAppViewContainer"] { background: var(--ehs-background); }
[data-testid="stHeader"] { background: rgba(243, 247, 250, 0.96); }
[data-testid="stAppViewContainer"] .block-container {
    max-width: 1660px;
    padding: 1.75rem clamp(1rem, 2.4vw, 2.5rem) 3rem;
}
h1, h2, h3 { color: var(--ehs-navy); }
h1 { font-size: 1.8rem; font-weight: 700; }
h2, h3 { font-weight: 650; }
[data-testid="stSidebar"] { background: var(--ehs-navy); }
[data-testid="stSidebar"] * { color: #F5FAFC; }
[data-testid="stSidebarNav"] { padding: 0.55rem 0 1rem; }
[data-testid="stSidebarNavLink"] {
    min-height: 2.7rem;
    margin: 3px 8px;
    padding: 0.45rem 0.75rem;
    border-radius: 6px;
    transition: background-color 120ms ease;
}
[data-testid="stSidebarNavLink"]:hover { background: rgba(255, 255, 255, 0.1); }
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background: #DCECF4;
    border-left: 3px solid var(--ehs-accent);
    font-weight: 700;
}
[data-testid="stSidebarNavLink"][aria-current="page"] * { color: var(--ehs-navy); }
[data-testid="stMetric"] {
    min-height: 5.4rem;
    background: var(--ehs-surface);
    border: 1px solid var(--ehs-border);
    border-top: 3px solid var(--ehs-accent);
    border-radius: 7px;
    padding: 0.8rem 1rem;
    box-shadow: 0 2px 8px rgba(7, 52, 79, 0.045);
}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p,
[data-testid="stMetricValue"], [data-testid="stMetricValue"] div {
    color: var(--ehs-navy) !important;
}
[data-testid="stMetricLabel"] p { font-weight: 650; }
[data-testid="stMetricValue"] { font-weight: 750; }
[data-baseweb="tab-list"] { gap: 0.35rem; border-bottom: 1px solid var(--ehs-border); }
[data-baseweb="tab"] { color: var(--ehs-navy); }
[data-baseweb="tab-highlight"] { background: var(--ehs-accent); }
[data-testid="stExpander"] { border: 1px solid var(--ehs-border); border-radius: 7px; background: var(--ehs-surface); }
[data-testid="stDataFrame"], [data-testid="stTable"] {
    max-width: 100%;
    border: 1px solid var(--ehs-border);
    border-radius: 7px;
    background: var(--ehs-surface);
}
.stButton > button, [data-testid="stDownloadButton"] button {
    min-height: 2.65rem;
    border: 1px solid #C7D7E0;
    border-radius: 6px;
    color: var(--ehs-navy);
    font-weight: 650;
    transition: background-color 120ms ease, border-color 120ms ease;
}
.stButton > button:hover, [data-testid="stDownloadButton"] button:hover {
    border-color: var(--ehs-accent);
    color: var(--ehs-primary);
}
.stButton > button[kind="primary"] {
    background: var(--ehs-primary);
    border-color: var(--ehs-primary);
    color: #FFFFFF;
}
.stButton > button[kind="primary"]:hover { background: var(--ehs-navy); color: #FFFFFF; }
input, textarea { border-radius: 5px !important; }
[data-baseweb="select"] > div { border-radius: 5px; }
[data-testid="stMain"] [data-testid="stWidgetLabel"],
[data-testid="stMain"] [data-testid="stWidgetLabel"] p,
[data-testid="stMain"] [data-testid="stRadio"] label,
[data-testid="stMain"] [data-testid="stCheckbox"] label,
[data-testid="stMain"] [data-testid="stCaptionContainer"],
[data-testid="stMain"] [data-testid="stCaptionContainer"] p,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] > p {
    color: var(--ehs-navy) !important;
}
[data-testid="stMain"] [data-testid="stRadio"] label,
[data-testid="stMain"] [data-testid="stCheckbox"] label {
    background-color: transparent !important;
}
[data-testid="stMain"] [data-testid="stTextInput"] [data-baseweb="input"],
[data-testid="stMain"] [data-testid="stNumberInput"] [data-baseweb="input"],
[data-testid="stMain"] [data-testid="stDateInput"] [data-baseweb="input"],
[data-testid="stMain"] [data-testid="stTextArea"] [data-baseweb="textarea"] {
    background-color: #FFFFFF !important;
    color: var(--ehs-navy) !important;
    border-color: var(--ehs-border) !important;
}
[data-testid="stMain"] [data-testid="stTextInput"] input,
[data-testid="stMain"] [data-testid="stNumberInput"] input,
[data-testid="stMain"] [data-testid="stDateInput"] input,
[data-testid="stMain"] [data-testid="stTextArea"] textarea,
[data-testid="stMain"] [data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMain"] [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    color: var(--ehs-navy) !important;
    border-color: var(--ehs-border) !important;
}
[data-testid="stMain"] input::placeholder,
[data-testid="stMain"] textarea::placeholder {
    color: #526A7A !important;
    opacity: 1;
}
[data-testid="stMain"] input:focus,
[data-testid="stMain"] textarea:focus,
[data-testid="stMain"] [data-baseweb="select"]:focus-within > div {
    border-color: var(--ehs-primary) !important;
    box-shadow: 0 0 0 1px var(--ehs-primary) !important;
    outline: none;
}
[data-testid="stMain"] input[type="radio"],
[data-testid="stMain"] input[type="checkbox"] {
    accent-color: var(--ehs-primary);
}
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="popover"] [role="option"] {
    background-color: #FFFFFF;
    color: var(--ehs-navy);
}
[data-baseweb="popover"] [role="option"][aria-selected="true"] {
    background-color: #EAF3F7;
    color: var(--ehs-navy);
}
[data-testid="stCameraInput"], [data-testid="stFileUploader"] {
    border: 1px solid var(--ehs-border);
    border-radius: 7px;
    background: var(--ehs-surface);
}
[data-testid="stAlert"] { border-radius: 7px; }
@media (max-width: 720px) {
    [data-testid="stAppViewContainer"] .block-container { padding: 1rem 0.75rem 2rem; }
    h1 { font-size: 1.45rem; }
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: 0.65rem; }
    [data-testid="column"] { min-width: 100% !important; }
    [data-testid="stDataFrame"] { overflow-x: auto; }
    [data-testid="stImage"] img { max-height: 62vh; object-fit: contain; }
    .stButton > button, [data-testid="stDownloadButton"] button { width: 100%; }
}
</style>
"""


def apply_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)
