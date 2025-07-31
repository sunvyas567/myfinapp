# app.py
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

st.set_page_config(page_title="Retirement Finance Planner", layout="wide")

STORAGE_FILE = "user_data.json"

def clean_formula(formula):
    # This function cleans up formula strings for safe evaluation
    if not isinstance(formula, str) or not formula.startswith("="):
        return formula
    formula = formula[1:].strip()
    formula = unicodedata.normalize("NFKC", formula).strip()
    # Standardize math operators
    formula = formula.replace("−", "-").replace("\u2212", "-")
    formula = formula.replace("“", "\"").replace("”", "\"")
    return formula

def load_user_data():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_user_data(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def eval_formula_with_debug_old(formula, data_context, field_name):
    expression = clean_formula(formula)
    
    def replacer(match):
        var_name = match.group(1)
        val = data_context.get(var_name, {}).get("input", 0)
        try:
            return str(float(val))
        except (ValueError, TypeError):
            return "0"
            
    # Replace all {variable} placeholders with their numeric values
    expression = re.sub(r"\{([^}]+)\}", replacer, expression)
    
    try:
        # Evaluate the final mathematical expression
        result = eval(expression, {"__builtins__": None, "math": math}, {})
        return result
    except Exception as e:
        st.error(f"❌ ERROR calculating `{field_name}`: {expression} -> {e}")
        return "Error"

def eval_formula_with_debug(formula, data_context, field_name):
    expression = clean_formula(formula)
    
    def replacer(match):
        var_name = match.group(1)
        # Use .get on the dictionary to avoid errors if a key is missing
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
        return 0 # Return 0 on error to prevent crashes
    
def render_text_sheet(sheet_name):
    st.header(sheet_name)
    if sheet_name == "AboutApp":
        st.markdown(ABOUT_APP_TEXT)
    elif sheet_name == "KnowledgebaseFAQ":
        df = pd.DataFrame(KNOWLEDGEBASE_FAQ_DATA)
        st.dataframe(df, use_container_width=True)

def render_input_form_old(config_data, sheet_name):
    st.header(sheet_name)
    df = pd.DataFrame(config_data)
    
    for _, row in df.iterrows():
        label = str(row["Field Description"])
        varname = str(row["Field Name"])
        default_val = row.get("Field Default Value", "")
        input_val_formula = row.get("Field Input", "")

        # Calculate default value if it's a formula
        if isinstance(default_val, str) and default_val.startswith("="):
            default_val = eval_formula_with_debug(default_val, user_data, varname)

        # Determine if the field is calculated or user-editable
        if isinstance(input_val_formula, str) and input_val_formula.startswith("="):
            calculated_val = eval_formula_with_debug(input_val_formula, user_data, varname)
            editable = False
        else:
            # Get saved user input, or fall back to the default value
            input_val = user_data.get(varname, {}).get("input", default_val)
            editable = True

        cols = st.columns([3, 2, 3])
        cols[0].markdown(f"**{label}**")
        
        # Display the default value, formatting for readability
        display_default = f"{default_val:,.2f}" if isinstance(default_val, (int, float)) else default_val
        cols[1].markdown(f"`Default: {display_default}`")

        if editable:
            # Ensure the input value is a float for the number_input widget
            try:
                current_value = float(input_val)
            except (ValueError, TypeError):
                current_value = 0.0
            user_input = cols[2].number_input(" ", value=current_value, key=varname, label_visibility="collapsed")
        else:
            # Display the calculated value
            display_calculated = f"{calculated_val:,.2f}" if isinstance(calculated_val, (int, float)) else calculated_val
            cols[2].markdown(f"`Calculated: {display_calculated}`")
            user_input = calculated_val
        
        # Store the current value (either from user or calculation)
        user_data[varname] = {"default": default_val, "input": user_input}
    
    # Plot charts for specific sheets
    if sheet_name == "ExpensesOneTime":
        plot_onetime_expenses(df, user_data)
def render_input_form_old2(config_data, sheet_name):
    st.header(f"📊 {sheet_name}")
    st.markdown("Enter your details below. Start with the basics and expand sections as needed.")

    # Helper function to generate a number input or display text
    def generate_field(varname, label, default_val, editable=True):
        if editable:
            try:
                current_value = float(user_data.get(varname, {}).get("input", default_val))
            except (ValueError, TypeError):
                current_value = float(default_val) if isinstance(default_val, (int, float)) else 0.0
            
            user_input = st.number_input(label, value=current_value, key=varname)
            user_data[varname] = {"default": default_val, "input": user_input}
        else:
            # Display non-editable default value
            display_value = f"{default_val:,.2f}" if isinstance(default_val, (int, float)) else default_val
            st.metric(label=label, value=display_value)
            # Ensure user_data is populated even if not edited
            if varname not in user_data:
                user_data[varname] = {"default": default_val, "input": default_val}

    # Create a dictionary from the config for easier lookup
    field_map = {item["Field Name"]: item for item in config_data}

    # --- Main Layout ---
    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.subheader("👤 Personal Info")
            generate_field("GLAge", "Current Age", field_map["GLAge"]["Field Default Value"])
            # Using a selectbox for Gender
            gender_options = ["Male", "Female"]
            current_gender = user_data.get("GLGender", {}).get("input", field_map["GLGender"]["Field Default Value"])
            user_gender = st.selectbox("Gender", options=gender_options, index=gender_options.index(current_gender) if current_gender in gender_options else 0, key="GLGender")
            user_data["GLGender"] = {"default": field_map["GLGender"]["Field Default Value"], "input": user_gender}
    
    with col2:
        with st.container(border=True):
            st.subheader("🗓️ Core Assumptions")
            generate_field("GLProjectionYears", "Projection Years", field_map["GLProjectionYears"]["Field Default Value"])
            generate_field("GLInflationRate", "Assumed Annual Inflation (%)", field_map["GLInflationRate"]["Field Default Value"])

    # --- Rates Section with Edit Toggle ---
    with st.container(border=True):
        st.subheader("📈 Interest Rates & Growth Assumptions")
        edit_rates = st.checkbox("Edit Default Rates and Assumptions")

        rate_cols = st.columns(4)
        rate_fields = ["GLSrCitizenFDRate", "GLNormalFDRate", "GLSCSSRate", "GLPOMISRate"]
        
        for i, field_name in enumerate(rate_fields):
            with rate_cols[i]:
                item = field_map[field_name]
                generate_field(item["Field Name"], f"{item['Field Description']} (%)", item["Field Default Value"], editable=edit_rates)

        st.markdown("---") # Visual separator
        swp_cols = st.columns(2)
        with swp_cols[0]:
            item = field_map["GLSWPGrowthRate"]
            generate_field(item["Field Name"], f"{item['Field Description']} (%)", item["Field Default Value"], editable=edit_rates)
        with swp_cols[1]:
            item = field_map["GLSWPMonthlyWithdrawal"]
            generate_field(item["Field Name"], item['Field Description'], item["Field Default Value"], editable=True) # Withdrawal is always editable

    # --- Advanced Settings in an Expander ---
    with st.expander("Advanced Settings: Initial Corpus, Other Income & Allocations"):
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.subheader("💰 Initial Corpus")
                corpus_fields = ["GLPFAccumulation", "GLPPFAccumulation", "GLSuperannuation"]
                for field_name in corpus_fields:
                    item = field_map[field_name]
                    generate_field(item["Field Name"], item["Field Description"], item["Field Default Value"])

        with c2:
            with st.container(border=True):
                st.subheader("🏠 Other Income Sources (Yearly)")
                other_income_fields = ["GLDividendIncome", "GLAgricultureIncome", "GLTradingIncome", "GLRealStateIncome", "GLConsultingIncome"]
                for field_name in other_income_fields:
                    item = field_map[field_name]
                    generate_field(item["Field Name"], item["Field Description"], item["Field Default Value"])

        st.markdown("---")
        c3, c4 = st.columns(2)
        with c3:
            with st.container(border=True):
                st.subheader("📊 Investment Allocation (%)")
                alloc_fields = ["GLSWPInvestmentPercentage", "GLNonSWPInvestmentPercentage", "GLNormalFDExcludingPOMISSCSS", "GLSrCitizenFDExcludingPOMISSCSS"]
                for field_name in alloc_fields:
                    item = field_map[field_name]
                    generate_field(item["Field Name"], item["Field Description"], item["Field Default Value"])
        
        with c4:
            with st.container(border=True):
                st.subheader("🏦 Other Allowances & Annuities")
                allowance_fields = ["GLPOMISSingle", "GLSCSSSingle", "GLCurrentMonthlyRental", "GLMaxMonthlyRental", "GLAnnuityExistingMonthly", "GLPensionEPS"]
                for field_name in allowance_fields:
                    item = field_map[field_name]
                    generate_field(item["Field Name"], item["Field Description"], item["Field Default Value"])

def render_input_form_old3(config_data, sheet_name):
    # This function now has a special, user-friendly layout for "BaseData" and "ExpensesOneTime",
    # and a default layout for any other potential sheets.

    if sheet_name == "BaseData":
        # ... (The code for the BaseData page remains the same as the previous version) ...
        # ... (I am omitting it here for brevity, no changes needed to this part) ...
        st.header("📊 Base Data & Assumptions")
        st.markdown("Enter your details below. Start with the basics and expand other sections as needed.")

        # Helper function to generate a field, making the code cleaner
        def generate_field(varname, label, default_val, editable=True, is_percent=False):
            # Display a metric for non-editable fields
            if not editable:
                display_value = f"{default_val:,.1f}%" if is_percent else f"{default_val:,.0f}"
                st.metric(label=label, value=display_value)
                if varname not in user_data: # Ensure data is saved even if not edited
                    user_data[varname] = {"default": default_val, "input": default_val}
            # Display a number input for editable fields
            else:
                try:
                    current_value = float(user_data.get(varname, {}).get("input", default_val))
                except (ValueError, TypeError):
                    current_value = float(default_val) if isinstance(default_val, (int, float)) else 0.0
                
                user_input = st.number_input(label, value=current_value, key=varname)
                user_data[varname] = {"default": default_val, "input": user_input}

        # Create a dictionary from the config for easier lookup
        field_map = {item["Field Name"]: item for item in config_data}

        # --- Main Layout ---
        col1, col2 = st.columns(2)

        with col1:
            with st.container(border=True):
                st.subheader("👤 Personal Info")
                generate_field("GLAge", "Current Age", field_map["GLAge"]["Field Default Value"])
                # Using a selectbox for Gender is more intuitive
                gender_options = ["Male", "Female"]
                current_gender = user_data.get("GLGender", {}).get("input", field_map["GLGender"]["Field Default Value"])
                user_gender = st.selectbox("Gender", options=gender_options, index=gender_options.index(current_gender) if current_gender in gender_options else 0, key="GLGender")
                user_data["GLGender"] = {"default": field_map["GLGender"]["Field Default Value"], "input": user_gender}
        
        with col2:
            with st.container(border=True):
                st.subheader("🗓️ Core Assumptions")
                generate_field("GLProjectionYears", "Projection Years", field_map["GLProjectionYears"]["Field Default Value"])
                generate_field("GLInflationRate", "Assumed Annual Inflation", field_map["GLInflationRate"]["Field Default Value"], is_percent=True)

        # --- Rates Section with Edit Toggle ---
        with st.container(border=True):
            st.subheader("📈 Interest Rates & Growth Assumptions")
            edit_rates = st.checkbox("Edit Default Rates and Assumptions")

            rate_cols = st.columns(4)
            rate_fields = ["GLSrCitizenFDRate", "GLNormalFDRate", "GLSCSSRate", "GLPOMISRate"]
            
            for i, field_name in enumerate(rate_fields):
                with rate_cols[i]:
                    item = field_map[field_name]
                    generate_field(item["Field Name"], item['Field Description'], item["Field Default Value"], editable=edit_rates, is_percent=True)

            st.markdown("---") # Visual separator
            swp_cols = st.columns(2)
            with swp_cols[0]:
                item = field_map["GLSWPGrowthRate"]
                generate_field(item["Field Name"], item['Field Description'], item["Field Default Value"], editable=edit_rates, is_percent=True)
            with swp_cols[1]:
                item = field_map["GLSWPMonthlyWithdrawal"]
                generate_field(item["Field Name"], item['Field Description'], item["Field Default Value"], editable=True)

        # --- Advanced Settings are hidden by default in an Expander ---
        with st.expander("⚙️ Advanced Settings: Initial Corpus, Other Income & Allocations"):
            c1, c2 = st.columns(2)
            with c1:
                with st.container(border=True):
                    st.subheader("💰 Initial Corpus")
                    corpus_fields = ["GLPFAccumulation", "GLPPFAccumulation", "GLSuperannuation"]
                    for field_name in corpus_fields:
                        item = field_map[field_name]
                        generate_field(item["Field Name"], item["Field Description"], item["Field Default Value"])

            with c2:
                with st.container(border=True):
                    st.subheader("🏠 Other Income Sources (Yearly)")
                    other_income_fields = ["GLDividendIncome", "GLAgricultureIncome", "GLTradingIncome", "GLRealStateIncome", "GLConsultingIncome"]
                    for field_name in other_income_fields:
                        item = field_map[field_name]
                        generate_field(item["Field Name"], item["Field Description"], item["Field Default Value"])
            
            st.markdown("---")
            c3, c4 = st.columns(2)
            with c3:
                with st.container(border=True):
                    st.subheader("📊 Investment Allocation")
                    alloc_fields = ["GLSWPInvestmentPercentage", "GLNonSWPInvestmentPercentage", "GLNormalFDExcludingPOMISSCSS", "GLSrCitizenFDExcludingPOMISSCSS"]
                    for field_name in alloc_fields:
                        item = field_map[field_name]
                        generate_field(item["Field Name"], item["Field Description"], item["Field Default Value"], is_percent=True)
            
            with c4:
                with st.container(border=True):
                    st.subheader("🏦 Other Allowances & Annuities")
                    allowance_fields = ["GLPOMISSingle", "GLSCSSSingle", "GLCurrentMonthlyRental", "GLMaxMonthlyRental", "GLAnnuityExistingMonthly", "GLPensionEPS"]
                    for field_name in allowance_fields:
                        item = field_map[field_name]
                        generate_field(item["Field Name"], item["Field Description"], item["Field Default Value"])

    elif sheet_name == "ExpensesOneTime":
        st.header("💸 One-Time Expenses")
        st.markdown("Enter any large, one-off expenses you anticipate for retirement.")
        
        field_map = {item["Field Name"]: item for item in config_data}

        # Helper to generate fields for this specific page
        def generate_expense_field(varname, editable=True):
            item = field_map[varname]
            label = item["Field Description"]
            default_val = item["Field Default Value"]
            
            if editable:
                current_value = float(user_data.get(varname, {}).get("input", default_val))
                user_input = st.number_input(label, value=current_value, key=varname)
                user_data[varname] = {"default": default_val, "input": user_input}
            else:
                # For calculated totals
                calculated_val = eval_formula_with_debug(item["Field Input"], user_data, varname)
                st.metric(label=label, value=f"{calculated_val:,.0f}")
                user_data[varname] = {"default": default_val, "input": calculated_val}
        
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.subheader("✅ Must-Have Expenses")
                must_fields = ["LocalKidsEducation", "LocalHouseRenovation", "LocalVehicleRenewal", "LocalJewelry", "LocalTravelForeign", "LocalOthers"]
                for field in must_fields:
                    generate_expense_field(field)
                st.markdown("---")
                generate_expense_field("LocalTotalOneTimeMust", editable=False)

        with col2:
            with st.container(border=True):
                st.subheader("🏖️ Optional / Delayed Expenses")
                delayed_fields = ["LocalMarriages", "LocalProperty"]
                for field in delayed_fields:
                    generate_expense_field(field)
                st.markdown("---")
                generate_expense_field("LocalTotalOneTimeDelayed", editable=False)
        
        st.markdown("##") # Adds some vertical space
        with st.container(border=True):
            generate_expense_field("GrandTotalOneTime", editable=False)
        
        # Plot chart at the end
        df = pd.DataFrame(config_data)
        plot_onetime_expenses(df, user_data)
        
    # This 'else' block handles any other sheet that might be added later
    else:
        st.header(sheet_name)
        # ... (The old, simple layout code remains here as a fallback) ...
        df = pd.DataFrame(config_data)
        for _, row in df.iterrows():
            label = str(row["Field Description"])
            varname = str(row["Field Name"])
            default_val = row.get("Field Default Value", "")
            input_val_formula = row.get("Field Input", "")

            if isinstance(default_val, str) and default_val.startswith("="):
                default_val = eval_formula_with_debug(default_val, user_data, varname)

            if isinstance(input_val_formula, str) and input_val_formula.startswith("="):
                calculated_val = eval_formula_with_debug(input_val_formula, user_data, varname)
                editable = False
            else:
                input_val = user_data.get(varname, {}).get("input", default_val)
                editable = True

            cols = st.columns([3, 2, 3])
            cols[0].markdown(f"**{label}**")
            display_default = f"{default_val:,.2f}" if isinstance(default_val, (int, float)) else default_val
            cols[1].markdown(f"`Default: {display_default}`")

            if editable:
                try:
                    current_value = float(input_val)
                except (ValueError, TypeError):
                    current_value = 0.0
                user_input = cols[2].number_input(" ", value=current_value, key=varname, label_visibility="collapsed")
            else:
                display_calculated = f"{calculated_val:,.2f}" if isinstance(calculated_val, (int, float)) else calculated_val
                cols[2].markdown(f"`Calculated: {display_calculated}`")
                user_input = calculated_val
            
            user_data[varname] = {"default": default_val, "input": user_input}


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

def render_expenses_recurring_old(config_data, sheet_name):
    st.header(sheet_name)
    df = pd.DataFrame(config_data)

    for _, row in df.iterrows():
        label, varname = str(row["Field Description"]), str(row["Field Name"])
        default_val, input_formula = row.get("Field Default Value", ""), row.get("Field Input", "")

        if isinstance(default_val, str) and default_val.startswith("="):
            default_val = eval_formula_with_debug(default_val, user_data, varname)

        if isinstance(input_formula, str) and input_formula.startswith("="):
            calculated_val = eval_formula_with_debug(input_formula, user_data, varname)
            editable = False
        else:
            input_val = user_data.get(varname, {}).get("input", default_val)
            editable = True

        cols = st.columns([3, 2, 2, 2, 2])
        cols[0].markdown(f"**{label}**")
        display_default = f"{default_val:,.2f}" if isinstance(default_val, (int, float)) else default_val
        cols[1].markdown(f"`Default: {display_default}`")

        if editable:
            try:
                current_value = float(input_val)
            except (ValueError, TypeError):
                current_value = 0.0
            user_input = cols[2].number_input(" ", value=current_value, key=varname, label_visibility="collapsed")
        else:
            display_calculated = f"{calculated_val:,.2f}" if isinstance(calculated_val, (int, float)) else calculated_val
            cols[2].markdown(f"`Calculated: {display_calculated}`")
            user_input = calculated_val
            
        # Calculate and display yearly values
        try:
            yearly = float(user_input) * 12
            yearly_rounded = round(yearly)
            cols[3].markdown(f"`Yearly: {yearly:,.2f}`")
            cols[4].markdown(f"`Rounded: {yearly_rounded:,.0f}`")
        except:
            cols[3].markdown("`Yearly: Error`")
            cols[4].markdown("`Rounded: Error`")
            
        user_data[varname] = {"default": default_val, "input": user_input}

    plot_recurring_expenses(df, user_data)

def render_expenses_recurring_old2(config_data, sheet_name):
    st.header("🗓️ Monthly Recurring Expenses")
    st.markdown("Enter your typical monthly spending. The tool will calculate the annual total and apply inflation.")

    field_map = {item["Field Name"]: item for item in config_data}

    # Define the groups and the fields that belong in them
    expense_groups = {
        "🏡 Home & Utilities": ["LocalGroceryVeg", "LocalWaterElectricity", "LocalHouseRepairs", "LocalMaidServices"],
        "🚗 Transport & Auto": ["LocalInsuranceVehicle", "LocalTransportFuel", "LocalVehicleMaintenance"],
        "🎉 Lifestyle & Entertainment": ["LocalEntertainment", "LocalInternetMobileTelecom", "LocalTVOTT", "LocalTravelLeisureInland", "LocalFunctionsEtc"],
        "💰 Taxes & Insurance": ["LocalPropertyTax", "LocalMedicalInsurance", "LocalMiscellaneousTax"],
        "✈️ Optional Expenses": ["LocalTravelLeisureForeignOpt", "LocalOthersOpt"]
    }

    # Helper function to generate an input row
    def generate_recurring_field(varname):
        item = field_map[varname]
        label = item["Field Description"].split(" (")[0] # Clean up label
        default_val = item["Field Default Value"]
        
        current_value = float(user_data.get(varname, {}).get("input", default_val))
        
        cols = st.columns([2,1])
        with cols[0]:
            user_input = st.number_input(label, value=current_value, key=varname)
        with cols[1]:
            st.metric(label="Yearly", value=f"{user_input * 12:,.0f}")
            
        user_data[varname] = {"default": default_val, "input": user_input}

    # Create the layout
    for group_title, fields in expense_groups.items():
        with st.container(border=True):
            st.subheader(group_title)
            # Create a two-column layout inside each container
            c1, c2 = st.columns(2)
            for i, field_name in enumerate(fields):
                if i % 2 == 0:
                    with c1:
                        generate_recurring_field(field_name)
                else:
                    with c2:
                        generate_recurring_field(field_name)

    # Display totals at the bottom
    st.markdown("---")
    st.subheader("Totals")
    total_cols = st.columns(2)
    with total_cols[0]:
        total_must_val = eval_formula_with_debug(field_map["GLTotalYearlyExpensesMust"]["Field Input"], user_data, "GLTotalYearlyExpensesMust")
        st.metric("Total Yearly (Must-Have)", f"{total_must_val * 12:,.0f}")
        user_data["GLTotalYearlyExpensesMust"]["input"] = total_must_val

    with total_cols[1]:
        total_opt_val = eval_formula_with_debug(field_map["GLTotalYearlyExpensesOptional"]["Field Input"], user_data, "GLTotalYearlyExpensesOptional")
        st.metric("Total Yearly (Optional)", f"{total_opt_val * 12:,.0f}")
        user_data["GLTotalYearlyExpensesOptional"]["input"] = total_opt_val

    # Plot chart at the end
    df = pd.DataFrame(config_data)
    plot_recurring_expenses(df, user_data)

def store_and_eval_all_variables_old():
    # This function iterates through the entire plan to calculate all values
    # It's crucial for dependent calculations to work correctly
    for item in INVESTMENT_PLAN_CONFIG:
        varname = item["Field Name"]
        formula = item["Field Value"]
        if isinstance(formula, str) and formula.startswith("="):
            value = eval_formula_with_debug(formula, user_data, varname)
            # Store the calculated value back into the context for the next calculation
            user_data[varname] = {"input": value}

 # Added sheet_name to accept the argument
    st.header(sheet_name)
    
    # First, run all calculations to populate user_data
    store_and_eval_all_variables()

    projection_years = int(user_data.get("GLProjectionYears", {}).get("input", 1))
    if projection_years <= 0:
        st.warning("Projection Years must be greater than 0. Please set it in BaseData.")
        return
        
    all_years_data = []
    
    # Set the initial corpus for Year 1
    swp_corpus = user_data.get("LocalSWPInvestAmount", {}).get("input", 0)

    for year in range(1, projection_years + 1):
        year_data = {"Year": year}
        
        # Update values that change annually (like inflation)
        user_data["CurrentYear"] = {"input": year}
        user_data["LocalSWPInvestAmount"]["input"] = swp_corpus # Use the corpus from the previous year's end
        
        # Re-evaluate all formulas for the current year context
        store_and_eval_all_variables()
        
        for item in config_data:
            varname = item["Field Name"]
            year_data[varname] = user_data.get(varname, {}).get("input", 0)

        all_years_data.append(year_data)
        
        # Update swp_corpus for the next year
        swp_corpus = user_data.get("LocalSWPBalancePostWithdrawal", {}).get("input", 0)
        
    df_out = pd.DataFrame(all_years_data)
    
    # Format the display DataFrame
    df_display = df_out.set_index("Year").T
    df_display.index.name = "Field Name"
    df_display.columns = [f"Year {i}" for i in range(1, projection_years + 1)]

    # Add the Field Description for clarity
    desc_map = {item["Field Name"]: item["Field Description"] for item in config_data}
    df_display.insert(0, "Field Description", df_display.index.map(desc_map))

    st.dataframe(df_display.style.format(precision=2, thousands=","))
    
    # --- CHARTING ---
    fields_to_plot = [
        "LocalSWPYearlyWithdrawal", "LocalSWPYearlyInterest", "GLSWPCorpusStatus",
        "LocalNormalFDYearlyIncome", "LocalSrFDYearlyIncomeFirst5", "LocalPOMISYearlyIncome", 
        "LocalSCSSYearlyIncome", "LocalSrFDYearlyIncomePast5", "LocalRentalIncome",
        "LocalDividentIncome", "LocalAnnuityExisting", "LocalAnnuityNew", "LocalPensionEPS",
        "LocalTradingIncome", "LocalRealStateIncome", "LocalConsultingIncome"
    ]
    
    plot_df = df_out[["Year"] + fields_to_plot]
    plot_df = plot_df.melt(id_vars="Year", var_name="Income Source", value_name="Amount")

    # Clean up names for the legend
    desc_map_plot = {name: desc.split(" - ")[0] for name, desc in desc_map.items()}
    plot_df["Income Source"] = plot_df["Income Source"].map(desc_map_plot)

    fig = px.bar(plot_df, x="Year", y="Amount", color="Income Source", title="Yearly Income Projection by Source")
    fig.update_layout(barmode="stack", xaxis_title="Year", yaxis_title="Amount (₹)")
    st.plotly_chart(fig, use_container_width=True)

def store_and_eval_all_variables_old2(calc_context):
    # This function iterates through the entire plan to calculate all values
    # It's crucial for dependent calculations to work correctly
    for item in INVESTMENT_PLAN_CONFIG:
        varname = item["Field Name"]
        formula = item["Field Value"]
        if isinstance(formula, str) and formula.startswith("="):
            value = eval_formula_with_debug(formula, calc_context, varname)
            # Store the calculated value back into the context for the next calculation
            if varname not in calc_context:
                calc_context[varname] = {}
            calc_context[varname]["input"] = value
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

def render_output_table_old(config_data, sheet_name):
    st.header(sheet_name)
    
    projection_years = int(user_data.get("GLProjectionYears", {}).get("input", 1))
    if projection_years <= 0:
        st.warning("Projection Years must be greater than 0. Please set it in BaseData.")
        return

    # Create a deep copy of user_data to use for calculations.
    base_context = json.loads(json.dumps(user_data))
    
    # --- Get all base values once ---
    inflation_rate = base_context.get("GLInflationRate", {}).get("input", 0) / 100.0
    base_monthly_rental = base_context.get("GLCurrentMonthlyRental", {}).get("input", 0)
    max_monthly_rental = base_context.get("GLMaxMonthlyRental", {}).get("input", 0)
    
    # Get base recurring expenses
    recurring_expense_varnames = [
        item['Field Name'] for item in RECURRING_EXPENSES_CONFIG 
        if not item['Field Name'].startswith('GLTotal')
    ]
    base_recurring_expenses = {
        var: base_context.get(var, {}).get('input', 0) 
        for var in recurring_expense_varnames
    }
    
    # Get FD & Investment base values
    store_and_eval_all_variables(base_context) # Initial run to get starting values
    fd_investment_fund = base_context.get("LocalFDInvestmentFund", {}).get("input", 0)
    scss_amount = base_context.get("LocalSCSSAmount", {}).get("input", 0)
    pomis_amount = base_context.get("LocalPOMISAmount", {}).get("input", 0)
    normal_fd_percent = base_context.get("LocalNormalFDPercent", {}).get("input", 0) / 100.0
    sr_citizen_fd_percent = 1.0 - normal_fd_percent
    
    normal_fd_rate = base_context.get("GLNormalFDRate", {}).get("input", 0) / 100.0
    sr_citizen_fd_rate = base_context.get("GLSrCitizenFDRate", {}).get("input", 0) / 100.0
    pomis_rate = base_context.get("GLPOMISRate", {}).get("input", 0) / 100.0
    scss_rate = base_context.get("GLSCSSRate", {}).get("input", 0) / 100.0
    
    all_years_data = []
    swp_corpus = base_context.get("LocalSWPInvestAmount", {}).get("input", 0)
    
    # --- Main yearly calculation loop ---
    for year in range(1, projection_years + 1):
        calc_context = json.loads(json.dumps(base_context))

        # 1. Set year-specific context
        calc_context["CurrentYear"] = {"input": year}
        calc_context["LocalSWPInvestAmount"]["input"] = swp_corpus

        # 2. Inflate recurring expenses and rental income
        for varname, base_value in base_recurring_expenses.items():
            calc_context[varname]["input"] = base_value * ((1 + inflation_rate) ** (year - 1))
        
        inflated_monthly_rental = base_monthly_rental * ((1 + inflation_rate) ** (year - 1))
        calc_context["LocalRentalIncome"]["input"] = min(inflated_monthly_rental, max_monthly_rental) * 12

        # 3. Manually calculate time-based FD, POMIS, and SCSS logic
        if year <= 5:
            # Principal for FDs is the total fund MINUS amounts locked in POMIS/SCSS
            fd_principal_for_year = fd_investment_fund - scss_amount - pomis_amount
            
            calc_context["LocalNormalFDYearlyIncome"]["input"] = fd_principal_for_year * normal_fd_percent * normal_fd_rate
            calc_context["LocalSrFDYearlyIncomeFirst5"]["input"] = fd_principal_for_year * sr_citizen_fd_percent * sr_citizen_fd_rate
            
            # These are active only for the first 5 years
            calc_context["LocalPOMISYearlyIncome"]["input"] = pomis_amount * pomis_rate
            calc_context["LocalSCSSYearlyIncome"]["input"] = scss_amount * scss_rate
            
            # This is zero for the first 5 years
            calc_context["LocalSrFDYearlyIncomePast5"]["input"] = 0
        else: # Year 6 and onwards
            # Principal from POMIS/SCSS is now reinvested into the main FD pool
            fd_principal_for_year = fd_investment_fund
            
            calc_context["LocalNormalFDYearlyIncome"]["input"] = fd_principal_for_year * normal_fd_percent * normal_fd_rate
            # Note: Using Sr Citizen Rate for this calculation, as is logical.
            calc_context["LocalSrFDYearlyIncomePast5"]["input"] = fd_principal_for_year * sr_citizen_fd_percent * sr_citizen_fd_rate

            # These are zero from year 6 onwards
            calc_context["LocalSrFDYearlyIncomeFirst5"]["input"] = 0
            calc_context["LocalPOMISYearlyIncome"]["input"] = 0
            calc_context["LocalSCSSYearlyIncome"]["input"] = 0

        # 4. Re-evaluate all other formulas (like totals) based on the manually set values
        store_and_eval_all_variables(calc_context)
        
        # 5. Store final calculated values for the year
        year_data = {"Year": year}
        for item in config_data:
            year_data[item["Field Name"]] = calc_context.get(item["Field Name"], {}).get("input", 0)
        all_years_data.append(year_data)
        
        # 6. Update the SWP corpus for the start of the next year
        swp_corpus = calc_context.get("LocalSWPBalancePostWithdrawal", {}).get("input", 0)
        
    # --- DataFrame Creation and Display ---
    if not all_years_data:
        st.warning("No data to display.")
        return

    df_out = pd.DataFrame(all_years_data)
    df_display = df_out.set_index("Year").T
    df_display.index.name = "Field Name"
    df_display.columns = [f"Year {i}" for i in range(1, projection_years + 1)]

    desc_map = {item["Field Name"]: item["Field Description"] for item in config_data}
    df_display.insert(0, "Field Description", df_display.index.map(desc_map))

    st.dataframe(df_display.style.format(precision=0, thousands=","))
    
    # --- CHARTING ---
    fields_to_plot = [
        "LocalNormalFDYearlyIncome", "LocalSrFDYearlyIncomeFirst5", 
        "LocalSrFDYearlyIncomePast5", "LocalPOMISYearlyIncome", "LocalSCSSYearlyIncome", 
        "LocalRentalIncome", "LocalDividentIncome", "LocalAnnuityExisting", "LocalAnnuityNew", 
        "LocalPensionEPS", "LocalTradingIncome", "LocalRealStateIncome", "LocalConsultingIncome",
        "GLSWPCorpusStatus" 
    ]
    
    plot_df = df_out[["Year"] + fields_to_plot]
    plot_df = plot_df.melt(id_vars="Year", var_name="Income/Gain Source", value_name="Amount")

    desc_map_plot = {name: desc.split(" - ")[0].split("(")[0] for name, desc in desc_map.items()}
    plot_df["Income/Gain Source"] = plot_df["Income/Gain Source"].map(desc_map_plot)

    fig = px.bar(plot_df, x="Year", y="Amount", color="Income/Gain Source", title="Yearly Income & SWP Gain/Loss Projection")
    fig.update_layout(barmode="relative", xaxis_title="Year", yaxis_title="Amount (₹)")
    st.plotly_chart(fig, use_container_width=True)

def render_output_table_old2(config_data, sheet_name):
    st.header(sheet_name)
    
    projection_years = int(user_data.get("GLProjectionYears", {}).get("input", 1))
    if projection_years <= 0:
        st.warning("Projection Years must be greater than 0. Please set it in BaseData.")
        return

    # --- Create a stable base context from user inputs ---
    base_context = json.loads(json.dumps(user_data))
    store_and_eval_all_variables(base_context) # Run once to resolve initial formulas
    
    # --- Get all base values needed for the loop ---
    inflation_rate = base_context.get("GLInflationRate", {}).get("input", 0) / 100.0
    base_monthly_rental = base_context.get("GLCurrentMonthlyRental", {}).get("input", 0)
    max_monthly_rental = base_context.get("GLMaxMonthlyRental", {}).get("input", 0)

    recurring_expense_varnames = [
        item['Field Name'] for item in RECURRING_EXPENSES_CONFIG 
        if not item['Field Name'].startswith('GLTotal')
    ]
    base_recurring_expenses = {
        var: base_context.get(var, {}).get('input', 0) for var in recurring_expense_varnames
    }
    
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
    # Initialize the SWP corpus for the start of Year 1
    swp_corpus = base_context.get("LocalSWPInvestAmount", {}).get("input", 0)

    # --- Main yearly calculation loop ---
    for year in range(1, projection_years + 1):
        # This context holds the final values for the current year
        year_context = base_context.copy()

        # --- Manually calculate all primary values for the current year ---

        # 1. SWP Calculations (this is now stateful and correct)
        yearly_interest = swp_corpus * ((1 + swp_monthly_rate) ** 12 - 1)
        yearly_withdrawal = swp_monthly_withdrawal * 12
        ending_balance = swp_corpus + yearly_interest - yearly_withdrawal
        
        year_context["LocalSWPInvestAmount"]["input"] = swp_corpus
        year_context["LocalSWPYearlyInterest"]["input"] = yearly_interest
        year_context["LocalSWPYearlyWithdrawal"]["input"] = yearly_withdrawal
        year_context["LocalSWPBalancePostWithdrawal"]["input"] = ending_balance
        year_context["GLSWPCorpusStatus"]["input"] = ending_balance - swp_corpus
        
        # 2. Inflate recurring expenses and rental income
        for varname, base_value in base_recurring_expenses.items():
            year_context[varname]["input"] = base_value * ((1 + inflation_rate) ** (year - 1))
        
        inflated_monthly_rental = base_monthly_rental * ((1 + inflation_rate) ** (year - 1))
        year_context["LocalRentalIncome"]["input"] = min(inflated_monthly_rental, max_monthly_rental) * 12

        # 3. Time-based FD, POMIS, and SCSS logic
        if year <= 5:
            fd_principal = fd_investment_fund - scss_amount - pomis_amount
            year_context["LocalNormalFDYearlyIncome"]["input"] = fd_principal * normal_fd_percent * normal_fd_rate
            year_context["LocalSrFDYearlyIncomeFirst5"]["input"] = fd_principal * sr_citizen_fd_percent * sr_citizen_fd_rate
            year_context["LocalPOMISYearlyIncome"]["input"] = pomis_amount * pomis_rate
            year_context["LocalSCSSYearlyIncome"]["input"] = scss_amount * scss_rate
            year_context["LocalSrFDYearlyIncomePast5"]["input"] = 0
        else: # Year 6 and onwards
            fd_principal = fd_investment_fund # Reinvested
            year_context["LocalNormalFDYearlyIncome"]["input"] = fd_principal * normal_fd_percent * normal_fd_rate
            year_context["LocalSrFDYearlyIncomePast5"]["input"] = fd_principal * sr_citizen_fd_percent * sr_citizen_fd_rate
            year_context["LocalSrFDYearlyIncomeFirst5"]["input"] = 0
            year_context["LocalPOMISYearlyIncome"]["input"] = 0
            year_context["LocalSCSSYearlyIncome"]["input"] = 0

        # 4. Now, evaluate only the TOTALS using the final values set above
        store_and_eval_all_variables(year_context)
        
        # 5. Store the results
        year_data = {"Year": year}
        for item in config_data:
            year_data[item["Field Name"]] = year_context.get(item["Field Name"], {}).get("input", 0)
        all_years_data.append(year_data)
        
        # 6. IMPORTANT: Update swp_corpus for the start of the NEXT year
        swp_corpus = ending_balance

    # --- DataFrame Creation and Display ---
    if not all_years_data:
        st.warning("No data to display.")
        return

    df_out = pd.DataFrame(all_years_data)
    df_display = df_out.set_index("Year").T
    df_display.index.name = "Field Name"
    df_display.columns = [f"Year {i}" for i in range(1, projection_years + 1)]

    desc_map = {item["Field Name"]: item["Field Description"] for item in config_data}
    df_display.insert(0, "Field Description", df_display.index.map(desc_map))
    
    st.dataframe(df_display.style.format(precision=0, thousands=","))
    
    # --- Charting ---
    # (Charting code remains the same as it reads from the final dataframe)
    fields_to_plot = [
        "LocalNormalFDYearlyIncome", "LocalSrFDYearlyIncomeFirst5", 
        "LocalSrFDYearlyIncomePast5", "LocalPOMISYearlyIncome", "LocalSCSSYearlyIncome", 
        "LocalRentalIncome", "LocalDividentIncome", "LocalAnnuityExisting", "LocalAnnuityNew", 
        "LocalPensionEPS", "LocalTradingIncome", "LocalRealStateIncome", "LocalConsultingIncome",
        "GLSWPCorpusStatus" 
    ]
    
    plot_df = df_out[["Year"] + fields_to_plot]
    plot_df = plot_df.melt(id_vars="Year", var_name="Income/Gain Source", value_name="Amount")

    desc_map_plot = {name: desc.split(" - ")[0].split("(")[0] for name, desc in desc_map.items()}
    plot_df["Income/Gain Source"] = plot_df["Income/Gain Source"].map(desc_map_plot)

    fig = px.bar(plot_df, x="Year", y="Amount", color="Income/Gain Source", title="Yearly Income & SWP Gain/Loss Projection")
    fig.update_layout(barmode="relative", xaxis_title="Year", yaxis_title="Amount (₹)")
    st.plotly_chart(fig, use_container_width=True)

def render_output_table_old3(config_data, sheet_name):
    st.header(sheet_name)
    
    projection_years = int(user_data.get("GLProjectionYears", {}).get("input", 1))
    if projection_years <= 0:
        st.warning("Projection Years must be greater than 0. Please set it in BaseData.")
        return

    # Create a stable base context from user inputs
    base_context = json.loads(json.dumps(user_data))
    store_and_eval_all_variables(base_context)
    
    # --- Get all base values needed for the loop ---
    inflation_rate = base_context.get("GLInflationRate", {}).get("input", 0) / 100.0
    base_monthly_rental = base_context.get("GLCurrentMonthlyRental", {}).get("input", 0)
    max_monthly_rental = base_context.get("GLMaxMonthlyRental", {}).get("input", 0)
    recurring_expense_varnames = [item['Field Name'] for item in RECURRING_EXPENSES_CONFIG if not item['Field Name'].startswith('GLTotal')]
    base_recurring_expenses = {var: base_context.get(var, {}).get('input', 0) for var in recurring_expense_varnames}
    
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
    # Initialize the SWP corpus for the start of Year 1
    swp_corpus = base_context.get("LocalSWPInvestAmount", {}).get("input", 0)

    # --- Main yearly calculation loop ---
    for year in range(1, projection_years + 1):
        calc_context = json.loads(json.dumps(base_context))

        # --- Manually calculate all primary values for the current year ---
        # The 'source': 'manual' flag protects these values from being overwritten.
        
        # 1. Stateful SWP Calculations
        yearly_interest = swp_corpus * ((1 + swp_monthly_rate) ** 12 - 1)
        yearly_withdrawal = swp_monthly_withdrawal * 12
        ending_balance = swp_corpus + yearly_interest - yearly_withdrawal
        
        calc_context["LocalSWPInvestAmount"] = {"input": swp_corpus, "source": "manual"}
        calc_context["LocalSWPYearlyInterest"] = {"input": yearly_interest, "source": "manual"}
        calc_context["LocalSWPYearlyWithdrawal"] = {"input": yearly_withdrawal, "source": "manual"}
        calc_context["LocalSWPBalancePostWithdrawal"] = {"input": ending_balance, "source": "manual"}
        calc_context["GLSWPCorpusStatus"] = {"input": ending_balance - swp_corpus, "source": "manual"}
        
        # 2. Inflated recurring expenses and rental income
        for varname, base_value in base_recurring_expenses.items():
            calc_context[varname] = {"input": base_value * ((1 + inflation_rate) ** (year - 1)), "source": "manual"}
        
        inflated_monthly_rental = base_monthly_rental * ((1 + inflation_rate) ** (year - 1))
        calc_context["LocalRentalIncome"] = {"input": min(inflated_monthly_rental, max_monthly_rental) * 12, "source": "manual"}

        # 3. Time-based FD, POMIS, and SCSS logic
        if year <= 5:
            fd_principal = fd_investment_fund - scss_amount - pomis_amount
            calc_context["LocalNormalFDYearlyIncome"] = {"input": fd_principal * normal_fd_percent * normal_fd_rate, "source": "manual"}
            calc_context["LocalSrFDYearlyIncomeFirst5"] = {"input": fd_principal * sr_citizen_fd_percent * sr_citizen_fd_rate, "source": "manual"}
            calc_context["LocalPOMISYearlyIncome"] = {"input": pomis_amount * pomis_rate, "source": "manual"}
            calc_context["LocalSCSSYearlyIncome"] = {"input": scss_amount * scss_rate, "source": "manual"}
            calc_context["LocalSrFDYearlyIncomePast5"] = {"input": 0, "source": "manual"}
        else: # Year 6 and onwards
            fd_principal = fd_investment_fund # Reinvested
            calc_context["LocalNormalFDYearlyIncome"] = {"input": fd_principal * normal_fd_percent * normal_fd_rate, "source": "manual"}
            calc_context["LocalSrFDYearlyIncomePast5"] = {"input": fd_principal * sr_citizen_fd_percent * sr_citizen_fd_rate, "source": "manual"}
            calc_context["LocalSrFDYearlyIncomeFirst5"] = {"input": 0, "source": "manual"}
            calc_context["LocalPOMISYearlyIncome"] = {"input": 0, "source": "manual"}
            calc_context["LocalSCSSYearlyIncome"] = {"input": 0, "source": "manual"}

        # 4. Evaluate only the remaining formulas (like totals)
        store_and_eval_all_variables(calc_context)
        
        # 5. Store results
        year_data = {"Year": year}
        for item in config_data:
            year_data[item["Field Name"]] = calc_context.get(item["Field Name"], {}).get("input", 0)
        all_years_data.append(year_data)
        
        # 6. Update swp_corpus for the NEXT year
        swp_corpus = ending_balance

    # --- DataFrame Creation and Display ---
    if not all_years_data:
        st.warning("No data to display.")
        return

    df_out = pd.DataFrame(all_years_data)
    df_display = df_out.set_index("Year").T
    df_display.index.name = "Field Name"
    df_display.columns = [f"Year {i}" for i in range(1, projection_years + 1)]
    desc_map = {item["Field Name"]: item["Field Description"] for item in config_data}
    df_display.insert(0, "Field Description", df_display.index.map(desc_map))
    st.dataframe(df_display.style.format(precision=0, thousands=","))
    
    # --- Charting ---
    fields_to_plot = [
        "LocalNormalFDYearlyIncome", "LocalSrFDYearlyIncomeFirst5", 
        "LocalSrFDYearlyIncomePast5", "LocalPOMISYearlyIncome", "LocalSCSSYearlyIncome", 
        "LocalRentalIncome", "LocalDividentIncome", "LocalAnnuityExisting", "LocalAnnuityNew", 
        "LocalPensionEPS", "LocalTradingIncome", "LocalRealStateIncome", "LocalConsultingIncome",
        "GLSWPCorpusStatus" 
    ]
    plot_df = df_out[["Year"] + fields_to_plot]
    plot_df = plot_df.melt(id_vars="Year", var_name="Income/Gain Source", value_name="Amount")
    desc_map_plot = {name: desc.split(" - ")[0].split("(")[0] for name, desc in desc_map.items()}
    plot_df["Income/Gain Source"] = plot_df["Income/Gain Source"].map(desc_map_plot)
    fig = px.bar(plot_df, x="Year", y="Amount", color="Income/Gain Source", title="Yearly Income & SWP Gain/Loss Projection")
    fig.update_layout(barmode="relative", xaxis_title="Year", yaxis_title="Amount (₹)")
    st.plotly_chart(fig, use_container_width=True)

def render_output_table_old4(config_data, sheet_name):
    st.header("📈 Investment Plan Projections")
    
    projection_years = int(user_data.get("GLProjectionYears", {}).get("input", 1))
    if projection_years <= 0:
        st.warning("Projection Years must be greater than 0. Please set it in BaseData.")
        return

    # --- (Calculation logic remains the same) ---
    base_context = json.loads(json.dumps(user_data))
    store_and_eval_all_variables(base_context)
    
    inflation_rate = base_context.get("GLInflationRate", {}).get("input", 0) / 100.0
    base_monthly_rental = base_context.get("GLCurrentMonthlyRental", {}).get("input", 0)
    max_monthly_rental = base_context.get("GLMaxMonthlyRental", {}).get("input", 0)
    recurring_expense_varnames = [item['Field Name'] for item in RECURRING_EXPENSES_CONFIG if not item['Field Name'].startswith('GLTotal')]
    base_recurring_expenses = {var: base_context.get(var, {}).get('input', 0) for var in recurring_expense_varnames}
    
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
        
        for varname, base_value in base_recurring_expenses.items():
            calc_context[varname] = {"input": base_value * ((1 + inflation_rate) ** (year - 1)), "source": "manual"}
        
        inflated_monthly_rental = base_monthly_rental * ((1 + inflation_rate) ** (year - 1))
        calc_context["LocalRentalIncome"] = {"input": min(inflated_monthly_rental, max_monthly_rental) * 12, "source": "manual"}

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
        
        year_data = {"Year": year}
        for item in config_data:
            year_data[item["Field Name"]] = calc_context.get(item["Field Name"], {}).get("input", 0)
        all_years_data.append(year_data)
        
        swp_corpus = ending_balance
    
    # --- UI and DataFrame Manipulation Starts Here ---
    if not all_years_data:
        st.warning("No data to display.")
        return
        
    # --- 1. Define the new field order and split static/dynamic rows ---
    all_fields_ordered = [item['Field Name'] for item in config_data]
    
    # Move 'investmentatrisk' to its new position
    all_fields_ordered.remove('LocalSWPInvestAmount')
    pomis_index = all_fields_ordered.index('LocalPOMISAmount')
    all_fields_ordered.insert(pomis_index + 1, 'LocalSWPInvestAmount')

    split_index = all_fields_ordered.index('LocalSWPInvestAmount')
    static_fields = all_fields_ordered[:split_index]
    dynamic_fields = all_fields_ordered[split_index:]

    desc_map = {item["Field Name"]: item["Field Description"] for item in config_data}
    year_1_data = all_years_data[0] # Get the first year's data for the static box

    # --- 2. Render the Static Box with Year 1 values ---
    st.subheader("Initial Investment Setup (Calculated for Year 1)")
    with st.container(border=True):
        cols = st.columns(3)
        col_idx = 0
        for field_name in static_fields:
            if field_name not in year_1_data: continue
            with cols[col_idx]:
                label = desc_map.get(field_name, field_name).split("(")[0] # Clean up label
                value = year_1_data[field_name]
                st.metric(label=label, value=f"{value:,.0f}")
            col_idx = (col_idx + 1) % len(cols)

    # --- 3. Create, filter, and display the main dynamic table ---
    st.subheader("Year-over-Year Financial Projections")
    df_out = pd.DataFrame(all_years_data)
    
    # Set the index to Field Name for easier filtering and ordering
    df_for_display = df_out.drop(columns=['Year']).T
    df_for_display.columns = [f"Year {y}" for y in range(1, projection_years + 1)]

    # Filter and reorder the DataFrame to match the dynamic list
    df_dynamic_display = df_for_display[df_for_display.index.isin(dynamic_fields)]
    df_dynamic_display = df_dynamic_display.reindex(dynamic_fields)

    # Add the description column for clarity
    df_dynamic_display.insert(0, "Field Description", df_dynamic_display.index.map(desc_map))

    st.dataframe(df_dynamic_display.style.format(precision=0, thousands=","))
    
    # --- Charting (no changes needed here) ---
    fields_to_plot = [
        "LocalNormalFDYearlyIncome", "LocalSrFDYearlyIncomeFirst5", 
        "LocalSrFDYearlyIncomePast5", "LocalPOMISYearlyIncome", "LocalSCSSYearlyIncome", 
        "LocalRentalIncome", "LocalDividentIncome", "LocalAnnuityExisting", "LocalAnnuityNew", 
        "LocalPensionEPS", "LocalTradingIncome", "LocalRealStateIncome", "LocalConsultingIncome",
        "GLSWPCorpusStatus" 
    ]
    
    plot_df = df_out[["Year"] + fields_to_plot]
    plot_df = plot_df.melt(id_vars="Year", var_name="Income/Gain Source", value_name="Amount")

    desc_map_plot = {name: desc.split(" - ")[0].split("(")[0] for name, desc in desc_map.items()}
    plot_df["Income/Gain Source"] = plot_df["Income/Gain Source"].map(desc_map_plot)

    fig = px.bar(plot_df, x="Year", y="Amount", color="Income/Gain Source", title="Yearly Income & SWP Gain/Loss Projection")
    fig.update_layout(barmode="relative", xaxis_title="Year", yaxis_title="Amount (₹)")
    st.plotly_chart(fig, use_container_width=True)

def render_input_form(config_data, sheet_name):
    # This function now has a special, user-friendly layout for "BaseData" and "ExpensesOneTime",
    # and a default layout for any other potential sheets.
    
    # Define icons for the fields
    FIELD_ICONS = {
        "LocalKidsEducation": "🎓", "LocalHouseRenovation": "🏡", "LocalVehicleRenewal": "🚗",
        "LocalJewelry": "💎", "LocalTravelForeign": "✈️", "LocalOthers": "🛍️",
        "LocalMarriages": "💍", "LocalProperty": "🏘️",
        "LocalTotalOneTimeMust": "✅", "LocalTotalOneTimeDelayed": "🏖️", "GrandTotalOneTime": "∑"
    }

    if sheet_name == "BaseData":
        # ... (The code for the BaseData page remains the same as the previous version) ...
        # ... (I am omitting it here for brevity, no changes needed to this part) ...
        st.header("📊 Base Data & Assumptions")
        st.markdown("Enter your details below. Start with the basics and expand other sections as needed.")

        # Helper function to generate a field, making the code cleaner
        def generate_field(varname, label, default_val, editable=True, is_percent=False):
            # Display a metric for non-editable fields
            if not editable:
                display_value = f"{default_val:,.1f}%" if is_percent else f"{default_val:,.0f}"
                st.metric(label=label, value=display_value)
                if varname not in user_data: # Ensure data is saved even if not edited
                    user_data[varname] = {"default": default_val, "input": default_val}
            # Display a number input for editable fields
            else:
                try:
                    current_value = float(user_data.get(varname, {}).get("input", default_val))
                except (ValueError, TypeError):
                    current_value = float(default_val) if isinstance(default_val, (int, float)) else 0.0
                
                user_input = st.number_input(label, value=current_value, key=varname)
                user_data[varname] = {"default": default_val, "input": user_input}

        # Create a dictionary from the config for easier lookup
        field_map = {item["Field Name"]: item for item in config_data}

        # --- Main Layout ---
        col1, col2 = st.columns(2)

        with col1:
            with st.container(border=True):
                st.subheader("👤 Personal Info")
                generate_field("GLAge", "Current Age", field_map["GLAge"]["Field Default Value"])
                # Using a selectbox for Gender is more intuitive
                gender_options = ["Male", "Female"]
                current_gender = user_data.get("GLGender", {}).get("input", field_map["GLGender"]["Field Default Value"])
                user_gender = st.selectbox("Gender", options=gender_options, index=gender_options.index(current_gender) if current_gender in gender_options else 0, key="GLGender")
                user_data["GLGender"] = {"default": field_map["GLGender"]["Field Default Value"], "input": user_gender}
        
        with col2:
            with st.container(border=True):
                st.subheader("🗓️ Core Assumptions")
                generate_field("GLProjectionYears", "Projection Years", field_map["GLProjectionYears"]["Field Default Value"])
                generate_field("GLInflationRate", "Assumed Annual Inflation", field_map["GLInflationRate"]["Field Default Value"], is_percent=True)

        # --- Rates Section with Edit Toggle ---
        with st.container(border=True):
            st.subheader("📈 Interest Rates & Growth Assumptions")
            edit_rates = st.checkbox("Edit Default Rates and Assumptions")

            rate_cols = st.columns(4)
            rate_fields = ["GLSrCitizenFDRate", "GLNormalFDRate", "GLSCSSRate", "GLPOMISRate"]
            
            for i, field_name in enumerate(rate_fields):
                with rate_cols[i]:
                    item = field_map[field_name]
                    generate_field(item["Field Name"], item['Field Description'], item["Field Default Value"], editable=edit_rates, is_percent=True)

            st.markdown("---") # Visual separator
            swp_cols = st.columns(2)
            with swp_cols[0]:
                item = field_map["GLSWPGrowthRate"]
                generate_field(item["Field Name"], item['Field Description'], item["Field Default Value"], editable=edit_rates, is_percent=True)
            with swp_cols[1]:
                item = field_map["GLSWPMonthlyWithdrawal"]
                generate_field(item["Field Name"], item['Field Description'], item["Field Default Value"], editable=True)

        # --- Advanced Settings are hidden by default in an Expander ---
        with st.expander("⚙️ Advanced Settings: Initial Corpus, Other Income & Allocations"):
            c1, c2 = st.columns(2)
            with c1:
                with st.container(border=True):
                    st.subheader("💰 Initial Corpus")
                    corpus_fields = ["GLPFAccumulation", "GLPPFAccumulation", "GLSuperannuation"]
                    for field_name in corpus_fields:
                        item = field_map[field_name]
                        generate_field(item["Field Name"], item["Field Description"], item["Field Default Value"])

            with c2:
                with st.container(border=True):
                    st.subheader("🏠 Other Income Sources (Yearly)")
                    other_income_fields = ["GLDividendIncome", "GLAgricultureIncome", "GLTradingIncome", "GLRealStateIncome", "GLConsultingIncome"]
                    for field_name in other_income_fields:
                        item = field_map[field_name]
                        generate_field(item["Field Name"], item["Field Description"], item["Field Default Value"])
            
            st.markdown("---")
            c3, c4 = st.columns(2)
            with c3:
                with st.container(border=True):
                    st.subheader("📊 Investment Allocation")
                    alloc_fields = ["GLSWPInvestmentPercentage", "GLNonSWPInvestmentPercentage", "GLNormalFDExcludingPOMISSCSS", "GLSrCitizenFDExcludingPOMISSCSS"]
                    for field_name in alloc_fields:
                        item = field_map[field_name]
                        generate_field(item["Field Name"], item["Field Description"], item["Field Default Value"], is_percent=True)
            
            with c4:
                with st.container(border=True):
                    st.subheader("🏦 Other Allowances & Annuities")
                    allowance_fields = ["GLPOMISSingle", "GLSCSSSingle", "GLCurrentMonthlyRental", "GLMaxMonthlyRental", "GLAnnuityExistingMonthly", "GLPensionEPS"]
                    for field_name in allowance_fields:
                        item = field_map[field_name]
                        generate_field(item["Field Name"], item["Field Description"], item["Field Default Value"])

    elif sheet_name == "ExpensesOneTime":
        st.header("💸 One-Time Expenses")
        st.markdown("Enter any large, one-off expenses you anticipate for retirement.")
        
        field_map = {item["Field Name"]: item for item in config_data}

        # Helper to generate fields for this specific page
        def generate_expense_field(varname, editable=True):
            item = field_map[varname]
            icon = FIELD_ICONS.get(varname, "💰") # Get icon, with a default
            label = f"{icon} {item['Field Description']}" # Add icon to the label
            default_val = item["Field Default Value"]
            
            if editable:
                current_value = float(user_data.get(varname, {}).get("input", default_val))
                user_input = st.number_input(label, value=current_value, key=varname)
                user_data[varname] = {"default": default_val, "input": user_input}
            else:
                # For calculated totals
                calculated_val = eval_formula_with_debug(item["Field Input"], user_data, varname)
                st.metric(label=label, value=f"{calculated_val:,.0f}")
                user_data[varname] = {"default": default_val, "input": calculated_val}
        
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.subheader("✅ Must-Have Expenses")
                must_fields = ["LocalKidsEducation", "LocalHouseRenovation", "LocalVehicleRenewal", "LocalJewelry", "LocalTravelForeign", "LocalOthers"]
                for field in must_fields:
                    generate_expense_field(field)
                st.markdown("---")
                generate_expense_field("LocalTotalOneTimeMust", editable=False)

        with col2:
            with st.container(border=True):
                st.subheader("🏖️ Optional / Delayed Expenses")
                delayed_fields = ["LocalMarriages", "LocalProperty"]
                for field in delayed_fields:
                    generate_expense_field(field)
                st.markdown("---")
                generate_expense_field("LocalTotalOneTimeDelayed", editable=False)
        
        st.markdown("##") # Adds some vertical space
        with st.container(border=True):
            generate_expense_field("GrandTotalOneTime", editable=False)
        
        # Plot chart at the end
        df = pd.DataFrame(config_data)
        plot_onetime_expenses(df, user_data)
        
    # This 'else' block handles any other sheet that might be added later
    else:
        st.header(sheet_name)
        df = pd.DataFrame(config_data)
        for _, row in df.iterrows():
            label = str(row["Field Description"])
            varname = str(row["Field Name"])
            default_val = row.get("Field Default Value", "")
            input_val_formula = row.get("Field Input", "")

            if isinstance(default_val, str) and default_val.startswith("="):
                default_val = eval_formula_with_debug(default_val, user_data, varname)

            if isinstance(input_val_formula, str) and input_val_formula.startswith("="):
                calculated_val = eval_formula_with_debug(input_val_formula, user_data, varname)
                editable = False
            else:
                input_val = user_data.get(varname, {}).get("input", default_val)
                editable = True

            cols = st.columns([3, 2, 3])
            cols[0].markdown(f"**{label}**")
            display_default = f"{default_val:,.2f}" if isinstance(default_val, (int, float)) else default_val
            cols[1].markdown(f"`Default: {display_default}`")

            if editable:
                try:
                    current_value = float(input_val)
                except (ValueError, TypeError):
                    current_value = 0.0
                user_input = cols[2].number_input(" ", value=current_value, key=varname, label_visibility="collapsed")
            else:
                display_calculated = f"{calculated_val:,.2f}" if isinstance(calculated_val, (int, float)) else calculated_val
                cols[2].markdown(f"`Calculated: {display_calculated}`")
                user_input = calculated_val
            
            user_data[varname] = {"default": default_val, "input": user_input}

def render_expenses_recurring(config_data, sheet_name):
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
            user_input = st.number_input(label, value=current_value, key=varname)
        with cols[1]:
            st.metric(label="Yearly", value=f"{user_input * 12:,.0f}")
            
        user_data[varname] = {"default": default_val, "input": user_input}

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
        user_data["GLTotalYearlyExpensesMust"]["input"] = total_must_val

    with total_cols[1]:
        total_opt_val = eval_formula_with_debug(field_map["GLTotalYearlyExpensesOptional"]["Field Input"], user_data, "GLTotalYearlyExpensesOptional")
        st.metric("Total Yearly (Optional)", f"{total_opt_val * 12:,.0f}")
        user_data["GLTotalYearlyExpensesOptional"]["input"] = total_opt_val

    df = pd.DataFrame(config_data)
    plot_recurring_expenses(df, user_data)

def render_output_table_old5(config_data, sheet_name):
    st.header("📈 Investment Plan Projections")
    
    projection_years = int(user_data.get("GLProjectionYears", {}).get("input", 1))
    if projection_years <= 0:
        st.warning("Projection Years must be greater than 0. Please set it in BaseData.")
        return

    # --- (Calculation logic remains the same) ---
    base_context = json.loads(json.dumps(user_data))
    store_and_eval_all_variables(base_context)
    
    inflation_rate = base_context.get("GLInflationRate", {}).get("input", 0) / 100.0
    base_monthly_rental = base_context.get("GLCurrentMonthlyRental", {}).get("input", 0)
    max_monthly_rental = base_context.get("GLMaxMonthlyRental", {}).get("input", 0)
    recurring_expense_varnames = [item['Field Name'] for item in RECURRING_EXPENSES_CONFIG if not item['Field Name'].startswith('GLTotal')]
    base_recurring_expenses = {var: base_context.get(var, {}).get('input', 0) for var in recurring_expense_varnames}
    
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
        
        for varname, base_value in base_recurring_expenses.items():
            calc_context[varname] = {"input": base_value * ((1 + inflation_rate) ** (year - 1)), "source": "manual"}
        
        inflated_monthly_rental = base_monthly_rental * ((1 + inflation_rate) ** (year - 1))
        calc_context["LocalRentalIncome"] = {"input": min(inflated_monthly_rental, max_monthly_rental) * 12, "source": "manual"}

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
        
        year_data = {"Year": year}
        for item in config_data:
            year_data[item["Field Name"]] = calc_context.get(item["Field Name"], {}).get("input", 0)
        all_years_data.append(year_data)
        
        swp_corpus = ending_balance

    if not all_years_data:
        st.warning("No data to display.")
        return
        
    all_fields_ordered = [item['Field Name'] for item in config_data]
    
    all_fields_ordered.remove('LocalSWPInvestAmount')
    pomis_index = all_fields_ordered.index('LocalPOMISAmount')
    all_fields_ordered.insert(pomis_index + 1, 'LocalSWPInvestAmount')

    split_index = all_fields_ordered.index('LocalSWPInvestAmount')
    static_fields = all_fields_ordered[:split_index]
    dynamic_fields = all_fields_ordered[split_index:]

    desc_map = {item["Field Name"]: item["Field Description"] for item in config_data}
    year_1_data = all_years_data[0]

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
    df_out = pd.DataFrame(all_years_data)
    
    df_for_display = df_out.drop(columns=['Year']).T
    df_for_display.columns = [f"Year {y}" for y in range(1, projection_years + 1)]

    df_dynamic_display = df_for_display[df_for_display.index.isin(dynamic_fields)]
    df_dynamic_display = df_dynamic_display.reindex(dynamic_fields)

    df_dynamic_display.insert(0, "Field Description", df_dynamic_display.index.map(desc_map))

    # --- Hide the 'Field Name' index column ---
    final_table = df_dynamic_display.reset_index(drop=True)
    st.dataframe(
        final_table.style.format(precision=0, thousands=","),
        hide_index=True
    )
    
    fields_to_plot = [
        "LocalNormalFDYearlyIncome", "LocalSrFDYearlyIncomeFirst5", 
        "LocalSrFDYearlyIncomePast5", "LocalPOMISYearlyIncome", "LocalSCSSYearlyIncome", 
        "LocalRentalIncome", "LocalDividentIncome", "LocalAnnuityExisting", "LocalAnnuityNew", 
        "LocalPensionEPS", "LocalTradingIncome", "LocalRealStateIncome", "LocalConsultingIncome",
        "GLSWPCorpusStatus" 
    ]
    
    plot_df = df_out[["Year"] + fields_to_plot]
    plot_df = plot_df.melt(id_vars="Year", var_name="Income/Gain Source", value_name="Amount")

    desc_map_plot = {name: desc.split(" - ")[0].split("(")[0] for name, desc in desc_map.items()}
    plot_df["Income/Gain Source"] = plot_df["Income/Gain Source"].map(desc_map_plot)

    fig = px.bar(plot_df, x="Year", y="Amount", color="Income/Gain Source", title="Yearly Income & SWP Gain/Loss Projection")
    fig.update_layout(barmode="relative", xaxis_title="Year", yaxis_title="Amount (₹)")
    st.plotly_chart(fig, use_container_width=True)

# Add this function to your app.py
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

# Add this new function to your app.py
# This function centralizes the core calculation logic.
def calculate_projections_old():
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
        
        for varname, base_value in base_recurring_expenses.items():
            calc_context[varname] = {"input": base_value * ((1 + inflation_rate) ** (year - 1)), "source": "manual"}
        
        inflated_monthly_rental = base_monthly_rental * ((1 + inflation_rate) ** (year - 1))
        calc_context["LocalRentalIncome"] = {"input": min(inflated_monthly_rental, max_monthly_rental) * 12, "source": "manual"}

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
        
        year_data = {"Year": year}
        for item in INVESTMENT_PLAN_CONFIG:
            year_data[item["Field Name"]] = calc_context.get(item["Field Name"], {}).get("input", 0)
        all_years_data.append(year_data)
        
        swp_corpus = ending_balance
    
    df_out = pd.DataFrame(all_years_data) if all_years_data else pd.DataFrame()
    return df_out, base_context

# In app.py, replace the existing calculate_projections function with this one.

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

# Add this new function to your app.py
from fpdf import FPDF
import io

def render_summary_page_old(config_data):
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
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, 'Financial Summary Report', 0, 1, 'C')
            
            # Key Metrics
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, 'Key Initial Figures', 0, 1, 'L')
            pdf.set_font("Arial", '', 10)
            for key, value in summary_data["key_metrics"].items():
                pdf.cell(0, 8, f"- {key}: {value:,.0f}", 0, 1)
            pdf.ln(10)

            # Income vs Expense Chart
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, 'Income vs. Expenses Over Time', 0, 1, 'L')
            pdf.image(io.BytesIO(summary_data["income_expense_chart"]), w=190)
            pdf.ln(10)
            
            # Display a small part of the projection table
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, 'Yearly Projection Data (Sample)', 0, 1, 'L')
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(20, 8, 'Year', 1)
            pdf.cell(50, 8, 'Total Income', 1)
            pdf.cell(50, 8, 'Total Expenses', 1)
            pdf.cell(50, 8, 'Ending SWP Corpus', 1)
            pdf.ln()
            
            pdf.set_font("Arial", '', 8)
            for _, row in df_chart.head(15).iterrows(): # Show first 15 years
                pdf.cell(20, 8, str(int(row['Year'])), 1)
                pdf.cell(50, 8, f"{row['Total Income']:,.0f}", 1)
                pdf.cell(50, 8, f"{row['Total Expenses']:,.0f}", 1)
                # Get the ending corpus for that year
                ending_corpus = df_projections.loc[df_projections['Year'] == row['Year'], 'LocalSWPBalancePostWithdrawal'].iloc[0]
                pdf.cell(50, 8, f"{ending_corpus:,.0f}", 1)
                pdf.ln()

            pdf_output = pdf.output(dest='S').encode('latin-1')
            
            st.download_button(
                label="📥 Download as PDF",
                data=pdf_output,
                file_name="financial_summary.pdf",
                mime="application/pdf"
            )
# In app.py, replace the existing render_summary_page function with this one.

def render_summary_page_old2(config_data):
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
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, 'Financial Summary Report', 0, 1, 'C')
            
            # Key Metrics
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, 'Key Initial Figures', 0, 1, 'L')
            pdf.set_font("Arial", '', 10)
            for key, value in summary_data["key_metrics"].items():
                pdf.cell(0, 8, f"- {key}: {value:,.0f}", 0, 1)
            pdf.ln(10)

            # Income vs Expense Chart
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, 'Income vs. Expenses Over Time', 0, 1, 'L')
            pdf.image(io.BytesIO(summary_data["income_expense_chart"]), w=190)
            pdf.ln(10)
            
            # Display a small part of the projection table
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, 'Yearly Projection Data (Sample)', 0, 1, 'L')
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(20, 8, 'Year', 1)
            pdf.cell(50, 8, 'Total Income', 1)
            pdf.cell(50, 8, 'Total Expenses', 1)
            pdf.cell(50, 8, 'Ending SWP Corpus', 1)
            pdf.ln()
            
            pdf.set_font("Arial", '', 8)
            for _, row in df_chart.head(15).iterrows(): # Show first 15 years
                pdf.cell(20, 8, str(int(row['Year'])), 1)
                pdf.cell(50, 8, f"{row['Total Income']:,.0f}", 1)
                pdf.cell(50, 8, f"{row['Total Expenses']:,.0f}", 1)
                ending_corpus = df_projections.loc[df_projections['Year'] == row['Year'], 'LocalSWPBalancePostWithdrawal'].iloc[0]
                pdf.cell(50, 8, f"{ending_corpus:,.0f}", 1)
                pdf.ln()

            # ** THE FIX: Removed the unnecessary .encode() call **
            pdf_output = pdf.output()
            
            st.download_button(
                label="📥 Download as PDF",
                data=pdf_output,
                file_name="financial_summary.pdf",
                mime="application/pdf"
            )

# In app.py, replace the existing render_summary_page function with this one.

def render_summary_page(config_data):
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
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, 'Financial Summary Report', 0, 1, 'C')
            
            # Key Metrics
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, 'Key Initial Figures', 0, 1, 'L')
            pdf.set_font("Arial", '', 10)
            for key, value in summary_data["key_metrics"].items():
                pdf.cell(0, 8, f"- {key}: {value:,.0f}", 0, 1)
            pdf.ln(10)

            # Income vs Expense Chart
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, 'Income vs. Expenses Over Time', 0, 1, 'L')
            pdf.image(io.BytesIO(summary_data["income_expense_chart"]), w=190)
            pdf.ln(10)
            
            # Display a small part of the projection table
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, 'Yearly Projection Data (Sample)', 0, 1, 'L')
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(20, 8, 'Year', 1)
            pdf.cell(50, 8, 'Total Income', 1)
            pdf.cell(50, 8, 'Total Expenses', 1)
            pdf.cell(50, 8, 'Ending SWP Corpus', 1)
            pdf.ln()
            
            pdf.set_font("Arial", '', 8)
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
                file_name="financial_summary.pdf",
                mime="application/pdf"
            )

# REPLACE your existing render_output_table function with this one
# It now calls the central calculation function.
def render_output_table(config_data, sheet_name):
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

# REPLACE your existing main function with this one
# It now includes the new "Summary" page in the correct order.
def main():
    inject_pwa_script()
    global user_data
    user_data = load_user_data()

    with st.sidebar:
        st.title("📋 Navigation")
        # Define the order and configuration for each page
        pages = {
            "AboutApp": {"config": None, "render_func": render_text_sheet},
            "BaseData": {"config": BASE_DATA_CONFIG, "render_func": render_input_form},
            "ExpensesOneTime": {"config": ONETIME_EXPENSES_CONFIG, "render_func": render_input_form},
            "ExpensesRecurring": {"config": RECURRING_EXPENSES_CONFIG, "render_func": render_expenses_recurring},
            "InvestmentPlanCalculations": {"config": INVESTMENT_PLAN_CONFIG, "render_func": render_output_table},
            # --- New Summary Page Added Here ---
            "Summary": {"config": None, "render_func": render_summary_page},
            "KnowledgebaseFAQ": {"config": None, "render_func": render_text_sheet}
        }
        selection = st.radio("Go to", list(pages.keys()))

    selected_page = pages[selection]
    
    if selected_page["config"]:
        selected_page["render_func"](selected_page["config"], selection)
    else:
        selected_page["render_func"](selection) # For pages that don't need config_data
        
    save_user_data(user_data)

def main_old():
    inject_pwa_script() # <-- ADD THIS LINE
    global user_data
    user_data = load_user_data()

    with st.sidebar:
        st.title("📋 Navigation")
        # Define the order and configuration for each page
        pages = {
            "AboutApp": {"config": None, "render_func": render_text_sheet},
            "BaseData": {"config": BASE_DATA_CONFIG, "render_func": render_input_form},
            "ExpensesOneTime": {"config": ONETIME_EXPENSES_CONFIG, "render_func": render_input_form},
            "ExpensesRecurring": {"config": RECURRING_EXPENSES_CONFIG, "render_func": render_expenses_recurring},
            "InvestmentPlanCalculations": {"config": INVESTMENT_PLAN_CONFIG, "render_func": render_output_table},
            "KnowledgebaseFAQ": {"config": None, "render_func": render_text_sheet}
        }
        selection = st.radio("Go to", list(pages.keys()))

    # Get the selected page's details
    selected_page = pages[selection]
    
    # Call the appropriate render function with its config data
    if selected_page["config"]:
        # The line below is the corrected one
        selected_page["render_func"](selected_page["config"], selection)
    else:
        selected_page["render_func"](selection)
        
    save_user_data(user_data)

if __name__ == "__main__":
    main()