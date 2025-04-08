# **Miele Gateway Python Add-on for Home Assistant**

An API gateway for Miele appliances that decrypts and exposes appliance data for integration with Home Assistant. This add-on enables communication with Miele appliances using the XKM 3100 W module by handling the necessary encryption and decryption, allowing for seamless integration and control within Home Assistant.  
Note: This script is based on the [MieleXKM3100WGateway](https://github.com/Ich-Eben/MieleXKM3100WGateway) project by Ich-Eben, originally written in JavaScript. Some insights were also gained from analyzing the [MieleRESTServer](https://github.com/akappner/MieleRESTServer/tree/master) project by akappner.

## **Table of Contents**

* [Introduction](#bookmark=id.ga26qgngnbgp)  
* [Features](#bookmark=id.awzotf72wxtz)  
* [Requirements](#bookmark=id.4mzk77s9736z)  
* [Installation](#bookmark=id.w44gmaqw79e5)  
* [Configuration](#bookmark=id.u499lxo3u7tv)  
* [Usage](#bookmark=id.8cbap9kf22b)  
  * [Initializing the Device (Pairing)](#bookmark=id.2es9wrossru5)  
  * [Explore Appliance Data](#bookmark=id.8ocf90lo5oxr)  
  * [Access Specific Data](#bookmark=id.vezvlrqebhae)  
* [Integrating with Home Assistant Sensors](#bookmark=id.9208zq55basm)  
* [How It Works](#bookmark=id.jfqql5pqm9js)  
* [Acknowledgments](#bookmark=id.cq40onehz45k)  
* [Disclaimer](#bookmark=id.cfj8nguroex0)  
* [Support](#bookmark=id.ixrl986gb9lp)

## **Introduction**

Miele appliances equipped with the XKM 3100 W module communicate using a proprietary protocol that involves encryption. This add-on acts as a gateway by decrypting the data from the appliance and exposing it via a local API, enabling Home Assistant to interact with the appliance without dealing with encryption complexities.

## **Features**

* Decrypts and exposes Miele appliance data.  
* Provides an API to interact with the appliance.  
* Supports both IP addresses and hostnames for appliance identification.  
* Handles errors gracefully when the appliance is unavailable.  
* Easy integration with Home Assistant as an add-on.  
* Based on the proven functionality of the original JavaScript gateway.

## **Requirements**

* Home Assistant instance running on one of the supported architectures:  
  * aarch64  
  * amd64  
  * armv7  
  * armhf  
  * i386  
* Miele appliance equipped with the XKM 3100 W module.  
* Access to the appliance's network (the appliance and Home Assistant must be on the same network).  
* GROUP\_KEY and GROUP\_ID values specific to your appliance pairing session.

## **Installation**

### **Adding the Custom Repository**

To install the Miele Gateway add-on, you need to add the custom repository to your Home Assistant instance.

1. **Access the Add-on Store**  
   * In Home Assistant, navigate to **Settings** \> **Add-ons**.  
   * Click on the **Add-on Store** button in the bottom right.  
2. **Add the Repository**  
   * Click on the three dots (⋮) in the top right corner and select **Repositories**.  
   * In the **Add repository** field, enter the URL of the custom repository hosting the Miele Gateway add-on. For example:  
     https://github.com/JameZUK/MieleXKM3100WGateway-HomeAssistant

   * Click **Add**.  
3. **Refresh the Add-on Store**  
   * Close the repository management dialog. Home Assistant should refresh.  
   * If it doesn't refresh automatically, click on the **Reload** button or refresh your browser.  
4. **Install the Miele Gateway Add-on**  
   * Find the "Miele Gateway" add-on in the store (it might be under the repository name).  
   * Click on the add-on to view its details.  
   * Click **Install** and wait for the installation to complete.

## **Configuration**

Before starting the add-on, you need to provide your GROUP\_KEY and GROUP\_ID. These are essential for authenticating with your Miele appliance.

### **1\. Obtain GROUP\_KEY and GROUP\_ID**

* **Important**: The GROUP\_KEY and GROUP\_ID are unique to your appliance **pairing session** and are required for encrypted communication.  
* These values are typically generated during a pairing process (e.g., using specific tools or methods documented elsewhere for Miele local API access). They are **not** usually found in standard appliance documentation.  
* Ensure that you have obtained these values correctly before proceeding.

### **2\. Configure the Add-on**

#### **Access the Configuration**

* In Home Assistant, navigate to **Settings** \> **Add-ons**.  
* Click on the Miele Gateway add-on.  
* Click on the **Configuration** tab.

#### **Enter Your Credentials**

* Provide your GROUP\_KEY and GROUP\_ID in the respective fields under "Options":  
  group\_key: "your\_group\_key\_in\_hex"  
  group\_id: "your\_group\_id\_in\_hex"

  Replace "your\_group\_key\_in\_hex" and "your\_group\_id\_in\_hex" with your actual keys in hexadecimal format (lowercase or uppercase is acceptable here, the script handles it).

#### **Save Configuration**

* Click **Save** to save your configuration.

### **3\. Network Configuration (Optional)**

* If your appliance is on a different subnet or requires specific network settings, ensure that your Home Assistant instance can communicate with it.  
* Adjust firewall rules or network settings as needed. The add-on typically runs on port 3000\.

### **4\. Start the Add-on**

* Return to the **Info** tab of the add-on.  
* Click **Start**.  
* Check the **Log** tab to ensure the add-on starts without errors and that it correctly reads the keys.

## **Usage**

Once the add-on is running, it exposes an API typically on port 3000\. You interact with your Miele appliance *through* this proxy API.

### **Initializing the Device (Pairing)**

This step sends the GROUP\_ID and GROUP\_KEY (that you configured in the add-on) **to** the Miele device. This is a *mandatory* step to establish a secure communication channel with your appliance. Without it, subsequent API calls will fail.

* **Purpose**: To register the add-on's credentials with the Miele device using its standard commissioning endpoint.  
* **When to Use**: Run this endpoint *immediately after* configuring the add-on with your Group ID and Key. If you encounter persistent 403 Forbidden errors when trying to access device data, try running this endpoint again to re-establish the pairing. The device usually needs to be in a receptive state (e.g., pairing mode, recently reset, or as per specific device requirements).  
* **Endpoint on Proxy**:  
  http://\<home\_assistant\_ip\_or\_hostname\>:3000/init/\<appliance\_host\_or\_ip\>

* **Method**: GET (Send a GET request *to the proxy URL*)  
* **Parameters**:  
  * \<home\_assistant\_ip\_or\_hostname\>: The IP address or hostname of your Home Assistant instance.  
  * \<appliance\_host\_or\_ip\>: The IP address or hostname of your Miele appliance on the network.  
* **Action**: The proxy receives your GET request and sends an *unsigned* PUT request containing the configured GroupID and GroupKey to http://\<appliance\_host\_or\_ip\>/Security/Commissioning/.  
* **Example**:  
  \# Using curl from another machine on the network (using IP addresses)  
  curl http://192.168.1.10:3000/init/192.168.1.50

  \# Or open in a browser on your network (using hostname)  
  http://homeassistant.local:3000/init/\<appliance\_host\_or\_ip\>

* **Expected Outcome**:  
  * **Success**: The device often returns 200 OK or 204 No Content. Check the add-on logs for the response details.  
  * **Failure**: A 403 Forbidden likely means the device rejected the credentials or wasn't in the correct state. Other errors (5xx) usually indicate network issues reaching the device.

### **Explore Appliance Data**

Retrieve and explore the data exposed by your appliance *after* successful initialization/pairing.

* **Endpoint on Proxy**:  
  http://\<home\_assistant\_ip\_or\_hostname\>:3000/explore/\<appliance\_host\_or\_ip\>/

* **Method**: GET  
* **Example**:  
  http://homeassistant.local:3000/explore/192.168.1.50/

* **Usage**:  
  * This endpoint provides a basic HTML view of the appliance's API structure.  
  * Responses containing API paths (like /Devices/...) will be rendered as clickable links, allowing you to navigate the API directly in your browser through the proxy.  
  * Use this to discover the paths needed for specific data (e.g., /Devices/\<ID\>/State).

### **Access Specific Data**

Access specific data or control endpoints of your appliance *after* successful initialization/pairing.

* **Endpoint on Proxy**:  
  http://\<home\_assistant\_ip\_or\_hostname\>:3000/\<appliance\_host\_or\_ip\>/\<path\>

* **Method**: GET (for reading data)  
* **Parameters**:  
  * \<path\>: The specific API path on the Miele device you want to access (discovered via the explore endpoint or other documentation). Remember to include the full path as seen on the device API (e.g., Devices/\<ID\>/State).  
* **Example**:  
  http://homeassistant.local:3000/192.168.1.50/Devices/000123456789/State

* **Response**: The proxy will send a signed request to the device, receive the encrypted response, decrypt it, and return the plaintext JSON data to you.

## **Integrating with Home Assistant Sensors**

You can create custom sensors in Home Assistant to monitor the status of your Miele appliance using the REST platform, querying the proxy add-on.

### **Creating a Custom Sensor**

1. **Edit Your configuration.yaml** (or create sensors via UI if preferred, using RESTful Sensor integration).  
2. **Add Sensor Configuration**:  
   \# Example configuration.yaml entry  
   rest:  
     \- resource: http://\<addon\_hostname\_or\_ip\>:3000/\<appliance\_host\_or\_ip\>/Devices/\<device\_id\>/State  
       scan\_interval: 15 \# Adjust frequency as needed  
       sensor:  
         \- name: "Miele Appliance State Raw"  
           unique\_id: miele\_appliance\_state\_raw\_01234  
           value\_template: "{{ value\_json.Status.value\_raw }}" \# Access raw status code  
           json\_attributes:  
             \- Status  
             \- ProgramType  
             \- ProgramPhase  
             \# Add other top-level keys from the JSON response you want as attributes  
     \- resource: http://\<addon\_hostname\_or\_ip\>:3000/\<appliance\_host\_or\_ip\>/Devices/\<device\_id\>/State  
       scan\_interval: 15 \# Should match above if querying same endpoint  
       sensor:  
         \- name: "Miele Appliance Status"  
           unique\_id: miele\_appliance\_status\_01234  
           \# Example mapping raw status codes to human-readable states  
           value\_template: \>  
             {% set status\_map \= {  
                 1: 'Off', 2: 'On', 3: 'Programmed', 4: 'WaitingToStart',  
                 5: 'Running', 6: 'Paused', 7: 'EndOfProgram', 8: 'Failure',  
                 9: 'ProgramInterrupted', 10: 'Idle', 11: 'RinseHold',  
                 12: 'Service', 13: 'Superfreezing', 14: 'Supercooling', 15: 'Superheating'  
             } %}  
             {% set raw\_status \= value\_json.Status.value\_raw | int(-1) %}  
             {{ status\_map.get(raw\_status, 'Unknown (' \~ raw\_status \~ ')') }}  
           json\_attributes: \# Redundant if using the raw sensor above, choose one method  
             \- Status  
             \- ProgramType  
             \- ProgramPhase

   **Notes on Sensor Config:**  
   * Replace \<addon\_hostname\_or\_ip\> with the address Home Assistant uses to reach the add-on (often localhost or the add-on's specific hostname like a0d7b954-miele-gateway).  
   * Replace \<appliance\_host\_or\_ip\> with the Miele device's address.  
   * Replace \<device\_id\> with the actual ID found via the /explore/ endpoint (usually under /Devices/).  
   * Adjust the value\_template and json\_attributes based on the actual JSON structure returned by the /State endpoint (use /explore/ to see it).  
   * Carefully consider the scan\_interval. Frequent polling can put unnecessary load on your Miele device and network. Start with a higher value (e.g., 60 seconds or more) and decrease it only if you need more real-time updates.

## **How It Works**

1. **Configuration**: You provide the GROUP\_ID and GROUP\_KEY via the add-on configuration.  
2. **Initialization (Optional but Recommended)**: Sending a request to /init/\<appliance\> triggers the add-on to send these keys to the appliance via an unsigned PUT to /Security/Commissioning/.  
3. **API Request**: You send a standard HTTP request to the add-on's API endpoint (e.g., /\<appliance\>/Devices/.../State).  
4. **Signing**: The add-on constructs the required signing string (including method, path, headers, date), calculates the HMAC-SHA256 signature using your GROUP\_KEY, and adds the Authorization header.  
5. **Forwarding**: The add-on sends the signed request to the Miele appliance.  
6. **Receiving**: The appliance validates the signature and sends back an encrypted response (AES-CBC). It also includes an X-Signature header.  
7. **Decryption**: The add-on uses the first half of your GROUP\_KEY as the AES key and derives the IV from the appliance's X-Signature response header to decrypt the response body.  
8. **Response**: The add-on returns the decrypted plaintext JSON data to your client (e.g., Home Assistant REST sensor).

## **Acknowledgments**

* **Original JavaScript Script**: This add-on is heavily based on the [MieleXKM3100WGateway](https://github.com/Ich-Eben/MieleXKM3100WGateway) project by Ich-Eben.  
* **Protocol Insights**: Some understanding of the protocol was gained from analyzing the [MieleRESTServer](https://github.com/akappner/MieleRESTServer/tree/master) project by akappner.  
* **Contributors**:  
  * Ich-Eben: For the original JavaScript implementation.  
  * Community: For ongoing support, testing, and improvements.

## **Disclaimer**

* **Use at Your Own Risk**: This add-on is not affiliated with or endorsed by Miele. Use is at your own risk. The author is not responsible for any issues arising from its use.  
* **Security Considerations**: Your GROUP\_KEY and GROUP\_ID are sensitive. Keep them secure and do not share them publicly or commit them to version control.  
* **Compliance with Terms of Service**: Ensure using this add-on complies with Miele's terms of service and local regulations. Consult Miele support if unsure.

## **Support**

For questions, issues, or contributions, please open an issue on the project's GitHub repository ([JameZUK/MieleXKM3100WGateway-HomeAssistant](https://github.com/JameZUK/MieleXKM3100WGateway-HomeAssistant)). Provide detailed information, including **add-on logs** (with keys masked if sharing publicly), configurations, and appliance details.
