import azure.functions as func
import logging
import requests # For making HTTP requests
import jwt # For generating JWT for management API
import time
import os
# import urllib.parse # Not strictly needed if we construct URL carefully

def generate_management_token(audience: str, access_key: str, issuer: str = None, lifetime_seconds: int = 3600):
    """Generates a JWT token for authenticating with SignalR Management API."""
    payload = {
        'iat': int(time.time()),
        'exp': int(time.time()) + lifetime_seconds,
        'aud': audience,
    }
    if issuer:
        payload['iss'] = issuer
    logging.info(f"Generating token with audience: {audience}") # Log the audience
    token = jwt.encode(payload, access_key, algorithm='HS256')
    return token

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request for join_group.')

    user_id = req.params.get('userId')
    farm_id = req.params.get('farmId')
    connection_id = req.params.get('connectionId') # Client should send this after connecting

    if not (user_id or connection_id) or not farm_id:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            user_id = user_id or req_body.get('userId')
            farm_id = farm_id or req_body.get('farmId')
            connection_id = connection_id or req_body.get('connectionId')

    if not farm_id:
        return func.HttpResponse(
             "Please pass farmId in the query string or in the request body",
             status_code=400
        )
    if not user_id and not connection_id:
        return func.HttpResponse(
             "Please pass userId or connectionId",
             status_code=400
        )

    try:
        signalr_conn_str = os.environ["AzureSignalRConnectionString"]
        parts = dict(part.split('=', 1) for part in signalr_conn_str.split(';') if part)
        
        # Construct the base management API endpoint correctly
        service_hostname = parts['Endpoint'] # e.g., https://<name>.service.signalr.net
        if service_hostname.endswith('/'):
            service_hostname = service_hostname[:-1] # Remove trailing slash if present
        management_api_base = f"{service_hostname}/api/v1/"
        
        access_key = parts['AccessKey']
        hub_name = "iboihub"
        group_name = f"farm_{farm_id}"

        # Audience for management token is the hub URL
        audience_hub_url = f"{service_hostname}/hubs/{hub_name}" # Older docs sometimes used this, or just the hub itself
        # More robust audience for management API is often the API base itself or specific endpoint
        # Let's try with the management API base for the hub as audience, which is common
        token_audience = f"{management_api_base}hubs/{hub_name}"
        
        management_token = generate_management_token(token_audience, access_key)

        headers = {
            'Authorization': f'Bearer {management_token}',
            'Content-Type': 'application/json'
        }

        action_desc = ""
        management_url = ""
        
        if user_id:
            management_url = f"{management_api_base}hubs/{hub_name}/users/{user_id}/groups/{group_name}"
            action_desc = f"user {user_id}"
        elif connection_id:
            management_url = f"{management_api_base}hubs/{hub_name}/groups/{group_name}/connections/{connection_id}"
            action_desc = f"connection {connection_id}"
        else:
            return func.HttpResponse("Logic error: No identifier for group action.", status_code=500)

        # Set the audience to the specific management URL being called
        token_audience = management_url 
        management_token = generate_management_token(token_audience, access_key)

        headers = {
            'Authorization': f'Bearer {management_token}',
            'Content-Type': 'application/json'
        }

        logging.info(f"Attempting to PUT to SignalR Management API: {management_url}")
        response = requests.put(management_url, headers=headers)

        if 200 <= response.status_code < 300:
            logging.info(f"Successfully added {action_desc} to group {group_name}. Status: {response.status_code}")
            return func.HttpResponse(f"Added {action_desc} to group {group_name}.", status_code=response.status_code)
        else:
            logging.error(f"Error adding to group: {response.status_code} - {response.text}") # Log response.text for more details
            return func.HttpResponse(f"Error adding to group: {response.status_code} - {response.text}", status_code=response.status_code)

    except KeyError as e:
        logging.error(f"Missing configuration: {str(e)}")
        return func.HttpResponse("Server configuration error.", status_code=500)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        return func.HttpResponse("An internal server error occurred.", status_code=500) 