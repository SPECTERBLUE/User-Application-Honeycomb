# USER-APPLICATION-HONEYCOMB

## 📌 Overview
USER-APPLICATION-HONEYCOMB is a Python-based application designed to **fetch, manage, and process IoT device data** from **ChirpStack**. The system dynamically updates the device list and decodes incoming sensor data using predefined codecs.  

### **🚀 Key Features**
- **Device Management**: Fetches and maintains a dictionary (`all_devices`) with devices and their codecs.
- **Event Processing**: Listens to MQTT events from ChirpStack and decodes device payloads.
- **Automatic Updates**: A scheduler ensures newly added devices are fetched periodically.
- **Modular Design**: Well-structured code for better maintainability.
- **Asymmetric Ciphering Support**: Supports **ECDH ciphering** for secure encryption and decryption of device data.

---

## **📂 Project Structure**
```
USER-APPLICATION-HONEYCOMB/
🕠 __pycache__/               # Compiled Python files
🕠 .venv/                     # Virtual environment (if used)
🕠 old_code/                  # Backup of previous versions
🕠 .gitignore                 # Git ignore rules
🕠 application_fetcher.py      # Fetches applications from ChirpStack
🕠 codec_fetcher.py           # Retrieves codec information for devices
🕠 config.py                  # Stores configuration variables
🕠 device_fetcher.py          # Fetches devices from ChirpStack
🕠 device_manager.py          # Manages device storage and updates
🕠 event_fetcher_parse.py     # Listens to MQTT events and decodes data
🕠 main.py                    # Starts the system (scheduler + MQTT listener)
🕠 README.md                  # Project documentation
🕠 requirements.txt           # Required dependencies
🕠 scheduler.py               # Periodically updates device list
🕠 tenant_fetcher.py          # Fetches tenants from ChirpStack
```

---

## **📦 Installation & Setup**
### **1️⃣ Prerequisites**
Ensure you have:
- Python **3.x**
- ChirpStack MQTT broker running
- `pip` installed

### **2️⃣ Clone the Repository**
```sh
git clone https://github.com/your-repo/user-application-honeycomb.git
cd user-application-honeycomb
```

### **3️⃣ Create a Virtual Environment (Recommended)**
```sh
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### **4️⃣ Install Dependencies**
```sh
pip install -r requirements.txt
```

### **5️⃣ Configure `config.py`**
Update `config.py` with your ChirpStack credentials:
```python
CHIRPSTACK_HOST = "localhost:8080"  # Update with your host
AUTH_METADATA = {"Authorization": "Bearer YOUR_TOKEN"}
```

---

## **🚀 How It Works**
### **🔹 Device Fetching & Management**
- `device_manager.py` **fetches and stores** devices in `all_devices` (key: `device_name`, value: `{euid, codec}`).
- `scheduler.py` **refreshes the device list every 10 minutes**.

### **🔹 MQTT Event Processing**
- `event_fetcher_parse.py` **subscribes to ChirpStack MQTT topics**.
- When an event arrives:
  - It extracts `dev_eui` and payload data.
  - It **matches `dev_eui` with `euid` in `all_devices`**.
  - It retrieves the **correct codec** and decodes the data.

---

## **📋 Running the Application**
Start the application by running:
```sh
python main.py
```
This will:
- Start **the scheduler** (to update the device list every 10 minutes).
- Start **the MQTT listener** (to process incoming sensor events).

---

## **⚙️ Code Breakdown**
### **1️⃣ `device_manager.py`**
Handles fetching and storing device information:
```python
device_manager.fetch_all_devices()  # Fetches all devices
device_manager.show_device_names()  # Displays the list of devices
```

### **2️⃣ `scheduler.py`**
Runs every **10 minutes** to update `all_devices`:
```python
schedule.every(10).minutes.do(scheduled_update)
```

### **3️⃣ `event_fetcher_parse.py`**
Listens for MQTT events and decodes messages:
```python
client.subscribe("application/+/device/+/event/+")
```
Matches `dev_eui` with `euid`:
```python
def get_device_codec(dev_eui):
    for device_name, device_info in device_manager.all_devices.items():
        if device_info.get("euid") == dev_eui:
            return device_info.get("codec")
    return None
```

---

## **🔧 Debugging & Logs**
Check **device updates**:
```sh
tail -f scheduler.log
```
Check **incoming MQTT messages**:
```sh
tail -f event_fetcher.log
```

---

## **📌 Future Enhancements**
- **Real-time WebSocket integration** for device updates.
- **Database storage** for historical events.
- **Custom decoders** for different device types.

---

## **📝 License**
This project is licensed under the **MIT License**.

---

## **👨‍💻 Contributing**
Pull requests are welcome! Open an issue for discussions.

