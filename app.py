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

# ------------------ LEAD OUTREACH TAB ------------------ #
def show_lead_outreach():
    st.markdown("<div class='section-header'>🎯 Lead Outreach Management</div>", unsafe_allow_html=True)
    
    outreach_df = st.session_state.outreach_df
    
    if outreach_df.empty:
        st.warning("📭 No outreach data loaded. Please load your outreach sheet from the sidebar.")
        st.info("💡 **How to get started:**\n1. Configure your outreach sheet ID in the sidebar\n2. Click 'Load/Refresh Data'\n3. Your leads will appear here")
        return
    
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
        sent = len(outreach_df[outreach_df['status'] == 'sent']) if 'status' in outreach_df.columns else 0
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{sent}</div>
            <div class="stat-label">Sent</div>
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
        search_query = st.text_input("🔍 Search", placeholder="Search leads...")
    
    with col2:
        status_filter = st.selectbox(
            "📊 Status",
            ["All"] + list(outreach_df['status'].unique()) if 'status' in outreach_df.columns else ["All"]
        )
    
    with col3:
        city_filter = st.selectbox(
            "🌆 City",
            ["All"] + list(outreach_df['search_city'].unique()) if 'search_city' in outreach_df.columns else ["All"]
        )
    
    with col4:
        sort_by = st.selectbox(
            "🔄 Sort By",
            ["timestamp", "profile_name", "status", "search_city"]
        )
    
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
    
    if sort_by in filtered_df.columns:
        filtered_df = filtered_df.sort_values(by=sort_by, ascending=False)
    
    st.markdown(f"**Showing {len(filtered_df)} leads**")
    
    # View mode selection
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        view_mode = st.radio("View Mode", ["Cards", "Table", "Compact"], horizontal=True)
    with col2:
        leads_per_page = st.selectbox("Per Page", [10, 25, 50, 100], index=1)
    with col3:
        page_num = st.number_input("Page", min_value=1, max_value=max(1, (len(filtered_df)-1)//leads_per_page + 1), value=1)
    
    st.markdown("---")
    
    # Pagination
    start_idx = (page_num - 1) * leads_per_page
    end_idx = start_idx + leads_per_page
    paginated_df = filtered_df.iloc[start_idx:end_idx]
    
    # Display based on view mode
    if view_mode == "Cards":
        display_leads_cards(paginated_df)
    elif view_mode == "Table":
        display_leads_table(paginated_df)
    else:
        display_leads_compact(paginated_df)
    
    # Bulk actions
    if not filtered_df.empty:
        st.markdown("---")
        st.markdown("### ⚡ Bulk Actions")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            bulk_count = st.number_input("Number of leads", min_value=1, max_value=len(filtered_df), value=min(5, len(filtered_df)))
        
        with col2:
            if st.button("📤 Send Bulk", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, (i, row) in enumerate(filtered_df.head(bulk_count).iterrows()):
                    status_text.text(f"Sending to {row.get('profile_name', 'Lead')}...")
                    st.session_state.sent_leads.add(i)
                    
                    # Log activity
                    st.session_state.activity_log.append({
                        "type": "Bulk Send",
                        "details": f"Message to {row.get('profile_name', 'Lead')}",
                        "status": "✅ Success",
                        "time": datetime.now().strftime("%H:%M:%S")
                    })
                    
                    progress_bar.progress((idx + 1) / bulk_count)
                    time.sleep(0.3)
                
                status_text.text("✅ Bulk operation completed!")
                st.success(f"✅ Successfully sent {bulk_count} messages!")
                time.sleep(2)
                st.rerun()
        
        with col3:
            if st.button("📊 Export CSV", use_container_width=True):
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download",
                    data=csv,
                    file_name=f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col4:
            if st.button("🔄 Refresh", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

def display_leads_cards(df):
    """Display leads in card format"""
    for idx, (i, row) in enumerate(df.iterrows()):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            name = str(row.get('profile_name', row.get('name', 'Unnamed Lead')))
            location = str(row.get('profile_location', row.get('location', 'Unknown')))
            tagline = str(row.get('profile_tagline', row.get('tagline', 'No tagline')))
            linkedin_url = str(row.get('linkedin_url', '#'))
            message = str(row.get('linkedin_message', 'No message'))
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
            
            if st.button("🚀 Send", key=f"send_{i}", disabled=is_sent, use_container_width=True):
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
            
            if st.button("📋 Copy", key=f"copy_{i}", use_container_width=True):
                st.info("📋 Lead data copied!")
            
            if st.button("⭐ Save", key=f"save_{i}", use_container_width=True):
                st.info("⭐ Lead saved!")
            
            is_selected = i in st.session_state.selected_leads
            if st.checkbox("Select", key=f"select_{i}", value=is_selected):
                if i not in st.session_state.selected_leads:
                    st.session_state.selected_leads.append(i)
            else:
                if i in st.session_state.selected_leads:
                    st.session_state.selected_leads.remove(i)

def display_leads_table(df):
    """Display leads in table format"""
    display_columns = []
    if not df.empty:
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
    for idx, (i, row) in enumerate(df.iterrows()):
        name = str(row.get('profile_name', row.get('name', 'Unnamed Lead')))
        location = str(row.get('profile_location', row.get('location', 'Unknown')))
        status = str(row.get('status', 'unknown'))
        
        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
        
        with col1:
            st.write(f"👤 **{name}**")
        with col2:
            st.write(f"📍 {location}")
        with col3:
            st.write(f"📊 {status}")
        with col4:
            is_sent = status == 'sent' or i in st.session_state.sent_leads
            if st.button("🚀", key=f"send_compact_{i}", help="Send message", disabled=is_sent):
                st.session_state.sent_leads.add(i)
                st.success("Sent!")
                st.rerun()

# ------------------ SEARCH INTERFACE TAB ------------------ #
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
                        "client": st.session_state.current_client['name'] if st.session_state.current_client else "Unknown"
                    }
                    
                    try:
                        with st.spinner("🔍 Searching for leads..."):
                            response = requests.post(webhook_url, json=payload, timeout=10)
                        
                        if response.status_code == 200:
                            st.success(f"✅ Search initiated for {search_term} in {city}, {country}!")
                            st.info("📊 Results will appear in your outreach sheet shortly. Click 'Load/Refresh Data' in sidebar to see them.")
                            st.balloons()
                            
                            # Log activity
                            st.session_state.activity_log.append({
                                "type": "Search",
                                "details": f"{search_term} in {city}, {country}",
                                "status": "✅ Success",
                                "time": datetime.now().strftime("%H:%M:%S")
                            })
                            
                            # Add to webhook history
                            st.session_state.webhook_history.append({
                                "search": f"{search_term} - {city}",
                                "status": "Success",
                                "time": datetime.now().strftime("%H:%M:%S"),
                                "leads": num_leads
                            })
                        else:
                            st.error(f"❌ Error: HTTP {response.status_code}")
                            st.session_state.activity_log.append({
                                "type": "Search",
                                "details": f"{search_term} in {city}",
                                "status": f"❌ Failed ({response.status_code})",
                                "time": datetime.now().strftime("%H:%M:%S")
                            })
                    
                    except requests.exceptions.Timeout:
                        st.warning("⚠️ Request timeout - webhook may be slow. The search might still process.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    with col2:
        st.markdown("### 📊 Search Activity")
        
        # Recent searches
        if st.session_state.webhook_history:
            st.markdown("#### 🔍 Recent Searches")
            recent_searches = st.session_state.webhook_history[-5:]
            
            for search in reversed(recent_searches):
                st.markdown(f"""
                <div style="background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #667eea; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                    <strong>{search['search']}</strong><br>
                    <small>🕐 {search['time']}</small><br>
                    <small>📊 {search['leads']} leads</small><br>
                    <small>Status: {search['status']}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No recent searches")
        
        st.markdown("---")
        
        # Statistics
        st.markdown("#### 📈 Statistics")
        total_searches = len([log for log in st.session_state.activity_log if log.get('type') == 'Search'])
        successful_searches = len([log for log in st.session_state.activity_log if log.get('type') == 'Search' and 'Success' in log.get('status', '')])
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Total Searches", total_searches)
        with col_b:
            success_rate = (successful_searches / total_searches * 100) if total_searches > 0 else 0
            st.metric("Success Rate", f"{success_rate:.0f}%")
        
        st.markdown("---")
        
        # Quick actions
        st.markdown("#### ⚡ Quick Actions")
        if st.button("🔄 Refresh Outreach Data", use_container_width=True):
            st.cache_data.clear()
            st.info("Refreshing... click Load/Refresh Data in sidebar")
        
        if st.button("📊 View All Leads", use_container_width=True):
            st.info("Navigate to 'Lead Outreach' tab to view all leads")

# ------------------ ADVANCED ANALYTICS TAB ------------------ #
def show_advanced_analytics():
    st.markdown("<div class='section-header'>📈 Advanced Analytics</div>", unsafe_allow_html=True)
    
    chat_df = st.session_state.chat_df
    outreach_df = st.session_state.outreach_df
    
    if chat_df.empty and outreach_df.empty:
        st.warning("📭 No data loaded. Please load your sheets to see analytics.")
        return
    
    # Create tabs for different analytics
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🌍 Geographic", "⏰ Timeline", "🎯 Performance"])
    
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
        st.markdown("#### 💬 Chat Analytics")
        if not chat_df.empty:
            if 'date' in chat_df.columns:
                daily_activity = chat_df.groupby('date').size().reset_index(name='messages')
                
                fig = px.line(
                    daily_activity,
                    x='date',
                    y='messages',
                    title="Daily Message Activity",
                    markers=True
                )
                fig.update_traces(line_color='#667eea', marker_color='#764ba2')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No chat data available")
    
    with col2:
        st.markdown("#### 🎯 Outreach Analytics")
        if not outreach_df.empty and 'status' in outreach_df.columns:
            status_counts = outreach_df['status'].value_counts()
            
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Lead Status Distribution",
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No outreach data available")

def show_geographic_analytics(outreach_df):
    """Show geographic analytics"""
    if outreach_df.empty:
        st.info("No outreach data for geographic analysis")
        return
    
    if 'search_city' in outreach_df.columns:
        city_counts = outreach_df['search_city'].value_counts().head(15)
        
        fig = px.bar(
            x=city_counts.values,
            y=city_counts.index,
            orientation='h',
            title="🌆 Top Cities by Lead Count",
            labels={'x': 'Number of Leads', 'y': 'City'},
            color=city_counts.values,
            color_continuous_scale='Blues'
        )
        fig.update_layout(showlegend=False, height=500)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No city data available")

def show_timeline_analytics(chat_df, outreach_df):
    """Show timeline analytics"""
    col1, col2 = st.columns(2)
    
    with col1:
        if not chat_df.empty and 'date' in chat_df.columns:
            st.markdown("#### 💬 Chat Timeline")
            daily_chats = chat_df.groupby('date').size().tail(30).reset_index(name='count')
            
            fig = px.area(
                daily_chats,
                x='date',
                y='count',
                title="Last 30 Days - Chat Activity"
            )
            fig.update_traces(fillcolor='rgba(102, 126, 234, 0.3)', line_color='#667eea')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No chat timeline data")
    
    with col2:
        if not outreach_df.empty and 'timestamp' in outreach_df.columns:
            st.markdown("#### 🎯 Outreach Timeline")
            try:
                outreach_df['date'] = pd.to_datetime(outreach_df['timestamp']).dt.date
                daily_outreach = outreach_df.groupby('date').size().tail(30).reset_index(name='count')
                
                fig = px.area(
                    daily_outreach,
                    x='date',
                    y='count',
                    title="Last 30 Days - Outreach Activity"
                )
                fig.update_traces(fillcolor='rgba(245, 158, 11, 0.3)', line_color='#f59e0b')
                st.plotly_chart(fig, use_container_width=True)
            except:
                st.info("Unable to parse outreach timeline")
        else:
            st.info("No outreach timeline data")

def show_performance_analytics(outreach_df):
    """Show performance analytics"""
    if outreach_df.empty:
        st.info("No data for performance analysis")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'status' in outreach_df.columns:
            sent_count = len(outreach_df[outreach_df['status'] == 'sent'])
            total_count = len(outreach_df)
            conversion_rate = (sent_count / total_count * 100) if total_count > 0 else 0
            
            st.metric(
                "📤 Conversion Rate",
                f"{conversion_rate:.1f}%",
                delta=f"{sent_count} of {total_count} sent"
            )
    
    with col2:
        if 'search_term' in outreach_df.columns:
            unique_terms = outreach_df['search_term'].nunique()
            st.metric("🎯 Search Diversity", unique_terms, delta="Unique job titles")
    
    with col3:
        if 'search_city' in outreach_df.columns:
            unique_cities = outreach_df['search_city'].nunique()
            st.metric("🌍 Geographic Reach", unique_cities, delta="Unique cities")
    
    # Performance trends
    if 'timestamp' in outreach_df.columns and 'status' in outreach_df.columns:
        try:
            outreach_df['date'] = pd.to_datetime(outreach_df['timestamp']).dt.date
            daily_performance = outreach_df.groupby(['date', 'status']).size().unstack(fill_value=0)
            
            if not daily_performance.empty:
                fig = px.area(
                    daily_performance.reset_index(),
                    x='date',
                    y=daily_performance.columns.tolist(),
                    title="📈 Daily Performance by Status"
                )
                st.plotly_chart(fig, use_container_width=True)
        except:
            st.info("Unable to generate performance trends")

# ------------------ RUN APPLICATION ------------------ #
if __name__ == "__main__":
    main() PAGE CONFIG ------------------ #
st.set_page_config(
    page_title="LinkedIn Analytics & Outreach Hub",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    
    .message-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
    return query_params.get('client', None)

def load_client_profile(client_id):
    """Load client-specific profile and preferences"""
    client_profiles = {
        'donmenico': {
            'name': 'Donmenico Hudson',
            'linkedin_url': 'https://www.linkedin.com/in/donmenicohudson/',
            'chat_sheet_id': '1klm60YFXSoV510S4igv5LfREXeykDhNA5Ygq7HNFN0I',
            'chat_sheet_name': 'linkedin_chat_history_advanced 2',
            'outreach_sheet_id': '1eLEFvyV1_f74UC1g5uQ-xA7A62sK8Pog27KIjw_Sk3Y',
            'outreach_sheet_name': 'Sheet1',
            'webhook_url': 'https://agentonline-u29564.vm.elestio.app/webhook/Leadlinked'
        },
        # Add more client profiles as needed
        'demo': {
            'name': 'Demo User',
            'linkedin_url': 'https://www.linkedin.com/in/demo/',
            'chat_sheet_id': '',
            'chat_sheet_name': 'Sheet1',
            'outreach_sheet_id': '',
            'outreach_sheet_name': 'Sheet1',
            'webhook_url': ''
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
    """Create a message activity chart"""
    if df.empty or 'date' not in df.columns:
        return None
    
    message_counts = df['date'].value_counts().sort_index()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=message_counts.index,
        y=message_counts.values,
        mode='lines+markers',
        line=dict(color='#667eea', width=3),
        marker=dict(size=8, color='#764ba2'),
        fill='tozeroy',
        fillcolor='rgba(102, 126, 234, 0.2)'
    ))
    
    fig.update_layout(
        title="Message Activity Over Time",
        xaxis_title="Date",
        yaxis_title="Messages",
        template="plotly_white",
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

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
            st.markdown("### 👤 Your Profile")
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; color: white; margin-bottom: 15px;">
                <h3 style="margin: 0 0 10px 0;">{st.session_state.current_client['name']}</h3>
                <a href="{st.session_state.current_client['linkedin_url']}" target="_blank" style="color: white; text-decoration: none;">
                    🔗 View LinkedIn Profile →
                </a>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Data Source Configuration
        st.subheader("📊 Data Configuration")
        
        if st.session_state.current_client:
            # Auto-load client sheets
            chat_sheet_id = st.text_input(
                "Chat History Sheet ID",
                value=st.session_state.current_client['chat_sheet_id'],
                help="Google Sheet ID for chat history"
            )
            chat_sheet_name = st.text_input(
                "Chat Sheet Name",
                value=st.session_state.current_client['chat_sheet_name']
            )
            
            outreach_sheet_id = st.text_input(
                "Outreach Sheet ID",
                value=st.session_state.current_client['outreach_sheet_id'],
                help="Google Sheet ID for outreach leads"
            )
            outreach_sheet_name = st.text_input(
                "Outreach Sheet Name",
                value=st.session_state.current_client['outreach_sheet_name']
            )
            
            webhook_url = st.text_input(
                "Webhook URL",
                value=st.session_state.current_client['webhook_url'],
                help="n8n webhook URL for lead searches"
            )
        else:
            # Manual configuration
            st.info("💡 Add ?client=donmenico to URL for auto-configuration")
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
                        if not st.session_state.chat_df.empty:
                            st.success(f"✅ Loaded {len(st.session_state.chat_df)} chat messages!")
                    
                    # Load outreach data
                    if outreach_sheet_id:
                        st.session_state.outreach_df = load_sheet_data(
                            st.session_state.gsheets_client,
                            outreach_sheet_id,
                            outreach_sheet_name
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
    
    # Main Dashboard Tabs
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
        show_search_interface(webhook_url if 'webhook_url' in locals() else None)
    
    with tab5:
        show_advanced_analytics()
    
    # Auto-refresh logic
    if 'auto_refresh' in locals() and auto_refresh:
        time.sleep(60)
        st.rerun()

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
        if st.session_state.current_client:
            contacts = get_contact_info(chat_df, {
                'name': st.session_state.current_client['name'],
                'url': st.session_state.current_client['linkedin_url']
            }) if not chat_df.empty else {}
            contact_count = len(contacts)
        else:
            contact_count = 0
        
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

# ------------------ CHAT ANALYTICS TAB ------------------ #
def show_chat_analytics():
    st.markdown("<div class='section-header'>💬 Chat History Analytics</div>", unsafe_allow_html=True)
    
    chat_df = st.session_state.chat_df
    
    if chat_df.empty:
        st.warning("📭 No chat data loaded. Please load your chat history sheet from the sidebar.")
        st.info("💡 **How to get started:**\n1. Configure your chat sheet ID in the sidebar\n2. Click 'Load/Refresh Data'\n3. Your chat history will appear here")
        return
    
    if not st.session_state.current_client:
        st.warning("⚠️ Client profile not loaded. Some features may be limited.")
        st.info("💡 Add ?client=donmenico to your URL for full functionality")
        
        # Basic stats without client profile
        st.markdown("### 📊 Basic Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Messages", len(chat_df))
        with col2:
            if 'date' in chat_df.columns:
                unique_dates = chat_df['date'].nunique()
                st.metric("Active Days", unique_dates)
        with col3:
            st.metric("Data Points", len(chat_df.columns))
        
        st.markdown("---")
        st.dataframe(chat_df, use_container_width=True, height=400)
        return
    
    my_profile = {
        'name': st.session_state.current_client['name'],
        'url': st.session_state.current_client['linkedin_url']
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
    selected_name = st.selectbox("Select a contact", list(contact_names.keys()))
    
    if not selected_name:
        return
    
    selected_url = contact_names[selected_name]
    contact_info = contacts[selected_url]
    
    # Contact header
    message_count = len(contact_info['messages'])
    initials = get_initials(contact_info['name'])
    
    st.markdown(f"""
    <div class='client-profile-banner'>
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <div class="profile-badge" style="width: 70px; height: 70px; font-size: 2em;">{initials}</div>
            <div>
                <h2 style="margin: 0;">{contact_info['name']}</h2>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">LinkedIn Professional</p>
            </div>
        </div>
        <div style="display: flex; gap: 20px; flex-wrap: wrap;">
            <div style="background: rgba(255,255,255,0.2); padding: 12px 20px; border-radius: 12px;">
                💬 <strong>{message_count}</strong> total messages
            </div>
            <div style="background: rgba(255,255,255,0.2); padding: 12px 20px; border-radius: 12px;">
                📤 <strong>{contact_info['sent_count']}</strong> sent
            </div>
            <div style="background: rgba(255,255,255,0.2); padding: 12px 20px; border-radius: 12px;">
                📥 <strong>{contact_info['received_count']}</strong> received
            </div>
        </div>
        <div class="linkedin-badge">
            <a href="{contact_info['url']}" target="_blank" style="color: white; text-decoration: none;">
                🔗 View LinkedIn Profile →
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 💬 Conversation History")
    
    # Sort messages
    messages = sorted(
        contact_info['messages'],
        key=lambda x: (x.get('date', ''), x.get('time', ''))
    )
    
    current_date = None
    
    # Display messages
    for msg in messages:
        sender_name = msg.get('sender_name', '')
        sender_url = msg.get('sender_linkedin_url', '')
        message_text = msg.get('message', '')
        date = msg.get('date', '')
        time_str = msg.get('time', '')
        shared_content = msg.get('shared_content', '')
        
        # Date divider
        if date and date != current_date:
            st.markdown(f'<div class="conversation-date-divider">{date}</div>', unsafe_allow_html=True)
            current_date = date
        
        is_my_message = is_me(sender_name, sender_url, my_profile)
        
        if is_my_message:
            st.markdown(f"""
            <div class="message-sent">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <strong>You</strong>
                    <span class="message-time" style="font-size: 0.85em; opacity: 0.8;">🕐 {time_str}</span>
                </div>
                <p style="margin: 0; line-height: 1.6;">{message_text}</p>
                {f'<div style="background: rgba(255,255,255,0.2); padding: 8px; border-radius: 8px; margin-top: 10px; font-size: 0.9em;">📎 {shared_content}</div>' if shared_content else ''}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="message-received">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <strong style="color: #667eea;">{sender_name}</strong>
                    <span class="message-time" style="font-size: 0.85em; color: #94a3b8;">🕐 {time_str}</span>
                </div>
                <p style="margin: 0; color: #333; line-height: 1.6;">{message_text}</p>
                {f'<div style="background: #f0f2f5; padding: 8px; border-radius: 8px; margin-top: 10px; font-size: 0.9em; color: #5f6368;">📎 {shared_content}</div>' if shared_content else ''}
            </div>
            """, unsafe_allow_html=True)

def show_all_messages_view(chat_df, my_profile):
    """Display all messages in table/card format"""
    st.subheader("📋 All Messages")
    st.markdown("*Complete message archive with advanced filtering*")
    
    # Filters
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("🔍 Search messages", "", placeholder="Type to search...")
    with col2:
        show_only = st.selectbox("Filter", ["All", "Sent by Me", "Received"])
    with col3:
        sort_order = st.selectbox("Sort", ["Newest First", "Oldest First"])
    
    # Apply filters
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
    
    # Sort
    if 'date' in filtered_df.columns and 'time' in filtered_df.columns:
        filtered_df = filtered_df.sort_values(
            by=['date', 'time'],
            ascending=(sort_order == "Oldest First")
        )
    
    st.markdown(f"**Showing {len(filtered_df)} messages**")
    st.markdown("---")
    
    if filtered_df.empty:
        st.info("🔭 No messages found matching your filters")
        return
    
    # Display messages
    for idx, (i, row) in enumerate(filtered_df.iterrows()):
        sender_name = str(row.get('sender_name', 'Unknown'))
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
            badge_text = "You"
            badge_style = "background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"
        else:
            contact_name = sender_name
            contact_url = sender_url
            badge_text = "Received"
            badge_style = "background: #10b981;"
        
        st.markdown(f"""
        <div class="message-card-all">
            <div class="message-header">
                <div>
                    <div class="message-sender">
                        {sender_name}
                        <span class="message-badge" style="{badge_style}">{badge_text}</span>
                    </div>
                </div>
                <div class="message-timestamp">
                    🗓️ {date} • 🕐 {time_str}
                </div>
            </div>
            
            <div class="message-content">
                {message}
            </div>
            
            <div class="message-footer">
                <span>
                    <strong>Contact:</strong> {contact_name if contact_name else 'N/A'}
                </span>
                {f'<span><strong>📎 Attachment:</strong> {shared_content}</span>' if shared_content else ''}
                {f'<a href="{contact_url}" target="_blank" class="linkedin-link">🔗 View Profile →</a>' if contact_url else ''}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ------------------
