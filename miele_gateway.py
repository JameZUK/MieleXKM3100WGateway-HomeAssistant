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

# Initialize Flask app
app = Flask(__name__)

# Debug flag - Set to True for verbose logging
debug_log = False

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

def get_current_time_in_http_format():
    """Generates the current time in UTC RFC 7231 format."""
    # Use timezone-aware UTC time for consistency
    return datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')

def is_valid_host(host):
    """Validates if the host string is a valid hostname or IP address."""
    if not host: # Cannot be empty
        return False
    try:
        # Try to parse as an IP address (IPv4 or IPv6)
        ipaddress.ip_address(host)
        return True
    except ValueError:
        # If not an IP, check if it's a potentially valid hostname
        # Allows domain labels (letters, digits, hyphen but not at start/end) separated by dots.
        # Max length constraints are not checked here but generally handled by OS/network stack.
        hostname_regex = re.compile(
            r'^(([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
        )
        # Check if it looks like a hostname and isn't excessively long
        return len(host) <= 253 and re.match(hostname_regex, host) is not None

# --- MODIFIED DECRYPT FUNCTION ---
def decrypt(payload, group_key, signature_hex):
    """
    Decrypts the payload using AES-256-CBC with key/IV derived from group_key
    and the response signature, using standard finalization for padding.
    """
    # Key derivation: Use the first 32 bytes (256 bits) of the group key for AES
    if len(group_key) < 32:
         raise ValueError("Group key too short (< 32 bytes) to derive AES-256 key")
    key = group_key[:32]

    # IV derivation: Use the first 16 bytes of the server's signature (from X-Signature header)
    try:
        iv_buf = bytes.fromhex(signature_hex)
    except ValueError:
        raise ValueError("Invalid hex format in server signature for IV derivation")

    # AES IV is always 16 bytes (128 bits)
    if len(iv_buf) < 16:
         raise ValueError("Server signature too short (< 16 bytes) to derive 16-byte IV")
    iv = iv_buf[:16]

    if debug_log:
        print(f"-- Decryption Start --")
        print(f"Using Key (first 4 bytes): {key[:4].hex()}...")
        print(f"Using IV: {iv.hex()}")
        print(f"Ciphertext length: {len(payload)}")
        print(f"Ciphertext sample (first 32 bytes): {payload[:32].hex()}")

    try:
        # Initialize AES-CBC Cipher from cryptography library
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()

        # Perform decryption using update() + finalize()
        # finalize() handles the removal of standard padding (e.g., PKCS#7)
        decrypted_data = decryptor.update(payload) + decryptor.finalize()

        if debug_log:
            print(f"Plaintext length after finalize: {len(decrypted_data)}")
            # Avoid printing potentially huge data, show sample
            sample = decrypted_data[:200].decode('utf-8', errors='replace')
            print(f"Plaintext sample (first 200 bytes decoded): {sample}{'...' if len(decrypted_data)>200 else ''}")
            print(f"-- Decryption End --")

        # Return the raw plaintext bytes
        return decrypted_data
    except ValueError as e:
        # This often indicates incorrect padding (if device doesn't use standard padding),
        # or potentially key/IV mismatch.
        print(f"Decryption error (likely padding/key/IV issue): {e}")
        raise # Re-raise the exception to be caught by the route handler

# --- END OF MODIFIED DECRYPT FUNCTION ---


def iterate_to_all_hrefs(obj, host, base_path):
    """
    Recursively traverses JSON data (dicts/lists) and replaces 'href' values
    with full proxy links suitable for the '/explore/' route.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == 'href' and isinstance(value, str) and value: # Process only non-empty string hrefs
                # Construct the absolute path on the target device
                # Assume href value is relative to the current base_path
                # Normalize slashes: ensure base_path ends with '/', value doesn't start with '/'
                full_target_path = f"{base_path.rstrip('/')}/{value.lstrip('/')}"

                # Create the link pointing back to our proxy's explore endpoint
                proxy_link = f'/explore/{host}/{full_target_path.lstrip("/")}'

                # Replace the original value with an HTML anchor tag
                obj[key] = f'<a href="{proxy_link}">{value}</a>'
            else:
                # Recurse into nested dictionaries or lists
                iterate_to_all_hrefs(value, host, base_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
             # Pass index for potential context if needed later, currently unused
            iterate_to_all_hrefs(item, host, base_path)


@app.route('/init/<path:resource>', methods=['GET'])
def init(resource):
    """
    Handles the initial commissioning request to the device.
    The 'resource' path part should contain the target host/IP.
    Example: /init/192.168.1.50
    """
    if debug_log:
        print(f"\n=== INIT Request Received ===")
        print(f"Request URL: {request.url}")

    # Extract host from the beginning of the 'resource' path
    path_parts = resource.strip('/').split('/')
    if not path_parts:
        return jsonify({'error': 'Missing host in path'}), 400
    host = path_parts[0]

    if not is_valid_host(host):
        return jsonify({'error': f"Invalid host format provided: '{host}'"}), 400

    # Miele commissioning endpoint path
    init_resource_path = '/Security/Commissioning/'
    target_url = f'http://{host}{init_resource_path}'

    try:
        current_time_gmt = get_current_time_in_http_format()
        # Headers required for the commissioning PUT request
        headers = {
            'Accept': accept_header,
            'Date': current_time_gmt,
            'User-Agent': 'Miele@mobile 2.3.3 Android', # User agent might matter
            'Host': host,
            'Accept-Encoding': 'gzip', # requests library handles gzip transparently
            'Content-Type': 'application/json; charset=utf-8' # Specify content type for JSON body
        }
        # Payload containing the Group ID and Key
        payload_data = {
            'GroupID': group_id.hex().upper(),
            'GroupKey': group_key.hex().upper(),
        }

        if debug_log:
            print(f"Target URL: PUT {target_url}")
            print(f"Request Headers: {json.dumps(headers, indent=2)}")
            print(f"Request Body: {json.dumps(payload_data, indent=2)}")

        # Send the PUT request
        response = req.put(target_url, headers=headers, json=payload_data, timeout=20) # Increased timeout

        if debug_log:
             print(f"--- INIT Response ---")
             print(f"Status Code: {response.status_code}")
             print(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
             # Try to print JSON response if available, handle potential non-JSON or empty
             try:
                 print(f"Response JSON: {response.json()}")
             except json.JSONDecodeError:
                 print(f"Response Content (non-JSON or empty): {response.text}")

        # Check for HTTP errors (4xx, 5xx) after logging
        response.raise_for_status()

        # Return the raw response from the device (often 204 No Content on success)
        # Forwarding headers might be useful depending on client needs
        return response.content, response.status_code, response.headers.items()

    # --- Specific Error Handling ---
    except req.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else 500
        error_message = f"HTTP error from device: {status_code}"
        details = e.response.text if e.response is not None and e.response.text else 'No details provided.'
        print(f'HTTP error during /init request to {host}: {status_code} {e.response.reason if e.response is not None else ""}')
        print(f"Response body: {details}")
        return jsonify({'error': error_message, 'details': details}), status_code
    except req.exceptions.Timeout:
        print(f'Timeout during /init request to {host}')
        return jsonify({'error': 'Device communication timed out'}), 504 # 504 Gateway Timeout
    except req.exceptions.ConnectionError:
        print(f'Connection error during /init request to {host}')
        return jsonify({'error': 'Device connection refused or unavailable'}), 503 # 503 Service Unavailable is often better here
    except req.exceptions.RequestException as e:
        print(f'Network request error during /init to {host}: {e}')
        return jsonify({'error': f'Network request failed: {e}'}), 500
    # --- General Error Handling ---
    except Exception as e:
        print(f'Unexpected error during /init: {e}')
        traceback.print_exc() # Print full traceback for unexpected errors
        return jsonify({'error': 'Internal Server Error occurred during initialization'}), 500


@app.route('/explore/<path:resource>', methods=['GET'])
def explore(resource):
    """Route specifically for browser-friendly exploration."""
    # Pass explore=True to the main handler
    return main_route(resource, explore_mode=True)

@app.route('/', defaults={'resource': ''}) # Handle root path
@app.route('/<path:resource>', methods=['GET'])
def main_route(resource, explore_mode=False):
    """
    Main route to handle GET requests, perform authentication, decryption,
    and return either raw JSON or HTML for exploration.
    """
    # Handle browser requests for favicon early
    if resource == 'favicon.ico':
        return '', 204 # No content response

    # Determine if this request came via /explore/ prefix in the original URL path
    # We use the explore_mode flag passed from the dedicated route now.
    is_explore_request = explore_mode

    if debug_log:
        print(f"\n=== {'EXPLORE ' if is_explore_request else ''}Request Received ===")
        print(f"Request URL: {request.url}")
        print(f"Resource path received: /{resource}")

    # Extract host and the actual resource path relative to the host
    path_parts = resource.strip('/').split('/')
    if not path_parts or not path_parts[0]: # Check if host part is missing
         # If resource is empty (root request), we need a host from query param? Or error?
         # Let's assume host must be in the path for now.
        return jsonify({'error': 'Missing host in request path. Use format /<host>/<device_path>'}), 400
    host = path_parts[0]

    if not is_valid_host(host):
        return jsonify({'error': f"Invalid host format provided: '{host}'"}), 400

    # The resource path on the target device starts after the host part
    # Join the remaining parts, ensuring a leading slash
    resource_path_on_device = '/' + '/'.join(path_parts[1:])

    if debug_log:
        print(f"Target Host: {host}")
        print(f"Target Resource Path: {resource_path_on_device}")

    try:
        current_time_gmt = get_current_time_in_http_format()

        # --- Prepare Authentication Signature ---
        # String to sign for GET request (no Content-Type header, empty body line)
        # Format: Method\nHost+ResourcePath\nContentTypeHeader\nAcceptHeader\nDate\nBody
        signing_string = f'GET\n{host}{resource_path_on_device}\n\n{accept_header}\n{current_time_gmt}\n'
        # Calculate HMAC-SHA256 signature using the full group key
        signature_bytes = hmac.new(group_key, signing_string.encode('utf-8'), hashlib.sha256).digest()
        signature_hex = signature_bytes.hex().upper()

        # Construct the Authorization header value
        auth_header_value = f'MieleH256 {group_id.hex().upper()}:{signature_hex}'

        # --- Prepare Request Headers ---
        headers = {
            'Accept': accept_header,
            'Date': current_time_gmt,
            'User-Agent': 'Miele@mobile 2.3.3 Android', # Consistency is key
            'Host': host, # Target host
            'Authorization': auth_header_value,
            'Accept-Encoding': 'gzip', # Let requests handle compression
        }

        target_url = f'http://{host}{resource_path_on_device}'

        if debug_log:
             print(f"Target URL: GET {target_url}")
             print(f"Request Headers: {json.dumps(headers, indent=2)}")
             print(f"String Signed:\n{signing_string.strip()}")
             # print(f"Signature Hex: {signature_hex}") # Can be verbose

        # --- Send Request to Device ---
        response = req.get(target_url, headers=headers, timeout=20) # Increased timeout

        if debug_log:
            print(f"--- Device Response ---")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")

        # Check for HTTP errors after logging
        response.raise_for_status()

        # --- Process Successful Response ---

        # Handle responses with no content (e.g., 204)
        if response.status_code == 204 or not response.content:
             if debug_log: print("Received 204 No Content or empty body. No decryption needed.")
             # Return appropriate empty response based on mode
             if is_explore_request:
                 return Response(f"<html><body><h1>{response.status_code} No Content</h1><p>Path: {host}{resource_path_on_device}</p></body></html>", mimetype='text/html', status=response.status_code)
             else:
                 # Return empty JSON object for consistency? Or just 204? Let's go with 204.
                 return Response(status=204, mimetype='application/json')


        # --- Decrypt Response Body ---
        # Get server signature from X-Signature header for IV derivation
        response_signature_header = response.headers.get('X-Signature', None)
        if not response_signature_header:
             print("Error: Missing X-Signature header in device response.")
             return jsonify({'error': 'Missing required X-Signature header from device'}), 500 # Internal Server Error as we can't proceed

        # Validate format: MieleH256 <id>:<sig_hex>
        sig_parts = response_signature_header.split(':')
        if len(sig_parts) != 2 or not sig_parts[0].startswith('MieleH256 '):
             print(f"Error: Invalid X-Signature header format received: '{response_signature_header}'")
             return jsonify({'error': 'Invalid X-Signature header format from device'}), 500

        server_signature_hex = sig_parts[1]

        # Perform decryption using the updated function
        decrypted_bytes = decrypt(response.content, group_key, server_signature_hex)

        # Decode the decrypted bytes to a UTF-8 string
        # Use 'replace' to avoid errors on invalid bytes, shows '?' instead
        decrypted_str = decrypted_bytes.decode('utf-8', errors='replace')

        # --- Return Response Based on Mode ---
        if is_explore_request:
            # Try to parse as JSON and make links clickable
            try:
                json_data = json.loads(decrypted_str)
                # Pass the device resource path for correct relative link generation in explore mode
                iterate_to_all_hrefs(json_data, host, resource_path_on_device)
                # Use <pre> for formatting, add basic CSS for readability
                html_content = f"""
                <!DOCTYPE html>
                <html lang="en">
                  <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Explore: {host}{resource_path_on_device}</title>
                    <style>
                      body {{ font-family: sans-serif; background-color: #f8f9fa; margin: 1em; color: #212529; }}
                      h1 {{ color: #495057; border-bottom: 1px solid #dee2e6; padding-bottom: 0.5em;}}
                      pre {{ white-space: pre-wrap; word-wrap: break-word; background-color: #ffffff; border: 1px solid #ced4da; padding: 1em; border-radius: 0.25rem; font-family: monospace; font-size: 0.9em; }}
                      a {{ color: #007bff; text-decoration: none; }}
                      a:hover {{ text-decoration: underline; }}
                      .error {{ color: #dc3545; background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 1em; border-radius: 0.25rem; }}
                    </style>
                  </head>
                  <body>
                    <h1>{host}{resource_path_on_device}</h1>
                    <pre>{json.dumps(json_data, indent=2)}</pre>
                  </body>
                </html>
                """
                return Response(html_content, mimetype='text/html')
            except json.JSONDecodeError as e:
                print(f"Warning: Decrypted data for explore mode is not valid JSON: {e}")
                # Show the raw decrypted data if it wasn't JSON, wrapped in HTML
                html_content = f"""
                 <!DOCTYPE html>
                 <html lang="en">
                   <head><title>Explore Error: Not JSON</title><style>.error{{color:red;}} body{{font-family:monospace; white-space:pre;}}</style></head>
                   <body><h1>Error: Response was not valid JSON</h1><p class="error">Path: {host}{resource_path_on_device}</p><hr><p>{decrypted_str}</p></body>
                 </html>"""
                return Response(html_content, mimetype='text/html', status=200) # Return 200 but show error in content
        else:
            # Return raw decrypted data as JSON
            # Verify it's valid JSON before setting content type? Or trust the device?
            # Let's trust for now, but add a check if issues arise.
            return Response(decrypted_str, mimetype='application/json')

    # --- Specific Error Handling for Main Route ---
    except req.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else 500
        error_message = f"HTTP error from device: {status_code}"
        details = e.response.text if e.response is not None and e.response.text else 'No details provided.'
        print(f'HTTP error during {"explore " if is_explore_request else ""}request to {host}{resource_path_on_device}: {status_code} {e.response.reason if e.response is not None else ""}')
        print(f"Response body: {details}")
        return jsonify({'error': error_message, 'details': details}), status_code
    except req.exceptions.Timeout:
        print(f'Timeout during {"explore " if is_explore_request else ""}request to {host}{resource_path_on_device}')
        return jsonify({'error': 'Device communication timed out'}), 504
    except req.exceptions.ConnectionError:
        print(f'Connection error during {"explore " if is_explore_request else ""}request to {host}{resource_path_on_device}')
        return jsonify({'error': 'Device connection refused or unavailable'}), 503
    except req.exceptions.RequestException as e:
        print(f'Network request error during {"explore " if is_explore_request else ""}request to {host}{resource_path_on_device}: {e}')
        return jsonify({'error': f'Network request failed: {e}'}), 500
    # --- Error Handling for Decryption/Processing ---
    except ValueError as e: # Catch potential errors from decrypt (padding, signature format) or JSON parsing
        print(f"Data processing error (decrypt/JSON): {e}")
        traceback.print_exc()
        return jsonify({'error': f'Data processing error: {e}'}), 500 # Internal error as we couldn't process response
    # --- General Error Handling ---
    except Exception as e:
        print(f'Unexpected error during {"explore " if is_explore_request else ""}request: {e}')
        traceback.print_exc()
        return jsonify({'error': 'Internal Server Error occurred'}), 500


if __name__ == '__main__':
    # Get port from environment variable 'PORT' or default to 3000
    port = int(os.environ.get('PORT', 3000))

    print(f"--- Miele Proxy Server Starting ---")
    print(f"Listening on: http://0.0.0.0:{port}")
    # Mask sensitive parts of ID/Key in startup log
    print(f"Using Group ID: ...{group_id.hex()[-4:].upper() if len(group_id)==8 else 'Invalid Length'}")
    print(f"Using Group Key: {'Set (length OK)' if len(group_key)==64 else 'Invalid Length or Default'}")
    print(f"Debug Logging: {'Enabled' if debug_log else 'Disabled'}")
    print(f"---------------------------------")

    # Run the Flask development server
    # Set debug=False for production or stable environments
    # use_reloader=True is helpful during development but can cause issues in some environments
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=True)
