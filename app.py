import os
import json
from flask import Flask, render_template_string, send_from_directory, request, jsonify

app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def home():
    """Serves the main index.html design over HTTP/HTTPS to eliminate file:// restrictions."""
    if os.path.exists('index.html'):
        return send_from_directory('.', 'index.html')
    elif os.path.exists('design.html'):
        return send_from_directory('.', 'design.html')
    return "<h1>Canva to HTML Server</h1><p>No template found yet. Run converter.py or place index.html in directory.</p>"

@app.route('/design.html')
def design_page():
    return send_from_directory('.', 'design.html')

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

    try:
        rendered = render_template_string(content, **data)
        return rendered
    except Exception as e:
        return jsonify({"error": f"Jinja rendering error: {str(e)}"}), 500

@app.route('/health')
def health():
    return jsonify({"status": "ok", "service": "CanvaToHTML"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
