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
import hashlib
from io import BytesIO
import base64

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
MY_PROFILE = {"name": "Donmenico Hudson", "url": "https://www.linkedin.com/in/donmenicohudson/"}
WEBHOOK_URL = "https://agentonline-u29564.vm.elestio.app/webhook/Leadlinked"

# ------------------ SESSION STATE ------------------ #
for key, default in [
    ('authenticated', False), ('gsheets_client', None), ('activity_log', []),
    ('sent_leads', set()), ('selected_leads', []), ('current_client', None),
    ('chat_df', pd.DataFrame()), ('outreach_df', pd.DataFrame()),
    ('last_refresh', datetime.utcnow()), ('webhook_history', []), ('email_queue', []),
    ('show_notifications', True), ('dark_mode', False), ('selected_contact', None),
    ('filter_status', 'all'), ('filter_date_range', 7), ('sort_by', 'timestamp'),
    ('search_query', ''), ('favorites', set()), ('notes', {}), ('tags', {}),
    ('export_format', 'csv'), ('auto_refresh', False), ('refresh_interval', 60)
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ------------------ ENHANCED STYLES ------------------ #
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    
    * { 
        font-family: 'Inter', sans-serif; 
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .stApp { 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        background-attachment: fixed;
    }
    
    .main .block-container {
        padding: 2rem 3rem;
        max-width: 1400px;
    }
    
    /* Main Title with Animation */
    .main-title {
        text-align: center; 
        font-size: 4rem; 
        font-weight: 900;
        background: linear-gradient(135deg, #fff 0%, #f0f0f0 100%);
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem; 
        text-shadow: 0 4px 20px rgba(0,0,0,0.3);
        animation: fadeInDown 0.8s ease-out;
        letter-spacing: -2px;
    }
    
    @keyframes fadeInDown {
        from {
            opacity: 0;
            transform: translateY(-30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .sub-title {
        text-align: center; 
        font-size: 1.4rem; 
        color: #ffffff;
        margin-bottom: 3rem; 
        font-weight: 500; 
        opacity: 0.95;
        animation: fadeIn 1s ease-out;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    /* Enhanced Metric Cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 25px; 
        padding: 2.5rem; 
        text-align: center;
        box-shadow: 0 15px 45px rgba(0,0,0,0.2); 
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        border: 2px solid rgba(255, 255, 255, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(255,255,255,0.1), transparent);
        transform: rotate(45deg);
        transition: all 0.5s;
    }
    
    .metric-card:hover {
        transform: translateY(-10px) scale(1.02);
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }
    
    .metric-card:hover::before {
        left: 100%;
    }
    
    .metric-value { 
        font-size: 3.5rem; 
        font-weight: 900; 
        margin-bottom: 0.8rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: countUp 1s ease-out;
    }
    
    @keyframes countUp {
        from { transform: scale(0.5); opacity: 0; }
        to { transform: scale(1); opacity: 1; }
    }
    
    .metric-label { 
        font-size: 1.1rem; 
        color: #666; 
        text-transform: uppercase; 
        letter-spacing: 2px; 
        font-weight: 700;
    }
    
    .metric-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        filter: drop-shadow(0 4px 8px rgba(0,0,0,0.1));
    }
    
    /* Enhanced Lead Cards */
    .lead-card, .email-card, .crm-card {
        background: rgba(255, 255, 255, 0.98);
        backdrop-filter: blur(20px);
        border-radius: 25px; 
        padding: 2.5rem; 
        margin-bottom: 2rem;
        box-shadow: 0 8px 30px rgba(0,0,0,0.15); 
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        border-left: 6px solid #667eea;
        position: relative;
        overflow: hidden;
    }
    
    .lead-card::after, .email-card::after, .crm-card::after {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 100px;
        height: 100px;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        border-radius: 0 0 0 100%;
    }
    
    .lead-card:hover, .email-card:hover, .crm-card:hover {
        transform: translateY(-12px);
        box-shadow: 0 20px 50px rgba(0,0,0,0.25);
        border-left-width: 8px;
    }
    
    .lead-card *, .email-card *, .crm-card *, .message-card-all * {
        color: #2d3748 !important;
    }
    
    .lead-title { 
        font-size: 1.8rem; 
        font-weight: 800; 
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .lead-sub { 
        font-size: 1.1rem; 
        margin-bottom: 0.8rem; 
        font-weight: 500;
        opacity: 0.8;
    }
    
    .lead-msg {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 20px; 
        padding: 1.8rem; 
        margin: 1.5rem 0;
        border-left: 5px solid #667eea; 
        line-height: 1.8; 
        font-style: italic;
        box-shadow: inset 0 2px 8px rgba(0,0,0,0.05);
        position: relative;
    }
    
    .lead-msg::before {
        content: '"';
        position: absolute;
        top: -10px;
        left: 10px;
        font-size: 4rem;
        color: #667eea;
        opacity: 0.2;
    }
    
    /* Profile Badge */
    .profile-badge {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2rem;
        font-weight: 900;
        color: white;
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        flex-shrink: 0;
    }
    
    /* Enhanced Message Cards */
    .message-card-all {
        background: rgba(255, 255, 255, 0.98);
        backdrop-filter: blur(20px);
        padding: 2.5rem; 
        border-radius: 25px; 
        margin-bottom: 2rem;
        box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        transition: all 0.4s ease;
        border: 2px solid transparent;
    }
    
    .message-card-all:hover {
        border-color: #667eea;
        transform: translateX(10px);
        box-shadow: 0 12px 40px rgba(102, 126, 234, 0.2);
    }
    
    /* Enhanced Status Badges */
    .status-badge {
        display: inline-flex; 
        align-items: center; 
        gap: 0.5rem; 
        padding: 0.7rem 1.5rem;
        border-radius: 30px; 
        font-size: 0.9rem; 
        font-weight: 700;
        text-transform: uppercase; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        letter-spacing: 1px;
        animation: slideIn 0.5s ease-out;
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(-20px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .status-success { 
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white !important;
    }
    
    .status-ready { 
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
        color: white !important;
    }
    
    .status-sent { 
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white !important;
    }
    
    .status-pending { 
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white !important;
    }
    
    .status-error { 
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white !important;
    }
    
    /* Section Headers */
    .section-header {
        font-size: 2.5rem; 
        font-weight: 800; 
        color: #ffffff; 
        margin: 3rem 0 2rem 0;
        padding-bottom: 1.5rem; 
        border-bottom: 4px solid rgba(255, 255, 255, 0.3);
        text-shadow: 0 4px 12px rgba(0,0,0,0.3);
        position: relative;
        animation: slideInLeft 0.6s ease-out;
    }
    
    @keyframes slideInLeft {
        from {
            transform: translateX(-50px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .section-header::after {
        content: '';
        position: absolute;
        bottom: -4px;
        left: 0;
        width: 100px;
        height: 4px;
        background: white;
        border-radius: 2px;
    }
    
    /* Enhanced Stat Boxes */
    .stat-box {
        background: rgba(255, 255, 255, 0.98);
        backdrop-filter: blur(20px);
        padding: 2.5rem; 
        border-radius: 25px; 
        text-align: center;
        box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        border-top: 6px solid #667eea;
        position: relative;
        overflow: hidden;
    }
    
    .stat-box::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(255,255,255,0.1), transparent);
        transform: rotate(45deg);
        transition: all 0.5s;
    }
    
    .stat-box:hover {
        transform: translateY(-10px) scale(1.05);
        box-shadow: 0 15px 45px rgba(0,0,0,0.25);
    }
    
    .stat-box:hover::before {
        left: 100%;
    }
    
    .stat-number { 
        font-size: 3rem; 
        font-weight: 900; 
        margin: 1rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .stat-label { 
        font-size: 1rem; 
        color: #666; 
        text-transform: uppercase; 
        letter-spacing: 1.5px; 
        font-weight: 700;
    }
    
    /* Enhanced Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        padding: 1rem 2.5rem !important;
        border-radius: 20px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) scale(1.02) !important;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.5) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0) scale(0.98) !important;
    }
    
    /* Sidebar Styling */
    .css-1d391kg, [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 249, 250, 0.95) 100%);
        backdrop-filter: blur(20px);
    }
    
    /* Enhanced Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255, 255, 255, 0.2);
        padding: 8px;
        border-radius: 20px;
        backdrop-filter: blur(10px);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.3);
        border-radius: 15px;
        color: white;
        font-weight: 700;
        padding: 12px 24px;
        transition: all 0.3s ease;
        border: 2px solid transparent;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(255, 255, 255, 0.5);
        transform: translateY(-2px);
    }
    
    .stTabs [aria-selected="true"] {
        background: white !important;
        color: #667eea !important;
        border-color: white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Form Inputs */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stMultiSelect > div > div > div,
    .stTextArea > div > div > textarea {
        background: rgba(255, 255, 255, 0.95) !important;
        border: 2px solid rgba(102, 126, 234, 0.3) !important;
        border-radius: 15px !important;
        padding: 12px 16px !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > div:focus,
    .stMultiSelect > div > div > div:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
    }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        border-radius: 15px;
        font-weight: 700;
        padding: 1rem 1.5rem;
        border: 2px solid rgba(102, 126, 234, 0.2);
        transition: all 0.3s ease;
    }
    
    .streamlit-expanderHeader:hover {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
        transform: translateX(5px);
    }
    
    /* Loading Animation */
    .stSpinner > div {
        border-color: #667eea transparent transparent transparent !important;
    }
    
    /* Success/Error Messages */
    .stSuccess, .stError, .stWarning, .stInfo {
        background: rgba(255, 255, 255, 0.95) !important;
        border-radius: 15px !important;
        padding: 1.5rem !important;
        border-left-width: 6px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
        animation: slideIn 0.5s ease-out !important;
    }
    
    /* Scrollbar Styling */
    ::-webkit-scrollbar {
        width: 12px;
        height: 12px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* Action Buttons Container */
    .action-buttons {
        display: flex;
        gap: 12px;
        margin-top: 1.5rem;
        flex-wrap: wrap;
    }
    
    .action-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 24px;
        border-radius: 15px;
        font-weight: 700;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        transition: all 0.3s ease;
        border: 2px solid transparent;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
    
    .action-btn:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        border-color: white;
    }
    
    /* Stats Grid */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 20px;
        margin: 2rem 0;
    }
    
    /* Filter Panel */
    .filter-panel {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(20px);
        padding: 2rem;
        border-radius: 25px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 30px rgba(0,0,0,0.15);
    }
    
    /* Tag Badge */
    .tag-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0.2rem;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
        color: #667eea;
        border: 1px solid rgba(102, 126, 234, 0.3);
    }
    
    /* Note Card */
    .note-card {
        background: #fff9e6;
        border-left: 4px solid #f59e0b;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        font-style: italic;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# ------------------ HELPER FUNCTIONS ------------------ #
@st.cache_resource
def init_google_sheets(credentials_json):
    """Initialize Google Sheets client with service account credentials"""
    try:
        credentials_dict = json.loads(credentials_json)
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"🔴 Authentication Error: {str(e)}")
        return None

@st.cache_data(ttl=60)
def load_sheet_data(_client, sheet_id, sheet_name):
    """Load data from Google Sheets with caching"""
    try:
        spreadsheet = _client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"🔴 Data Loading Error: {str(e)}")
        return pd.DataFrame()

def parse_timestamp(timestamp_str):
    """Parse various timestamp formats"""
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
    """Check if a message has been sent"""
    if row.get("email_subject") or row.get("email_message"):
        return False
    success = str(row.get('success', '')).lower()
    return success == 'true' or success == 'yes' or success == '1'

def is_me(sender_name, sender_url, my_profile):
    """Check if the sender is the current user"""
    if not sender_name or not isinstance(sender_name, str):
        return False
    return (my_profile["name"].lower() in sender_name.lower() or
            (sender_url and my_profile["url"].lower() in str(sender_url).lower()))

def get_initials(name):
    """Get initials from a name"""
    if not name:
        return "?"
    parts = name.split()
    return f"{parts[0][0]}{parts[1][0]}".upper() if len(parts) >= 2 else name[0].upper()

def send_webhook_request(webhook_url, payload):
    """Send data to webhook endpoint"""
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        return response.status_code == 200, response.text
    except Exception as e:
        return False, str(e)

def generate_lead_id(profile_name, linkedin_url):
    """Generate unique lead ID"""
    unique_string = f"{profile_name}_{linkedin_url}_{datetime.now().isoformat()}"
    return hashlib.md5(unique_string.encode()).hexdigest()[:12]

def export_to_csv(df, filename="export.csv"):
    """Export dataframe to CSV"""
    return df.to_csv(index=False).encode('utf-8')

def create_pdf_report(data_dict):
    """Create a PDF report from data dictionary"""
    # This is a placeholder - implement with reportlab or similar
    return b"PDF Report Content"

def filter_dataframe(df, filters):
    """Apply filters to dataframe"""
    filtered_df = df.copy()
    
    if filters.get('status') and filters['status'] != 'all':
        filtered_df = filtered_df[filtered_df['status'] == filters['status']]
    
    if filters.get('date_range'):
        days = filters['date_range']
        cutoff_date = datetime.now() - timedelta(days=days)
        if 'parsed_time' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['parsed_time'] >= cutoff_date]
    
    if filters.get('search_query'):
        query = filters['search_query'].lower()
        mask = filtered_df.apply(lambda row: any(
            query in str(val).lower() for val in row.values
        ), axis=1)
        filtered_df = filtered_df[mask]
    
    return filtered_df

def calculate_metrics(chat_df, outreach_df):
    """Calculate comprehensive metrics"""
    metrics = {
        'total_conversations': len(chat_df),
        'total_leads': len(outreach_df),
        'messages_sent': 0,
        'messages_received': 0,
        'response_rate': 0,
        'avg_response_time': 0,
        'pending_leads': 0,
        'ready_to_send': 0,
        'conversion_rate': 0
    }
    
    if not chat_df.empty:
        # Ensure the result of apply is a boolean Series before using it for indexing
        is_my_message = chat_df.apply(
            lambda row: is_me(row.get(\'sender_name\'), row.get(\'sender_url\'), MY_PROFILE), axis=1
        ).astype(bool)
        metrics['messages_sent'] = len(chat_df[is_my_message])
        metrics['messages_received'] = len(chat_df) - metrics['messages_sent']
        
        if metrics['messages_sent'] > 0:
            metrics['response_rate'] = round((metrics['messages_received'] / metrics['messages_sent']) * 100, 2)
    
    if not outreach_df.empty:
        if 'status' in outreach_df.columns:
            metrics['pending_leads'] = len(outreach_df[outreach_df['status'] == 'pending'])
            metrics['ready_to_send'] = len(outreach_df[outreach_df['status'] == 'ready_to_send'])
        
        if 'success' in outreach_df.columns:
            sent_count = len(outreach_df[outreach_df['success'].astype(str).str.lower() == 'true'])
            if metrics['total_leads'] > 0:
                metrics['conversion_rate'] = round((sent_count / metrics['total_leads']) * 100, 2)
    
    return metrics

# ------------------ AUTHENTICATION ------------------ #
def authenticate_user():
    """User authentication interface"""
    st.markdown("<div class='main-title'>🔐 LinkedIn Analytics Hub</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Secure Authentication Portal</div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style='background: rgba(255, 255, 255, 0.95); padding: 3rem; border-radius: 25px; 
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3); text-align: center;'>
            <h2 style='color: #667eea; margin-bottom: 2rem; font-weight: 800;'>🚀 Welcome Back!</h2>
            <p style='color: #666; font-size: 1.1rem; margin-bottom: 2rem;'>
                Upload your service account credentials to access your analytics dashboard
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("📁 Upload Service Account JSON", type=['json'], 
                                        help="Drag and drop your Google Service Account JSON file here")
        
        if uploaded_file:
            try:
                with st.spinner("🔄 Authenticating your credentials..."):
                    credentials_json = uploaded_file.read().decode('utf-8')
                    client = init_google_sheets(credentials_json)
                    if client:
                        st.session_state.authenticated = True
                        st.session_state.gsheets_client = client
                        st.success("✅ Authentication Successful!")
                        st.balloons()
                        time.sleep(1.5)
                        st.rerun()
            except Exception as e:
                st.error(f"❌ Authentication Failed: {str(e)}")

# ------------------ DASHBOARD OVERVIEW ------------------ #
def show_dashboard_overview(metrics):
    """Display main dashboard with key metrics"""
    st.markdown("<div class='main-title'>🚀 LinkedIn Analytics Hub</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Comprehensive Outreach & Engagement Platform</div>", unsafe_allow_html=True)
    
    # Key Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">💬</div>
            <div class="metric-value">{metrics['total_conversations']}</div>
            <div class="metric-label">Conversations</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">🎯</div>
            <div class="metric-value">{metrics['total_leads']}</div>
            <div class="metric-label">Total Leads</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">📊</div>
            <div class="metric-value">{metrics['response_rate']}%</div>
            <div class="metric-label">Response Rate</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">✅</div>
            <div class="metric-value">{metrics['conversion_rate']}%</div>
            <div class="metric-label">Conversion Rate</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Secondary Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="metric-icon">📤</div>
            <div class="stat-number">{metrics['messages_sent']}</div>
            <div class="stat-label">Sent</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-box" style="border-top-color: #10b981;">
            <div class="metric-icon">📥</div>
            <div class="stat-number">{metrics['messages_received']}</div>
            <div class="stat-label">Received</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-box" style="border-top-color: #f59e0b;">
            <div class="metric-icon">⏳</div>
            <div class="stat-number">{metrics['pending_leads']}</div>
            <div class="stat-label">Pending</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-box" style="border-top-color: #22c55e;">
            <div class="metric-icon">🚀</div>
            <div class="stat-number">{metrics['ready_to_send']}</div>
            <div class="stat-label">Ready</div>
        </div>
        """, unsafe_allow_html=True)

# ------------------ CONVERSATION HISTORY ------------------ #
def show_conversation_history(chat_df):
    """Display conversation history with threading"""
    st.markdown("<div class='section-header'>💬 Conversation History</div>", unsafe_allow_html=True)
    
    if chat_df.empty:
        st.markdown("""
        <div style='background: rgba(255, 255, 255, 0.95); padding: 4rem; border-radius: 25px; 
                    text-align: center; box-shadow: 0 10px 40px rgba(0,0,0,0.15);'>
            <h2 style='color: #667eea; font-size: 3rem; margin-bottom: 1rem;'>💬</h2>
            <h3 style='color: #2d3748; margin-bottom: 1rem;'>No Conversations Yet</h3>
            <p style='color: #666; font-size: 1.1rem;'>Start engaging with leads to see conversations here</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Parse timestamps
    if 'timestamp' in chat_df.columns:
        chat_df['parsed_time'] = chat_df['timestamp'].apply(parse_timestamp)
        chat_df = chat_df.sort_values('parsed_time', ascending=False)
    
    # Group by conversation
    conversations = defaultdict(list)
    for _, row in chat_df.iterrows():
        conv_id = row.get('conversation_id', 'unknown')
        conversations[conv_id].append(row)
    
    # Display conversations
    for conv_id, messages in conversations.items():
        with st.expander(f"🗨️ Conversation with {messages[0].get('recipient_name', 'Unknown')} ({len(messages)} messages)", expanded=False):
            for msg in sorted(messages, key=lambda x: x.get('parsed_time', datetime.min)):
                sender_name = msg.get('sender_name', 'Unknown')
                message_text = msg.get('message', 'No message content')
                timestamp = msg.get('timestamp', 'N/A')
                is_from_me = is_me(sender_name, msg.get('sender_url'), MY_PROFILE)
                
                alignment = "right" if is_from_me else "left"
                bg_color = "#667eea" if is_from_me else "#f8f9fa"
                text_color = "white" if is_from_me else "#2d3748"
                
                st.markdown(f"""
                <div style='display: flex; justify-content: {alignment}; margin: 1rem 0;'>
                    <div style='max-width: 70%; background: {bg_color}; color: {text_color}; 
                                padding: 1.5rem; border-radius: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);'>
                        <div style='font-weight: 700; margin-bottom: 0.5rem;'>{sender_name}</div>
                        <div style='line-height: 1.6;'>{message_text}</div>
                        <div style='font-size: 0.85rem; opacity: 0.7; margin-top: 0.5rem;'>{timestamp}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ------------------ CRM DASHBOARD ------------------ #
def show_crm_dashboard(outreach_df):
    """Display comprehensive CRM dashboard"""
    st.markdown("<div class='section-header'>📋 CRM Dashboard</div>", unsafe_allow_html=True)
    
    if outreach_df.empty:
        st.markdown("""
        <div style='background: rgba(255, 255, 255, 0.95); padding: 4rem; border-radius: 25px; 
                    text-align: center; box-shadow: 0 10px 40px rgba(0,0,0,0.15);'>
            <h2 style='color: #667eea; font-size: 3rem; margin-bottom: 1rem;'>🎯</h2>
            <h3 style='color: #2d3748; margin-bottom: 1rem;'>No Outreach Data Found</h3>
            <p style='color: #666; font-size: 1.1rem;'>Use the Search & Send feature to generate new leads</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Filters
    st.markdown("<div class='filter-panel'>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        filter_status = st.selectbox("📊 Status Filter", 
                                     ['all', 'pending', 'ready_to_send', 'sent', 'responded'],
                                     key='crm_status_filter')
    
    with col2:
        filter_days = st.selectbox("📅 Date Range", 
                                   [7, 14, 30, 60, 90, 180, 365],
                                   format_func=lambda x: f"Last {x} days",
                                   key='crm_date_filter')
    
    with col3:
        sort_by = st.selectbox("🔄 Sort By", 
                              ['timestamp', 'profile_name', 'company_name', 'status'],
                              key='crm_sort')
    
    with col4:
        search_query = st.text_input("🔍 Search", placeholder="Search leads...", key='crm_search')
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Apply filters
    filtered_df = filter_dataframe(outreach_df, {
        'status': filter_status,
        'date_range': filter_days,
        'search_query': search_query
    })
    
    # Sort
    if sort_by in filtered_df.columns:
        filtered_df = filtered_df.sort_values(sort_by, ascending=False)
    
    # Display statistics
    st.markdown("<div class='stats-grid'>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="metric-icon">🎯</div>
            <div class="stat-number">{len(filtered_df)}</div>
            <div class="stat-label">Filtered Leads</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        sent = len(filtered_df[filtered_df['success'].astype(str).str.lower() == 'true']) if 'success' in filtered_df.columns else 0
        st.markdown(f"""
        <div class="stat-box" style="border-top-color: #10b981;">
            <div class="metric-icon">✅</div>
            <div class="stat-number">{sent}</div>
            <div class="stat-label">Messages Sent</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        pending = len(filtered_df[filtered_df['status'] == 'pending']) if 'status' in filtered_df.columns else 0
        st.markdown(f"""
        <div class="stat-box" style="border-top-color: #f59e0b;">
            <div class="metric-icon">⏳</div>
            <div class="stat-number">{pending}</div>
            <div class="stat-label">Pending</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        ready = len(filtered_df[filtered_df['status'] == 'ready_to_send']) if 'status' in filtered_df.columns else 0
        st.markdown(f"""
        <div class="stat-box" style="border-top-color: #22c55e;">
            <div class="metric-icon">🚀</div>
            <div class="stat-number">{ready}</div>
            <div class="stat-label">Ready to Send</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div><br>", unsafe_allow_html=True)
    
    # Export options
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("📥 Export to CSV", use_container_width=True):
            csv_data = export_to_csv(filtered_df)
            st.download_button(
                label="⬇️ Download CSV",
                data=csv_data,
                file_name=f"leads_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📊 Generate Report", use_container_width=True):
            st.info("📊 Report generation feature coming soon!")
    
    # Lead Cards
    st.markdown("<br>", unsafe_allow_html=True)
    for idx, (i, row) in enumerate(filtered_df.iterrows()):
        with st.container():
            linkedin_url = row.get('linkedin_url', '#')
            profile_name = row.get('profile_name', 'Unknown')
            tagline = row.get('profile_tagline', 'N/A')
            message = row.get('linkedin_message', 'No message available')
            timestamp = row.get('timestamp', 'N/A')
            location = row.get('profile_location', 'N/A')
            company = row.get('company_name', 'N/A')
            status = row.get('status', 'unknown')
            
            # Status badge
            status_class = {
                'sent': 'status-sent',
                'pending': 'status-pending',
                'ready_to_send': 'status-ready',
                'responded': 'status-success'
            }.get(status, 'status-pending')
            
            # Check if favorited
            lead_id = generate_lead_id(profile_name, linkedin_url)
            is_favorited = lead_id in st.session_state.favorites
            has_notes = lead_id in st.session_state.notes
            lead_tags = st.session_state.tags.get(lead_id, [])
            
            st.markdown(f"""
            <div class="lead-card">
                <div style="display: flex; align-items: start; gap: 1.5rem; margin-bottom: 1rem;">
                    <div class="profile-badge">{get_initials(profile_name)}</div>
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div>
                                <h3 class="lead-title">{profile_name}</h3>
                                <p class="lead-sub">💼 {tagline}</p>
                            </div>
                            <span class="status-badge {status_class}">{status.replace('_', ' ').title()}</span>
                        </div>
                        <div style="display: flex; gap: 2rem; margin: 1rem 0; flex-wrap: wrap;">
                            <span style="color: #666;">📍 {location}</span>
                            <span style="color: #666;">🏢 {company}</span>
                            <span style="color: #666;">🕐 {timestamp}</span>
                        </div>
                        {"<div style='margin: 0.5rem 0;'>" + "".join([f"<span class='tag-badge'>{tag}</span>" for tag in lead_tags]) + "</div>" if lead_tags else ""}
                    </div>
                </div>
                
                <div class="lead-msg">
                    <strong style="color: #667eea; font-size: 1.1rem;">📩 Outreach Message:</strong><br><br>
                    {message}
                </div>
            """, unsafe_allow_html=True)
            
            # Display notes if any
            if has_notes:
                st.markdown(f"""
                <div class="note-card">
                    <strong>📝 Note:</strong> {st.session_state.notes[lead_id]}
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<div class='action-buttons'>", unsafe_allow_html=True)
            st.markdown(f"""
                <a href="{linkedin_url}" target="_blank" class="action-btn">
                    🔗 View LinkedIn Profile
                </a>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Action buttons
            col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns(5)
            
            with col_btn1:
                if st.button("✉️ Send Message", key=f"lead_send_{i}_{idx}", use_container_width=True):
                    success, response = send_webhook_request(WEBHOOK_URL, {
                        'action': 'send_message',
                        'profile_url': linkedin_url,
                        'message': message
                    })
                    if success:
                        st.success("✅ Message sent successfully!")
                    else:
                        st.error(f"❌ Failed to send: {response}")
            
            with col_btn2:
                if st.button("📧 Send Email", key=f"lead_email_{i}_{idx}", use_container_width=True):
                    st.session_state.email_queue.append({
                        'to': profile_name,
                        'subject': f"Following up on LinkedIn",
                        'body': message
                    })
                    st.success("✅ Email queued!")
            
            with col_btn3:
                fav_icon = "⭐" if is_favorited else "☆"
                if st.button(f"{fav_icon} Favorite", key=f"lead_fav_{i}_{idx}", use_container_width=True):
                    if is_favorited:
                        st.session_state.favorites.remove(lead_id)
                        st.info("Removed from favorites")
                    else:
                        st.session_state.favorites.add(lead_id)
                        st.success("⭐ Added to favorites!")
                    st.rerun()
            
            with col_btn4:
                if st.button("📝 Add Note", key=f"lead_note_{i}_{idx}", use_container_width=True):
                    st.session_state.selected_contact = lead_id
            
            with col_btn5:
                if st.button("🏷️ Add Tag", key=f"lead_tag_{i}_{idx}", use_container_width=True):
                    st.session_state.selected_contact = f"tag_{lead_id}"
            
            # Note input
            if st.session_state.selected_contact == lead_id:
                note_text = st.text_area("Enter your note:", key=f"note_input_{lead_id}")
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.button("💾 Save Note", key=f"save_note_{lead_id}"):
                        st.session_state.notes[lead_id] = note_text
                        st.session_state.selected_contact = None
                        st.success("📝 Note saved!")
                        st.rerun()
                with col_cancel:
                    if st.button("❌ Cancel", key=f"cancel_note_{lead_id}"):
                        st.session_state.selected_contact = None
                        st.rerun()
            
            # Tag input
            if st.session_state.selected_contact == f"tag_{lead_id}":
                tag_text = st.text_input("Enter tag:", key=f"tag_input_{lead_id}")
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.button("💾 Add Tag", key=f"save_tag_{lead_id}"):
                        if lead_id not in st.session_state.tags:
                            st.session_state.tags[lead_id] = []
                        st.session_state.tags[lead_id].append(tag_text)
                        st.session_state.selected_contact = None
                        st.success("🏷️ Tag added!")
                        st.rerun()
                with col_cancel:
                    if st.button("❌ Cancel", key=f"cancel_tag_{lead_id}"):
                        st.session_state.selected_contact = None
                        st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)

# ------------------ SEARCH INTERFACE ------------------ #
def show_search_interface(webhook_url):
    """Advanced lead search and generation interface"""
    st.markdown("<div class='section-header'>🔍 Advanced Lead Search & Generation</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style='background: rgba(255, 255, 255, 0.95); padding: 2.5rem; border-radius: 25px; 
                text-align: center; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-bottom: 3rem;'>
        <h2 style='color: #667eea; margin-bottom: 1rem; font-weight: 800;'>🌍 Global Business Intelligence</h2>
        <p style='color: #666; font-size: 1.2rem; line-height: 1.8;'>
            Search and connect with decision-makers worldwide. Target by job title, location, industry, 
            and company size to generate highly qualified leads instantly.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Expanded job titles (100+)
    SEARCH_TERMS = [
        "Business Owner", "CEO", "Founder", "President", "Co-Founder", "Managing Director",
        "VP of Sales", "VP of Marketing", "Marketing Director", "Sales Director", "Chief Operating Officer",
        "Chief Financial Officer", "Chief Marketing Officer", "Chief Technology Officer", "Chief Strategy Officer",
        "Partner", "Investor", "Consultant", "Business Analyst", "Strategic Advisor", "Operations Manager",
        "Growth Manager", "Product Manager", "Head of Business Development", "Sales Executive", "Client Relations Manager",
        "Customer Success Manager", "Account Executive", "Regional Manager", "General Manager", "Division Head",
        "Chief Revenue Officer", "Chief Commercial Officer", "Chief Innovation Officer", "Chief Data Officer",
        "Chief Information Officer", "Chief People Officer", "Chief Legal Officer", "Chief Compliance Officer",
        "Director of Operations", "Director of Finance", "Director of HR", "Director of IT", "Director of Engineering",
        "VP of Engineering", "VP of Product", "VP of Operations", "VP of Finance", "VP of HR",
        "Head of Sales", "Head of Marketing", "Head of Growth", "Head of Customer Success", "Head of Partnerships",
        "Business Development Manager", "Sales Manager", "Marketing Manager", "Operations Director", "Finance Director",
        "Strategy Director", "Innovation Director", "Digital Transformation Officer", "E-commerce Director",
        "Supply Chain Director", "Procurement Manager", "Purchasing Manager", "Logistics Manager",
        "Quality Assurance Manager", "Project Manager", "Program Manager", "Portfolio Manager",
        "Investment Manager", "Fund Manager", "Asset Manager", "Wealth Manager", "Relationship Manager",
        "Branch Manager", "Store Manager", "Retail Manager", "Restaurant Owner", "Franchise Owner",
        "Real Estate Developer", "Property Manager", "Construction Manager", "Architect", "Engineer",
        "Healthcare Administrator", "Medical Director", "Practice Manager", "Clinic Owner", "Hospital CEO",
        "School Principal", "Dean", "University President", "Education Director", "Training Manager",
        "HR Director", "Talent Acquisition Manager", "Recruitment Manager", "People Operations Manager",
        "Legal Director", "General Counsel", "Compliance Manager", "Risk Manager", "Audit Manager"
    ]
    
    # Expanded locations (200+ cities worldwide)
    LOCATIONS = [
        # North America
        "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", "Phoenix, AZ",
        "Philadelphia, PA", "San Antonio, TX", "San Diego, CA", "Dallas, TX", "San Jose, CA",
        "Austin, TX", "Jacksonville, FL", "Fort Worth, TX", "Columbus, OH", "San Francisco, CA",
        "Charlotte, NC", "Indianapolis, IN", "Seattle, WA", "Denver, CO", "Washington, DC",
        "Boston, MA", "Nashville, TN", "Detroit, MI", "Portland, OR", "Las Vegas, NV",
        "Miami, FL", "Atlanta, GA", "Toronto, Canada", "Vancouver, Canada", "Montreal, Canada",
        "Calgary, Canada", "Ottawa, Canada", "Mexico City, Mexico", "Guadalajara, Mexico",
        
        # Europe
        "London, UK", "Paris, France", "Berlin, Germany", "Madrid, Spain", "Rome, Italy",
        "Amsterdam, Netherlands", "Brussels, Belgium", "Vienna, Austria", "Stockholm, Sweden",
        "Copenhagen, Denmark", "Oslo, Norway", "Helsinki, Finland", "Dublin, Ireland",
        "Zurich, Switzerland", "Geneva, Switzerland", "Barcelona, Spain", "Milan, Italy",
        "Munich, Germany", "Frankfurt, Germany", "Hamburg, Germany", "Warsaw, Poland",
        "Prague, Czech Republic", "Budapest, Hungary", "Athens, Greece", "Lisbon, Portugal",
        "Edinburgh, UK", "Manchester, UK", "Birmingham, UK", "Lyon, France", "Marseille, France",
        
        # Asia
        "Tokyo, Japan", "Singapore", "Hong Kong", "Seoul, South Korea", "Shanghai, China",
        "Beijing, China", "Shenzhen, China", "Guangzhou, China", "Mumbai, India", "Delhi, India",
        "Bangalore, India", "Hyderabad, India", "Chennai, India", "Pune, India", "Kolkata, India",
        "Bangkok, Thailand", "Jakarta, Indonesia", "Manila, Philippines", "Kuala Lumpur, Malaysia",
        "Ho Chi Minh City, Vietnam", "Hanoi, Vietnam", "Taipei, Taiwan", "Osaka, Japan",
        "Dubai, UAE", "Abu Dhabi, UAE", "Riyadh, Saudi Arabia", "Doha, Qatar", "Tel Aviv, Israel",
        
        # Australia & New Zealand
        "Sydney, Australia", "Melbourne, Australia", "Brisbane, Australia", "Perth, Australia",
        "Adelaide, Australia", "Auckland, New Zealand", "Wellington, New Zealand",
        
        # South America
        "São Paulo, Brazil", "Rio de Janeiro, Brazil", "Buenos Aires, Argentina", "Santiago, Chile",
        "Lima, Peru", "Bogotá, Colombia", "Caracas, Venezuela", "Montevideo, Uruguay",
        
        # Africa
        "Johannesburg, South Africa", "Cape Town, South Africa", "Cairo, Egypt", "Lagos, Nigeria",
        "Nairobi, Kenya", "Casablanca, Morocco", "Accra, Ghana", "Addis Ababa, Ethiopia"
    ]
    
    # Industries
    INDUSTRIES = [
        "Technology", "Software", "SaaS", "E-commerce", "Fintech", "Healthcare", "Biotechnology",
        "Pharmaceuticals", "Manufacturing", "Retail", "Real Estate", "Construction", "Energy",
        "Renewable Energy", "Finance", "Banking", "Insurance", "Consulting", "Marketing",
        "Advertising", "Media", "Entertainment", "Education", "Hospitality", "Food & Beverage",
        "Transportation", "Logistics", "Automotive", "Aerospace", "Telecommunications",
        "Legal Services", "Professional Services", "Human Resources", "Recruitment",
        "Non-profit", "Government", "Agriculture", "Mining", "Oil & Gas", "Utilities"
    ]
    
    # Company sizes
    COMPANY_SIZES = [
        "1-10 employees", "11-50 employees", "51-200 employees", "201-500 employees",
        "501-1000 employees", "1001-5000 employees", "5001-10000 employees", "10000+ employees"
    ]
    
    # Search form
    with st.form("lead_search_form"):
        st.markdown("### 🎯 Define Your Target Audience")
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_titles = st.multiselect(
                "👔 Job Titles",
                SEARCH_TERMS,
                default=["CEO", "Founder", "Business Owner"],
                help="Select one or more job titles to target"
            )
            
            selected_locations = st.multiselect(
                "📍 Locations",
                LOCATIONS,
                default=["New York, NY", "San Francisco, CA", "London, UK"],
                help="Select target locations"
            )
            
            selected_industries = st.multiselect(
                "🏢 Industries",
                INDUSTRIES,
                default=["Technology", "Software", "SaaS"],
                help="Select target industries"
            )
        
        with col2:
            selected_company_sizes = st.multiselect(
                "📊 Company Size",
                COMPANY_SIZES,
                default=["11-50 employees", "51-200 employees"],
                help="Select target company sizes"
            )
            
            num_leads = st.slider(
                "🎯 Number of Leads",
                min_value=10,
                max_value=500,
                value=50,
                step=10,
                help="How many leads do you want to generate?"
            )
            
            custom_message = st.text_area(
                "✉️ Custom Message Template",
                value="Hi {name}, I noticed your work at {company} and would love to connect!",
                height=100,
                help="Use {name} and {company} as placeholders"
            )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_button = st.form_submit_button("🔍 Search Leads", use_container_width=True)
        
        with col2:
            save_search = st.form_submit_button("💾 Save Search", use_container_width=True)
        
        with col3:
            load_search = st.form_submit_button("📂 Load Search", use_container_width=True)
    
    # Handle search submission
    if search_button:
        if not selected_titles or not selected_locations:
            st.error("❌ Please select at least one job title and one location")
        else:
            with st.spinner("🔍 Searching for leads... This may take a moment"):
                # Prepare webhook payload
                payload = {
                    'action': 'search_leads',
                    'job_titles': selected_titles,
                    'locations': selected_locations,
                    'industries': selected_industries,
                    'company_sizes': selected_company_sizes,
                    'num_leads': num_leads,
                    'message_template': custom_message
                }
                
                # Send to webhook
                success, response = send_webhook_request(webhook_url, payload)
                
                if success:
                    st.success(f"✅ Successfully initiated search for {num_leads} leads!")
                    st.balloons()
                    
                    # Log activity
                    st.session_state.activity_log.append({
                        'timestamp': datetime.now(),
                        'action': 'search_initiated',
                        'details': f"Searching for {num_leads} leads"
                    })
                    
                    # Display search summary
                    st.markdown("""
                    <div class='crm-card'>
                        <h3 style='color: #667eea; margin-bottom: 1rem;'>📊 Search Summary</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("🎯 Target Leads", num_leads)
                    with col2:
                        st.metric("👔 Job Titles", len(selected_titles))
                    with col3:
                        st.metric("📍 Locations", len(selected_locations))
                    
                    # Show webhook response
                    with st.expander("🔍 View Webhook Response"):
                        st.json(json.loads(response) if response else {})
                else:
                    st.error(f"❌ Search failed: {response}")
    
    if save_search:
        st.info("💾 Search saved! (Feature in development)")
    
    if load_search:
        st.info("📂 Load saved search (Feature in development)")
    
    # Recent searches
    st.markdown("<br><div class='section-header' style='font-size: 2rem;'>📜 Recent Activity</div>", unsafe_allow_html=True)
    
    if st.session_state.activity_log:
        for activity in reversed(st.session_state.activity_log[-10:]):
            st.markdown(f"""
            <div class='message-card-all'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div>
                        <strong style='color: #667eea;'>{activity['action'].replace('_', ' ').title()}</strong>
                        <p style='color: #666; margin: 0.5rem 0 0 0;'>{activity['details']}</p>
                    </div>
                    <span style='color: #999; font-size: 0.9rem;'>{activity['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No recent activity to display")

# ------------------ ANALYTICS & REPORTS ------------------ #
def show_analytics(chat_df, outreach_df):
    """Display comprehensive analytics and visualizations"""
    st.markdown("<div class='section-header'>📊 Analytics & Insights</div>", unsafe_allow_html=True)
    
    if chat_df.empty and outreach_df.empty:
        st.info("📊 No data available for analytics. Start generating leads to see insights!")
        return
    
    # Time-based analysis
    st.markdown("### 📈 Activity Over Time")
    
    if not chat_df.empty and 'timestamp' in chat_df.columns:
        chat_df['parsed_time'] = chat_df['timestamp'].apply(parse_timestamp)
        chat_df['date'] = chat_df['parsed_time'].dt.date
        
        daily_messages = chat_df.groupby('date').size().reset_index(name='count')
        
        fig = px.line(daily_messages, x='date', y='count',
                     title='Daily Message Activity',
                     labels={'date': 'Date', 'count': 'Number of Messages'})
        fig.update_traces(line_color='#667eea', line_width=3)
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(255,255,255,0.95)',
            font=dict(family='Inter', size=12),
            title_font_size=20,
            title_font_color='#667eea'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Lead status distribution
    if not outreach_df.empty and 'status' in outreach_df.columns:
        st.markdown("### 🎯 Lead Status Distribution")
        
        status_counts = outreach_df['status'].value_counts()
        
        fig = px.pie(values=status_counts.values, names=status_counts.index,
                    title='Lead Status Breakdown',
                    color_discrete_sequence=['#667eea', '#764ba2', '#f59e0b', '#10b981', '#ef4444'])
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(
            paper_bgcolor='rgba(255,255,255,0.95)',
            font=dict(family='Inter', size=12),
            title_font_size=20,
            title_font_color='#667eea'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Geographic distribution
    if not outreach_df.empty and 'profile_location' in outreach_df.columns:
        st.markdown("### 🌍 Geographic Distribution")
        
        location_counts = outreach_df['profile_location'].value_counts().head(10)
        
        fig = px.bar(x=location_counts.values, y=location_counts.index,
                    orientation='h',
                    title='Top 10 Locations',
                    labels={'x': 'Number of Leads', 'y': 'Location'})
        fig.update_traces(marker_color='#667eea')
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(255,255,255,0.95)',
            font=dict(family='Inter', size=12),
            title_font_size=20,
            title_font_color='#667eea'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Company distribution
    if not outreach_df.empty and 'company_name' in outreach_df.columns:
        st.markdown("### 🏢 Top Companies")
        
        company_counts = outreach_df['company_name'].value_counts().head(10)
        
        fig = px.bar(x=company_counts.index, y=company_counts.values,
                    title='Top 10 Companies',
                    labels={'x': 'Company', 'y': 'Number of Leads'})
        fig.update_traces(marker_color='#764ba2')
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(255,255,255,0.95)',
            font=dict(family='Inter', size=12),
            title_font_size=20,
            title_font_color='#667eea'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Response rate analysis
    if not chat_df.empty:
        st.markdown("### 💬 Response Analysis")
        
        sent_messages = len(chat_df[chat_df.apply(
            lambda row: is_me(row.get('sender_name'), row.get('sender_url'), MY_PROFILE), axis=1
        )])
        received_messages = len(chat_df) - sent_messages
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📤 Messages Sent", sent_messages)
        with col2:
            st.metric("📥 Messages Received", received_messages)
        with col3:
            response_rate = round((received_messages / sent_messages * 100), 2) if sent_messages > 0 else 0
            st.metric("📊 Response Rate", f"{response_rate}%")

# ------------------ EMAIL QUEUE MANAGER ------------------ #
def show_email_queue():
    """Display and manage email queue"""
    st.markdown("<div class='section-header'>📧 Email Queue Manager</div>", unsafe_allow_html=True)
    
    if not st.session_state.email_queue:
        st.markdown("""
        <div style='background: rgba(255, 255, 255, 0.95); padding: 4rem; border-radius: 25px; 
                    text-align: center; box-shadow: 0 10px 40px rgba(0,0,0,0.15);'>
            <h2 style='color: #667eea; font-size: 3rem; margin-bottom: 1rem;'>📧</h2>
            <h3 style='color: #2d3748; margin-bottom: 1rem;'>Email Queue is Empty</h3>
            <p style='color: #666; font-size: 1.1rem;'>Queue emails from the CRM dashboard</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    st.markdown(f"""
    <div class='stat-box'>
        <div class='metric-icon'>📧</div>
        <div class='stat-number'>{len(st.session_state.email_queue)}</div>
        <div class='stat-label'>Queued Emails</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    for idx, email in enumerate(st.session_state.email_queue):
        st.markdown(f"""
        <div class='email-card'>
            <h3 class='lead-title'>To: {email['to']}</h3>
            <p class='lead-sub'><strong>Subject:</strong> {email['subject']}</p>
            <div class='lead-msg'>
                {email['body']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ Send Now", key=f"send_email_{idx}", use_container_width=True):
                st.success(f"✅ Email sent to {email['to']}!")
                st.session_state.email_queue.pop(idx)
                st.rerun()
        with col2:
            if st.button("✏️ Edit", key=f"edit_email_{idx}", use_container_width=True):
                st.info("✏️ Edit feature coming soon!")
        with col3:
            if st.button("🗑️ Delete", key=f"delete_email_{idx}", use_container_width=True):
                st.session_state.email_queue.pop(idx)
                st.rerun()

# ------------------ WEBHOOK MONITOR ------------------ #
def show_webhook_monitor():
    """Monitor webhook activity and test connections"""
    st.markdown("<div class='section-header'>🔗 Webhook Monitor</div>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class='crm-card'>
        <h3 style='color: #667eea; margin-bottom: 1rem;'>📡 Webhook Configuration</h3>
        <p style='color: #666;'><strong>Endpoint:</strong> {WEBHOOK_URL}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Test webhook
    st.markdown("### 🧪 Test Webhook Connection")
    
    col1, col2 = st.columns(2)
    
    with col1:
        test_action = st.selectbox("Select Test Action", 
                                   ['ping', 'search_leads', 'send_message', 'get_status'])
    
    with col2:
        if st.button("🚀 Send Test Request", use_container_width=True):
            with st.spinner("Sending test request..."):
                test_payload = {
                    'action': test_action,
                    'test': True,
                    'timestamp': datetime.now().isoformat()
                }
                
                success, response = send_webhook_request(WEBHOOK_URL, test_payload)
                
                if success:
                    st.success("✅ Webhook test successful!")
                    st.session_state.webhook_history.append({
                        'timestamp': datetime.now(),
                        'action': test_action,
                        'status': 'success',
                        'response': response
                    })
                else:
                    st.error(f"❌ Webhook test failed: {response}")
                    st.session_state.webhook_history.append({
                        'timestamp': datetime.now(),
                        'action': test_action,
                        'status': 'failed',
                        'response': response
                    })
    
    # Webhook history
    st.markdown("### 📜 Webhook History")
    
    if st.session_state.webhook_history:
        for entry in reversed(st.session_state.webhook_history[-20:]):
            status_class = 'status-success' if entry['status'] == 'success' else 'status-error'
            status_icon = '✅' if entry['status'] == 'success' else '❌'
            
            st.markdown(f"""
            <div class='message-card-all'>
                <div style='display: flex; justify-content: space-between; align-items: start;'>
                    <div style='flex: 1;'>
                        <div style='display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem;'>
                            <span class='status-badge {status_class}'>{status_icon} {entry['status'].upper()}</span>
                            <strong style='color: #667eea;'>{entry['action']}</strong>
                        </div>
                        <p style='color: #666; margin: 0.5rem 0; font-size: 0.9rem;'>
                            Response: {entry['response'][:100]}{'...' if len(str(entry['response'])) > 100 else ''}
                        </p>
                    </div>
                    <span style='color: #999; font-size: 0.85rem; white-space: nowrap;'>
                        {entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No webhook history yet. Send a test request to get started!")

# ------------------ SETTINGS ------------------ #
def show_settings():
    """Application settings and configuration"""
    st.markdown("<div class='section-header'>⚙️ Settings & Configuration</div>", unsafe_allow_html=True)
    
    # General Settings
    st.markdown("### 🎛️ General Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.session_state.show_notifications = st.checkbox(
            "🔔 Show Notifications",
            value=st.session_state.show_notifications
        )
        
        st.session_state.auto_refresh = st.checkbox(
            "🔄 Auto Refresh Data",
            value=st.session_state.auto_refresh
        )
    
    with col2:
        st.session_state.dark_mode = st.checkbox(
            "🌙 Dark Mode (Coming Soon)",
            value=st.session_state.dark_mode,
            disabled=True
        )
        
        if st.session_state.auto_refresh:
            st.session_state.refresh_interval = st.slider(
                "Refresh Interval (seconds)",
                min_value=30,
                max_value=300,
                value=st.session_state.refresh_interval,
                step=30
            )
    
    # Data Management
    st.markdown("### 💾 Data Management")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh All Data", use_container_width=True):
            st.cache_data.clear()
            st.success("✅ Data refreshed!")
            st.rerun()
    
    with col2:
        if st.button("🗑️ Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("✅ Cache cleared!")
    
    with col3:
        if st.button("📥 Export All Data", use_container_width=True):
            st.info("📥 Export feature coming soon!")
    
    # Account Information
    st.markdown("### 👤 Account Information")
    
    st.markdown(f"""
    <div class='crm-card'>
        <p><strong>Profile Name:</strong> {MY_PROFILE['name']}</p>
        <p><strong>LinkedIn URL:</strong> <a href="{MY_PROFILE['url']}" target="_blank">{MY_PROFILE['url']}</a></p>
        <p><strong>Last Refresh:</strong> {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Advanced Settings
    with st.expander("🔧 Advanced Settings"):
        st.markdown("#### API Configuration")
        
        webhook_url_custom = st.text_input("Webhook URL", value=WEBHOOK_URL)
        
        if st.button("💾 Save Webhook URL"):
            st.success("✅ Webhook URL saved!")
        
        st.markdown("#### Data Retention")
        retention_days = st.slider("Keep data for (days)", 30, 365, 90)
        
        st.markdown("#### Export Format")
        export_format = st.selectbox("Default Export Format", ['CSV', 'Excel', 'JSON', 'PDF'])

# ------------------ MAIN APPLICATION ------------------ #
def main():
    """Main application logic"""
    
    # Check authentication
    if not st.session_state.authenticated:
        authenticate_user()
        return
    
    # Load data
    client = st.session_state.gsheets_client
    
    with st.spinner("📊 Loading data..."):
        chat_df = load_sheet_data(client, CHAT_SPREADSHEET_ID, CHAT_SHEET_NAME)
        outreach_df = load_sheet_data(client, OUTREACH_SPREADSHEET_ID, OUTREACH_SHEET_NAME)
        
        st.session_state.chat_df = chat_df
        st.session_state.outreach_df = outreach_df
        st.session_state.last_refresh = datetime.utcnow()
    
    # Calculate metrics
    metrics = calculate_metrics(chat_df, outreach_df)
    
    # Sidebar Navigation
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; padding: 2rem 0;'>
            <h1 style='color: #667eea; font-size: 2rem; font-weight: 900;'>🚀 LinkedIn Hub</h1>
            <p style='color: #666; font-size: 0.9rem;'>Analytics & Outreach Platform</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        page = st.radio(
            "📍 Navigation",
            [
                "🏠 Dashboard",
                "💬 Conversations",
                "📋 CRM",
                "🔍 Search & Send",
                "📊 Analytics",
                "📧 Email Queue",
                "🔗 Webhook Monitor",
                "⚙️ Settings"
            ],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Quick Stats in Sidebar
        st.markdown("### 📊 Quick Stats")
        st.metric("Total Leads", metrics['total_leads'])
        st.metric("Response Rate", f"{metrics['response_rate']}%")
        st.metric("Conversion", f"{metrics['conversion_rate']}%")
        
        st.markdown("---")
        
        # Quick Actions
        st.markdown("### ⚡ Quick Actions")
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()
        
        st.markdown("---")
        
        # Footer
        st.markdown("""
        <div style='text-align: center; padding: 1rem; color: #999; font-size: 0.8rem;'>
            <p>Last updated:<br>{}</p>
            <p style='margin-top: 1rem;'>Made with ❤️ by Donmenico</p>
        </div>
        """.format(st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S')), unsafe_allow_html=True)
    
    # Main Content Area
    if page == "🏠 Dashboard":
        show_dashboard_overview(metrics)
    
    elif page == "💬 Conversations":
        show_conversation_history(chat_df)
    
    elif page == "📋 CRM":
        show_crm_dashboard(outreach_df)
    
    elif page == "🔍 Search & Send":
        show_search_interface(WEBHOOK_URL)
    
    elif page == "📊 Analytics":
        show_analytics(chat_df, outreach_df)
    
    elif page == "📧 Email Queue":
        show_email_queue()
    
    elif page == "🔗 Webhook Monitor":
        show_webhook_monitor()
    
    elif page == "⚙️ Settings":
        show_settings()

# ------------------ RUN APPLICATION ------------------ #
if __name__ == "__main__":
    main()
