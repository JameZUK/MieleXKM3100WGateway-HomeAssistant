import os
import re
import json
import hmac
import hashlib
import ipaddress
from flask import Flask, request, jsonify, Response
import requests as req
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Initialize Flask app
app = Flask(__name__)

# Debug flag
debug_log = False

# Group Key and Group ID from environment variables or default values
group_key_hex = os.environ.get('GROUP_KEY', '00' * 64)
group_id_hex = os.environ.get('GROUP_ID', '00' * 8)

group_key = bytes.fromhex(group_key_hex)
group_id = bytes.fromhex(group_id_hex)

accept_header = 'application/vnd.miele.v1+json'

def get_current_time_in_http_format():
    return datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')

def is_valid_host(host):
    # Validates if the host is a valid hostname or IP address
    try:
        # Try to parse as an IP address
        ipaddress.ip_address(host)
        return True
    except ValueError:
        # If not an IP, check if it's a valid hostname
        # Hostname validation regex
        hostname_regex = re.compile(
            r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*'
            r'([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'
        )
        return re.match(hostname_regex, host) is not None

def decrypt(payload, group_key, signature):
    key = group_key[:len(group_key)//2]
    iv_buf = bytes.fromhex(signature)
    iv = iv_buf[:len(iv_buf)//2]

    # Append a zero byte to the payload
    padded_payload = payload + b'\x00'

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_data = decryptor.update(padded_payload)
    # Do not call decryptor.finalize() to mimic Node.js behavior
    return decrypted_data

def iterate_to_all_hrefs(obj, host, resource_path):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == 'href' and isinstance(value, str):
                obj[key] = f'<a href="/explore/{host}{resource_path}{value}">{value}</a>'
            else:
                iterate_to_all_hrefs(value, host, resource_path)
    elif isinstance(obj, list):
        for item in obj:
            iterate_to_all_hrefs(item, host, resource_path)

@app.route('/init/<path:resource>', methods=['GET'])
def init(resource):
    if debug_log:
        print(f'GET: {request.url}')

    resource_path = '/' + resource
    host_match = re.match(r'^/([^/]+)', resource_path)
    host = host_match.group(1) if host_match else ''

    if not host or not is_valid_host(host):
        return jsonify({'error': 'Invalid or missing host'}), 400

    resource_path = resource_path.replace(f'/{host}', '')

    try:
        act_date = get_current_time_in_http_format()
        url = f'http://{host}/Security/Commissioning/'
        headers = {
            'Accept': accept_header,
            'Date': act_date,
            'User-Agent': 'Miele@mobile 2.3.3 Android',
            'Host': host,
            'Accept-Encoding': 'gzip',
        }
        data = {
            'GroupID': group_id.hex().upper(),
            'GroupKey': group_key.hex().upper(),
        }
        response = req.put(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return jsonify(response.json())
    except req.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else 500
        error_message = e.response.reason if e.response else 'Initialization failed'
        print(f'HTTP error during /init request to {host}: {error_message}')
        return jsonify({'error': error_message}), status_code
    except req.exceptions.RequestException as e:
        print(f'Error during /init request to {host}: {e}')
        error_message = 'Appliance gateway is unavailable' if isinstance(e, (req.exceptions.ConnectionError, req.exceptions.Timeout)) else str(e)
        return jsonify({'error': error_message}), 500

@app.route('/explore/<path:resource>', methods=['GET'])
def explore(resource):
    return main_route(resource, explore=True)

@app.route('/<path:resource>', methods=['GET'])
def main_route(resource, explore=False):
    if request.path == '/favicon.ico':
        return '', 204

    if debug_log:
        print(f'GET: {request.url}')

    resource_path = '/' + resource

    if resource_path.startswith('/explore'):
        resource_path = resource_path.replace('/explore', '', 1)
        explore = True

    host_match = re.match(r'^/([^/]+)', resource_path)
    host = host_match.group(1) if host_match else ''

    if not host or not is_valid_host(host):
        return jsonify({'error': 'Invalid or missing host'}), 400

    resource_path = resource_path.replace(f'/{host}', '')

    try:
        act_date = get_current_time_in_http_format()
        signature_str = f'GET\n{host}{resource_path}\n\n{accept_header}\n{act_date}\n'
        signature = hmac.new(group_key, signature_str.encode('ascii'), hashlib.sha256).hexdigest().upper()

        url = f'http://{host}{resource_path}'
        headers = {
            'Accept': accept_header,
            'Date': act_date,
            'User-Agent': 'Miele@mobile 2.3.3 Android',
            'Host': host,
            'Authorization': f'MieleH256 {group_id.hex().upper()}:{signature}',
            'Accept-Encoding': 'gzip',
        }
        response = req.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        response_signature = response.headers.get('x-signature', '')
        sig_parts = response_signature.split(':')
        server_signature = sig_parts[1] if len(sig_parts) >= 2 else ''

        # Decrypt the response content
        data = decrypt(response.content, group_key, server_signature)
        data_str = data.decode('utf-8', errors='ignore').rstrip('\x00')

        if debug_log:
            print(f'Decrypted data: {data_str}')

        if explore:
            json_data = json.loads(data_str)
            iterate_to_all_hrefs(json_data, host, resource_path)
            html_content = f"""
            <html>
              <head>
                <title>Explore Miele Device</title>
                <style>
                  body {{ font-family: monospace; white-space: pre; }}
                  a {{ color: blue; text-decoration: none; }}
                  a:hover {{ text-decoration: underline; }}
                </style>
              </head>
              <body>{json.dumps(json_data, indent=4)}</body>
            </html>
            """
            return Response(html_content, mimetype='text/html')
        else:
            return Response(data_str, mimetype='application/json')
    except req.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else 500
        error_message = e.response.reason if e.response else 'Request failed'
        print(f'HTTP error during request to {host}{resource_path}: {error_message}')
        return jsonify({'error': error_message}), status_code
    except req.exceptions.RequestException as e:
        print(f'Error during request to {host}{resource_path}: {e}')
        error_message = 'Appliance gateway is unavailable' if isinstance(e, (req.exceptions.ConnectionError, req.exceptions.Timeout)) else str(e)
        return jsonify({'error': error_message}), 500
    except Exception as e:
        print(f'Unexpected error: {e}')
        return jsonify({'error': 'Internal Server Error'}), 500

if __name__ == '__main__':
    # Run the Flask app
    app.run(host='0.0.0.0', port=3000)
