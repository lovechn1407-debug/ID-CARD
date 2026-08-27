import os
import json
from flask import Flask, render_template_string, send_from_directory, request, jsonify, Response

app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def home():
    """Serves the main index.html design over HTTP/HTTPS to eliminate file:// restrictions."""
    if os.path.exists('index.html'):
        return send_from_directory('.', 'index.html')
    elif os.path.exists('design.html'):
        return send_from_directory('.', 'design.html')
    return "<h1>Canva to HTML Server</h1><p>No template found yet.</p>"

@app.route('/design.html')
def design_page():
    return send_from_directory('.', 'design.html')

@app.route('/favicon.ico')
def favicon():
    """Returns a simple SVG favicon to resolve 404 errors."""
    svg_icon = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <rect width="100" height="100" rx="20" fill="#6366F1"/>
        <text x="50" y="68" font-size="55" font-family="sans-serif" font-weight="bold" fill="white" text-anchor="middle">ID</text>
    </svg>'''
    return Response(svg_icon, mimetype='image/svg+xml')

@app.route('/images/block/<path:filename>')
def block_images(filename):
    """Fallback handler for Canva internal relative image assets."""
    # Return transparent SVG or dark gradient background fallback
    bg_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600">
        <defs>
            <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#0f172a"/>
                <stop offset="100%" stop-color="#1e1b4b"/>
            </linearGradient>
        </defs>
        <rect width="100%" height="100%" fill="url(#g)"/>
    </svg>'''
    return Response(bg_svg, mimetype='image/svg+xml')

@app.route('/render', methods=['GET', 'POST'])
def render_jinja_route():
    """Renders index.html or design.html using Jinja2 with custom dynamic parameters."""
    template_name = request.args.get('template', 'index.html')
    if not os.path.exists(template_name):
        return jsonify({"error": f"Template '{template_name}' not found."}), 404
    
    with open(template_name, 'r', encoding='utf-8') as f:
        content = f.read()

    data = {}
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
    else:
        data = request.args.to_dict()

    # Default fallback variables for ID Card
    default_context = {
        "name": "Love Chauhan",
        "title": "Senior Software Engineer",
        "id_number": "EMP-884920",
        "department": "Engineering & AI",
        "issue_date": "2026-01-15",
        "expiry_date": "2029-01-15",
        "company_name": "CANVA TECH LABS",
        "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80"
    }
    default_context.update(data)

    try:
        rendered = render_template_string(content, **default_context)
        return rendered
    except Exception as e:
        return jsonify({"error": f"Jinja rendering error: {str(e)}"}), 500

@app.route('/health')
def health():
    return jsonify({"status": "ok", "service": "CanvaToHTML-IDCard"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
