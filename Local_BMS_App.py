import streamlit as st
import asyncio
import threading
import json
import time
from asyncua import Server
import paho.mqtt.client as mqtt

# ==========================================
# 1. IoT BACKGROUND ENGINE (OPC UA & MQTT)
# ==========================================

# We use @st.cache_resource to create a "Shared Dictionary" that 
# survives Streamlit reruns. The UI writes to it, the background thread reads from it.
@st.cache_resource
def get_shared_state():
    return {"Voltage": 250, "SoC": 50, "SoH": 98}

shared_state = get_shared_state()

# We use @st.cache_resource to ensure the servers only start ONCE
@st.cache_resource
def start_bms_background_task():
    def run_bms():
        # Setup an async loop for this specific thread (required for asyncua)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Initialize OPC UA Server
        server = Server()
        loop.run_until_complete(server.init())
        server.set_endpoint("opc.tcp://127.0.0.1:4840/freeopcua/server/")
        
        # Register Catena-X Namespace
        idx = loop.run_until_complete(server.register_namespace("urn:io.catenax.battery.dpp"))
        obj = loop.run_until_complete(server.nodes.objects.add_object(idx, "Battery_Pack"))
        
        # Create OPC UA Nodes
        v_node = loop.run_until_complete(obj.add_variable(idx, "Voltage", 0.0))
        soc_node = loop.run_until_complete(obj.add_variable(idx, "SoC", 0.0))
        soh_node = loop.run_until_complete(obj.add_variable(idx, "SoH", 0.0))
        
        loop.run_until_complete(server.start())
        print("OPC UA Server started on port 4840")
        
        # Initialize MQTT Client
        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        mqtt_client.connect("broker.hivemq.com", 1883, 60)
        mqtt_client.loop_start()
        print("MQTT Connected to broker.hivemq.com")
        
        try:
            while True:
                # 1. Read the latest values from your Streamlit UI Sliders
                current_v = float(shared_state["Voltage"])
                current_soc = float(shared_state["SoC"])
                current_soh = float(shared_state["SoH"])
                
                # 2. Update local OPC UA Server
                loop.run_until_complete(v_node.write_value(current_v))
                loop.run_until_complete(soc_node.write_value(current_soc))
                loop.run_until_complete(soh_node.write_value(current_soh))
                
                # 3. Publish to public MQTT Broker
                payload = {
                    "assetId": "EU240186EX2380002323",
                    "timestamp": time.time(),
                    "dynamicData": {
                        "voltage": current_v,
                        "stateOfCharge": current_soc,
                        "stateOfHealth": current_soh
                    }
                }
                mqtt_topic = "catenax/dpp/demo/bms_telemetry"
                mqtt_client.publish(mqtt_topic, json.dumps(payload))
                
                # Broadcast every 3 seconds
                time.sleep(3)
        finally:
            loop.run_until_complete(server.stop())

    # Start the engine in a daemon thread so it runs silently in the background
    thread = threading.Thread(target=run_bms, daemon=True)
    thread.start()
    return thread

# Trigger the engine to start
start_bms_background_task()

# ==========================================
# 2. YOUR STREAMLIT FRONT-END UI
# ==========================================

st.set_page_config(page_title="My Webpage", page_icon=":tada:", layout="wide")

## -- Header section ---
st.title("Better Together - DPP4.0 - Live Dynamic Battery DPP Demo")
st.subheader("A demo with Catena-X, OPCF, IDTA, ECLASS, Eclipse, ZVEI, VDMA,")
st.write("i am passionate about basttery DPP ")

# Wrapped in a try-except so your app doesn't crash if the image is missing from the folder
try:
    st.image('PowerPointHMI - DPP Demo HMI2026_V2.jpg')
except Exception:
    st.warning("Image 'PowerPointHMI - DPP Demo HMI2026_V2.jpg' not found in directory.")

st.sidebar.title("Sidebar")
st.sidebar.markdown("This is a Stremlit sidebar...place holders")

# Added status indicators so you know the backend is running
st.sidebar.divider()
st.sidebar.success("✅ **MQTT Active:** Publishing to broker.hivemq.com")
st.sidebar.success("✅ **OPC UA Active:** opc.tcp://127.0.0.1:4840")
st.sidebar.info("**MQTT Topic:** `catenax/dpp/demo/bms_telemetry`")

st.link_button("Visit Complete Static DPP", "https://eds.worldeds.com/dpp/index.html#/dppDetailLocal?sn&passportId=EU240186EX2380002323&model=&partNum=01076608")
st.link_button("Visit Huawei Digital Power", "https://solar.huawei.com/de/products/luna2000-7-14-21-s1/")

def clicked():
    st.write('Clicked')
    
x = st.button("click Me", on_click=clicked)
st.write(x)

st.divider()

# sliders to edit values (Notice how they update shared_state directly)
shared_state["Voltage"] = st.slider("BESS Voltage",
                min_value=10,
                max_value=800,
                value=shared_state["Voltage"],
                step=10,
                )
st.write(f"Voltage: {shared_state['Voltage']} V")

shared_state["SoC"] = st.slider("BESS Stage of Charge",
                min_value=0,
                max_value=100,
                value=shared_state["SoC"],
                step=1,
                )
st.write(f"SoC: {shared_state['SoC']} %")

shared_state["SoH"] = st.slider("BESS Stat of health",
                min_value=0,
                max_value=100,
                value=shared_state["SoH"],
                step=1,
                )
st.write(f"SoH: {shared_state['SoH']} %")
