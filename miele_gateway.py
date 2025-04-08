@app.route('/', defaults={'resource': ''}) # Handle root path
@app.route('/<path:resource>', methods=['GET'])
def main_route(resource, explore_mode=False):
    """
    Main route to handle GET requests, perform authentication, decryption,
    and return either raw JSON or HTML for exploration.
    Handles trailing slashes consistently. Tries ASCII encoding for signing.
    """
    # Handle browser requests for favicon early
    if resource == 'favicon.ico':
        return '', 204 # No content response

    # Determine if this request came via /explore/ prefix in the original URL path
    is_explore_request = explore_mode

    if debug_log:
        print(f"\n=== {'EXPLORE ' if is_explore_request else ''}Request Received ===")
        print(f"Request URL: {request.url}")
        print(f"Raw resource path received: /{resource}")

    # Extract host and the actual resource path relative to the host
    path_parts = resource.strip('/').split('/')
    if not path_parts or not path_parts[0]:
        return jsonify({'error': 'Missing host in request path. Use format /<host>/<device_path>'}), 400
    host = path_parts[0]

    if not is_valid_host(host):
        return jsonify({'error': f"Invalid host format provided: '{host}'"}), 400

    # --- Path Handling (Trailing Slash Fix - kept from v2) ---
    resource_path_part = '/'.join(path_parts[1:])
    original_request_path_had_trailing_slash = resource.endswith('/')
    resource_path_on_device = "/" + resource_path_part
    current_path_has_trailing_slash = resource_path_on_device.endswith('/')
    if original_request_path_had_trailing_slash and not current_path_has_trailing_slash and resource_path_on_device != '/':
        resource_path_on_device += '/'
    elif not original_request_path_had_trailing_slash and current_path_has_trailing_slash and resource_path_on_device != '/':
         resource_path_on_device = resource_path_on_device.rstrip('/')
    if len(path_parts) == 1 and original_request_path_had_trailing_slash:
        resource_path_on_device = '/'
    elif len(path_parts) == 1 and not original_request_path_had_trailing_slash:
         resource_path_on_device = '/'
    # --- End Path Handling ---

    if debug_log:
        print(f"Target Host: {host}")
        print(f"Original had trailing slash: {original_request_path_had_trailing_slash}")
        print(f"Final Target Resource Path (used for signing & URL): '{resource_path_on_device}'")

    try:
        current_time_gmt = get_current_time_in_http_format()

        # --- Prepare Authentication Signature ---
        signing_string = f'GET\n{host}{resource_path_on_device}\n\n{accept_header}\n{current_time_gmt}\n'

        # --- MODIFICATION: Use ASCII encoding for the signing string ---
        # This matches an attempt in the user's original script and might be required by Miele.
        try:
            signing_bytes = signing_string.encode('ascii')
            if debug_log:
                print("Using ASCII encoding for signing string.")
        except UnicodeEncodeError:
            # Fallback or error if path/host contains non-ASCII (shouldn't typically happen)
            print("Warning: Signing string contains non-ASCII characters, falling back to UTF-8.")
            signing_bytes = signing_string.encode('utf-8')
        # --- End Modification ---

        # Calculate HMAC-SHA256 signature using the full group key
        signature_bytes = hmac.new(group_key, signing_bytes, hashlib.sha256).digest()
        signature_hex = signature_bytes.hex().upper()
        auth_header_value = f'MieleH256 {group_id.hex().upper()}:{signature_hex}'

        # --- Prepare Request Headers ---
        headers = {
            'Accept': accept_header,
            'Date': current_time_gmt,
            'User-Agent': 'Miele@mobile 2.3.3 Android',
            'Host': host,
            'Authorization': auth_header_value,
            'Accept-Encoding': 'gzip',
        }

        target_url = f'http://{host}{resource_path_on_device}'

        if debug_log:
             print(f"Target URL: GET {target_url}")
             print(f"Request Headers: {json.dumps(headers, indent=2)}")
             print(f"String Signed (raw):\n{signing_string.strip()}") # Show the string before encoding

        # --- Send Request to Device ---
        response = req.get(target_url, headers=headers, timeout=20)

        if debug_log:
            print(f"--- Device Response ---")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")

        # Check for HTTP errors after logging
        response.raise_for_status()

        # --- Process Successful Response (Code identical to v2 from here) ---
        if response.status_code == 204 or not response.content:
             if debug_log: print("Received 204 No Content or empty body.")
             if is_explore_request:
                 return Response(f"<html><body><h1>{response.status_code} No Content</h1><p>Path: {host}{resource_path_on_device}</p></body></html>", mimetype='text/html', status=response.status_code)
             else:
                 return Response(status=204, mimetype='application/json')

        # --- Decrypt Response Body ---
        response_signature_header = response.headers.get('X-Signature', None)
        if not response_signature_header:
             print("Error: Missing X-Signature header in device response.")
             return jsonify({'error': 'Missing required X-Signature header from device'}), 500
        sig_parts = response_signature_header.split(':')
        if len(sig_parts) != 2 or not sig_parts[0].startswith('MieleH256 '):
             print(f"Error: Invalid X-Signature header format received: '{response_signature_header}'")
             return jsonify({'error': 'Invalid X-Signature header format from device'}), 500
        server_signature_hex = sig_parts[1]

        decrypted_bytes = decrypt(response.content, group_key, server_signature_hex)
        decrypted_str = decrypted_bytes.decode('utf-8', errors='replace')

        # --- Return Response Based on Mode ---
        if is_explore_request:
            try:
                json_data = json.loads(decrypted_str)
                iterate_to_all_hrefs(json_data, host, resource_path_on_device)
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
                html_content = f"""
                 <!DOCTYPE html>
                 <html lang="en">
                   <head><title>Explore Error: Not JSON</title><style>.error{{color:red;}} body{{font-family:monospace; white-space:pre;}}</style></head>
                   <body><h1>Error: Response was not valid JSON</h1><p class="error">Path: {host}{resource_path_on_device}</p><hr><p>{decrypted_str}</p></body>
                 </html>"""
                return Response(html_content, mimetype='text/html', status=200)
        else:
            return Response(decrypted_str, mimetype='application/json')

    # --- Error Handling (Copied from previous version, unchanged) ---
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
    except ValueError as e:
        print(f"Data processing error (decrypt/JSON/path): {e}")
        traceback.print_exc()
        return jsonify({'error': f'Data processing error: {e}'}), 500
    except Exception as e:
        print(f'Unexpected error during {"explore " if is_explore_request else ""}request: {e}')
        traceback.print_exc()
        return jsonify({'error': 'Internal Server Error occurred'}), 500

# Note: The rest of the script (imports, other functions, __main__) remains the same
# Only the main_route function needs to be replaced.
