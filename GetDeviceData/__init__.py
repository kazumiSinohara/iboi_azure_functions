import logging
import azure.functions as func
import os
import json
import requests
from azure.cosmos import CosmosClient

SQL_API_URL = os.environ.get("SQL_API_URL")
endpoint = os.environ["COSMOS_URI"]
key = os.environ["COSMOS_KEY"]
database_name = "iotdb"
container_name = "devicestate_v2"

client = CosmosClient(endpoint, credential=key)
database = client.get_database_client(database_name)
container = database.get_container_client(container_name)

def main(req: func.HttpRequest) -> func.HttpResponse:
    device_id = req.route_params.get("device_id")

    if not device_id:
        return func.HttpResponse("Device ID is required", status_code=400)

    # --- Get farmId from SQL API to use as Partition Key ---
    farm_id = None
    if SQL_API_URL:
        try:
            device_info_url = f"{SQL_API_URL}/api/devices/eui/{device_id}"
            logging.info(f"Querying for device info to get farmId: {device_info_url}")
            
            resp = requests.get(device_info_url)
            
            if resp.status_code == 404:
                logging.warning(f"Device EUI '{device_id}' not found in SQL database.")
                return func.HttpResponse(f"Device {device_id} not found.", status_code=404)
            
            resp.raise_for_status()
            
            device_info = resp.json()
            farm_id = device_info.get("farmID")

            if not farm_id:
                logging.error(f"SQL API response for device '{device_id}' did not contain a farmID.")
                return func.HttpResponse("Could not determine device's farm to query data.", status_code=500)

        except requests.exceptions.RequestException as e:
            logging.error(f"Could not retrieve device info for '{device_id}': {e}")
            return func.HttpResponse("Error communicating with backend service.", status_code=500)
        except json.JSONDecodeError:
            logging.error(f"Could not decode JSON response from device info endpoint for device '{device_id}'")
            return func.HttpResponse("Invalid response from backend service.", status_code=500)
    
    if not farm_id:
        logging.error("Could not determine farmId because SQL_API_URL is not set.")
        return func.HttpResponse("Server configuration error: cannot determine partition.", status_code=500)
        
    try:
        # Partition key is now the farmId
        logging.info(f"Reading item '{device_id}' from partition '{farm_id}'")
        device_data = container.read_item(item=device_id, partition_key=farm_id)
        return func.HttpResponse(json.dumps(device_data), mimetype="application/json", status_code=200)
    except Exception as e:
        # Check if the exception is due to item not found (typically a CosmosHttpResponseError with status 404)
        if hasattr(e, 'status_code') and e.status_code == 404:
            logging.warning(f"Device {device_id} with farmID {farm_id} not found in container {container_name}.")
            return func.HttpResponse(f"Device {device_id} not found.", status_code=404)
        
        logging.error(f"Error reading device {device_id} from container {container_name}: {str(e)}")
        return func.HttpResponse(f"Error retrieving data for device {device_id}.", status_code=500)
