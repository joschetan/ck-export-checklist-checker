import streamlit as st
import pandas as pd
import os
import json
from google import genai
from google.genai import types

# Page Configuration & Title Setup
st.set_page_config(page_title="CK EXPORT CHECKLIST CHECKER", layout="wide")
st.markdown("""
    <style>
    .main-title { font-size:34px !important; font-weight: bold; color: #1E3A8A; text-align: center; margin-bottom:20px; }
    .section-box { padding: 20px; border-radius: 10px; background-color: #F3F4F6; margin-bottom: 20px; border: 1px solid #E5E7EB; }
    .admin-header { color: #D97706; font-weight: bold; }
    .user-header { color: #2563EB; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🚢 CK EXPORT CHECKLIST CHECKER</div>', unsafe_allow_html=True)

# Initialize Gemini Client using Secrets
def get_gemini_client():
    if "GEMINI_API_KEY" in st.secrets:
        return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    return None

client = get_gemini_client()

# ------------------------------------------------------------------
# DATA HANDLING (Rules & Excel Text Storage)
# ------------------------------------------------------------------
DATA_FILE = "shipper_rules.json"

def load_rules():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_rules(shipper_name, instructions, excel_text=""):
    rules = load_rules()
    rules[shipper_name.upper().strip()] = {
        "instructions": instructions,
        "excel_data_summary": excel_text  # Excel data converted to text for AI
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=4)

trained_shippers = load_rules()

# ------------------------------------------------------------------
# SECTION 1: ADMIN CONTROL / AI TRAINING (PASSWORD: CK@SOHAM)
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown('<h2 class="admin-header">⚙️ Admin / AI Training Control</h2>', unsafe_allow_html=True)
    show_admin = st.checkbox("Train AI / Add New Shipper Rules")
    
    if show_admin:
        password = st.text_input("Enter Admin Password", type="password")
        if password == "CK@SOHAM":
            st.success("Access Granted!")
            st.markdown("---")
            
            new_shipper = st.text_input("Enter New Shipper Name (e.g. BKT)").upper().strip()
            
            # NEW: Excel File Upload Option for Admin/Shipper Master Data
            uploaded_excel = st.file_uploader("Upload Shipper Master Data / Excel List (Optional)", type=["xlsx", "xls", "csv"])
            
            admin_instructions = st.text_area("Write Instructions in Hindi/English (e.g. 1st row heading hai, Column A me HS Code hai...)", height=150)
            
            if st.button("Train AI for this Shipper 🧠"):
                if new_shipper and admin_instructions:
                    excel_text = ""
                    # If admin uploads an excel sheet, convert it to a text format that Gemini can read easily
                    if uploaded_excel is not None:
                        try:
                            if uploaded_excel.name.endswith('.csv'):
                                df = pd.read_csv(uploaded_excel)
                            else:
                                df = pd.read_excel(uploaded_excel)
                            
                            # Convert entire dataframe to string format for AI context
                            excel_text = df.to_string()
                            st.info("Excel data parsed successfully!")
                        except Exception as e:
                            st.error(f"Excel read error: {str(e)}")
                    
                    save_rules(new_shipper, admin_instructions, excel_text)
                    st.success(f"AI successfully trained for {new_shipper}! It will now appear in the User dropdown.")
                    st.rerun()
                else:
                    st.error("Please enter Shipper Name and Instructions both.")
        elif password != "":
            st.error("Incorrect Password! (Caps Lock Check karein)")

# ------------------------------------------------------------------
# SECTION 2: USER AUDIT / CHECKLIST VERIFICATION
# ------------------------------------------------------------------
st.markdown('<h2 class="user-header">📋 Staff Verification Panel</h2>', unsafe_allow_html=True)

shipper_list = list(trained_shippers.keys())

if not shipper_list:
    st.info("👋 Welcome! Currently, no shippers are trained. Please use the Admin panel on the left with your password to train the AI for your first shipper.")
else:
    selected_shipper = st.selectbox("🔍 Search & Select Shipper Name", ["-- Select Shipper --"] + shipper_list)
    
    if selected_shipper != "-- Select Shipper --":
        st.markdown(f'<div class="section-box"><h3>📂 Upload Documents for {selected_shipper}</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            f1 = st.file_uploader("1. Upload Checklist (PDF)", type=["pdf"])
            f2 = st.file_uploader("2. Upload Invoice & Packing List (PDF)", type=["pdf"])
        with col2:
            f3 = st.file_uploader("3. Upload GST Invoice (PDF)", type=["pdf"])
            f4 = st.file_uploader("4. Upload Declaration (PDF)", type=["pdf"])
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("🚀 Analyze & Check Mistakes"):
            if not client:
                st.error("Gemini API Key missing in Streamlit Secrets Locker!")
            elif f1 and f2: 
                with st.spinner("AI is auditing documents based on your specific trained rules..."):
                    try:
                        uploaded_contents = []
                        
                        for f, label in [(f1, "Checklist"), (f2, "Invoice"), (f3, "GST_Invoice"), (f4, "Declaration")]:
                            if f:
                                bytes_data = f.read()
                                uploaded_contents.append(
                                    types.Part.from_bytes(
                                        data=bytes_data,
                                        mime_type="application/pdf"
                                    )
                                )
                        
                        # Fetch saved instructions and excel text
                        shipper_info = trained_shippers[selected_shipper]
                        shipper_specific_rules = shipper_info.get("instructions", "")
                        shipper_excel_data = shipper_info.get("excel_data_summary", "")
                        
                        system_instruction = """
                        You are a senior Customs House Agent (CHA) Document Auditor. Your job is to thoroughly check the 'Checklist' file against the 'Invoice', 'GST Invoice', 'Declaration' and the custom user rules/master data provided.
                        
                        Provide your analysis response in clear Hindi/Hinglish language so the staff can easily understand.
                        Structure your response precisely like this:
                        ❌ **Alert / Warning:** [List data mismatches, typos, or specific custom rule violations here]
                        ⚠️ **Manual Check Needed:** [List parameters that could not be verified automatically, like manual freight checks]
                        ✅ **OK:** [List what fields perfectly matched]
                        """
                        
                        # Injecting the saved Excel data right into the prompt along with Hindi instructions
                        final_prompt = f"""
                        Here are the specific business conditions and formatting layout instructions provided by the Admin for this shipper ({selected_shipper}):
                        {shipper_specific_rules}
                        
                        ---
                        HERE IS THE MASTER EXCEL DATA PROVIDED BY THE ADMIN FOR THIS SHIPPER:
                        {shipper_excel_data}
                        ---
                        
                        Please audit the uploaded staff documents strictly according to the master excel layout and conditions mentioned above.
                        """
                        
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=uploaded_contents + [final_prompt],
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                temperature=0.2
                            )
                        )
                        
                        st.markdown("### 📢 Audit Report (Result)")
                        st.write(response.text)
                        
                    except Exception as e:
                        st.error(f"An error occurred during analysis: {str(e)}")
            else:
                st.error("Please upload at least the Checklist and Invoice to start auditing.")
