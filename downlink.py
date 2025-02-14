import logging
from key_rotation import KeyManager, SharedKey, SensorCrypto
from binascii import hexlify

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for detailed logs
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Initialize UA Key Manager (generates private/public key pair)
ua_key_manager = KeyManager()
last_rotation_time = 0  # Timestamp for last key rotation

# Store device-specific encryption keys
device_public_keys = {}  # Example: {"2cf7f12052608e69": <ED public key>}
device_crypto = {}  # Stores SensorCrypto instances keyed by DevEUI

class DownlinkReassembler:
    """Handles reassembly of segmented downlink messages."""
    
    MAX_SEGMENT_LENGTH = 128  # Adjust as needed
    
    def __init__(self):
        """Initialize segmented message tracking."""
        self.segmented_message = {
            "type": None,
            "total": 0,
            "received": 0,
            "payload": ""
        }

    def reassemble_segment(self, segment: str) -> str:
        """
        Processes incoming segments and reassembles the full message when all parts are received.

        :param segment: The received segment string.
        :return: The full reassembled message when complete, otherwise an empty string.
        """
        logging.debug(f"Processing segment: {segment}")

        if segment.startswith("SEG"):
            try:
                # Extract header and payload
                header, payload = segment.split(":", 1)
                header = header[3:]  # Remove "SEG" prefix
                seg_num, total_segments = map(int, header.split("/"))

                # Initialize segmented message tracking if it's the first segment
                if self.segmented_message["type"] is None:
                    self.segmented_message["type"] = "PUBKEY"
                    self.segmented_message["total"] = total_segments
                    self.segmented_message["received"] = 0
                    self.segmented_message["payload"] = ""

                # Append the payload
                self.segmented_message["payload"] += payload
                self.segmented_message["received"] += 1

                logging.info(f"Received segment {seg_num}/{total_segments}")

                # If all segments are received, return the full message
                if self.segmented_message["received"] == self.segmented_message["total"]:
                    full_message = self.segmented_message["payload"]

                    # Reset for the next segmented message
                    self.segmented_message = {
                        "type": None,
                        "total": 0,
                        "received": 0,
                        "payload": ""
                    }

                    logging.info("Reassembly complete. Returning full message.")
                    return full_message

            except ValueError as ve:
                logging.error(f"Error parsing segment header: {ve}", exc_info=True)
            except Exception as e:
                logging.error(f"Unexpected error during reassembly: {e}", exc_info=True)

        else:
            logging.debug("Received a non-segmented message.")
            return segment  # Return non-segmented messages as-is

        return ""  # Return empty if reassembly is incomplete

def process_downlink_packet(packet: str):
    """
    Processes a received downlink packet, extracts the necessary fields, and handles key updates or sensor data.

    :param packet: The downlink packet string.
    """
    global device_public_keys, device_crypto, ua_key_manager

    logging.info(f"Processing downlink packet: {packet}")
    
    try:
        # Assume packet format: "PORT:<port> RX:<data> DevEUI:<dev_eui>"
        port_index = packet.index("PORT:")
        data_index = packet.index("RX:")
        dev_eui_index = packet.index("DevEUI:")

        port_str = packet[port_index+5:data_index].strip()
        port = int(port_str)
        data = packet[data_index+3:dev_eui_index].strip()
        dev_eui = packet[dev_eui_index+7:].strip()

        # Remove any surrounding quotes
        if data.startswith("\""):
            data = data[1:]
        if data.endswith("\""):
            data = data[:-1]

    except Exception as e:
        logging.error(f"Error parsing downlink packet: {e}", exc_info=True)
        return

    if port == 76:
        logging.info(f"Received new UA public key on FPort 76 for device {dev_eui}: {data}")

    elif port == 10:
        logging.info(f"Acknowledgement received on FPort 10 for device {dev_eui}: {data}")

    elif port == 26:
        logging.info(f"Received ED public key update on FPort 26 for device {dev_eui}: {data}")
        
        reassembler = DownlinkReassembler()
        if data.startswith("SEG"):
            full_payload = reassembler.reassemble_segment(data)
            if full_payload and full_payload.startswith("PUBKEY:"):
                new_ed_pub = full_payload[7:]
                logging.info(f"Reassembled ED public key for device {dev_eui}: {new_ed_pub}")
        else:
            if data.startswith("PUBKEY:"):
                new_ed_pub = data[7:]
                logging.info(f"ED public key update received for device {dev_eui}: {new_ed_pub}")

        if len(new_ed_pub) == 130:
            device_public_keys[dev_eui] = new_ed_pub
            try:
                sk = SharedKey(ua_key_manager.get_private_key(), new_ed_pub)
                device_crypto[dev_eui] = SensorCrypto(sk.get_shared_secret())
                logging.info(f"Updated shared secret for device {dev_eui}")
            except Exception as e:
                logging.error(f"Error updating shared secret for device {dev_eui}: {e}", exc_info=True)
        else:
            logging.warning(f"Invalid ED public key length for device {dev_eui}: {len(new_ed_pub) // 2} bytes")

    else:
        # Assume sensor data on FPorts 1–25.
        if dev_eui not in device_crypto:
            logging.warning(f"No SensorCrypto available for device {dev_eui} -> cannot decrypt sensor data.")
            return

        sc = device_crypto[dev_eui]
        try:
            decrypted_data = sc.decrypt(data)
            logging.info(f"Decrypted Sensor Data for device {dev_eui}: {decrypted_data}")
        except Exception as e:
            logging.error(f"Decryption failed for device {dev_eui}: {e}", exc_info=True)
