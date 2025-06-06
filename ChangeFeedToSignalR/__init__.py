import json
import logging
import azure.functions as func
import time

def main(documents: func.DocumentList,
         signalRMessages: func.Out[str]):

    if documents:
        logging.info(f"Change feed triggered for {len(documents)} document(s).")
        for doc in documents:
            farm_id = doc.get('farmID')
            device_id = doc.get('id')

            if farm_id:
                group_name = f"farm_{farm_id}"
                
                device_payload = {
                    "deviceId": device_id,
                    "farmID": farm_id,
                    "battery_level": doc.get("battery_level"),
                    "location": doc.get("location"),
                    "timestamp": time.time()
                }

                signalr_message_obj = {
                    "target": "updateDeviceState",
                    "arguments": [device_payload],
                    "groupName": group_name
                }

                signalRMessages.set(json.dumps(signalr_message_obj))
                
                logging.info(
                    f"✅ Sent device update for '{device_id}' to group '{group_name}'."
                )
            else:
                logging.warning(f"Document with id {doc.get('id')} is missing farmID. Cannot send SignalR message.")
