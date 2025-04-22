import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

def init_authenticator():
    with open('./config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)
    
    return stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )

authenticator = init_authenticator()

def login():
    try:
        # Only initialize logout key if not present
        if 'logout' not in st.session_state:
            st.session_state['logout'] = True  # Assume logged out by default

        return authenticator.login('Login', 'main')
    except Exception as e:
        st.error(f"Login failed: {str(e)}")
        return None, None, None

name, authentication_status, username = login()

if authentication_status:
    authenticator.logout('Logout', 'sidebar')
    st.session_state['name'] = name
    st.session_state['authentication_status'] = authentication_status
    st.session_state['username'] = username
elif authentication_status is False:
    st.error('Username/password is incorrect')
elif authentication_status is None:
    st.warning('Please enter your username and password')
