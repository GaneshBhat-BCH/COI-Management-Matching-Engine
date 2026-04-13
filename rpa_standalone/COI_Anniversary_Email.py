import re
import sys
import urllib.parse

# --- HARDCODED SETTINGS ---
# These are baked directly into the script for Automation Anywhere
SHAREPOINT_ROOT_URL = "https://bostonchildrenshospital.sharepoint.com/:f:/r/sites/OGCIntelligentAutomation/Legal%20Business%20Units/COI%20Management/COI%20Management%20Plans"
SHAREPOINT_URL_PARAMS = "csf=1&web=1&e=Ivm2oM"

def generate_maintenance_report_html(data_string: str):
    """
    Standalone function to generate the Anniversary Report Email.
    Parses {Date, User, ID, File} format.
    """
    # 1. Parse the string format: {val1, val2, val3, val4}, {...}
    records = []
    if data_string and data_string.strip():
        # Matches content inside curly braces
        matches = re.findall(r'\{(.*?)\}', data_string)
        for m in matches:
            parts = [p.strip() for p in m.split(',')]
            if len(parts) >= 4:
                records.append({
                    "doc_date": parts[0],             # First part is always the date
                    "file_name": parts[-1],           # Last part is always the file
                    "doc_id": parts[-2],              # Second to last is the ID
                    "from_user": ", ".join(parts[1:-2]) # Joins Wayne Lencer and MD back together
                })

    # 2. Build HTML
    html_parts = ["""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; line-height: 1.6; }
            .container { max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px; background-color: #ffffff; }
            .header { background-color: #1a237e; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }
            .header h2 { margin: 0; font-weight: 600; letter-spacing: 0.5px; }
            .intro { padding: 20px 0; font-size: 1.05rem; color: #444; }
            .msg-box { padding: 40px; text-align: center; background-color: #f8f9fa; border-radius: 8px; margin: 20px 0; border: 2px dashed #e0e0e0; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.95rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            th { background-color: #3f51b5; border-bottom: 2px solid #1a237e; padding: 14px; text-align: left; font-weight: 600; color: #ffffff; }
            td { padding: 14px; border-bottom: 1px solid #eee; vertical-align: middle; }
            tr:nth-child(even) { background-color: #fcfcfc; }
            .footer { margin-top: 40px; font-size: 0.85rem; color: #777; text-align: center; border-top: 2px solid #f5f5f5; padding-top: 20px; }
            .file-link { background-color: #3f51b5; color: white !important; padding: 8px 12px; border-radius: 4px; text-decoration: none; font-weight: 600; font-size: 0.85rem; display: inline-block; }
            .file-link:hover { background-color: #1a237e; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>COI: Annual Management Plan Reminder</h2>
            </div>
    """]

    if not records:
        html_parts.append("""
            <div class="msg-box">
                <h3 style="color: #666;">Scan Complete: No Plans found for today.</h3>
                <p>No Conflict of Interest Management Plans have reached their anniversary as of today.</p>
            </div>
        """)
    else:
        intro_html = f"""
            <div class="intro">
                <p>Hello,</p>
                <p>The following <strong>{len(records)} Conflict of Interest (COI) Management Plans</strong> have reached their annual anniversary as of today. Per institutional policy, these plans should be reviewed to ensure continued compliance.</p>
            </div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 30%;">Researcher / Entity</th>
                        <th style="width: 20%;">Anniversary</th>
                        <th style="width: 30%;">Docusign ID</th>
                        <th style="width: 20%;">Plan Document</th>
                    </tr>
                </thead>
                <tbody>
        """
        html_parts.append(intro_html)
        
        for r in records:
            # Construct SharePoint URL
            encoded_path = urllib.parse.quote(r['file_name'])
            sharepoint_url = f"{SHAREPOINT_ROOT_URL}/{encoded_path}?{SHAREPOINT_URL_PARAMS}"
            
            row_html = f"""
                <tr>
                    <td><strong>{r['from_user']}</strong></td>
                    <td>{r['doc_date']}</td>
                    <td style="font-family: monospace; color: #666; font-size: 0.85rem;">{r['doc_id']}</td>
                    <td style="text-align: center;"><a href="{sharepoint_url}" class="file-link" target="_blank">Open Plan</a></td>
                </tr>
            """
            html_parts.append(row_html)
        
        html_parts.append("</tbody></table>")

    html_parts.append("""
            <div class="footer">
                <strong>Institutional Conflict of Interest (COI) Office</strong><br>
                Automated System Notification | Internal Use Only
            </div>
        </div>
    </body>
    </html>
    """)
    
    return "".join(html_parts)

if __name__ == "__main__":
    # If using Automation Anywhere "Run Script" command with arguments
    if len(sys.argv) > 1:
        # sys.argv[1] will be the dynamic data string
        print(generate_maintenance_report_html(sys.argv[1]))
    else:
        # Default sample for testing
        sample = "{2022-06-23, Wayne Lencer, MD, 880A2BE1, Lencer.pdf}, {2016-06-23, Martha Murray, NA, Murray.pdf}"
        # print(generate_maintenance_report_html(sample))
        pass
