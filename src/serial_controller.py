# --- START OF FILE: src/serial_controller.py ---

import serial
import time

class SerialController:
    """Manages the serial connection and data transmission to the microcontroller."""
    def __init__(self, port, baudrate=921600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.header = b'\xAA\x55'  # Magic bytes to indicate start of a frame

        try:
            print(f"Attempting to connect to {self.port} at {self.baudrate} bps...")
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(2)  # Wait for the serial connection to initialize
            print("Serial connection successful.")
        except serial.SerialException as e:
            print(f"FATAL: Could not open serial port {self.port}. Error: {e}")
            print("Please check the port name and ensure the device is connected.")
            self.ser = None

    def send_led_data(self, color_array):
        """
        Converts the numpy color array to a byte packet and sends it.
        Expected input: A numpy array of shape (900, 3) with dtype int.
        """
        if not self.is_connected():
            return

        try:
            # Flatten the array and convert to a byte string
            # IMPORTANT: The color order must match what the microcontroller expects (e.g., GRB)
            # The FastLED library on the ESP32 will be configured for GRB, so we swap R and G here.
            # color_array[:, [1, 0, 2]] creates a new array with Green, then Red, then Blue.
            byte_data = color_array[:, [1, 0, 2]].astype('uint8').tobytes()
            
            # Create the full packet with header
            packet = self.header + byte_data
            
            self.ser.write(packet)
        except Exception as e:
            print(f"ERROR: Failed to send data over serial. Error: {e}")
            self.close()

    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    def close(self):
        if self.is_connected():
            self.ser.close()
            print("Serial connection closed.")