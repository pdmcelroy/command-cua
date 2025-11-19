# Cargomatic Computer Use Agent Walkthrough (Staging)

## Overview
This agent automates the process of retrieving shipper information from the Cargomatic Command Center (Staging Environment).

## Workflow
1.  **Login**: Authenticates using provided credentials ("admin"/"admin").
2.  **Global Search**: Enters the shipment ID (`AUT-201270`) in the top-level search bar.
3.  **Select Result**: Clicks the first result from the dropdown list.
4.  **Click Shipper**: Navigates to the shipment details page and clicks the "Shipper" link.
5.  **Verify Navigation**: Confirms navigation to the shipper's profile page.

## Verification Results
The agent was successfully tested with shipment ID `AUT-201270` on `https://command-staging.cargomatic.com`.

### Output Log
```
Navigating to https://command-staging.cargomatic.com...
Logging in...
Login successful! Current URL: https://command-staging.cargomatic.com/
Searching globally for: AUT-201270
Search submitted. Waiting for results...
Clicking first result...
Waiting for navigation to shipment details...
Navigated to: https://command-staging.cargomatic.com/shipments/691e14d9083a543df4f1dd58
Locating and clicking Shipper link...
Waiting for page content to load...
Found Shipper: AUTO 067289 Co. Clicking link...
Navigated to Shipper Page: https://command-staging.cargomatic.com/users/691e14bb083a543df4f1d406
```

## Key Code Components
-   `search_global(reference_number)`: Handles the search interaction.
-   `click_shipper_link()`: Locates the `dt` element with text "Shipper", finds the link in the following `dd` element, clicks it, and waits for navigation.
