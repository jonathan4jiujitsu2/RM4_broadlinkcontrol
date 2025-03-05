import time
import kasa
import openpyxl
import broadlink
import serial
import psycopg2
from datetime import datetime
from mcculw import ul
from mcculw.device_info import DaqDeviceInfo
from mcculw.enums import TempScale

# Database Connection
DB_HOST = "localhost"
DB_NAME = "hvac_data"
DB_USER = "postgres"
DB_PASS = "yourpassword"

def connect_db():
    try:
        return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
    except Exception as e:
        print(f"❌ DB Connection Failed: {e}")
        exit(1)

conn = connect_db()
cursor = conn.cursor()

# Device Configurations
DEVICE_NAME = "VERGA1"
ARDUINO_PORT = "COM7"
BAUD_RATE = 9600
PLUG_IP = "192.168.1.3"
TEMP_HIGH = 70
TEMP_LOW = 60
DAMPER_CLOSE_TEMP = 65
DAMPER_OPEN_TEMP = 75
CHECK_INTERVAL = 10

# Connect to Arduino
try:
    arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
    print(f"✅ Connected to Arduino on {ARDUINO_PORT}")
except Exception as e:
    print(f"❌ ERROR: Unable to connect to Arduino on {ARDUINO_PORT}: {e}")
    arduino = None

# Connect to Broadlink RM4 Mini
print("Searching for Broadlink devices...")
devices = broadlink.discover(timeout=5)
device = None
for dev in devices:
    if hasattr(dev, "name") and dev.name == DEVICE_NAME:
        device = dev
        break

if not device:
    print(f"❌ ERROR: Device '{DEVICE_NAME}' not found!")
    exit(1)

device.auth()
print(f"✅ Connected to {DEVICE_NAME}")

# Connect to Kasa Smart Plug KP115
plug = kasa.SmartPlug(PLUG_IP)

def read_temperature(board_num, channel):
    try:
        return round(ul.t_in(board_num, channel, TempScale.FAHRENHEIT), 2)
    except Exception as e:
        return f"Error reading from board {board_num}, channel {channel}: {e}"

def send_ir(command):
    ir_codes = {
        'Power On': b'&\x00P\x00\x00\x01 \x8f\x10\x13\x10\x13\x10\x13\x104\x104\x11\x12\x11\x12\x113\x104\x105\x104\x103\x11\x12\x114\x113\x10\x13\x104\x10\x13\x10\x13\x104\x113\x11\x12\x11\x12\x11\x12\x10\x13\x104\x105\x0f\x14\x0f\x13\x104\x113\x114\x0f\x00\x04Y\x00\x01 E\x0f\x00\r\x05',
        'Power Off': b'&\x00P\x00\x00\x01 \x8e\x11\x12\x11\x12\x11\x12\x114\x0f5\x10\x13\x10\x13\x103\x114\x104\x104\x105\x10\x13\x0f4\x113\x11\x12\x114\x0f\x14\x0f\x14\x0f5\x103\x11\x12\x11\x12\x11\x12\x11\x12\x114\x0f5\x10\x13\x10\x13\x103\x114\x104\x10\x00\x04Y\x00\x01\x1fD\x11\x00\r\x05'
    }
    if command in ir_codes:
        device.send_data(ir_codes[command])
        print(f"📡 Sent IR Command: {command}")

def send_damper_command(damper_num, command):
    if arduino:
        arduino.write(f"DAMPER{damper_num}_{command}\n".encode())
        print(f"🛠 Sent Damper {damper_num} Command: {command}")

def store_data(timestamp, board_num, channel, temperature, power_w, current_a, voltage_v, total_kwh, ac_state, damper_state):
    cursor.execute("""
        INSERT INTO sensor_data (timestamp, board_num, channel, temperature, power_w, current_a, voltage_v, total_kwh, ac_state, damper_state)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """, (timestamp, board_num, channel, temperature, power_w, current_a, voltage_v, total_kwh, ac_state, damper_state))
    conn.commit()

print("\n=== Starting Unified System ===")
ac_status = "OFF"
damper_status = ["CLOSED"] * 8

while True:
    for board_num in range(6):
        for channel in range(8):
            temp = read_temperature(board_num, channel)

            if isinstance(temp, str) and "Error" in temp:
                print(f"Board {board_num}, Channel {channel}: {temp}")
                continue

            plug.update()
            power_data = plug.emeter_realtime

            power_w = power_data["power_mw"] / 1000
            current_a = power_data["current_ma"] / 1000
            voltage_v = power_data["voltage_mv"] / 1000
            total_kwh = power_data["total_wh"] / 1000
            state = "ON" if power_w > 0 else "OFF"

            if temp > TEMP_HIGH and ac_status == "OFF":
                send_ir('Power On')
                ac_status = "ON"

            elif temp < TEMP_LOW and ac_status == "ON":
                send_ir('Power Off')
                ac_status = "OFF"

            if temp > DAMPER_OPEN_TEMP and damper_status[channel] == "CLOSED":
                send_damper_command(channel, "OPEN")
                damper_status[channel] = "OPEN"

            elif temp < DAMPER_CLOSE_TEMP and damper_status[channel] == "OPEN":
                send_damper_command(channel, "CLOSE")
                damper_status[channel] = "CLOSED"

            store_data(datetime.now(), board_num, channel, temp, power_w, current_a, voltage_v, total_kwh, ac_status, damper_status[channel])

    time.sleep(CHECK_INTERVAL)
