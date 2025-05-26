import logging
import azure.functions as func
from azure.cosmos import CosmosClient
import os
import json

COSMOS_URI = os.environ["COSMOS_URI"]
COSMOS_KEY = os.environ["COSMOS_KEY"]
DB_NAME = "iotdb"
CONTAINER_NAME = "devicestate_v2"

client = CosmosClient(COSMOS_URI, COSMOS_KEY)
container = client.get_database_client(DB_NAME).get_container_client(CONTAINER_NAME)

def main(req: func.HttpRequest) -> func.HttpResponse:
    farm_id = req.route_params.get("farm_id")
    if not farm_id:
        return func.HttpResponse("Missing farm_id", status_code=400)

    query = "SELECT * FROM c WHERE c.farmId = @farmId"
    parameters = [{"name": "@farmId", "value": farm_id}]

    try:
        results = list(container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        return func.HttpResponse(json.dumps(results), mimetype="application/json")
    except Exception as e:
        logging.error(f"Query failed: {e}")
        return func.HttpResponse("Error querying Cosmos DB", status_code=500)
