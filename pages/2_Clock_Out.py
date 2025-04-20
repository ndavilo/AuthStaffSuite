from utils.config import configure_app
configure_app()
import streamlit as st
from streamlit_webrtc import webrtc_streamer
import av
import time
import cv2

st.subheader('Clock-Out')

# Apply custom styling
from styles import LAGOS_STYLE, get_topbar_style, get_topbar_html

# Apply styling and top bar
st.markdown(LAGOS_STYLE, unsafe_allow_html=True)
st.markdown(get_topbar_style(), unsafe_allow_html=True)
st.markdown(get_topbar_html(), unsafe_allow_html=True)

# Import check requirements after initial Streamlit setup
import check_requirements

# Network verification first
access_granted, reason = check_requirements.ip_address_range_verification()
    
if not access_granted:
    st.error(f"Access Denied: Invalid {reason}")
    st.stop()
    
# Retrieve the data from Redis Database
with st.spinner('Retrieving Data from Database ...'):
    import face_utils
    redis_face_db = face_utils.retrive_data(name='staff:register')

waitTime = 10  # time in sec
setTime = time.time()
realtimepred = face_utils.RealTimePrediction()
last_action_status = None

def video_frame_callback(frame):
    global setTime, last_action_status

    img = frame.to_ndarray(format="bgr24")
    pred_img = realtimepred.face_prediction(
        img,
        redis_face_db,
        'Facial_features',
        ['File No. Name', 'Role', 'Zone'],  # Added Zone to name_role
        thresh=0.5
    )

    timenow = time.time()
    difftime = timenow - setTime

    if difftime >= waitTime:
        # Check if action is allowed before saving
        if any(realtimepred.logs['name']):
            name = realtimepred.logs['name'][0]
            if realtimepred.check_last_action(name, 'Clock_Out'):
                realtimepred.saveLogs_redis(Clock_In_Out='Clock_Out')
                last_action_status = "✔️ Clock-Out recorded"
            else:
                last_action_status = "❌ Already clocked-out today"
        setTime = time.time()

    # Add status text to the frame if available
    if last_action_status:
        cv2.putText(pred_img, last_action_status, (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    return av.VideoFrame.from_ndarray(pred_img, format="bgr24")

webrtc_streamer(key="realtimePrediction", video_frame_callback=video_frame_callback,
rtc_configuration={
        "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
    }
)