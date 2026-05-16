"""
Deploy Bug Zero dashboard HTML to SharePoint Online.
Uploads the generated index.html to a SharePoint document library
so anyone with Harman access can view it via a shareable link.

Usage: python scripts/deploy_sharepoint.py

Prerequisites:
  pip install Office365-REST-Python-Client
"""
import os, sys, json
from datetime import datetime

_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_script_dir)
sys.path.insert(0, _script_dir)

from publish_dashboard import fetch_data


def generate_html():
    """Fetch live data and build the dashboard HTML."""
    print("Fetching Bug Zero data from Elvis DB...")
    data = fetch_data()
    print(f"Total Open: {data['total_open']} | Working Days Left: {data['working_days_left']}")

    template_path = os.path.join(_repo_root, "site", "index.html")
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    data_json = json.dumps(data, default=str, ensure_ascii=False)
    html = template.replace("/*__DASHBOARD_DATA__*/", f"window.__DATA__ = {data_json};")

    build_dir = os.path.join(_repo_root, "site", "_build")
    os.makedirs(build_dir, exist_ok=True)
    out_path = os.path.join(build_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML generated: {out_path}")
    return out_path, data


def upload_to_sharepoint(html_path):
    """Upload the HTML file to SharePoint Online using Office365 REST client."""
    try:
        from office365.runtime.auth.user_credential import UserCredential
        from office365.sharepoint.client_context import ClientContext
    except ImportError:
        print("\nERROR: Office365-REST-Python-Client not installed.")
        print("Run: pip install Office365-REST-Python-Client")
        sys.exit(1)

    # SharePoint configuration — update these for your site
    site_url = os.getenv("SHAREPOINT_SITE_URL", "")
    username = os.getenv("SHAREPOINT_USER", "")
    password = os.getenv("SHAREPOINT_PASS", "")
    folder_path = os.getenv("SHAREPOINT_FOLDER", "Shared Documents/BugZero_Dashboard")

    if not site_url or not username:
        print("\n" + "=" * 60)
        print("  SharePoint Configuration Needed")
        print("=" * 60)
        print()
        print("Add these to your .env file:")
        print()
        print('  SHAREPOINT_SITE_URL=https://harman.sharepoint.com/sites/YOUR_SITE')
        print('  SHAREPOINT_USER=merlin.devarapaga@harman.com')
        print('  SHAREPOINT_PASS=your_password')
        print('  SHAREPOINT_FOLDER=Shared Documents/BugZero_Dashboard')
        print()
        print("Or use the simpler OneDrive method below.")
        print("=" * 60)
        _offer_onedrive_method(html_path)
        return

    print(f"Connecting to SharePoint: {site_url}")
    ctx = ClientContext(site_url).with_credentials(UserCredential(username, password))

    # Upload file
    target_folder = ctx.web.get_folder_by_server_relative_url(folder_path)
    filename = "DA28_BugZero_Dashboard.html"
    with open(html_path, "rb") as f:
        content = f.read()

    target_folder.upload_file(filename, content).execute_query()
    print(f"Uploaded to SharePoint: {folder_path}/{filename}")

    # Get sharing link
    file_url = f"{site_url}/{folder_path}/{filename}"
    print(f"\nSharePoint URL: {file_url}")
    print("Share this link with your team — anyone with Harman login can view it.")


def _offer_onedrive_method(html_path):
    """Offer to copy to OneDrive sync folder as a simpler alternative."""
    onedrive_path = os.path.join(os.path.expanduser("~"), "OneDrive - Harman")
    if not os.path.exists(onedrive_path):
        # Try alternate paths
        for name in ["OneDrive - HARMAN", "OneDrive - Harman International", "OneDrive"]:
            alt = os.path.join(os.path.expanduser("~"), name)
            if os.path.exists(alt):
                onedrive_path = alt
                break

    if os.path.exists(onedrive_path):
        dest_dir = os.path.join(onedrive_path, "BugZero_Dashboard")
        os.makedirs(dest_dir, exist_ok=True)
        import shutil
        dest = os.path.join(dest_dir, "DA28_BugZero_Dashboard.html")
        shutil.copy2(html_path, dest)
        print(f"\nCopied to OneDrive: {dest}")
        print("It will auto-sync to SharePoint/OneDrive cloud.")
        print("Right-click the file in OneDrive > 'Share' > 'Copy link'")
        print("Share that link with your team.")
    else:
        # Last resort: copy to a known shared path
        print(f"\nOneDrive folder not found at: {onedrive_path}")
        print(f"\nManual steps:")
        print(f"  1. Open: {html_path}")
        print(f"  2. Upload to SharePoint/OneDrive/Teams manually")
        print(f"  3. Share the link")


def copy_to_teams_channel(html_path):
    """
    Alternative: Open the HTML in browser and offer to copy to Teams.
    Teams channels have a SharePoint-backed Files tab.
    """
    print("\nAlternative — Upload via Teams:")
    print("  1. Open your Teams channel")
    print("  2. Go to 'Files' tab")
    print("  3. Upload this file:")
    print(f"     {html_path}")
    print("  4. Click the uploaded file > 'Copy link'")
    print("  5. Share the link — anyone in the team can open it")


def main():
    html_path, data = generate_html()

    print(f"\n{'='*60}")
    print(f"  MSIL DA2.8 Bug Zero Dashboard — {data['total_open']} Open")
    print(f"{'='*60}")

    # Primary method: Copy to OneDrive - HARMAN for auto-sync
    _offer_onedrive_method(html_path)

    # Also open in browser for preview
    print(f"\nOpening preview in browser...")
    os.startfile(html_path)


if __name__ == "__main__":
    main()
