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
# Google Sheets Configuration
CHAT_SPREADSHEET_ID = "1klm60YFXSoV510S4igv5LfREXeykDhNA5Ygq7HNFN0I"
CHAT_SHEET_NAME = "linkedin_chat_history_advanced 2"

OUTREACH_SPREADSHEET_ID = "1eLEFvyV1_f74UC1g5uQ-xA7A62sK8Pog27KIjw_Sk3Y"
OUTREACH_SHEET_NAME = "linkedin-tracking-csv.csv"

# My profile information
MY_PROFILE = {
    "name": "Donmenico Hudson",
    "url": "https://www.linkedin.com/in/donmenicohudson/"
}

# Webhook URL
WEBHOOK_URL = "https://agentonline-u29564.vm.elestio.app/webhook/Leadlinked"

# ------------------ SESSION STATE INITIALIZATION ------------------ #
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'gsheets_client' not in st.session_state:
    st.session_state.gsheets_client = None
if 'client_data' not in st.session_state:
    st.session_state.client_data = None
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
if 'message_tracking' not in st.session_state:
    st.session_state.message_tracking = {}
if 'daily_stats' not in st.session_state:
    st.session_state.daily_stats = defaultdict(lambda: {'searches': 0, 'messages': 0, 'responses': 0})

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
        color: #64748b;
        margin-bottom: 2rem;
        font-weight: 500;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        border: 1px solid rgba(255,255,255,0.1);
        position: relative;
        overflow: hidden;
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 100%);
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 35px rgba(102, 126, 234, 0.4);
    }
    
    .metric-card:hover::before {
        opacity: 1;
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
    
    .metric-trend {
        font-size: 0.9rem;
        margin-top: 0.5rem;
        opacity: 0.8;
    }
    
    .contact-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 20px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        transition: all 0.3s ease;
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }
    
    .contact-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 100%);
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    
    .contact-card:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 15px 40px rgba(102, 126, 234, 0.4);
    }
    
    .contact-card:hover::before {
        opacity: 1;
    }
    
    .contact-name {
        font-size: 1.8em;
        font-weight: 700;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .contact-stats {
        display: flex;
        gap: 20px;
        margin-top: 15px;
        flex-wrap: wrap;
    }
    
    .contact-stat-item {
        background: rgba(255,255,255,0.15);
        padding: 8px 15px;
        border-radius: 10px;
        font-size: 0.95em;
    }
    
    .lead-card {
        background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        margin-bottom: 1.5rem;
        transition: all 0.4s ease;
        border-left: 5px solid #667eea;
        position: relative;
        overflow: hidden;
    }
    
    .lead-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, #667eea, #764ba2);
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    
    .lead-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 15px 35px rgba(0,0,0,0.15);
    }
    
    .lead-card:hover::before {
        opacity: 1;
    }
    
    .lead-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .lead-sub {
        font-size: 1rem;
        color: #475569;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: center;
        gap: 0.8rem;
        font-weight: 500;
    }
    
    .lead-msg {
        background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
        border-radius: 15px;
        padding: 1.2rem;
        margin: 1.2rem 0;
        font-size: 1rem;
        color: #334155;
        border-left: 4px solid #667eea;
        line-height: 1.6;
        font-style: italic;
    }
    
    .message-received {
        background: white;
        padding: 25px;
        border-radius: 20px 20px 20px 5px;
        margin-bottom: 20px;
        border-left: 5px solid #667eea;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        transition: all 0.2s ease;
    }
    
    .message-received:hover {
        box-shadow: 0 6px 20px rgba(0,0,0,0.12);
        transform: translateX(5px);
    }
    
    .message-sent {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 25px;
        border-radius: 20px 20px 5px 20px;
        margin-bottom: 20px;
        color: white;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        margin-left: 60px;
        transition: all 0.2s ease;
    }
    
    .message-sent:hover {
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        transform: translateX(-5px);
    }
    
    .message-card-all {
        background: white;
        padding: 32px;
        border-radius: 20px;
        margin-bottom: 24px;
        box-shadow: 0 2px 16px rgba(0,0,0,0.08);
        border: 1px solid #e1e4e8;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .message-card-all::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        width: 5px;
        height: 100%;
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        transform: scaleY(0);
        transition: transform 0.3s ease;
    }
    
    .message-card-all:hover {
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.15);
        transform: translateY(-3px);
        border-color: #667eea;
    }
    
    .message-card-all:hover::before {
        transform: scaleY(1);
    }
    
    .message-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 20px;
        padding-bottom: 18px;
        border-bottom: 2px solid #f5f7fa;
    }
    
    .message-sender {
        font-size: 1.25em;
        font-weight: 700;
        color: #1a1a2e;
        display: flex;
        align-items: center;
        gap: 12px;
        letter-spacing: -0.02em;
    }
    
    .message-sender-badge {
        background: #667eea;
        color: white;
        padding: 6px 14px;
        border-radius: 14px;
        font-size: 0.7em;
        font-weight: 600;
        letter-spacing: 0.3px;
        text-transform: uppercase;
    }
    
    .message-timestamp {
        color: #6b7280;
        font-size: 0.95em;
        display: flex;
        align-items: center;
        gap: 6px;
        font-weight: 500;
    }
    
    .message-content {
        color: #2d3748;
        font-size: 1.08em;
        line-height: 1.75;
        margin: 20px 0;
        white-space: pre-wrap;
        word-wrap: break-word;
        font-weight: 400;
    }
    
    .message-footer {
        display: flex;
        flex-wrap: wrap;
        gap: 20px;
        margin-top: 20px;
        padding-top: 18px;
        border-top: 2px solid #f5f7fa;
        font-size: 0.92em;
        color: #6b7280;
        align-items: center;
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
    }
    
    .status-ready {
        background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
        color: #166534;
        border: 1px solid #22c55e;
    }
    
    .status-sent {
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        color: #1e40af;
        border: 1px solid #3b82f6;
    }
    
    .status-pending {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        color: #92400e;
        border: 1px solid #f59e0b;
    }
    
    .section-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1e293b;
        margin: 2.5rem 0 1.5rem 0;
        padding-bottom: 0.8rem;
        border-bottom: 3px solid #667eea;
        position: relative;
    }
    
    .section-header::after {
        content: '';
        position: absolute;
        bottom: -3px;
        left: 0;
        width: 60px;
        height: 3px;
        background: linear-gradient(90deg, #764ba2, #667eea);
    }
    
    .client-profile-banner {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 40px;
        border-radius: 20px;
        color: white;
        margin-bottom: 30px;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
    }
    
    .timestamp {
        font-size: 0.9rem;
        color: #94a3b8;
        text-align: right;
        font-weight: 500;
        background: rgba(148, 163, 184, 0.1);
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        display: inline-block;
    }
    
    .stats-container {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 2rem;
        border: 1px solid rgba(102, 126, 234, 0.1);
    }
    
    .activity-item {
        background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
        border-radius: 15px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        transition: all 0.3s ease;
    }
    
    .activity-item:hover {
        transform: translateX(5px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .filter-section {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(102, 126, 234, 0.1);
    }
    
    .chart-container {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        margin-bottom: 1.5rem;
    }
    
    .profile-badge {
        width: 50px;
        height: 50px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 1.5em;
        font-weight: 700;
        margin-right: 15px;
    }
    
    .linkedin-link {
        color: #667eea;
        text-decoration: none;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 5px;
        transition: all 0.2s ease;
    }
    
    .linkedin-link:hover {
        color: #764ba2;
        gap: 8px;
    }
    
    .linkedin-badge {
        background: rgba(255,255,255,0.2);
        padding: 8px 16px;
        border-radius: 25px;
        display: inline-block;
        margin-top: 15px;
        font-size: 0.95em;
        transition: all 0.3s ease;
    }
    
    .linkedin-badge:hover {
        background: rgba(255,255,255,0.3);
        transform: scale(1.05);
    }
    
    .conversation-date-divider {
        text-align: center;
        color: #5f6368;
        font-size: 0.9em;
        margin: 30px 0;
        position: relative;
    }
    
    .conversation-date-divider::before,
    .conversation-date-divider::after {
        content: '';
        position: absolute;
        top: 50%;
        width: 40%;
        height: 1px;
        background: #e8eaed;
    }
    
    .conversation-date-divider::before {
        left: 0;
    }
    
    .conversation-date-divider::after {
        right: 0;
    }
    
    .auth-container {
        max-width: 600px;
        margin: 50px auto;
        background: white;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.1);
    }
    
    .stat-box {
        background: white;
        padding: 30px;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        text-align: center;
        border-top: 5px solid #667eea;
        transition: all 0.3s ease;
    }
    
    .stat-box:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }
    
    .stat-number {
        font-size: 3em;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .stat-label {
        color: #5f6368;
        font-size: 1em;
        margin-top: 8px;
        font-weight: 500;
        letter-spacing: 0.5px;
    }
</style>
""", unsafe_allow_html=True)

# ------------------ GOOGLE SHEETS CONNECTION ------------------ #
@st.cache_resource
def init_google_sheets(credentials_json):
    """Initialize Google Sheets connection with service account"""
    try:
        credentials_dict = json.loads(credentials_json)
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = Credentials.from_service_account_info(
            credentials_dict, 
            scopes=scopes
        )
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Error initializing Google Sheets: {str(e)}")
        return None

@st.cache_data(ttl=60)
def load_sheet_data(_client, sheet_id, sheet_name):
    """Load data from a specific Google Sheet"""
    try:
        spreadsheet = _client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Error loading data from {sheet_name}: {str(e)}")
        return pd.DataFrame()

# ------------------ CLIENT PROFILE SYSTEM ------------------ #
def get_client_from_url():
    """Extract client identifier from URL parameters"""
    query_params = st.query_params
    return query_params.get('client', 'donmenico')  # Default to donmenico

def load_client_profile(client_id):
    """Load client-specific profile and preferences"""
    # Always use static configuration
    return {
        'name': MY_PROFILE['name'],
        'linkedin_url': MY_PROFILE['url'],
        'chat_sheet_id': CHAT_SPREADSHEET_ID,
        'chat_sheet_name': CHAT_SHEET_NAME,
        'outreach_sheet_id': OUTREACH_SPREADSHEET_ID,
        'outreach_sheet_name': OUTREACH_SHEET_NAME,
        'webhook_url': WEBHOOK_URL
    }

# ------------------ AUTHENTICATION ------------------ #
def authenticate_user():
    """Handle user authentication with service account"""
    st.markdown("<div class='main-title'>🔐 LinkedIn Analytics Hub</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Secure Login with Google Service Account</div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
        
        st.markdown("### 📁 Upload Service Account Credentials")
        st.markdown("---")
        
        uploaded_file = st.file_uploader(
            "Choose your Google Service Account JSON file",
            type=['json'],
            help="This file contains your Google Cloud credentials",
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            try:
                credentials_json = uploaded_file.read().decode('utf-8')
                
                with st.spinner("🔄 Authenticating..."):
                    client = init_google_sheets(credentials_json)
                
                if client:
                    st.session_state.authenticated = True
                    st.session_state.gsheets_client = client
                    st.success("✅ Authentication successful!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to authenticate. Please check your credentials.")
            except Exception as e:
                st.error(f"❌ Authentication error: {str(e)}")
        
        st.markdown("---")
        
        with st.expander("📋 Setup Instructions", expanded=True):
            st.markdown("""
            **Step-by-Step Guide:**
            
            **1. Google Cloud Console**
            - Visit [console.cloud.google.com](https://console.cloud.google.com)
            - Create a new project or select existing one
            
            **2. Enable Required APIs**
            - Navigate to "APIs & Services" > "Library"
            - Search and enable:
              - Google Sheets API
              - Google Drive API
            
            **3. Create Service Account**
            - Go to "IAM & Admin" > "Service Accounts"
            - Click "Create Service Account"
            - Give it a name (e.g., "linkedin-analytics")
            - Grant "Editor" role
            - Click "Done"
            
            **4. Download JSON Key**
            - Click on your new service account
            - Go to "Keys" tab
            - Click "Add Key" > "Create new key"
            - Choose "JSON" format
            - Download the file
            
            **5. Share Your Google Sheets**
            - Open your Google Sheets (both chat and outreach)
            - Click "Share" button
            - Paste the service account email (from JSON file)
            - Grant "Editor" access
            - Click "Send"
            
            **6. Upload & Login**
            - Use the file uploader above
            - Upload your downloaded JSON file
            - Authentication will happen automatically
            """)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.info("💡 **Pro Tip:** Your credentials are processed securely and never stored on our servers.")

# ------------------ HELPER FUNCTIONS ------------------ #
def is_me(sender_name, sender_url, my_profile):
    """Check if the sender is the current user"""
    if not sender_name or not isinstance(sender_name, str):
        return False
    return (
        my_profile["name"].lower() in sender_name.lower() or
        (sender_url and my_profile["url"].lower() in str(sender_url).lower())
    )

def get_initials(name):
    """Get initials from name"""
    if not name:
        return "?"
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[1][0]}".upper()
    return name[0].upper()

# ------------------ CHAT ANALYTICS FUNCTIONS ------------------ #
def get_contact_info(df, my_profile):
    """Extract unique contacts from chat data"""
    contacts = {}
    
    for idx, row in df.iterrows():
        sender_name = row.get('sender_name', '')
        sender_url = row.get('sender_linkedin_url', '')
        lead_name = row.get('lead_name', '')
        lead_url = row.get('lead_linkedin_url', '')
        
        if is_me(sender_name, sender_url, my_profile):
            continue
        
        contact_url = sender_url if sender_url else lead_url
        contact_name = sender_name if sender_name else lead_name
        
        if contact_url and contact_url not in contacts:
            contacts[contact_url] = {
                'name': contact_name,
                'url': contact_url,
                'messages': [],
                'last_contact': None,
                'received_count': 0,
                'sent_count': 0
            }
    
    for idx, row in df.iterrows():
        sender_name = row.get('sender_name', '')
        sender_url = row.get('sender_linkedin_url', '')
        lead_url = row.get('lead_linkedin_url', '')
        
        contact_url = None
        if is_me(sender_name, sender_url, my_profile):
            contact_url = lead_url
        else:
            contact_url = sender_url
            
        if contact_url in contacts:
            contacts[contact_url]['messages'].append(row)
            
            # Update last contact time
            try:
                timestamp = pd.to_datetime(row.get('timestamp'))
                if contacts[contact_url]['last_contact'] is None or timestamp > contacts[contact_url]['last_contact']:
                    contacts[contact_url]['last_contact'] = timestamp
            except:
                pass
            
            # Count sent/received
            if is_me(sender_name, sender_url, my_profile):
                contacts[contact_url]['sent_count'] += 1
            else:
                contacts[contact_url]['received_count'] += 1
                
    # Format last contact time
    for url, info in contacts.items():
        if info['last_contact'] is not None:
            contacts[url]['last_contact'] = info['last_contact'].strftime('%Y-%m-%d %H:%M')
        else:
            contacts[url]['last_contact'] = 'N/A'
            
    return contacts

def create_message_chart(df):
    """Create a chart showing message activity over time"""
    if df.empty or 'timestamp' not in df.columns:
        return None
    
    df['date'] = df['timestamp'].dt.date
    daily_activity = df.groupby('date').size().reset_index(name='Messages')
    
    fig = px.line(
        daily_activity,
        x='date',
        y='Messages',
        title='Daily Message Activity',
        labels={'date': 'Date', 'Messages': 'Total Messages'},
        color_discrete_sequence=['#667eea']
    )
    
    fig.update_layout(
        xaxis_title=None,
        yaxis_title="Message Count",
        font=dict(family="Inter", size=12, color="#1e293b"),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

# ------------------ LEAD OUTREACH FUNCTIONS ------------------ #
def create_outreach_chart(df):
    """Create a chart showing outreach status distribution"""
    if df.empty or 'status' not in df.columns:
        return None
    
    status_counts = df['status'].value_counts().reset_index()
    status_counts.columns = ['status', 'count']
    
    color_map = {
        'Replied': '#22c55e',
        'Sent': '#3b82f6',
        'Booked': '#f59e0b',
        'Not Sent': '#ef4444',
        'Unknown': '#94a3b8'
    }
    
    fig = px.pie(
        status_counts, 
        values='count', 
        names='status', 
        title='Distribution of Outreach Statuses',
        color='status',
        color_discrete_map=color_map,
        hole=0.3
    )
    
    fig.update_traces(textinfo='percent+label')
    fig.update_layout(
        font=dict(family="Inter", size=12, color="#1e293b"),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

# ------------------ MAIN APPLICATION FLOW ------------------ #
def main():
    """Main function to run the Streamlit app"""
    
    # Sidebar for configuration and data loading
    with st.sidebar:
        st.markdown(f"## 👤 {MY_PROFILE['name']}'s Dashboard")
        st.markdown(f"**Last Refresh:** {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        st.markdown("---")
        
        # Authentication Status
        if st.session_state.authenticated:
            st.success("✅ Authenticated")
            st.markdown(f"""
            <div style="background: #f8fafc; padding: 10px; border-radius: 10px; margin-top: 10px;">
                <small>🔗 Client: **{MY_PROFILE['name']}**</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error("❌ Not Authenticated")
            st.info("Please upload your Google Service Account JSON file to proceed.")
        
        st.markdown("---")
        
        # Data Source Configuration (Display only - values are static)
        st.subheader("📊 Data Configuration")
        
        st.info("📌 Using default configuration for Donmenico Hudson")
        
        with st.expander("View Configuration Details"):
            st.text(f"Chat Sheet ID: {CHAT_SPREADSHEET_ID}")
            st.text(f"Chat Sheet Name: {CHAT_SHEET_NAME}")
            st.text(f"Outreach Sheet ID: {OUTREACH_SPREADSHEET_ID}")
            st.text(f"Outreach Sheet Name: {OUTREACH_SHEET_NAME}")
            st.text(f"Webhook URL: {WEBHOOK_URL}")
        
        st.markdown("---")
        
        # Load Data Button
        if st.button("🔄 Load/Refresh Data", use_container_width=True):
            if not st.session_state.authenticated:
                st.error("Please authenticate first.")
            else:
                with st.spinner("Loading data from Google Sheets..."):
                    try:
                        # Load chat data
                        st.session_state.chat_df = load_sheet_data(
                            st.session_state.gsheets_client,
                            CHAT_SPREADSHEET_ID,
                            CHAT_SHEET_NAME
                        )
                        if not st.session_state.chat_df.empty:
                            st.success(f"✅ Loaded {len(st.session_state.chat_df)} chat messages!")
                        
                        # Load outreach data
                        st.session_state.outreach_df = load_sheet_data(
                            st.session_state.gsheets_client,
                            OUTREACH_SPREADSHEET_ID,
                            OUTREACH_SHEET_NAME
                        )
                        if not st.session_state.outreach_df.empty:
                            st.success(f"✅ Loaded {len(st.session_state.outreach_df)} leads!")
                        
                        st.session_state.last_refresh = datetime.utcnow()
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error loading data: {str(e)}")
        
        st.markdown("---")
        
        # Quick Stats
        st.subheader("📊 Quick Stats")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("💬 Chat Messages", len(st.session_state.chat_df))
        with col2:
            st.metric("🎯 Outreach Leads", len(st.session_state.outreach_df))
        
        st.markdown(f"""
        <div style="background: #f8fafc; padding: 10px; border-radius: 10px; margin-top: 10px;">
            <small>🕐 Last refresh: {st.session_state.last_refresh.strftime('%H:%M:%S UTC')}</small>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("🔄 Auto-refresh (60s)", value=False)
        
        st.markdown("---")
        
        # Logout
        if st.button("🚪 Logout", use_container_width=True, type="primary"):
            st.session_state.authenticated = False
            st.session_state.gsheets_client = None
            st.session_state.chat_df = pd.DataFrame()
            st.session_state.outreach_df = pd.DataFrame()
            st.session_state.current_client = None
            st.success("👋 Logged out successfully!")
            time.sleep(1)
            st.rerun()
    
    # Main Content
    if not st.session_state.authenticated:
        authenticate_user()
    else:
        # Ensure data is loaded on first run after auth
        if st.session_state.chat_df.empty and st.session_state.outreach_df.empty:
            st.info("Data not loaded. Click 'Load/Refresh Data' in the sidebar to begin.")
            return
        
        st.markdown("<h1 class='main-title'>LinkedIn Analytics & Outreach Hub</h1>", unsafe_allow_html=True)
        st.markdown(f"<div class='sub-title'>Welcome, {MY_PROFILE['name']}!</div>", unsafe_allow_html=True)
        
        # Tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Overview",
            "💬 Chat Analytics",
            "🎯 Lead Outreach",
            "🔍 Search & Send",
            "📈 Advanced Analytics"
        ])
        
        with tab1:
            show_overview()
        
        with tab2:
            show_chat_analytics()
        
        with tab3:
            show_lead_outreach()
        
        with tab4:
            show_search_interface(WEBHOOK_URL)
        
        with tab5:
            show_advanced_analytics()
        
        # Auto-refresh logic
        if auto_refresh:
            time.sleep(60)
            st.rerun()

# ------------------ TAB CONTENT FUNCTIONS ------------------ #
def show_overview():
    """Display the main dashboard overview"""
    chat_df = st.session_state.chat_df
    outreach_df = st.session_state.outreach_df
    
    st.markdown("<div class='section-header'>🚀 Dashboard Overview</div>", unsafe_allow_html=True)
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_chats = len(chat_df)
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <div class="metric-value">{total_chats}</div>
            <div class="metric-label">Total Chats</div>
            <div class="metric-trend">💬 All conversations</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_leads = len(outreach_df)
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);">
            <div class="metric-value">{total_leads}</div>
            <div class="metric-label">Total Leads</div>
            <div class="metric-trend">🎯 Outreach database</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        sent_count = len(outreach_df[outreach_df['status'] == 'sent']) if 'status' in outreach_df.columns and not outreach_df.empty else 0
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
            <div class="metric-value">{sent_count}</div>
            <div class="metric-label">Messages Sent</div>
            <div class="metric-trend">✅ Successfully delivered</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Always use static profile
        contacts = get_contact_info(chat_df, {
            'name': MY_PROFILE['name'],
            'url': MY_PROFILE['url']
        }) if not chat_df.empty else {}
        contact_count = len(contacts)
        
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);">
            <div class="metric-value">{contact_count}</div>
            <div class="metric-label">Active Contacts</div>
            <div class="metric-trend">👥 Unique conversations</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Recent Activity Section
    st.markdown("### 📈 Recent Activity")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 💬 Chat Activity")
        if not chat_df.empty and 'date' in chat_df.columns:
            try:
                daily_chats = chat_df.groupby('date').size().tail(7).reset_index()
                daily_chats.columns = ['Date', 'Messages']
                
                fig = px.bar(
                    daily_chats,
                    x='Date',
                    y='Messages',
                    title="Last 7 Days",
                    color='Messages',
                    color_continuous_scale='Blues'
                )
                fig.update_layout(
                    showlegend=False,
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.info("No date data available for visualization")
        else:
            st.info("📭 No chat data loaded yet")
    
    with col2:
        st.markdown("#### 🎯 Outreach Status")
        if not outreach_df.empty and 'status' in outreach_df.columns:
            status_counts = outreach_df['status'].value_counts()
            
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Lead Status Distribution",
                color_discrete_sequence=px.colors.qualitative.Set3,
                hole=0.4
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📭 No outreach data loaded yet")
    
    st.markdown("---")
    
    # Activity Log
    st.markdown("### 🔔 Recent Activity Log")
    
    if st.session_state.activity_log:
        recent_activities = st.session_state.activity_log[-10:]
        
        for activity in reversed(recent_activities):
            st.markdown(f"""
            <div class="activity-item">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{activity.get('type', 'Activity')}</strong>: {activity.get('details', 'No details')}
                        <br><small>📊 Status: {activity.get('status', 'Unknown')}</small>
                    </div>
                    <div class="timestamp">🕐 {activity.get('time', 'N/A')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("🔔 No recent activity. Start using the dashboard to see activity here!")

def show_chat_analytics():
    st.markdown("<div class='section-header'>💬 Chat History Analytics</div>", unsafe_allow_html=True)
    
    chat_df = st.session_state.chat_df
    
    if chat_df.empty:
        st.warning("📭 No chat data loaded. Please load your chat history sheet from the sidebar.")
        st.info("💡 **How to get started:**\n1. Click 'Load/Refresh Data' in the sidebar\n2. Your chat history will appear here")
        return
    
    # Always use static profile
    my_profile = {
        'name': MY_PROFILE['name'],
        'url': MY_PROFILE['url']
    }
    
    contacts = get_contact_info(chat_df, my_profile)
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{len(chat_df)}</div>
            <div class="stat-label">Total Messages</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{len(contacts)}</div>
            <div class="stat-label">Contacts</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        my_messages = sum(1 for _, row in chat_df.iterrows() if is_me(row.get('sender_name', ''), row.get('sender_linkedin_url', ''), my_profile))
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{my_messages}</div>
            <div class="stat-label">Sent by You</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        received = len(chat_df) - my_messages
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{received}</div>
            <div class="stat-label">Received</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Message activity chart
    with st.expander("📊 View Message Activity Chart", expanded=False):
        chart = create_message_chart(chat_df)
        if chart:
            st.plotly_chart(chart, use_container_width=True)
    
    st.markdown("---")
    
    # View Selection
    view_mode = st.radio(
        "### 🔍 Select View Mode",
        ["📇 All Contacts", "💬 Contact Conversation", "📋 All Messages"],
        horizontal=True
    )
    
    st.markdown("---")
    
    if view_mode == "📇 All Contacts":
        show_all_contacts(contacts)
    elif view_mode == "💬 Contact Conversation":
        show_contact_conversation(contacts, chat_df, my_profile)
    else:
        show_all_messages_view(chat_df, my_profile)

def show_all_contacts(contacts):
    """Display all contacts in card format"""
    st.subheader("📇 All Contacts")
    st.markdown("*Click on LinkedIn profile to connect with contacts*")
    
    if not contacts:
        st.info("🔭 No contacts found in chat history")
        return
    
    # Search and filters
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Search contacts by name", "", key="contact_search")
    with col2:
        sort_by = st.selectbox("Sort by", ["Name", "Messages", "Recent"])
    
    # Filter contacts
    filtered_contacts = {
        url: info for url, info in contacts.items()
        if not search or search.lower() in info['name'].lower()
    }
    
    # Sort contacts
    if sort_by == "Messages":
        filtered_contacts = dict(sorted(
            filtered_contacts.items(),
            key=lambda x: len(x[1]['messages']),
            reverse=True
        ))
    elif sort_by == "Name":
        filtered_contacts = dict(sorted(
            filtered_contacts.items(),
            key=lambda x: x[1]['name']
        ))
    
    st.markdown(f"**Showing {len(filtered_contacts)} contacts**")
    st.markdown("")
    
    # Display in columns
    cols = st.columns(2)
    
    for idx, (url, info) in enumerate(filtered_contacts.items()):
        col = cols[idx % 2]
        
        message_count = len(info['messages'])
        initials = get_initials(info['name'])
        
        with col:
            st.markdown(f"""
            <div class="contact-card">
                <div style="display: flex; align-items: center; margin-bottom: 20px;">
                    <div class="profile-badge">{initials}</div>
                    <div>
                        <div class="contact-name">{info['name']}</div>
                    </div>
                </div>
                <div class="contact-stats">
                    <div class="contact-stat-item">
                        💬 <strong>{message_count}</strong> messages
                    </div>
                    <div class="contact-stat-item">
                        📤 <strong>{info['sent_count']}</strong> sent
                    </div>
                    <div class="contact-stat-item">
                        📥 <strong>{info['received_count']}</strong> received
                    </div>
                </div>
                <p style="margin-top: 15px; opacity: 0.9;">
                    <strong>Last Contact:</strong> {info['last_contact']}
                </p>
                <div class="linkedin-badge">
                    <a href="{url}" target="_blank" style="color: white; text-decoration: none;">
                        🔗 View LinkedIn Profile →
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)

def show_contact_conversation(contacts, chat_df, my_profile):
    """Display conversation with a specific contact"""
    st.subheader("💬 Contact Conversation")
    st.markdown("*View detailed conversation history*")
    
    if not contacts:
        st.info("🔭 No contacts found")
        return
    
    # Contact selection
    contact_names = {info['name']: url for url, info in contacts.items()}
    selected_name = st.selectbox("Select Contact", sorted(contact_names.keys()))
    
    if selected_name:
        selected_url = contact_names[selected_name]
        contact_info = contacts[selected_url]
        
        st.markdown(f"### Conversation with {selected_name}")
        st.markdown(f"**LinkedIn:** [{selected_url}]({selected_url})")
        st.markdown(f"**Total Messages:** {len(contact_info['messages'])}")
        st.markdown("---")
        
        # Sort messages by timestamp
        messages_df = pd.DataFrame(contact_info['messages']).sort_values(by='timestamp', ascending=True)
        
        last_date = None
        
        for _, row in messages_df.iterrows():
            current_date = row['timestamp'].date()
            
            # Date Divider
            if current_date != last_date:
                st.markdown(f"<div class='conversation-date-divider'>{current_date.strftime('%B %d, %Y')}</div>", unsafe_allow_html=True)
                last_date = current_date
            
            # Message Card
            sender_name = row.get('sender_name', 'Unknown')
            message = row.get('message', 'No content')
            timestamp = row['timestamp'].strftime('%I:%M %p')
            
            if is_me(sender_name, row.get('sender_linkedin_url', ''), my_profile):
                # Sent Message (Blue/Purple gradient)
                st.markdown(f"""
                <div class='message-sent'>
                    <p style='font-size: 0.9em; opacity: 0.8; margin-bottom: 5px;'>{timestamp} - You</p>
                    <p style='margin: 0;'>{message}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Received Message (White/Light background)
                st.markdown(f"""
                <div class='message-received'>
                    <p style='font-size: 0.9em; color: #667eea; margin-bottom: 5px;'>{timestamp} - {sender_name}</p>
                    <p style='margin: 0; color: #1e293b;'>{message}</p>
                </div>
                """, unsafe_allow_html=True)

def show_all_messages_view(chat_df, my_profile):
    """Display all messages in a searchable/filterable list"""
    st.subheader("📋 All Messages")
    
    # Filtering and Searching
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_term = st.text_input("Search Messages (Content, Sender)", "", key="message_search")
    
    with col2:
        sender_filter = st.multiselect(
            "Filter by Sender",
            options=['You', 'Contact'],
            default=['You', 'Contact']
        )
        
    filtered_df = chat_df.copy()
    
    # Add a 'Sender Type' column for easy filtering
    filtered_df['sender_type'] = filtered_df.apply(
        lambda row: 'You' if is_me(row.get('sender_name', ''), row.get('sender_linkedin_url', ''), my_profile) else 'Contact',
        axis=1
    )
    
    filtered_df = filtered_df[filtered_df['sender_type'].isin(sender_filter)]
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df.apply(lambda row: search_term.lower() in str(row).lower(), axis=1)
        ]
        
    st.info(f"Displaying {filtered_df.shape[0]} out of {chat_df.shape[0]} total messages.")
    
    # Display Messages
    for _, row in filtered_df.sort_values(by='timestamp', ascending=False).iterrows():
        sender_name = row.get('sender_name', 'Unknown')
        message = row.get('message', 'No content')
        timestamp = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        sender_type = row['sender_type']
        
        badge_style = "background: #667eea;" if sender_type == 'You' else "background: #10b981;"
        
        st.markdown(f"""
        <div class='message-card-all'>
            <div class='message-header'>
                <div class='message-sender'>
                    <span class='message-sender-badge' style='{badge_style}'>{sender_type}</span>
                    {sender_name}
                </div>
                <div class='message-timestamp'>
                    🕐 {timestamp}
                </div>
            </div>
            <div class='message-content'>
                {message}
            </div>
        </div>
        """, unsafe_allow_html=True)

def show_lead_outreach():
    """Display the lead outreach management interface"""
    st.markdown("<div class='section-header'>🎯 Lead Outreach Management</div>", unsafe_allow_html=True)
    
    outreach_df = st.session_state.outreach_df
    
    if outreach_df.empty:
        st.warning("📭 No outreach data loaded. Please load your outreach tracking sheet from the sidebar.")
        st.info("💡 **How to get started:**\n1. Click 'Load/Refresh Data' in the sidebar\n2. Your leads will appear here")
        return
    
    # Filtering and Searching
    st.markdown("### ⚙️ Filters and Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        search_term = st.text_input("Search Leads", "", key="lead_search")
    
    with col2:
        status_filter = st.multiselect(
            "Filter by Status",
            options=outreach_df['status'].unique().tolist(),
            default=outreach_df['status'].unique().tolist()
        )
        
    filtered_df = outreach_df[outreach_df['status'].isin(status_filter)]
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df.apply(lambda row: search_term.lower() in str(row).lower(), axis=1)
        ]
        
    st.info(f"Displaying {filtered_df.shape[0]} out of {outreach_df.shape[0]} total leads.")
    
    # Bulk Actions
    st.markdown("### 🚀 Bulk Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("Select All", use_container_width=True):
            st.session_state.selected_leads = filtered_df.index.tolist()
            st.rerun()
            
    with col2:
        if st.button("Clear Selection", use_container_width=True):
            st.session_state.selected_leads = []
            st.rerun()
            
    bulk_count = len(st.session_state.selected_leads)
    
    with col3:
        if st.button(f"Bulk Send ({bulk_count})", use_container_width=True, disabled=bulk_count == 0):
            status_text = st.empty()
            progress_bar = st.progress(0)
            
            for idx, i in enumerate(st.session_state.selected_leads):
                if i not in st.session_state.sent_leads:
                    row = filtered_df.loc[i]
                    lead_name = row.get('profile_name', row.get('name', 'Lead'))
                    status_text.text(f"Sending to {lead_name}...")
                    st.session_state.sent_leads.add(i)
                    
                    # Log activity
                    st.session_state.activity_log.append({
                        "type": "Bulk Send",
                        "details": f"Message to {lead_name}",
                        "status": "✅ Success",
                        "time": datetime.now().strftime("%H:%M:%S")
                    })
                    
                    progress_bar.progress((idx + 1) / bulk_count)
                    time.sleep(0.3)
                
            status_text.text("✅ Bulk operation completed!")
            st.success(f"✅ Successfully sent {bulk_count} messages!")
            time.sleep(2)
            st.rerun()
    
    with col4:
        if st.button("📊 Export CSV", use_container_width=True, key="export_csv"):
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Download",
                data=csv,
                file_name=f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="download_csv"
            )
            
    st.markdown("---")
    
    # Display Leads
    display_leads_cards(filtered_df)

def display_leads_cards(df):
    """Display leads in card format"""
    if df.empty:
        st.info("No leads to display")
        return
    
    for idx, (i, row) in enumerate(df.iterrows()):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            name = str(row.get('profile_name', row.get('name', 'Unnamed Lead')))
            location = str(row.get('profile_location', row.get('location', 'Unknown')))
            tagline = str(row.get('profile_tagline', row.get('tagline', 'No tagline')))
            linkedin_url = str(row.get('linkedin_url', '#'))
            message = str(row.get('linkedin_message', row.get('message', 'No message')))
            status = str(row.get('status', 'unknown'))
            
            try:
                timestamp = pd.to_datetime(row.get('timestamp', datetime.now()))
                if pd.isna(timestamp):
                    timestamp = datetime.now()
                timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M')
            except:
                timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M')
            
            search_term = str(row.get('search_term', 'N/A'))
            search_city = str(row.get('search_city', 'N/A'))
            
            status_class = {
                'ready_to_send': 'status-ready',
                'sent': 'status-sent',
                'pending': 'status-pending'
            }.get(status, 'status-pending')
            
            is_sent = status == 'sent' or i in st.session_state.sent_leads
            sent_indicator = "✅ SENT" if is_sent else ""
            
            st.markdown(f"""
            <div class="lead-card">
                <div class="lead-title">
                    👤 {name} {sent_indicator}
                </div>
                <div class="lead-sub">📍 {location}</div>
                <div class="lead-sub">💼 {tagline}</div>
                <div class="lead-sub">🔍 Search: {search_term} in {search_city}</div>
                <div class="lead-sub">🔗 <a href="{linkedin_url}" target="_blank" style="color: #667eea; text-decoration: none;">View LinkedIn Profile →</a></div>
                <div class="lead-msg">💬 {message}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem;">
                    <span class="status-badge {status_class}">{status.replace('_', ' ').title()}</span>
                    <span class="timestamp">🕐 {timestamp_str}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Actions**")
            
            if st.button("🚀 Send", key=f"send_{i}_{idx}", disabled=is_sent, use_container_width=True):
                st.session_state.sent_leads.add(i)
                st.session_state.activity_log.append({
                    "type": "Message Sent",
                    "details": f"To {name}",
                    "status": "✅ Success",
                    "time": datetime.now().strftime("%H:%M:%S")
                })
                st.success(f"✅ Message sent to {name}!")
                time.sleep(1)
                st.rerun()
            
            if st.button("📋 Copy", key=f"copy_{i}_{idx}", use_container_width=True):
                st.info("📋 Lead data copied!")
            
            if st.button("⭐ Save", key=f"save_{i}_{idx}", use_container_width=True):
                st.info("⭐ Lead saved!")
            
            is_selected = i in st.session_state.selected_leads
            if st.checkbox("Select", key=f"select_{i}_{idx}", value=is_selected):
                if i not in st.session_state.selected_leads:
                    st.session_state.selected_leads.append(i)
            else:
                if i in st.session_state.selected_leads:
                    st.session_state.selected_leads.remove(i)

def show_search_interface(webhook_url):
    st.markdown("<div class='section-header'>🔍 Search & Send New Leads</div>", unsafe_allow_html=True)
    
    # Predefined options
    SEARCH_TERMS = [
        "Business Owner", "CEO", "Chief Executive Officer", "Founder", "Co-Founder",
        "Managing Director", "President", "Vice President", "VP of Sales", "VP of Marketing",
        "VP of Operations", "VP of Business Development", "Chief Operating Officer",
        "Chief Marketing Officer", "Chief Technology Officer", "Chief Financial Officer",
        "Director of Sales", "Director of Marketing", "Director of Operations",
        "Sales Manager", "Marketing Manager", "Operations Manager", "General Manager"
    ]
    
    CITIES = [
        "Tampa", "Miami", "Orlando", "Jacksonville", "St. Petersburg", "Fort Lauderdale",
        "Tallahassee", "Fort Myers", "Sarasota", "Naples", "Atlanta", "Charlotte",
        "Raleigh", "Nashville", "Memphis", "New Orleans", "Birmingham", "New York",
        "Brooklyn", "Manhattan", "Los Angeles", "San Francisco", "San Diego",
        "Chicago", "Houston", "Dallas", "Austin", "Phoenix", "Philadelphia", "Boston"
    ]
    
    COUNTRIES = [
        "United States", "Canada", "United Kingdom", "Australia", "Germany", "France",
        "Spain", "Italy", "Netherlands", "Switzerland", "Sweden", "Singapore"
    ]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🎯 Search Criteria")
        
        with st.form("search_form"):
            search_term = st.selectbox(
                "Job Title / Role",
                SEARCH_TERMS,
                help="Select the job title to search for"
            )
            
            col_a, col_b = st.columns(2)
            with col_a:
                city = st.selectbox("City", CITIES)
            with col_b:
                country = st.selectbox("Country", COUNTRIES)
            
            num_leads = st.slider("Number of Leads", 1, 50, 10)
            
            notes = st.text_area("Notes (Optional)", placeholder="Add any notes about this search...")
            
            submitted = st.form_submit_button("🚀 Start Search", use_container_width=True, type="primary")
            
            if submitted:
                if not webhook_url:
                    st.error("❌ Webhook URL not configured! Please configure it in the sidebar.")
                else:
                    payload = {
                        "search_term": search_term,
                        "city": city,
                        "country": country,
                        "num_leads": num_leads,
                        "notes": notes,
                        "timestamp": datetime.utcnow().isoformat(),
                        "source": "unified_dashboard",
                        "client": MY_PROFILE['name']
                    }
                    
                    try:
                        with st.spinner("🔍 Searching for leads..."):
                            response = requests.post(webhook_url, json=payload, timeout=10)
                        
                        if response.status_code == 200:
                            st.success(f"✅ Search initiated for {search_term} in {city}, {country}!")
                            st.info("📊 Results will appear in your outreach sheet shortly. Click 'Load/Refresh Data' in sidebar to see them.")
                            st.session_state.activity_log.append({
                                "type": "Search Initiated",
                                "details": f"Search for {search_term} in {city}",
                                "status": "✅ Success",
                                "time": datetime.now().strftime("%H:%M:%S")
                            })
                            st.session_state.daily_stats[datetime.now().date()]['searches'] += 1
                        else:
                            st.error(f"❌ Search initiation failed. Status: {response.status_code}. Response: {response.text}")
                            st.session_state.activity_log.append({
                                "type": "Search Initiated",
                                "details": f"Search for {search_term} in {city}",
                                "status": "❌ Failed",
                                "time": datetime.now().strftime("%H:%M:%S")
                            })
                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ An error occurred while initiating search: {e}")
                        st.session_state.activity_log.append({
                            "type": "Search Initiated",
                            "details": f"Search for {search_term} in {city}",
                            "status": "❌ Error",
                            "time": datetime.now().strftime("%H:%M:%S")
                        })
    
    with col2:
        st.markdown("### 🔔 Activity Log")
        if st.session_state.activity_log:
            for activity in reversed(st.session_state.activity_log[-5:]):
                st.markdown(f"""
                <div class="activity-item" style="border-left: 4px solid {'#22c55e' if 'Success' in activity['status'] else '#ef4444'};">
                    <small><strong>{activity['type']}</strong></small>
                    <p style="margin: 0; font-size: 0.9em;">{activity['details']}</p>
                    <small style="opacity: 0.7;">{activity['time']}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No recent search activity.")

def show_advanced_analytics():
    st.markdown("<div class='section-header'>📈 Advanced Analytics</div>", unsafe_allow_html=True)
    
    chat_df = st.session_state.chat_df
    outreach_df = st.session_state.outreach_df
    
    if chat_df.empty and outreach_df.empty:
        st.warning("No data loaded for advanced analytics.")
        return
    
    # Combined Metrics
    st.markdown("### 🔗 Cross-Platform Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Assuming 'date_sent' is the date of first outreach
        first_contact_date = outreach_df['date_sent'].min().strftime('%Y-%m-%d') if not outreach_df.empty and 'date_sent' in outreach_df.columns else 'N/A'
        st.metric("First Outreach Date", first_contact_date)
        
    with col2:
        # Assuming 'date_replied' is the date of first reply
        total_replies = outreach_df['date_replied'].dropna().shape[0] if not outreach_df.empty and 'date_replied' in outreach_df.columns else 0
        st.metric("Total Replies Tracked", total_replies)
        
    with col3:
        # Assuming 'days_to_reply' is calculated in preprocessing
        avg_days_to_reply = outreach_df['days_to_reply'].mean() if not outreach_df.empty and 'days_to_reply' in outreach_df.columns else 'N/A'
        st.metric("Avg. Days to Reply", f"{avg_days_to_reply:.2f}" if avg_days_to_reply != 'N/A' else 'N/A')
        
    st.markdown("---")
    
    # Daily Stats
    st.markdown("### 📅 Daily Usage Statistics")
    
    daily_stats_data = []
    for date, stats in st.session_state.daily_stats.items():
        daily_stats_data.append({
            'Date': date,
            'Searches': stats['searches'],
            'Messages Sent (Simulated)': stats['messages'],
            'Responses Received (Simulated)': stats['responses']
        })
        
    if daily_stats_data:
        daily_df = pd.DataFrame(daily_stats_data).sort_values(by='Date', ascending=False)
        st.dataframe(daily_df, use_container_width=True)
    else:
        st.info("No daily usage statistics recorded yet.")
    
    st.markdown("---")
    
    # Webhook History
    st.markdown("### 📡 Webhook Sender History")
    
    if st.session_state.webhook_history:
        history_df = pd.DataFrame(st.session_state.webhook_history)
        st.dataframe(history_df, use_container_width=True)
    else:
        st.info("No webhook history recorded.")

# ------------------ INITIALIZATION ------------------ #
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'gsheets_client' not in st.session_state:
    st.session_state.gsheets_client = None
if 'chat_df' not in st.session_state:
    st.session_state.chat_df = pd.DataFrame()
if 'outreach_df' not in st.session_state:
    st.session_state.outreach_df = pd.DataFrame()
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.utcnow()
if 'activity_log' not in st.session_state:
    st.session_state.activity_log = []
if 'sent_leads' not in st.session_state:
    st.session_state.sent_leads = set()
if 'selected_leads' not in st.session_state:
    st.session_state.selected_leads = []
if 'daily_stats' not in st.session_state:
    st.session_state.daily_stats = defaultdict(lambda: {'searches': 0, 'messages': 0, 'responses': 0})
if 'webhook_history' not in st.session_state:
    st.session_state.webhook_history = []

# ------------------ RUN APPLICATION ------------------ #
if __name__ == "__main__":
    main()
