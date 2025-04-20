from utils.config import configure_app
configure_app()
import streamlit as st
import pandas as pd
import redis
import csv
from io import StringIO
from datetime import datetime
import face_utils
from auth import authenticator

st.subheader('Staff Movement Records')

# Apply custom styling
from styles import LAGOS_STYLE, get_topbar_style, get_topbar_html

# Apply styling and top bar
st.markdown(LAGOS_STYLE, unsafe_allow_html=True)
st.markdown(get_topbar_style(), unsafe_allow_html=True)
st.markdown(get_topbar_html(), unsafe_allow_html=True)

# Authentication check
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None

if not st.session_state.authentication_status:
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

    # Connect to Redis Client
    r = face_utils.r

    def main():
        # Network verification first
        access_granted, reason = check_requirements.ip_address_range_verification()
        
        if not access_granted:
            st.error(f"Access Denied: Invalid {reason}")
            st.stop()
            
        # Rest of your app content would go here
        
        def load_movement_logs():
            """Load all movement logs from Redis"""
            logs_list = r.lrange('staff:movement:logs', 0, -1)
            records = []
            
            for log in logs_list:
                if isinstance(log, bytes):
                    log = log.decode('utf-8')
                
                parts = log.split('@')
                if len(parts) == 7:
                    name, role, timestamp, movement_type, purpose, location, note = parts
                    records.append({
                        'Name': name,
                        'Role': role,
                        'Timestamp': timestamp,
                        'Movement Type': movement_type,
                        'Purpose': purpose,
                        'Location': location,
                        'Note': note
                    })
            
            return pd.DataFrame(records)

        def clear_movement_logs():
            """Clear all movement logs from Redis"""
            r.delete('staff:movement:logs')
            st.success("All movement records have been cleared!")

        def convert_df_to_csv(df):
            """Convert DataFrame to CSV string"""
            output = StringIO()
            df.to_csv(output, index=False)
            return output.getvalue()

        # Load movement data
        movement_df = load_movement_logs()

        if not movement_df.empty:
            # Convert timestamp to datetime and sort
            movement_df['Timestamp'] = pd.to_datetime(movement_df['Timestamp'])
            movement_df.sort_values('Timestamp', ascending=False, inplace=True)
            
            # Display filters
            col1, col2, col3 = st.columns(3)
            
            with col1:
                name_filter = st.selectbox(
                    'Filter by Name',
                    ['All'] + sorted(movement_df['Name'].unique().tolist())
                )
            
            with col2:
                movement_filter = st.selectbox(
                    'Filter by Movement Type',
                    ['All'] + sorted(movement_df['Movement Type'].unique().tolist())
                )
            
            with col3:
                date_filter = st.selectbox(
                    'Filter by Date',
                    ['All'] + sorted(movement_df['Timestamp'].dt.date.unique().astype(str).tolist())
                )
            
            # Apply filters
            if name_filter != 'All':
                movement_df = movement_df[movement_df['Name'] == name_filter]
            
            if movement_filter != 'All':
                movement_df = movement_df[movement_df['Movement Type'] == movement_filter]
            
            if date_filter != 'All':
                movement_df = movement_df[movement_df['Timestamp'].dt.date.astype(str) == date_filter]
            
            # Display the filtered DataFrame
            st.dataframe(movement_df.style.format({'Timestamp': lambda x: x.strftime('%Y-%m-%d %H:%M:%S')}))
            
            # Download and Clear buttons
            col1, col2 = st.columns(2)
            
            with col1:
                csv_data = convert_df_to_csv(movement_df)
                st.download_button(
                    label="Download as CSV",
                    data=csv_data,
                    file_name=f"staff_movement_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime='text/csv'
                )
            
            with col2:
                if st.button('Clear All Records', type="primary"):
                    clear_movement_logs()
                    st.experimental_rerun()
        else:
            st.info("No movement records found in the database")


    if __name__ == "__main__":
        main()
