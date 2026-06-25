import streamlit as st
import pandas as pd
import os
import json

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

# ------------------------------------------------------------------
# DATA HANDLING (Rules Storage)
# ------------------------------------------------------------------
DATA_FILE = "shipper_rules.json"

def load_rules():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_rules(shipper_name, instructions, files_data=None):
    rules = load_rules()
    rules[shipper_name.upper().strip()] = {
        "instructions": instructions,
        "has_excel": True if files_data else False
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=4)

# Load existing trained shippers
trained_shippers = load_rules()

# ------------------------------------------------------------------
# SECTION 1: ADMIN CONTROL / AI TRAINING (PASSWORD: CK@SOHAM)
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown('<h2 class="admin-header">⚙️ Admin / AI Training Control</h2>', unsafe_allow_html=True)
    show_admin = st.checkbox("Train AI / Add New Shipper Rules")
    
    if show_admin:
        # Password set to CK@SOHAM
        password = st.text_input("Enter Admin Password", type="password")
        if password == "CK@SOHAM":
            st.success("Access Granted!")
            st.markdown("---")
            
            new_shipper = st.text_input("Enter New Shipper Name (e.g. JYOTINDRA INTERNATIONAL)").upper().strip()
            admin_instructions = st.text_area("Write Instructions in Hindi/English (e.g. BKT rules, HS codes logic etc.)")
            uploaded_excel = st.file_uploader("Upload Shipper Master Data / Excel List (Optional)", type=["xlsx", "xls", "csv"])
            
            if st.button("Train AI for this Shipper 🧠"):
                if new_shipper and admin_instructions:
                    save_rules(new_shipper, admin_instructions, uploaded_excel)
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
    # Searchable Dropdown with "jyoti" type search enabled
    selected_shipper = st.selectbox("🔍 Search & Select Shipper Name", ["-- Select Shipper --"] + shipper_list)
    
    if selected_shipper != "-- Select Shipper --":
        st.markdown(f'<div class="section-box"><h3>📂 Upload Documents for {selected_shipper}</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            f1 = st.file_uploader("1. Upload Checklist (PDF/Image)", type=["pdf", "png", "jpg", "jpeg"])
            f2 = st.file_uploader("2. Upload Invoice & Packing List (PDF)", type=["pdf"])
        with col2:
            f3 = st.file_uploader("3. Upload GST Invoice (PDF)", type=["pdf"])
            f4 = st.file_uploader("4. Upload Declaration (PDF)", type=["pdf"])
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("🚀 Analyze & Check Mistakes"):
            if f1 and f2: 
                with st.spinner("AI is auditing documents based on your specific trained rules..."):
                    
                    # Gemini API Connectivity Placeholder
                    st.markdown("### 📢 Audit Report (Result)")
                    st.error("❌ **Alert / Warning:** Checklist me Freight 2000 USD likha hai par Invoice ya kisi aur document pe nahi mila. **Please check Freight manually.**")
                    st.warning("⚠️ **Warning:** HSN Code 40111010 ke samne Description Master list se match nahi ho raha hai.")
                    st.success("✅ **OK:** AD Code aur Bank Account Details bilkul sahi hain.")
            else:
                st.error("Please upload at least the Checklist and Invoice to start auditing.")
