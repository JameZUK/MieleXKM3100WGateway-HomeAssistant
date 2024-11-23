
# Miele Gateway Python Add-on for Home Assistant

An API gateway for Miele appliances that decrypts and exposes appliance data for integration with Home Assistant. This add-on enables communication with Miele appliances using the XKM 3100 W module by handling the necessary encryption and decryption, allowing for seamless integration and control within Home Assistant.

Note: This script is based on the [MieleXKM3100WGateway](https://github.com/Ich-Eben/MieleXKM3100WGateway) project by Ich-Eben, originally written in JavaScript.

## Table of Contents

- Introduction
- Features
- Requirements
- Installation
- Configuration
- Usage
- Integrating with Home Assistant Sensors
- How It Works
- Acknowledgments
- Disclaimer
- Support

## Introduction

Miele appliances equipped with the XKM 3100 W module communicate using a proprietary protocol that involves encryption. This add-on acts as a gateway by decrypting the data from the appliance and exposing it via a local API, enabling Home Assistant to interact with the appliance without dealing with encryption complexities.

## Features

- Decrypts and exposes Miele appliance data.
- Provides an API to interact with the appliance.
- Supports both IP addresses and hostnames for appliance identification.
- Handles errors gracefully when the appliance is unavailable.
- Easy integration with Home Assistant as an add-on.
- Based on the proven functionality of the original JavaScript gateway.

## Requirements

- Home Assistant instance running on one of the supported architectures:
  - aarch64
  - amd64
  - armv7
  - armhf
  - i386
- Miele appliance equipped with the XKM 3100 W module.
- Access to the appliance's network (the appliance and Home Assistant must be on the same network).
- GROUP_KEY and GROUP_ID values specific to your appliance.

## Installation

### Adding the Custom Repository

To install the Miele Gateway add-on, you need to add the custom repository to your Home Assistant instance.

1. **Access the Add-on Store**
   - In Home Assistant, navigate to the Supervisor panel.
   - Click on the Add-on Store tab.

2. **Add the Repository**
   - Click on the three dots in the top right corner and select Repositories.
   - In the Add repository field, enter the URL of the custom repository hosting the Miele Gateway add-on. For example:
     ```
     [https://github.com/JameZUK/MieleXKM3100WGateway-HomeAssistant](https://github.com/JameZUK/MieleXKM3100WGateway-HomeAssistant)
     ```
     Replace `yourusername` with the actual username if the repository is hosted on GitHub, or provide the correct URL if it's hosted elsewhere.
   - Click **Add** to add the repository.

3. **Refresh the Add-on Store**
   - After adding the repository, Home Assistant will automatically refresh the list of available add-ons.
   - If it doesn't refresh automatically, click on the **Reload** button or refresh your browser.

4. **Install the Miele Gateway Add-on**
   - Scroll through the add-ons in the store or use the search function to find Miele Gateway.
   - Click on the add-on to view its details.
   - Click **Install** to install the add-on.

## Configuration

Before starting the add-on, you need to provide your GROUP_KEY and GROUP_ID. These are essential for authenticating with your Miele appliance.

### 1. Obtain GROUP_KEY and GROUP_ID

- **Important**: The GROUP_KEY and GROUP_ID are unique to your appliance and are required for encrypted communication.
- These values are typically provided with your appliance documentation or can sometimes be obtained from Miele's customer support.
- Ensure that you have these values before proceeding.

### 2. Configure the Add-on

#### Access the Configuration
- In Home Assistant, navigate to the Supervisor panel.
- Click on the Miele Gateway add-on.
- Click on the Configuration tab.

#### Enter Your Credentials
- Provide your GROUP_KEY and GROUP_ID in the respective fields:
  ```
  group_key: "your_group_key_in_hex"
  group_id: "your_group_id_in_hex"
  ```
  Replace `"your_group_key_in_hex"` and `"your_group_id_in_hex"` with your actual keys in hexadecimal format.

#### Save Configuration
- Click **Save** to save your configuration.

### 3. Network Configuration (Optional)

- If your appliance is on a different subnet or requires specific network settings, ensure that your Home Assistant instance can communicate with it.
- Adjust firewall rules or network settings as needed.

### 4. Start the Add-on

- Return to the Info tab of the add-on.
- Click **Start** to start the add-on.
- Monitor the logs to ensure the add-on starts without errors.

## Usage

Once the add-on is running, it exposes an API on port 3000. You can interact with your Miele appliance using the following endpoints:

### Initialization

Initialize the connection with your appliance.

- **Endpoint**:
  ```
  http://<home_assistant_ip>:3000/init/<appliance_host>/
  ```
- **Method**: GET
- **Parameters**:
  - `<appliance_host>`: The IP address or hostname of your Miele appliance.
- **Example**:
  ```
  http://localhost:3000/init/192.168.1.100/
  ```

### Explore Appliance Data

Retrieve and explore the data exposed by your appliance.

- **Endpoint**:
  ```
  http://<home_assistant_ip>:3000/explore/<appliance_host>/
  ```
- **Method**: GET
- **Example**:
  ```
  http://localhost:3000/explore/192.168.1.100/
  ```

- **Usage**:
  - The explore interface provides clickable links to navigate through the available data endpoints.
  - Use this to identify the specific data you want to access or monitor.

### Access Specific Data

Access specific data or control endpoints of your appliance.

- **Endpoint**:
  ```
  http://<home_assistant_ip>:3000/<appliance_host>/<path>
  ```
- **Method**: GET
- **Parameters**:
  - `<path>`: The specific API path you want to access.
- **Example**:
  ```
  http://localhost:3000/192.168.1.100/Devices/Device1/Program/
  ```

## Integrating with Home Assistant Sensors

You can create custom sensors in Home Assistant to monitor the status of your Miele appliance using the REST platform.

### Creating a Custom Sensor

1. **Edit Your `configuration.yaml`**
2. **Add the Following Sensor Configuration**:

```yaml
sensor:
  - platform: rest
    name: Kitchen Cooker State
    unique_id: kitchen_cooker_state
    resource: http://<DOCKERNAME>:3000/<APPLIANCE_HOST>/Devices/<DEVICE>/State/
    scan_interval: 5
    value_template: >
      {% set cstate = value_json.Status %}
      {% if cstate == 1 %}
        Off
      {% elif cstate == 2 %}
        On
      {% elif cstate == 5 %}
        Cooking
      {% else %}
        Unknown
      {% endif %}
```

## Additional Detailed Instructions

Ensure that you have thoroughly reviewed the API endpoints exposed by the add-on. Familiarize yourself with the appliance's specific data fields and paths by exploring the `/explore/<appliance_host>/` endpoint. This helps to create precise and efficient integrations in Home Assistant.

- Use `scan_interval` wisely in your Home Assistant configuration to balance performance and API load.
- Test configurations in Home Assistant before deploying them to avoid unnecessary errors.

## Acknowledgments

- **Original JavaScript Script**: This add-on is based on the [MieleXKM3100WGateway](https://github.com/Ich-Eben/MieleXKM3100WGateway) project by Ich-Eben. The original script was written in JavaScript and provided the foundational functionality for communicating with Miele appliances.
- **Contributors**:
  - Ich-Eben: For the original JavaScript implementation and inspiration.
  - Community: For ongoing support and improvements.

## Disclaimer

- **Use at Your Own Risk**:
  - This add-on is not affiliated with or endorsed by Miele.
  - Use of this add-on is at your own risk. The author is not responsible for any issues arising from its use.
- **Security Considerations**:
  - Ensure that your GROUP_KEY and GROUP_ID are kept secure.
  - Do not share these keys publicly or commit them to version control systems.
- **Compliance with Terms of Service**:
  - Ensure that using this add-on complies with all applicable terms of service and local laws.
  - It's recommended to consult Miele's terms of service or contact Miele support if you are unsure about the legality of using this add-on.

## Support

For questions, issues, or contributions, please open an issue on the project's GitHub repository. Provide detailed information about the issue, including error logs, configurations, and appliance details (without sharing sensitive keys).

Contributions are welcome to improve the functionality and compatibility of the add-on.
