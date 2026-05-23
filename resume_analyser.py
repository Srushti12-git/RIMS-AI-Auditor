import streamlit as st
import os
import PyPDF2
import re
import base64
import requests
import json
import time
import pandas as pd
from PIL import Image
import io

# --- Installation & Setup Instructions ---
# 1. Install dependencies: 
#    & "C:/Program Files (x86)/Microsoft Visual Studio/Shared/Python39_64/python.exe" -m pip install streamlit PyPDF2 requests pandas Pillow openpyxl
# 2. Run the software:
#    & "C:/Program Files (x86)/Microsoft Visual Studio/Shared/Python39_64/python.exe" -m streamlit run d:/RIMS_software/fwdrimsresumes/resume_analyser.py

MODEL_NAME = "gemini-2.5-flash-preview-09-2025"

def call_gemini_api(api_key, prompt, base64_data=None, mime_type="application/pdf"):
    """Calls Gemini API with strict JSON schema for RIMS/FORM 5 compliance."""
    if not api_key:
        return "ERROR_NO_KEY: Please provide an API Key in the sidebar."
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={api_key}"
    
    parts = [{"text": prompt}]
    if base64_data:
        parts.append({"inlineData": {"mimeType": mime_type, "data": base64_data}})

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "OLD ID NO": {"type": "string"},
                    "PHONE NUMBER": {"type": "string"},
                    "KYC DOCUMENT NUMBER": {"type": "string", "description": "12-digit Aadhaar Number from the handwritten form"},
                    "NAME  ": {"type": "string"},
                    "Fathers Name or husbands Name (in case of married women)": {"type": "string"},
                    "Date of Birth": {"type": "string"},
                    "Sex": {"type": "string", "enum": ["Male", "Female", "Other"]},
                    "IFSC CODE": {"type": "string"},
                    "BANK ACCOUNTED NO": {"type": "string"},
                    "BANK NAME": {"type": "string"},
                    "AADHAAR_FROM_XEROX": {"type": "string", "description": "The 12-digit number physically printed on the Aadhaar card image"},
                    "VERIFICATION_STATUS": {"type": "string", "description": "Comparison result: 'Match' or 'Mismatch'"}
                }
            }
        }
    }

    for i in range(5):
        try:
            response = requests.post(url, json=payload, timeout=120)
            if response.status_code == 200:
                result = response.json()
                return result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "")
            elif response.status_code == 403:
                return "ERROR_403: Invalid API Key or Permission Denied. Please check your key."
            elif response.status_code == 429:
                time.sleep(2**i)
            else:
                return f"ERROR_{response.status_code}: {response.text[:100]}"
        except Exception as e:
            if i == 4: return f"CONNECTION_ERROR: {str(e)}"
            time.sleep(2**i)
    return "API_TIMEOUT"

def process_rims_package(api_key, file_path):
    """Processes the multi-page PDF containing the form and ID proofs."""
    try:
        file_path = os.path.normpath(file_path)
        if not os.path.exists(file_path):
            return {"error": "File path invalid", "Filename": os.path.basename(file_path)}

        with open(file_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        
        prompt = """
        You are an HR Auditor for RIMS MANPOWER SOLUTIONS. 
        Analyze this PDF:
        - Page 1: Handwritten APPLICATION FOR EMPLOYMENT form.
        - Other pages: Xerox copies of Aadhaar card and Bank Passbook.
        TASK: Extract handwritten details for Excel. Read printed Aadhaar number from card image (Page 2/3). 
        Compare handwritten vs printed. Set VERIFICATION_STATUS to 'Match' or 'Mismatch'.
        """
        
        res_json = call_gemini_api(api_key, prompt, encoded)
        
        if "ERROR" in res_json or "TIMEOUT" in res_json:
            return {"error": res_json, "Filename": os.path.basename(file_path)}
        
        data = json.loads(res_json)
        data['Filename'] = os.path.basename(file_path)
        data['RESUMES STATUS'] = "Processed"
        data['TYPE OF KYC'] = "Aadhaar"
        return data
    except Exception as e:
        return {"error": str(e), "Filename": os.path.basename(file_path)}

# --- Streamlit Dashboard ---
st.set_page_config(page_title="RIMS AI Auditor Pro", page_icon="📑", layout="wide")

st.title("📑 RIMS Form & Aadhaar AI Auditor")
st.markdown("Automated processing of handwritten application forms and **Identity Verification**.")

# Sidebar - Security & Config
st.sidebar.header("🔑 Authentication")
user_api_key = st.sidebar.text_input("Enter Gemini API Key:", type="password", help="Get a free key from https://aistudio.google.com/app/apikey")

if not user_api_key:
    st.sidebar.warning("⚠️ You must enter an API Key to use this software.")

st.sidebar.divider()
app_mode = st.sidebar.selectbox("Select Mode:", ["Batch Process Folder", "Single File Test"])

if app_mode == "Single File Test":
    p = st.text_input("Enter Local File Path:", placeholder="D:/RIMS_software/fwdrimsresumes/111101.pdf")
    if p and os.path.isfile(p):
        if st.button("Run Audit"):
            with st.spinner("AI is analyzing..."):
                data = process_rims_package(user_api_key, p)
                if data and "error" not in data:
                    st.success("Analysis Complete")
                    st.json(data)
                else:
                    st.error(f"Failed: {data.get('error')}")

else:
    st.header("📂 Bulk Folder Audit & Excel Export")
    folder_path = st.text_input("Enter Folder Path containing PDFs:", placeholder="D:/RIMS_software/fwdrimsresumes")
    
    if folder_path and os.path.isdir(folder_path):
        all_files = os.listdir(folder_path)
        pdfs = [f for f in all_files if f.lower().endswith('.pdf')]
        st.write(f"📁 Found **{len(pdfs)}** files in folder.")
        
        if st.button("Start Batch Processing"):
            if not user_api_key:
                st.error("Please enter your API Key in the sidebar first.")
            else:
                results = []
                error_log = []
                progress_bar = st.progress(0)
                
                for idx, filename in enumerate(pdfs):
                    full_path = os.path.join(folder_path, filename)
                    data = process_rims_package(user_api_key, full_path)
                    
                    if data and "error" not in data:
                        results.append(data)
                    else:
                        error_log.append({"File": filename, "Issue": data.get('error') if data else "No Response"})
                    
                    progress_bar.progress((idx + 1) / len(pdfs))
                
                if results:
                    st.success(f"Audit Complete! {len(results)} records extracted.")
                    df = pd.DataFrame(results)
                    st.dataframe(df[['NAME  ', 'KYC DOCUMENT NUMBER', 'VERIFICATION_STATUS', 'BANK ACCOUNTED NO']])
                    
                    towrite = io.BytesIO()
                    with pd.ExcelWriter(towrite, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='FORM 5 DATA')
                    
                    st.download_button(
                        label="📥 Download RIMS Verified Excel",
                        data=towrite.getvalue(),
                        file_name="RIMS_Verified_Batch.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                if error_log:
                    with st.expander("⚠️ View Failures (Reasoning)"):
                        st.table(error_log)
    elif folder_path:
        st.error("The path provided does not exist or is not a folder.")

st.sidebar.markdown("---")
st.sidebar.info("Tip: Ensure PDF contains the form on page 1 and Aadhaar xerox on pages 2-3.")