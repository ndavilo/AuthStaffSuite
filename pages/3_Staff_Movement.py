from utils.config import configure_app
configure_app()
import streamlit as st
from streamlit_webrtc import webrtc_streamer
import av
import sys
import os
sys.path.append(os.path.dirname(__file__))
import face_utils

st.subheader('Staff Movement System')

# Apply custom styling
from styles import LAGOS_STYLE, get_topbar_style, get_topbar_html

# Apply styling and top bar
st.markdown(LAGOS_STYLE, unsafe_allow_html=True)
st.markdown(get_topbar_style(), unsafe_allow_html=True)
st.markdown(get_topbar_html(), unsafe_allow_html=True)

# Import check requirements after initial Streamlit setup
import check_requirements

def main():
    # Network verification first
    access_granted, reason = check_requirements.ip_address_range_verification()
    
    if not access_granted:
        st.error(f"Access Denied: Invalid {reason}")
        st.stop()
        
    # Rest of your app content would go here
    
    # Initialize StaffMovement
    staff_movement = face_utils.StaffMovement()

    # Form layout
    col1, col2 = st.columns(2)

    with col1:
        # Movement type selection
        movement_type = st.radio(
            "Movement Type:",
            options=["Clock_In", "Clock_Out"],
            horizontal=True
        )
        
        purpose = st.selectbox(
            "Purpose of Movement:",
            ["Official Duty", "Meeting", "Break", "Personal", "Other"]
        )
        
        location = st.text_input("Location:", placeholder="Where are you going?")

    with col2:
        # Conditional fields based on movement type
        if movement_type == "Clock_Out":
            note = st.text_area("Note:", placeholder="Reason for leaving")
        else:
            note = st.text_area("Return Note:", placeholder="Any updates after returning")

    # Face verification
    def video_callback_func(frame):
        img = frame.to_ndarray(format="bgr24")
        reg_img = staff_movement.get_embedding(img)
        return av.VideoFrame.from_ndarray(reg_img, format="bgr24")

    webrtc_streamer(
        key="movement_verification",
        video_frame_callback=video_callback_func,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
    )

    # Submit button
    if st.button('Submit Movement'):
        # Validate required fields
        if not all([purpose, location]):
            st.error("Please fill all required fields")
        else:
            result = staff_movement.save_movement_data(
                movement_type,
                purpose,
                location,
                note
            )
            
            if result is True:
                st.success("Movement logged successfully!")
                st.balloons()
            elif result == 'No face embedding found':
                st.error("Face verification failed. Please ensure your face is visible.")
            elif result == 'Verification failed - Unknown staff':
                st.error("""
                Verification failed - Staff not recognized. Please:
                1. Try again with proper face alignment, or
                2. Visit ICT department for assistance
                """)


if __name__ == "__main__":
    main()
