import json
import logging
import azure.functions as func
import time

def main(documents: func.DocumentList,
         signalRMessages: func.Out[str]):

    logging.info("🚀 ChangeFeedToSignalR function triggered.")

    if not documents:
        logging.warning("Triggered with no documents.")
        return

    logging.info(f"Processing {len(documents)} changed document(s).")

    for doc in documents:
        try:
            logging.info(f"Processing document: {doc.to_json()}")
            
            farm_id = doc.get('farmID')
            device_id = doc.get('id')
            logging.info(f"Extracted farmID: '{farm_id}', deviceId: '{device_id}'")

            if farm_id and device_id:
                group_name = f"farm_{farm_id}"
                logging.info(f"Targeting SignalR group: '{group_name}'")
                
                device_payload = {
                    "deviceId": device_id,
                    "farmID": farm_id,
                    "battery_level": doc.get("battery_level"),
                    "location": doc.get("location"),
                    "timestamp": time.time()
                }
                logging.info(f"Constructed device payload: {json.dumps(device_payload)}")

                signalr_message_obj = {
                    "target": "updateDeviceState",
                    "arguments": [device_payload],
                    "groupName": group_name
                }
                
                final_json = json.dumps(signalr_message_obj)
                logging.info(f"Final SignalR JSON to be sent: {final_json}")

                signalRMessages.set(final_json)
                
                logging.info(f"✅ Successfully sent update for '{device_id}' to group '{group_name}'.")
            else:
                logging.warning(f"Document is missing 'id' or 'farmID'. Cannot send SignalR message.")
        except Exception as e:
            logging.error(f"❌ An error occurred while processing a document: {e}")
            logging.error(f"Problematic document was: {doc.to_json()}")
