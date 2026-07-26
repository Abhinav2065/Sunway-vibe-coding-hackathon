import http.server
import socketserver
import urllib.request
import json
import os
import sys
import socket
import base64
import re

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
STATUS_FILE = os.path.join(DIRECTORY, "status.json")
IMAGE_FILE = os.path.join(DIRECTORY, "latest.jpg")

# Initialize default status file if it doesn't exist
if not os.path.exists(STATUS_FILE):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "isMonkey": False,
            "timestamp": "None",
            "message": "No detection run yet"
        }, f, indent=2)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

class ProxyAndStaticHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        norm_path = self.path.rstrip('/')
        if not norm_path:
            norm_path = '/'

        # Endpoint 1: JSON status endpoint for other LAN computers
        if norm_path in ['/status.json', '/status', '/api/status']:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(json.dumps({"isMonkey": False, "message": "No data"}).encode('utf-8'))
            return

        # Endpoint 2: Latest snapshot image endpoint for other LAN computers
        elif norm_path in ['/latest.jpg', '/latest', '/api/latest_image']:
            if os.path.exists(IMAGE_FILE):
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                with open(IMAGE_FILE, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "No image captured yet")
            return

        else:
            # Fallback to standard static file serving
            super().do_GET()

    def do_POST(self):
        norm_path = self.path.rstrip('/')
        if norm_path == '/api/chat':
            content_length = int(self.headers.get('Content-Length', 0))
            body_bytes = self.rfile.read(content_length)
            
            # Parse body to extract base64 image for saving to latest.jpg
            try:
                body_json = json.loads(body_bytes.decode('utf-8'))
                body_json['model'] = 'qwen/qwen3.6-27b'
                forward_data = json.dumps(body_json).encode('utf-8')
                
                # Extract image base64 if present
                for msg in body_json.get('messages', []):
                    content = msg.get('content', [])
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get('type') == 'image_url':
                                url_str = item.get('image_url', {}).get('url', '')
                                if 'base64,' in url_str:
                                    b64_data = url_str.split('base64,')[1]
                                    with open(IMAGE_FILE, 'wb') as img_out:
                                        img_out.write(base64.b64decode(b64_data))
            except Exception as e:
                print("Error extracting image:", e)
                forward_data = body_bytes

            # Forward payload to Groq API using GROQ_API_KEY environment variable or fallback
            target_url = "https://api.groq.com/openai/v1/chat/completions"
            groq_api_key = os.environ.get("GROQ_API_KEY", "YOUR_GROQ_API_KEY_HERE")
            
            req = urllib.request.Request(
                target_url,
                data=forward_data,
                headers={
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                method="POST"
            )

            try:
                with urllib.request.urlopen(req) as response:
                    res_body = response.read()
                    
                    # Update status.json based on model response
                    try:
                        res_json = json.loads(res_body.decode('utf-8'))
                        raw_answer = res_json.get('choices', [{}])[0].get('message', {}).get('content', '')
                        
                        # Strip <think> reasoning tags
                        clean_answer = re.sub(r'<think>.*?</think>', '', raw_answer, flags=re.DOTALL).strip()
                        is_monkey = clean_answer.upper().startswith('YES') or clean_answer.upper() == 'YES'

                        status_data = {
                            "isMonkey": is_monkey,
                            "timestamp": self.date_time_string(),
                            "rawResponse": clean_answer
                        }

                        with open(STATUS_FILE, "w", encoding="utf-8") as sf:
                            json.dump(status_data, sf, indent=2)

                    except Exception as parse_err:
                        print("Error updating status.json:", parse_err)

                    self.send_response(response.status)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(res_body)
            except urllib.error.HTTPError as e:
                err_body = e.read()
                self.send_response(e.code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(err_body)
            except Exception as e:
                err_json = json.dumps({"error": str(e)}).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(err_json)
        else:
            self.send_error(404, "Endpoint not found")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    local_ip = get_local_ip()
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), ProxyAndStaticHTTPRequestHandler) as httpd:
        print("="*60)
        print(f"Server is RUNNING and accessible across your Local Network (LAN):")
        print(f"  - Web Application URL:   http://{local_ip}:{PORT}")
        print(f"  - Localhost URL:         http://localhost:{PORT}")
        print(f"  - 1. JSON Status Endpoint: http://{local_ip}:{PORT}/status.json")
        print(f"  - 2. Latest Image Endpoint: http://{local_ip}:{PORT}/latest.jpg")
        print("="*60)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Server stopped.")
