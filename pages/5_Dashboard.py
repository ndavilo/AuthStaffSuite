from utils.config import configure_app
configure_app()

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import face_utils
import redis
from auth import authenticator
from utils.session import init_auth_session_keys

init_auth_session_keys()

# Set page config
st.subheader('Attendance Visualization Dashboard')

# Apply custom styling
from styles import LAGOS_STYLE, get_topbar_style, get_topbar_html
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
    authenticator.logout('Logout', 'sidebar')
    st.write(f'Welcome *{st.session_state["name"]}*')

    # Redis connection
    r = face_utils.r

    def load_data_from_redis():
        """Load and process attendance data from Redis"""
        name = 'attendance:logs'
        logs = face_utils.load_logs(name=name)

        cleaned_logs = []
        for log in logs:
            if isinstance(log, bytes):
                log = log.decode('utf-8')
            log = log.strip("b'")
            parts = log.split('@')
            if len(parts) == 4:
                file_name_role, role, timestamp, Clock_In_Out = parts
                file_no, name = file_name_role.split('.', 1)

                # Normalize Clock_In_Out values (important!)
                Clock_In_Out = Clock_In_Out.strip().replace("-", "_").title()

                cleaned_logs.append({
                    'File No.': file_no,
                    'Name': name,
                    'Role': role,
                    'Timestamp': timestamp,
                    'Clock_In_Out': Clock_In_Out
                })

        if not cleaned_logs:
            return pd.DataFrame()

        df = pd.DataFrame(cleaned_logs)
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        df['Date'] = df['Timestamp'].dt.date
        df['Time'] = df['Timestamp'].dt.time
        df['Hour'] = df['Timestamp'].dt.hour
        df['Day'] = df['Timestamp'].dt.day_name()
        return df

    with st.spinner('Loading attendance data from Redis...'):
        df = load_data_from_redis()

    if df.empty:
        st.warning("No attendance data found in Redis database")
        st.stop()

    # Debug: Show unique Clock_In_Out values
    st.write("🔍 Clock_In_Out values in dataset:", df['Clock_In_Out'].unique())

    # Sidebar filters
    st.sidebar.header('Filter Options')
    selected_roles = st.sidebar.multiselect(
        'Select Roles',
        options=df['Role'].unique(),
        default=df['Role'].unique()
    )

    date_range = st.sidebar.date_input(
        'Select Date Range',
        value=[df['Date'].min(), df['Date'].max()],
        min_value=df['Date'].min(),
        max_value=df['Date'].max()
    )

    # Filter data
    filtered_df = df[
        (df['Role'].isin(selected_roles)) &
        (df['Date'] >= date_range[0]) &
        (df['Date'] <= date_range[1])
    ]

    st.write(f"Displaying data from {date_range[0]} to {date_range[1]}")

    # KPI cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Records", len(filtered_df))
    with col2:
        st.metric("Unique Employees", filtered_df['Name'].nunique())
    with col3:
        st.metric("Date Range", f"{filtered_df['Date'].min()} to {filtered_df['Date'].max()}")

    # Main charts
    tab1, tab2, tab3 = st.tabs(["Daily Activity", "Employee Patterns", "Hourly Trends"])

    with tab1:
        st.subheader("Daily Attendance Activity")
        if not filtered_df.empty:
            daily_counts = filtered_df.groupby(['Date', 'Clock_In_Out']).size().unstack(fill_value=0)

            fig, ax = plt.subplots(figsize=(10, 6))
            daily_counts.plot(kind='bar', stacked=True, ax=ax)
            plt.title('Daily Clock-Ins and Clock-Outs')
            plt.xlabel('Date')
            plt.ylabel('Count')
            plt.xticks(rotation=45)
            st.pyplot(fig)

            st.subheader("Activity by Day of Week")
            day_counts = filtered_df.groupby(['Day', 'Clock_In_Out']).size().unstack(fill_value=0)
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_counts = day_counts.reindex(day_order)

            fig, ax = plt.subplots(figsize=(10, 4))
            day_counts.plot(kind='bar', stacked=True, ax=ax)
            plt.title('Activity by Day of Week')
            plt.xlabel('Day')
            plt.ylabel('Count')
            plt.xticks(rotation=45)
            st.pyplot(fig)
        else:
            st.warning("No data available for selected filters")

    with tab2:
        st.subheader("Employee Activity Patterns")
        if not filtered_df.empty:
            emp_activity = filtered_df.groupby(['Name', 'Clock_In_Out']).size().unstack(fill_value=0)

            # Ensure expected columns exist
            for col in ['Clock_In', 'Clock_Out']:
                if col not in emp_activity.columns:
                    emp_activity[col] = 0

            emp_activity['Total'] = emp_activity[['Clock_In', 'Clock_Out']].sum(axis=1)
            emp_activity = emp_activity.sort_values('Total', ascending=False)

            fig, ax = plt.subplots(figsize=(10, 6))
            emp_activity[['Clock_In', 'Clock_Out']].plot(kind='bar', stacked=True, ax=ax)
            plt.title('Employee Activity Count')
            plt.xlabel('Employee')
            plt.ylabel('Count')
            plt.xticks(rotation=45)
            st.pyplot(fig)

            st.subheader("Employee Daily Presence")
            emp_presence = filtered_df.groupby(['Name', 'Date']).size().unstack(fill_value=0)

            fig, ax = plt.subplots(figsize=(12, 6))
            sns.heatmap(emp_presence, cmap='Blues', ax=ax)
            plt.title('Employee Daily Presence (Darker = More Activity)')
            plt.xlabel('Date')
            plt.ylabel('Employee')
            st.pyplot(fig)
        else:
            st.warning("No data available for selected filters")

    with tab3:
        st.subheader("Hourly Activity Trends")
        if not filtered_df.empty:
            hourly_dist = filtered_df.groupby(['Hour', 'Clock_In_Out']).size().unstack(fill_value=0)

            fig, ax = plt.subplots(figsize=(10, 4))
            hourly_dist.plot(kind='area', stacked=True, ax=ax)
            plt.title('Hourly Activity Distribution')
            plt.xlabel('Hour of Day')
            plt.ylabel('Count')
            plt.xticks(range(24))
            st.pyplot(fig)

            st.subheader("Role-Specific Hourly Patterns")
            role_hourly = filtered_df.groupby(['Role', 'Hour']).size().unstack(fill_value=0)

            fig, ax = plt.subplots(figsize=(12, 6))
            sns.heatmap(role_hourly, cmap='YlOrRd', ax=ax)
            plt.title('Role Activity by Hour (Darker = More Activity)')
            plt.xlabel('Hour of Day')
            plt.ylabel('Role')
            st.pyplot(fig)
        else:
            st.warning("No data available for selected filters")

    # Refresh button
    if st.button('Refresh Data'):
        st.experimental_rerun()
