# Azure Functions IoT Hub to SignalR Project

This project implements an Azure Functions-based backend for processing IoT device data, storing it, and pushing real-time updates to connected clients using Azure SignalR Service. It also allows clients to join specific groups for targeted updates.

## Core Functionality

The system consists of several Azure Functions working together:

1.  **Device Data Ingestion & Storage (`IoTEventTrigger`)**:
    *   **Trigger**: Azure Event Hub (configured to receive messages from an Azure IoT Hub).
    *   **Action**:
        *   Receives telemetry data from IoT devices.
        *   Parses the event message and metadata to extract device ID, timestamp, location (latitude, longitude, direction), battery level, signal strength (RSRP, CSQ), bands, wakeup reason, GNSS satellite count, application version, and eSim ID.
        *   Adjusts latitude and longitude (currently by negating them, this might need review based on actual device data format).
        *   Constructs a JSON document with the processed device state.
        *   Upserts (updates or inserts) this document into an Azure Cosmos DB container named `devicestate_v2` within the `iotdb` database.
    *   **Purpose**: Acts as the primary entry point for device data, ensuring it's stored durably and in a structured format.

2.  **Real-time Updates to Clients (`ChangeFeedToSignalR`)**:
    *   **Trigger**: Azure Cosmos DB change feed on the `devicestate_v2` container.
    *   **Action**:
        *   Activates whenever a document in `devicestate_v2` is created or updated (e.g., by `IoTEventTrigger`).
        *   Extracts `deviceId`, `farmId`, and other relevant fields (like location, battery) from the changed document.
        *   Constructs a JSON payload containing this device update information.
        *   Sends this payload as a message via Azure SignalR Service.
        *   **Targeting**: The message is sent to a specific SignalR group named `farm_<farmId>` (e.g., `farm_boa_vista`).
        *   **Client Method Invoked**: The message is sent with a target method name `"updateDeviceState"`, which client applications should listen for.
    *   **Purpose**: Enables real-time broadcasting of device state changes to clients subscribed to specific farm groups.

3.  **Client Connection Negotiation (`Negotiate`)**:
    *   **Trigger**: HTTP (GET or POST requests to `/api/negotiate`).
    *   **Action**:
        *   Uses the Azure SignalR Service input binding.
        *   Expects a `userId` as a query parameter (e.g., `/api/negotiate?userId=clientUser1`).
        *   Generates and returns the necessary connection information (SignalR Service URL and an access token) for a client to connect to the `"iboihub"` SignalR hub. The returned access token will be associated with the provided `userId`.
    *   **Purpose**: Provides a secure endpoint for SignalR clients to obtain the credentials needed to establish a connection with the Azure SignalR Service, associating the connection with a user.

4.  **Client Group Management (`join_group`)**:
    *   **Trigger**: HTTP (GET or POST requests to `/api/join_group`).
    *   **Action**:
        *   Expects `farmId` and either `userId` or `connectionId` as query parameters or in the JSON request body.
        *   Constructs the target SignalR group name (e.g., `farm_<farmId>`).
        *   Makes an authenticated HTTP PUT request to the Azure SignalR Service's REST management API to add the specified user (by `userId`) or connection (by `connectionId`) to the constructed group within the `"iboihub"`.
        *   Generates a JWT token internally using the `AzureSignalRConnectionString`'s access key to authenticate the management API call. The audience for this JWT is the specific management API endpoint being called.
    *   **Purpose**: Allows clients (or a backend process acting on their behalf) to dynamically join SignalR groups corresponding to specific farms, enabling them to receive targeted updates from `ChangeFeedToSignalR`.

5.  **Device Data Retrieval (API Endpoints)**:
    *   **`GetDeviceData`**:
        *   **Trigger**: HTTP GET to `/api/devices/{device_id}`.
        *   **Action**: Retrieves and returns the state of a specific device by its ID from the `devicestate` Cosmos DB container (Note: current implementation writes to `devicestate_v2`, so this function might be reading from an older/different container).
        *   **Purpose**: Provides a direct way to query the last known state of a single device.
    *   **`GetFarmDevices`**:
        *   **Trigger**: HTTP GET to `/api/farm/{farm_id}`.
        *   **Action**: Queries and returns all device documents from the `devicestate_v2` Cosmos DB container that match the specified `farm_id`.
        *   **Purpose**: Allows retrieval of all device states associated with a particular farm.

## Key Azure Services Used

*   **Azure Functions**: Hosts the serverless application logic.
*   **Azure IoT Hub**: (Implicitly) The source of device messages, sending data to an Event Hub.
*   **Azure Event Hubs**: Triggers the `IoTEventTrigger` function.
*   **Azure Cosmos DB**:
    *   Stores device state data (in `devicestate_v2` container, `iotdb` database).
    *   Provides the change feed to trigger `ChangeFeedToSignalR`.
    *   Stores leases for the Cosmos DB trigger (in the `leases` container).
*   **Azure SignalR Service**:
    *   Manages real-time WebSocket connections with clients.
    *   Facilitates message broadcasting to specific groups or users.
    *   Used in "Serverless" mode.
*   **Azure Blob Storage**: (Implicitly via `AzureWebJobsStorage`) Used by Azure Functions for host state, lease management for Event Hub triggers, etc.

## Setup and Configuration (local.settings.json)

The following application settings are crucial for the functions to operate:

*   `AzureWebJobsStorage`: Connection string for Azure Storage (used by Functions host).
*   `FUNCTIONS_WORKER_RUNTIME`: Set to `"python"`.
*   `FUNCTIONS_EXTENSION_VERSION`: Set to `"~4"` (for Azure Functions V4 runtime).
*   `IoTHubConnection`: Event Hub compatible connection string for the IoT Hub.
*   `CosmosDB`: Connection string for the Azure Cosmos DB account (e.g., `AccountEndpoint=...;AccountKey=...;`).
    *   _Note: This was previously `COSMOS_CONNECTION`. The `ChangeFeedToSignalR` function (when using bundles) expected the default name `CosmosDB`._
    *   _The `IoTEventTrigger` might still be using `COSMOS_URI` and `COSMOS_KEY` if its code hasn't been updated to use a single connection string setting._
*   `AzureSignalRConnectionString`: Connection string for the Azure SignalR Service instance.
*   `Host`: Contains CORS settings for local development (e.g., `"CORS": "*"`).

## Deployment

The project can be deployed to Azure Functions using `func azure functionapp publish <AppName> --build remote`.
Ensure:
*   All necessary application settings (from `local.settings.json`) are configured in the Azure Function App's "Configuration" section.
*   The Azure SignalR Service instance is set to **"Serverless"** mode.
*   CORS settings for the deployed Function App are configured to allow access from your client application's domain.

## Client Interaction Flow (Example)

1.  **Client (e.g., `remote_test.html`) requests connection info:**
    *   Client UI inputs `userId` and `farmId`.
    *   Client JavaScript calls `fetch('https://<app_name>.azurewebsites.net/api/negotiate?userId=<userId>')`.
2.  **`Negotiate` function responds:**
    *   Returns `{ "url": "...", "accessToken": "..." }`. The `accessToken` is bound to the `userId`.
3.  **Client connects to SignalR:**
    *   Uses the `url` and `accessToken` to establish a WebSocket connection via the SignalR client library.
4.  **Client joins a group:**
    *   After connecting, client JavaScript calls `fetch('https://<app_name>.azurewebsites.net/api/join_group?farmId=<farmId>&userId=<userId>')` (or passes `connectionId`).
    *   `join_group` function uses the SignalR REST API to add this user/connection to the `farm_<farmId>` group.
5.  **Device sends data:**
    *   IoT device sends telemetry.
    *   `IoTEventTrigger` processes it and upserts to Cosmos DB (`devicestate_v2`).
6.  **Real-time update occurs:**
    *   Cosmos DB change triggers `ChangeFeedToSignalR`.
    *   `ChangeFeedToSignalR` constructs a message with `target: "updateDeviceState"` and `arguments: [devicePayload]`, and sends it to the `groupName: "farm_<farmId>"` (where `<farmId>` matches the updated document).
7.  **Client receives update:**
    *   The client's `connection.on("updateDeviceState", (message) => { ... });` handler is invoked.
    *   The client UI updates with the new device information from the `message` payload.

This provides a comprehensive overview of the system's architecture, functionality, and operational flow. 