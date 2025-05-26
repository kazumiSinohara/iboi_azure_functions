import json
import azure.functions as func
import logging


def main(
    req: func.HttpRequest,
    connectionInfo  # This is the input binding
) -> func.HttpResponse:

    logging.info(f"Negotiate: connectionInfo type from binding: {type(connectionInfo)}")
    
    body_to_return = ""
    if isinstance(connectionInfo, str):
        # If it's already a string, assume it's a JSON string and pass it through
        logging.info("Negotiate: connectionInfo is already a string, passing through.")
        body_to_return = connectionInfo
    elif isinstance(connectionInfo, dict):
        # If it's a dict, dump it to a JSON string
        logging.info("Negotiate: connectionInfo is a dict, dumping to JSON string.")
        body_to_return = json.dumps(connectionInfo)
    else:
        # Fallback or error if it's an unexpected type
        logging.error(f"Negotiate: connectionInfo is an unexpected type: {type(connectionInfo)}")
        # Attempt to dump it anyway, or return an error
        try:
            body_to_return = json.dumps(connectionInfo)
        except TypeError:
            return func.HttpResponse("Error processing connection info.", status_code=500)

    return func.HttpResponse(
        body_to_return,
        mimetype="application/json"
    )
