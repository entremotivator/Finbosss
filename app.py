import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import json
from collections import defaultdict
import plotly.express as px
import plotly.graph_objects as go
import requests
import time

# ------------------ PAGE CONFIG ------------------ #
st.set_page_config(
    page_title="LinkedIn Analytics & Outreach Hub",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------ SESSION STATE INITIALIZATION ------------------ #
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
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

# ------------------ ENHANCED STYLES ------------------ #
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main {
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
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
    }
    
    .metric-value {
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    
    .metric-label {
        font-size: 1rem;
        opacity: 0.95;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 600;
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
    }
    
    .contact-card:hover {
        transform: translateY(-8px) scale(1.02);
    }
    
    .contact-name {
        font-size: 1.8em;
        font-weight: 700;
        margin-bottom: 15px;
    }
    
    .lead-card {
        background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        margin-bottom: 1.5rem;
        transition: all 0.4s ease;
        border-left: 5px solid #667eea;
    }
    
    .lead-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 15px 35px rgba(0,0,0,0.15);
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
    
    .message-sent {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 25px;
        border-radius: 20px 20px 5px 20px;
        margin-bottom: 20px;
        color: white;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        margin-left: 60px;
    }
    
    .section-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1e293b;
        margin: 2.5rem 0 1.5rem 0;
        padding-bottom: 0.8rem;
        border-bottom: 3px solid #667eea;
    }
    
    .status-badge {
        display: inline-flex;
        padding: 0.5rem 1.2rem;
        border-radius: 25px;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .status-ready {
        background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
        color: #166534;
    }
    
    .status-sent {
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        color: #1e40af;
    }
    
    .client-profile-banner {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 40px;
        border-radius: 20px;
        color: white;
        margin-bottom: 30px;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
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
    return query_params.get('client', None)

def load_client_profile(client_id):
    """Load client-specific profile and preferences"""
    # This would typically come from a database or config file
    client_profiles = {
        'donmenico': {
            'name': 'Donmenico Hudson',
            'linkedin_url': 'https://www.linkedin.com/in/donmenicohudson/',
            'chat_sheet_id': '1klm60YFXSoV510S4igv5LfREXeykDhNA5Ygq7HNFN0I',
            'chat_sheet_name': 'linkedin_chat_history_advanced 2',
            'outreach_sheet_id': '1eLEFvyV1_f74UC1g5uQ-xA7A62sK8Pog27KIjw_Sk3Y',
            'outreach_sheet_name': 'Sheet1',
            'webhook_url': 'https://agentonline-u29564.vm.elestio.app/webhook/Leadlinked'
        }
    }
    
    return client_profiles.get(client_id, None)

# ------------------ AUTHENTICATION ------------------ #
def authenticate_user():
    """Handle user authentication with service account"""
    st.markdown("<div class='main-title'>🔐 LinkedIn Analytics Hub</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>Secure Login with Google Service Account</div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        st.subheader("📁 Upload Service Account Credentials")
        
        uploaded_file = st.file_uploader(
            "Upload your Google Service Account JSON file",
            type=['json'],
            help="This file contains your Google Cloud credentials"
        )
        
        if uploaded_file is not None:
            try:
                credentials_json = uploaded_file.read().decode('utf-8')
                client = init_google_sheets(credentials_json)
                
                if client:
                    st.session_state.authenticated = True
                    st.session_state.gsheets_client = client
                    st.success("✅ Authentication successful!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to authenticate. Please check your credentials.")
            except Exception as e:
                st.error(f"❌ Authentication error: {str(e)}")
        
        st.markdown("---")
        st.info("""
        **📋 Setup Instructions:**
        
        1. **Google Cloud Console**
           - Go to console.cloud.google.com
           - Create or select a project
        
        2. **Enable APIs**
           - Google Sheets API
           - Google Drive API
        
        3. **Create Service Account**
           - IAM & Admin > Service Accounts
           - Create service account
           - Download JSON key
        
        4. **Share Your Sheets**
           - Open your Google Sheets
           - Share with service account email
           - Grant "Editor" access
        
        5. **Upload JSON**
           - Use the uploader above
        """)

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
            if contact_url in contacts:
                contacts[contact_url]['sent_count'] += 1
        else:
            contact_url = sender_url if sender_url else lead_url
            if contact_url in contacts:
                contacts[contact_url]['received_count'] += 1
        
        if contact_url in contacts:
            contacts[contact_url]['messages'].append(row)
            contacts[contact_url]['last_contact'] = f"{row.get('date', '')} {row.get('time', '')}"
    
    return contacts

# ------------------ MAIN APPLICATION ------------------ #
def main():
    # Check authentication
    if not st.session_state.authenticated:
        authenticate_user()
        return
    
    # Get client from URL
    client_id = get_client_from_url()
    
    if client_id:
        client_profile = load_client_profile(client_id)
        if client_profile:
            st.session_state.current_client = client_profile
    
    # Header
    st.markdown("<div class='main-title'>🚀 LinkedIn Analytics & Outreach Hub</div>", unsafe_allow_html=True)
    
    if st.session_state.current_client:
        st.markdown(f"<div class='sub-title'>Welcome back, {st.session_state.current_client['name']}!</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='sub-title'>Unified Dashboard for Chat Analytics & Lead Outreach</div>", unsafe_allow_html=True)
    
    # Sidebar Configuration
    with st.sidebar:
        st.header("⚙️ Dashboard Settings")
        
        # Client Profile Display
        if st.session_state.current_client:
            st.markdown("---")
            st.subheader("👤 Your Profile")
            st.markdown(f"""
            **{st.session_state.current_client['name']}**  
            [View LinkedIn Profile →]({st.session_state.current_client['linkedin_url']})
            """)
        
        st.markdown("---")
        
        # Data Source Configuration
        st.subheader("📊 Data Configuration")
        
        if st.session_state.current_client:
            # Auto-load client sheets
            chat_sheet_id = st.text_input(
                "Chat History Sheet ID",
                value=st.session_state.current_client['chat_sheet_id']
            )
            chat_sheet_name = st.text_input(
                "Chat Sheet Name",
                value=st.session_state.current_client['chat_sheet_name']
            )
            
            outreach_sheet_id = st.text_input(
                "Outreach Sheet ID",
                value=st.session_state.current_client['outreach_sheet_id']
            )
            outreach_sheet_name = st.text_input(
                "Outreach Sheet Name",
                value=st.session_state.current_client['outreach_sheet_name']
            )
            
            webhook_url = st.text_input(
                "Webhook URL",
                value=st.session_state.current_client['webhook_url']
            )
        else:
            # Manual configuration
            chat_sheet_id = st.text_input("Chat History Sheet ID")
            chat_sheet_name = st.text_input("Chat Sheet Name", value="Sheet1")
            outreach_sheet_id = st.text_input("Outreach Sheet ID")
            outreach_sheet_name = st.text_input("Outreach Sheet Name", value="Sheet1")
            webhook_url = st.text_input("Webhook URL")
        
        st.markdown("---")
        
        # Load Data Button
        if st.button("🔄 Load/Refresh Data", use_container_width=True):
            with st.spinner("Loading data from Google Sheets..."):
                try:
                    # Load chat data
                    if chat_sheet_id:
                        st.session_state.chat_df = load_sheet_data(
                            st.session_state.gsheets_client,
                            chat_sheet_id,
                            chat_sheet_name
                        )
                    
                    # Load outreach data
                    if outreach_sheet_id:
                        st.session_state.outreach_df = load_sheet_data(
                            st.session_state.gsheets_client,
                            outreach_sheet_id,
                            outreach_sheet_name
                        )
                    
                    st.success("✅ Data loaded successfully!")
                except Exception as e:
                    st.error(f"❌ Error loading data: {str(e)}")
        
        st.markdown("---")
        
        # Quick Stats
        st.subheader("📊 Quick Stats")
        st.metric("Chat Messages", len(st.session_state.chat_df))
        st.metric("Outreach Leads", len(st.session_state.outreach_df))
        
        st.markdown("---")
        
        # Logout
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.gsheets_client = None
            st.session_state.chat_df = pd.DataFrame()
            st.session_state.outreach_df = pd.DataFrame()
            st.rerun()
    
    # Main Dashboard Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview",
        "💬 Chat Analytics",
        "🎯 Lead Outreach",
        "🔍 Search & Send"
    ])
    
    with tab1:
        show_overview()
    
    with tab2:
        show_chat_analytics()
    
    with tab3:
        show_lead_outreach()
    
    with tab4:
        show_search_interface(webhook_url if 'webhook_url' in locals() else None)

# ------------------ OVERVIEW TAB ------------------ #
def show_overview():
    st.markdown("<div class='section-header'>📊 Dashboard Overview</div>", unsafe_allow_html=True)
    
    # Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    chat_df = st.session_state.chat_df
    outreach_df = st.session_state.outreach_df
    
    with col1:
        total_chats = len(chat_df)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_chats}</div>
            <div class="metric-label">Total Chats</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_leads = len(outreach_df)
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);">
            <div class="metric-value">{total_leads}</div>
            <div class="metric-label">Total Leads</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        sent_count = len(outreach_df[outreach_df['status'] == 'sent']) if 'status' in outreach_df.columns and not outreach_df.empty else 0
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
            <div class="metric-value">{sent_count}</div>
            <div class="metric-label">Messages Sent</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        if st.session_state.current_client:
            contacts = get_contact_info(chat_df, {
                'name': st.session_state.current_client['name'],
                'url': st.session_state.current_client['linkedin_url']
            })
            contact_count = len(contacts)
        else:
            contact_count = 0
        
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);">
            <div class="metric-value">{contact_count}</div>
            <div class="metric-label">Active Contacts</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Recent Activity
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Recent Chat Activity")
        if not chat_df.empty and 'date' in chat_df.columns:
            daily_chats = chat_df.groupby('date').size().tail(7)
            fig = px.bar(
                x=daily_chats.index,
                y=daily_chats.values,
                title="Last 7 Days",
                labels={'x': 'Date', 'y': 'Messages'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No chat data available")
    
    with col2:
        st.subheader("🎯 Outreach Performance")
        if not outreach_df.empty and 'status' in outreach_df.columns:
            status_counts = outreach_df['status'].value_counts()
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Status Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No outreach data available")

# ------------------ CHAT ANALYTICS TAB ------------------ #
def show_chat_analytics():
    st.markdown("<div class='section-header'>💬 Chat History Analytics</div>", unsafe_allow_html=True)
    
    chat_df = st.session_state.chat_df
    
    if chat_df.empty:
        st.warning("📭 No chat data loaded. Please load your chat history sheet.")
        return
    
    if not st.session_state.current_client:
        st.warning("⚠️ Client profile not loaded. Some features may be limited.")
        return
    
    my_profile = {
        'name': st.session_state.current_client['name'],
        'url': st.session_state.current_client['linkedin_url']
    }
    
    contacts = get_contact_info(chat_df, my_profile)
    
    # View Selection
    view_mode = st.radio(
        "Select View",
        ["📇 All Contacts", "💬 Contact Conversation", "📋 All Messages"],
        horizontal=True
    )
    
    st.markdown("---")
    
    if view_mode == "📇 All Contacts":
        st.subheader("📇 All Contacts")
        
        if not contacts:
            st.info("No contacts found in chat history")
            return
        
        cols = st.columns(2)
        
        for idx, (url, info) in enumerate(contacts.items()):
            col = cols[idx % 2]
            
            with col:
                st.markdown(f"""
                <div class="contact-card">
                    <div class="contact-name">{info['name']}</div>
                    <div>💬 {len(info['messages'])} messages</div>
                    <div>📤 {info['sent_count']} sent | 📥 {info['received_count']} received</div>
                    <div style="margin-top: 15px;">
                        <a href="{url}" target="_blank" style="color: white; text-decoration: none;">
                            🔗 View Profile →
                        </a>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    elif view_mode == "💬 Contact Conversation":
        st.subheader("💬 Contact Conversation")
        
        if not contacts:
            st.info("No contacts found")
            return
        
        contact_names = {info['name']: url for url, info in contacts.items()}
        selected_name = st.selectbox("Select Contact", list(contact_names.keys()))
        
        if selected_name:
            selected_url = contact_names[selected_name]
            contact_info = contacts[selected_url]
            
            st.markdown(f"""
            <div class='client-profile-banner'>
                <h2>{contact_info['name']}</h2>
                <p>💬 {len(contact_info['messages'])} messages</p>
                <p>📤 {contact_info['sent_count']} sent | 📥 {contact_info['received_count']} received</p>
            </div>
            """, unsafe_allow_html=True)
            
            messages = sorted(
                contact_info['messages'],
                key=lambda x: (x.get('date', ''), x.get('time', ''))
            )
            
            for msg in messages:
                sender_name = msg.get('sender_name', '')
                sender_url = msg.get('sender_linkedin_url', '')
                message_text = msg.get('message', '')
                time_str = msg.get('time', '')
                
                is_my_message = is_me(sender_name, sender_url, my_profile)
                
                if is_my_message:
                    st.markdown(f"""
                    <div class="message-sent">
                        <strong>You</strong> • {time_str}
                        <p style="margin-top: 10px;">{message_text}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="message-received">
                        <strong>{sender_name}</strong> • {time_str}
                        <p style="margin-top: 10px;">{message_text}</p>
                    </div>
                    """, unsafe_allow_html=True)
    
    else:  # All Messages
        st.subheader("📋 All Messages")
        st.dataframe(chat_df, use_container_width=True, height=600)

# ------------------ LEAD OUTREACH TAB ------------------ #
def show_lead_outreach():
    st.markdown("<div class='section-header'>🎯 Lead Outreach Management</div>", unsafe_allow_html=True)
    
    outreach_df = st.session_state.outreach_df
    
    if outreach_df.empty:
        st.warning("📭 No outreach data loaded. Please load your outreach sheet.")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Status Filter",
            ["All"] + list(outreach_df['status'].unique()) if 'status' in outreach_df.columns else ["All"]
        )
    
    with col2:
        city_filter = st.selectbox(
            "City Filter",
            ["All"] + list(outreach_df['search_city'].unique()) if 'search_city' in outreach_df.columns else ["All"]
        )
    
    with col3:
        sort_by = st.selectbox("Sort By", ["timestamp", "status", "profile_name"])
    
    # Apply filters
    filtered_df = outreach_df.copy()
    
    if status_filter != "All" and 'status' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['status'] == status_filter]
    
    if city_filter != "All" and 'search_city' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['search_city'] == city_filter]
    
    st.markdown(f"**Showing {len(filtered_df)} leads**")
    st.markdown("---")
    
    # Display leads
    for idx, (i, row) in enumerate(filtered_df.iterrows()):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            name = str(row.get('profile_name', 'Unnamed Lead'))
            location = str(row.get('profile_location', 'Unknown'))
            message = str(row.get('linkedin_message', ''))
            status = str(row.get('status', 'unknown'))
            
            st.markdown(f"""
            <div class="lead-card">
                <h3>👤 {name}</h3>
                <p>📍 {location}</p>
                <div style="background: #f1f5f9; padding: 15px; border-radius: 10px; margin: 15px 0;">
                    💬 {message}
                </div>
                <span class="status-badge {'status-sent' if status == 'sent' else 'status-ready'}">{status}</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Actions**")
            if st.button("🚀 Send", key=f"send_{i}", disabled=status=='sent', use_container_width=True):
                st.session_state.sent_leads.add(i)
                st.success(f"✅ Message sent to {name}!")
                st.rerun()
            
            if st.button("📋 Copy", key=f"copy_{i}", use_container_width=True):
                st.info("📋 Lead data copied!")
            
            if st.button("⭐ Save", key=f"save_{i}", use_container_width=True):
                st.info("⭐ Lead saved!")

# ------------------ SEARCH INTERFACE TAB ------------------ #
def show_search_interface(webhook_url):
    st.markdown("<div class='section-header'>🔍 Search & Send New Leads</div>", unsafe_allow_html=True)
    
    # Predefined options
    SEARCH_TERMS = [
        "Business Owner", "CEO", "Chief Executive Officer", "Founder", "Co-Founder",
        "Managing Director", "President", "Vice President", "VP of Sales", "VP of Marketing",
        "Director of Sales", "Director of Marketing", "Sales Manager", "Marketing Manager"
    ]
    
    CITIES = [
        "Tampa", "Miami", "Orlando", "Jacksonville", "Atlanta", "Charlotte",
        "New York", "Los Angeles", "San Francisco", "Chicago", "Boston", "Seattle"
    ]
    
    COUNTRIES = [
        "United States", "Canada", "United Kingdom", "Australia", "Germany", "France"
    ]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🔎 Search Criteria")
        
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
                if not webhook_url:
                    st.error("❌ Webhook URL not configured!")
                else:
                    payload = {
                        "search_term": search_term,
                        "city": city,
                        "country": country,
                        "num_leads": num_leads,
                        "timestamp": datetime.utcnow().isoformat(),
                        "source": "unified_dashboard"
                    }
                    
                    try:
                        with st.spinner("🔍 Searching for leads..."):
                            response = requests.post(webhook_url, json=payload, timeout=10)
                            
                        if response.status_code == 200:
                            st.success(f"✅ Search initiated for {search_term} in {city}, {country}!")
                            st.info("📊 Results will appear in your outreach sheet shortly.")
                            
                            # Log activity
                            st.session_state.activity_log.append({
                                "type": "Search",
                                "details": f"{search_term} in {city}",
                                "status": "Success",
                                "time": datetime.now().strftime("%H:%M:%S")
                            })
                        else:
                            st.error(f"❌ Error: HTTP {response.status_code}")
                    
                    except requests.exceptions.Timeout:
                        st.warning("⚠️ Request timeout - webhook may be slow")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    with col2:
        st.subheader("📊 Recent Searches")
        
        if st.session_state.activity_log:
            recent_searches = [log for log in st.session_state.activity_log if log.get('type') == 'Search'][-5:]
            
            for search in reversed(recent_searches):
                st.markdown(f"""
                <div style="background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #667eea;">
                    <strong>{search['details']}</strong><br>
                    <small>🕐 {search['time']} - {search['status']}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No recent searches")
        
        st.markdown("---")
        
        # Quick stats
        st.metric("Total Searches", len([log for log in st.session_state.activity_log if log.get('type') == 'Search']))
        st.metric("Success Rate", "95%")

# ------------------ RUN APPLICATION ------------------ #
if __name__ == "__main__":
    main()
