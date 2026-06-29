import streamlit as st
import pandas as pd
import os
import json
import requests
import base64
from google import genai
from google.genai import types

# Page Configuration
st.set_page_config(page_title="CK EXPORT CHECKLIST CHECKER", layout="wide", initial_sidebar_state="collapsed")
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

# Initialize Gemini Client
def get_gemini_client():
    if "GEMINI_API_KEY" in st.secrets:
        return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    return None

client = get_gemini_client()

# ------------------------------------------------------------------
# GITHUB CLOUD DATABASE LOGIC (PERMANENT STORAGE)
# ------------------------------------------------------------------
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_USER = st.secrets.get("GITHUB_USER", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")

def github_file_operation(filename, content=None, delete=False):
    if not GITHUB_TOKEN or not GITHUB_USER or not GITHUB_REPO:
        return None if content is None else False
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    
    if content is None and not delete:
        if res.status_code == 200:
            file_bytes = base64.b64decode(res.json()["content"])
            return file_bytes.decode("utf-8") if filename.endswith(".json") else file_bytes
        return "" if filename.endswith(".json") else None
        
    if delete:
        if sha:
            requests.delete(url, headers=headers, json={"message": f"Delete {filename}", "sha": sha})
        return True
        
    encoded_content = base64.b64encode(content if isinstance(content, bytes) else content.encode("utf-8")).decode("utf-8")
    data = {"message": f"Update {filename}", "content": encoded_content}
    if sha: data["sha"] = sha
    return requests.put(url, headers=headers, json=data).status_code in [200, 201]

def load_rules():
    data = github_file_operation("shipper_rules.json")
    if data:
        try: return json.loads(data)
        except: return {}
    return {}

def save_rules(shipper_name, instructions, new_excel_text=""):
    rules = load_rules()
    s_name = shipper_name.upper().strip()
    
    existing_data = rules.get(s_name, {"instructions": "", "excel_data_summary": ""})
    
    # Append/Merge logic for continuous training
    old_excel = existing_data.get("excel_data_summary", "")
    if new_excel_text and new_excel_text != "[PDF_MASTER_FILE_SAVED]":
        combined_excel = old_excel + "\n\n--- ADDITIONAL TRAINING DATA ADDED ---\n" + new_excel_text if old_excel else new_excel_text
    else:
        combined_excel = old_excel if old_excel else new_excel_text

    # Merge new instructions with previous text instead of overwriting completely
    old_instructions = existing_data.get("instructions", "")
    if instructions and old_instructions and instructions != old_instructions:
        combined_instructions = old_instructions + "\n" + instructions
    else:
        combined_instructions = instructions if instructions else old_instructions

    rules[s_name] = {
        "instructions": combined_instructions,
        "excel_data_summary": combined_excel
    }
    github_file_operation("shipper_rules.json", json.dumps(rules, indent=4))

trained_shippers = load_rules()
general_rules_data = json.loads(github_file_operation("general_rules.json") or '{"instructions":""}')

# ------------------------------------------------------------------
# ADMIN CONTROL PANEL
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown('<h2 class="admin-header">⚙️ Admin / AI Training Control</h2>', unsafe_allow_html=True)
    show_admin = st.checkbox("Train AI / Add Rules")
    
    if show_admin:
        password = st.text_input("Enter Admin Password", type="password", key="admin_pwd")
        if password == "CK@SOHAM":
            st.success("Access Granted!")
            st.markdown("---")
            
            # Formatted Tabs including the new Bulk Master Upload
            admin_tab = st.radio("Choose Action:", [
                "General Rules (All Shippers)", 
                "Specific Shipper Rules", 
                "View / Delete Existing Rules",
                "📦 Upload Bulk Master Excel"
            ])
            
            if admin_tab == "General Rules (All Shippers)":
                st.subheader("🌐 General Instructions")
                gen_instructions = st.text_area("Write General Instructions (Job check karte waqt dhyan rakhne yogya niyam):", value=general_rules_data.get("instructions", ""), height=200)
                if st.button("Save General Instructions 💾"):
                    github_file_operation("general_rules.json", json.dumps({"instructions": gen_instructions}, indent=4))
                    st.success("✅ General rules locked in cloud database!")
                    st.rerun()
                    
            elif admin_tab == "Specific Shipper Rules":
                st.subheader("🏢 Specific Shipper Setup")
                new_shipper = st.text_input("Enter New Shipper Name (e.g. BKT)").upper().strip()
                admin_instructions = st.text_area("Write Shipper General Rules / Base Conditions:", height=150)
                
                if st.button("Save New Shipper 🧠"):
                    if new_shipper and admin_instructions:
                        save_rules(new_shipper, admin_instructions, "")
                        st.success(f"✅ New Shipper '{new_shipper}' successfully registered with initial rules!")
                        st.rerun()
                    else:
                        st.error("Please enter both Shipper Name and Instructions.")
                        
            elif admin_tab == "View / Delete Existing Rules":
                st.subheader("📋 View / Delete Existing Rules")
                
                # Global rules view
                with st.expander("🌐 View Active General Rules"):
                    st.info(general_rules_data.get("instructions", "No general rules active."))
                
                st.markdown("---")
                
                # Filter by Shipper Name Dropdown to reduce cognitive load
                if trained_shippers:
                    search_shipper = st.selectbox("🎯 Select Shipper to View Saved Rules/Data List:", ["-- Select Shipper --"] + list(trained_shippers.keys()))
                    
                    if search_shipper != "-- Select Shipper --":
                        s_info = trained_shippers[search_shipper]
                        st.markdown(f"### 📄 Rules History for {search_shipper}:")
                        st.info(s_info.get("instructions", "No text rules recorded."))
                        
                        if s_info.get("excel_data_summary"):
                            with st.expander("📊 View Accumulated Excel/Text Data Brain Memory"):
                                st.text(s_info.get("excel_data_summary"))
                        
                        if st.button(f"Erase {search_shipper} Memory Completely 🗑️"):
                            del trained_shippers[search_shipper]
                            github_file_operation("shipper_rules.json", json.dumps(trained_shippers, indent=4))
                            github_file_operation(f"{search_shipper}_master.pdf", delete=True)
                            st.success(f"✅ Erased all records for {search_shipper}.")
                            st.rerun()
                else:
                    st.caption("No specific shippers trained yet.")
            
            elif admin_tab == "📦 Upload Bulk Master Excel":
                st.subheader("📦 Upload Master Excel Standards")
                st.markdown("""
                यहाँ आप अपने लैपटॉप की मुख्य एक्सेल फाइल अपलोड कर सकते हैं (चाहे उसमें 3 शीट्स हों या 5-6 शीट्स)। 
                यह अपलोड होते ही पुरानी पूरी मास्टर सेटिंग्स को हटाकर इसे ही नया ताज़ा बेस (Fresh Base) मान लेगा।
                """)
                
                uploaded_master_excel = st.file_uploader("Upload Master Excel File (.xlsx)", type=["xlsx"])
                
                if uploaded_master_excel is not None:
                    if st.button("Save & Overwrite Master Database 💾"):
                        with st.spinner("Reading all sheets and locking in GitHub..."):
                            try:
                                # Read all available sheets dynamically without hardcoding names
                                excel_file = pd.ExcelFile(uploaded_master_excel)
                                master_data_dict = {}
                                
                                for sheet_name in excel_file.sheet_names:
                                    df_sheet = pd.read_excel(uploaded_master_excel, sheet_name=sheet_name)
                                    # Convert to dictionary format for JSON storage
                                    master_data_dict[sheet_name] = df_sheet.to_dict(orient="records")
                                
                                # Convert the entire structure to JSON and overwrite on GitHub
                                success = github_file_operation(
                                    "master_excel_database.json", 
                                    json.dumps(master_data_dict, indent=4)
                                )
                                
                                if success:
                                    st.success(f"🎉 सफलता! आपकी एक्सेल की सभी {len(excel_file.sheet_names)} शीट्स का डेटा गिटहब क्लाउड में सुरक्षित ओवरराइट कर दिया गया है।")
                                else:
                                    st.error("गिटहब पर डेटा सेव करने में कोई समस्या आई। कृपया सीक्रेट्स टोकन जांचें।")
                            except Exception as ex:
                                st.error(f"Error reading Excel sheets: {str(ex)}")
                                
        elif password != "":
            st.error("Incorrect Password!")

# ------------------------------------------------------------------
# USER PANEL / STAFF VERIFICATION
# ------------------------------------------------------------------
st.markdown('<h2 class="user-header">📋 Staff Verification Panel</h2>', unsafe_allow_html=True)

shipper_list = list(trained_shippers.keys())

if not shipper_list:
    st.info("👋 Welcome! Please use the Admin panel to train the AI first.")
else:
    selected_shipper = st.selectbox("🔍 Search & Select Shipper Name", ["-- Select Shipper --"] + list(trained_shippers.keys()))
    
    if selected_shipper != "-- Select Shipper --":
        st.markdown(f'<div class="section-box"><h3>📂 Upload Documents for {selected_shipper}</h3>', unsafe_allow_html=True)
        f_checklist = st.file_uploader("1. Upload Checklist (PDF) *Mandatory*", type=["pdf"])
        f_invoices = st.file_uploader("2. Upload Invoices & Packing Lists (PDF) *Up to 5 files*", type=["pdf"], accept_multiple_files=True)
        f_gst = st.file_uploader("3. Upload GST Invoice (PDF) *Optional*", type=["pdf"])
        f_decl = st.file_uploader("4. Upload Declaration (PDF) *Optional*", type=["pdf"])
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("🚀 Analyze & Check Mistakes"):
            if f_checklist and f_invoices:
                with st.spinner("AI is auditing documents against history databases..."):
                    try:
                        uploaded_contents = []
                        uploaded_contents.append(types.Part.from_bytes(data=f_checklist.read(), mime_type="application/pdf"))
                        for inv in f_invoices:
                            uploaded_contents.append(types.Part.from_bytes(data=inv.read(), mime_type="application/pdf"))
                        if f_gst: uploaded_contents.append(types.Part.from_bytes(data=f_gst.read(), mime_type="application/pdf"))
                        if f_decl: uploaded_contents.append(types.Part.from_bytes(data=f_decl.read(), mime_type="application/pdf"))
                            
                        ship_pdf_bytes = github_file_operation(f"{selected_shipper}_master.pdf")
                        if ship_pdf_bytes:
                            uploaded_contents.append(types.Part.from_bytes(data=ship_pdf_bytes, mime_type="application/pdf"))
                        
                        shipper_info = trained_shippers[selected_shipper]
                        system_instruction = """
                        You are a senior Customs House Agent (CHA) Document Auditor working for SOHAM LOGISTICS PVT. LTD. (CHA CODE: AAHCS5361ECH005). 
                        Audit the USOFT export checklist against multiple documents and rules. Provide output precisely in Hindi/Hinglish.
                        Structure:
                        ❌ **Alert / Warning:** [Data mismatches]
                        ⚠️ **Manual Check Needed:** [Unverified details]
                        ✅ **OK:** [Matched fields]
                        """
                        
                        final_prompt = f"GENERAL RULES:\n{general_rules_data.get('instructions')}\n\nSPECIFIC RULES:\n{shipper_info.get('instructions')}\n\nDATABASE MASTER RECORDS:\n{shipper_info.get('excel_data_summary')}\n\nPlease analyze now."
                        
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=uploaded_contents + [final_prompt],
                            config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.2)
                        )
                        st.session_state.last_report = response.text
                        st.session_state.active_shipper = selected_shipper
                    except Exception as e: st.error(f"Error: {str(e)}")
        
        if "last_report" in st.session_state and st.session_state.active_shipper == selected_shipper:
            st.markdown("### 📢 Audit Report (Result)")
            st.markdown(f'<div class="report-box">{st.session_state.last_report}</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### 🧠 Train AI On This Report (Continuous Learning Feedback)")
            
            reply_pwd = st.text_input("Enter Password to Reply & Train AI", type="password", key="reply_pwd_input")
            if reply_pwd == "CK@SOHAM":
                st.success("Training Access Enabled!")
                
                uploaded_correction_file = st.file_uploader("Upload New Data File for this specific case (Optional Excel/PDF)", type=["xlsx", "xls", "csv", "pdf"])
                user_feedback = st.text_area("Write your reply/instruction to the AI (What it missed or needs to remember):")
                
                if st.button("Submit Feedback & Append to Shipper Memory 🚀"):
                    if user_feedback or uploaded_correction_file:
                        with st.spinner("Merging feedback permanently into GitHub Cloud Database..."):
                            try:
                                corr_text = ""
                                if uploaded_correction_file is not None:
                                    if uploaded_correction_file.name.endswith('.pdf'):
                                        github_file_operation(f"{selected_shipper}_master.pdf", uploaded_correction_file.read())
                                        corr_text = "[PDF_MASTER_FILE_SAVED]"
                                    else:
                                        df = pd.read_csv(uploaded_correction_file) if uploaded_correction_file.name.endswith('.csv') else pd.read_excel(uploaded_correction_file)
                                        corr_text = df.to_string()

                                current_rules = trained_shippers[selected_shipper]["instructions"]
                                training_prompt = f"OLD RULES:\n{current_rules}\n\nREPORT:\n{st.session_state.last_report}\n\nFEEDBACK:\n{user_feedback}\n\nMerge feedback into rules logically. Output ONLY complete updated text rules."
                                
                                update_response = client.models.generate_content(model='gemini-2.5-flash', contents=[training_prompt])
                                
                                save_rules(selected_shipper, update_response.text, corr_text)
                                st.success("🎉 'Aapki baat ko hamesha ke liye yaad kar liya gaya hai!' (Database updated permanently on GitHub)")
                                del st.session_state.last_report
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Error during training: {str(ex)}")
