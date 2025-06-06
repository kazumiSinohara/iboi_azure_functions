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
# Create Cosmos DB container client
client = CosmosClient(COSMOS_URI, COSMOS_KEY)
container = client.get_database_client(DB_NAME).get_container_client(CONTAINER_NAME)

def main(event: func.EventHubEvent):
    logging.info(">>> IOTHUB event received")

    try:
        msg = json.loads(event.get_body().decode("utf-8"))
        
        document_id = msg.get("id")
        farm_id = msg.get("farmID") # Get farmID directly from the payload

        if not document_id or not farm_id:
            logging.error(f"Message is missing 'id' or 'farmID'. Payload: {msg}")
            return # Abort if essential fields are missing

        logging.info(f"Processing message for device '{document_id}' on farm '{farm_id}'")

        timestamp = event.enqueued_time.isoformat()

        adjusted_lat = -1 * float(msg.get("latitude", 0))
        adjusted_lon = -1 * float(msg.get("longitude", 0))

        document = {
            "id": document_id, 
            "farmID": farm_id, # Partition Key
            "timestamp": timestamp,
            "connectionDeviceId": event.iothub_metadata.get("connection-device-id"), 
            "location": {
                "latitude": adjusted_lat,
                "longitude": adjusted_lon,
                "direction": msg.get("direction") 
            },
            "battery_level": msg.get("battery_level"),
            "rsrp": msg.get("rsrp"),
            "csq": msg.get("csq"),
            "bands": msg.get("bands"),
            "wakeup_reason": msg.get("wakeup_reason"),
            "gnss_satnum": msg.get("gnss_satnum"),
            "app_version": msg.get("app_version"),
            "idESim": msg.get("idESim")
        }

        container.upsert_item(document)
        logging.info(f"✅ Upserted data for document ID '{document_id}' to farm '{farm_id}'")

    except Exception as e:
        logging.error(f"❌ Error processing event: {e}")
