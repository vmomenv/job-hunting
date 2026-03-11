import os
from src.adb_utils import AdbController
from src.controller import DeviceController

print("Testing AdbController")
adb_ctrl = AdbController()
print(f"ADB path: {adb_ctrl.adb_path}")
print(f"Device connected: {adb_ctrl.check_connection()}")
print(f"Devices list: {adb_ctrl.get_devices()}")

print("\nTesting DeviceController")
dev_ctrl = DeviceController()
print(f"Connect status: {dev_ctrl.connect()}")
