from utils.config import configure_app
configure_app()
import streamlit as st
import face_utils
import pandas as pd
import redis
from auth import authenticator

from utils.session import init_auth_session_keys
init_auth_session_keys()

# Set page config
st.subheader('Attendance Report')

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

    # Redis connection
    r = face_utils.r

    def main():
        # Network verification first
        access_granted, reason = check_requirements.ip_address_range_verification()
        
        if not access_granted:
            st.error(f"Access Denied: Invalid {reason}")
            st.stop()
            
        # Retrieve the data from Redis Database
        name = 'attendance:logs'

        # Create filter controls
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            # Date range filter
            min_date = None
            max_date = None
            if 'attendance_df' in st.session_state and st.session_state.attendance_df is not None:
                st.session_state.attendance_df['Timestamp'] = pd.to_datetime(st.session_state.attendance_df['Timestamp'])
                min_date = st.session_state.attendance_df['Timestamp'].min().date()
                max_date = st.session_state.attendance_df['Timestamp'].max().date()
            
            date_range = st.date_input(
                'Filter by Date Range',
                value=[min_date, max_date] if min_date and max_date else None,
                min_value=min_date,
                max_value=max_date
            )
        
        with col_filter2:
            # Zone filter
            all_zones = ['All Zones']
            if 'attendance_df' in st.session_state and st.session_state.attendance_df is not None:
                if 'Zone' in st.session_state.attendance_df.columns:
                    all_zones.extend(sorted(st.session_state.attendance_df['Zone'].unique().tolist()))
            
            selected_zone = st.selectbox('Filter by Zone', all_zones)

        # Create a single row for all buttons
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button('Refresh Logs'):
                with st.spinner('Retrieving Data from Database ...'):
                    logs = face_utils.load_logs(name=name)
                    
                    # Decode and process the logs
                    cleaned_logs = []
                    for log in logs:
                        if isinstance(log, bytes):
                            log = log.decode('utf-8')
                        log = log.strip("b'")
                        parts = log.split('@')
                        if len(parts) >= 4:  # Updated to handle logs with zone information
                            file_name_role = parts[0]
                            role = parts[1]
                            timestamp = parts[2]
                            Clock_In_Out = parts[3]
                            zone = parts[4] if len(parts) > 4 else 'Lagos Zone 2'  # Default zone if not specified
                            
                            try:
                                file_no, name = file_name_role.split('.', 1)
                                cleaned_logs.append({
                                    'File No.': file_no,
                                    'Name': name,
                                    'Role': role,
                                    'Zone': zone,
                                    'Timestamp': timestamp,
                                    'Clock_In_Out': Clock_In_Out
                                })
                            except:
                                continue

                    if cleaned_logs:
                        df = pd.DataFrame(cleaned_logs)
                        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                        st.session_state.attendance_df = df
                        st.session_state.download_ready = True
                    else:
                        st.warning("No attendance logs found")
                        st.session_state.download_ready = False
                        st.session_state.attendance_df = None

        # Download and Clear buttons
        if 'download_ready' in st.session_state and st.session_state.download_ready:
            with col2:
                # Apply filters before download
                filtered_df = st.session_state.attendance_df.copy()
                if date_range and len(date_range) == 2:
                    filtered_df = filtered_df[
                        (filtered_df['Timestamp'].dt.date >= date_range[0]) & 
                        (filtered_df['Timestamp'].dt.date <= date_range[1])
                    ]
                if selected_zone != 'All Zones':
                    filtered_df = filtered_df[filtered_df['Zone'] == selected_zone]
                
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name="attendance_logs.csv",
                    mime='text/csv',
                    key='download_csv'
                )
            
            with col3:
                if st.button('Clear All Logs', key='clear_logs'):
                    r.delete(name)
                    st.session_state.attendance_df = None
                    st.session_state.download_ready = False
                    st.success("All attendance logs have been cleared!")
                    st.rerun()

        # Display the DataFrame if available
        if 'attendance_df' in st.session_state and st.session_state.attendance_df is not None:
            # Apply filters to displayed data
            display_df = st.session_state.attendance_df.copy()
            if date_range and len(date_range) == 2:
                display_df = display_df[
                    (display_df['Timestamp'].dt.date >= date_range[0]) & 
                    (display_df['Timestamp'].dt.date <= date_range[1])
                ]
            if selected_zone != 'All Zones':
                display_df = display_df[display_df['Zone'] == selected_zone]
            
            st.dataframe(display_df)
            
            # Show summary statistics
            st.subheader("Summary Statistics")
            col_sum1, col_sum2, col_sum3 = st.columns(3)
            with col_sum1:
                st.metric("Total Records", len(display_df))
            with col_sum2:
                st.metric("Unique Employees", display_df['Name'].nunique())
            with col_sum3:
                st.metric("Zones Represented", display_df['Zone'].nunique())
                
        elif 'attendance_df' in st.session_state and st.session_state.attendance_df is None:
            st.info("No attendance records available. Please refresh or check Redis connection.")

    if __name__ == "__main__":
        main()