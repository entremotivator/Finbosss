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
    page_title="MATRIX: LinkedIn Intelligence System",
    page_icon="💚",
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

# ------------------ MATRIX STYLES ------------------ #
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=VT323&display=swap');
    
    * {
        font-family: 'Share Tech Mono', monospace;
    }
    
    /* Matrix Background */
    .stApp {
        background: #000000;
        background-image: 
            linear-gradient(0deg, transparent 24%, rgba(0, 255, 0, .05) 25%, rgba(0, 255, 0, .05) 26%, transparent 27%, transparent 74%, rgba(0, 255, 0, .05) 75%, rgba(0, 255, 0, .05) 76%, transparent 77%, transparent),
            linear-gradient(90deg, transparent 24%, rgba(0, 255, 0, .05) 25%, rgba(0, 255, 0, .05) 26%, transparent 27%, transparent 74%, rgba(0, 255, 0, .05) 75%, rgba(0, 255, 0, .05) 76%, transparent 77%, transparent);
        background-size: 50px 50px;
        color: #00ff00;
    }
    
    /* Matrix Animation */
    @keyframes matrix-fall {
        0% { transform: translateY(-100%); opacity: 1; }
        100% { transform: translateY(100vh); opacity: 0; }
    }
    
    @keyframes glitch {
        0% { transform: translate(0); }
        20% { transform: translate(-2px, 2px); }
        40% { transform: translate(-2px, -2px); }
        60% { transform: translate(2px, 2px); }
        80% { transform: translate(2px, -2px); }
        100% { transform: translate(0); }
    }
    
    @keyframes scan {
        0% { top: 0; }
        100% { top: 100%; }
    }
    
    @keyframes flicker {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.8; }
    }
    
    @keyframes pulse-green {
        0%, 100% { box-shadow: 0 0 5px #00ff00, 0 0 10px #00ff00; }
        50% { box-shadow: 0 0 20px #00ff00, 0 0 30px #00ff00, 0 0 40px #00ff00; }
    }
    
    /* Main Title */
    .main-title {
        text-align: center;
        font-size: 4rem;
        font-weight: 900;
        color: #00ff00;
        text-shadow: 0 0 10px #00ff00, 0 0 20px #00ff00, 0 0 30px #00ff00;
        margin-bottom: 0.5rem;
        font-family: 'VT323', monospace;
        letter-spacing: 0.1em;
        animation: flicker 3s infinite;
    }
    
    .sub-title {
        text-align: center;
        font-size: 1.4rem;
        color: #00ff00;
        margin-bottom: 2rem;
        font-family: 'Share Tech Mono', monospace;
        text-shadow: 0 0 5px #00ff00;
        opacity: 0.8;
    }
    
    /* Metric Cards */
    .metric-card {
        background: rgba(0, 0, 0, 0.9);
        border: 2px solid #00ff00;
        border-radius: 0;
        padding: 2rem;
        color: #00ff00;
        text-align: center;
        box-shadow: 0 0 20px rgba(0, 255, 0, 0.3), inset 0 0 20px rgba(0, 255, 0, 0.1);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: -2px;
        left: -2px;
        right: -2px;
        height: 2px;
        background: linear-gradient(90deg, transparent, #00ff00, transparent);
        animation: scan 2s linear infinite;
    }
    
    .metric-card:hover {
        transform: scale(1.05);
        box-shadow: 0 0 30px rgba(0, 255, 0, 0.5), inset 0 0 30px rgba(0, 255, 0, 0.2);
        animation: pulse-green 1s infinite;
    }
    
    .metric-value {
        font-size: 3rem;
        font-weight: 900;
        font-family: 'VT323', monospace;
        text-shadow: 0 0 10px #00ff00;
        letter-spacing: 0.1em;
    }
    
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.8;
        text-transform: uppercase;
        letter-spacing: 0.2em;
        margin-top: 0.5rem;
    }
    
    .metric-trend {
        font-size: 0.8rem;
        margin-top: 0.5rem;
        opacity: 0.6;
    }
    
    /* Contact Cards */
    .contact-card {
        background: rgba(0, 0, 0, 0.95);
        border: 2px solid #00ff00;
        padding: 25px;
        border-radius: 0;
        color: #00ff00;
        margin-bottom: 20px;
        box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
        transition: all 0.3s ease;
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }
    
    .contact-card::after {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(0, 255, 0, 0.2), transparent);
        transition: left 0.5s;
    }
    
    .contact-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 0 30px rgba(0, 255, 0, 0.5);
        animation: glitch 0.3s infinite;
    }
    
    .contact-card:hover::after {
        left: 100%;
    }
    
    .contact-name {
        font-size: 1.8em;
        font-weight: 700;
        font-family: 'VT323', monospace;
        margin-bottom: 15px;
        text-shadow: 0 0 5px #00ff00;
        letter-spacing: 0.05em;
    }
    
    .contact-stats {
        display: flex;
        gap: 15px;
        margin-top: 15px;
        flex-wrap: wrap;
    }
    
    .contact-stat-item {
        background: rgba(0, 255, 0, 0.1);
        border: 1px solid #00ff00;
        padding: 8px 15px;
        border-radius: 0;
        font-size: 0.9em;
    }
    
    /* Lead Cards */
    .lead-card {
        background: rgba(0, 0, 0, 0.95);
        border: 2px solid #00ff00;
        border-radius: 0;
        padding: 2rem;
        box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .lead-card::before {
        content: '> SYSTEM_RECORD';
        position: absolute;
        top: 10px;
        right: 10px;
        font-size: 0.7em;
        opacity: 0.3;
        font-family: 'VT323', monospace;
    }
    
    .lead-card:hover {
        transform: translateX(10px);
        box-shadow: 0 0 30px rgba(0, 255, 0, 0.5);
        border-color: #0f0;
    }
    
    .lead-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #00ff00;
        margin-bottom: 0.8rem;
        font-family: 'VT323', monospace;
        text-shadow: 0 0 5px #00ff00;
        letter-spacing: 0.05em;
    }
    
    .lead-sub {
        font-size: 1rem;
        color: #00ff00;
        margin-bottom: 0.6rem;
        opacity: 0.8;
    }
    
    .lead-msg {
        background: rgba(0, 255, 0, 0.1);
        border-left: 3px solid #00ff00;
        border-radius: 0;
        padding: 1.2rem;
        margin: 1.2rem 0;
        font-size: 0.95rem;
        color: #00ff00;
        line-height: 1.6;
        font-style: italic;
    }
    
    /* Message Styles */
    .message-received {
        background: rgba(0, 0, 0, 0.9);
        border: 1px solid #00ff00;
        padding: 20px;
        border-radius: 0;
        margin-bottom: 15px;
        border-left: 3px solid #00ff00;
        box-shadow: 0 0 15px rgba(0, 255, 0, 0.2);
        color: #00ff00;
    }
    
    .message-sent {
        background: rgba(0, 255, 0, 0.1);
        border: 1px solid #00ff00;
        padding: 20px;
        border-radius: 0;
        margin-bottom: 15px;
        color: #00ff00;
        box-shadow: 0 0 15px rgba(0, 255, 0, 0.2);
        margin-left: 60px;
        border-right: 3px solid #00ff00;
    }
    
    .message-card-all {
        background: rgba(0, 0, 0, 0.95);
        border: 2px solid #00ff00;
        padding: 25px;
        border-radius: 0;
        margin-bottom: 20px;
        box-shadow: 0 0 15px rgba(0, 255, 0, 0.2);
        color: #00ff00;
        transition: all 0.3s ease;
    }
    
    .message-card-all:hover {
        box-shadow: 0 0 25px rgba(0, 255, 0, 0.4);
        transform: translateY(-3px);
    }
    
    .message-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 15px;
        padding-bottom: 15px;
        border-bottom: 1px solid rgba(0, 255, 0, 0.3);
    }
    
    .message-sender {
        font-size: 1.2em;
        font-weight: 700;
        font-family: 'VT323', monospace;
        text-shadow: 0 0 5px #00ff00;
    }
    
    .message-badge {
        background: rgba(0, 255, 0, 0.2);
        border: 1px solid #00ff00;
        color: #00ff00;
        padding: 4px 12px;
        border-radius: 0;
        font-size: 0.7em;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }
    
    .message-timestamp {
        color: #00ff00;
        font-size: 0.9em;
        opacity: 0.7;
        font-family: 'Share Tech Mono', monospace;
    }
    
    .message-content {
        color: #00ff00;
        font-size: 1em;
        line-height: 1.7;
        margin: 15px 0;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    
    .message-footer {
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
        margin-top: 15px;
        padding-top: 15px;
        border-top: 1px solid rgba(0, 255, 0, 0.3);
        font-size: 0.9em;
        opacity: 0.8;
    }
    
    /* Status Badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.4rem 1rem;
        border-radius: 0;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        border: 1px solid;
    }
    
    .status-ready {
        background: rgba(0, 255, 0, 0.2);
        color: #00ff00;
        border-color: #00ff00;
        animation: pulse-green 2s infinite;
    }
    
    .status-sent {
        background: rgba(0, 255, 0, 0.1);
        color: #00ff00;
        border-color: #00ff00;
    }
    
    .status-pending {
        background: rgba(255, 255, 0, 0.1);
        color: #ffff00;
        border-color: #ffff00;
    }
    
    /* Section Headers */
    .section-header {
        font-size: 2rem;
        font-weight: 700;
        color: #00ff00;
        margin: 2rem 0 1.5rem 0;
        padding-bottom: 0.8rem;
        border-bottom: 2px solid #00ff00;
        font-family: 'VT323', monospace;
        text-shadow: 0 0 10px #00ff00;
        letter-spacing: 0.1em;
        position: relative;
    }
    
    .section-header::before {
        content: '> ';
        color: #00ff00;
    }
    
    .section-header::after {
        content: '';
        position: absolute;
        bottom: -2px;
        left: 0;
        width: 100px;
        height: 2px;
        background: #00ff00;
        box-shadow: 0 0 10px #00ff00;
    }
    
    /* Profile Banner */
    .client-profile-banner {
        background: rgba(0, 0, 0, 0.9);
        border: 2px solid #00ff00;
        padding: 30px;
        border-radius: 0;
        color: #00ff00;
        margin-bottom: 30px;
        box-shadow: 0 0 30px rgba(0, 255, 0, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    .client-profile-banner::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 100%;
        background: repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(0, 255, 0, 0.03) 2px,
            rgba(0, 255, 0, 0.03) 4px
        );
        pointer-events: none;
    }
    
    /* Timestamp */
    .timestamp {
        font-size: 0.85rem;
        color: #00ff00;
        text-align: right;
        opacity: 0.7;
        background: rgba(0, 255, 0, 0.1);
        padding: 0.3rem 0.8rem;
        border-radius: 0;
        display: inline-block;
        border: 1px solid rgba(0, 255, 0, 0.3);
        font-family: 'Share Tech Mono', monospace;
    }
    
    /* Stats Container */
    .stats-container {
        background: rgba(0, 0, 0, 0.9);
        border: 2px solid #00ff00;
        border-radius: 0;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 0 20px rgba(0, 255, 0, 0.2);
    }
    
    /* Activity Item */
    .activity-item {
        background: rgba(0, 0, 0, 0.9);
        border-left: 3px solid #00ff00;
        border-radius: 0;
        padding: 1rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 0 10px rgba(0, 255, 0, 0.2);
        transition: all 0.3s ease;
        color: #00ff00;
    }
    
    .activity-item:hover {
        transform: translateX(5px);
        box-shadow: 0 0 15px rgba(0, 255, 0, 0.3);
    }
    
    /* Filter Section */
    .filter-section {
        background: rgba(0, 0, 0, 0.9);
        border: 1px solid #00ff00;
        border-radius: 0;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 0 15px rgba(0, 255, 0, 0.2);
    }
    
    /* Chart Container */
    .chart-container {
        background: rgba(0, 0, 0, 0.9);
        border: 2px solid #00ff00;
        border-radius: 0;
        padding: 1.5rem;
        box-shadow: 0 0 20px rgba(0, 255, 0, 0.2);
        margin-bottom: 1.5rem;
    }
    
    /* Profile Badge */
    .profile-badge {
        width: 50px;
        height: 50px;
        border-radius: 0;
        background: rgba(0, 255, 0, 0.2);
        border: 2px solid #00ff00;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #00ff00;
        font-size: 1.5em;
        font-weight: 700;
        margin-right: 15px;
        text-shadow: 0 0 5px #00ff00;
        font-family: 'VT323', monospace;
    }
    
    /* LinkedIn Link */
    .linkedin-link {
        color: #00ff00;
        text-decoration: none;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 5px;
        transition: all 0.2s ease;
        text-shadow: 0 0 5px #00ff00;
    }
    
    .linkedin-link:hover {
        gap: 8px;
        text-shadow: 0 0 10px #00ff00;
    }
    
    .linkedin-badge {
        background: rgba(0, 255, 0, 0.2);
        border: 1px solid #00ff00;
        padding: 8px 16px;
        border-radius: 0;
        display: inline-block;
        margin-top: 15px;
        font-size: 0.9em;
        transition: all 0.3s ease;
    }
    
    .linkedin-badge:hover {
        background: rgba(0, 255, 0, 0.3);
        box-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
    }
    
    /* Date Divider */
    .conversation-date-divider {
        text-align: center;
        color: #00ff00;
        font-size: 0.9em;
        margin: 25px 0;
        position: relative;
        font-family: 'VT323', monospace;
        text-shadow: 0 0 5px #00ff00;
    }
    
    .conversation-date-divider::before,
    .conversation-date-divider::after {
        content: '';
        position: absolute;
        top: 50%;
        width: 40%;
        height: 1px;
        background: rgba(0, 255, 0, 0.5);
        box-shadow: 0 0 5px rgba(0, 255, 0, 0.5);
    }
    
    .conversation-date-divider::before {
        left: 0;
    }
    
    .conversation-date-divider::after {
        right: 0;
    }
    
    /* Auth Container */
    .auth-container {
        max-width: 600px;
        margin: 50px auto;
        background: rgba(0, 0, 0, 0.95);
        border: 2px solid #00ff00;
        padding: 40px;
        border-radius: 0;
        box-shadow: 0 0 30px rgba(0, 255, 0, 0.3);
        color: #00ff00;
    }
    
    /* Stat Box */
    .stat-box {
        background: rgba(0, 0, 0, 0.9);
        border: 2px solid #00ff00;
        padding: 25px;
        border-radius: 0;
        box-shadow: 0 0 15px rgba(0, 255, 0, 0.2);
        text-align: center;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .stat-box::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(0, 255, 0, 0.2), transparent);
        transition: left 0.5s;
    }
    
    .stat-box:hover {
        transform: translateY(-5px);
        box-shadow: 0 0 25px rgba(0, 255, 0, 0.4);
    }
    
    .stat-box:hover::before {
        left: 100%;
    }
    
    .stat-number {
        font-size: 3em;
        font-weight: 700;
        color: #00ff00;
        text-shadow: 0 0 10px #00ff00;
        font-family: 'VT323', monospace;
        letter-spacing: 0.05em;
    }
    
    .stat-label {
        color: #00ff00;
        font-size: 0.9em;
        margin-top: 8px;
        font-weight: 500;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        opacity: 0.8;
    }
    
    /* Streamlit Overrides */
    .stButton>button {
        background: rgba(0, 255, 0, 0.1);
        border: 2px solid #00ff00;
        color: #00ff00;
        border-radius: 0;
        font-family: 'Share Tech Mono', monospace;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        transition: all 0.3s ease;
        box-shadow: 0 0 10px rgba(0, 255, 0, 0.2);
    }
    
    .stButton>button:hover {
        background: rgba(0, 255, 0, 0.2);
        box-shadow: 0 0 20px rgba(0, 255, 0, 0.4);
        transform: scale(1.05);
    }
    
    .stTextInput>div>div>input,
    .stSelectbox>div>div>select,
    .stTextArea>div>div>textarea,
    .stNumberInput>div>div>input {
        background: rgba(0, 0, 0, 0.9);
        border: 1px solid #00ff00;
        color: #00ff00;
        border-radius: 0;
        font-family: 'Share Tech Mono', monospace;
    }
    
    .stTextInput>div>div>input:focus,
    .stSelectbox>div>div>select:focus,
    .stTextArea>div>div>textarea:focus {
        border-color: #00ff00;
        box-shadow: 0 0 10px rgba(0, 255, 0, 0.3);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(0, 0, 0, 0.5);
        padding: 10px;
        border: 1px solid rgba(0, 255, 0, 0.3);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(0, 0, 0, 0.9);
        border: 1px solid #00ff00;
        color: #00ff00;
        border-radius: 0;
        font-family: 'VT323', monospace;
        font-size: 1.1em;
        padding: 10px 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background: rgba(0, 255, 0, 0.2);
        box-shadow: 0 0 15px rgba(0, 255, 0, 0.3);
    }
    
    .stRadio>div {
        background: rgba(0, 0, 0, 0.9);
        border: 1px solid #00ff00;
        padding: 10px;
        border-radius: 0;
    }
    
    .stRadio>div>label>div {
        color: #00ff00;
    }
    
    .stCheckbox>label {
        color: #00ff00;
    }
    
    .stMarkdown {
        color: #00ff00;
    }
    
    .stDataFrame {
        border: 2px solid #00ff00;
        border-radius: 0;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background: rgba(0, 0, 0, 0.95);
        border-right: 2px solid #00ff00;
    }
    
    section[data-testid="stSidebar"] * {
        color: #00ff00;
    }
    
    /* Info/Warning/Error Boxes */
    .stAlert {
        background: rgba(0, 0, 0, 0.9);
        border: 1px solid #00ff00;
        color: #00ff00;
        border-radius: 0;
    }
    
    .stSuccess {
        background: rgba(0, 255, 0, 0.1);
        border: 1px solid #00ff00;
        color: #00ff00;
    }
    
    .stWarning {
        background: rgba(255, 255, 0, 0.1);
        border: 1px solid #ffff00;
        color: #ffff00;
    }
    
    .stError {
        background: rgba(255, 0, 0, 0.1);
        border: 1px solid #ff0000;
        color: #ff0000;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(0, 0, 0, 0.9);
        border: 1px solid #00ff00;
        color: #00ff00;
        border-radius: 0;
        font-family: 'VT323', monospace;
    }
    
    /* Progress Bar */
    .stProgress > div > div > div {
        background: #00ff00;
        box-shadow: 0 0 10px #00ff00;
    }
    
    /* Metrics */
    [data-testid="stMetric"] {
        background: rgba(0, 0, 0, 0.9);
        border: 1px solid #00ff00;
        padding: 15px;
        border-radius: 0;
    }
    
    [data-testid="stMetricValue"] {
        color: #00ff00;
        font-family: 'VT323', monospace;
        font-size: 2em;
        text-shadow: 0 0 10px #00ff00;
    }
    
    [data-testid="stMetricLabel"] {
        color: #00ff00;
        font-family: 'Share Tech Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    
    /* Terminal Effect */
    .terminal-text {
        font-family: 'Share Tech Mono', monospace;
        color: #00ff00;
        text-shadow: 0 0 5px #00ff00;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #000000;
        border: 1px solid rgba(0, 255, 0, 0.2);
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(0, 255, 0, 0.5);
        border: 1px solid #00ff00;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(0, 255, 0, 0.7);
        box-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
    }
    
    /* Loading Spinner */
    .stSpinner > div {
        border-color: #00ff00 transparent transparent transparent;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #00ff00;
        font-family: 'VT323', monospace;
        text-shadow: 0 0 5px #00ff00;
        letter-spacing: 0.05em;
    }
    
    /* Links */
    a {
        color: #00ff00;
        text-shadow: 0 0 5px #00ff00;
    }
    
    a:hover {
        color: #0f0;
        text-shadow: 0 0 10px #00ff00;
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
        st.error(f"[ERROR] Failed to initialize Google Sheets: {str(e)}")
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
        st.error(f"[ERROR] Failed to load {sheet_name}: {str(e)}")
        return pd.DataFrame()

# ------------------ CLIENT PROFILE SYSTEM ------------------ #
def get_client_from_url():
    """Extract client identifier from URL parameters"""
    query_params = st.query_params
    return query_params.get('client', 'donmenico')

def load_client_profile(client_id):
    """Load client-specific profile and preferences"""
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
    st.markdown("<div class='main-title'>⚡ MATRIX: ACCESS POINT ⚡</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>[ SECURE CONNECTION REQUIRED ]</div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
        
        st.markdown("### > UPLOAD CREDENTIALS")
        st.markdown("---")
        
        uploaded_file = st.file_uploader(
            "[ Google Service Account JSON ]",
            type=['json'],
            help="Upload your service account credentials",
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            try:
                credentials_json = uploaded_file.read().decode('utf-8')
                
                with st.spinner("[ AUTHENTICATING... ]"):
                    client = init_google_sheets(credentials_json)
                
                if client:
                    st.session_state.authenticated = True
                    st.session_state.gsheets_client = client
                    st.success("✓ ACCESS GRANTED")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("✗ ACCESS DENIED")
            except Exception as e:
                st.error(f"✗ AUTHENTICATION ERROR: {str(e)}")
        
        st.markdown("---")
        
        with st.expander("[ SETUP PROTOCOL ]", expanded=True):
            st.markdown("""
            **INITIALIZATION SEQUENCE:**
            
            **> STEP 1: CLOUD CONSOLE**
            - Navigate to console.cloud.google.com
            - Initialize new project matrix
            
            **> STEP 2: ENABLE APIS**
            - Activate Google Sheets API
            - Activate Google Drive API
            
            **> STEP 3: CREATE SERVICE ACCOUNT**
            - Generate service account credentials
            - Assign Editor role permissions
            
            **> STEP 4: DOWNLOAD KEYS**
            - Export JSON key file
            - Store securely
            
            **> STEP 5: SHARE SHEETS**
            - Grant service account access
            - Editor permissions required
            
            **> STEP 6: UPLOAD & CONNECT**
            - Upload JSON credentials above
            - Establish secure connection
            """)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.info("⚡ ENCRYPTED CONNECTION | NO DATA STORED")

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

def create_message_chart(df):
    """Create a message activity chart with Matrix theme"""
    if df.empty or 'date' not in df.columns:
        return None
    
    message_counts = df['date'].value_counts().sort_index()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=message_counts.index,
        y=message_counts.values,
        mode='lines+markers',
        line=dict(color='#00ff00', width=3),
        marker=dict(size=8, color='#00ff00', line=dict(color='#000', width=1)),
        fill='tozeroy',
        fillcolor='rgba(0, 255, 0, 0.2)'
    ))
    
    fig.update_layout(
        title="[ MESSAGE ACTIVITY TIMELINE ]",
        xaxis_title="DATE",
        yaxis_title="MESSAGE COUNT",
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0.9)',
        plot_bgcolor='rgba(0,0,0,0.9)',
        font=dict(family="Share Tech Mono", color='#00ff00'),
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

# ------------------ LEAD OUTREACH TAB ------------------ #
def show_lead_outreach():
    st.markdown("<div class='section-header'>TARGET ACQUISITION SYSTEM</div>", unsafe_allow_html=True)
    
    outreach_df = st.session_state.outreach_df
    
    if outreach_df.empty:
        st.warning("[ NO TARGET DATA LOADED ]")
        st.info("⚡ PROTOCOL: Load outreach sheet from sidebar menu")
        return
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{len(outreach_df)}</div>
            <div class="stat-label">TOTAL TARGETS</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        sent = len(outreach_df[outreach_df['status'] == 'sent']) if 'status' in outreach_df.columns else 0
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{sent}</div>
            <div class="stat-label">SENT</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        pending = len(outreach_df[outreach_df['status'] == 'pending']) if 'status' in outreach_df.columns else 0
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{pending}</div>
            <div class="stat-label">PENDING</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        ready = len(outreach_df[outreach_df['status'] == 'ready_to_send']) if 'status' in outreach_df.columns else 0
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{ready}</div>
            <div class="stat-label">READY</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Filters
    st.markdown("### > FILTER PARAMETERS")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        search_query = st.text_input("[ SEARCH ]", placeholder="Enter search term...", key="lead_search")
    
    with col2:
        status_options = ["All"]
        if 'status' in outreach_df.columns:
            status_options.extend(sorted(outreach_df['status'].dropna().unique().tolist()))
        status_filter = st.selectbox("[ STATUS ]", status_options)
    
    with col3:
        city_options = ["All"]
        if 'search_city' in outreach_df.columns:
            city_options.extend(sorted(outreach_df['search_city'].dropna().unique().tolist()))
        city_filter = st.selectbox("[ LOCATION ]", city_options)
    
    with col4:
        sort_columns = [col for col in ["timestamp", "profile_name", "status", "search_city"] if col in outreach_df.columns]
        sort_by = st.selectbox("[ SORT ]", sort_columns if sort_columns else ["Default"])
    
    # Apply filters
    filtered_df = outreach_df.copy()
    
    if search_query:
        mask = filtered_df.astype(str).apply(
            lambda x: x.str.contains(search_query, case=False, na=False)
        ).any(axis=1)
        filtered_df = filtered_df[mask]
    
    if status_filter != "All" and 'status' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['status'] == status_filter]
    
    if city_filter != "All" and 'search_city' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['search_city'] == city_filter]
    
    if sort_by != "Default" and sort_by in filtered_df.columns:
        filtered_df = filtered_df.sort_values(by=sort_by, ascending=False)
    
    st.markdown(f"**[ DISPLAYING {len(filtered_df)} TARGETS ]**")
    
    # View mode selection
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        view_mode = st.radio("[ VIEW MODE ]", ["CARDS", "TABLE", "COMPACT"], horizontal=True, key="lead_view_mode")
    with col2:
        leads_per_page = st.selectbox("[ PER PAGE ]", [10, 25, 50, 100], index=1, key="lead_per_page")
    with col3:
        total_pages = max(1, (len(filtered_df) - 1) // leads_per_page + 1) if len(filtered_df) > 0 else 1
        page_num = st.number_input("[ PAGE ]", min_value=1, max_value=total_pages, value=1, key="lead_page_num")
    
    st.markdown("---")
    
    if filtered_df.empty:
        st.warning("[ NO TARGETS MATCH FILTER CRITERIA ]")
        st.info("⚡ ADJUST PARAMETERS AND RETRY")
        return
    
    # Pagination
    start_idx = (page_num - 1) * leads_per_page
    end_idx = min(start_idx + leads_per_page, len(filtered_df))
    paginated_df = filtered_df.iloc[start_idx:end_idx]
    
    # Display based on view mode
    if view_mode == "CARDS":
        display_leads_cards(paginated_df)
    elif view_mode == "TABLE":
        display_leads_table(paginated_df)
    else:
        display_leads_compact(paginated_df)
    
    # Bulk actions
    if not filtered_df.empty:
        st.markdown("---")
        st.markdown("### > BULK OPERATIONS")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            bulk_count = st.number_input("[ TARGET COUNT ]", min_value=1, max_value=len(filtered_df), value=min(5, len(filtered_df)), key="bulk_count")
        
        with col2:
            if st.button("⚡ EXECUTE BULK SEND", use_container_width=True, key="bulk_send"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, (i, row) in enumerate(filtered_df.head(bulk_count).iterrows()):
                    lead_name = row.get('profile_name', row.get('name', 'TARGET'))
                    status_text.text(f"[ SENDING TO {lead_name}... ]")
                    st.session_state.sent_leads.add(i)
                    
                    st.session_state.activity_log.append({
                        "type": "BULK_SEND",
                        "details": f"Message to {lead_name}",
                        "status": "✓ SUCCESS",
                        "time": datetime.now().strftime("%H:%M:%S")
                    })
                    
                    progress_bar.progress((idx + 1) / bulk_count)
                    time.sleep(0.3)
                
                status_text.text("✓ BULK OPERATION COMPLETE")
                st.success(f"✓ {bulk_count} MESSAGES TRANSMITTED")
                time.sleep(2)
                st.rerun()
        
        with col3:
            if st.button("📊 EXPORT DATA", use_container_width=True, key="export_csv"):
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="⬇ DOWNLOAD",
                    data=csv,
                    file_name=f"matrix_targets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_csv"
                )
        
        with col4:
            if st.button("🔄 REFRESH DATA", use_container_width=True, key="refresh_leads"):
                st.cache_data.clear()
                st.rerun()

def display_leads_cards(df):
    """Display leads in card format"""
    if df.empty:
        st.info("[ NO DATA ]")
        return
    
    for idx, (i, row) in enumerate(df.iterrows()):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            name = str(row.get('profile_name', row.get('name', 'UNKNOWN_TARGET')))
            location = str(row.get('profile_location', row.get('location', 'UNKNOWN')))
            tagline = str(row.get('profile_tagline', row.get('tagline', 'NO DATA')))
            linkedin_url = str(row.get('linkedin_url', '#'))
            message = str(row.get('linkedin_message', row.get('message', 'NO MESSAGE')))
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
            sent_indicator = "✓ TRANSMITTED" if is_sent else ""
            
            st.markdown(f"""
            <div class="lead-card">
                <div class="lead-title">
                    > {name} {sent_indicator}
                </div>
                <div class="lead-sub">LOCATION: {location}</div>
                <div class="lead-sub">PROFILE: {tagline}</div>
                <div class="lead-sub">SEARCH: {search_term} | {search_city}</div>
                <div class="lead-sub"><a href="{linkedin_url}" target="_blank" style="color: #00ff00; text-decoration: none;">⚡ ACCESS PROFILE →</a></div>
                <div class="lead-msg">MESSAGE: {message}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem;">
                    <span class="status-badge {status_class}">{status.replace('_', ' ').upper()}</span>
                    <span class="timestamp">[ {timestamp_str} ]</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("**[ ACTIONS ]**")
            
            if st.button("⚡ SEND", key=f"send_{i}_{idx}", disabled=is_sent, use_container_width=True):
                st.session_state.sent_leads.add(i)
                st.session_state.activity_log.append({
                    "type": "MESSAGE_SENT",
                    "details": f"To {name}",
                    "status": "✓ SUCCESS",
                    "time": datetime.now().strftime("%H:%M:%S")
                })
                st.success(f"✓ SENT TO {name}")
                time.sleep(1)
                st.rerun()
            
            if st.button("📋 COPY", key=f"copy_{i}_{idx}", use_container_width=True):
                st.info("✓ DATA COPIED")
            
            if st.button("⭐ SAVE", key=f"save_{i}_{idx}", use_container_width=True):
                st.info("✓ TARGET SAVED")
            
            is_selected = i in st.session_state.selected_leads
            if st.checkbox("[ SELECT ]", key=f"select_{i}_{idx}", value=is_selected):
                if i not in st.session_state.selected_leads:
                    st.session_state.selected_leads.append(i)
            else:
                if i in st.session_state.selected_leads:
                    st.session_state.selected_leads.remove(i)

def display_leads_table(df):
    """Display leads in table format"""
    if df.empty:
        st.info("[ NO DATA ]")
        return
    
    display_columns = []
    important_columns = ['profile_name', 'profile_location', 'status', 'timestamp', 'search_term', 'search_city']
    display_columns = [col for col in important_columns if col in df.columns]
    
    remaining_columns = [col for col in df.columns if col not in display_columns]
    display_columns.extend(remaining_columns[:5])
    
    if display_columns:
        st.dataframe(df[display_columns], use_container_width=True, height=600)
    else:
        st.dataframe(df, use_container_width=True, height=600)

def display_leads_compact(df):
    """Display leads in compact format"""
    if df.empty:
        st.info("[ NO DATA ]")
        return
    
    for idx, (i, row) in enumerate(df.iterrows()):
        name = str(row.get('profile_name', row.get('name', 'UNKNOWN_TARGET')))
        location = str(row.get('profile_location', row.get('location', 'UNKNOWN')))
        status = str(row.get('status', 'unknown'))
        
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        
        with col1:
            st.write(f"**> {name}**")
        with col2:
            st.write(f"LOC: {location}")
        with col3:
            st.write(f"[{status.upper()}]")
        with col4:
            is_sent = status == 'sent' or i in st.session_state.sent_leads
            if st.button("⚡", key=f"send_compact_{i}_{idx}", help="Send message", disabled=is_sent):
                st.session_state.sent_leads.add(i)
                st.success("✓ SENT")
                st.rerun()

# ------------------ SEARCH INTERFACE TAB ------------------ #
def show_search_interface(webhook_url):
    st.markdown("<div class='section-header'>TARGET SEARCH PROTOCOL</div>", unsafe_allow_html=True)
    
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
        st.markdown("### > SEARCH PARAMETERS")
        
        with st.form("search_form"):
            search_term = st.selectbox(
                "[ JOB TITLE / ROLE ]",
                SEARCH_TERMS,
                help="Select target job title"
            )
            
            col_a, col_b = st.columns(2)
            with col_a:
                city = st.selectbox("[ CITY ]", CITIES)
            with col_b:
                country = st.selectbox("[ COUNTRY ]", COUNTRIES)
            
            num_leads = st.slider("[ TARGET COUNT ]", 1, 50, 10)
            
            notes = st.text_area("[ NOTES (OPTIONAL) ]", placeholder="Add search notes...")
            
            submitted = st.form_submit_button("⚡ INITIATE SEARCH", use_container_width=True, type="primary")
            
            if submitted:
                if not webhook_url:
                    st.error("✗ WEBHOOK NOT CONFIGURED")
                else:
                    payload = {
                        "search_term": search_term,
                        "city": city,
                        "country": country,
                        "num_leads": num_leads,
                        "notes": notes,
                        "timestamp": datetime.utcnow().isoformat(),
                        "source": "matrix_interface",
                        "client": st.session_state.current_client['name'] if st.session_state.current_client else "UNKNOWN"
                    }
                    
                    try:
                        with st.spinner("[ SEARCHING NETWORK... ]"):
                            response = requests.post(webhook_url, json=payload, timeout=10)
                        
                        if response.status_code == 200:
                            st.success(f"✓ SEARCH INITIATED: {search_term} | {city}, {country}")
                            st.info("⚡ RESULTS WILL POPULATE IN OUTREACH SHEET")
                            st.balloons()
                            
                            st.session_state.activity_log.append({
                                "type": "SEARCH",
                                "details": f"{search_term} | {city}, {country}",
                                "status": "✓ SUCCESS",
                                "time": datetime.now().strftime("%H:%M:%S")
                            })
                            
                            st.session_state.webhook_history.append({
                                "search": f"{search_term} - {city}",
                                "status": "SUCCESS",
                                "time": datetime.now().strftime("%H:%M:%S"),
                                "leads": num_leads
                            })
                        else:
                            st.error(f"✗ ERROR: HTTP {response.status_code}")
                            st.session_state.activity_log.append({
                                "type": "SEARCH",
                                "details": f"{search_term} | {city}",
                                "status": f"✗ FAILED ({response.status_code})",
                                "time": datetime.now().strftime("%H:%M:%S")
                            })
                    
                    except requests.exceptions.Timeout:
                        st.warning("⚠ TIMEOUT - SEARCH MAY STILL PROCESS")
                    except Exception as e:
                        st.error(f"✗ ERROR: {str(e)}")
    
    with col2:
        st.markdown("### > ACTIVITY LOG")
        
        if st.session_state.webhook_history:
            st.markdown("#### [ RECENT SEARCHES ]")
            recent_searches = st.session_state.webhook_history[-5:]
            
            for search in reversed(recent_searches):
                st.markdown(f"""
                <div style="background: rgba(0, 0, 0, 0.9); border: 1px solid #00ff00; padding: 12px; border-radius: 0; margin-bottom: 8px; box-shadow: 0 0 10px rgba(0, 255, 0, 0.2);">
                    <strong>> {search['search']}</strong><br>
                    <small>TIME: {search['time']}</small><br>
                    <small>TARGETS: {search['leads']}</small><br>
                    <small>STATUS: {search['status']}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("[ NO RECENT ACTIVITY ]")
        
        st.markdown("---")
        
        st.markdown("#### [ STATISTICS ]")
        total_searches = len([log for log in st.session_state.activity_log if log.get('type') == 'SEARCH'])
        successful_searches = len([log for log in st.session_state.activity_log if log.get('type') == 'SEARCH' and 'SUCCESS' in log.get('status', '')])
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("TOTAL", total_searches)
        with col_b:
            success_rate = (successful_searches / total_searches * 100) if total_searches > 0 else 0
            st.metric("SUCCESS", f"{success_rate:.0f}%")
        
        st.markdown("---")
        
        st.markdown("#### [ QUICK ACTIONS ]")
        if st.button("🔄 REFRESH DATA", use_container_width=True):
            st.cache_data.clear()
            st.info("⚡ REFRESH OUTREACH DATA VIA SIDEBAR")
        
        if st.button("📊 VIEW TARGETS", use_container_width=True):
            st.info("⚡ NAVIGATE TO 'TARGET ACQUISITION' TAB")

# ------------------ ADVANCED ANALYTICS TAB ------------------ #
def show_advanced_analytics():
    st.markdown("<div class='section-header'>INTELLIGENCE ANALYTICS</div>", unsafe_allow_html=True)
    
    chat_df = st.session_state.chat_df
    outreach_df = st.session_state.outreach_df
    
    if chat_df.empty and outreach_df.empty:
        st.warning("[ NO DATA LOADED ]")
        return
    
    tab1, tab2, tab3, tab4 = st.tabs(["[ OVERVIEW ]", "[ GEOGRAPHIC ]", "[ TIMELINE ]", "[ PERFORMANCE ]"])
    
    with tab1:
        show_overview_analytics(chat_df, outreach_df)
    
    with tab2:
        show_geographic_analytics(outreach_df)
    
    with tab3:
        show_timeline_analytics(chat_df, outreach_df)
    
    with tab4:
        show_performance_analytics(outreach_df)

def show_overview_analytics(chat_df, outreach_df):
    """Show overview analytics"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### [ CHAT ANALYTICS ]")
        if not chat_df.empty:
            if 'date' in chat_df.columns:
                daily_activity = chat_df.groupby('date').size().reset_index(name='messages')
                
                fig = px.line(
                    daily_activity,
                    x='date',
                    y='messages',
                    title="[ DAILY MESSAGE ACTIVITY ]",
                    markers=True
                )
                fig.update_traces(line_color='#00ff00', marker_color='#00ff00')
                fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0.9)',
                    plot_bgcolor='rgba(0,0,0,0.9)',
                    font=dict(family="Share Tech Mono", color='#00ff00')
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("[ NO CHAT DATA ]")
    
    with col2:
        st.markdown("#### [ OUTREACH ANALYTICS ]")
        if not outreach_df.empty and 'status' in outreach_df.columns:
            status_counts = outreach_df['status'].value_counts()
            
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="[ TARGET STATUS DISTRIBUTION ]",
                hole=0.4
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0.9)',
                plot_bgcolor='rgba(0,0,0,0.9)',
                font=dict(family="Share Tech Mono", color='#00ff00')
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("[ NO OUTREACH DATA ]")

def show_geographic_analytics(outreach_df):
    """Show geographic analytics"""
    if outreach_df.empty:
        st.info("[ NO GEOGRAPHIC DATA ]")
        return
    
    if 'search_city' in outreach_df.columns:
        city_counts = outreach_df['search_city'].value_counts().head(15)
        
        fig = px.bar(
            x=city_counts.values,
            y=city_counts.index,
            orientation='h',
            title="[ TOP CITIES BY TARGET COUNT ]",
            labels={'x': 'TARGET COUNT', 'y': 'CITY'},
            color=city_counts.values,
            color_continuous_scale=['#003300', '#00ff00']
        )
        fig.update_layout(
            showlegend=False,
            height=500,
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0.9)',
            plot_bgcolor='rgba(0,0,0,0.9)',
            font=dict(family="Share Tech Mono", color='#00ff00')
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("[ NO CITY DATA ]")

def show_timeline_analytics(chat_df, outreach_df):
    """Show timeline analytics"""
    col1, col2 = st.columns(2)
    
    with col1:
        if not chat_df.empty and 'date' in chat_df.columns:
            st.markdown("#### [ CHAT TIMELINE ]")
            daily_chats = chat_df.groupby('date').size().tail(30).reset_index(name='count')
            
            fig = px.area(
                daily_chats,
                x='date',
                y='count',
                title="[ LAST 30 DAYS - CHAT ACTIVITY ]"
            )
            fig.update_traces(fillcolor='rgba(0, 255, 0, 0.3)', line_color='#00ff00')
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0.9)',
                plot_bgcolor='rgba(0,0,0,0.9)',
                font=dict(family="Share Tech Mono", color='#00ff00')
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("[ NO CHAT TIMELINE ]")
    
    with col2:
        if not outreach_df.empty and 'timestamp' in outreach_df.columns:
            st.markdown("#### [ OUTREACH TIMELINE ]")
            try:
                outreach_df['date'] = pd.to_datetime(outreach_df['timestamp']).dt.date
                daily_outreach = outreach_df.groupby('date').size().tail(30).reset_index(name='count')
                
                fig = px.area(
                    daily_outreach,
                    x='date',
                    y='count',
                    title="[ LAST 30 DAYS - OUTREACH ACTIVITY ]"
                )
                fig.update_traces(fillcolor='rgba(0, 255, 0, 0.3)', line_color='#00ff00')
                fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0.9)',
                    plot_bgcolor='rgba(0,0,0,0.9)',
                    font=dict(family="Share Tech Mono", color='#00ff00')
                )
                st.plotly_chart(fig, use_container_width=True)
            except:
                st.info("[ TIMELINE PARSE ERROR ]")
        else:
            st.info("[ NO OUTREACH TIMELINE ]")

def show_performance_analytics(outreach_df):
    """Show performance analytics"""
    if outreach_df.empty:
        st.info("[ NO PERFORMANCE DATA ]")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'status' in outreach_df.columns:
            sent_count = len(outreach_df[outreach_df['status'] == 'sent'])
            total_count = len(outreach_df)
            conversion_rate = (sent_count / total_count * 100) if total_count > 0 else 0
            
            st.metric(
                "CONVERSION RATE",
                f"{conversion_rate:.1f}%",
                delta=f"{sent_count} / {total_count}"
            )
    
    with col2:
        if 'search_term' in outreach_df.columns:
            unique_terms = outreach_df['search_term'].nunique()
            st.metric("SEARCH DIVERSITY", unique_terms, delta="Unique titles")
    
    with col3:
        if 'search_city' in outreach_df.columns:
            unique_cities = outreach_df['search_city'].nunique()
            st.metric("GEOGRAPHIC REACH", unique_cities, delta="Unique cities")
    
    if 'timestamp' in outreach_df.columns and 'status' in outreach_df.columns:
        try:
            outreach_df['date'] = pd.to_datetime(outreach_df['timestamp']).dt.date
            daily_performance = outreach_df.groupby(['date', 'status']).size().unstack(fill_value=0)
            
            if not daily_performance.empty:
                fig = px.area(
                    daily_performance.reset_index(),
                    x='date',
                    y=daily_performance.columns.tolist(),
                    title="[ DAILY PERFORMANCE BY STATUS ]"
                )
                fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0.9)',
                    plot_bgcolor='rgba(0,0,0,0.9)',
                    font=dict(family="Share Tech Mono", color='#00ff00')
                )
                st.plotly_chart(fig, use_container_width=True)
        except:
            st.info("[ PERFORMANCE TRENDS UNAVAILABLE ]")

# ------------------ OVERVIEW TAB ------------------ #
def show_overview():
    st.markdown("<div class='section-header'>SYSTEM DASHBOARD</div>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    chat_df = st.session_state.chat_df
    outreach_df = st.session_state.outreach_df
    
    with col1:
        total_chats = len(chat_df)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_chats}</div>
            <div class="metric-label">TOTAL CHATS</div>
            <div class="metric-trend">CONVERSATIONS</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_leads = len(outreach_df)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_leads}</div>
            <div class="metric-label">TOTAL TARGETS</div>
            <div class="metric-trend">OUTREACH DATABASE</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        sent_count = len(outreach_df[outreach_df['status'] == 'sent']) if 'status' in outreach_df.columns and not outreach_df.empty else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{sent_count}</div>
            <div class="metric-label">TRANSMITTED</div>
            <div class="metric-trend">MESSAGES SENT</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        contacts = get_contact_info(chat_df, {
            'name': MY_PROFILE['name'],
            'url': MY_PROFILE['url']
        }) if not chat_df.empty else {}
        contact_count = len(contacts)
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{contact_count}</div>
            <div class="metric-label">ACTIVE CONTACTS</div>
            <div class="metric-trend">UNIQUE USERS</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("### > RECENT ACTIVITY")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### [ CHAT ACTIVITY ]")
        if not chat_df.empty and 'date' in chat_df.columns:
            try:
                daily_chats = chat_df.groupby('date').size().tail(7).reset_index()
                daily_chats.columns = ['Date', 'Messages']
                
                fig = px.bar(
                    daily_chats,
                    x='Date',
                    y='Messages',
                    title="[ LAST 7 DAYS ]",
                    color='Messages',
                    color_continuous_scale=['#003300', '#00ff00']
                )
                fig.update_layout(
                    showlegend=False,
                    height=300,
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0.9)',
                    plot_bgcolor='rgba(0,0,0,0.9)',
                    font=dict(family="Share Tech Mono", color='#00ff00')
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.info("[ NO DATE DATA ]")
        else:
            st.info("[ NO CHAT DATA LOADED ]")
    
    with col2:
        st.markdown("#### [ OUTREACH STATUS ]")
        if not outreach_df.empty and 'status' in outreach_df.columns:
            status_counts = outreach_df['status'].value_counts()
            
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="[ TARGET STATUS ]",
                hole=0.4
            )
            fig.update_layout(
                height=300,
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0.9)',
                plot_bgcolor='rgba(0,0,0,0.9)',
                font=dict(family="Share Tech Mono", color='#00ff00')
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("[ NO OUTREACH DATA LOADED ]")
    
    st.markdown("---")
    
    st.markdown("### > ACTIVITY LOG")
    
    if st.session_state.activity_log:
        recent_activities = st.session_state.activity_log[-10:]
        
        for activity in reversed(recent_activities):
            st.markdown(f"""
            <div class="activity-item">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>> {activity.get('type', 'ACTIVITY')}</strong>: {activity.get('details', 'NO DETAILS')}
                        <br><small>STATUS: {activity.get('status', 'UNKNOWN')}</small>
                    </div>
                    <div class="timestamp">[ {activity.get('time', 'N/A')} ]</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("[ NO RECENT ACTIVITY ]")

# ------------------ CHAT ANALYTICS TAB ------------------ #
def show_chat_analytics():
    st.markdown("<div class='section-header'>CHAT INTELLIGENCE SYSTEM</div>", unsafe_allow_html=True)
    
    chat_df = st.session_state.chat_df
    
    if chat_df.empty:
        st.warning("[ NO CHAT DATA LOADED ]")
        st.info("⚡ PROTOCOL: Load chat history from sidebar")
        return
    
    my_profile = {
        'name': MY_PROFILE['name'],
        'url': MY_PROFILE['url']
    }
    
    contacts = get_contact_info(chat_df, my_profile)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{len(chat_df)}</div>
            <div class="stat-label">TOTAL MESSAGES</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{len(contacts)}</div>
            <div class="stat-label">CONTACTS</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        my_messages = sum(1 for _, row in chat_df.iterrows() if is_me(row.get('sender_name', ''), row.get('sender_linkedin_url', ''), my_profile))
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{my_messages}</div>
            <div class="stat-label">SENT BY YOU</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        received = len(chat_df) - my_messages
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{received}</div>
            <div class="stat-label">RECEIVED</div>
        </div>
        """, unsafe_allow_html=True)
    
    with st.expander("[ VIEW MESSAGE ACTIVITY CHART ]", expanded=False):
        chart = create_message_chart(chat_df)
        if chart:
            st.plotly_chart(chart, use_container_width=True)
    
    st.markdown("---")
    
    view_mode = st.radio(
        "### > SELECT VIEW MODE",
        ["[ ALL CONTACTS ]", "[ CONTACT CONVERSATION ]", "[ ALL MESSAGES ]"],
        horizontal=True
    )
    
    st.markdown("---")
    
    if view_mode == "[ ALL CONTACTS ]":
        show_all_contacts(contacts)
    elif view_mode == "[ CONTACT CONVERSATION ]":
        show_contact_conversation(contacts, chat_df, my_profile)
    else:
        show_all_messages_view(chat_df, my_profile)

def show_all_contacts(contacts):
    """Display all contacts"""
    st.subheader("[ ALL CONTACTS ]")
    
    if not contacts:
        st.info("[ NO CONTACTS FOUND ]")
        return
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("[ SEARCH ]", "", key="contact_search")
    with col2:
        sort_by = st.selectbox("[ SORT ]", ["Name", "Messages", "Recent"])
    
    filtered_contacts = {
        url: info for url, info in contacts.items()
        if not search or search.lower() in info['name'].lower()
    }
    
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
    
    st.markdown(f"**[ DISPLAYING {len(filtered_contacts)} CONTACTS ]**")
    st.markdown("")
    
    cols = st.columns(2)
    
    for idx, (url, info) in enumerate(filtered_contacts.items()):
        col = cols[idx % 2]
        
        message_count = len(info['messages'])
        initials = get_initials(info['name'])
        
        with col:
            st.markdown(f"""
            <div class="contact-card">
                <div style="display: flex; align-items: center; margin-bottom: 15px;">
                    <div class="profile-badge">{initials}</div>
                    <div>
                        <div class="contact-name">> {info['name']}</div>
                    </div>
                </div>
                <div class="contact-stats">
                    <div class="contact-stat-item">
                        MSG: <strong>{message_count}</strong>
                    </div>
                    <div class="contact-stat-item">
                        SENT: <strong>{info['sent_count']}</strong>
                    </div>
                    <div class="contact-stat-item">
                        RECV: <strong>{info['received_count']}</strong>
                    </div>
                </div>
                <p style="margin-top: 12px; opacity: 0.9;">
                    <strong>LAST CONTACT:</strong> {info['last_contact']}
                </p>
                <div class="linkedin-badge">
                    <a href="{url}" target="_blank" style="color: #00ff00; text-decoration: none;">
                        ⚡ ACCESS PROFILE →
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)

def show_contact_conversation(contacts, chat_df, my_profile):
    """Display conversation with specific contact"""
    st.subheader("[ CONTACT CONVERSATION ]")
    
    if not contacts:
        st.info("[ NO CONTACTS ]")
        return
    
    contact_names = {info['name']: url for url, info in contacts.items()}
    selected_name = st.selectbox("[ SELECT CONTACT ]", list(contact_names.keys()))
    
    if not selected_name:
        return
    
    selected_url = contact_names[selected_name]
    contact_info = contacts[selected_url]
    
    message_count = len(contact_info['messages'])
    initials = get_initials(contact_info['name'])
    
    st.markdown(f"""
    <div class='client-profile-banner'>
        <div style="display: flex; align-items: center; margin-bottom: 15px;">
            <div class="profile-badge" style="width: 60px; height: 60px; font-size: 2em;">{initials}</div>
            <div>
                <h2 style="margin: 0; color: #00ff00;">> {contact_info['name']}</h2>
                <p style="margin: 5px 0 0 0; opacity: 0.9; color: #00ff00;">CONTACT PROFILE</p>
            </div>
        </div>
        <div style="display: flex; gap: 15px; flex-wrap: wrap;">
            <div style="background: rgba(0, 255, 0, 0.2); border: 1px solid #00ff00; padding: 10px 18px; border-radius: 0;">
                MSG: <strong>{message_count}</strong>
            </div>
            <div style="background: rgba(0, 255, 0, 0.2); border: 1px solid #00ff00; padding: 10px 18px; border-radius: 0;">
                SENT: <strong>{contact_info['sent_count']}</strong>
            </div>
            <div style="background: rgba(0, 255, 0, 0.2); border: 1px solid #00ff00; padding: 10px 18px; border-radius: 0;">
                RECV: <strong>{contact_info['received_count']}</strong>
            </div>
        </div>
        <div class="linkedin-badge">
            <a href="{contact_info['url']}" target="_blank" style="color: #00ff00; text-decoration: none;">
                ⚡ ACCESS PROFILE →
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### > CONVERSATION HISTORY")
    
    messages = sorted(
        contact_info['messages'],
        key=lambda x: (x.get('date', ''), x.get('time', ''))
    )
    
    current_date = None
    
    for msg in messages:
        sender_name = msg.get('sender_name', '')
        sender_url = msg.get('sender_linkedin_url', '')
        message_text = msg.get('message', '')
        date = msg.get('date', '')
        time_str = msg.get('time', '')
        shared_content = msg.get('shared_content', '')
        
        if date and date != current_date:
            st.markdown(f'<div class="conversation-date-divider">[ {date} ]</div>', unsafe_allow_html=True)
            current_date = date
        
        is_my_message = is_me(sender_name, sender_url, my_profile)
        
        if is_my_message:
            st.markdown(f"""
            <div class="message-sent">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong>> YOU</strong>
                    <span style="font-size: 0.85em; opacity: 0.8;">[ {time_str} ]</span>
                </div>
                <p style="margin: 0; line-height: 1.6;">{message_text}</p>
                {f'<div style="background: rgba(0, 255, 0, 0.2); padding: 8px; border-radius: 0; margin-top: 8px; font-size: 0.9em; border: 1px solid #00ff00;">ATTACHMENT: {shared_content}</div>' if shared_content else ''}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="message-received">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong style="color: #00ff00;">> {sender_name}</strong>
                    <span style="font-size: 0.85em; opacity: 0.8;">[ {time_str} ]</span>
                </div>
                <p style="margin: 0; line-height: 1.6;">{message_text}</p>
                {f'<div style="background: rgba(0, 255, 0, 0.1); padding: 8px; border-radius: 0; margin-top: 8px; font-size: 0.9em; border: 1px solid rgba(0, 255, 0, 0.5);">ATTACHMENT: {shared_content}</div>' if shared_content else ''}
            </div>
            """, unsafe_allow_html=True)

def show_all_messages_view(chat_df, my_profile):
    """Display all messages"""
    st.subheader("[ ALL MESSAGES ]")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("[ SEARCH ]", "", placeholder="Search messages...")
    with col2:
        show_only = st.selectbox("[ FILTER ]", ["All", "Sent by Me", "Received"])
    with col3:
        sort_order = st.selectbox("[ SORT ]", ["Newest First", "Oldest First"])
    
    filtered_df = chat_df.copy()
    
    if search:
        mask = filtered_df.astype(str).apply(
            lambda x: x.str.contains(search, case=False, na=False)
        ).any(axis=1)
        filtered_df = filtered_df[mask]
    
    if show_only == "Sent by Me":
        filtered_df = filtered_df[filtered_df.apply(
            lambda row: is_me(row.get('sender_name', ''), row.get('sender_linkedin_url', ''), my_profile),
            axis=1
        )]
    elif show_only == "Received":
        filtered_df = filtered_df[filtered_df.apply(
            lambda row: not is_me(row.get('sender_name', ''), row.get('sender_linkedin_url', ''), my_profile),
            axis=1
        )]
    
    if 'date' in filtered_df.columns and 'time' in filtered_df.columns:
        filtered_df = filtered_df.sort_values(
            by=['date', 'time'],
            ascending=(sort_order == "Oldest First")
        )
    
    st.markdown(f"**[ DISPLAYING {len(filtered_df)} MESSAGES ]**")
    st.markdown("---")
    
    if filtered_df.empty:
        st.info("[ NO MESSAGES MATCH FILTER ]")
        return
    
    for idx, (i, row) in enumerate(filtered_df.iterrows()):
        sender_name = str(row.get('sender_name', 'UNKNOWN'))
        sender_url = str(row.get('sender_linkedin_url', ''))
        lead_name = str(row.get('lead_name', ''))
        lead_url = str(row.get('lead_linkedin_url', ''))
        message = str(row.get('message', ''))
        date = str(row.get('date', ''))
        time_str = str(row.get('time', ''))
        shared_content = str(row.get('shared_content', ''))
        
        is_my_message = is_me(sender_name, sender_url, my_profile)
        
        if is_my_message:
            contact_name = lead_name
            contact_url = lead_url
            badge_text = "YOU"
            badge_style = "background: rgba(0, 255, 0, 0.2); border: 1px solid #00ff00;"
        else:
            contact_name = sender_name
            contact_url = sender_url
            badge_text = "RECEIVED"
            badge_style = "background: rgba(0, 255, 0, 0.1); border: 1px solid #00ff00;"
        
        st.markdown(f"""
        <div class="message-card-all">
            <div class="message-header">
                <div>
                    <div class="message-sender">
                        > {sender_name}
                        <span class="message-badge" style="{badge_style}">{badge_text}</span>
                    </div>
                </div>
                <div class="message-timestamp">
                    [ {date} • {time_str} ]
                </div>
            </div>
            
            <div class="message-content">
                {message}
            </div>
            
            <div class="message-footer">
                <span>
                    <strong>CONTACT:</strong> {contact_name if contact_name else 'N/A'}
                </span>
                {f'<span><strong>ATTACHMENT:</strong> {shared_content}</span>' if shared_content else ''}
                {f'<a href="{contact_url}" target="_blank" class="linkedin-link">⚡ VIEW PROFILE →</a>' if contact_url else ''}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ------------------ MAIN FUNCTION ------------------ #
def main():
    if not st.session_state.authenticated:
        authenticate_user()
        return
    
    if not st.session_state.current_client:
        st.session_state.current_client = load_client_profile('donmenico')
    
    st.markdown("<div class='main-title'>⚡ MATRIX INTELLIGENCE SYSTEM ⚡</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sub-title'>[ OPERATOR: {st.session_state.current_client['name']} ]</div>", unsafe_allow_html=True)
    
    with st.sidebar:
        st.header("⚙ SYSTEM CONTROL")
        
        st.markdown("---")
        st.markdown("### > OPERATOR PROFILE")
        st.markdown(f"""
        <div style="background: rgba(0, 0, 0, 0.9); border: 2px solid #00ff00; padding: 20px; border-radius: 0; color: #00ff00; margin-bottom: 15px; box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);">
            <h3 style="margin: 0 0 10px 0; color: #00ff00; font-family: 'VT323', monospace; text-shadow: 0 0 5px #00ff00;">> {st.session_state.current_client['name']}</h3>
            <a href="{st.session_state.current_client['linkedin_url']}" target="_blank" style="color: #00ff00; text-decoration: none; text-shadow: 0 0 5px #00ff00;">
                ⚡ ACCESS PROFILE →
            </a>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.subheader("[ DATA CONFIGURATION ]")
        
        st.info("⚡ DEFAULT CONFIG LOADED")
        
        with st.expander("[ VIEW DETAILS ]"):
            st.text(f"Chat Sheet: {CHAT_SPREADSHEET_ID[:20]}...")
            st.text(f"Sheet Name: {CHAT_SHEET_NAME}")
            st.text(f"Outreach: {OUTREACH_SPREADSHEET_ID[:20]}...")
            st.text(f"Sheet Name: {OUTREACH_SHEET_NAME}")
            st.text(f"Webhook: {WEBHOOK_URL[:30]}...")
        
        st.markdown("---")
        
        if st.button("⚡ LOAD/REFRESH DATA", use_container_width=True):
            with st.spinner("[ LOADING DATA... ]"):
                try:
                    st.session_state.chat_df = load_sheet_data(
                        st.session_state.gsheets_client,
                        CHAT_SPREADSHEET_ID,
                        CHAT_SHEET_NAME
                    )
                    if not st.session_state.chat_df.empty:
                        st.success(f"✓ LOADED {len(st.session_state.chat_df)} CHAT MESSAGES")
                    
                    st.session_state.outreach_df = load_sheet_data(
                        st.session_state.gsheets_client,
                        OUTREACH_SPREADSHEET_ID,
                        OUTREACH_SHEET_NAME
                    )
                    if not st.session_state.outreach_df.empty:
                        st.success(f"✓ LOADED {len(st.session_state.outreach_df)} TARGETS")
                    
                    st.session_state.last_refresh = datetime.utcnow()
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"✗ ERROR: {str(e)}")
        
        st.markdown("---")
        
        st.subheader("[ QUICK STATS ]")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("CHATS", len(st.session_state.chat_df))
        with col2:
            st.metric("TARGETS", len(st.session_state.outreach_df))
        
        st.markdown(f"""
        <div style="background: rgba(0, 255, 0, 0.1); border: 1px solid #00ff00; padding: 8px; border-radius: 0; margin-top: 10px;">
            <small style="color: #00ff00;">LAST REFRESH: {st.session_state.last_refresh.strftime('%H:%M:%S UTC')}</small>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        auto_refresh = st.checkbox("[ AUTO-REFRESH (60s) ]", value=False)
        
        st.markdown("---")
        
        if st.button("⚡ DISCONNECT", use_container_width=True, type="primary"):
            st.session_state.authenticated = False
            st.session_state.gsheets_client = None
            st.session_state.chat_df = pd.DataFrame()
            st.session_state.outreach_df = pd.DataFrame()
            st.session_state.current_client = None
            st.success("✓ DISCONNECTED")
            time.sleep(1)
            st.rerun()
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "[ DASHBOARD ]",
        "[ CHAT INTEL ]",
        "[ TARGET ACQUISITION ]",
        "[ SEARCH PROTOCOL ]",
        "[ ANALYTICS ]"
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
    
    if auto_refresh:
        time.sleep(60)
        st.rerun()

if __name__ == "__main__":
    main()
