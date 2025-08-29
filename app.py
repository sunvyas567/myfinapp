# main.py
import streamlit as st
import pandas as pd
import json
import os
import re
import unicodedata
import math
import plotly.express as px
import plotly.graph_objects as go
import base64
from config_data import * # Import all data from the new config file
from fpdf import FPDF
from fpdf.enums import XPos, YPos # <-- ADD THIS LINE
import io
import requests
import streamlit_authenticator as stauth
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image
import google.generativeai as genai

st.set_page_config(page_title="Retirement Finance Planner", layout="wide")


# Add this line for debugging
st.write(st.secrets.to_dict()) 

# --- Firebase Initialization ---
try:
    if not firebase_admin._apps:

        # --- THIS IS THE FIX ---
        # When deployed on Streamlit Community Cloud, it will use the secrets.
        # Otherwise, it will fall back to the local JSON file.
        if 'firebase_credentials' in st.secrets:
            creds_dict = st.secrets["firebase_credentials"]
        else:
            with open("firebase_creds.json") as f:
                creds_dict = json.load(f)
        # This will use your local file for testing
        #with open("firebase_creds.json") as f:
        #    creds_dict = json.load(f)
        st.write("I am Here for Firebase certificate 1")
        # re-format it to include the proper newline characters.
        creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
        cred = credentials.Certificate(creds_dict)
        st.write("I am Here for Firebase certificate 2")
        firebase_admin.initialize_app(cred)
except Exception as e:
    st.error("Firebase initialization failed. Ensure 'firebase_creds.json' is in the correct folder.")
    st.stop()

db = firestore.client()

# --- YOUR EXISTING, WORKING AUTHENTICATION LOGIC (UNCHANGED) ---
def fetch_users():
    users_ref = db.collection('users').stream()
    users_data = {
        "credentials": {"usernames": {}},
        "cookie": {"name": "finance_sim_cookie_in", "key": "a_very_secret_key", "expiry_days": 0},
        "preauthorized": {"emails": []}
    }
    for user in users_ref:
        user_dict = user.to_dict()
        username = user.id
        users_data["credentials"]["usernames"][username] = {
            "email": user_dict.get("email"),
            "name": user_dict.get("name"),
            "password": user_dict.get("password_hash"),
            "premium": user_dict.get("premium", False)
        }
    return users_data

user_config = fetch_users()
authenticator = stauth.Authenticate(
    user_config['credentials'],
    user_config['cookie']['name'],
    user_config['cookie']['key'],
    user_config['cookie']['expiry_days']
)

# ############################################################################
#
# YOUR EXISTING, WORKING FUNCTIONS (UNCHANGED)
#
# ############################################################################

def clean_formula(formula):
    if not isinstance(formula, str) or not formula.startswith("="):
        return formula
    formula = formula[1:].strip()
    formula = unicodedata.normalize("NFKC", formula).strip()
    formula = formula.replace("−", "-").replace("\u2212", "-")
    return formula

def eval_formula_with_debug(formula, data_context, field_name):
    expression = clean_formula(formula)
    def replacer(match):
        var_name = match.group(1)
        val = data_context.get(var_name, {}).get("input", 0)
        try:
            return str(float(val))
        except (ValueError, TypeError):
            return "0"
    expression = re.sub(r"\{([^}]+)\}", replacer, expression)
    try:
        result = eval(expression, {"__builtins__": {"math": math, "min": min, "max": max}}, {})
        return result
    except Exception as e:
        st.error(f"❌ ERROR in `{field_name}` ({expression}): {e}")
        return 0

def render_text_sheet(sheet_name, is_guest=False):
    st.header(sheet_name)
    if sheet_name == "AboutApp":
        st.markdown(ABOUT_APP_TEXT)
    elif sheet_name == "KnowledgebaseFAQ":
        df = pd.DataFrame(KNOWLEDGEBASE_FAQ_DATA)
        st.dataframe(df, use_container_width=True)

def plot_onetime_expenses(df_config, user_data):
    df = df_config.copy()
    
    # Get the latest values from user_data
    def get_resolved_value(name):
        return user_data.get(name, {}).get("input", 0)

    df["Resolved Value"] = df["Field Name"].apply(get_resolved_value)
    
    # Exclude total rows from the chart
    df_plot = df[~df["Field Name"].str.contains("Total|GrandTotal")]

    # Separate 'Must' and 'Delayed' expenses
    df_must = df_plot[df_plot["Type"].str.lower() == "must"]
    df_delayed = df_plot[df_plot["Type"].str.lower() == "delayed"]

    # Create charts
    for sub_df, title in zip([df_must, df_delayed], ["Must Have Expenses", "Delayed Expenses"]):
        if not sub_df.empty:
            fig = px.bar(sub_df, x="Field Description", y="Resolved Value", title=title, text_auto='.2s')
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

def plot_recurring_expenses(df_config, user_data):
    df = df_config.copy()
    
    def get_resolved_value(name):
        return user_data.get(name, {}).get("input", 0)

    df["Resolved Value"] = df["Field Name"].apply(get_resolved_value) * 12 # Annualize
    
    # Exclude total rows and zero values from the pie chart
    df_plot = df[(~df["Field Name"].str.contains("Total")) & (df["Resolved Value"] > 0)]

    if not df_plot.empty:
        fig = px.pie(df_plot, names="Field Description", values="Resolved Value", title="Annual Recurring Expenses Breakdown")
        st.plotly_chart(fig, use_container_width=True)

def store_and_eval_all_variables(calc_context):
    # This function now only calculates secondary formulas (like totals)
    # and will NOT overwrite any primary values calculated in the yearly loop.
    for item in INVESTMENT_PLAN_CONFIG:
        varname = item["Field Name"]
        
        # If a value was already calculated by our yearly loop, DO NOT overwrite it.
        if varname in calc_context and "manual" in calc_context[varname].get("source", ""):
            continue

        formula = item["Field Value"]
        if isinstance(formula, str) and formula.startswith("="):
            value = eval_formula_with_debug(formula, calc_context, varname)
            if varname not in calc_context:
                calc_context[varname] = {}
            calc_context[varname]["input"] = value

def render_input_form(config_data, sheet_name, is_guest=False):
    # Define icons for the fields
    FIELD_ICONS = {
        "LocalKidsEducation": "🎓", "LocalHouseRenovation": "🏡", "LocalVehicleRenewal": "🚗",
        "LocalJewelry": "💎", "LocalTravelForeign": "✈️", "LocalOthers": "🛍️",
        "LocalMarriages": "💍", "LocalProperty": "🏘️",
        "LocalTotalOneTimeMust": "✅", "LocalTotalOneTimeDelayed": "🏖️", "GrandTotalOneTime": "∑"
    }

    if sheet_name == "Capture Basic Data":
        st.header("📊 Base Data & Assumptions")
        st.markdown("Enter your details below. Start with the basics and expand other sections as needed.")

        if not is_premium and not is_guest:
            st.warning("Free accounts are limited to a 2-year projection. Upgrade to Premium for unlimited planning!")
            user_data['GLProjectionYears'] = {'input': 2}

        # Helper function to generate a field, making the code cleaner
        def generate_field(varname, label, default_val, editable=True, is_percent=False):
            if not editable:
                display_value = f"{default_val:,.1f}%" if is_percent else f"{default_val:,.0f}"
                st.metric(label=label, value=display_value)
                if varname not in user_data:
                    user_data[varname] = {"input": default_val}
            else:
                current_value = float(user_data.get(varname, {}).get("input", default_val))
                # Apply the disabled flag for guest mode
                user_input = st.number_input(label, value=current_value, key=varname, disabled=is_guest)
                user_data[varname] = {"input": user_input}

        field_map = {item["Field Name"]: item for item in config_data}

        # --- Main Layout ---
        col1, col2 = st.columns(2)

        with col1:
            with st.container(border=True):
                st.subheader("👤 Personal Info")
                generate_field("GLAge", "Current Age", field_map["GLAge"]["Field Default Value"])
                gender_options = ["Male", "Female"]
                current_gender = user_data.get("GLGender", {}).get("input", field_map["GLGender"]["Field Default Value"])
                user_gender = st.selectbox("Gender", options=gender_options, index=gender_options.index(current_gender) if current_gender in gender_options else 0, key="GLGender", disabled=is_guest)
                user_data["GLGender"] = {"input": user_gender}
        
        with col2:
            with st.container(border=True):
                st.subheader("🗓️ Core Assumptions")
                # Make projection years non-editable for free users, but viewable for guests
                generate_field("GLProjectionYears", "Projection Years", user_data.get("GLProjectionYears", {}).get("input", field_map["GLProjectionYears"]["Field Default Value"]), editable=(is_premium and not is_guest))
                generate_field("GLInflationRate", "Assumed Annual Inflation", field_map["GLInflationRate"]["Field Default Value"], is_percent=True, editable=not is_guest)

        # --- Rates Section with Edit Toggle ---
        with st.container(border=True):
            st.subheader("📈 Interest Rates & Growth Assumptions")
            edit_rates = st.checkbox("Edit Default Rates and Assumptions", disabled=is_guest)

            rate_cols = st.columns(4)
            rate_fields = ["GLSrCitizenFDRate", "GLNormalFDRate", "GLSCSSRate", "GLPOMISRate"]
            
            for i, field_name in enumerate(rate_fields):
                with rate_cols[i]:
                    item = field_map[field_name]
                    generate_field(item["Field Name"], item['Field Description'], item["Field Default Value"], editable=edit_rates and not is_guest, is_percent=True)

            st.markdown("---")
            swp_cols = st.columns(2)
            with swp_cols[0]:
                item = field_map["GLSWPGrowthRate"]
                generate_field(item["Field Name"], item['Field Description'], item["Field Default Value"], editable=edit_rates and not is_guest, is_percent=True)
            with swp_cols[1]:
                item = field_map["GLSWPMonthlyWithdrawal"]
                generate_field(item["Field Name"], item['Field Description'], item["Field Default Value"], editable=not is_guest)

        # --- Advanced Settings are hidden by default in an Expander ---
        with st.expander("⚙️ Advanced Settings: Initial Corpus, Other Income & Allocations"):
            c1, c2 = st.columns(2)
            with c1:
                with st.container(border=True):
                    st.subheader("💰 Initial Corpus")
                    corpus_fields = ["GLPFAccumulation", "GLPPFAccumulation", "GLSuperannuation"]
                    for field_name in corpus_fields:
                        item = field_map[field_name]
                        generate_field(item["Field Name"], item["Field Description"], item["Field Default Value"], editable=not is_guest)

            with c2:
                with st.container(border=True):
                    st.subheader("🏠 Other Income Sources (Yearly)")
                    other_income_fields = ["GLDividendIncome", "GLAgricultureIncome", "GLTradingIncome", "GLRealStateIncome", "GLConsultingIncome"]
                    for field_name in other_income_fields:
                        item = field_map[field_name]
                        generate_field(item["Field Name"], item["Field Description"], item["Field Default Value"], editable=not is_guest)
            
            st.markdown("---")
            c3, c4 = st.columns(2)
            with c3:
                with st.container(border=True):
                    st.subheader("📊 Investment Allocation")
                    alloc_fields = ["GLSWPInvestmentPercentage", "GLNonSWPInvestmentPercentage", "GLNormalFDExcludingPOMISSCSS", "GLSrCitizenFDExcludingPOMISSCSS"]
                    for field_name in alloc_fields:
                        item = field_map[field_name]
                        generate_field(item["Field Name"], item["Field Description"], item["Field Default Value"], is_percent=True, editable=not is_guest)
            
            with c4:
                with st.container(border=True):
                    st.subheader("🏦 Other Allowances & Annuities")
                    allowance_fields = ["GLPOMISSingle", "GLSCSSSingle", "GLCurrentMonthlyRental", "GLMaxMonthlyRental", "GLAnnuityExistingMonthly", "GLPensionEPS"]
                    for field_name in allowance_fields:
                        item = field_map[field_name]
                        generate_field(item["Field Name"], item["Field Description"], item["Field Default Value"], editable=not is_guest)

    elif sheet_name == "Capture Major One Time Expenses":
        st.header("💸 One-Time Expenses")
        st.markdown("Enter any large, one-off expenses you anticipate for retirement.")
        
        field_map = {item["Field Name"]: item for item in config_data}

        def generate_expense_field(varname, editable=True):
            item = field_map[varname]
            icon = FIELD_ICONS.get(varname, "💰")
            label = f"{icon} {item['Field Description']}"
            default_val = item["Field Default Value"]
            

            # --- THIS IS THE FIX ---
            # Check if the field is a formula before trying to evaluate it
            if not editable and isinstance(item.get("Field Input"), str) and item["Field Input"].startswith("="):
                # For calculated totals
                calculated_val = eval_formula_with_debug(item["Field Input"], user_data, varname)
                st.metric(label=label, value=f"{calculated_val:,.0f}")
                user_data[varname] = {"input": calculated_val}
            else:
                # For regular user inputs
                current_value = float(user_data.get(varname, {}).get("input", default_val))
                user_input = st.number_input(label, value=current_value, key=varname, disabled=is_guest)
                user_data[varname] = {"input": user_input}

            #if editable:
            #   current_value = float(user_data.get(varname, {}).get("input", default_val))
            #    user_input = st.number_input(label, value=current_value, key=varname, disabled=is_guest)
            #    user_data[varname] = {"input": user_input}
            #else:
            #    calculated_val = eval_formula_with_debug(item["Field Input"], user_data, varname)
            #    st.metric(label=label, value=f"{calculated_val:,.0f}")
            #    user_data[varname] = {"input": calculated_val}
        
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.subheader("✅ Must-Have Expenses")
                must_fields = ["LocalKidsEducation", "LocalHouseRenovation", "LocalVehicleRenewal", "LocalJewelry", "LocalTravelForeign", "LocalOthers"]
                for field in must_fields:
                    generate_expense_field(field, editable=not is_guest)
                st.markdown("---")
                generate_expense_field("LocalTotalOneTimeMust", editable=False)

        with col2:
            with st.container(border=True):
                st.subheader("🏖️ Optional / Delayed Expenses")
                delayed_fields = ["LocalMarriages", "LocalProperty"]
                for field in delayed_fields:
                    generate_expense_field(field, editable=not is_guest)
                st.markdown("---")
                generate_expense_field("LocalTotalOneTimeDelayed", editable=False)
        
        st.markdown("##")
        with st.container(border=True):
            generate_expense_field("GrandTotalOneTime", editable=False)
        
        df = pd.DataFrame(config_data)
        plot_onetime_expenses(df, user_data)

def render_expenses_recurring(config_data, sheet_name, is_guest=False):
    st.header("🗓️ Monthly Recurring Expenses")
    st.markdown("Enter your typical monthly spending. The tool will calculate the annual total and apply inflation.")

    field_map = {item["Field Name"]: item for item in config_data}
    
    FIELD_ICONS = {
        "LocalGroceryVeg": "🛒", "LocalWaterElectricity": "💡", "LocalHouseRepairs": "🛠️", "LocalMaidServices": "🧹",
        "LocalInsuranceVehicle": "🛡️", "LocalTransportFuel": "⛽", "LocalVehicleMaintenance": "🔧",
        "LocalEntertainment": "🎬", "LocalInternetMobileTelecom": "📱", "LocalTVOTT": "📺", "LocalTravelLeisureInland": "🏞️", "LocalFunctionsEtc": "🎉",
        "LocalPropertyTax": "🧾", "LocalMedicalInsurance": "🩺", "LocalMiscellaneousTax": "💸",
        "LocalTravelLeisureForeignOpt": "✈️", "LocalOthersOpt": "🛍️"
    }

    expense_groups = {
        "🏡 Home & Utilities": ["LocalGroceryVeg", "LocalWaterElectricity", "LocalHouseRepairs", "LocalMaidServices"],
        "🚗 Transport & Auto": ["LocalInsuranceVehicle", "LocalTransportFuel", "LocalVehicleMaintenance"],
        "🎉 Lifestyle & Entertainment": ["LocalEntertainment", "LocalInternetMobileTelecom", "LocalTVOTT", "LocalTravelLeisureInland", "LocalFunctionsEtc"],
        "💰 Taxes & Insurance": ["LocalPropertyTax", "LocalMedicalInsurance", "LocalMiscellaneousTax"],
        "✈️ Optional Expenses": ["LocalTravelLeisureForeignOpt", "LocalOthersOpt"]
    }

    def generate_recurring_field(varname):
        item = field_map[varname]
        icon = FIELD_ICONS.get(varname, "💵")
        label = f"{icon} {item['Field Description'].split(' (')[0]}"
        default_val = item["Field Default Value"]
        current_value = float(user_data.get(varname, {}).get("input", default_val))
        
        cols = st.columns([2, 1])
        with cols[0]:
            user_input = st.number_input(label, value=current_value, key=varname, disabled=is_guest)
        with cols[1]:
            st.metric(label="Yearly", value=f"{user_input * 12:,.0f}")
            
        user_data[varname] = {"input": user_input}

    for group_title, fields in expense_groups.items():
        with st.container(border=True):
            st.subheader(group_title)
            c1, c2 = st.columns(2)
            for i, field_name in enumerate(fields):
                if i % 2 == 0:
                    with c1:
                        generate_recurring_field(field_name)
                else:
                    with c2:
                        generate_recurring_field(field_name)

    st.markdown("---")
    st.subheader("Totals")
    total_cols = st.columns(2)
    with total_cols[0]:
        total_must_val = eval_formula_with_debug(field_map["GLTotalYearlyExpensesMust"]["Field Input"], user_data, "GLTotalYearlyExpensesMust")
        st.metric("Total Yearly (Must-Have)", f"{total_must_val * 12:,.0f}")
        user_data["GLTotalYearlyExpensesMust"] = {"input": total_must_val}

    with total_cols[1]:
        total_opt_val = eval_formula_with_debug(field_map["GLTotalYearlyExpensesOptional"]["Field Input"], user_data, "GLTotalYearlyExpensesOptional")
        st.metric("Total Yearly (Optional)", f"{total_opt_val * 12:,.0f}")
        user_data["GLTotalYearlyExpensesOptional"] = {"input": total_opt_val}

    df = pd.DataFrame(config_data)
    plot_recurring_expenses(df, user_data)

def inject_pwa_script():
    """
    Injects the PWA manifest and service worker registration script into the app.
    """
    # Read the manifest and service worker files
    try:
        with open("manifest.json", "r") as f:
            manifest_content = f.read()
        with open("service-worker.js", "r") as f:
            service_worker_content = f.read()
    except FileNotFoundError:
        st.error("PWA files (manifest.json, service-worker.js) not found. Please ensure they are in the root directory.")
        return

    # PWA registration script
    pwa_script = f"""
    <link rel="manifest" href="data:application/manifest+json;base64,{base64.b64encode(manifest_content.encode()).decode()}">
    <script>
        if ('serviceWorker' in navigator) {{
            const swContent = `{service_worker_content}`;
            const swBlob = new Blob([swContent], {{type: 'application/javascript'}});
            const swUrl = URL.createObjectURL(swBlob);

            navigator.serviceWorker.register(swUrl).then(function(registration) {{
                console.log('Service Worker registration successful with scope: ', registration.scope);
            }}).catch(function(err) {{
                console.log('Service Worker registration failed: ', err);
            }});
        }}
    </script>
    """
    st.markdown(pwa_script, unsafe_allow_html=True)

def calculate_projections():
    """
    Runs the full financial projection loop and returns the calculated data.
    """
    projection_years = int(user_data.get("GLProjectionYears", {}).get("input", 1))
    if projection_years <= 0:
        return None, None

    base_context = json.loads(json.dumps(user_data))
    store_and_eval_all_variables(base_context)
    
    # --- Get all base values needed for the loop ---
    inflation_rate = base_context.get("GLInflationRate", {}).get("input", 0) / 100.0
    base_monthly_rental = base_context.get("GLCurrentMonthlyRental", {}).get("input", 0)
    max_monthly_rental = base_context.get("GLMaxMonthlyRental", {}).get("input", 0)
    recurring_expense_varnames = [item['Field Name'] for item in RECURRING_EXPENSES_CONFIG if not item['Field Name'].startswith('GLTotal')]
    base_recurring_expenses = {var: base_context.get(var, {}).get('input', 0) for var in recurring_expense_varnames}
    
    # Create a map for recurring expense formulas
    recurring_field_map = {item["Field Name"]: item for item in RECURRING_EXPENSES_CONFIG}
    
    fd_investment_fund = base_context.get("LocalFDInvestmentFund", {}).get("input", 0)
    scss_amount = base_context.get("LocalSCSSAmount", {}).get("input", 0)
    pomis_amount = base_context.get("LocalPOMISAmount", {}).get("input", 0)
    normal_fd_percent = base_context.get("LocalNormalFDPercent", {}).get("input", 0) / 100.0
    sr_citizen_fd_percent = 1.0 - normal_fd_percent
    
    normal_fd_rate = base_context.get("GLNormalFDRate", {}).get("input", 0) / 100.0
    sr_citizen_fd_rate = base_context.get("GLSrCitizenFDRate", {}).get("input", 0) / 100.0
    pomis_rate = base_context.get("GLPOMISRate", {}).get("input", 0) / 100.0
    scss_rate = base_context.get("GLSCSSRate", {}).get("input", 0) / 100.0
    
    swp_monthly_rate = base_context.get("LocalSWPMonthlyRate", {}).get("input", 0)
    swp_monthly_withdrawal = base_context.get("GLSWPMonthlyWithdrawal", {}).get("input", 0)
    
    all_years_data = []
    swp_corpus = base_context.get("LocalSWPInvestAmount", {}).get("input", 0)

    for year in range(1, projection_years + 1):
        calc_context = json.loads(json.dumps(base_context))
        
        yearly_interest = swp_corpus * ((1 + swp_monthly_rate) ** 12 - 1)
        yearly_withdrawal = swp_monthly_withdrawal * 12
        ending_balance = swp_corpus + yearly_interest - yearly_withdrawal
        
        calc_context["LocalSWPInvestAmount"] = {"input": swp_corpus, "source": "manual"}
        calc_context["LocalSWPYearlyInterest"] = {"input": yearly_interest, "source": "manual"}
        calc_context["LocalSWPYearlyWithdrawal"] = {"input": yearly_withdrawal, "source": "manual"}
        calc_context["LocalSWPBalancePostWithdrawal"] = {"input": ending_balance, "source": "manual"}
        calc_context["GLSWPCorpusStatus"] = {"input": ending_balance - swp_corpus, "source": "manual"}
        
        # Inflate recurring expenses
        for varname, base_value in base_recurring_expenses.items():
            calc_context[varname] = {"input": base_value * ((1 + inflation_rate) ** (year - 1)), "source": "manual"}
        
        # ** THE FIX - Part 1: Explicitly calculate expense totals for the year **
        must_formula = recurring_field_map["GLTotalYearlyExpensesMust"]["Field Input"]
        optional_formula = recurring_field_map["GLTotalYearlyExpensesOptional"]["Field Input"]
        total_must_val = eval_formula_with_debug(must_formula, calc_context, "GLTotalYearlyExpensesMust")
        total_opt_val = eval_formula_with_debug(optional_formula, calc_context, "GLTotalYearlyExpensesOptional")
        calc_context["GLTotalYearlyExpensesMust"] = {"input": total_must_val, "source": "manual"}
        calc_context["GLTotalYearlyExpensesOptional"] = {"input": total_opt_val, "source": "manual"}
        
        # Inflate rental income
        inflated_monthly_rental = base_monthly_rental * ((1 + inflation_rate) ** (year - 1))
        calc_context["LocalRentalIncome"] = {"input": min(inflated_monthly_rental, max_monthly_rental) * 12, "source": "manual"}

        # Time-based FD logic
        if year <= 5:
            fd_principal = fd_investment_fund - scss_amount - pomis_amount
            calc_context["LocalNormalFDYearlyIncome"] = {"input": fd_principal * normal_fd_percent * normal_fd_rate, "source": "manual"}
            calc_context["LocalSrFDYearlyIncomeFirst5"] = {"input": fd_principal * sr_citizen_fd_percent * sr_citizen_fd_rate, "source": "manual"}
            calc_context["LocalPOMISYearlyIncome"] = {"input": pomis_amount * pomis_rate, "source": "manual"}
            calc_context["LocalSCSSYearlyIncome"] = {"input": scss_amount * scss_rate, "source": "manual"}
            calc_context["LocalSrFDYearlyIncomePast5"] = {"input": 0, "source": "manual"}
        else:
            fd_principal = fd_investment_fund
            calc_context["LocalNormalFDYearlyIncome"] = {"input": fd_principal * normal_fd_percent * normal_fd_rate, "source": "manual"}
            calc_context["LocalSrFDYearlyIncomePast5"] = {"input": fd_principal * sr_citizen_fd_percent * sr_citizen_fd_rate, "source": "manual"}
            calc_context["LocalSrFDYearlyIncomeFirst5"] = {"input": 0, "source": "manual"}
            calc_context["LocalPOMISYearlyIncome"] = {"input": 0, "source": "manual"}
            calc_context["LocalSCSSYearlyIncome"] = {"input": 0, "source": "manual"}

        store_and_eval_all_variables(calc_context)
        
        # ** THE FIX - Part 2: Collect all relevant data for the year **
        year_data = {"Year": year}
        for key, value_dict in calc_context.items():
            if "input" in value_dict:
                year_data[key] = value_dict["input"]
        all_years_data.append(year_data)
        
        swp_corpus = ending_balance
    
    df_out = pd.DataFrame(all_years_data) if all_years_data else pd.DataFrame()
    return df_out, base_context

def render_summary_page_old(config_data, is_guest=False):
    # ... (Your existing function, modified below) ...
    st.header("📄 Financial Summary")
    df_projections, year_1_context = calculate_projections()
    if df_projections is None or df_projections.empty:
        st.warning("Please set a valid 'Projection Years' value in the BaseData page to see the summary.")
        return
    # (Your existing metrics and charts logic goes here)
    st.markdown("---")
    if is_guest or not is_premium:
        st.info("Download PDF reports and get personalized AI advice by upgrading to Premium.")
    else:
        # (Your existing AI and PDF buttons go here)
        pass

def render_summary_page(config_data, is_guest=False):
    st.header("📄 Financial Summary")
    st.markdown("This page provides a high-level overview of your financial projection.")

    df_projections, year_1_context = calculate_projections()

    if df_projections is None or df_projections.empty:
        st.warning("Please set a valid 'Projection Years' value in the BaseData page to see the summary.")
        return

    # --- Key Metrics ---
    st.subheader("Key Initial Figures")
    c1, c2, c3 = st.columns(3)
    with c1:
        total_one_time = year_1_context.get("GrandTotalOneTime", {}).get("input", 0)
        st.metric("Total One-Time Expenses", f"{total_one_time:,.0f}")
    with c2:
        total_must_recurring = year_1_context.get("GLTotalYearlyExpensesMust", {}).get("input", 0)
        st.metric("Annual Recurring Expenses (Must)", f"{total_must_recurring * 12:,.0f}")
    with c3:
        initial_corpus = year_1_context.get("LocalStartingCorpus", {}).get("input", 0)
        st.metric("Starting Investment Corpus", f"{initial_corpus:,.0f}")
    
    st.markdown("---")

    # --- Income vs Expense Chart ---
    st.subheader("Income vs. Expenses Over Time")
    
    # Calculate Total Expenses
    df_projections['TotalYearlyExpenses'] = df_projections['GLTotalYearlyExpensesMust'] + df_projections['GLTotalYearlyExpensesOptional']
    
    # Prepare data for plotting
    df_chart = df_projections[['Year', 'GLTotalIncomeOverallFDs', 'TotalYearlyExpenses']].copy()
    df_chart.rename(columns={'GLTotalIncomeOverallFDs': 'Total Income', 'TotalYearlyExpenses': 'Total Expenses'}, inplace=True)
    
    fig_iv_exp = px.line(df_chart, x='Year', y=['Total Income', 'Total Expenses'], title="Income vs. Expense Projection", markers=True)
    fig_iv_exp.update_layout(yaxis_title="Amount (₹)")
    st.plotly_chart(fig_iv_exp, use_container_width=True)

    # --- Expense Breakdown Charts ---
    st.subheader("Initial Expense Breakdown")
    c1, c2 = st.columns(2)
    with c1:
        plot_onetime_expenses(pd.DataFrame(ONETIME_EXPENSES_CONFIG), user_data)
    with c2:
        plot_recurring_expenses(pd.DataFrame(RECURRING_EXPENSES_CONFIG), user_data)
    
    st.markdown("---")

    if is_guest or not is_premium:
        st.info("Download PDF reports and get personalized AI advice by upgrading to Premium.")
    
    else:
        # --- AI Financial Coach Section (NEW) ---
        # moved to new tab
        # --- PDF Download Section ---
        st.subheader("Download Report")

        if st.button("Generate Summary PDF"):
            with st.spinner("Creating PDF..."):
                
                # Prepare data for PDF
                summary_data = {
                    "key_metrics": {
                        "Total One-Time Expenses": total_one_time,
                        "Annual Recurring Expenses (Must)": total_must_recurring * 12,
                        "Starting Investment Corpus": initial_corpus
                    },
                    "income_expense_chart": fig_iv_exp.to_image(format="png", scale=2),
                    "projections_df": df_projections
                }
                
                # Create PDF in memory
                pdf = FPDF()
                pdf.add_page()

                #--- THIS IS THE FIX ---
                # Use the new syntax for cell creation
                pdf.set_font("Helvetica", 'B', 16)
                pdf.cell(0, 10, 'Financial Summary Report', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
                
                pdf.set_font("Helvetica", 'B', 12)
                pdf.cell(0, 10, 'Key Initial Figures', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
                pdf.set_font("Helvetica", '', 10)
                for key, value in summary_data["key_metrics"].items():
                    pdf.cell(0, 8, f"- {key}: {value:,.0f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(10)

                # Income vs Expense Chart
                pdf.set_font("Helvetica", 'B', 12)
                pdf.cell(0, 10, 'Income vs. Expenses Over Time', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
                pdf.image(io.BytesIO(summary_data["income_expense_chart"]), w=190)
                pdf.ln(10)
                
                # Display a small part of the projection table
                pdf.set_font("Helvetica", 'B', 12)
                pdf.cell(0, 10, 'Yearly Projection Data (Sample)',new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
                pdf.set_font("Helvetica", 'B', 8)
                pdf.cell(20, 8, 'Year', 1)
                pdf.cell(50, 8, 'Total Income', 1)
                pdf.cell(50, 8, 'Total Expenses', 1)
                pdf.cell(50, 8, 'Ending SWP Corpus', 1)
                pdf.ln()
                
                pdf.set_font("Helvetica", '', 8)
                for _, row in df_chart.head(15).iterrows(): # Show first 15 years
                    pdf.cell(20, 8, str(int(row['Year'])), 1)
                    pdf.cell(50, 8, f"{row['Total Income']:,.0f}", 1)
                    pdf.cell(50, 8, f"{row['Total Expenses']:,.0f}", 1)
                    ending_corpus = df_projections.loc[df_projections['Year'] == row['Year'], 'LocalSWPBalancePostWithdrawal'].iloc[0]
                    pdf.cell(50, 8, f"{ending_corpus:,.0f}", 1)
                    pdf.ln()

                # ** THE FIX: Convert the bytearray to bytes **
                pdf_output = bytes(pdf.output())
                
                st.download_button(
                    label="📥 Download as PDF",
                    data=pdf_output,
                    file_name=f"{st.session_state['username']}_financial_summary.pdf",
                    mime="application/pdf"
                )

# It now calls the central calculation function.
def render_output_table(config_data, sheet_name,is_guest=False):
    st.header("📈 Investment Plan Projections")
    
    df_projections, year_1_context = calculate_projections()
    
    if df_projections is None or df_projections.empty:
        st.warning("Please set a valid 'Projection Years' value in the BaseData page to see the projection.")
        return

    # --- UI and DataFrame Manipulation Starts Here ---
    all_fields_ordered = [item['Field Name'] for item in config_data]
    
    all_fields_ordered.remove('LocalSWPInvestAmount')
    pomis_index = all_fields_ordered.index('LocalPOMISAmount')
    all_fields_ordered.insert(pomis_index + 1, 'LocalSWPInvestAmount')

    split_index = all_fields_ordered.index('LocalSWPInvestAmount')
    static_fields = all_fields_ordered[:split_index]
    dynamic_fields = all_fields_ordered[split_index:]

    desc_map = {item["Field Name"]: item["Field Description"] for item in config_data}
    year_1_data = df_projections.iloc[0].to_dict()

    st.subheader("Initial Investment Setup (Calculated for Year 1)")
    with st.container(border=True):
        cols = st.columns(3)
        col_idx = 0
        for field_name in static_fields:
            if field_name not in year_1_data: continue
            with cols[col_idx]:
                label = desc_map.get(field_name, field_name).split("(")[0]
                value = year_1_data[field_name]
                st.metric(label=label, value=f"{value:,.0f}")
            col_idx = (col_idx + 1) % len(cols)

    st.subheader("Year-over-Year Financial Projections")
    
    df_for_display = df_projections.drop(columns=['Year']).T
    df_for_display.columns = [f"Year {y+1}" for y in range(len(df_projections))]

    df_dynamic_display = df_for_display[df_for_display.index.isin(dynamic_fields)]
    df_dynamic_display = df_dynamic_display.reindex(dynamic_fields)

    df_dynamic_display.insert(0, "Field Description", df_dynamic_display.index.map(desc_map))

    final_table = df_dynamic_display.reset_index(drop=True)
    st.dataframe(final_table.style.format(precision=0, thousands=","), hide_index=True)
    
    # Charting
    fields_to_plot = [
        "LocalNormalFDYearlyIncome", "LocalSrFDYearlyIncomeFirst5", "LocalSrFDYearlyIncomePast5",
        "LocalPOMISYearlyIncome", "LocalSCSSYearlyIncome", "LocalRentalIncome", "LocalDividentIncome",
        "LocalAnnuityExisting", "LocalAnnuityNew", "LocalPensionEPS", "LocalTradingIncome",
        "LocalRealStateIncome", "LocalConsultingIncome", "GLSWPCorpusStatus" 
    ]
    
    plot_df = df_projections[["Year"] + [f for f in fields_to_plot if f in df_projections.columns]]
    plot_df = plot_df.melt(id_vars="Year", var_name="Income/Gain Source", value_name="Amount")
    desc_map_plot = {name: desc.split(" - ")[0].split("(")[0] for name, desc in desc_map.items()}
    plot_df["Income/Gain Source"] = plot_df["Income/Gain Source"].map(desc_map_plot)

    fig = px.bar(plot_df, x="Year", y="Amount", color="Income/Gain Source", title="Yearly Income & SWP Gain/Loss Projection")
    fig.update_layout(barmode="relative", xaxis_title="Year", yaxis_title="Amount (₹)")
    st.plotly_chart(fig, use_container_width=True)

def calculate_initial_totals(data_context):
        """
        Calculates all formula-based fields from the config files and adds them
        to the data context. This should be run after loading user data.
        """
        all_configs = BASE_DATA_CONFIG + ONETIME_EXPENSES_CONFIG + RECURRING_EXPENSES_CONFIG
        
        for item in all_configs:
            key = item.get('Field Name')
            formula = item.get('Field Default Value', '')
            
            if key and isinstance(formula, str) and formula.startswith('='):
                # If a field is a formula, calculate its value
                value = eval_formula_with_debug(formula, data_context, key)
                if key not in data_context:
                    data_context[key] = {}
                data_context[key]['input'] = value
        
        return data_context

# ############################################################################
#
# NEW APPLICATION FLOW LOGIC
# This section wraps your existing functions into a new, professional flow.
#
# ############################################################################

# --- Main Controller / Router ---

# This function contains your main app logic and is called when a user is logged in or in guest mode.
def run_simulator(is_guest=False):
    # (Your existing, working run_simulator function goes here, unchanged)
    # The only change is inside the sidebar for the guest mode button.
    global user_data, is_premium, STORAGE_FILE
    
    #print(f"DEBUG: Running Simulator")
    if not is_guest:
        # --- THIS IS THE FIX ---
        # The logout button now correctly resets the view state and immediately
        # stops the current script run before the KeyError can happen.
        #if st.sidebar.button("Logout"):
        #   authenticator.logout()
        #   st.session_state.view = "landing"
        #   st.rerun()
        username = st.session_state["username"]
        is_premium = user_config['credentials']['usernames'][username]['premium']
        STORAGE_FILE = f"{username}_user_data.json"
    else:
        username = "guest"
        is_premium = False
        STORAGE_FILE = "guest_user_data.json"
        #st.sidebar.title("Guest Mode")
        #st.sidebar.info("This is a live demo with sample data.")
        #if st.sidebar.button("Sign Up for Free to Create Your Own Plan"):
        #    st.session_state.view = "login"
        #    st.rerun()

    def load_user_data():
        if os.path.exists(STORAGE_FILE):
            with open(STORAGE_FILE, "r") as f:
                try: return json.load(f)
                except json.JSONDecodeError: return {}
        default_data = {}
        all_configs = BASE_DATA_CONFIG + ONETIME_EXPENSES_CONFIG + RECURRING_EXPENSES_CONFIG
        for item in all_configs:
            key = item.get('Field Name')
            if key and not (isinstance(item.get('Field Default Value', ''), str) and item.get('Field Default Value', '').startswith('=')):
                default_data[key] = {'input': item.get('Field Default Value')}
        return default_data

    def save_user_data(data):
        if not is_guest:
            with open(STORAGE_FILE, "w") as f:
                json.dump(data, f, indent=2)

    user_data = load_user_data()
    user_data = calculate_initial_totals(user_data)

    # --- Main App Layout ---
    if not is_guest:
        st.sidebar.title(f"Welcome, {st.session_state['name']}!")
    else:
        st.sidebar.title("Guest Mode")
        st.sidebar.info("This is a live demo with sample data.")
        if st.sidebar.button("Create Your Free Account"):
           st.session_state.view = "register"
           st.rerun()

    if not is_guest and is_premium:
        st.sidebar.success("Premium Member ✨")
    elif not is_guest:
        if st.sidebar.button("Upgrade to Premium 🚀"):
            st.session_state.page = "Upgrade"
            st.rerun()

    # --- Navigation ---
    pages = ["AboutApp", "Capture Basic Data", "Capture Major One Time Expenses", "Capture Recurring Expenses", 
             "Investment Plan", "Your Financial Summary", "KnowledgebaseFAQ"]
    if is_premium:
        pages.insert(6, "AI Advisor")

    if 'page' not in st.session_state or st.session_state.page not in pages + ["Upgrade"]:
        st.session_state.page = "AboutApp"

    # Handle the Upgrade page BEFORE rendering the main navigation.
    if st.session_state.page == "Upgrade":
        st.title("🚀 Upgrade to Premium with Payment via Gateway")
        st.image("https://placehold.co/250x250/ffffff/000000?text=Scan+Me", width=250)
        if st.button("Payment Done"):
            #db.collection('users').document(username).update({"premium": True})
            st.success("This is trial version so payment option is available to upgrade to Premiium.")
            st.session_state.page = "Summary"
            st.balloons()
            st.rerun()
    else:
        # --- Standard Navigation and Page Rendering ---
        with st.sidebar:
            selection = st.radio("Go to", pages, index=pages.index(st.session_state.page))
            if selection != st.session_state.page:
                st.session_state.page = selection
                st.rerun()
        
        pages_config = {
            "AboutApp": {"config": None, "render_func": render_text_sheet},
            "Capture Basic Data": {"config": BASE_DATA_CONFIG, "render_func": render_input_form},
            "Capture Major One Time Expenses": {"config": ONETIME_EXPENSES_CONFIG, "render_func": render_input_form},
            "Capture Recurring Expenses": {"config": RECURRING_EXPENSES_CONFIG, "render_func": render_expenses_recurring},
            "Investment Plan": {"config": INVESTMENT_PLAN_CONFIG, "render_func": render_output_table},
            "Your Financial Summary": {"config": None, "render_func": render_summary_page},
            "AI Advisor": {"config": None, "render_func": render_ai_advisor_page},
            "KnowledgebaseFAQ": {"config": None, "render_func": render_text_sheet}
        }
        
        selected_page = pages_config[st.session_state.page]
        if selected_page["config"]:
            selected_page["render_func"](selected_page["config"], st.session_state.page, is_guest=is_guest)
        else:
            selected_page["render_func"](st.session_state.page, is_guest=is_guest)
    
    if not is_guest:
        save_user_data(user_data)

def run_onboarding_wizard():
    st.title("Welcome! Let's set up your financial plan.")
    st.markdown("We just need a few key details to get started. You can add more later.")

    with st.form("onboarding_form"):
        age = st.number_input("What is your current age?", min_value=18, max_value=100, value=45)
        initial_corpus = st.number_input("What is your approximate current investment corpus (PF, PPF, etc.)?", min_value=0, value=5000000)
        monthly_expenses = st.number_input("What are your approximate total monthly expenses?", min_value=0, value=50000)
        
        submitted = st.form_submit_button("Create My First Plan!")
        if submitted:
            username = st.session_state["username"]
            STORAGE_FILE = f"{username}_user_data.json"
            user_data = {}
            user_data['GLAge'] = {'input': age}
            # ... (save other wizard inputs to user_data) ...
            with open(STORAGE_FILE, "w") as f:
                json.dump(user_data, f, indent=2)

            db.collection('users').document(username).update({"onboarding_complete": True})
            st.session_state.onboarding_complete = True
            st.session_state.page = "Summary"
            st.rerun()

def render_ai_advisor_page_old(sheet_name, is_guest=False):
    st.title("🤖 AI Advisor & Scenario Planner")
    st.markdown("Stress-test your financial plan against different future scenarios.")

    if is_guest:
        st.info("This is a premium feature. In Guest Mode, you can see how it works with sample data.")

    # --- Scenario 1: Early Retirement ---
    with st.container(border=True):
        st.subheader("The Early Retirement Scenario")
        retire_years_earlier = st.slider("How many years earlier would you like to retire?", 1, 10, 5, disabled=is_guest)
        if st.button("Analyze Early Retirement", disabled=is_guest):
            with st.spinner("AI is analyzing the impact of retiring early..."):
                st.info(f"**AI Analysis:** Retiring {retire_years_earlier} years earlier is ambitious. To achieve this, you would need to increase your monthly investments by approximately **₹45,000** or secure an additional one-time corpus of **₹25,00,000**.")

    # --- Scenario 2: High Inflation ---
    with st.container(border=True):
        st.subheader("The High Inflation Scenario")
        inflation_increase = st.slider("Simulate an increase in the average inflation rate by (%):", 1.0, 5.0, 2.0, 0.5, disabled=is_guest)
        if st.button("Analyze High Inflation Impact", disabled=is_guest):
            with st.spinner("AI is analyzing the impact of higher inflation..."):
                st.warning(f"**AI Analysis:** A sustained {inflation_increase}% increase in inflation would cause your expenses to outpace your income by **Year 12**. Your plan is vulnerable to high inflation, and you should consider allocating more towards growth assets to counter this risk.")

def render_ai_advisor_page(sheet_name, is_guest=False):
    st.title("🤖 AI Advisor & Scenario Planner")
    st.markdown("Stress-test your financial plan against different future scenarios. This is a premium feature.")

    if is_guest:
        st.info("In Guest Mode, you can see the available scenarios. Create a free account and upgrade to Premium to run them on your own data.")
    
    try:
        # Configure the Gemini client with your secret key
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        # --- Scenario 1: Early Retirement ---
        with st.container(border=True):
            st.subheader("The Early Retirement Scenario")
            retire_years_earlier = st.slider("How many years earlier would you like to retire?", 1, 10, 5, disabled=is_guest)
            if st.button("Analyze Early Retirement", disabled=is_guest):
                with st.spinner("AI is analyzing the impact of retiring early..."):

                    #try:
                        # Configure the Gemini client with your secret key
                    #genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
                    #model = genai.GenerativeModel('gemini-1.5-flash')

                        # Create a simple text summary to send to the AI
                        initial_corpus = user_data.get("LocalStartingCorpus", {}).get("input", 0)
                        summary_text = (
                            f"A user in India has an initial investment corpus of {initial_corpus:,.0f} INR. and wants to retire {retire_years_earlier} years earlier)"
                            "Based on their plan, provide some brief, helpful financial advice in 2-3 sentences."
                        )
                
                        # Generate the advice using the Gemini API
                        response = model.generate_content(summary_text)
                        st.info(f"**AI Coach says:** {response.text}")
                    #except Exception as e:
                    #   st.error(f"Could not connect to the AI coach. Error: {e}")
                    #st.info(f"**AI Analysis:** Retiring {retire_years_earlier} years earlier is ambitious. To achieve this, you would need to increase your monthly investments by approximately **₹45,000** or secure an additional one-time corpus of **₹25,00,000**.")

        # --- Scenario 2: High Inflation ---
        with st.container(border=True):
            st.subheader("The High Inflation Scenario")
            inflation_increase = st.slider("Simulate an increase in the average inflation rate by (%):", 1.0, 5.0, 2.0, 0.5, disabled=is_guest)
            if st.button("Analyze High Inflation Impact", disabled=is_guest):
                with st.spinner("AI is analyzing the impact of higher inflation..."):
                        summary_text = (
                            f"Simulate an increase in the average inflation rate by (%):{inflation_increase})"
                            "Based on their plan, provide some brief, helpful financial advice in 2-3 sentences."
                        )
                
                        # Generate the advice using the Gemini API
                        response = model.generate_content(summary_text)
                        st.info(f"**AI Coach says:** {response.text}")
          
                    #st.warning(f"**AI Analysis:** A sustained {inflation_increase}% increase in inflation would cause your expenses to outpace your income by **Year 12**. Your plan is vulnerable to high inflation, and you should consider allocating more towards growth assets to counter this risk.")

        # --- Scenario 3: Market Downturn ---
        with st.container(border=True):
            st.subheader("The Market Downturn Scenario")
            market_drop = st.slider("Simulate a one-time market drop of (%):", 10, 50, 20, 5, disabled=is_guest)
            drop_year = st.slider("In which year should this drop occur?", 1, 10, 3, disabled=is_guest)
            if st.button("Analyze Market Downturn", disabled=is_guest):
                with st.spinner("AI is analyzing the impact of a market downturn..."):
                    summary_text = (
                            f"Simulate a one-time market drop of (%) {market_drop} in the year {drop_year}"
                        )
                        # Generate the advice using the Gemini API
                    response = model.generate_content(summary_text)
                    st.info(f"**AI Coach says:** {response.text}")
          
                    #st.success(f"**AI Analysis:** A {market_drop}% market correction in Year {drop_year} would be a significant setback. However, your plan is resilient enough to recover. Your final corpus would be approximately **15% lower**, but you would still remain financially secure throughout your projection.")
        
        # --- Scenario 4: Major Unplanned Expense ---
        with st.container(border=True):
            st.subheader("The Major Expense Scenario")
            unplanned_expense = st.number_input("Enter the amount for a large, unplanned expense (e.g., medical emergency):", min_value=100000, value=2000000, step=100000, disabled=is_guest)
            expense_year = st.slider("In which year should this expense occur?", 1, 20, 10, disabled=is_guest)
            if st.button("Analyze Unplanned Expense", disabled=is_guest):
                with st.spinner("AI is analyzing the impact of a major expense..."):
                    summary_text = (
                            f"Analyze unplanned expense of emergency in year {expense_year}"
                        )
                        # Generate the advice using the Gemini API
                    response = model.generate_content(summary_text)
                    st.info(f"**AI Coach says:** {response.text}")
          
                    #st.error(f"**AI Analysis:** An unplanned expense of **₹{unplanned_expense:,.0f}** in Year {expense_year} would significantly deplete your corpus. It is highly recommended to build a separate emergency fund or secure a dedicated insurance plan to mitigate this risk.")

        # --- Scenario 5: Longevity Risk ---
        with st.container(border=True):
            st.subheader("The Longevity Risk Scenario")
            st.markdown("What if you live longer than expected? Let's extend your plan.")
            extra_years = st.slider("How many extra years would you like to add to your plan?", 1, 15, 5, disabled=is_guest)
            if st.button("Analyze Longevity Risk", disabled=is_guest):
                with st.spinner("AI is analyzing the impact of a longer lifespan..."):
                    summary_text = (
                            f"Want to add extra {extra_years} to plan, analyze longetivity risk"
                        )
                        # Generate the advice using the Gemini API
                    response = model.generate_content(summary_text)
                    st.info(f"**AI Coach says:** {response.text}")
          
                    #st.info(f"**AI Analysis:** Extending your plan by {extra_years} years is a wise precaution. Your current plan would support you until age 85, but with this extension, your corpus would be depleted by age 88. You may need to consider a slightly lower annual withdrawal to ensure your funds last.")
    
    except Exception as e:
        st.error(f"Could not connect to the AI coach. Error: {e}")
# ############################################################################
#
# SECTION 3: NEW MAIN CONTROLLER / ROUTER
# This is the new logic that controls what the user sees.
#
# ############################################################################


# --- This is the main control flow for the entire application ---
if 'view' not in st.session_state:
    st.session_state.view = 'landing'

# --- FIX: The logout button is now part of the main controller ---
if st.session_state.get("authentication_status"):
        # If logged in, display the logout button in the sidebar.
    run_simulator(is_guest=False)
    # The logout() widget returns True when the button is clicked.
    authenticator.logout("Logout", "sidebar")
        # When logout is clicked, reset the view and rerun immediately
    #print("DEBUG: Re Running post logout 1") 
    #print("DEBUG: Re Running post logout 2")
    st.session_state.view = "landing"
    #print("DEBUG: Re Running post logout 3")
    #    st.rerun()
    
    # If the logout button was NOT clicked, run the main simulator.
    #run_simulator(is_guest=False)
    # If logged in, display the logout button in the sidebar.
    #authenticator.logout("Logout", "sidebar")
    # Now that the logout button is handled, run the main simulator.
    #run_simulator(is_guest=False)
    #run_simulator(is_guest=False)

elif st.session_state.view == "landing":
    st.title("Visualize Your Financial Future in Few Minutes")
    st.markdown("Our simulator helps you plan for inflation, analyze investments, and stress-test your financial future.")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.subheader("📊 Interactive Demo")
            st.markdown("Try a live demo with pre-filled sample data to see how the simulator works. No sign-up required.")
            if st.button("Try the Live Demo", key="demo_button"):
                st.session_state.view = "demo"
                st.rerun()

    with col2:
        with st.container(border=True):
            st.subheader("🚀 Get Started for Free")
            st.markdown("Create a free account to build your own personalized financial plan and save your progress.")
            if st.button("Create Free Account", key="register_button"):
                st.session_state.view = "register"
                st.session_state.auth_tab = "Register"
                st.rerun()

    with col3:
        with st.container(border=True):
            st.subheader("👤 Existing User Login")
            st.markdown("Already have an account? Log in to access your saved financial plans and premium features.")
            if st.button("Login", key="login_button"):
                st.session_state.view = "login"
                st.session_state.auth_tab = "Login"
                st.rerun()

elif st.session_state.view == 'demo':
    run_simulator(is_guest=True)

elif st.session_state.view == 'login' or st.session_state.view == 'register':
    
    try:
        if (st.session_state.view == 'login'):
            st.title("Log In to your account")
            #login_tab = st.tabs(["Login"])

            #with login_tab:
            authenticator.login(location='main')
            if st.session_state["authentication_status"] is False:
                st.error('Username/password is incorrect')
        else :
            st.title("Create an Account")
            #register_tab = st.tabs(["Register"])
            #with register_tab:
            email, username, name = authenticator.register_user(location='main')
            if email:
                st.success('User registered successfully! Please log in from the "Login" tab.')
                hashed_password = user_config['credentials']['usernames'][username]['password']
                db.collection('users').document(username).set({
                    "email": email, "name": name, 
                     "password_hash": hashed_password, "premium": False,
                    "onboarding_complete": False
                    })
                st.rerun()
    except Exception as e:
        st.error(e)
    
    if st.button("Back to Home"):
        st.session_state.view = 'landing'
        st.rerun()