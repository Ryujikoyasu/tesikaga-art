// --- START OF FILE: ESP32_LED_Receiver.ino ---

#include <FastLED.h>

// --- LED Configuration ---
#define NUM_LEDS         900  // Total number of LEDs (3 strips * 300 LEDs/strip)
#define DATA_PIN         4    // The GPIO pin on the ESP32 connected to the LED data line
#define BRIGHTNESS       200  // Global brightness limit (0-255). A safety measure.
#define LED_TYPE         WS2811
#define COLOR_ORDER      GRB  // IMPORTANT: This must match the order in the Python script

// --- Communication Configuration ---
#define BAUD_RATE        921600 // IMPORTANT: Must match the Python script
#define SERIAL_TIMEOUT   100   // Milliseconds to wait for data before resetting

// This is the buffer that FastLED uses to control the LEDs
CRGB leds[NUM_LEDS];

// --- Setup Function: Runs once on boot ---
void setup() {
  Serial.begin(BAUD_RATE);
  Serial.setTimeout(SERIAL_TIMEOUT);

  // Initialize the LED strip
  FastLED.addLeds<LED_TYPE, DATA_PIN, COLOR_ORDER>(leds, NUM_LEDS)
         .setCorrection(TypicalLED5mm); // Apply color correction typical for 5050 LEDs
  FastLED.setBrightness(BRIGHTNESS);

  // Indicate that the setup is complete and ready to receive data
  fill_solid(leds, NUM_LEDS, CRGB::Black);
  FastLED.show();
  delay(500);
  fill_solid(leds, NUM_LEDS, CRGB::Blue); // Show blue to indicate "Ready"
  FastLED.show();
  delay(1000);
  fill_solid(leds, NUM_LEDS, CRGB::Black);
  FastLED.show();
}

// --- Main Loop: Runs continuously ---
void loop() {
  // State machine for robustly reading serial data
  enum class State {
    WAIT_FOR_HEADER_1,
    WAIT_FOR_HEADER_2,
    READ_DATA
  };
  static State currentState = State::WAIT_FOR_HEADER_1;

  switch (currentState) {
    case State::WAIT_FOR_HEADER_1:
      // Wait for the first magic byte (0xAA)
      if (Serial.available() > 0 && Serial.read() == 0xAA) {
        currentState = State::WAIT_FOR_HEADER_2;
      }
      break;

    case State::WAIT_FOR_HEADER_2:
      // Wait for the second magic byte (0x55)
      if (Serial.available() > 0) {
        if (Serial.read() == 0x55) {
          currentState = State::READ_DATA;
        } else {
          // If we get the wrong byte, go back to waiting for the first one
          currentState = State::WAIT_FOR_HEADER_1;
        }
      }
      break;

    case State::READ_DATA:
      // Check if we have enough bytes for a full frame
      if (Serial.available() >= NUM_LEDS * 3) {
        // Read the color data directly into the FastLED buffer
        // This is highly efficient.
        Serial.readBytes((char*)leds, NUM_LEDS * 3);
        
        // Update the physical LEDs with the new data
        FastLED.show();
        
        // Go back to the start to wait for the next frame
        currentState = State::WAIT_FOR_HEADER_1;
      }
      break;
  }
}