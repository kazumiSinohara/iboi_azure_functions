import logging
import azure.functions as func
import os
import json
from azure.cosmos import CosmosClient

endpoint = os.environ["COSMOS_URI"]
key = os.environ["COSMOS_KEY"]
database_name = "iotdb"
container_name = "devicestate"

client = CosmosClient(endpoint, credential=key)
database = client.get_database_client(database_name)
container = database.get_container_client(container_name)

def main(req: func.HttpRequest) -> func.HttpResponse:
    device_id = req.route_params.get("device_id")

    if not device_id:
        return func.HttpResponse("Device ID is required", status_code=400)

    try:
        # Partition key and ID are assumed to be the same
        device_data = container.read_item(item=device_id, partition_key=device_id)
        return func.HttpResponse(json.dumps(device_data), mimetype="application/json", status_code=200)
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return func.HttpResponse(f"Device {device_id} not found.", status_code=404)
