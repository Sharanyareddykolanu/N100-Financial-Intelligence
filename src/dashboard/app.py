import streamlit as st

st.set_page_config(
    page_title="Nifty 100 Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("Nifty 100 Analytics")

screens = [
    "Home",
    "Profile",
    "Screener",
    "Peers",
    "Trends",
    "Sectors",
    "Capital",
    "Reports",
]

selected = st.sidebar.radio("Navigate", screens)

st.title("Nifty 100 Analytics")
st.write(f"Currently selected: **{selected}**")