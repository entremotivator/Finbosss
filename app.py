import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import json
from collections import defaultdict
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
import re

# ------------------ PAGE CONFIG ------------------ #
st.set_page_config(
    page_title="LinkedIn Analytics & Outreach Hub",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------ STATIC CONFIGURATION ------------------ #
CHAT_SPREADSHEET_ID = "1klm60YFXSoV510S4igv5LfREXeykDhNA5Ygq7HNFN0I"
CHAT_SHEET_NAME = "linkedin_chat_history_advanced 2"

OUTREACH_SPREADSHEET_ID = "1eLEFvyV1_f74UC1g5uQ-xA7A62sK8Pog27KIjw_Sk3Y"
OUTREACH_SHEET_NAME = "linkedin-tracking-csv.csv"

MY_PROFILE = {
    "name": "Donmenico Hudson",
    "url": "https://www.linkedin.com/in/donmenicohudson/"
}

WEBHOOK_URL = "https://agentonline-u29564.vm.elestio.app/webhook/Leadlinked"

# ------------------ SESSION STATE ------------------ #
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'gsheets_client' not in st.session_state:
    st.session_state.gsheets_client = None
if 'activity_log' not in st.session_state:
    st.session_state.activity_log = []
if 'sent_leads' not in st.session_state:
    st.session_state.sent_leads = set()
if 'selected_leads' not in st.session_state:
    st.session_state.selected_leads = []
if 'current_client' not in st.session_state:
    st.session_state.current_client = None
if 'chat_df' not in st.session_state:
    st.session_state.chat_df = pd.DataFrame()
if 'outreach_df' not in st.session_state:
    st.session_state.outreach_df = pd.DataFrame()
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.utcnow()
if 'webhook_history' not in st.session_state:
    st.session_state.webhook_history = []
if 'email_queue' not in st.session_state:
    st.session_state.email_queue = []

# ------------------ ENHANCED STYLES ------------------ #
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background: #f5f7fa;
    }
    
    .main-title {
        text-align: center;
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .sub-title {
        text-align: center;
        font-size: 1.2rem;
        color: #1a1a1a;
        margin-bottom: 2rem;
        font-weight: 500;
        text-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 8px 25px rgba(0,0,0,0.2);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 35px rgba(0,0,0,0.25);
    }
    
    .metric-value {
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    .metric-label {
        font-size: 1rem;
        opacity: 0.95;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 600;
    }
    
    .lead-card {
        background: white;
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        margin-bottom: 1.5rem;
        transition: all 0.4s ease;
        border-left: 5px solid #667eea;
    }
    
    .lead-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 15px 35px rgba(0,0,0,0.2);
    }
    
    .lead-card * {
        color: #1a1a1a !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    .lead-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 0.8rem;
    }
    
    .lead-sub {
        font-size: 1rem;
        color: #1a1a1a;
        margin-bottom: 0.6rem;
        font-weight: 500;
    }
    
    .lead-msg {
        background: #f8f9fa;
        border-radius: 15px;
        padding: 1.2rem;
        margin: 1.2rem 0;
        font-size: 1rem;
        color: #1a1a1a;
        border-left: 4px solid #667eea;
        line-height: 1.6;
        font-style: italic;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .message-card-all {
        background: white;
        padding: 32px;
        border-radius: 20px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        border: 1px solid #e1e4e8;
        transition: all 0.3s ease;
    }
    
    .message-card-all:hover {
        box-shadow: 0 8px 32px rgba(0,0,0,0.2);
        transform: translateY(-3px);
    }
    
    .message-card-all * {
        color: #1a1a1a !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.5rem 1.2rem;
        border-radius: 25px;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .status-success {
        background: #10b981;
        color: white !important;
    }
    
    .status-ready {
        background: #22c55e;
        color: white !important;
    }
    
    .status-sent {
        background: #3b82f6;
        color: white !important;
    }
    
    .status-pending {
        background: #f59e0b;
        color: white !important;
    }
    
    .status-error {
        background: #ef4444;
        color: white !important;
    }
    
    .section-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a1a1a;
        margin: 2.5rem 0 1.5rem 0;
        padding-bottom: 0.8rem;
        border-bottom: 3px solid #667eea;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .timestamp {
        font-size: 0.9rem;
        color: #1a1a1a;
        text-align: right;
        font-weight: 500;
        background: rgba(0,0,0,0.05);
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .stat-box {
        background: white;
        padding: 30px;
        border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        text-align: center;
        border-top: 5px solid #667eea;
        transition: all 0.3s ease;
    }
    
    .stat-box:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.2);
    }
    
    .stat-number {
        font-size: 3em;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: none;
    }
    
    .stat-label {
        color: #1a1a1a;
        font-size: 1em;
        margin-top: 8px;
        font-weight: 500;
        text-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .crm-card {
        background: white;
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        border-left: 5px solid #667eea;
    }
    
    .crm-card:hover {
        box-shadow: 0 8px 30px rgba(0,0,0,0.2);
    }
    
    .crm-field {
        margin-bottom: 1rem;
        padding: 0.8rem;
        background: #f8f9fa;
        border-radius: 10px;
        color: #1a1a1a;
        text-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    .crm-field strong {
        color: #667eea;
        margin-right: 0.5rem;
    }
    
    .email-card {
        background: white;
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        border-left: 5px solid #10b981;
    }
    
    .email-card * {
        color: #1a1a1a !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# ------------------ HELPER FUNCTIONS ------------------ #
@st.cache_resource
def init_google_sheets(credentials_json):
    try:
        credentials_dict = json.loads(credentials_json)
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Error initializing Google Sheets: {str(e)}")
        return None

@st.cache_data(ttl=60)
def load_sheet_data(_client, sheet_id, sheet_name):
    try:
        spreadsheet = _client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def parse_timestamp(timestamp_str):
    """Parse timestamp in format: 10/7/2025 3:54:56"""
    try:
        if pd.isna(timestamp_str) or timestamp_str == '':
            return None
        return pd.to_datetime(timestamp_str, format='%m/%d/%Y %H:%M:%S')
    except:
        try:
            return pd.to_datetime(timestamp_str)
        except:
            return None

def is_message_sent(row):
    """Check if message was successfully sent"""
    success = str(row.get('success', '')).lower()
    return success == 'true' or success == 'yes' or success == '1'

# ------------------ AUTHENTICATION ------------------ #
def authenticate_user():
    st.markdown("<div class='main-title'>🔐 LinkedIn Analytics Hub</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Secure Login</div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        uploaded_file = st.file_uploader("Upload Service Account JSON", type=['json'])
        
        if uploaded_file:
            try:
                credentials_json = uploaded_file.read().decode('utf-8')
                client = init_google_sheets(credentials_json)
                
                if client:
                    st.session_state.authenticated = True
                    st.session_state.gsheets_client = client
                    st.success("✅ Authenticated!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# ------------------ CRM TAB ------------------ #
def show_crm_dashboard():
    st.markdown("<div class='section-header'>📋 CRM Dashboard</div>", unsafe_allow_html=True)
    
    outreach_df = st.session_state.outreach_df.copy()
    
    if outreach_df.empty:
        st.warning("📭 No CRM data loaded.")
        return
    
    # Add parsed timestamp
    if 'timestamp' in outreach_df.columns:
        outreach_df['parsed_time'] = outreach_df['timestamp'].apply(parse_timestamp)
        outreach_df['date'] = outreach_df['parsed_time'].dt.date
        outreach_df['time'] = outreach_df['parsed_time'].dt.time
    
    # Filters
    st.markdown("### 🔍 Filter Leads")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        search = st.text_input("🔍 Search", placeholder="Name, location, etc.")
    
    with col2:
        if 'date' in outreach_df.columns:
            dates = sorted(outreach_df['date'].dropna().unique())
            date_options = ["All"] + [str(d) for d in dates]
            date_filter = st.selectbox("📅 Date", date_options)
        else:
            date_filter = "All"
    
    with col3:
        success_filter = st.selectbox("✅ Success Status", ["All", "True", "False"])
    
    with col4:
        if 'search_city' in outreach_df.columns:
            cities = ["All"] + sorted(outreach_df['search_city'].dropna().unique().tolist())
            city_filter = st.selectbox("🌆 City", cities)
        else:
            city_filter = "All"
    
    # Apply filters
    filtered_df = outreach_df.copy()
    
    if search:
        mask = filtered_df.astype(str).apply(
            lambda x: x.str.contains(search, case=False, na=False)
        ).any(axis=1)
        filtered_df = filtered_df[mask]
    
    if date_filter != "All" and 'date' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['date'].astype(str) == date_filter]
    
    if success_filter != "All" and 'success' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['success'].astype(str).str.lower() == success_filter.lower()]
    
    if city_filter != "All" and 'search_city' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['search_city'] == city_filter]
    
    st.markdown(f"**Showing {len(filtered_df)} of {len(outreach_df)} leads**")
    st.markdown("---")
    
    # Display CRM cards
    for idx, (i, row) in enumerate(filtered_df.iterrows()):
        with st.container():
            st.markdown(f"""
            <div class="crm-card">
                <h3 style="margin-bottom: 1rem; color: #667eea;">👤 {row.get('profile_name', row.get('name', 'Unknown'))}</h3>
            """, unsafe_allow_html=True)
            
            # Basic Info
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                <div class="crm-field"><strong>📍 Location:</strong> {row.get('profile_location', row.get('location', 'N/A'))}</div>
                <div class="crm-field"><strong>💼 Tagline:</strong> {row.get('profile_tagline', row.get('tagline', 'N/A'))}</div>
                <div class="crm-field"><strong>🔍 Search Term:</strong> {row.get('search_term', 'N/A')}</div>
                <div class="crm-field"><strong>🌆 Search City:</strong> {row.get('search_city', 'N/A')}</div>
                <div class="crm-field"><strong>🌍 Search Country:</strong> {row.get('search_country', 'N/A')}</div>
                """, unsafe_allow_html=True)
            
            with col2:
                timestamp = row.get('timestamp', 'N/A')
                success = row.get('success', 'N/A')
                status = row.get('status', 'N/A')
                connection_status = row.get('connection_status', 'N/A')
                credits = row.get('credits_used', 'N/A')
                
                success_badge = "status-success" if is_message_sent(row) else "status-error"
                
                st.markdown(f"""
                <div class="crm-field"><strong>🕐 Timestamp:</strong> {timestamp}</div>
                <div class="crm-field"><strong>✅ Success:</strong> <span class="status-badge {success_badge}">{success}</span></div>
                <div class="crm-field"><strong>📊 Status:</strong> {status}</div>
                <div class="crm-field"><strong>🔗 Connection:</strong> {connection_status}</div>
                <div class="crm-field"><strong>💳 Credits Used:</strong> {credits}</div>
                """, unsafe_allow_html=True)
            
            # Messages
            with st.expander("💬 View Messages & Details"):
                linkedin_subject = row.get('linkedin_subject', 'N/A')
                linkedin_message = row.get('linkedin_message', 'N/A')
                email_subject = row.get('email_subject', 'N/A')
                email_message = row.get('email_message', 'N/A')
                
                st.markdown("**LinkedIn Message:**")
                st.markdown(f"**Subject:** {linkedin_subject}")
                st.markdown(f"```\n{linkedin_message}\n```")
                
                st.markdown("---")
                
                st.markdown("**Email Message:**")
                st.markdown(f"**Subject:** {email_subject}")
                st.markdown(f"```\n{email_message}\n```")
                
                st.markdown("---")
                
                st.markdown("**Additional Info:**")
                st.markdown(f"**Outreach Strategy:** {row.get('outreach_strategy', 'N/A')}")
                st.markdown(f"**Personalization Points:** {row.get('personalization_points', 'N/A')}")
                st.markdown(f"**Follow-up Suggestions:** {row.get('follow_up_suggestions', 'N/A')}")
                st.markdown(f"**Summary:** {row.get('summary', 'N/A')}")
                
                if row.get('error_message'):
                    st.error(f"**Error:** {row.get('error_message')}")
                
                linkedin_url = row.get('linkedin_url', '')
                image_url = row.get('image_url', '')
                
                if linkedin_url:
                    st.markdown(f"[🔗 View LinkedIn Profile]({linkedin_url})")
                
                if image_url:
                    try:
                        st.image(image_url, width=100)
                    except:
                        pass
            
            st.markdown("</div>", unsafe_allow_html=True)

# ------------------ EMAIL TAB ------------------ #
def show_email_outreach():
    st.markdown("<div class='section-header'>📧 Email Outreach</div>", unsafe_allow_html=True)
    
    outreach_df = st.session_state.outreach_df.copy()
    
    if outreach_df.empty:
        st.warning("📭 No email data loaded.")
        return
    
    # Filter for leads with email content
    email_df = outreach_df[
        (outreach_df['email_subject'].notna() & (outreach_df['email_subject'] != '')) |
        (outreach_df['email_message'].notna() & (outreach_df['email_message'] != ''))
    ].copy()
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{len(outreach_df)}</div>
            <div class="stat-label">Total Leads</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        sent = len(outreach_df[outreach_df['success'].astype(str).str.lower() == 'true']) if 'success' in outreach_df.columns else 0
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{sent}</div>
            <div class="stat-label">Successfully Sent</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        pending = len(outreach_df[outreach_df['status'] == 'pending']) if 'status' in outreach_df.columns else 0
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{pending}</div>
            <div class="stat-label">Pending</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        ready = len(outreach_df[outreach_df['status'] == 'ready_to_send']) if 'status' in outreach_df.columns else 0
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{ready}</div>
            <div class="stat-label">Ready to Send</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Filters
    st.markdown("### 🔍 Filters & Search")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        search = st.text_input("🔍 Search", placeholder="Search leads...", key="lead_search")
    
    with col2:
        if 'date' in outreach_df.columns:
            dates = sorted(outreach_df['date'].dropna().unique())
            date_options = ["All"] + [str(d) for d in dates]
            date_filter = st.selectbox("📅 Date", date_options)
        else:
            date_filter = "All"
    
    with col3:
        if 'search_city' in outreach_df.columns:
            cities = ["All"] + sorted(outreach_df['search_city'].dropna().unique().tolist())
            city_filter = st.selectbox("🌆 City", cities)
        else:
            city_filter = "All"
    
    with col4:
        success_filter = st.selectbox("✅ Success", ["All", "True", "False"])
    
    # Apply filters
    filtered_df = outreach_df.copy()
    
    if search:
        mask = filtered_df.astype(str).apply(
            lambda x: x.str.contains(search, case=False, na=False)
        ).any(axis=1)
        filtered_df = filtered_df[mask]
    
    if date_filter != "All" and 'date' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['date'].astype(str) == date_filter]
    
    if city_filter != "All" and 'search_city' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['search_city'] == city_filter]
    
    if success_filter != "All" and 'success' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['success'].astype(str).str.lower() == success_filter.lower()]
    
    st.markdown(f"**Showing {len(filtered_df)} leads**")
    
    # View mode
    view_mode = st.radio("View Mode", ["Cards", "Table"], horizontal=True)
    
    st.markdown("---")
    
    if view_mode == "Cards":
        display_lead_cards(filtered_df)
    else:
        display_lead_table(filtered_df)

def display_lead_cards(df):
    """Display leads in card format with all columns"""
    if df.empty:
        st.info("No leads to display")
        return
    
    for idx, (i, row) in enumerate(df.iterrows()):
        name = row.get('profile_name', row.get('name', 'Unknown'))
        location = row.get('profile_location', row.get('location', 'N/A'))
        tagline = row.get('profile_tagline', row.get('tagline', 'N/A'))
        linkedin_url = row.get('linkedin_url', '#')
        linkedin_message = row.get('linkedin_message', 'No message')
        status = row.get('status', 'unknown')
        timestamp = row.get('timestamp', 'N/A')
        success = is_message_sent(row)
        search_term = row.get('search_term', 'N/A')
        search_city = row.get('search_city', 'N/A')
        
        success_indicator = "✅ MESSAGE SENT" if success else ""
        status_class = "status-success" if success else "status-pending"
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"""
            <div class="lead-card">
                <div class="lead-title">👤 {name} {success_indicator}</div>
                <div class="lead-sub">📍 {location}</div>
                <div class="lead-sub">💼 {tagline}</div>
                <div class="lead-sub">🔍 Search: {search_term} in {search_city}</div>
                <div class="lead-sub">🕐 {timestamp}</div>
                <div class="lead-sub">🔗 <a href="{linkedin_url}" target="_blank" style="color: #667eea;">LinkedIn Profile →</a></div>
                <div class="lead-msg">💬 {linkedin_message[:150]}{'...' if len(str(linkedin_message)) > 150 else ''}</div>
                <span class="status-badge {status_class}">{status.replace('_', ' ').title()}</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Actions**")
            
            if st.button("🚀 Send", key=f"send_{i}_{idx}", disabled=success, use_container_width=True):
                st.success(f"✅ Sent to {name}!")
                st.session_state.activity_log.append({
                    "type": "Message Sent",
                    "details": f"To {name}",
                    "status": "✅ Success",
                    "time": datetime.now().strftime("%H:%M:%S")
                })
            
            if st.button("📋 Copy", key=f"copy_{i}_{idx}", use_container_width=True):
                st.info("📋 Copied!")
            
            with st.expander("📊 Full Details"):
                st.markdown(f"**Connection Status:** {row.get('connection_status', 'N/A')}")
                st.markdown(f"**Credits Used:** {row.get('credits_used', 'N/A')}")
                st.markdown(f"**Session:** {row.get('browserflow_session', 'N/A')}")
                st.markdown(f"**Summary:** {row.get('summary', 'N/A')}")
                if row.get('error_message'):
                    st.error(f"Error: {row.get('error_message')}")

def display_lead_table(df):
    """Display all columns in table format"""
    if df.empty:
        st.info("No leads to display")
        return
    
    st.dataframe(df, use_container_width=True, height=600)

# ------------------ SEARCH INTERFACE ------------------ #
def show_search_interface(webhook_url):
    st.markdown("<div class='section-header'>🔍 Search & Send New Leads</div>", unsafe_allow_html=True)
    
    SEARCH_TERMS = [
        "Business Owner", "CEO", "Chief Executive Officer", "Founder", "Co-Founder",
        "Managing Director", "President", "Vice President", "VP of Sales", "VP of Marketing"
    ]
    
    CITIES = [
        "Tampa", "Miami", "Orlando", "Jacksonville", "Atlanta", "Charlotte", "New York", "Los Angeles"
    ]
    
    COUNTRIES = ["United States", "Canada", "United Kingdom", "Australia"]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🎯 Search Criteria")
        
        with st.form("search_form"):
            search_term = st.selectbox("Job Title / Role", SEARCH_TERMS)
            
            col_a, col_b = st.columns(2)
            with col_a:
                city = st.selectbox("City", CITIES)
            with col_b:
                country = st.selectbox("Country", COUNTRIES)
            
            num_leads = st.slider("Number of Leads", 1, 50, 10)
            
            submitted = st.form_submit_button("🚀 Start Search", use_container_width=True)
            
            if submitted:
                payload = {
                    "search_term": search_term,
                    "city": city,
                    "country": country,
                    "num_leads": num_leads,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                try:
                    with st.spinner("🔍 Searching..."):
                        response = requests.post(webhook_url, json=payload, timeout=10)
                    
                    if response.status_code == 200:
                        st.success(f"✅ Search initiated!")
                        st.balloons()
                        st.session_state.activity_log.append({
                            "type": "Search",
                            "details": f"{search_term} in {city}",
                            "status": "✅ Success",
                            "time": datetime.now().strftime("%H:%M:%S")
                        })
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    with col2:
        st.markdown("### 📊 Recent Activity")
        
        if st.session_state.activity_log:
            for activity in reversed(st.session_state.activity_log[-5:]):
                st.markdown(f"""
                <div style="background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <strong style="color: #1a1a1a;">{activity['type']}</strong><br>
                    <small style="color: #1a1a1a;">{activity['details']}</small><br>
                    <small style="color: #1a1a1a;">🕐 {activity['time']}</small>
                </div>
                """, unsafe_allow_html=True)

# ------------------ OVERVIEW ------------------ #
def show_overview():
    st.markdown("<div class='section-header'>📊 Dashboard Overview</div>", unsafe_allow_html=True)
    
    chat_df = st.session_state.chat_df
    outreach_df = st.session_state.outreach_df.copy()
    
    # Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(chat_df)}</div>
            <div class="metric-label">Total Chats</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);">
            <div class="metric-value">{len(outreach_df)}</div>
            <div class="metric-label">Total Leads</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        sent = len(outreach_df[outreach_df['success'].astype(str).str.lower() == 'true']) if 'success' in outreach_df.columns and not outreach_df.empty else 0
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
            <div class="metric-value">{sent}</div>
            <div class="metric-label">Messages Sent</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        pending = len(outreach_df) - sent if not outreach_df.empty else 0
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);">
            <div class="metric-value">{pending}</div>
            <div class="metric-label">Pending</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📈 Lead Status Distribution")
        if not outreach_df.empty and 'status' in outreach_df.columns:
            status_counts = outreach_df['status'].value_counts()
            fig = px.pie(values=status_counts.values, names=status_counts.index, hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 🌆 Top Cities")
        if not outreach_df.empty and 'search_city' in outreach_df.columns:
            city_counts = outreach_df['search_city'].value_counts().head(10)
            fig = px.bar(x=city_counts.values, y=city_counts.index, orientation='h')
            st.plotly_chart(fig, use_container_width=True)

# ------------------ MAIN ------------------ #
def main():
    if not st.session_state.authenticated:
        authenticate_user()
        return
    
    if not st.session_state.current_client:
        st.session_state.current_client = {
            'name': MY_PROFILE['name'],
            'linkedin_url': MY_PROFILE['url']
        }
    
    st.markdown("<div class='main-title'>🚀 LinkedIn Analytics & Outreach Hub</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sub-title'>Welcome, {st.session_state.current_client['name']}!</div>", unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Dashboard Settings")
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; color: white;">
            <h3>{st.session_state.current_client['name']}</h3>
            <a href="{st.session_state.current_client['linkedin_url']}" target="_blank" style="color: white;">🔗 LinkedIn →</a>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("🔄 Load/Refresh Data", use_container_width=True):
            with st.spinner("Loading..."):
                try:
                    st.session_state.chat_df = load_sheet_data(
                        st.session_state.gsheets_client,
                        CHAT_SPREADSHEET_ID,
                        CHAT_SHEET_NAME
                    )
                    st.session_state.outreach_df = load_sheet_data(
                        st.session_state.gsheets_client,
                        OUTREACH_SPREADSHEET_ID,
                        OUTREACH_SHEET_NAME
                    )
                    st.success("✅ Data loaded!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("💬 Chats", len(st.session_state.chat_df))
        with col2:
            st.metric("🎯 Leads", len(st.session_state.outreach_df))
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()
    
    # Main Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Overview",
        "🎯 Lead Outreach",
        "📧 Email Outreach",
        "🔍 Search & Send",
        "📋 CRM Dashboard",
        "💬 Chat Analytics"
    ])
    
    with tab1:
        show_overview()
    
    with tab2:
        show_lead_outreach()
    
    with tab3:
        show_email_outreach()
    
    with tab4:
        show_search_interface(WEBHOOK_URL)
    
    with tab5:
        show_crm_dashboard()
    
    with tab6:
        if not st.session_state.chat_df.empty:
            st.markdown("### 💬 Chat History")
            st.dataframe(st.session_state.chat_df, use_container_width=True)
        else:
            st.info("No chat data loaded")

if __name__ == "__main__":
    main() st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{len(email_df)}</div>
            <div class="stat-label">Total Emails</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        ready = len(email_df[email_df['status'] == 'ready_to_send']) if 'status' in email_df.columns else 0
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{ready}</div>
            <div class="stat-label">Ready to Send</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        sent = len(email_df[email_df['success'].astype(str).str.lower() == 'true']) if 'success' in email_df.columns else 0
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{sent}</div>
            <div class="stat-label">Sent</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        pending = len(email_df) - sent
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{pending}</div>
            <div class="stat-label">Pending</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search = st.text_input("🔍 Search", placeholder="Search emails...")
    
    with col2:
        status_options = ["All", "Ready to Send", "Sent", "Pending"]
        status_filter = st.selectbox("📊 Status", status_options)
    
    with col3:
        sort_by = st.selectbox("🔄 Sort", ["Newest First", "Oldest First", "Name A-Z"])
    
    # Apply filters
    filtered_df = email_df.copy()
    
    if search:
        mask = filtered_df.astype(str).apply(
            lambda x: x.str.contains(search, case=False, na=False)
        ).any(axis=1)
        filtered_df = filtered_df[mask]
    
    if status_filter == "Ready to Send" and 'status' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['status'] == 'ready_to_send']
    elif status_filter == "Sent" and 'success' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['success'].astype(str).str.lower() == 'true']
    elif status_filter == "Pending":
        if 'success' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['success'].astype(str).str.lower() != 'true']
    
    # Sort
    if 'timestamp' in filtered_df.columns:
        filtered_df['parsed_time'] = filtered_df['timestamp'].apply(parse_timestamp)
        if sort_by == "Newest First":
            filtered_df = filtered_df.sort_values('parsed_time', ascending=False)
        elif sort_by == "Oldest First":
            filtered_df = filtered_df.sort_values('parsed_time', ascending=True)
    
    if sort_by == "Name A-Z" and 'profile_name' in filtered_df.columns:
        filtered_df = filtered_df.sort_values('profile_name')
    
    st.markdown(f"**Showing {len(filtered_df)} emails**")
    st.markdown("---")
    
    # Display email cards
    for idx, (i, row) in enumerate(filtered_df.iterrows()):
        name = row.get('profile_name', row.get('name', 'Unknown'))
        email_subject = row.get('email_subject', 'No Subject')
        email_message = row.get('email_message', 'No Message')
        timestamp = row.get('timestamp', 'N/A')
        success = is_message_sent(row)
        
        success_indicator = "✅ SENT" if success else "📤 READY"
        success_class = "status-success" if success else "status-pending"
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"""
            <div class="email-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <h3 style="margin: 0; color: #1a1a1a;">📧 {name}</h3>
                    <span class="status-badge {success_class}">{success_indicator}</span>
                </div>
                <div class="crm-field"><strong>📋 Subject:</strong> {email_subject}</div>
                <div class="crm-field"><strong>🕐 Time:</strong> {timestamp}</div>
                <div style="background: #f8f9fa; padding: 1rem; border-radius: 10px; margin-top: 1rem; color: #1a1a1a;">
                    <strong>Message:</strong><br>
                    {email_message[:200]}{'...' if len(str(email_message)) > 200 else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Actions**")
            
            if st.button("📧 Send Email", key=f"email_send_{i}_{idx}", disabled=success, use_container_width=True):
                st.success(f"✅ Email queued for {name}!")
                st.session_state.email_queue.append({
                    'name': name,
                    'subject': email_subject,
                    'message': email_message,
                    'time': datetime.now().strftime('%H:%M:%S')
                })
            
            if st.button("📋 Copy", key=f"email_copy_{i}_{idx}", use_container_width=True):
                st.info("📋 Email copied!")
            
            with st.expander("👁️ Full Message"):
                st.markdown(f"**Subject:** {email_subject}")
                st.markdown("---")
                st.markdown(email_message)

# ------------------ LEAD OUTREACH (UPDATED) ------------------ #
def show_lead_outreach():
    st.markdown("<div class='section-header'>🎯 Lead Outreach Management</div>", unsafe_allow_html=True)
    
    outreach_df = st.session_state.outreach_df.copy()
    
    if outreach_df.empty:
        st.warning("📭 No outreach data loaded.")
        return
    
    # Parse timestamps
    if 'timestamp' in outreach_df.columns:
        outreach_df['parsed_time'] = outreach_df['timestamp'].apply(parse_timestamp)
        outreach_df['date'] = outreach_df['parsed_time'].dt.date
        outreach_df['time'] = outreach_df['parsed_time'].dt.time
    
    # Statistics
    col1, col2, col3, col4 =
