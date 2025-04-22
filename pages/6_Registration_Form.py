from utils.config import configure_app
configure_app()
import streamlit as st
from streamlit_webrtc import webrtc_streamer
import av
import face_utils
from auth import authenticator

from utils.session import init_auth_session_keys
init_auth_session_keys()

# Set page config
st.subheader('Registration Form')

# Apply custom styling
from styles import LAGOS_STYLE, get_topbar_style, get_topbar_html

# Apply styling and top bar
st.markdown(LAGOS_STYLE, unsafe_allow_html=True)
st.markdown(get_topbar_style(), unsafe_allow_html=True)
st.markdown(get_topbar_html(), unsafe_allow_html=True)


if not st.session_state.get("authentication_status"):
    name, authentication_status, username = authenticator.login('Login', 'main')
    if authentication_status:
        st.session_state.update({
            'name': name,
            'authentication_status': authentication_status,
            'username': username
        })
        st.rerun()
else:
    # Only show content to authenticated users
    authenticator.logout('Logout', 'sidebar')
    st.write(f'Welcome *{st.session_state["name"]}*')
    
    # Import check requirements after initial Streamlit setup
    import check_requirements

    def main():
        # Network verification first
        access_granted, reason = check_requirements.ip_address_range_verification()
        
        if not access_granted:
            st.error(f"Access Denied: Invalid {reason}")
            st.stop()
            
        # Init registration form
        registration_form = face_utils.RegistrationForm()

        # Personal Information
        col1, col2 = st.columns(2)
        with col1:
            file_number = st.text_input('Enter your file number: ', placeholder='File Number')
            first_name = st.text_input(label='Enter your first name: ', placeholder='First Name')
        with col2:
            last_name = st.text_input(label='Enter your last name: ', placeholder='Last Name')
            
            # Zone selection
            zones = {
                "1": "Lagos Zone 1",
                "2": "Lagos Zone 2",
                "3": "Abuja Zone 1",
                "4": "Port Harcourt Zone",
                "5": "Kano Zone"
            }
            zone_number = st.selectbox(
                "Select Zone:",
                options=list(zones.keys()),
                format_func=lambda x: zones[x]
            )
            zone = zones[zone_number]

        # Role selection options
        st.write("Select Role:")
        roles = {
            "1": "ICT",
            "2": "LEGAL",
            "3": "Investigation",
            "4": "Unit Head",
            "5": "Sectional Head",
            "6": "Admin",
            "7": "Security",
            "8": "Forensic",
            "9": "Others"
        }
        role_number = st.radio(
            "Choose role:",
            options=list(roles.keys()),
            format_func=lambda x: f"{x}. {roles[x]}",
            horizontal=True
        )
        role = roles[role_number]

        # Collect facial embedding
        def video_callback_func(frame):
            img = frame.to_ndarray(format="bgr24")
            reg_img, embedding = registration_form.get_embedding(img)

            if embedding is not None:
                with open('face_embedding.txt', mode='ab') as f:
                    face_utils.np.savetxt(f,embedding)

            return av.VideoFrame.from_ndarray(reg_img, format="bgr24")

        webrtc_streamer(key="registration", 
                        video_frame_callback=video_callback_func,
                        rtc_configuration={
                            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
                            }
                        )    

        # Save the data in redis database 
        if st.button('Submit'):
            if not all([file_number, first_name, last_name]):
                st.error("Please fill all required fields (marked with *)")
            else:
                return_val = registration_form.save_data_in_redis_db(
                    file_number=file_number, 
                    first_name=first_name, 
                    last_name=last_name, 
                    role=role,
                    zone=zone  # Added zone parameter
                )
                        
                if return_val is True:
                    st.success(f"Successfully registered {first_name} {last_name} ({file_number}) in {zone}")
                    st.balloons()
                elif return_val == 'false file number':
                    st.error('Invalid file number format')
                elif return_val == 'false first_name':
                    st.error('Invalid first name format')
                elif return_val == 'No face_embedding.txt':
                    st.error('Face embedding not found. Please try capturing your face again.')
                else:
                    st.error(f"Registration failed: {return_val}")

    if __name__ == "__main__":
        main()