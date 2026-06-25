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
# DATA HANDLING (Rules Storage)
# ------------------------------------------------------------------
DATA_FILE = "shipper_rules.json"
GENERAL_RULES_FILE = "general_rules.json"

def load_rules():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_rules(shipper_name, instructions, excel_text=""):
    rules = load_rules()
    rules[shipper_name.upper().strip()] = {
        "instructions": instructions,
        "excel_data_summary": excel_text
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=4)

def delete_shipper_rule(shipper_name):
    rules = load_rules()
    s_name = shipper_name.upper().strip()
    if s_name in rules:
        del rules[s_name]
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(rules, f, indent=4)
        if os.path.exists(f"{s_name}_master.pdf"):
            os.remove(f"{s_name}_master.pdf")
        return True
    return False

def load_general_rules():
    if os.path.exists(GENERAL_RULES_FILE):
        with open(GENERAL_RULES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # Default format check structure initialized
    return {"instructions": "", "has_pdf": os.path.exists("general_sample.pdf")}

def save_general_rules(instructions, has_pdf=False):
    with open(GENERAL_RULES_FILE, "w", encoding="utf-8") as f:
        json.dump({"instructions": instructions, "has_pdf": has_pdf}, f, indent=4)

def delete_general_rules():
    if os.path.exists(GENERAL_RULES_FILE):
        os.remove(GENERAL_RULES_FILE)
    if os.path.exists("general_sample.pdf"):
        os.remove("general_sample.pdf")

trained_shippers = load_rules()
general_rules_data = load_general_rules()

# ------------------------------------------------------------------
# SECTION 1: ADMIN CONTROL / AI TRAINING (PASSWORD: CK@SOHAM)
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown('<h2 class="admin-header">⚙️ Admin / AI Training Control</h2>', unsafe_allow_html=True)
    show_admin = st.checkbox("Train AI / Add Rules")
    
    if show_admin:
        password = st.text_input("Enter Admin Password", type="password")
        if password == "CK@SOHAM":
            st.success("Access Granted!")
            st.markdown("---")
            
            admin_tab = st.radio("Choose Action:", ["General Rules (All Shippers)", "Specific Shipper Rules", "View / Delete Existing Rules"])
            
            # --- 1. GENERAL RULES ---
            if admin_tab == "General Rules (All Shippers)":
                st.subheader("🌐 General Instructions")
                gen_pdf = st.file_uploader("Upload Sample Checklist (PDF)", type=["pdf"], key="gen_pdf_upload")
                
                if "gen_text" not in st.session_state:
                    st.session_state.gen_text = ""
                    
                gen_instructions = st.text_area("Write General Instructions:", value=st.session_state.gen_text, height=120)
                
                if st.button("Save General Instructions 💾"):
                    pdf_saved = False
                    if gen_pdf is not None:
                        with open("general_sample.pdf", "wb") as f:
                            f.write(gen_pdf.read())
                        pdf_saved = True
                    elif os.path.exists("general_sample.pdf"):
                        pdf_saved = True
                        
                    save_general_rules(gen_instructions, has_pdf=pdf_saved)
                    st.success("✅ General Instructions saved successfully for all shippers! (Aapki baat maan li gai hai)")
                    st.toast("Saved! 🧠")
                    st.session_state.gen_text = "" 
                    st.rerun()
                    
            # --- 2. SPECIFIC SHIPPER RULES ---
            elif admin_tab == "Specific Shipper Rules":
                st.subheader("🏢 Specific Shipper Setup")
                new_shipper = st.text_input("Enter Shipper Name (e.g. BKT)").upper().strip()
                uploaded_master = st.file_uploader("Upload Shipper Master File (Excel or PDF)", type=["xlsx", "xls", "csv", "pdf"])
                
                if "ship_text" not in st.session_state:
                    st.session_state.ship_text = ""
                    
                admin_instructions = st.text_area("Write Specific Instructions:", value=st.session_state.ship_text, height=120)
                
                if st.button("Train AI for this Shipper 🧠"):
                    if new_shipper and admin_instructions:
                        master_text = ""
                        if uploaded_master is not None:
                            try:
                                if uploaded_master.name.endswith('.pdf'):
                                    with open(f"{new_shipper}_master.pdf", "wb") as f:
                                        f.write(uploaded_master.read())
                                    master_text = "[PDF_MASTER_FILE_SAVED]"
                                else:
                                    if uploaded_master.name.endswith('.csv'):
                                        df = pd.read_csv(uploaded_master)
                                    else:
                                        df = pd.read_excel(uploaded_master)
                                    master_text = df.to_string()
                            except Exception as e:
                                st.error(f"File read error: {str(e)}")
                        
                        save_rules(new_shipper, admin_instructions, master_text)
                        st.success(f"✅ AI successfully trained for {new_shipper}! Old data updated. (Aapki baat maan li gai hai)")
                        st.toast(f"{new_shipper} Updated!")
                        st.session_state.ship_text = "" 
                        st.rerun()
                    else:
                        st.error("Please enter Shipper Name and Instructions.")
            
            # --- 3. VIEW & DELETE ACTIVE RULES ---
            elif admin_tab == "View / Delete Existing Rules":
                st.subheader("🔍 Active Brain Memory")
                
                st.markdown("**🌐 Active General Rules:**")
                if general_rules_data.get("instructions") or os.path.exists("general_sample.pdf"):
                    if general_rules_data.get("instructions"):
                        st.info(general_rules_data.get("instructions"))
                    if os.path.exists("general_sample.pdf"):
                        st.success("📄 General Sample Checklist PDF is safely locked in memory.")
                        
                    if st.button("Delete General Rules 🗑️"):
                        delete_general_rules()
                        st.success("✅ General conditions successfully deleted!")
                        st.rerun()
                else:
                    st.caption("No General Rules saved yet.")
                
                st.markdown("---")
                
                st.markdown("**🏢 Active Shipper Rules:**")
                if trained_shippers:
                    for s_name, s_info in trained_shippers.items():
                        with st.expander(f"📌 {s_name} (Click to View rules)"):
                            st.write("**Instructions Given:**", s_info.get("instructions"))
                            if s_info.get("excel_data_summary") == "[PDF_MASTER_FILE_SAVED]" or os.path.exists(f"{s_name}_master.pdf"):
                                st.success("📄 PDF Master Guide file linked in memory.")
                            elif s_info.get("excel_data_summary"):
                                st.caption("📊 Master Excel sheet data linked.")
                                
                            if st.button(f"Delete {s_name} Conditions ❌", key=f"del_{s_name}"):
                                if delete_shipper_rule(s_name):
                                    st.success(f"✅ {s_name} condition successfully deleted from AI Brain!")
                                    st.rerun()
                else:
                    st.caption("No specific shippers trained yet.")
                        
        elif password != "":
            st.error("Incorrect Password!")

# ------------------------------------------------------------------
# SECTION 2: USER AUDIT / CHECKLIST VERIFICATION
# ------------------------------------------------------------------
st.markdown('<h2 class="user-header">📋 Staff Verification Panel</h2>', unsafe_allow_html=True)

if general_rules_data.get("instructions"):
    st.caption("⚙️ **General Rules Active:** AI will automatically apply global custom guidelines to all checks.")

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
                with st.spinner("AI is auditing documents based on your specific and general rules..."):
                    try:
                        uploaded_contents = []
                        
                        for f, label in [(f1, "Checklist"), (f2, "Invoice"), (f3, "GST_Invoice"), (f4, "Declaration")]:
                            if f:
                                bytes_data = f.read()
                                uploaded_contents.append(types.Part.from_bytes(data=bytes_data, mime_type="application/pdf"))
                        
                        if os.path.exists("general_sample.pdf"):
                            with open("general_sample.pdf", "rb") as f:
                                uploaded_contents.append(types.Part.from_bytes(data=f.read(), mime_type="application/pdf"))
                        
                        if os.path.exists(f"{selected_shipper}_master.pdf"):
                            with open(f"{selected_shipper}_master.pdf", "rb") as f:
                                uploaded_contents.append(types.Part.from_bytes(data=f.read(), mime_type="application/pdf"))
                        
                        shipper_info = trained_shippers[selected_shipper]
                        shipper_specific_rules = shipper_info.get("instructions", "")
                        shipper_excel_data = shipper_info.get("excel_data_summary", "")
                        general_instructions = general_rules_data.get("instructions", "")
                        
                        # ADVANCED SYSTEM KNOWLEDGE INJECTED FOR USOFT CHA EXPORT AUDITING
                        system_instruction = """
                        You are a senior Customs House Agent (CHA) Document Auditor working for SOHAM LOGISTICS PVT. LTD. (CHA CODE: AAHCS5361ECH005). 
                        Your absolute objective is to audit the staff's 'Checklist' generated via USOFT export software against the 'Invoice', 'GST Invoice', 'Declaration' and master guidelines.
                        
                        You must verify all 50 critical parameters of the shipping bill layout including Port of Loading, AD Code, HSN/RITC Codes, Net/Gross Weights, and values like RoDTEP, ROSCTL, DBK, and IGST.
                        
                        CRITICAL AUDIT RULE: If values like Freight, Insurance, Commission, or Discount are declared on the Checklist but are completely missing or unverified in primary invoices/declarations, flag a prominent alert.
                        
                        Provide your analysis response in clear Hindi/Hinglish language so the staff can easily understand.
                        Structure your response precisely like this:
                        ❌ **Alert / Warning:** [List data mismatches, typos, or specific custom rule violations here]
                        ⚠️ **Manual Check Needed:** [List parameters that could not be verified automatically, like manual freight checks]
                        ✅ **OK:** [List what fields perfectly matched]
                        """
                        
                        final_prompt = f"""
                        --- MANDATORY GENERAL RULES FOR ALL SHIPPERS ---
                        {general_instructions}
                        
                        --- SPECIFIC RULES FOR THIS SHIPPER ({selected_shipper}) ---
                        {shipper_specific_rules}
                        
                        --- MASTER EXCEL DATA FOR THIS SHIPPER (IF APPLICABLE) ---
                        {shipper_excel_data if shipper_excel_data != '[PDF_MASTER_FILE_SAVED]' else 'Master file is attached as a PDF part.'}
                        
                        Please audit the uploaded staff documents strictly according to these criteria.
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
