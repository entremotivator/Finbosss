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
MY_PROFILE = {"name": "Donmenico Hudson", "url": "https://www.linkedin.com/in/donmenicohudson/"}
WEBHOOK_URL = "https://agentonline-u29564.vm.elestio.app/webhook/Leadlinked"

# ------------------ SESSION STATE ------------------ #
for key, default in [
    ('authenticated', False), ('gsheets_client', None), ('activity_log', []),
    ('sent_leads', set()), ('selected_leads', []), ('current_client', None),
    ('chat_df', pd.DataFrame()), ('outreach_df', pd.DataFrame()),
    ('last_refresh', datetime.utcnow()), ('webhook_history', []), ('email_queue', [])
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ------------------ ENHANCED STYLES ------------------ #
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background: #f5f7fa; }
    
    .main-title {
        text-align: center; font-size: 3rem; font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem; text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .sub-title {
        text-align: center; font-size: 1.2rem; color: #000000;
        margin-bottom: 2rem; font-weight: 500; text-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px; padding: 2rem; color: white; text-align: center;
        box-shadow: 0 8px 25px rgba(0,0,0,0.2); transition: all 0.3s ease;
    }
    
    .metric-card:hover { transform: translateY(-5px); box-shadow: 0 12px 35px rgba(0,0,0,0.25); }
    .metric-value { font-size: 3rem; font-weight: 800; margin-bottom: 0.5rem; }
    .metric-label { font-size: 1rem; opacity: 0.95; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600; }
    
    .lead-card, .email-card, .crm-card {
        background: white; border-radius: 20px; padding: 2rem; margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15); transition: all 0.4s ease; border-left: 5px solid #667eea;
    }
    
    .lead-card:hover, .email-card:hover, .crm-card:hover {
        transform: translateY(-8px); box-shadow: 0 15px 35px rgba(0,0,0,0.2);
    }
    
    .lead-card *, .email-card *, .crm-card *, .message-card-all * {
        color: #000000 !important; text-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    .lead-title { font-size: 1.4rem; font-weight: 700; margin-bottom: 0.8rem; }
    .lead-sub { font-size: 1rem; margin-bottom: 0.6rem; font-weight: 500; }
    .lead-msg {
        background: #f8f9fa; border-radius: 15px; padding: 1.2rem; margin: 1.2rem 0;
        border-left: 4px solid #667eea; line-height: 1.6; font-style: italic;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .message-card-all {
        background: white; padding: 32px; border-radius: 20px; margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15); transition: all 0.3s ease;
    }
    
    .status-badge {
        display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.5rem 1.2rem;
        border-radius: 25px; font-size: 0.85rem; font-weight: 600;
        text-transform: uppercase; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .status-success { background: #10b981; color: white !important; }
    .status-ready { background: #22c55e; color: white !important; }
    .status-sent { background: #3b82f6; color: white !important; }
    .status-pending { background: #f59e0b; color: white !important; }
    .status-error { background: #ef4444; color: white !important; }
    
    .section-header {
        font-size: 1.8rem; font-weight: 700; color: #000000; margin: 2.5rem 0 1.5rem 0;
        padding-bottom: 0.8rem; border-bottom: 3px solid #667eea; text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .stat-box {
        background: white; padding: 30px; border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        text-align: center; border-top: 5px solid #667eea; transition: all 0.3s ease;
    }
    
    .stat-box:hover { transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.2); }
    
    .stat-number {
        font-size: 3em; font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    
    .stat-label { color: #000000; font-size: 1em; margin-top: 8px; font-weight: 500; }
    .crm-field { margin-bottom: 1rem; padding: 0.8rem; background: #f8f9fa; border-radius: 10px; }
    .crm-field strong { color: #667eea; margin-right: 0.5rem; }
    
    .contact-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px; border-radius: 20px; color: white; margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3); transition: all 0.3s ease; cursor: pointer;
    }
    
    .contact-card:hover { transform: translateY(-8px) scale(1.02); box-shadow: 0 15px 40px rgba(102, 126, 234, 0.4); }
    .profile-badge {
        width: 50px; height: 50px; border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        display: flex; align-items: center; justify-content: center;
        color: white; font-size: 1.5em; font-weight: 700; margin-right: 15px;
    }
    
    .timestamp {
        font-size: 0.9rem; color: #000000; text-align: right; font-weight: 500;
        background: rgba(0,0,0,0.05); padding: 0.3rem 0.8rem; border-radius: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ------------------ HELPER FUNCTIONS ------------------ #
@st.cache_resource
def init_google_sheets(credentials_json):
    try:
        credentials_dict = json.loads(credentials_json)
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

@st.cache_data(ttl=60)
def load_sheet_data(_client, sheet_id, sheet_name):
    try:
        spreadsheet = _client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        return pd.DataFrame(worksheet.get_all_records())
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return pd.DataFrame()

def parse_timestamp(timestamp_str):
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
    if row.get("email_subject") or row.get("email_message"):
        return False
    success = str(row.get('success', '')).lower()
    return success == 'true' or success == 'yes' or success == '1'

def is_me(sender_name, sender_url, my_profile):
    if not sender_name or not isinstance(sender_name, str):
        return False
    return (my_profile["name"].lower() in sender_name.lower() or
            (sender_url and my_profile["url"].lower() in str(sender_url).lower()))

def get_initials(name):
    if not name:
        return "?"
    parts = name.split()
    return f"{parts[0][0]}{parts[1][0]}".upper() if len(parts) >= 2 else name[0].upper()

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

# ------------------ CRM DASHBOARD ------------------ #
def show_crm_dashboard():
    st.markdown("<div class='section-header'>📋 CRM Dashboard - Complete Lead Details</div>", unsafe_allow_html=True)
    
    outreach_df = st.session_state.outreach_df.copy()
    if outreach_df.empty:
        st.warning("📭 No CRM data loaded.")
        return
    
    if 'timestamp' in outreach_df.columns:
        outreach_df['parsed_time'] = outreach_df['timestamp'].apply(parse_timestamp)
        outreach_df['date'] = outreach_df['parsed_time'].dt.date
        outreach_df['time'] = outreach_df['parsed_time'].dt.time
    
    st.markdown("### 🔍 Filter Leads")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        search = st.text_input("🔍 Search", placeholder="Name, location, etc.", key="crm_search")
    with col2:
        if 'date' in outreach_df.columns:
            dates = sorted(outreach_df['date'].dropna().unique())
            date_filter = st.selectbox("📅 Date", ["All"] + [str(d) for d in dates])
        else:
            date_filter = "All"
    with col3:
        success_filter = st.selectbox("✅ Success", ["All", "True", "False"], key="crm_success")
    with col4:
        if 'search_city' in outreach_df.columns:
            cities = ["All"] + sorted(outreach_df['search_city'].dropna().unique().tolist())
            city_filter = st.selectbox("🌆 City", cities, key="crm_city")
        else:
            city_filter = "All"
    
    filtered_df = outreach_df.copy()
    if search:
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        filtered_df = filtered_df[mask]
    if date_filter != "All" and 'date' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['date'].astype(str) == date_filter]
    if success_filter != "All" and 'success' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['success'].astype(str).str.lower() == success_filter.lower()]
    if city_filter != "All" and 'search_city' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['search_city'] == city_filter]
    
    st.markdown(f"**Showing {len(filtered_df)} of {len(outreach_df)} leads**")
    st.markdown("---")
    
    for idx, (i, row) in enumerate(filtered_df.iterrows()):
        with st.container():
            st.markdown(f'''
            <div class="crm-card">
                <h3 style="margin-bottom: 1rem; color: #667eea;">👤 {row.get('profile_name', row.get('name', 'Unknown'))}</h3>
            ''', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f'''
                <div class="crm-field"><strong>📍 Location:</strong> {row.get('profile_location', row.get('location', 'N/A'))}</div>
                <div class="crm-field"><strong>🏢 Company:</strong> {row.get('company_name', 'N/A')}</div>
                <div class="crm-field"><strong>🔗 Profile URL:</strong> <a href="{row.get('linkedin_url', '#')}" target="_blank">{row.get('linkedin_url', 'N/A').split('/in/')[-1].replace('/', '') if row.get('linkedin_url') else 'N/A'}</a></div>
                <div class="crm-field"><strong>💼 Tagline:</strong> {row.get('profile_tagline', row.get('tagline', 'N/A'))}</div>
                <div class="crm-field"><strong>🔍 Search Term:</strong> {row.get('search_term', 'N/A')}</div>
                <div class="crm-field"><strong>🌆 Search City:</strong> {row.get('search_city', 'N/A')}</div>
                <div class="crm-field"><strong>🌍 Search Country:</strong> {row.get('search_country', 'N/A')}</div>
                <div class="crm-field"><strong>📧 Email:</strong> {row.get('email', 'N/A')}</div>
                <div class="crm-field"><strong>📞 Phone:</strong> {row.get('phone_number', 'N/A')}</div>
                ''', unsafe_allow_html=True)
            
            with col2:
                success_badge = "status-success" if is_message_sent(row) else "status-error"
                st.markdown(f'''
                <div class="crm-field"><strong>🕐 Timestamp:</strong> {row.get('timestamp', 'N/A')}</div>
                <div class="crm-field"><strong>✅ Success:</strong> <span class="status-badge {success_badge}">{row.get('success', 'N/A')}</span></div>
                <div class="crm-field"><strong>📊 Status:</strong> {row.get('status', 'N/A')}</div>
                <div class="crm-field"><strong>🔗 Connection:</strong> {row.get('connection_status', 'N/A')}</div>
                <div class="crm-field"><strong>📅 Last Activity:</strong> {row.get('last_activity', 'N/A')}</div>
                <div class="crm-field"><strong>📝 Notes:</strong> {row.get('notes', 'N/A')[:100]}{'...' if len(str(row.get('notes', ''))) > 100 else ''}</div>
                <div class="crm-field"><strong>💳 Credits Used:</strong> {row.get('credits_used', 'N/A')}</div>
                ''', unsafe_allow_html=True)
            
            with st.expander("💬 View All Messages & Complete Details"):
                st.markdown("**📧 LinkedIn Outreach:**")
                st.markdown(f"**Subject:** {row.get('linkedin_subject', 'N/A')}")
                st.markdown(f"```\n{row.get('linkedin_message', 'N/A')}\n```")
                
                st.markdown("---")
                st.markdown("**📨 Email Outreach:**")
                st.markdown(f"**Subject:** {row.get('email_subject', 'N/A')}")
                st.markdown(f"```\n{row.get('email_message', 'N/A')}\n```")
                
                st.markdown("---")
                st.markdown("**🎯 Strategy & Personalization:**")
                st.markdown(f"**Outreach Strategy:** {row.get('outreach_strategy', 'N/A')}")
                st.markdown(f"**Personalization Points:** {row.get('personalization_points', 'N/A')}")
                st.markdown(f"**Follow-up Suggestions:** {row.get('follow_up_suggestions', 'N/A')}")
                
                st.markdown("---")
                st.markdown(f"**📝 Summary:** {row.get('summary', 'N/A')}")
                
                if row.get('error_message'):
                    st.error(f"**❌ Error:** {row.get('error_message')}")
                
                if row.get('image_url'):
                    try:
                        st.image(row.get('image_url'), width=200, caption="Profile Image")
                    except:
                        pass
            
            st.markdown("</div>", unsafe_allow_html=True)

# ------------------ EMAIL OUTREACH ------------------ #
def show_email_outreach():
    st.markdown("<div class='section-header'>📧 Email Outreach Campaign Manager</div>", unsafe_allow_html=True)
    
    outreach_df = st.session_state.outreach_df.copy()
    if outreach_df.empty:
        st.warning("📭 No email data.")
        return
    
    email_df = outreach_df[
        (outreach_df['email_subject'].notna() & (outreach_df['email_subject'] != '')) |
        (outreach_df['email_message'].notna() & (outreach_df['email_message'] != ''))
    ].copy()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'''
        <div class="stat-box">
            <div class="stat-number">{len(email_df)}</div>
            <div class="stat-label">Total Emails</div>
        </div>
        ''', unsafe_allow_html=True)
    with col2:
        ready = len(email_df[email_df['status'] == 'ready_to_send']) if 'status' in email_df.columns else 0
        st.markdown(f'''
        <div class="stat-box">
            <div class="stat-number">{ready}</div>
            <div class="stat-label">Ready</div>
        </div>
        ''', unsafe_allow_html=True)
    with col3:
        sent = len(email_df[email_df['success'].astype(str).str.lower() == 'true']) if 'success' in email_df.columns else 0
        st.markdown(f'''
        <div class="stat-box">
            <div class="stat-number">{sent}</div>
            <div class="stat-label">Sent</div>
        </div>
        ''', unsafe_allow_html=True)
    with col4:
        pending = len(email_df) - sent
        st.markdown(f'''
        <div class="stat-box">
            <div class="stat-number">{pending}</div>
            <div class="stat-label">Pending</div>
        </div>
        ''', unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        search = st.text_input("🔍 Search", placeholder="Search emails...", key="email_search")
    with col2:
        status_filter = st.selectbox("📊 Status", ["All", "Ready", "Sent", "Pending"], key="email_status")
    with col3:
        sort_by = st.selectbox("🔄 Sort", ["Newest", "Oldest", "Name"], key="email_sort")
    
    filtered_df = email_df.copy()
    if search:
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        filtered_df = filtered_df[mask]
    
    if status_filter == "Ready" and 'status' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['status'] == 'ready_to_send']
    elif status_filter == "Sent" and 'success' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['success'].astype(str).str.lower() == 'true']
    elif status_filter == "Pending" and 'success' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['success'].astype(str).str.lower() != 'true']
    
    if 'timestamp' in filtered_df.columns:
        filtered_df['parsed_time'] = filtered_df['timestamp'].apply(parse_timestamp)
        if sort_by == "Newest":
            filtered_df = filtered_df.sort_values('parsed_time', ascending=False)
        elif sort_by == "Oldest":
            filtered_df = filtered_df.sort_values('parsed_time', ascending=True)
    
    if sort_by == "Name" and 'profile_name' in filtered_df.columns:
        filtered_df = filtered_df.sort_values('profile_name')
    
    st.markdown(f"**Showing {len(filtered_df)} emails**")
    st.markdown("---")
    
    for idx, (i, row) in enumerate(filtered_df.iterrows()):
        name = row.get('profile_name', row.get('name', 'Unknown'))
        email_subject = row.get('email_subject', 'No Subject')
        email_message = row.get('email_message', 'No Message')
        timestamp = row.get('timestamp', 'N/A')
        success = is_message_sent(row)
        
        success_class = "status-success" if success else "status-pending"
        success_text = "✅ SENT" if success else "📤 READY"
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f'''
            <div class="email-card">
                <div style="display: flex; justify-content: space-between; margin-bottom: 1rem;">
                    <h3 style="margin: 0;">📧 {name}</h3>
                    <span class="status-badge {success_class}">{success_text}</span>
                </div>
                <div class="crm-field"><strong>📋 Subject:</strong> {email_subject}</div>
                <div class="crm-field"><strong>🕐 Time:</strong> {timestamp}</div>
                <div style="background: #f8f9fa; padding: 1rem; border-radius: 10px; margin-top: 1rem;">
                    <strong>Message:</strong><br>
                    {email_message[:200]}{'...' if len(str(email_message)) > 200 else ''}
                </div>
            </div>
            ''', unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Actions**")
            if st.button("📧 Send", key=f"email_send_{i}_{idx}", disabled=success, use_container_width=True):
                st.success(f"✅ Queued for {name}!")
                st.session_state.email_queue.append({'name': name, 'time': datetime.now().strftime('%H:%M:%S')})
            if st.button("📋 Copy", key=f"email_copy_{i}_{idx}", use_container_width=True):
                st.info("📋 Copied!")
            with st.expander("👁️ Full"):
                st.markdown(f"**Subject:** {email_subject}")
                st.markdown("---")
                st.markdown(email_message)

# ------------------ LEAD OUTREACH ------------------ #
def show_lead_outreach():
    st.markdown("<div class='section-header'>🎯 Lead Outreach Management</div>", unsafe_allow_html=True)
    
    outreach_df = st.session_state.outreach_df.copy()
    if outreach_df.empty:
        st.warning("📭 No outreach data.")
        return
    
    if 'timestamp' in outreach_df.columns:
        outreach_df['parsed_time'] = outreach_df['timestamp'].apply(parse_timestamp)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'''<div class="stat-box"><div class="stat-number">{len(outreach_df)}</div><div class="stat-label">Total Leads</div></div>''', unsafe_allow_html=True)
    with col2:
        sent = len(outreach_df[outreach_df['success'].astype(str).str.lower() == 'true']) if 'success' in outreach_df.columns else 0
        st.markdown(f'''<div class="stat-box"><div class="stat-number">{sent}</div><div class="stat-label">Sent</div></div>''', unsafe_allow_html=True)
    with col3:
        pending = len(outreach_df[outreach_df['status'] == 'pending']) if 'status' in outreach_df.columns else 0
        st.markdown(f'''<div class="stat-box"><div class="stat-number">{pending}</div><div class="stat-label">Pending</div></div>''', unsafe_allow_html=True)
    with col4:
        ready = len(outreach_df[outreach_df['status'] == 'ready_to_send']) if 'status' in outreach_df.columns else 0
        st.markdown(f'''<div class="stat-box"><div class="stat-number">{ready}</div><div class="stat-label">Ready</div></div>''', unsafe_allow_html=True)
    
    st.markdown("---")

    for idx, (i, row) in enumerate(outreach_df.iterrows()):
        with st.container():
            st.markdown(f'''
            <div class="lead-card">
                <h3 class="lead-title">{row.get('profile_name', 'Unknown')}</h3>
                <p class="lead-sub">{row.get('profile_tagline', 'N/A')}</p>
                <div class="lead-msg">{row.get('linkedin_message', 'N/A')}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem;">
                    <a href="{row.get('linkedin_url', '#')}" target="_blank">View Profile</a>
                    <span class="timestamp">{row.get('timestamp', 'N/A')}</span>
                </div>
            </div>
            ''', unsafe_allow_html=True)

# ------------------ SEARCH INTERFACE ------------------ #
def show_search_interface(webhook_url):
    st.markdown("<div class='section-header'>🔍 Search & Send New Leads</div>", unsafe_allow_html=True)
    st.caption("Search global business professionals by title, city, and industry to generate targeted leads instantly.")

    # --- Expanded job titles (60+) ---
    SEARCH_TERMS = [
        "Business Owner", "CEO", "Founder", "President", "Co-Founder", "Managing Director",
        "VP of Sales", "VP of Marketing", "Marketing Director", "Sales Director", "Chief Operating Officer",
        "Chief Financial Officer", "Chief Marketing Officer", "Chief Technology Officer", "Chief Strategy Officer",
        "Partner", "Investor", "Consultant", "Business Analyst", "Strategic Advisor", "Operations Manager",
        "Growth Manager", "Product Manager", "Head of Business Development", "Sales Executive", "Client Relations Manager",
        "Customer Success Manager", "IT Director", "Engineering Manager", "Account Executive", "Recruitment Director",
        "HR Manager", "Brand Manager", "Media Buyer", "Digital Marketing Specialist", "Public Relations Manager",
        "Software Engineer", "Data Scientist", "AI Researcher", "UX Designer", "Creative Director",
        "E-commerce Manager", "Financial Advisor", "Wealth Manager", "Real Estate Broker", "Attorney",
        "Doctor", "Dentist", "Architect", "Construction Manager", "Logistics Coordinator", "Supply Chain Manager",
        "Nonprofit Director", "Government Affairs Lead", "Policy Advisor", "Educator", "Professor", "Coach", "Trainer"
    ]

    # --- Expanded city list (300+) ---
    CITIES = [
        # USA - 100+
        "Atlanta", "Austin", "Baltimore", "Birmingham", "Boston", "Buffalo", "Charlotte", "Chicago", "Cincinnati",
        "Cleveland", "Columbus", "Dallas", "Denver", "Detroit", "El Paso", "Fort Worth", "Fresno", "Houston",
        "Indianapolis", "Jacksonville", "Kansas City", "Las Vegas", "Los Angeles", "Louisville", "Memphis", "Miami",
        "Milwaukee", "Minneapolis", "Nashville", "New Orleans", "New York", "Oklahoma City", "Orlando", "Philadelphia",
        "Phoenix", "Pittsburgh", "Portland", "Raleigh", "Richmond", "Sacramento", "Salt Lake City", "San Antonio",
        "San Diego", "San Francisco", "San Jose", "Seattle", "St. Louis", "Tampa", "Tulsa", "Washington DC", "Wichita",
        "Albuquerque", "Anchorage", "Arlington", "Boise", "Chandler", "Des Moines", "Durham", "Greensboro",
        "Honolulu", "Knoxville", "Little Rock", "Madison", "Mesa", "Mobile", "Newark", "Norfolk", "Omaha", "Plano",
        "Reno", "Riverside", "Scottsdale", "Spokane", "Toledo", "Tucson", "Virginia Beach", "Winston-Salem",
        # Canada
        "Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa", "Edmonton", "Winnipeg", "Quebec City", "Halifax", "Victoria",
        # UK & Europe
        "London", "Manchester", "Birmingham (UK)", "Glasgow", "Liverpool", "Dublin", "Paris", "Berlin", "Munich", "Frankfurt",
        "Hamburg", "Madrid", "Barcelona", "Valencia", "Amsterdam", "Rotterdam", "Rome", "Milan", "Naples", "Lisbon", "Porto",
        "Vienna", "Zurich", "Geneva", "Stockholm", "Oslo", "Copenhagen", "Warsaw", "Prague", "Budapest", "Brussels",
        # Middle East
        "Dubai", "Abu Dhabi", "Doha", "Riyadh", "Jeddah", "Kuwait City", "Manama", "Muscat", "Amman", "Tel Aviv",
        # Asia-Pacific
        "Singapore", "Tokyo", "Osaka", "Kyoto", "Seoul", "Busan", "Hong Kong", "Beijing", "Shanghai", "Shenzhen", "Taipei",
        "Bangkok", "Jakarta", "Kuala Lumpur", "Manila", "Sydney", "Melbourne", "Brisbane", "Perth", "Auckland", "Wellington",
        # Africa
        "Cape Town", "Johannesburg", "Durban", "Nairobi", "Kampala", "Accra", "Lagos", "Abuja", "Casablanca", "Marrakesh",
        "Cairo", "Alexandria", "Tunis", "Algiers", "Addis Ababa", "Dakar", "Harare",
        # Latin America
        "Mexico City", "Guadalajara", "Monterrey", "Bogotá", "Medellín", "Lima", "Quito", "Caracas",
        "Santiago", "Buenos Aires", "São Paulo", "Rio de Janeiro", "Brasilia", "Montevideo", "Asunción",
        "Panama City", "San José", "Kingston", "Havana", "Port of Spain", "Santo Domingo"
    ]

    COUNTRIES = [
        "United States", "Canada", "United Kingdom", "Australia", "Germany", "France", "Italy",
        "Spain", "Portugal", "Netherlands", "Sweden", "Switzerland", "India", "Singapore",
        "Japan", "South Korea", "China", "Brazil", "Mexico", "United Arab Emirates", "South Africa"
    ]

    INDUSTRIES = [
        "Technology", "Finance", "Healthcare", "Education", "Real Estate", "Retail", "Manufacturing",
        "Marketing", "Hospitality", "Legal", "Construction", "Transportation", "Media", "Telecommunications",
        "Energy", "Agriculture", "Nonprofit", "Entertainment", "Insurance", "Logistics", "Government", "Consulting"
    ]

    COMPANY_TYPES = ["Private", "Public", "Startup", "Nonprofit", "Government", "Franchise"]
    COMPANY_SIZE = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
    REVENUE_RANGE = ["<$1M", "$1M-$5M", "$5M-$10M", "$10M-$50M", "$50M-$100M", "$100M+"]

    # --- Search Form UI ---
    with st.form("search_form"):
        st.subheader("🎯 Lead Search Filters")

        col1, col2, col3 = st.columns(3)
        with col1:
            search_term = st.selectbox("Job Title", SEARCH_TERMS)
        with col2:
            city = st.selectbox("City", CITIES)
        with col3:
            country = st.selectbox("Country", COUNTRIES)

        col4, col5, col6 = st.columns(3)
        with col4:
            industry = st.selectbox("Industry", INDUSTRIES)
        with col5:
            company_type = st.selectbox("Company Type", COMPANY_TYPES)
        with col6:
            company_size = st.selectbox("Company Size", COMPANY_SIZE)

        col7, col8 = st.columns(2)
        with col7:
            revenue = st.selectbox("Revenue Range", REVENUE_RANGE)
        with col8:
            num_leads = st.slider("Number of Leads", 1, 200, 25)

        tags = st.text_input("Keywords (comma-separated)", placeholder="e.g. SaaS, B2B, fintech, real estate")

        submitted = st.form_submit_button("🚀 Start Search", use_container_width=True)

        if submitted:
            payload = {
                "search_term": search_term,
                "city": city,
                "country": country,
                "industry": industry,
                "company_type": company_type,
                "company_size": company_size,
                "revenue": revenue,
                "tags": tags,
                "num_leads": num_leads
            }

            with st.spinner(f"Searching for {num_leads} {search_term}s in {city}, {country}..."):
                try:
                    response = requests.post(webhook_url, json=payload, timeout=15)
                    if response.status_code == 200:
                        st.success(f"✅ Search initiated for {search_term}s in {city}, {country}!")
                        st.balloons()
                        if "activity_log" not in st.session_state:
                            st.session_state.activity_log = []
                        st.session_state.activity_log.append({
                            "type": "Search",
                            "details": f"{search_term} in {city}, {country} ({industry})",
                            "status": "✅ Success",
                            "time": datetime.now().strftime("%H:%M:%S")
                        })
                    else:
                        st.error(f"⚠️ Unexpected status: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f"❌ Error occurred: {str(e)}")

    # --- Activity Log ---
    if "activity_log" in st.session_state and st.session_state.activity_log:
        st.markdown("### 🕒 Recent Activity")
        for entry in reversed(st.session_state.activity_log[-15:]):
            st.write(f"**{entry['time']}** | {entry['type']}: {entry['details']} ({entry['status']})")


# ------------------ CHAT ANALYTICS ------------------ #
def get_contact_info(df, my_profile):
    contacts = {}
    for idx, row in df.iterrows():
        sender_name = row.get('sender_name', '')
        sender_url = row.get('sender_linkedin_url', '')
        if is_me(sender_name, sender_url, my_profile):
            continue
        contact_url = sender_url if sender_url else row.get('lead_linkedin_url', '')
        contact_name = sender_name if sender_name else row.get('lead_name', '')
        if contact_url and contact_url not in contacts:
            contacts[contact_url] = {
                'name': contact_name, 'url': contact_url, 'messages': [],
                'last_contact': None, 'received_count': 0, 'sent_count': 0
            }
    
    for idx, row in df.iterrows():
        sender_name = row.get('sender_name', '')
        sender_url = row.get('sender_linkedin_url', '')
        lead_url = row.get('lead_linkedin_url', '')
        
        if is_me(sender_name, sender_url, my_profile):
            if lead_url in contacts:
                contacts[lead_url]['sent_count'] += 1
                contacts[lead_url]['messages'].append(row)
                contacts[lead_url]['last_contact'] = f"{row.get('date', '')} {row.get('time', '')}"
        else:
            contact_url = sender_url if sender_url else lead_url
            if contact_url in contacts:
                contacts[contact_url]['received_count'] += 1
                contacts[contact_url]['messages'].append(row)
                contacts[contact_url]['last_contact'] = f"{row.get('date', '')} {row.get('time', '')}"
    
    return contacts

def show_chat_analytics():
    st.markdown("<div class='section-header'>💬 Chat History Analytics</div>", unsafe_allow_html=True)
    
    chat_df = st.session_state.chat_df
    if chat_df.empty:
        st.warning("📭 No chat data.")
        return
    
    my_profile = {'name': MY_PROFILE['name'], 'url': MY_PROFILE['url']}
    contacts = get_contact_info(chat_df, my_profile)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'''<div class="stat-box"><div class="stat-number">{len(chat_df)}</div><div class="stat-label">Total Messages</div></div>''', unsafe_allow_html=True)
    with col2:
        st.markdown(f'''<div class="stat-box"><div class="stat-number">{len(contacts)}</div><div class="stat-label">Contacts</div></div>''', unsafe_allow_html=True)
    with col3:
        my_messages = sum(1 for _, row in chat_df.iterrows() if is_me(row.get('sender_name', ''), row.get('sender_linkedin_url', ''), my_profile))
        st.markdown(f'''<div class="stat-box"><div class="stat-number">{my_messages}</div><div class="stat-label">Sent by You</div></div>''', unsafe_allow_html=True)
    with col4:
        received = len(chat_df) - my_messages
        st.markdown(f'''<div class="stat-box"><div class="stat-number">{received}</div><div class="stat-label">Received</div></div>''', unsafe_allow_html=True)
    
    st.markdown("---")
    
    view_mode = st.radio("View Mode", ["📇 Contacts", "📋 All Messages"], horizontal=True)
    st.markdown("---")
    
    if view_mode == "📇 Contacts":
        if not contacts:
            st.info("🔭 No contacts found")
            return
        
        cols = st.columns(2)
        for idx, (url, info) in enumerate(contacts.items()):
            col = cols[idx % 2]
            message_count = len(info['messages'])
            initials = get_initials(info['name'])
            
            with col:
                st.markdown(f'''
                <div class="contact-card">
                    <div style="display: flex; align-items: center; margin-bottom: 15px;">
                        <div class="profile-badge">{initials}</div>
                        <div><h3 style="margin: 0;">{info['name']}</h3></div>
                    </div>
                    <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                        <div style="background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 10px;">💬 {message_count} messages</div>
                        <div style="background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 10px;">📤 {info['sent_count']} sent</div>
                        <div style="background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 10px;">📥 {info['received_count']} received</div>
                    </div>
                    <p style="margin-top: 15px;"><strong>Last:</strong> {info['last_contact']}</p>
                    <a href="{url}" target="_blank" style="color: white; text-decoration: none; background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 25px; display: inline-block; margin-top: 10px;">🔗 LinkedIn →</a>
                </div>
                ''', unsafe_allow_html=True)
    else:
        for idx, (i, row) in enumerate(chat_df.iterrows()):
            sender_name = str(row.get('sender_name', 'Unknown'))
            message = str(row.get('message', ''))
            date = str(row.get('date', ''))
            time_str = str(row.get('time', ''))
            
            is_my_message = is_me(sender_name, row.get('sender_linkedin_url', ''), my_profile)
            badge_style = "background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);" if is_my_message else "background: #10b981;"
            badge_text = "You" if is_my_message else "Received"
            
            st.markdown(f'''
            <div class="message-card-all">
                <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
                    <div>
                        <strong style="font-size: 1.2em;">{sender_name}</strong>
                        <span class="status-badge" style="{badge_style} color: white !important;">{badge_text}</span>
                    </div>
                    <div class="timestamp">🗓️ {date} • 🕐 {time_str}</div>
                </div>
                <div style="margin: 15px 0; line-height: 1.6;">{message}</div>
            </div>
            ''', unsafe_allow_html=True)

# ------------------ OVERVIEW ------------------ #
def show_overview():
    st.markdown("<div class='section-header'>📊 Dashboard Overview</div>", unsafe_allow_html=True)
    
    chat_df = st.session_state.chat_df
    outreach_df = st.session_state.outreach_df.copy()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'''<div class="metric-card"><div class="metric-value">{len(chat_df)}</div><div class="metric-label">Total Chats</div></div>''', unsafe_allow_html=True)
    with col2:
        st.markdown(f'''<div class="metric-card" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);"><div class="metric-value">{len(outreach_df)}</div><div class="metric-label">Total Leads</div></div>''', unsafe_allow_html=True)
    with col3:
        sent = len(outreach_df[outreach_df['success'].astype(str).str.lower() == 'true']) if 'success' in outreach_df.columns and not outreach_df.empty else 0
        st.markdown(f'''<div class="metric-card" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);"><div class="metric-value">{sent}</div><div class="metric-label">Messages Sent</div></div>''', unsafe_allow_html=True)
    with col4:
        pending = len(outreach_df) - sent if not outreach_df.empty else 0
        st.markdown(f'''<div class="metric-card" style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);"><div class="metric-value">{pending}</div><div class="metric-label">Pending</div></div>''', unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📈 Lead Status")
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

# ------------------ MAIN APP ------------------ #
def main():
    if not st.session_state.authenticated:
        authenticate_user()
        return
    
    if not st.session_state.current_client:
        st.session_state.current_client = {'name': MY_PROFILE['name'], 'linkedin_url': MY_PROFILE['url']}
    
    st.markdown("<div class='main-title'>🚀 LinkedIn Analytics & Outreach Hub</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sub-title'>Welcome, {st.session_state.current_client['name']}!</div>", unsafe_allow_html=True)
    
    with st.sidebar:
        st.header("⚙️ Dashboard Settings")
        st.markdown(f'''
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; color: white;">
            <h3>{st.session_state.current_client['name']}</h3>
            <a href="{st.session_state.current_client['linkedin_url']}" target="_blank" style="color: white;">🔗 LinkedIn →</a>
        </div>
        ''', unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("🔄 Load/Refresh Data", use_container_width=True):
            with st.spinner("Loading..."):
                try:
                    st.session_state.chat_df = load_sheet_data(st.session_state.gsheets_client, CHAT_SPREADSHEET_ID, CHAT_SHEET_NAME)
                    st.session_state.outreach_df = load_sheet_data(st.session_state.gsheets_client, OUTREACH_SPREADSHEET_ID, OUTREACH_SHEET_NAME)
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
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Overview", "🎯 Lead Outreach", "📧 Email Outreach",
        "🔍 Search & Send", "📋 CRM Dashboard", "💬 Chat Analytics"
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
        show_chat_analytics()

if __name__ == "__main__":
    main()
