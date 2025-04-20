from utils.config import configure_app
configure_app()
import streamlit as st
from streamlit_webrtc import webrtc_streamer
import av
import sys
import os
sys.path.append(os.path.dirname(__file__))
import face_utils
from datetime import datetime

st.subheader('Staff Duty Reporting System')

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
    
    # Initialize StaffDutyReport
    duty_report = face_utils.StaffDutyReport()

    # Form layout
    col1, col2 = st.columns(2)
    
    with col1:
        # Officer role selection
        officer_role = st.selectbox(
            "Your Role:",
            options=["CRO", "Incident Duty Officer", "Visiting Rounds Senior Officer"],
            index=0
        )
        
        # Duty information
        duty_type = st.radio(
            "Duty Shift:",
            options=["Morning (06:00-18:00)", "Night (18:00-06:00)"],
            index=0 if datetime.now().hour >= 6 and datetime.now().hour < 18 else 1
        )
        
        # Staff lists as text areas
        st.subheader("Staff Locations")
        cell_officers = st.text_area(
            "Officers at Cells (one per line):",
            height=100,
            placeholder="Enter names of officers at cells\nOne name per line"
        )
        
        gate_officers = st.text_area(
            "Officers at Main Gate (one per line):",
            height=100,
            placeholder="Enter names of officers at main gate\nOne name per line"
        )
    
    with col2:
        standby_officers = st.text_area(
            "Officers on Standby Duty (one per line):",
            height=100,
            placeholder="Enter names of standby officers\nOne name per line"
        )
        
        other_officers = st.text_area(
            "Other Locations (one per line):",
            height=100,
            placeholder="Enter names of officers at other locations\nOne name per line"
        )
        
        # Report details
        st.subheader("Report Details")
        comments = st.text_area("General Comments:", height=100)
        challenges = st.text_area("Challenges Encountered:", height=100)
        observations = st.text_area("Key Observations:", height=100)
    
    # Face verification (always visible below form)
    st.subheader("Face Verification for Submission")
    
    def video_callback_func(frame):
        img = frame.to_ndarray(format="bgr24")
        reg_img = duty_report.get_embedding(img)
        return av.VideoFrame.from_ndarray(reg_img, format="bgr24")
    
    webrtc_streamer(
        key="duty_report_verification",
        video_frame_callback=video_callback_func,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
    )
    
    # Submit button
    if st.button('Submit Duty Report'):
        # Process text areas into lists
        def process_names(text):
            return [name.strip() for name in text.split('\n') if name.strip()]
        
        report_data = {
            'officer_role': officer_role,
            'duty_type': duty_type,
            'cell_officers': '\n'.join(process_names(cell_officers)),
            'gate_officers': '\n'.join(process_names(gate_officers)),
            'standby_officers': '\n'.join(process_names(standby_officers)),
            'other_officers': '\n'.join(process_names(other_officers)),
            'comments': comments,
            'challenges': challenges,
            'observations': observations
        }
        
        # Validate at least one officer is listed
        if not any([cell_officers, gate_officers, standby_officers, other_officers]):
            st.error("Please list officers in at least one location")
        else:
            result = duty_report.save_duty_report(report_data)
            
            if result is True:
                st.success("Duty report submitted successfully!")
                st.balloons()
            elif result == 'No face verification found':
                st.error("Face verification failed. Please ensure your face is visible.")
            elif result == 'Verification failed - Unknown staff':
                st.error("""
                Verification failed - Staff not recognized. Please:
                1. Try again with proper face alignment, or
                2. Visit ICT department for assistance
                """)

if __name__ == "__main__":
    main()