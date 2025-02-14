import paho.mqtt.client as mqtt
import base64
import json
import logging
import time
from device_manager import device_manager
from downlink import process_downlink_packet 
from key_rotation import KeyRotationManager

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# MQTT broker details
broker = "localhost"  # Replace with your ChirpStack MQTT broker address
port = 1883           # Default MQTT port (use 8883 for TLS)
topic = "application/+/device/+/event/up"  # Topic for all events

# Global State
last_rotation_time = 0  # Timestamp of the last key rotation
key_manager = None  # KeyRotationManager instance (initialized later)

def initialize_key_rotation(channel_input, auth_token_input):
    """Initialize KeyRotationManager before use."""
    global key_manager, channel, auth_token, last_rotation_time

    channel = channel_input
    auth_token = auth_token_input

    key_manager = KeyRotationManager(channel, auth_token)
    logger.info(" Key Rotation Manager initialized successfully.")


def on_connect(client, userdata, flags, rc):
    """Callback when the client connects to the MQTT broker."""
    if rc == 0:
        logger.info(f"Connected to MQTT broker at {broker}:{port} with result code {rc}")
        try:
            client.subscribe(topic)
            logger.info(f"Subscribed to topic: {topic}")
        except Exception as e:
            logger.error(f"Error subscribing to topic {topic}: {e}")
    else:
        logger.error(f"Failed to connect to MQTT broker, return code {rc}")

def get_device_codec(dev_eui):
    """Find the codec for a device based on dev_eui."""
    try:
        for device_name, device_info in device_manager.all_devices.items():
            if device_info.get("euid") == dev_eui:
                logger.debug(f"Device {dev_eui} matched with {device_name}, using codec: {device_info.get('codec')}")
                return device_info.get("codec")
        logger.warning(f"No codec found for device {dev_eui}")
        return None
    except Exception as e:
        logger.error(f"Error fetching codec for device {dev_eui}: {e}")
        return None

def on_message(client, userdata, msg):
    """Callback when a message is received."""
    global last_rotation_time, key_manager
    
    try:
        logger.debug(f"Message received on topic {msg.topic}")

        # Decode JSON payload
        payload = json.loads(msg.payload.decode("utf-8"))
        logger.debug(f"Decoded JSON payload: {payload}")

        # Extract required fields
        dr = payload.get("dr")
        f_cnt = payload.get("fCnt")
        f_port = payload.get("fPort")
        data_base64 = payload.get("data")
        dev_eui = payload["deviceInfo"].get("devEui")

        if not all([dr, f_cnt, f_port, data_base64, dev_eui]):
            logger.warning("Missing fields in payload")
            return

        # Decode Base64 data
        data_bytes = base64.b64decode(data_base64)
        data_hex = data_bytes.hex()
        
        # Append DevEUI info into the packet string for processing.
        packet = f"PORT:{f_port} RX:{data_hex} DevEUI:{dev_eui}"
        logging.info(f"packet :{packet}")
        
        # Call `process_downlink_packet` from `downlink.py`
        process_downlink_packet(packet)
        
        # Find codec for the device
        codec = get_device_codec(dev_eui)

        if codec:
            logger.info(f"Device {dev_eui} found. Using codec: {codec}")
            # decoded_data = codec.decode(data_hex)  # Implement decoding logic
            # logger.info(f"Decoded Data: {decoded_data}")
        else:
            logger.warning(f"No codec found for device {dev_eui}. Raw data: {data_hex}")

        # Log extracted information
        logger.info(f"DR: {dr}, FCnt: {f_cnt}, FPort: {f_port}, Data (Hex): {data_hex}")
        logger.info(f"Device EUI: {dev_eui}")
        
        # Check if 2 months have passed and trigger key rotation
        current_time = time.time()
        if current_time - last_rotation_time >= 5184000:  # 2 months in seconds
            logger.info("🔄 2 months passed. Initiating key rotation...")
            if key_manager:
                key_manager.rotate_keys()
                last_rotation_time = current_time  # Update timestamp
            else:
                logger.warning("KeyRotationManager not initialized!")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON message: {e}")
    except base64.binascii.Error as e:
        logger.error(f"Base64 decoding error: {e}")
    except KeyError as e:
        logger.error(f"Missing key in payload: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error processing message: {e}")

def start_mqtt_client():
    """Initialize and start the MQTT client."""
    try:
        client = mqtt.Client()

        # Assign callbacks
        client.on_connect = on_connect
        client.on_message = on_message

        logger.info("Connecting to MQTT broker...")
        client.connect(broker, port, 60)

        logger.info("Listening for device events...")
        client.loop_forever()

    except Exception as e:
        logger.exception(f"MQTT Client error: {e}")
