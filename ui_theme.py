import streamlit as st


THEME_CSS = """
<style>
:root {
    --ehs-primary: #05507D;
    --ehs-navy: #07344F;
    --ehs-accent: #0E8B9C;
}
html, body, [data-testid="stAppViewContainer"] {
    font-family: "Pretendard", "Noto Sans KR", "Apple SD Gothic Neo", sans-serif;
}
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
@media (max-width: 720px) {
    [data-testid="stAppViewContainer"] .block-container { padding: 1rem 0.75rem 2rem; }
    h1 { font-size: 1.45rem; }
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: 0.65rem; }
    [data-testid="column"] { min-width: 100%; }
    [data-testid="stImage"] img { max-height: 62vh; object-fit: contain; }
}
</style>
"""


def apply_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)
