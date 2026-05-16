"""
Serve the Bug Zero dashboard as a local web server accessible on the network.
Anyone on the same network can open http://<your-ip>:8080 in their browser.

Usage: python scripts/serve_dashboard.py
"""
import os, sys, json, threading, time, importlib
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime, timedelta, date

_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_script_dir)
_serve_dir = os.path.join(_repo_root, "site", "_build")


def _import_fetch_data():
    """Import fetch_data from publish_dashboard without breaking stdout."""
    import io
    saved = sys.stdout
    sys.path.insert(0, _script_dir)
    mod = importlib.import_module("publish_dashboard")
    sys.stdout = saved  # restore after module-level stdout wrap
    return mod.fetch_data


fetch_data = _import_fetch_data()


def get_local_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "localhost"
    finally:
        s.close()


def generate_html():
    """Fetch live data and generate the dashboard HTML."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching data from Elvis DB...")
    data = fetch_data()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Total Open: {data['total_open']} | Working Days Left: {data['working_days_left']}")

    template_path = os.path.join(_repo_root, "site", "index.html")
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    data_json = json.dumps(data, default=str, ensure_ascii=False)
    html = template.replace("/*__DASHBOARD_DATA__*/", f"window.__DATA__ = {data_json};")

    os.makedirs(_serve_dir, exist_ok=True)
    out_path = os.path.join(_serve_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Dashboard HTML generated.")
    return out_path


def auto_refresh(interval_minutes=10):
    """Regenerate dashboard HTML every N minutes."""
    while True:
        time.sleep(interval_minutes * 60)
        try:
            generate_html()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Auto-refreshed.")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Refresh error: {e}")


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=_serve_dir, **kwargs)

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.address_string()} - {format % args}")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    ip = get_local_ip()

    # Generate initial dashboard
    generate_html()

    # Start auto-refresh in background
    t = threading.Thread(target=auto_refresh, args=(10,), daemon=True)
    t.start()

    print(f"\n{'='*60}")
    print(f"  MSIL DA2.8 Bug Zero Dashboard")
    print(f"  Share this link with your team:")
    print(f"")
    print(f"  http://{ip}:{port}")
    print(f"")
    print(f"  Auto-refreshes every 10 minutes")
    print(f"  Press Ctrl+C to stop")
    print(f"{'='*60}\n")

    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
