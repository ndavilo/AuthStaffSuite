from utils.config import configure_app
configure_app()
import streamlit as st
import face_utils
import pandas as pd
import numpy as np
from streamlit_modal import Modal
from auth import authenticator

from utils.session import init_auth_session_keys
init_auth_session_keys()

st.subheader('Staff List')

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


    # Initialize Redis connection
    r = face_utils.r
    REDIS_KEY = 'staff:register'

    def main():
        # Network verification first
        access_granted, reason = check_requirements.ip_address_range_verification()
        
        if not access_granted:
            st.error(f"Access Denied: Invalid {reason}")
            st.stop()
            
        def get_full_staff_data():
            """Retrieve complete staff data from Redis including facial features"""
            with st.spinner('Retrieving Data from Database...'):
                return face_utils.retrive_data(name=REDIS_KEY)

        def get_display_data(full_df):
            """Extract only display columns from full data"""
            return full_df[['File No. Name', 'Role', 'Zone']].copy()

        # Initialize session state
        if 'full_staff_df' not in st.session_state:
            st.session_state.full_staff_df = get_full_staff_data()
        if 'display_df' not in st.session_state:
            st.session_state.display_df = get_display_data(st.session_state.full_staff_df)

        # Add filter for Zone
        all_zones = ['All Zones'] + sorted(st.session_state.full_staff_df['Zone'].unique().tolist())
        selected_zone = st.selectbox('Filter by Zone:', all_zones)

        # Filter data by selected zone
        if selected_zone != 'All Zones':
            filtered_df = st.session_state.display_df[st.session_state.display_df['Zone'] == selected_zone].copy()
        else:
            filtered_df = st.session_state.display_df.copy()

        # Add delete checkboxes
        filtered_df['Delete'] = False

        # Display editable dataframe with checkboxes
        edited_df = st.data_editor(
            filtered_df,
            column_config={
                "Delete": st.column_config.CheckboxColumn(
                    "Select to delete",
                    help="Check to delete staff member",
                    default=False,
                )
            },
            disabled=["File No. Name", "Role", "Zone"],
            hide_index=True,
            use_container_width=True
        )

        # Get selected staff for deletion
        to_delete = edited_df[edited_df['Delete']]['File No. Name'].tolist()

        # Confirmation modal for individual deletions
        if len(to_delete) > 0:
            delete_modal = Modal(
                "Confirm Deletion", 
                key="delete_modal",
                padding=20,
                max_width=500
            )
            
            with delete_modal.container():
                st.warning(f"Are you sure you want to delete {len(to_delete)} staff member(s)?")
                st.write("Selected staff:")
                for staff in to_delete:
                    # Get the full record to include role and zone in deletion key
                    full_record = st.session_state.full_staff_df[
                        st.session_state.full_staff_df['File No. Name'] == staff
                    ].iloc[0]
                    st.write(f"- {staff} (Role: {full_record['Role']}, Zone: {full_record['Zone']})")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Confirm Delete", key="confirm_delete"):
                        success_count = 0
                        for staff in to_delete:
                            # Get the full record to construct the correct Redis key
                            full_record = st.session_state.full_staff_df[
                                st.session_state.full_staff_df['File No. Name'] == staff
                            ].iloc[0]
                            redis_key = f"{staff}@{full_record['Role']}@{full_record['Zone']}"
                            if r.hdel(REDIS_KEY, redis_key):
                                success_count += 1
                        
                        if success_count > 0:
                            st.success(f"Deleted {success_count} staff member(s)")
                            st.session_state.full_staff_df = get_full_staff_data()
                            st.session_state.display_df = get_display_data(st.session_state.full_staff_df)
                            st.rerun()
                        delete_modal.close()
                        
                with col2:
                    if st.button("❌ Cancel", key="cancel_delete"):
                        delete_modal.close()

        # Action buttons row
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔄 Refresh Staff List"):
                st.session_state.full_staff_df = get_full_staff_data()
                st.session_state.display_df = get_display_data(st.session_state.full_staff_df)
                st.rerun()

        with col2:
            # Download CSV with all data (including facial features)
            if not st.session_state.full_staff_df.empty:
                csv_data = st.session_state.full_staff_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv_data,
                    file_name="staff_registry_backup.csv",
                    mime="text/csv",
                    help="Download complete staff data including facial features"
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
                    st.error("⚠️ This will delete ALL staff data!")
                    st.write("Are you sure you want to continue?")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Confirm", type="primary"):
                            r.delete(REDIS_KEY)
                            st.success("Database cleared!")
                            st.session_state.full_staff_df = pd.DataFrame(columns=['File No. Name', 'Role', 'Zone', 'Facial_features'])
                            st.session_state.display_df = pd.DataFrame(columns=['File No. Name', 'Role', 'Zone'])
                            st.rerun()
                            clear_modal.close()
                    with col2:
                        if st.button("❌ Cancel", type="secondary"):
                            clear_modal.close()

        # Display status
        if filtered_df.empty:
            st.info("No staff members found" + (f" in {selected_zone}" if selected_zone != 'All Zones' else ""))
        else:
            st.success(f"Showing {len(filtered_df)} staff members" + (f" in {selected_zone}" if selected_zone != 'All Zones' else ""))


    if __name__ == "__main__":
        main()