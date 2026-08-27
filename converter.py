import json
import re
import time
import requests
from bs4 import BeautifulSoup
import tinycss2
import argparse
from urllib.parse import urlparse

# Try importing undetected_chromedriver and standard selenium
try:
    import undetected_chromedriver as uc
    HAS_UC = True
except ImportError:
    HAS_UC = False

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class FontExtractor:
    FONT_BASE_URL = 'https://font-public.canva.com/'
    WEIGHT_MAP = {
        'Thin': 100,
        'ExtraLight': 200,
        'Light': 300,
        'Regular': 400,
        'Medium': 500,
        'SemiBold': 600,
        'Bold': 700,
        'ExtraBold': 800,
        'Black': 900
    }
    STYLE_MAP = {
        'Italic': 'italic',
        'Normal': 'normal'
    }
    FONT_FORMATS = ['woff2', 'ttf', 'woff']

    def __init__(self, html_content):
        self.html_content = html_content

    def extract_font_face_rules(self):
        soup = BeautifulSoup(self.html_content, 'html.parser')
        font_face_rules = []
        seen_rules = set()

        for element in soup.find_all(style=True):
            font_family = self._extract_font_family(element['style'])
            if font_family:
                print(f"Found font family: {font_family}")
                font_links = self._find_font_links(font_family)
                for link, weight, style, format_type in font_links:
                    rule = (
                        f"@font-face {{\n"
                        f"  font-family: '{font_family}';\n"
                        f"  src: url('{link}') format('{format_type}');\n"
                        f"  font-weight: {weight};\n"
                        f"  font-style: {style};\n"
                        f"}}\n"
                    )
                    if rule not in seen_rules:
                        seen_rules.add(rule)
                        font_face_rules.append(rule)
                        print(f"Added @font-face rule for: {font_family} ({weight}, {style}, {format_type})")
        return font_face_rules

    def _extract_font_family(self, style):
        # Matches font-family: "Font Name", font-family: 'Font Name', or font-family: Font Name
        match = re.search(r"font-family:\s*['\"]?([^;'\"\s,]+(?: [^;'\"\s,]+)*)['\"]?", style, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _find_font_links(self, font_family):
        font_family_encoded = font_family.replace(' ', '/')
        font_links = []

        pattern = re.compile(rf"{re.escape(self.FONT_BASE_URL + font_family_encoded)}/[^\s/\"']+\.({'|'.join(self.FONT_FORMATS)})", re.IGNORECASE)

        for match in pattern.finditer(self.html_content):
            href = match.group(0)
            weight, style = self._extract_font_weight_and_style(href)
            format_type = href.split('.')[-1].lower()
            font_links.append((href, weight, style, format_type))

        return font_links

    def _extract_font_weight_and_style(self, font_filename):
        weight = 'normal'
        style = 'normal'
        for weight_name, weight_value in FontExtractor.WEIGHT_MAP.items():
            if weight_name.lower() in font_filename.lower():
                weight = weight_value
                break
        for style_name, style_value in FontExtractor.STYLE_MAP.items():
            if style_name.lower() in font_filename.lower():
                style = style_value
                break
        return weight, style


class BlobToSVGConverter:
    BLOB_URL_PATTERN = r'blob:https?://'

    def __init__(self, driver):
        self.driver = driver

    def replace_images_with_svg_or_base64(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        img_tags = soup.find_all('img', src=re.compile(self.BLOB_URL_PATTERN))

        if not img_tags:
            return html_content

        for img in img_tags:
            blob_url = img['src']
            try:
                content, is_svg = self._fetch_blob_content(blob_url)
                if content and not str(content).startswith('Error:'):
                    if is_svg:
                        svg_soup = BeautifulSoup(content, 'html.parser')
                        svg = svg_soup.find('svg')
                        if svg:
                            img.replace_with(svg)
                    else:
                        img['src'] = content
                else:
                    print(f"Could not convert blob URL {blob_url}: {content}")
            except Exception as e:
                print(f"Failed to convert blob image {blob_url}: {e}")

        return str(soup)

    def _fetch_blob_content(self, blob_url):
        script = f"""
            var callback = arguments[arguments.length - 1];
            fetch("{blob_url}")
                .then(response => response.blob())
                .then(blob => {{
                    var reader = new FileReader();
                    reader.onloadend = () => callback([reader.result, blob.type === 'image/svg+xml']);
                    if (blob.type === 'image/svg+xml') {{
                        reader.readAsText(blob);
                    }} else {{
                        reader.readAsDataURL(blob);
                    }}
                }})
                .catch(error => callback(['Error: ' + error.message, false]));
        """
        try:
            self.driver.set_script_timeout(10)
            return self.driver.execute_async_script(script)
        except Exception as e:
            return f"Error: {e}", False


class CSSOptimizer:
    def __init__(self, html_content, css_content):
        self.html_content = html_content
        self.css_content = css_content

    def get_html_selectors(self):
        soup = BeautifulSoup(self.html_content, 'html.parser')
        selectors = set()
        for element in soup.find_all(True):
            selectors.add(element.name)
            classes = element.get("class", [])
            if isinstance(classes, list):
                for class_ in classes:
                    selectors.add(f".{class_}")
            elif isinstance(classes, str):
                selectors.add(f".{classes}")

            id_attr = element.get("id")
            if id_attr:
                if isinstance(id_attr, list):
                    for id_ in id_attr:
                        selectors.add(f"#{id_}")
                elif isinstance(id_attr, str):
                    selectors.add(f"#{id_attr}")

            # Collect data attributes
            for attr in element.attrs:
                if attr.startswith('data-'):
                    selectors.add(attr)

        return selectors

    def optimize(self):
        if not self.css_content.strip():
            return ""

        html_selectors = self.get_html_selectors()
        rules = tinycss2.parse_stylesheet(self.css_content, skip_comments=True)
        optimized_rules = []

        for rule in rules:
            if rule.type == 'error':
                continue
            elif rule.type == 'at-rule':
                # Retain font-face, keyframes, media, supports, root declarations
                prelude = tinycss2.serialize(rule.prelude).strip()
                content = tinycss2.serialize(rule.content) if rule.content else ""
                keyword = getattr(rule, 'at_keyword', getattr(rule, 'lower_at_keyword', ''))
                if content:
                    optimized_rules.append(f"@{keyword} {prelude} {{{content}}}")
                else:
                    optimized_rules.append(f"@{keyword} {prelude};")
            elif rule.type == 'qualified-rule':
                prelude = tinycss2.serialize(rule.prelude).strip()
                content = tinycss2.serialize(rule.content) if rule.content else ""

                # Preserve global/root selectors
                is_global = any(g in prelude for g in [':root', 'html', 'body', '*', '@font-face'])
                is_matched = is_global or any(sel in prelude for sel in html_selectors if len(sel) > 1)

                if is_matched:
                    optimized_rules.append(f"{prelude} {{{content}}}")

        return '\n'.join(optimized_rules)


class CanvaConverter:
    FALLBACK_SELECTORS = [
        '[data-element-type="page"]',
        '[class*="pageContainer"]',
        '[class*="design-container"]',
        '.uPeMFQ',
        'main[role="main"]',
        'main',
        '#root',
        'body'
    ]
    DEFAULT_CSS_URL = 'https://static.canva.com/web/36b99f3659b2c9ed.ltr.css'

    def __init__(self, driver, url, output_file='new_page.html'):
        self.driver = driver
        self.url = url
        self.output_file = output_file

    def grab_html_and_wait(self):
        print(f"Navigating to {self.url}...")
        self.driver.get(self.url)
        self.driver.set_page_load_timeout(30)
        
        # Wait for Canva page elements to start rendering
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            time.sleep(5)  # Allow dynamic JS/Canvas elements to settle
        except Exception as e:
            print(f"Warning during page load wait: {e}")

        return self.driver.page_source

    def grab_selected_html(self, page_source):
        soup = BeautifulSoup(page_source, 'html.parser')
        
        for selector in self.FALLBACK_SELECTORS:
            elements = soup.select(selector)
            if elements:
                print(f"Found match using selector: '{selector}' ({len(elements)} element(s))")
                if len(elements) == 1:
                    return str(elements[0])
                else:
                    wrapper = soup.new_tag('div', **{'class': 'canva-exported-pages'})
                    for el in elements:
                        wrapper.append(el)
                    return str(wrapper)

        print("Warning: No specific design container found. Exporting full <body>.")
        body = soup.find('body')
        return str(body) if body else page_source

    def extract_live_css(self):
        print("Extracting live CSS from browser DOM...")
        css_blocks = []

        # 1. Inline <style> tags in DOM
        try:
            style_elements = self.driver.find_elements(By.TAG_NAME, 'style')
            for el in style_elements:
                content = el.get_attribute('innerText') or el.get_attribute('textContent') or ''
                if content.strip():
                    css_blocks.append(content)
        except Exception as e:
            print(f"Error reading inline <style> tags: {e}")

        # 2. External <link rel="stylesheet"> tags
        try:
            link_elements = self.driver.find_elements(By.XPATH, '//link[@rel="stylesheet"]')
            for link in link_elements:
                href = link.get_attribute('href')
                if href and href.startswith('http'):
                    try:
                        resp = requests.get(href, timeout=5)
                        if resp.status_code == 200:
                            css_blocks.append(resp.text)
                    except Exception as err:
                        print(f"Could not download external CSS from {href}: {err}")
        except Exception as e:
            print(f"Error fetching external stylesheet links: {e}")

        # 3. Fallback to default static CSS if no live styles found
        if not css_blocks:
            try:
                resp = requests.get(self.DEFAULT_CSS_URL, timeout=5)
                if resp.status_code == 200:
                    css_blocks.append(resp.text)
            except Exception as e:
                print(f"Could not fetch fallback CSS URL: {e}")

        return '\n'.join(css_blocks)

    def parse_and_create_new_html(self, selected_html_content, css_content, font_face_rules):
        new_html_content = (
            f"<!DOCTYPE html>\n"
            f"<html>\n<head>\n"
            f"<meta charset=\"UTF-8\">\n"
            f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            f"<title>Converted Canva Design</title>\n"
            f"<style>\n{''.join(font_face_rules)}\n{css_content}\n</style>\n"
            f"</head>\n"
            f"<body>\n{selected_html_content}\n</body>\n</html>"
        )
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(new_html_content)
        print(f"Successfully saved converted output to '{self.output_file}'!")

    def perform(self):
        full_html_content     = self.grab_html_and_wait()
        selected_html_content = self.grab_selected_html(full_html_content)
        font_extractor        = FontExtractor(full_html_content)
        font_face_rules       = font_extractor.extract_font_face_rules()
        css_content           = self.extract_live_css()
        blob_to_svg_converter = BlobToSVGConverter(self.driver)
        html_with_svg         = blob_to_svg_converter.replace_images_with_svg_or_base64(selected_html_content)
        css_optimizer         = CSSOptimizer(selected_html_content, css_content)
        optimized_css         = css_optimizer.optimize()

        self.parse_and_create_new_html(html_with_svg, optimized_css, font_face_rules)


def parse_and_validate_arguments():
    parser = argparse.ArgumentParser(description='Convert Canva design to HTML/CSS.')
    parser.add_argument('--url', help='URL of the Canva design', required=True)
    parser.add_argument('--cookies', help='Path to the cookies JSON file (optional)', required=False, default=None)
    parser.add_argument('--output', help='Path to output HTML file (default: output.html)', required=False, default='output.html')
    parser.add_argument('--headless', help='Run browser in headless mode', action='store_true')
    args = parser.parse_args()

    return args.url, args.cookies, args.output, args.headless


def initialize_driver(headless=False):
    print("Initializing Chrome browser driver...")
    options = Options()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')

    if HAS_UC:
        try:
            uc_options = uc.ChromeOptions()
            if headless:
                uc_options.add_argument('--headless=new')
            uc_options.add_argument('--no-sandbox')
            uc_options.add_argument('--disable-dev-shm-usage')
            uc_options.add_argument('--window-size=1920,1080')
            return uc.Chrome(use_subprocess=True, options=uc_options)
        except Exception as e:
            print(f"Undetected Chromedriver notice: {e}")
            print("Using standard Selenium Chrome driver...")

    return webdriver.Chrome(options=options)


def load_cookies(driver, cookies_file, url):
    if not cookies_file:
        return

    print(f"Loading cookies from '{cookies_file}'...")
    try:
        with open(cookies_file, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
    except FileNotFoundError:
        print(f"Error: The cookies file '{cookies_file}' was not found.")
        return
    except Exception as e:
        print(f"Error reading cookies file: {e}")
        return

    driver.get(url)
    time.sleep(2)

    allowed_keys = {'name', 'value', 'domain', 'path', 'expiry', 'httpOnly', 'secure', 'sameSite'}

    for cookie in cookies:
        clean_cookie = {k: v for k, v in cookie.items() if k in allowed_keys}
        
        if 'expirationDate' in cookie and 'expiry' not in clean_cookie:
            clean_cookie['expiry'] = int(cookie['expirationDate'])
            
        if 'sameSite' in clean_cookie:
            ss = str(clean_cookie['sameSite']).lower()
            if ss in ('no_restriction', 'unspecified', 'none'):
                clean_cookie['sameSite'] = 'None'
            elif ss == 'lax':
                clean_cookie['sameSite'] = 'Lax'
            elif ss == 'strict':
                clean_cookie['sameSite'] = 'Strict'
            else:
                del clean_cookie['sameSite']

        try:
            driver.add_cookie(clean_cookie)
        except Exception as e:
            # Domain mismatches or expired cookies are common; skip gracefully
            pass

    print("Cookies loaded.")


if __name__ == '__main__':
    url, cookies_file, output_file, headless = parse_and_validate_arguments()
    driver = initialize_driver(headless=headless)
    
    try:
        if cookies_file:
            load_cookies(driver, cookies_file, 'https://www.canva.com/')

        converter = CanvaConverter(driver, url, output_file=output_file)
        converter.perform()
    finally:
        driver.quit()
