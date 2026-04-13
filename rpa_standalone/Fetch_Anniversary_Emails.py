import sys
import os
import json
import urllib.parse

# ==========================================
# SAFE IMPORTS
# ==========================================
IMPORT_ERROR = None
try:
    import asyncio
    import asyncpg
    import re
    from datetime import datetime
except Exception as e:
    IMPORT_ERROR = str(e)

# ==========================================
# HARDCODED CONFIGURATION
# ==========================================
DB_USER = "postgres"
DB_PASSWORD = "IntelligentAutomation2026!"
DB_HOST = "aws-bch-np-intelligentautomation-db.cluster-cmfdfqm1vnou.us-east-1.rds.amazonaws.com"
DB_PORT = "5432"
DB_NAME = "RPASQLP"

# ==========================================
# FUNCTIONS
# ==========================================

def log_debug(message):
    sys.stderr.write(f"DEBUG: {message}\n")
    sys.stderr.flush()

async def fetch_anniversary_data(target_mm_dd):
    """Core logic: Fetches data and builds drafts."""
    conn = None
    try:
        log_debug(f"Connecting to database (Target Date: {target_mm_dd})...")
        conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME
        )
        
        query = """
        SELECT doc_date, from_user, docusign_id AS doc_id, file_name, file_path, company, email
        FROM coi_mgmt.pdf_documents
        WHERE doc_date IS NOT NULL 
          AND doc_date NOT IN ('NA', 'N/A', '', 'None')
          AND TO_CHAR(TO_DATE(doc_date, 'YYYY-MM-DD'), 'MM-DD') = $1;
        """
        
        log_debug(f"Executing database query for {target_mm_dd}...")
        rows = await conn.fetch(query, target_mm_dd)
        if not rows: 
            return {
                "status": "success",
                "emails_to_send": [], 
                "missing_emails_table_body": ""
            }
        
        valid_results = []
        missing_rows = []
        for row in rows:
            doc_date = row['doc_date']
            from_user = row['from_user']
            company_name = row['company'].strip() if row['company'] and str(row['company']).upper().strip() != "NA" else "[Company]"
            
            # Multi-Researcher Greeting Logic
            names = re.split(r';|,| and | & ', from_user, flags=re.IGNORECASE)
            last_names = []
            for n in names:
                clean_n = re.sub(r'\b(MD|M\.D\.|PhD|Ph\.D\.|DO|D\.O\.|MBBS|MPH)\b', '', n, flags=re.IGNORECASE).strip()
                name_parts = clean_n.split()
                if name_parts:
                    last_names.append(name_parts[-1])
            
            if len(last_names) > 1:
                greeting = f"Drs. {last_names[0]} and {last_names[1]}" if len(last_names) == 2 else f"Drs. {', '.join(last_names[:-1])}, and {last_names[-1]}"
            else:
                greeting = f"Dr. {last_names[0]}" if last_names else "Dr. [Last Name]"
            
            researcher_email = row['email'].strip() if row['email'] else ""
            is_missing_email = not researcher_email or researcher_email.upper() in ['NA', 'N/A', 'NONE']
            
            if is_missing_email:
                missing_rows.append(row)
            else:
                email_draft = (
                    f"<p>Dear {greeting},</p>"
                    f"<p>I am reaching out about your COI management plan for {company_name}, which was approved by the COI Committee on {doc_date}.</p>"
                    "<p>As noted in your COI management plan, you are required to provide an update on an annual basis to the COI Office.</p>"
                    "<p>Kindly complete the attached form at your earliest convenience.</p>"
                    "<p>Please respond to this email with any questions or concerns.</p>"
                    "<p>Thank you,<br>COI Office</p>"
                )

                valid_results.append({
                    "status": "success",
                    "doc_date": str(doc_date),
                    "researcher_names": from_user,
                    "researcher_emails": researcher_email,
                    "doc_id": row['doc_id'],
                    "file_name": row['file_name'],
                    "email_draft_body": email_draft,
                    "company": company_name
                })
                
        # Generate the HTML Table for missing emails
        missing_table_body = ""
        if missing_rows:
            table_html = "<table border='1' style='border-collapse: collapse; font-family: sans-serif;'>"
            table_html += "<tr style='background-color: #f2f2f2;'><th style='padding:8px;'>Date</th><th style='padding:8px;'>Researcher</th><th style='padding:8px;'>Company</th><th style='padding:8px;'>File Name</th></tr>"
            for r in missing_rows:
                d_val = r['doc_date'] if r['doc_date'] else "NA"
                n_val = r['from_user'] if r['from_user'] else "NA"
                c_val = r['company'] if r['company'] else "NA"
                f_val = r['file_name'] if r['file_name'] else "NA"
                
                # Construct exact magic SharePoint link
                if f_val != "NA":
                    base_path = "/sites/OGCIntelligentAutomation/Legal Business Units/COI Management/COI Management Plans/"
                    full_path = base_path + f_val
                    encoded_id = urllib.parse.quote(full_path)
                    view_id = "04ab7f45-5398-44c4-a73e-8b3177dbfe2b"
                    magic_link = f"https://bostonchildrenshospital.sharepoint.com/sites/OGCIntelligentAutomation/Legal%20Business%20Units/Forms/AllItems.aspx?id={encoded_id}&viewid={view_id}"
                else:
                    magic_link = "#"
                
                # Make file name a clickable hyperlink
                f_val_linked = f"<a href='{magic_link}' target='_blank' style='color: #0078d4; text-decoration: none;'>{f_val}</a>"
                table_html += f"<tr><td style='padding:8px;'>{d_val}</td><td style='padding:8px;'>{n_val}</td><td style='padding:8px;'>{c_val}</td><td style='padding:8px;'>{f_val_linked}</td></tr>"
            table_html += "</table>"
            intro_text = (
                "<p>Hello Team,</p>"
                "<p>The following Conflict of Interest (COI) Management Plans are due for their annual review. "
                "However, our system indicates that the researchers associated with these plans do not have a valid email address on file.</p>"
                "<p>Please review the records below and follow up to secure the appropriate contact information so their annual notifications can be distributed.</p><br>"
            )
            outro_text = "<br><p>Thank you,<br>Intelligent Automation System</p>"
            
            missing_table_body = intro_text + table_html + outro_text

        return {
            "status": "success",
            "emails_to_send": valid_results,
            "missing_emails_table_body": missing_table_body
        }
    except Exception as e:
        return {"status": "error", "message": f"Execution Error: {str(e)}"}
    finally:
        if conn: await conn.close()

def get_anniversary_emails(target_date=None):
    """
    ENTRY POINT FOR AUTOMATION ANYWHERE.
    target_date: Optional string in 'MM-DD' format.
    """
    if IMPORT_ERROR:
        return json.dumps({
            "status": "error", 
            "message": f"Dependency Error: {IMPORT_ERROR}. Env: {sys.executable}"
        })
    
    # Default to today if no date provided
    if not target_date or str(target_date).strip() == "":
        target_mm_dd = datetime.now().strftime('%m-%d')
    else:
        target_mm_dd = str(target_date).strip()

    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        final_data = asyncio.run(fetch_anniversary_data(target_mm_dd))
        return json.dumps(final_data)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Critical Failure: {str(e)}"})

if __name__ == "__main__":
    # Test with today's date
    print(get_anniversary_emails())
    # Example test with specific date:
    # print(get_anniversary_emails("03-25"))
