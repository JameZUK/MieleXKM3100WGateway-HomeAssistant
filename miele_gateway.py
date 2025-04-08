import os
import re
import json
import hmac
import hashlib
import ipaddress
from flask import Flask, request, jsonify, Response
import requests as req
from datetime import datetime, timezone # Ensure timezone aware datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import traceback # Added for potentially better error logging

# --- Initialize Flask App FIRST ---
app = Flask(__name__)

# --- Configuration ---
# Debug flag - Set to True for verbose logging AND printing full keys on startup
debug_log = True # <<< SET TO True TO ENABLE DEBUG LOGGING AND KEY PRINTING >>>

# Group Key and Group ID from environment variables or default values
# Ensure your actual keys are set as environment variables for security
group_key_hex = os.environ.get('GROUP_KEY', '00' * 64) # Example: 64 zero bytes (invalid)
group_id_hex = os.environ.get('GROUP_ID', '00' * 8)   # Example: 8 zero bytes (invalid)

try:
    group_key = bytes.fromhex(group_key_hex)
    group_id = bytes.fromhex(group_id_hex)
    if len(group_key) != 64:
        print("Warning: GROUP_KEY length is not 64 bytes (128 hex chars).")
    if len(group_id) != 8:
        print("Warning: GROUP_ID length is not 8 bytes (16 hex chars).")
except ValueError:
    print("Error: GROUP_KEY or GROUP_ID environment variables contain invalid hex characters.")
    # Handle error appropriately, e.g., exit or use placeholder that signals an error
    group_key = bytes(64) # Use placeholder on error
    group_id = bytes(8)   # Use placeholder on error

# Standard Miele Accept header
accept_header = 'application/vnd.miele.v1+json'

# --- Helper Functions ---
def get_current_time_in_http_format():
    """Generates the current time in UTC RFC 7231 format."""
    return datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')

def is_valid_host(host):
    """Validates if the host string is a valid hostname or IP address."""
    if not host: return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        hostname_regex = re.compile(
            r'^(([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
        )
        return len(host) <= 253 and re.match(hostname_regex, host) is not None

def decrypt(payload, group_key, signature_hex):
    """
    Decrypts the payload using AES-256-CBC with key/IV derived from group_key
    and the response signature, using standard finalization for padding.
    """
    if len(group_key) < 32: raise ValueError("Group key too short (< 32 bytes) to derive AES-256 key")
    key = group_key[:32]
    try: iv_buf = bytes.fromhex(signature_hex)
    except ValueError: raise ValueError("Invalid hex format in server signature for IV derivation")
    if len(iv_buf) < 16: raise ValueError("Server signature too short (< 16 bytes) to derive 16-byte IV")
    iv = iv_buf[:16]

    if debug_log:
        print(f"-- Decryption Start --")
        print(f"Using Key (first 4 bytes): {key[:4].hex()}...")
        print(f"Using IV: {iv.hex()}")
        print(f"Ciphertext length: {len(payload)}")
        print(f"Ciphertext sample (first 32 bytes): {payload[:32].hex()}")
    try:
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(payload) + decryptor.finalize()
        if debug_log:
            print(f"Plaintext length after finalize: {len(decrypted_data)}")
            sample = decrypted_data[:200].decode('utf-8', errors='replace')
            print(f"Plaintext sample (first 200 bytes decoded): {sample}{'...' if len(decrypted_data)>200 else ''}")
            print(f"-- Decryption End --")
        return decrypted_data
    except ValueError as e:
        print(f"Decryption error (likely padding/key/IV issue): {e}")
        raise

def iterate_to_all_hrefs(obj, host, base_path):
    """
    Recursively traverses JSON data (dicts/lists) and replaces 'href' values
    with full proxy links suitable for the '/explore/' route.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == 'href' and isinstance(value, str) and value:
                full_target_path = f"{base_path.rstrip('/')}/{value.lstrip('/')}"
                proxy_link = f'/explore/{host}/{full_target_path.lstrip("/")}'
                obj[key] = f'<a href="{proxy_link}">{value}</a>'
            else: iterate_to_all_hrefs(value, host, base_path)
    elif isinstance(obj, list):
        for item in obj: iterate_to_all_hrefs(item, host, base_path)

# --- Route Definitions ---
@app.route('/init/<path:resource>', methods=['GET'])
def init(resource):
    """Handles the initial commissioning request to the device."""
    if debug_log: print(f"\n=== INIT Request Received ===\nRequest URL: {request.url}")
    path_parts = resource.strip('/').split('/')
    if not path_parts: return jsonify({'error': 'Missing host in path'}), 400
    host = path_parts[0]
    if not is_valid_host(host): return jsonify({'error': f"Invalid host format provided: '{host}'"}), 400
    init_resource_path = '/Security/Commissioning/'
    target_url = f'http://{host}{init_resource_path}'
    try:
        current_time_gmt = get_current_time_in_http_format()
        headers = {
            'Accept': accept_header, 'Date': current_time_gmt,
            'User-Agent': 'Miele@mobile 2.3.3 Android', 'Host': host,
            'Accept-Encoding': 'gzip', 'Content-Type': 'application/json; charset=utf-8'
        }
        payload_data = { 'GroupID': group_id.hex().upper(), 'GroupKey': group_key.hex().upper() }
        if debug_log:
            print(f"Target URL: PUT {target_url}")
            print(f"Request Headers: {json.dumps(headers, indent=2)}")
            print(f"Request Body: {json.dumps(payload_data, indent=2)}")
        response = req.put(target_url, headers=headers, json=payload_data, timeout=20)
        if debug_log:
             print(f"--- INIT Response ---\nStatus Code: {response.status_code}")
             print(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
             try: print(f"Response JSON: {response.json()}")
             except json.JSONDecodeError: print(f"Response Content (non-JSON or empty): {response.text}")
        response.raise_for_status()
        return response.content, response.status_code, response.headers.items()
    except req.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else 500
        error_message = f"HTTP error from device: {status_code}"
        details = e.response.text if e.response is not None and e.response.text else 'No details provided.'
        print(f'HTTP error during /init request to {host}: {status_code} {e.response.reason if e.response is not None else ""}\nResponse body: {details}')
        return jsonify({'error': error_message, 'details': details}), status_code
    except req.exceptions.Timeout: print(f'Timeout during /init request to {host}'); return jsonify({'error': 'Device communication timed out'}), 504
    except req.exceptions.ConnectionError: print(f'Connection error during /init request to {host}'); return jsonify({'error': 'Device connection refused or unavailable'}), 503
    except req.exceptions.RequestException as e: print(f'Network request error during /init to {host}: {e}'); return jsonify({'error': f'Network request failed: {e}'}), 500
    except Exception as e: print(f'Unexpected error during /init: {e}'); traceback.print_exc(); return jsonify({'error': 'Internal Server Error occurred during initialization'}), 500

@app.route('/explore/<path:resource>', methods=['GET'])
def explore(resource):
    """Route specifically for browser-friendly exploration."""
    return main_route(resource, explore_mode=True)

@app.route('/', defaults={'resource': ''})
@app.route('/<path:resource>', methods=['GET'])
def main_route(resource, explore_mode=False):
    """Main route for GET requests, handling auth, decryption, and response formatting."""
    if resource == 'favicon.ico': return '', 204
    is_explore_request = explore_mode
    if debug_log: print(f"\n=== {'EXPLORE ' if is_explore_request else ''}Request Received ===\nRequest URL: {request.url}\nRaw resource path received: /{resource}")
    path_parts = resource.strip('/').split('/')
    if not path_parts or not path_parts[0]: return jsonify({'error': 'Missing host in request path. Use format /<host>/<device_path>'}), 400
    host = path_parts[0]
    if not is_valid_host(host): return jsonify({'error': f"Invalid host format provided: '{host}'"}), 400
    # Path Handling (Trailing Slash Fix)
    resource_path_part = '/'.join(path_parts[1:])
    original_request_path_had_trailing_slash = resource.endswith('/')
    resource_path_on_device = "/" + resource_path_part
    current_path_has_trailing_slash = resource_path_on_device.endswith('/')
    if original_request_path_had_trailing_slash and not current_path_has_trailing_slash and resource_path_on_device != '/': resource_path_on_device += '/'
    elif not original_request_path_had_trailing_slash and current_path_has_trailing_slash and resource_path_on_device != '/': resource_path_on_device = resource_path_on_device.rstrip('/')
    if len(path_parts) == 1 and original_request_path_had_trailing_slash: resource_path_on_device = '/'
    elif len(path_parts) == 1 and not original_request_path_had_trailing_slash: resource_path_on_device = '/'
    if debug_log: print(f"Target Host: {host}\nOriginal had trailing slash: {original_request_path_had_trailing_slash}\nFinal Target Resource Path (used for signing & URL): '{resource_path_on_device}'")
    try:
        current_time_gmt = get_current_time_in_http_format()
        # Prepare Auth Signature (ASCII encoding)
        signing_string = f'GET\n{host}{resource_path_on_device}\n\n{accept_header}\n{current_time_gmt}\n'
        try: signing_bytes = signing_string.encode('ascii'); #if debug_log: print("Using ASCII encoding for signing string.") # Redundant with raw print below
        except UnicodeEncodeError: print("Warning: Signing string non-ASCII, falling back to UTF-8."); signing_bytes = signing_string.encode('utf-8')
        signature_bytes = hmac.new(group_key, signing_bytes, hashlib.sha256).digest()
        signature_hex = signature_bytes.hex().upper()
        auth_header_value = f'MieleH256 {group_id.hex().upper()}:{signature_hex}'
        # Prepare Headers
        headers = { 'Accept': accept_header, 'Date': current_time_gmt, 'User-Agent': 'Miele@mobile 2.3.3 Android', 'Host': host, 'Authorization': auth_header_value, 'Accept-Encoding': 'gzip' }
        target_url = f'http://{host}{resource_path_on_device}'
        if debug_log: print(f"Target URL: GET {target_url}\nRequest Headers: {json.dumps(headers, indent=2)}\nString Signed (raw):\n{signing_string.strip()}")
        # Send Request
        response = req.get(target_url, headers=headers, timeout=20)
        if debug_log: print(f"--- Device Response ---\nStatus Code: {response.status_code}\nResponse Headers: {json.dumps(dict(response.headers), indent=2)}")
        response.raise_for_status()
        # Process Success Response
        if response.status_code == 204 or not response.content:
             if debug_log: print("Received 204 No Content or empty body.")
             if is_explore_request: return Response(f"<html><body><h1>{response.status_code} No Content</h1><p>Path: {host}{resource_path_on_device}</p></body></html>", mimetype='text/html', status=response.status_code)
             else: return Response(status=204, mimetype='application/json')
        # Decrypt Response
        response_signature_header = response.headers.get('X-Signature', None)
        if not response_signature_header: print("Error: Missing X-Signature header"); return jsonify({'error': 'Missing required X-Signature header from device'}), 500
        sig_parts = response_signature_header.split(':')
        if len(sig_parts) != 2 or not sig_parts[0].startswith('MieleH256 '): print(f"Error: Invalid X-Signature header format: '{response_signature_header}'"); return jsonify({'error': 'Invalid X-Signature header format from device'}), 500
        server_signature_hex = sig_parts[1]
        decrypted_bytes = decrypt(response.content, group_key, server_signature_hex)
        decrypted_str = decrypted_bytes.decode('utf-8', errors='replace')
        # Return Based on Mode
        if is_explore_request:
            try:
                json_data = json.loads(decrypted_str)
                iterate_to_all_hrefs(json_data, host, resource_path_on_device)
                html_content = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Explore: {host}{resource_path_on_device}</title><style>body{{font-family:sans-serif;margin:1em;}} h1{{border-bottom:1px solid #ccc;}} pre{{white-space:pre-wrap;background:#f0f0f0;padding:1em;border:1px solid #ddd;}} a{{color:blue;}}</style></head><body><h1>{host}{resource_path_on_device}</h1><pre>{json.dumps(json_data, indent=2)}</pre></body></html>"""
                return Response(html_content, mimetype='text/html')
            except json.JSONDecodeError as e:
                print(f"Warning: Decrypted data for explore mode is not valid JSON: {e}")
                html_content = f"""<!DOCTYPE html><html lang="en"><head><title>Explore Error: Not JSON</title><style>.error{{color:red;}} body{{font-family:monospace;white-space:pre;}}</style></head><body><h1>Error: Response was not valid JSON</h1><p class="error">Path: {host}{resource_path_on_device}</p><hr><p>{decrypted_str}</p></body></html>"""
                return Response(html_content, mimetype='text/html', status=200)
        else: return Response(decrypted_str, mimetype='application/json')
    # Error Handling
    except req.exceptions.HTTPError as e: status_code = e.response.status_code if e.response is not None else 500; error_message = f"HTTP error from device: {status_code}"; details = e.response.text if e.response is not None and e.response.text else 'No details provided.'; print(f'HTTP error during {"explore " if is_explore_request else ""}request to {host}{resource_path_on_device}: {status_code} {e.response.reason if e.response is not None else ""}\nResponse body: {details}'); return jsonify({'error': error_message, 'details': details}), status_code
    except req.exceptions.Timeout: print(f'Timeout during {"explore " if is_explore_request else ""}request to {host}{resource_path_on_device}'); return jsonify({'error': 'Device communication timed out'}), 504
    except req.exceptions.ConnectionError: print(f'Connection error during {"explore " if is_explore_request else ""}request to {host}{resource_path_on_device}'); return jsonify({'error': 'Device connection refused or unavailable'}), 503
    except req.exceptions.RequestException as e: print(f'Network request error during {"explore " if is_explore_request else ""}request to {host}{resource_path_on_device}: {e}'); return jsonify({'error': f'Network request failed: {e}'}), 500
    except ValueError as e: print(f"Data processing error (decrypt/JSON/path): {e}"); traceback.print_exc(); return jsonify({'error': f'Data processing error: {e}'}), 500
    except Exception as e: print(f'Unexpected error during {"explore " if is_explore_request else ""}request: {e}'); traceback.print_exc(); return jsonify({'error': 'Internal Server Error occurred'}), 500

# --- Main Execution ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print(f"--- Miele Proxy Server Starting ---")
    print(f"Listening on: http://0.0.0.0:{port}")

    # --- MODIFIED: Print full keys only if debug_log is True ---
    if debug_log:
        # WARNING: Printing full keys to log can be a security risk!
        print(f"Using Group ID (Debug): {group_id_hex}") # Print full hex ID
        print(f"Using Group Key (Debug): {group_key_hex}") # Print full hex key
    else:
        # Original masked output for non-debug mode
        print(f"Using Group ID: ...{group_id.hex()[-4:].upper() if len(group_id)==8 else 'Invalid Length'}")
        print(f"Using Group Key: {'Set (length OK)' if len(group_key)==64 else 'Invalid Length or Default'}")
    # --- END MODIFICATION ---

    print(f"Debug Logging: {'Enabled' if debug_log else 'Disabled'}")
    print(f"---------------------------------")
    # Set debug=False for production/stable use
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=True)
