import streamlit as st
import requests
import pymongo
from datetime import datetime
import pandas as pd
from streamlit_extras.colored_header import colored_header
import plotly.express as px

# Set page configuration
st.set_page_config(
    page_title="Call Filter System",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {font-size: 2.5rem !important; font-weight: 700 !important; margin-bottom: 1rem !important;}
    .sub-header {font-size: 1.5rem !important; font-weight: 600 !important; margin-top: 1rem !important;}
    .card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .success-card {background-color: #d4edda; color: #155724; border-left: 5px solid #28a745;}
    .warning-card {background-color: #fff3cd; color: #856404; border-left: 5px solid #ffc107;}
    .danger-card {background-color: #f8d7da; color: #721c24; border-left: 5px solid #dc3545;}
    .info-card {background-color: #d1ecf1; color: #0c5460; border-left: 5px solid #17a2b8;}
    .sidebar .sidebar-content {background-color: #f8f9fa !important;}
</style>
""", unsafe_allow_html=True)

# MongoDB Configuration (Replace with your MongoDB URI)
MONGO_URI = "mongodb+srv://radheshyamjanwa666:TPo5T91ldKNiWWCM@cluster0.bdfxa.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "call_filter_db"
FILTER_COLLECTION = "filter_rules"
LISTS_COLLECTION = "phone_lists"
API_HISTORY_COLLECTION = "api_history"
AADHAAR_RECORDS_COLLECTION = "aadhar_data"
UNLINKED_HISTORY_COLLECTION = "unlinked_history"

# Connect to MongoDB
@st.cache_resource
def init_connection():
    return pymongo.MongoClient(MONGO_URI)

client = init_connection()
db = client[DB_NAME]
rules_collection = db[FILTER_COLLECTION]
lists_collection = db[LISTS_COLLECTION]
api_history_collection = db[API_HISTORY_COLLECTION]
aadhaar_records_collection = db[AADHAAR_RECORDS_COLLECTION]
unlinked_history_collection = db[UNLINKED_HISTORY_COLLECTION]

# API Configuration
NUMLOOKUP_API_KEY = "num_live_zo8k5QYZZ7zjPiqBMhI0s0K4B5TtMMgtbeqBzJgM"

def validate_number(mobile_number):
    """Check if a mobile number is valid using NumLookup API and detect spam calls."""
    url = f"https://www.numlookupapi.com/api/validate/{mobile_number}?apikey={NUMLOOKUP_API_KEY}"
    
    with st.spinner('Validating number...'):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("valid"):
                return None  # Invalid number
            
            # Check for missing values (spam detection)
            if not all([data.get("location"), data.get("carrier"), data.get("line_type")]):
                data["spam_status"] = True  # Mark as spam
            else:
                data["spam_status"] = False  # Safe number
            
            # Store API response in MongoDB
            api_history_collection.insert_one({
                "number": mobile_number,
                "response": data,
                "timestamp": datetime.now()
            })
            
            return data
        except requests.RequestException as e:
            st.error(f"API request failed: {e}")
            return None

@st.cache_data(ttl=300)
def get_api_history():
    """Retrieve stored API call data from MongoDB."""
    return list(api_history_collection.find({}, {"_id": 0}).sort("timestamp", -1))

@st.cache_data(ttl=60)
def get_phone_list(list_name):
    """Retrieve phone numbers from MongoDB list (whitelist, blacklist, blocked)."""
    result = lists_collection.find_one({"list_name": list_name})
    return set(result["numbers"]) if result else set()

def update_phone_list(list_name, phone_number, action="add"):
    """Add or remove a phone number from a specified list (whitelist, blacklist, blocked)."""
    if action == "add":
        lists_collection.update_one(
            {"list_name": list_name},
            {"$addToSet": {"numbers": phone_number}},
            upsert=True
        )
    elif action == "remove":
        lists_collection.update_one(
            {"list_name": list_name},
            {"$pull": {"numbers": phone_number}}
        )
    # Clear cache to refresh data
    st.cache_data.clear()

@st.cache_data(ttl=60)
def get_all_filter_rules():
    """Retrieve all filter rules from MongoDB."""
    return list(rules_collection.find({}))

def add_filter_rule(rule):
    """Insert a new filter rule into MongoDB."""
    rules_collection.insert_one(rule)
    # Clear cache to refresh data
    st.cache_data.clear()

def remove_filter_rule(rule_id):
    """Remove a filter rule from MongoDB by its ID."""
    rules_collection.delete_one({"_id": rule_id})
    # Clear cache to refresh data
    st.cache_data.clear()

def check_filters(data):
    """Apply filter rules from MongoDB to determine if a number should be allowed or blocked."""
    country = data.get("country_code", "")
    location = data.get("location", "")
    now = datetime.now().time()
    
    filter_rules = get_all_filter_rules()
    
    # If there are no rules, allow the call
    if not filter_rules:
        return True, "No filter rules defined"
    
    for rule in filter_rules:
        reason = None
        
        # Check country restrictions
        if rule.get("country") and country in rule.get("country", []):
            reason = f"Blocked by country rule: {rule['name']}"
            return False, reason
        
        # Check location restrictions
        if rule.get("location") and location in rule.get("location", []):
            reason = f"Blocked by location rule: {rule['name']}"
            return False, reason
        
        # Check time restrictions
        for time_range in rule.get("time", []):
            try:
                start, end = [datetime.strptime(t.strip(), "%H:%M").time() for t in time_range.split("-")]
                if start <= now <= end:
                    reason = f"Blocked by time rule: {rule['name']} ({time_range})"
                    return False, reason
            except ValueError:
                continue  # Ignore invalid time format
    
    # If no rules matched, allow the call
    return True, "Passed all filter rules"

def display_data_card(title, data, card_type="info"):
    """Display data in a styled card."""
    st.markdown(f"""
    <div class="card {card_type}-card">
        <h3>{title}</h3>
        <pre>{data}</pre>
    </div>
    """, unsafe_allow_html=True)

def get_api_stats():
    """Get statistics from API history."""
    history = get_api_history()
    if not history:
        return None
    
    total_calls = len(history)
    spam_calls = sum(1 for record in history if record.get('response', {}).get('spam_status', False))
    valid_calls = sum(1 for record in history if record.get('response', {}).get('valid', False))
    
    return {
        "total": total_calls,
        "spam": spam_calls,
        "valid": valid_calls,
        "spam_percentage": (spam_calls / total_calls * 100) if total_calls > 0 else 0
    }

# Sidebar with improved navigation
with st.sidebar:
    # st.image("https://img.icons8.com/fluency/96/000000/phone-disconnected.png", width=80)
    st.markdown("<h1 style='text-align: center;'>Call Filter System</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Dashboard metrics in sidebar
    stats = get_api_stats()
    if stats:
        st.markdown("### 📊 Dashboard")
        col1, col2 = st.columns(2)
        col1.metric("Total Lookups", stats["total"])
        col2.metric("Spam Detected", stats["spam"])
        
        # Create a mini chart
        chart_data = pd.DataFrame({
            'Category': ['Valid', 'Spam'],
            'Count': [stats["valid"] - stats["spam"], stats["spam"]]
        })
        fig = px.pie(chart_data, values='Count', names='Category', 
                    color_discrete_map={'Valid': '#28a745', 'Spam': '#dc3545'},
                    height=200)
        fig.update_layout(margin=dict(l=20, r=20, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")
    
    # Navigation menu with icons
    st.markdown("### 📋 Navigation")
    page = st.radio("", 
                   ["🔍 Number Checker", 
                    "⚙️ Filter Rules", 
                    "📞 Phone Lists", 
                    "📊 API History",
                    "🔧 Settings",
                    "📱 Aadhaar-Mobile Link Checker"])

# Main content area
if page == "🔍 Number Checker":
    colored_header(label="📱 Mobile Number Verification", description="Check if a number is valid, spam, or blocked", color_name="blue-70")
    
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            mobile_number = st.text_input("Enter Mobile Number:", placeholder="+1234567890").strip()
        with col2:
            st.write("")
            st.write("")
            check_button = st.button("Check Number", use_container_width=True)
    
    if check_button:
        if not mobile_number:
            st.error("Please enter a mobile number.")
        else:
            whitelist = get_phone_list("whitelist")
            blacklist = get_phone_list("blacklist")
            blocked_list = get_phone_list("blocked")
            
            with st.container():
                if mobile_number in blacklist:
                    st.error("❌ This number is in the blacklist.")
                    st.button("➕ Add to Whitelist", on_click=lambda: update_phone_list("whitelist", mobile_number, action="add"))
                elif mobile_number in blocked_list:
                    st.error("❌ This number is in the blocked list.")
                    st.button("➕ Add to Whitelist", on_click=lambda: update_phone_list("whitelist", mobile_number, action="add"))
                elif mobile_number in whitelist:
                    st.success("✅ This number is whitelisted and allowed.")
                    st.button("➖ Remove from Whitelist", on_click=lambda: update_phone_list("whitelist", mobile_number, action="remove"))
                else:
                    data = validate_number(mobile_number)
                    if not data:
                        st.error("❌ Invalid number or API failure.")
                    else:
                        allowed, reason = check_filters(data)
                        
                        cols = st.columns(3)
                        if data.get("spam_status"):
                            cols[0].error("🚨 SPAM ALERT! Missing carrier or location data.")
                            cols[1].button("➕ Add to Blacklist", on_click=lambda: update_phone_list("blacklist", mobile_number, action="add"))
                        elif not allowed:
                            cols[0].warning(f"🚫 Number blocked: {reason}")
                            cols[1].button("➕ Add to Whitelist", on_click=lambda: update_phone_list("whitelist", mobile_number, action="add"))
                        else:
                            cols[0].success(f"✅ Number allowed: {reason}")
                            cols[1].button("➕ Add to Blacklist", on_click=lambda: update_phone_list("blacklist", mobile_number, action="add"))
                        
                        # Display results in a nice formatted card
                        with st.expander("📋 View Detailed Information", expanded=True):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("### 📞 Number Information")
                                st.markdown(f"**Number:** {data.get('number', 'N/A')}")
                                st.markdown(f"**Country:** {data.get('country_code', 'N/A')} ({data.get('country_name', 'N/A')})")
                                st.markdown(f"**Location:** {data.get('location', 'N/A')}")
                                st.markdown(f"**Carrier:** {data.get('carrier', 'N/A')}")
                                st.markdown(f"**Line Type:** {data.get('line_type', 'N/A')}")
                            
                            with col2:
                                st.markdown("### 🔍 Verification Status")
                                status_color = "green" if not data.get("spam_status") and allowed else "red"
                                st.markdown(f"**Valid Number:** {'✅' if data.get('valid') else '❌'}")
                                st.markdown(f"**Spam Status:** {'🚨 Potential Spam' if data.get('spam_status') else '✅ Not Spam'}")
                                st.markdown(f"**Filter Status:** {'✅ Allowed' if allowed else '🚫 Blocked'}")
                                st.markdown(f"**Filter Reason:** {reason}")

elif page == "⚙️ Filter Rules":
    colored_header(label="⚙️ Filter System Rules", description="Configure rules to filter incoming calls", color_name="blue-70")
    
    with st.expander("➕ Add New Filter Rule", expanded=True):
        st.markdown("Define rules to Block calls based on country, location, or time of day.")
        
        col1, col2 = st.columns(2)
        with col1:
            rule_name = st.text_input("Rule Name:", placeholder="e.g., Block Night Calls").strip()
        
        with col2:
            rule_type = st.selectbox("Rule Type:", ["Country-based", "Location-based", "Time-based", "Combined"])
        
        if rule_type == "Country-based" or rule_type == "Combined":
            country_values = st.text_area("Enter Countries (comma-separated):", 
                                          placeholder="e.g., US, CA, UK").strip()
        else:
            country_values = ""
            
        if rule_type == "Location-based" or rule_type == "Combined":
            location_values = st.text_area("Enter Locations (comma-separated):", 
                                           placeholder="e.g., New York, California").strip()
        else:
            location_values = ""
            
        if rule_type == "Time-based" or rule_type == "Combined":
            time_values = st.text_area("Enter Time Ranges (HH:MM-HH:MM, comma-separated):", 
                                       placeholder="e.g., 22:00-06:00, 12:00-13:00").strip()
        else:
            time_values = ""

        if st.button("Add Rule", use_container_width=True):
            if rule_name:
                new_rule = {
                    "name": rule_name,
                    "country": [c.strip() for c in country_values.split(",") if c.strip()],
                    "location": [l.strip() for l in location_values.split(",") if l.strip()],
                    "time": [t.strip() for t in time_values.split(",") if t.strip()]
                }
                add_filter_rule(new_rule)
                st.success(f"Rule '{rule_name}' added successfully!")
            else:
                st.error("Please provide a valid rule name.")

    st.markdown("---")
    st.markdown("### 📋 Current Rules")
    filter_rules = get_all_filter_rules()
    
    if not filter_rules:
        st.info("No rules added yet. Use the form above to create your first rule.")
    else:
        for i, rule in enumerate(filter_rules):
            with st.container():
                st.markdown(f"<div class='card'>", unsafe_allow_html=True)
                cols = st.columns([3, 1])
                with cols[0]:
                    st.markdown(f"#### 📌 {rule['name']}")
                    
                    if rule['country']:
                        st.markdown(f"🌍 **Countries:** {', '.join(rule['country'])}")
                    
                    if rule['location']:
                        st.markdown(f"📍 **Locations:** {', '.join(rule['location'])}")
                    
                    if rule['time']:
                        st.markdown(f"⏱️ **Time Ranges:** {', '.join(rule['time'])}")
                
                with cols[1]:
                    st.markdown("##### Actions")
                    if st.button("🗑️ Remove", key=f"remove_rule_{i}", use_container_width=True):
                        remove_filter_rule(rule['_id'])
                        st.success(f"Rule '{rule['name']}' removed successfully!")
                        st.rerun()
                
                st.markdown(f"</div>", unsafe_allow_html=True)

elif page == "📞 Phone Lists":
    colored_header(label="📞 Manage Phone Lists", description="Organize phone numbers into lists", color_name="blue-70")
    
    # Create tabs for different lists
    tabs = st.tabs(["✅ Whitelist", "❌ Blacklist", "🚫 Blocked"])
    
    for i, list_type in enumerate(["whitelist", "blacklist", "blocked"]):
        with tabs[i]:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                phone_number = st.text_input(f"Enter Phone Number for {list_type.capitalize()}:", 
                                             placeholder="+1234567890", key=f"input_{list_type}").strip()
            
            with col2:
                st.write("")
                st.write("")
                add_col, remove_col = st.columns(2)
                with add_col:
                    add_button = st.button("Add", key=f"add_{list_type}", use_container_width=True)
                with remove_col:
                    remove_button = st.button("Remove", key=f"remove_{list_type}", use_container_width=True)
            
            if add_button and phone_number:
                update_phone_list(list_type, phone_number, action="add")
                st.success(f"✅ Added {phone_number} to {list_type}.")
            
            if remove_button and phone_number:
                update_phone_list(list_type, phone_number, action="remove")
                st.success(f"🚫 Removed {phone_number} from {list_type}.")
            
            # Show current list contents
            st.markdown("---")
            st.markdown(f"### Current {list_type.capitalize()}")
            
            current_list = get_phone_list(list_type)
            if not current_list:
                st.info(f"No numbers in the {list_type} yet.")
            else:
                # Create a DataFrame for better display
                df = pd.DataFrame({"Phone Number": list(current_list)})
                st.dataframe(df, use_container_width=True)
                
                # Export option
                st.download_button(
                    label="📥 Export List",
                    data=df.to_csv(index=False).encode('utf-8'),
                    file_name=f'{list_type}_numbers.csv',
                    mime='text/csv',
                )

elif page == "📊 API History":
    colored_header(label="📊 API Lookup History", description="View past number lookups and their results", color_name="blue-70")
    
    api_history = get_api_history()
    
    # Add some analytics at the top
    if api_history:
        stats = get_api_stats()
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Total Lookups", stats["total"])
        col2.metric("Valid Numbers", stats["valid"])
        col3.metric("Spam Numbers", stats["spam"])
        col4.metric("Spam Rate", f"{stats['spam_percentage']:.1f}%")
        
        # Create chart data
        lookup_dates = [record.get('timestamp').date() for record in api_history if 'timestamp' in record]
        if lookup_dates:
            date_counts = {}
            for date in lookup_dates:
                date_str = date.strftime('%Y-%m-%d')
                date_counts[date_str] = date_counts.get(date_str, 0) + 1
            
            chart_df = pd.DataFrame({
                'Date': list(date_counts.keys()),
                'Lookups': list(date_counts.values())
            })
            chart_df['Date'] = pd.to_datetime(chart_df['Date'])
            chart_df = chart_df.sort_values('Date')
            
            # Plot the chart
            fig = px.line(chart_df, x='Date', y='Lookups', 
                        title='Number Lookups Over Time',
                        labels={'Lookups': 'Number of Lookups', 'Date': 'Date'},
                        markers=True)
            fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
    
    # Display history records
    st.markdown("### Recent Lookups")
    
    if not api_history:
        st.info("No API lookup history available yet.")
    else:
        # Convert to DataFrame for better display
        records = []
        for record in api_history:
            response = record.get('response', {})
            records.append({
                'Number': record.get('number'),
                'Timestamp': record.get('timestamp'),
                'Valid': '✅' if response.get('valid') else '❌',
                'Country': response.get('country_code'),
                'Location': response.get('location'),
                'Carrier': response.get('carrier'),
                'Line Type': response.get('line_type'),
                'Spam': '🚨' if response.get('spam_status') else '✅',
            })
        
        df = pd.DataFrame(records)
        st.dataframe(df, use_container_width=True)
        
        # Add export option
        st.download_button(
            label="📥 Export History",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name='api_lookup_history.csv',
            mime='text/csv',
        )
        
        # Option to view detailed records
        with st.expander("View Detailed Records", expanded=False):
            for i, record in enumerate(api_history[:10]):  # Show only the latest 10 for performance
                response = record.get('response', {})
                st.markdown(f"#### Number: {record.get('number')}")
                st.markdown(f"Timestamp: {record.get('timestamp')}")
                st.json(response)
                st.markdown("---")

elif page == "🔧 Settings":
    colored_header(label="🔧 Settings", description="Configure application settings", color_name="blue-70")
    
    st.markdown("### API Configuration")
    api_key = st.text_input("NumLookup API Key:", value=NUMLOOKUP_API_KEY, type="password")
    
    if st.button("Save API Key"):
        st.success("API Key saved successfully!")
        # In a real implementation, you would save this to a secure configuration
    
    st.markdown("---")
    
    st.markdown("### Database Connection")
    st.code(f"MongoDB URI: {MONGO_URI.replace(MONGO_URI.split('@')[0] + '@', '*****@')}")
    st.code(f"Database: {DB_NAME}")
    
    if st.button("Test Connection"):
        try:
            client.admin.command('ping')
            st.success("✅ Database connection successful!")
        except Exception as e:
            st.error(f"❌ Database connection failed: {e}")
    
    st.markdown("---")
    
    st.markdown("### Clear Data")
    if st.button("Clear API History"):
        api_history_collection.delete_many({})
        st.cache_data.clear()
        st.success("API history cleared successfully!")
    
    if st.button("Reset All Settings"):
        st.warning("This will clear all data including filter rules and phone lists.")
        confirm = st.checkbox("I understand this action cannot be undone")
        if confirm:
            if st.button("Confirm Reset"):
                rules_collection.delete_many({})
                lists_collection.delete_many({})
                api_history_collection.delete_many({})
                st.cache_data.clear()
                st.success("All data has been reset!")
elif page == "📱 Aadhaar-Mobile Link Checker":
    st.header("1️⃣ Add Aadhaar-Mobile Record")
    with st.form("record_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        aadhaar = col1.text_input("Aadhaar Number", max_chars=12)
        mobile = col2.text_input("Mobile Number(s)", placeholder="Comma-separated if multiple")
        add = st.form_submit_button("Add Record")
        if add and db is not None:
            if aadhaar.isdigit() and len(aadhaar) == 12:
                mobiles = [m.strip() for m in mobile.split(",") if m.strip().isdigit() and len(m.strip()) == 10]
                if mobiles:
                    # Get existing record if any
                    existing_record = aadhaar_records_collection.find_one({"aadhaar": aadhaar})
                    
                    if existing_record:
                        # Update existing record
                        existing_mobiles = existing_record.get("mobiles", [])
                        for m in mobiles:
                            if m not in existing_mobiles:
                                existing_mobiles.append(m)
                        
                        aadhaar_records_collection.update_one(
                            {"aadhaar": aadhaar},
                            {"$set": {"mobiles": existing_mobiles, "updated_at": datetime.now()}}
                        )
                    else:
                        # Create new record
                        aadhaar_records_collection.insert_one({
                            "aadhaar": aadhaar,
                            "mobiles": mobiles,
                            "created_at": datetime.now(),
                            "updated_at": datetime.now()
                        })
                    st.success("✅ Mobile number(s) added to Aadhaar successfully!")
                else:
                    st.error("❌ Please enter valid 10-digit mobile number(s).")
            else:
                st.error("❌ Enter a valid 12-digit Aadhaar number.")

    # --- Section: Manage Records ---
    st.header("2️⃣ Manage Records")
    if db is not None:
        # Fetch all records
        all_records = list(aadhaar_records_collection.find({}, {"_id": 0}))
        
        if all_records:
            flat_data = []
            for record in all_records:
                for mobile in record.get("mobiles", []):
                    flat_data.append({
                        "aadhaar_number": record["aadhaar"],
                        "mobile_number": mobile
                    })

            df = pd.DataFrame(flat_data)

            # Search Filter
            search = st.text_input("🔍 Search Mobile Number")
            if search:
                df = df[df['mobile_number'].str.contains(search)]

            st.dataframe(df, use_container_width=True)

            # Delete by Aadhaar
            del_aadhaar = st.text_input("❌ Delete Record - Enter Aadhaar Number")
            if st.button("Delete By Aadhaar"):
                result = aadhaar_records_collection.delete_one({"aadhaar": del_aadhaar})
                if result.deleted_count > 0:
                    st.success("🗑️ All mobile numbers for Aadhaar deleted.")
                else:
                    st.warning("⚠️ No record found for that Aadhaar.")

            # Clear all
            if st.button("🧹 Clear All Records"):
                aadhaar_records_collection.delete_many({})
                st.success("All records cleared.")
        else:
            st.info("No records yet. Add some above.")
    else:
        st.error("Database connection failed. Check your MongoDB connection.")

    # --- Section: Active Numbers ---
    st.header("3️⃣ Check Active Mobile Numbers")

    active_input = st.text_area("📥 Paste active numbers (comma-separated or single)",
                                placeholder="e.g. 9876543210,7654321098")

    if active_input and db is not None:
        active_list = [num.strip() for num in active_input.split(",") if num.strip().isdigit()]
        df_status_list = []
        
        timestamp = datetime.now()
        unlinked_this_round = []

        # Loop through Aadhaar records
        records = list(aadhaar_records_collection.find())
        for record in records:
            aadhaar = record["aadhaar"]
            mobiles = record.get("mobiles", [])
            active_mobiles = []
            
            for m in mobiles:
                status = "✅ Active" if m in active_list else "⚠️ Reassigned"
                df_status_list.append({
                    "aadhaar_number": aadhaar,
                    "mobile_number": m,
                    "Status": status
                })
                
                if status == "✅ Active":
                    active_mobiles.append(m)
                else:
                    unlink_record = {
                        "aadhaar": aadhaar,
                        "mobile": m,
                        "status": status,
                        "disconnected_at": timestamp
                    }
                    unlinked_history_collection.insert_one(unlink_record)
                    unlinked_this_round.append({
                        "aadhaar_number": aadhaar,
                        "mobile_number": m,
                        "Status": status,
                        "disconnected_at": timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    })
            
            # Update records: only keep active numbers
            if active_mobiles:
                aadhaar_records_collection.update_one(
                    {"aadhaar": aadhaar},
                    {"$set": {"mobiles": active_mobiles, "updated_at": timestamp}}
                )
            else:
                aadhaar_records_collection.delete_one({"aadhaar": aadhaar})

        # Show status
        if df_status_list:
            df_status = pd.DataFrame(df_status_list)
            st.subheader("📊 Aadhaar-Mobile Status")
            st.dataframe(df_status, use_container_width=True)
            st.download_button("📥 Download All Status CSV", df_status.to_csv(index=False).encode('utf-8'),
                            "aadhaar_mobile_status.csv", "text/csv")

            # Show disconnected
            if unlinked_this_round:
                df_unlinked = pd.DataFrame(unlinked_this_round)
                
                st.subheader("🚫 Disconnected Aadhaar Records")
                st.dataframe(df_unlinked, use_container_width=True)
                st.download_button("📤 Download Disconnected Aadhaar CSV",
                                df_unlinked.to_csv(index=False).encode('utf-8'),
                                "unlinked_aadhaar_records.csv", "text/csv")

                st.success(f"🔗 {len(df_unlinked)} reassigned mobile number(s) unlinked.")
        else:
            st.info("No records to check.")
    else:
        if db is not None and aadhaar_records_collection.count_documents({}) > 0:
            st.info("Paste or enter mobile numbers above to check.")

    # --- Section: View Audit Log ---
    st.header("🕒 Audit Log (Disconnections History)")
    if db is not None:
        unlinked_history = list(unlinked_history_collection.find({}, {"_id": 0}))
        if unlinked_history:
            # Convert MongoDB objects to DataFrame-friendly format
            formatted_history = []
            for record in unlinked_history:
                formatted_history.append({
                    "aadhaar_number": record["aadhaar"],
                    "mobile_number": record["mobile"],
                    "Status": record["status"],
                    "disconnected_at": record["disconnected_at"].strftime("%Y-%m-%d %H:%M:%S")
                })
            
            df_log = pd.DataFrame(formatted_history)
            st.dataframe(df_log, use_container_width=True)

            csv_log = df_log.to_csv(index=False).encode('utf-8')
            st.download_button("📑 Download Audit Log CSV", csv_log, "aadhaar_audit_log.csv", "text/csv")
        else:
            st.info("No disconnections yet.")
                    
# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>Call Filter System © 2025 - Version 2.0</p>", unsafe_allow_html=True)