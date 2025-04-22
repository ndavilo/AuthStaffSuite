import streamlit as st

def init_auth_session_keys():
    for key in ['logout', 'authentication_status', 'name', 'username']:
        if key not in st.session_state:
            # Set sensible defaults
            st.session_state[key] = True if key == 'logout' else None
