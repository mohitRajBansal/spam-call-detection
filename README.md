
# Call Filter System

A comprehensive Streamlit application for validating, filtering, and managing phone calls with advanced spam detection features.

![Call Filter System](https://img.shields.io/badge/Call%20Filter-System-blue)
![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B)
![Version](https://img.shields.io/badge/Version-2.0-brightgreen)

## 🌟 Features

- **📱 Number Validation**: Verify if a mobile number is valid using the NumLookup API
- **🚨 Spam Detection**: Identify potential spam numbers based on missing carrier or location data
- **⚙️ Customizable Filter Rules**: Create rules to filter calls based on country, location, or time
- **📋 Phone List Management**: Maintain whitelists, blacklists, and blocked number lists
- **📊 API History Tracking**: View and analyze past number lookups with visualizations
- **🔗 Aadhaar-Mobile Link Checker**: Manage and verify Aadhaar-Mobile number linkages

## 📋 Pages

1. **🔍 Number Checker**
   - Validate mobile numbers
   - Check against whitelist/blacklist
   - Apply custom filter rules
   - Detect potential spam calls

2. **⚙️ Filter Rules**
   - Create country-based, location-based, or time-based rules
   - Combined rule types for complex filtering scenarios
   - Manage existing rules

3. **📞 Phone Lists**
   - Maintain separate whitelists, blacklists, and blocked lists
   - Add/remove numbers from any list
   - Export lists as CSV files

4. **📊 API History**
   - Track all number lookups
   - Visualize trends with interactive charts
   - Export history as CSV files

5. **🔧 Settings**
   - Configure API keys
   - Test database connection
   - Clear history and reset application settings

6. **📱 Aadhaar-Mobile Link Checker**
   - Add/manage Aadhaar-mobile number linkages
   - Check active mobile numbers
   - Track disconnected or reassigned numbers
   - View audit logs of disconnections

## 🛠️ Technologies Used

- **Frontend**: Streamlit
- **Database**: MongoDB
- **API**: NumLookup API for phone validation
- **Visualization**: Plotly Express
- **Styling**: Custom CSS, Streamlit Extras

## 🔧 Installation & Setup

1. **Install Requirements**

```bash
pip install streamlit requests pymongo pandas plotly streamlit-extras
```

2. **Set Up MongoDB**

You'll need a MongoDB instance. Update the `MONGO_URI` variable with your connection string:

```python
MONGO_URI = "your_mongodb_connection_string"
```

3. **API Configuration**

Get an API key from [NumLookup API](https://www.numlookupapi.com/) and update the `NUMLOOKUP_API_KEY` variable:

```python
NUMLOOKUP_API_KEY = "your_api_key"
```

4. **Run the Application**

```bash
streamlit run app.py
```

## 🗄️ Database Structure

The application uses the following MongoDB collections:

- `filter_rules`: Stores custom filter rules
- `phone_lists`: Manages whitelist, blacklist, and blocked numbers
- `api_history`: Tracks all API calls and responses
- `aadhar_data`: Stores Aadhaar-mobile linkage records
- `unlinked_history`: Tracks disconnected Aadhaar-mobile pairs

## 🔍 Key Functions

- `validate_number()`: Validates phone numbers using NumLookup API
- `check_filters()`: Applies filter rules to determine if a call should be allowed
- `update_phone_list()`: Manages phone number lists
- `get_api_stats()`: Generates statistics from API history
- `add_filter_rule()`: Creates new filter rules
- `remove_filter_rule()`: Deletes existing filter rules

## 🧩 Custom Components

The application includes several custom components:

- Styled cards for displaying information
- Colored headers for section titles
- Interactive charts for data visualization
- Custom CSS styling for a modern UI

## 🔒 Security Considerations

- API keys are handled securely
- MongoDB connection string is partially masked in the UI
- Password fields use the `type="password"` attribute

## 📊 Data Visualization

The application includes several visualizations:

- Pie charts showing spam vs. valid call distributions
- Line charts tracking API lookups over time
- Tabular data for detailed analysis

## 🔗 Aadhaar-Mobile Link Management

This specialized module allows:

- Adding Aadhaar-mobile number pairs
- Checking numbers against an active list
- Tracking disconnected or reassigned numbers
- Auditing changes with timestamp records

## 👨‍💻 Author

Created by [Mohit raj Bansal]

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

© 2025 Call Filter System - Version 2.0
