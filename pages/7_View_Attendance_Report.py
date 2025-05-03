from utils.config import configure_app
configure_app()
import streamlit as st
import face_utils
import pandas as pd
import redis
from auth import authenticator
from streamlit_modal import Modal

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
    REDIS_KEY = 'attendance:logs'

    def main():
        # Network verification first
        access_granted, reason = check_requirements.ip_address_range_verification()
        
        if not access_granted:
            st.error(f"Access Denied: Invalid {reason}")
            st.stop()
            
        def get_full_attendance_data():
            """Retrieve complete attendance data from Redis"""
            with st.spinner('Retrieving Data from Database ...'):
                logs = face_utils.load_logs(name=REDIS_KEY)
                
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
                                'Clock_In_Out': Clock_In_Out,
                                'Redis_Key': log  # Store the original Redis key for deletion
                            })
                        except:
                            continue

                if cleaned_logs:
                    df = pd.DataFrame(cleaned_logs)
                    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                    return df
                return pd.DataFrame()

        # Initialize session state
        if 'attendance_df' not in st.session_state:
            st.session_state.attendance_df = get_full_attendance_data()

        # Create filter controls
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            # Date range filter
            min_date = None
            max_date = None
            if not st.session_state.attendance_df.empty:
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
            if not st.session_state.attendance_df.empty:
                if 'Zone' in st.session_state.attendance_df.columns:
                    all_zones.extend(sorted(st.session_state.attendance_df['Zone'].unique().tolist()))
            
            selected_zone = st.selectbox('Filter by Zone', all_zones)

        # Apply filters to the data
        filtered_df = st.session_state.attendance_df.copy()
        if date_range and len(date_range) == 2:
            filtered_df = filtered_df[
                (filtered_df['Timestamp'].dt.date >= date_range[0]) & 
                (filtered_df['Timestamp'].dt.date <= date_range[1])
            ]
        if selected_zone != 'All Zones':
            filtered_df = filtered_df[filtered_df['Zone'] == selected_zone]

        # Add delete checkboxes if there's data
        if not filtered_df.empty:
            filtered_df['Delete'] = False

            # Display editable dataframe with checkboxes
            edited_df = st.data_editor(
                filtered_df.drop(columns=['Redis_Key']),  # Don't show Redis key to users
                column_config={
                    "Delete": st.column_config.CheckboxColumn(
                        "Select to delete",
                        help="Check to delete attendance record",
                        default=False,
                    )
                },
                disabled=["File No.", "Name", "Role", "Zone", "Timestamp", "Clock_In_Out"],
                hide_index=True,
                use_container_width=True
            )

            # Get selected records for deletion
            to_delete = filtered_df[edited_df['Delete']]['Redis_Key'].tolist()

            # Confirmation modal for individual deletions
            if len(to_delete) > 0:
                delete_modal = Modal(
                    "Confirm Deletion", 
                    key="delete_modal",
                    padding=20,
                    max_width=500
                )
                
                with delete_modal.container():
                    st.warning(f"Are you sure you want to delete {len(to_delete)} attendance record(s)?")
                    st.write("Selected records:")
                    for record_key in to_delete:
                        parts = record_key.split('@')
                        st.write(f"- {parts[0]} (Time: {parts[2]}, Action: {parts[3]})")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Confirm Delete", key="confirm_delete"):
                            success_count = 0
                            for record_key in to_delete:
                                if r.lrem(REDIS_KEY, 0, record_key):  # Remove all matching entries
                                    success_count += 1
                            
                            if success_count > 0:
                                st.success(f"Deleted {success_count} attendance record(s)")
                                st.session_state.attendance_df = get_full_attendance_data()
                                st.rerun()
                            delete_modal.close()
                            
                    with col2:
                        if st.button("❌ Cancel", key="cancel_delete"):
                            delete_modal.close()

        # Action buttons row
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔄 Refresh Logs"):
                st.session_state.attendance_df = get_full_attendance_data()
                st.rerun()

        with col2:
            # Download CSV with filtered data
            if not filtered_df.empty:
                csv_data = filtered_df.drop(columns=['Redis_Key', 'Delete']).to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv_data,
                    file_name="attendance_logs.csv",
                    mime="text/csv",
                    help="Download filtered attendance data"
                )
            else:
                st.button("📥 Download as CSV", disabled=True)

        with col3:
            if st.button("🧹 Clear Database", type="primary"):
                clear_modal = Modal(
                    "Confirm Clearance",
                    key="clear_modal",
                    padding=20,
                    max_width=500
                )
                
                with clear_modal.container():
                    st.error("⚠️ This will delete ALL attendance logs!")
                    st.write("Are you sure you want to continue?")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Confirm", type="primary"):
                            r.delete(REDIS_KEY)
                            st.success("Attendance logs cleared!")
                            st.session_state.attendance_df = pd.DataFrame()
                            st.rerun()
                            clear_modal.close()
                    with col2:
                        if st.button("❌ Cancel", type="secondary"):
                            clear_modal.close()

        # Display status
        if filtered_df.empty:
            st.info("No attendance records found" + 
                   (f" in {selected_zone}" if selected_zone != 'All Zones' else "") + 
                   (f" between {date_range[0]} and {date_range[1]}" if date_range and len(date_range) == 2 else ""))
        else:
            st.success(f"Showing {len(filtered_df)} attendance records" + 
                      (f" in {selected_zone}" if selected_zone != 'All Zones' else "") + 
                      (f" between {date_range[0]} and {date_range[1]}" if date_range and len(date_range) == 2 else ""))

        # Show summary statistics if data exists
        if not filtered_df.empty:
            st.subheader("Summary Statistics")
            col_sum1, col_sum2, col_sum3 = st.columns(3)
            with col_sum1:
                st.metric("Total Records", len(filtered_df))
            with col_sum2:
                st.metric("Unique Employees", filtered_df['Name'].nunique())
            with col_sum3:
                st.metric("Zones Represented", filtered_df['Zone'].nunique())

    if __name__ == "__main__":
        main()