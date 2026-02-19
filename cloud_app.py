import streamlit as st
import paho.mqtt.client as mqtt
import json
import threading

st.set_page_config(page_title="Cloud DPP Dashboard", layout="wide")

# ==========================================
# 1. CLOUD MQTT SUBSCRIBER (Background Thread)
# ==========================================

# This stores the latest data received from the cloud broker
if "live_dpp_data" not in st.session_state:
    st.session_state.live_dpp_data = {
        "voltage": 0.0,
        "stateOfCharge": 0.0,
        "stateOfHealth": 0.0,
        "timestamp": "Waiting for data..."
    }

@st.cache_resource
def start_mqtt_subscriber():
    def on_connect(client, userdata, flags, reason_code, properties):
        print("Cloud Dashboard connected to HiveMQ!")
        client.subscribe("catenax/dpp/demo/bms_telemetry")

    def on_message(client, userdata, msg):
        try:
            # Parse the JSON payload sent by your local BMS_SIM
            payload = json.loads(msg.payload.decode())
            dynamic_data = payload.get("dynamicData", {})
            
            # Update the Streamlit state
            st.session_state.live_dpp_data["voltage"] = dynamic_data.get("voltage", 0)
            st.session_state.live_dpp_data["stateOfCharge"] = dynamic_data.get("stateOfCharge", 0)
            st.session_state.live_dpp_data["stateOfHealth"] = dynamic_data.get("stateOfHealth", 0)
            st.session_state.live_dpp_data["timestamp"] = payload.get("timestamp", "")
            
            print(f"Received Update: {dynamic_data}")
        except Exception as e:
            print(f"Error parsing message: {e}")

    def run_subscriber():
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect("broker.hivemq.com", 1883, 60)
        client.loop_forever()

    thread = threading.Thread(target=run_subscriber, daemon=True)
    thread.start()
    return thread

# Start the background listener
start_mqtt_subscriber()

# ==========================================
# 2. DPP HMI DASHBOARD (User Interface)
# ==========================================

st.title("🇪🇺 Digital Product Passport (DPP)")
st.subheader("Cloud Instance - Catena-X & ESPR Compliant")

# Static PLM Data (This would normally come from a database)
with st.expander("📦 Static Manufacturing Data (PLM)", expanded=True):
    col1, col2, col3 = st.columns(3)
    col1.metric("Manufacturer", "GreenEnergy EU")
    col1.metric("Battery Chemistry", "Lithium-Ion NMC")
    col2.metric("Asset ID", "EU240186EX2380002323")
    col2.metric("Nominal Capacity", "75 kWh")
    col3.metric("Production Date", "2025-11-12")
    col3.metric("CEN/CENELEC Standard", "JTC24")

st.divider()

# Dynamic Performance Data (Real-time from MQTT)
st.write("### 🔋 Live Battery Condition (Dynamic Data)")
st.caption(f"Last updated: {st.session_state.live_dpp_data['timestamp']}")

# We use an auto-refresh trick to make Streamlit update the UI when new data arrives
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=2000, key="data_refresh") # Refreshes the UI every 2 seconds

c1, c2, c3 = st.columns(3)

# Display the live values!
c1.metric(
    label="Operating Voltage", 
    value=f"{st.session_state.live_dpp_data['voltage']} V"
)
c2.metric(
    label="State of Charge (SoC)", 
    value=f"{st.session_state.live_dpp_data['stateOfCharge']} %"
)
c3.metric(
    label="State of Health (SoH)", 
    value=f"{st.session_state.live_dpp_data['stateOfHealth']} %"
)

st.success("Listening to public MQTT broker for live edge telemetry...")