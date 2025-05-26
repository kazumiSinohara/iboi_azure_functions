import logging
import json
import os
from azure.cosmos import CosmosClient
import azure.functions as func

# Cosmos DB configuration
COSMOS_URI = os.environ["COSMOS_URI"]
COSMOS_KEY = os.environ["COSMOS_KEY"]
DB_NAME = "iotdb"
CONTAINER_NAME = "devicestate_v2"
FARM_ID = 'boa_vista'

# Create Cosmos DB container client
client = CosmosClient(COSMOS_URI, COSMOS_KEY)
container = client.get_database_client(DB_NAME).get_container_client(CONTAINER_NAME)

def main(event: func.EventHubEvent):
    logging.info(">>> IOTHUB event received")
    logging.info(f"metadata keys: {event.metadata.keys()}")
    logging.info(f"iothub_metadata: {event.iothub_metadata}")

    try:
        # Parse body and metadata
        msg = json.loads(event.get_body().decode("utf-8"))
        device_id = (
            event.iothub_metadata.get("connection-device-id") or
            event.iothub_metadata.get("connectionDeviceId") or
            event.metadata.get("connectionDeviceId") or
            event.metadata.get("ConnectionDeviceId") or
            "unknown"
        )
        timestamp = event.enqueued_time.isoformat()

        # Extract farmId and validate
        farm_id = msg.get("farmId", FARM_ID)
        adjusted_lat = -1*float(msg.get("latitude",0))
        adjusted_lon = -1*float(msg.get("longitude",0))

        # Compose Cosmos document
        document = {
            "id": device_id,
            "farmId": farm_id,
            "timestamp": timestamp,
            "location": {
                "latitude": adjusted_lat,
                "longitude": adjusted_lon,
                "direction": msg.get("eastwest-ns")
            },
            "battery_level": msg.get("battery-level"),
            "rsrp": msg.get("rsrp"),
            "csq": msg.get("csq"),
            "bands": msg.get("bands"),
            "wakeup_reason": msg.get("wakeup-reason"),
            "gnss_satnum": msg.get("gnss-satnum"),
            "app_version": msg.get("app_ver"),
            "idESim": msg.get("idESim")
        }

        container.upsert_item(document)
        logging.info(f"✅ Upserted data for device '{device_id}' in farm '{farm_id}'")

    except Exception as e:
        logging.error(f"❌ Error processing event: {e}")
