import json
import logging
import azure.functions as func
import time

def main(documents: func.DocumentList,
         signalRMessages: func.Out[str]):

    if documents:
        for doc in documents:
            logging.info(f'Document Id: {doc.get("id")}')
            farm_id = doc.get('farmID')
            device_id = doc.get('id')

            if farm_id:
                group_name = f"farm_{farm_id}"
                
                # Build a rich JSON payload so the client can use the fields directly
                device_payload = {
                    "deviceId": device_id,
                    "farmID": farm_id,
                    # Include additional fields if they exist in the document
                    "battery_level": doc.get("battery_level"),
                    "location": doc.get("location"),
                    "timestamp": time.time()
                }

                signalr_message_obj = {
                    "target": "updateDeviceState",
                    "arguments": [device_payload],
                    # send to everyone in the farm-specific group
                    "groupName": group_name
                }

                signalRMessages.set(json.dumps(signalr_message_obj))
                
                logging.info(
                    "Sent device update for '%s' to group '%s' with target 'updateDeviceState'.",
                    device_id,
                    group_name,
                )
            else:
                logging.warning(f"Document {device_id} is missing farmID. Cannot send SignalR message.")
