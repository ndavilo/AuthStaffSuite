# utils/config.py
import base64
import streamlit as st
from pathlib import Path

def configure_app():
    """Centralized app configuration that must be called first"""
    # Favicon handling
    favicon = None
    try:
        if Path("EFCC1.png").exists():
            with open("EFCC1.png", "rb") as f:
                favicon = f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    except Exception as e:
        st.warning(f"Couldn't load favicon: {str(e)}")

    # Set all page config at once
    st.set_page_config(
        page_title="EFCC StaffSuite",
        page_icon=favicon if favicon else ":bust_in_silhouette:",
        layout="wide",
        initial_sidebar_state="expanded"
    )