import argparse
import json
import os
from jinja2 import Template


def render_template(template_path, output_path, context):
    """Loads a Jinja2 template HTML file, renders it with context variables, and saves the output."""
    if not os.path.exists(template_path):
        print(f"Error: Template file '{template_path}' not found.")
        return

    print(f"Reading template from '{template_path}'...")
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    template = Template(template_content)
    rendered_html = template.render(**context)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(rendered_html)

    print(f"Successfully rendered HTML saved to '{output_path}'!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Render converted Canva HTML using Jinja2 templating.')
    parser.add_argument('--template', help='Path to the HTML template file (default: design.html)', default='design.html')
    parser.add_argument('--output', help='Path to output rendered HTML file (default: rendered_output.html)', default='rendered_output.html')
    parser.add_argument('--data', help='JSON string or path to JSON file containing template variables', required=False, default='{}')

    args = parser.parse_args()

    # Parse context data
    context = {}
    if args.data:
        data_str = args.data.strip()
        if data_str.startswith('{'):
            try:
                context = json.loads(data_str)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON string: {e}")
                exit(1)
        elif os.path.exists(data_str):
            try:
                with open(data_str, 'r', encoding='utf-8') as f:
                    context = json.load(f)
            except Exception as e:
                print(f"Error reading JSON file '{data_str}': {e}")
                exit(1)
        else:
            print(f"Warning: Provided --data is neither a valid JSON string nor an existing file. Using empty context.")

    render_template(args.template, args.output, context)
