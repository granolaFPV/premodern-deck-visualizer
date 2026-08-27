"""
MTG Deck Visualizer Web Server.
Built on Python 3 http.server with REST API endpoints.
Provides:
- Deck list parsing (plain text, set/collector codes, Moxfield links)
- Scryfall image and Premodern printing resolution
- Retro Border detection and real scan prioritization
- 6x10 mainboard grid packing & angled sideboard fanning
- Interactive card printing & foreign language version lookup
- Custom card photo upload and alternate scan hosting
- High-res image proxying for canvas exports
- Utilitarian 90s retro web interface
"""

import os
import sys
import json
import base64
import hashlib
import urllib.request
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

# Add current directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import deck_parser
import scryfall_client
import grid_packer

STATIC_DIR = os.path.join(BASE_DIR, 'static')
UPLOADS_DIR = os.path.join(STATIC_DIR, 'uploads')
os.makedirs(UPLOADS_DIR, exist_ok=True)

class DeckVisualizerHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # 0. Download Project Zip
        if path in ('/download-zip', '/mtg_deck_visualizer.zip'):
            zip_file = os.path.join(STATIC_DIR, 'mtg_deck_visualizer.zip')
            if not os.path.exists(zip_file):
                zip_file = os.path.join(BASE_DIR, 'mtg_deck_visualizer.zip')
            self.serve_file(zip_file, 'application/zip', filename='mtg_deck_visualizer.zip')
            return

        # 1. API: Card printings & languages
        if path == '/api/card-printings':
            card_name = query.get('name', [''])[0]
            if not card_name:
                self.send_error_json(400, 'Missing card name parameter')
                return
            try:
                printings = scryfall_client.get_all_printings_and_languages(card_name)
                self.send_json({'card_name': card_name, 'printings': printings, 'total': len(printings)})
            except Exception as e:
                self.send_error_json(500, f'Error fetching printings: {e}')
            return

        # 2. API: Image proxy (ensures CORS-friendly Canvas export)
        if path == '/api/proxy-image':
            img_url = query.get('url', [''])[0]
            if not img_url:
                self.send_error_json(400, 'Missing image url parameter')
                return
            try:
                # If local static path
                clean_path = urllib.parse.urlparse(img_url).path
                if clean_path.startswith('/static/'):
                    rel_p = clean_path[len('/static/'):]
                    local_f = os.path.join(STATIC_DIR, rel_p)
                    if os.path.exists(local_f) and os.path.isfile(local_f):
                        c_type = 'image/jpeg'
                        if local_f.endswith('.png'):
                            c_type = 'image/png'
                        elif local_f.endswith('.webp'):
                            c_type = 'image/webp'
                        self.serve_file(local_f, c_type)
                        return

                req = urllib.request.Request(img_url, headers={
                    'User-Agent': 'MTGPremodernDeckVisualizer/1.0 (https://github.com/granolaFPV/premodern-deck-visualizer)'
                })
                with urllib.request.urlopen(req, timeout=10) as resp:
                    content_type = resp.headers.get('Content-Type', 'image/jpeg')
                    data = resp.read()
                    self.send_response(200)
                    self.send_header('Content-Type', content_type)
                    self.send_header('Cache-Control', 'public, max-age=86400')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
            except Exception as e:
                self.send_error_json(502, f'Error proxying image: {e}')
            return

        # 3. Static Files
        if path == '/' or path == '/index.html':
            filepath = os.path.join(STATIC_DIR, 'index.html')
            self.serve_file(filepath, 'text/html; charset=utf-8')
            return

        # Clean static relative path
        rel_path = path.lstrip('/')
        if rel_path.startswith('static/'):
            rel_path = rel_path[len('static/'):]
            
        filepath = os.path.join(STATIC_DIR, rel_path)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            content_type = 'text/plain'
            if filepath.endswith('.html'):
                content_type = 'text/html; charset=utf-8'
            elif filepath.endswith('.css'):
                content_type = 'text/css; charset=utf-8'
            elif filepath.endswith('.js'):
                content_type = 'application/javascript; charset=utf-8'
            elif filepath.endswith('.json'):
                content_type = 'application/json'
            elif filepath.endswith('.png'):
                content_type = 'image/png'
            elif filepath.endswith('.jpg') or filepath.endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif filepath.endswith('.svg'):
                content_type = 'image/svg+xml'
            elif filepath.endswith('.ico'):
                content_type = 'image/x-icon'
            self.serve_file(filepath, content_type)
            return

        self.send_error_json(404, f'Not Found: {path}')

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # Read JSON body
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len) if content_len > 0 else b'{}'
        try:
            req_data = json.loads(post_body.decode('utf-8'))
        except Exception:
            req_data = {}

        # 1. API: Upload Card Image (User photos, scans, drag & drop)
        if path == '/api/upload-card-image':
            data_url = req_data.get('data_url', '')
            card_name = req_data.get('card_name', 'custom_card')
            if not data_url or ',' not in data_url:
                self.send_error_json(400, 'Invalid data URL image format')
                return
            try:
                header, b64data = data_url.split(',', 1)
                img_bytes = base64.b64decode(b64data)
                
                # Determine extension
                ext = 'jpg'
                if 'png' in header:
                    ext = 'png'
                elif 'webp' in header:
                    ext = 'webp'

                file_hash = hashlib.md5(img_bytes).hexdigest()[:10]
                clean_name = ''.join(ch for ch in card_name.lower() if ch.isalnum() or ch in ('_', '-'))
                filename = f"{clean_name}_{file_hash}.{ext}"
                filepath = os.path.join(UPLOADS_DIR, filename)

                with open(filepath, 'wb') as f:
                    f.write(img_bytes)

                # Check for optional Cloudflare R2 / S3 storage (Free persistent storage on Render)
                r2_bucket = os.environ.get('R2_BUCKET_NAME')
                r2_endpoint = os.environ.get('R2_ENDPOINT_URL')
                r2_access = os.environ.get('R2_ACCESS_KEY_ID')
                r2_secret = os.environ.get('R2_SECRET_ACCESS_KEY')
                r2_domain = os.environ.get('R2_PUBLIC_DOMAIN', '').rstrip('/')

                public_url = f"/static/uploads/{filename}"
                if r2_bucket and r2_endpoint and r2_access and r2_secret:
                    try:
                        import boto3
                        s3 = boto3.client(
                            's3',
                            endpoint_url=r2_endpoint,
                            aws_access_key_id=r2_access,
                            aws_secret_access_key=r2_secret,
                            region_name='auto'
                        )
                        content_type = f"image/{ext}" if ext != 'jpg' else 'image/jpeg'
                        s3.put_object(
                            Bucket=r2_bucket,
                            Key=f"scans/{filename}",
                            Body=img_bytes,
                            ContentType=content_type
                        )
                        if r2_domain:
                            public_url = f"{r2_domain}/scans/{filename}"
                        else:
                            public_url = f"{r2_endpoint}/{r2_bucket}/scans/{filename}"
                    except Exception as r2_err:
                        print(f"R2 upload failed, using local: {r2_err}")

                self.send_json({
                    'success': True,
                    'url': public_url,
                    'card_name': card_name,
                    'filename': filename
                })
            except Exception as e:
                self.send_error_json(500, f'Error saving uploaded card image: {e}')
            return

        # 2. API: Submit Community Scan (Stores in community_scans.json)
        if path == '/api/submit-community-scan':
            card_name = req_data.get('card_name', '').strip()
            set_code = req_data.get('set', '').strip().lower()
            collector_num = str(req_data.get('collector_number', '')).strip().lower()
            lang = req_data.get('lang', 'ja').strip().lower()
            image_url = req_data.get('image_url', '').strip()
            printed_name = req_data.get('printed_name', '').strip() or card_name

            if not card_name or not set_code or not image_url:
                self.send_error_json(400, 'Missing required fields (card_name, set, image_url)')
                return

            card_key = f"{set_code}_{collector_num}_{lang}"
            scan_data = {
                'name': card_name,
                'set': set_code,
                'collector_number': collector_num,
                'lang': lang,
                'printed_name': printed_name,
                'image_url': image_url,
                'image_large': image_url,
                'submitted_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'is_premodern': True,
                'is_retro': True
            }
            success = scryfall_client.save_community_scan(card_key, scan_data)
            if success:
                self.send_json({'success': True, 'key': card_key, 'scan': scan_data})
            else:
                self.send_error_json(500, 'Failed to save community scan')
            return

        # 2. API: Parse Deck
        if path == '/api/parse-deck':
            text = req_data.get('text', '').strip()
            deck_url = req_data.get('url', '').strip() or req_data.get('moxfield_url', '').strip()
            deck_name = 'Premodern Deck'
            deck_format = 'premodern'

            mainboard_items = []
            sideboard_items = []

            # URL Import (Moxfield, TopDeck.gg, Archidekt, MTGGoldfish, MTGTop8, Cube Cobra, Pastebin, etc.)
            if deck_url:
                try:
                    parsed_deck = deck_parser.fetch_deck_from_url(deck_url)
                    deck_name = parsed_deck.get('name', 'Imported Deck')
                    deck_format = parsed_deck.get('format', 'premodern')
                    mainboard_items = parsed_deck.get('mainboard', [])
                    sideboard_items = parsed_deck.get('sideboard', [])
                except Exception as e:
                    self.send_error_json(400, f'Failed to import deck from URL: {e}')
                    return
            # Text Input
            elif text:
                parsed_text = deck_parser.parse_decklist_text(text)
                mainboard_items = parsed_text['mainboard']
                sideboard_items = parsed_text['sideboard']
            else:
                self.send_error_json(400, 'Please provide either deck text or a deck URL.')
                return

            if not mainboard_items and not sideboard_items:
                self.send_error_json(400, 'No cards could be parsed from the provided input.')
                return

            # Resolve cards via Scryfall
            all_items = mainboard_items + sideboard_items
            resolved_map = scryfall_client.resolve_deck_cards(all_items)

            # Build mainboard groups
            main_groups = []
            for i, it in enumerate(mainboard_items):
                key = (it['name'], it.get('set'), it.get('collector_number'), it.get('scryfall_id'))
                card_data = resolved_map.get(key)
                if not card_data:
                    card_data = scryfall_client.resolve_single_card(it)
                main_groups.append({
                    'name': it['name'],
                    'quantity': it['quantity'],
                    'card_data': card_data,
                    'group_id': f'main_{i}'
                })

            # Build sideboard groups
            sb_groups = []
            for i, it in enumerate(sideboard_items):
                key = (it['name'], it.get('set'), it.get('collector_number'), it.get('scryfall_id'))
                card_data = resolved_map.get(key)
                if not card_data:
                    card_data = scryfall_client.resolve_single_card(it)
                sb_groups.append({
                    'name': it['name'],
                    'quantity': it['quantity'],
                    'card_data': card_data,
                    'group_id': f'sb_{i}'
                })

            # Pack boards
            layout = req_data.get('layout', 'classic')
            stack_basics = bool(req_data.get('stack_basics', False))
            stack_all_multiples = bool(req_data.get('stack_all_multiples', False))
            packed_mb, packed_sb = grid_packer.pack_deck(
                main_groups, sb_groups,
                layout=layout,
                stack_basics=stack_basics,
                stack_all_multiples=stack_all_multiples
            )

            response = {
                'name': deck_name,
                'format': deck_format,
                'layout': layout,
                'mainboard': packed_mb,
                'sideboard': packed_sb,
                'main_groups': main_groups,
                'sb_groups': sb_groups,
                'total_main': sum(g['quantity'] for g in main_groups),
                'total_sb': sum(g['quantity'] for g in sb_groups)
            }
            self.send_json(response)
            return

        # 3. API: Repack Grid (Instant toggle without calling Scryfall)
        if path == '/api/repack-grid':
            main_groups = req_data.get('main_groups', [])
            sb_groups = req_data.get('sb_groups', [])
            layout = req_data.get('layout', 'classic')
            stack_basics = bool(req_data.get('stack_basics', False))
            stack_all_multiples = bool(req_data.get('stack_all_multiples', False))
            packed_mb, packed_sb = grid_packer.pack_deck(
                main_groups, sb_groups,
                layout=layout,
                stack_basics=stack_basics,
                stack_all_multiples=stack_all_multiples
            )
            self.send_json({
                'layout': layout,
                'mainboard': packed_mb,
                'sideboard': packed_sb,
                'total_main': sum(g['quantity'] for g in main_groups),
                'total_sb': sum(g['quantity'] for g in sb_groups)
            })
            return

        # 4. API: Client Error Logging
        if path == '/api/client-error':
            msg = req_data.get('msg', 'unknown')
            url = req_data.get('url', '')
            line = req_data.get('line', '')
            col = req_data.get('col', '')
            stack = req_data.get('stack', '')
            print(f"\n[CLIENT ERROR REPORTED] {msg} at {url}:{line}:{col}")
            if stack:
                print(f"[CLIENT STACK] {stack}\n")
            self.send_json({'status': 'logged'})
            return

        self.send_error_json(404, f'Unknown POST endpoint: {path}')

    def serve_file(self, filepath: str, content_type: str, filename: str = None):
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            if filename or filepath.endswith('.zip'):
                fn = filename or os.path.basename(filepath)
                self.send_header('Content-Disposition', f'attachment; filename="{fn}"')
            # Ensure HTML, JS and CSS are never cached stale by browser
            if any(filepath.endswith(ext) for ext in ('.html', '.js', '.css', '.json')):
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error_json(500, f'Error serving file: {e}')

    def send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: int, message: str):
        self.send_json({'error': message, 'status': status}, status=status)

def run_server(port=8080):
    server_address = ('0.0.0.0', port)
    httpd = ThreadingHTTPServer(server_address, DeckVisualizerHandler)
    print(f'MTG Deck Visualizer running at http://0.0.0.0:{port}')
    httpd.serve_forever()

if __name__ == '__main__':
    # Support dynamic PORT environment variable (Render, Railway, Heroku, Cloud Run)
    env_port = os.environ.get('PORT')
    if env_port:
        port = int(env_port)
    elif len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8080
    run_server(port)
