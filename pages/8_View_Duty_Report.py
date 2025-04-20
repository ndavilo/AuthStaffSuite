from utils.config import configure_app
configure_app()
import streamlit as st
import pandas as pd
import redis
from datetime import datetime
import face_utils
from auth import authenticator

# Set page config
st.subheader('Duty Report Records')

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

    # Connect to Redis
    r = face_utils.r

    def load_duty_reports():
        """Load all duty reports from Redis"""
        reports = []
        for key in r.scan_iter("duty_report:*"):
            report_data = r.hgetall(key)
            decoded_report = {k.decode('utf-8'): v.decode('utf-8') for k, v in report_data.items()}
            reports.append(decoded_report)
        return pd.DataFrame(reports)

    def clear_duty_reports():
        """Clear all duty reports from Redis"""
        for key in r.scan_iter("duty_report:*"):
            r.delete(key)
        st.success("All duty reports have been cleared!")

    def convert_to_csv(df):
        """Convert DataFrame to CSV"""
        return df.to_csv(index=False).encode('utf-8')

    # Main function
    def main():
        # Network verification first
        import check_requirements
        access_granted, reason = check_requirements.ip_address_range_verification()
        if not access_granted:
            st.error(f"Access Denied: Invalid {reason}")
            st.stop()

        # Load data
        with st.spinner('Loading duty reports...'):
            reports_df = load_duty_reports()

        if not reports_df.empty:
            # Convert timestamp and sort
            reports_df['timestamp'] = pd.to_datetime(reports_df['timestamp'])
            reports_df.sort_values('timestamp', ascending=False, inplace=True)

            # Filters
            col1, col2, col3 = st.columns(3)
            with col1:
                role_filter = st.selectbox(
                    'Filter by Officer Role',
                    ['All'] + sorted(reports_df['officer_role'].unique())
                )
            with col2:
                shift_filter = st.selectbox(
                    'Filter by Duty Shift',
                    ['All'] + sorted(reports_df['duty_type'].unique())
                )
            with col3:
                date_filter = st.selectbox(
                    'Filter by Date',
                    ['All'] + sorted(reports_df['timestamp'].dt.date.astype(str).unique())
                )

            # Apply filters
            if role_filter != 'All':
                reports_df = reports_df[reports_df['officer_role'] == role_filter]
            if shift_filter != 'All':
                reports_df = reports_df[reports_df['duty_type'] == shift_filter]
            if date_filter != 'All':
                reports_df = reports_df[reports_df['timestamp'].dt.date.astype(str) == date_filter]

            # Display reports
            st.dataframe(
                reports_df.style.format({'timestamp': lambda x: x.strftime('%Y-%m-%d %H:%M:%S')}),
                height=600
            )

            # Download and management
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="Download as CSV",
                    data=convert_to_csv(reports_df),
                    file_name=f"duty_reports_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime='text/csv'
                )
            with col2:
                if st.button('Clear All Reports', type="primary"):
                    clear_duty_reports()
                    st.experimental_rerun()
        else:
            st.info("No duty reports found in the system")

    if __name__ == "__main__":
        main()