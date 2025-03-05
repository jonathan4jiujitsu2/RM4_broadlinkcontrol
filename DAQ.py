from mcculw import ul
from mcculw.device_info import DaqDeviceInfo
from mcculw.enums import TempScale, BoardInfo

# Function to read temperature from a specific channel
def read_temperature(board_num, channel):
    try:
        temp = ul.t_in(board_num, channel, TempScale.FAHRENHEIT)
        return round(temp, 2)
    except Exception as e:
        return f"Error reading from board {board_num}, channel {channel}: {e}"

# Detect connected USB-TC devices
print("=== Detecting USB-TC Devices ===")
usb_tc_boards = []

for board_num in range(6):  # Check up to 6 boards
    try:
        daq_dev_info = DaqDeviceInfo(board_num)
        if "USB-TC" in daq_dev_info.product_name:
            usb_tc_boards.append(board_num)
            print(f"Board #{board_num}: {daq_dev_info.product_name} (ID: {daq_dev_info.unique_id})")
        else:
            print(f"Board #{board_num}: {daq_dev_info.product_name} (Skipped)")
    except Exception as e:
        print(f"Board #{board_num}: Not Found - {e}")

# Read temperatures from USB-TC boards only
print("\n=== Reading Temperatures from USB-TC ===")
for board_num in usb_tc_boards:
    for channel in range(8):  # 8 channels per board
        temp = read_temperature(board_num, channel)
        if "Error 145" in str(temp):
            print(f"Board {board_num}, Channel {channel}: Open Connection (Check Thermocouple)")
        elif "Error" in str(temp):
            print(f"Board {board_num}, Channel {channel}: {temp}")
        else:
            print(f"Board {board_num}, Channel {channel}: {temp} °F")
