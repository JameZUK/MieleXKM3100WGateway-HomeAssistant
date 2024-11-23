
# Miele Gateway Python Add-on for Home Assistant

An API gateway for Miele appliances that decrypts and exposes appliance data for integration with Home Assistant. 
This add-on enables communication with Miele appliances using the XKM 3100 W module by handling the necessary encryption 
and decryption, allowing for seamless integration and control within Home Assistant.

**Note:** This script is based on the MieleXKM3100WGateway project by Ich-Eben, originally written in JavaScript.

## Table of Contents

1. [Introduction](#introduction)
2. [Features](#features)
3. [Requirements](#requirements)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Usage](#usage)
7. [Integrating with Home Assistant Sensors](#integrating-with-home-assistant-sensors)
8. [How It Works](#how-it-works)
9. [Acknowledgments](#acknowledgments)
10. [Disclaimer](#disclaimer)
11. [Support](#support)

## Introduction

Miele appliances equipped with the XKM 3100 W module communicate using a proprietary protocol that involves encryption. 
This add-on acts as a gateway by decrypting the data from the appliance and exposing it via a local API, enabling Home Assistant 
to interact with the appliance without dealing with encryption complexities.

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
- `GROUP_KEY` and `GROUP_ID` values specific to your appliance.

## Installation

### Adding the Custom Repository

To install the Miele Gateway add-on, you need to add the custom repository to your Home Assistant instance.

1. **Access the Add-on Store**
    - In Home Assistant, navigate to the **Supervisor** panel.
    - Click on the **Add-on Store** tab.

2. **Add the Repository**
    - Click on the three dots in the top right corner and select **Repositories**.
    - In the **Add repository** field, enter the URL of the custom repository hosting the Miele Gateway add-on. 
      For example:

        `https://github.com/yourusername/miele-gateway-addon`

      Replace `yourusername` with the actual username if the repository is hosted on GitHub, or provide the correct URL 
      if it's hosted elsewhere.

    - Click **Add** to add the repository.

3. **Refresh the Add-on Store**
    - After adding the repository, Home Assistant will automatically refresh the list of available add-ons.
    - If it doesn't refresh automatically, click on the **Reload** button or refresh your browser.

4. **Install the Miele Gateway Add-on**
    - Scroll through the add-ons in the store or use the search function to find **Miele Gateway**.
    - Click on the add-on to view its details.
    - Click **Install** to install the add-on.

## Configuration

Before starting the add-on, you need to provide your `GROUP_KEY` and `GROUP_ID`. These are essential for authenticating 
with your Miele appliance.

### 1. Obtain `GROUP_KEY` and `GROUP_ID`

- **Important:** The `GROUP_KEY` and `GROUP_ID` are unique to your appliance and are required for encrypted communication.
- These values are typically provided with your appliance documentation or can sometimes be obtained from Miele's 
  customer support.
- Ensure that you have these values before proceeding.

### 2. Configure the Add-on

- **Access the Configuration**
    - In Home Assistant, navigate to the **Supervisor** panel.
    - Click on the **Miele Gateway** add-on.
    - Click on the **Configuration** tab.

- **Enter Your Credentials**
    - Provide your `GROUP_KEY` and `GROUP_ID` in the respective fields:

        ```yaml
        group_key: "your_group_key_in_hex"
        group_id: "your_group_id_in_hex"
        ```

    - Replace `"your_group_key_in_hex"` and `"your_group_id_in_hex"` with your actual keys in hexadecimal format.

- **Save Configuration**
    - Click **Save** to save your configuration.

### 3. Network Configuration (Optional)

If your appliance is on a different subnet or requires specific network settings, ensure that your Home Assistant instance 
can communicate with it. Adjust firewall rules or network settings as needed.

### 4. Start the Add-on

- Return to the **Info** tab of the add-on.
- Click **Start** to start the add-on.
- Monitor the logs to ensure the add-on starts without errors.

## Usage

Once the add-on is running, it exposes an API on port 3000. You can interact with your Miele appliance using the following endpoints:

### Initialization

Initialize the connection with your appliance.

- **Endpoint:**

  ```
  http://<home_assistant_ip>:3000/init/<appliance_host>/
  ```

- **Method:** GET

- **Parameters:**
  - `<appliance_host>`: The IP address or hostname of your Miele appliance.

- **Example:**

  ```
  http://localhost:3000/init/192.168.1.100/
  ```

### Explore Appliance Data

Retrieve and explore the data exposed by your appliance.

- **Endpoint:**

  ```
  http://<home_assistant_ip>:3000/explore/<appliance_host>/
  ```

- **Method:** GET

- **Example:**

  ```
  http://localhost:3000/explore/192.168.1.100/
  ```

### Access Specific Data

Access specific data or control endpoints of your appliance.

- **Endpoint:**

  ```
  http://<home_assistant_ip>:3000/<appliance_host>/<path>
  ```

- **Method:** GET

- **Parameters:**
  - `<path>`: The specific API path you want to access.

- **Example:**

  ```
  http://localhost:3000/192.168.1.100/Devices/Device1/Program/
  ```

... [Add remaining content as required]

