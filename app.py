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
    .report-box { padding: 15px; border-radius: 8px; background-color: #FFFFFF; border-left: 5px solid #10B981; margin-top: 15px; }
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
    s_name = shipper_name.upper().strip()
    # Keep old info if overwriting via reply
    existing_excel = rules.get(s_name, {}).get("excel_data_summary", "")
    final_excel = excel_text if excel_text else existing_excel
    
    rules[s_name] = {
        "instructions": instructions,
        "excel_data_summary": final_excel
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=4)

def load_general_rules():
    if os.path.exists(GENERAL_RULES_FILE):
        with open(GENERAL_RULES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"instructions": "", "has_pdf": os.path.exists("general_sample.pdf")}

def save_general_rules(instructions, has_pdf=False):
    with open(GENERAL_RULES_FILE, "w", encoding="utf-8") as f:
        json.dump({"instructions": instructions, "has_pdf": has_pdf}, f, indent=4)

trained_shippers = load_rules()
general_rules_data = load_general_rules()

# ------------------------------------------------------------------
# SECTION 1: ADMIN CONTROL / AI TRAINING (PASSWORD: CK@SOHAM)
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown('<h2 class="admin-header">⚙️ Admin / AI Training Control</h2>', unsafe_allow_html=True)
    show_admin = st.checkbox("Train AI / Add Rules")
    
    if show_admin:
        password = st.text_input("Enter Admin Password", type="password", key="admin_pwd")
        if password == "CK@SOHAM":
            st.success("Access Granted!")
            st.markdown("---")
            
            admin_tab = st.radio("Choose Action:", ["General Rules (All Shippers)", "Specific Shipper Rules"])
            
            if admin_tab == "General Rules (All Shippers)":
                st.subheader("🌐 General Instructions")
                gen_pdf = st.file_uploader("Upload Sample Checklist (PDF)", type=["pdf"], key="admin_gen_pdf")
                gen_instructions = st.text_area("Write General Instructions:", value=general_rules_data.get("instructions", ""), height=150)
                
                if st.button("Save General Instructions 💾"):
                    save_general_rules(gen_instructions, has_pdf=(gen_pdf is not None))
                    if gen_pdf:
                        with open("general_sample.pdf", "wb") as f:
                            f.write(gen_pdf.read())
                    st.success("✅ General Instructions saved successfully!")
                    st.rerun()
                    
            elif admin_tab == "Specific Shipper Rules":
                st.subheader("🏢 Specific Shipper Setup")
                new_shipper = st.text_input("Enter Shipper Name (e.g. BKT)").upper().strip()
                uploaded_master = st.file_uploader("Upload Shipper Master File", type=["xlsx", "xls", "csv", "pdf"])
                
                current_instr = trained_shippers.get(new_shipper, {}).get("instructions", "") if new_shipper else ""
                admin_instructions = st.text_area("Write Specific Instructions:", value=current_instr, height=150)
                
                if st.button("Train AI for this Shipper 🧠"):
                    if new_shipper and admin_instructions:
                        master_text = ""
                        if uploaded_master is not None:
                            if uploaded_master.name.endswith('.pdf'):
                                with open(f"{new_shipper}_master.pdf", "wb") as f:
                                    f.write(uploaded_master.read())
                                master_text = "[PDF_MASTER_FILE_SAVED]"
                            else:
                                df = pd.read_csv(uploaded_master) if uploaded_master.name.endswith('.csv') else pd.read_excel(uploaded_master)
                                master_text = df.to_string()
                        
                        save_rules(new_shipper, admin_instructions, master_text)
                        st.success(f"✅ AI trained for {new_shipper}!")
                        st.rerun()
        elif password != "":
            st.error("Incorrect Password!")

# ------------------------------------------------------------------
# SECTION 2: USER AUDIT / CHECKLIST VERIFICATION
# ------------------------------------------------------------------
st.markdown('<h2 class="user-header">📋 Staff Verification Panel</h2>', unsafe_allow_html=True)

shipper_list = list(trained_shippers.keys())

if not shipper_list:
    st.info("👋 Welcome! Please use the Admin panel on the left to train the AI first.")
else:
    selected_shipper = st.selectbox("🔍 Search & Select Shipper Name", ["-- Select Shipper --"] + shipper_list)
    
    if selected_shipper != "-- Select Shipper --":
        st.markdown(f'<div class="section-box"><h3>📂 Upload Documents for {selected_shipper}</h3>', unsafe_allow_html=True)
        
        # 1. Mandatory Checklist Upload
        f_checklist = st.file_uploader("1. Upload Checklist (PDF) *Mandatory*", type=["pdf"])
        
        # 2. UP TO 5 INVOICES / PACKING LISTS MULTIPLE UPLOAD
        f_invoices = st.file_uploader("2. Upload Invoices & Packing Lists (PDF) *Up to 5 files allowed*", type=["pdf"], accept_multiple_files=True)
        
        col1, col2 = st.columns(2)
        with col1:
            f_gst = st.file_uploader("3. Upload GST Invoice (PDF) *Optional*", type=["pdf"])
        with col2:
            f_decl = st.file_uploader("4. Upload Declaration (PDF) *Optional*", type=["pdf"])
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("🚀 Analyze & Check Mistakes"):
            if not f_checklist:
                st.error("Please upload the mandatory Checklist PDF file.")
            elif not f_invoices or len(f_invoices) > 5:
                st.error("Please upload at least 1 and maximum 5 Invoice/Packing List PDF files.")
            else:
                with st.spinner("AI is auditing documents based on rules..."):
                    try:
                        uploaded_contents = []
                        
                        # Add Checklist
                        uploaded_contents.append(types.Part.from_bytes(data=f_checklist.read(), mime_type="application/pdf"))
                        
                        # Add up to 5 Invoices
                        for inv in f_invoices:
                            uploaded_contents.append(types.Part.from_bytes(data=inv.read(), mime_type="application/pdf"))
                            
                        # Add Optional files if uploaded
                        if f_gst:
                            uploaded_contents.append(types.Part.from_bytes(data=f_gst.read(), mime_type="application/pdf"))
                        if f_decl:
                            uploaded_contents.append(types.Part.from_bytes(data=f_decl.read(), mime_type="application/pdf"))
                            
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
                        
                        system_instruction = """
                        You are a senior Customs House Agent (CHA) Document Auditor working for SOHAM LOGISTICS PVT. LTD. (CHA CODE: AAHCS5361ECH005). 
                        Your absolute objective is to audit the staff's 'Checklist' generated via USOFT export software against multiple uploaded Invoices, Packing lists, and optional GST/Declaration documents.
                        
                        Provide your analysis response in clear Hindi/Hinglish language so the staff can easily understand.
                        Structure your response precisely like this:
                        ❌ **Alert / Warning:** [List data mismatches, typos, or specific custom rule violations here]
                        ⚠️ **Manual Check Needed:** [List parameters that could not be verified automatically]
                        ✅ **OK:** [List what fields perfectly matched]
                        """
                        
                        final_prompt = f"""
                        --- MANDATORY GENERAL RULES FOR ALL SHIPPERS ---
                        {general_instructions}
                        
                        --- SPECIFIC RULES FOR THIS SHIPPER ({selected_shipper}) ---
                        {shipper_specific_rules}
                        
                        --- MASTER EXCEL DATA FOR THIS SHIPPER (IF APPLICABLE) ---
                        {shipper_excel_data}
                        
                        Please audit the uploaded staff documents strictly according to these criteria.
                        """
                        
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=uploaded_contents + [final_prompt],
                            config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.2)
                        )
                        
                        st.session_state.last_report = response.text
                        st.session_state.active_shipper = selected_shipper
                        
                    except Exception as e:
                        st.error(f"An error occurred during analysis: {str(e)}")
        
        # Display the result report if it exists in state
        if "last_report" in st.session_state and st.session_state.active_shipper == selected_shipper:
            st.markdown("### 📢 Audit Report (Result)")
            st.markdown(f'<div class="report-box">{st.session_state.last_report}</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### 🧠 Train AI On This Report (Reply Option)")
            
            # Secure Password Field to enable reply
            reply_pwd = st.text_input("Enter Password to Reply & Train AI", type="password", key="reply_pwd_input")
            
            if reply_pwd == "CK@SOHAM":
                st.success("Training Access Enabled!")
                user_feedback = st.text_area("Write your reply/correction to the AI (e.g., 'AD Code '6470013' sahi hai, use RBI Code se match mat karo...'):")
                
                if st.button("Submit Reply & Update Brain 🚀"):
                    if user_feedback:
                        with st.spinner("AI is processing your correction..."):
                            # Ask Gemini to learn from this feedback and merge it with previous rules
                            current_rules = trained_shippers[selected_shipper]["instructions"]
                            
                            training_prompt = f"""
                            You are an expert system manager. The user has given feedback on your recent audit report.
                            OLD RULES FOR THIS SHIPPER:
                            {current_rules}
                            
                            THE REPORT YOU GENERATED:
                            {st.session_state.last_report}
                            
                            USER'S CORRECTION / REPLY:
                            {user_feedback}
                            
                            Task: Read the user's correction carefully. Merge this new instruction into the OLD RULES logically so that next time this mistake is NOT repeated. Return ONLY the newly updated complete set of instructions in clear Hindi/English. Do not output anything else.
                            """
                            
                            try:
                                update_response = client.models.generate_content(
                                    model='gemini-2.5-flash',
                                    contents=[training_prompt]
                                )
                                
                                # Save newly updated rules back to database
                                save_rules(selected_shipper, update_response.text)
                                st.success("🎉 'Aapki baat ko hamesha ke liye yaad kar liya gaya hai!' (AI brain updated successfully)")
                                st.balloons()
                                del st.session_state.last_report # clear report view to refresh
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Error during training: {str(ex)}")
                    else:
                        st.error("Please enter a reply message.")
            elif reply_pwd != "":
                st.error("Incorrect Password! Reply option locked.")
