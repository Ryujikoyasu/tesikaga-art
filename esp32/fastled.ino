#include <FastLED.h>

// --- Hardware Settings ---
// Set to the absolute maximum number of LEDs you might ever connect.
// This allows for flexible hardware configurations without reprogramming.
#define NUM_LEDS         1500 // Max LEDs for 5 strips (300 pixels/strip * 5 strips)
#define DATA_PIN         13   // Data output pin for ESP32
#define LED_TYPE         WS2811
#define COLOR_ORDER      GRB

// --- Communication Settings ---
#define BAUD_RATE        115200 // Must match Python script
#define SERIAL_TIMEOUT   100    // ms

// --- Safety Settings ---
#define MAX_BRIGHTNESS   80     // 0-255. Be careful with power consumption!

CRGB leds[NUM_LEDS];

const byte MAGIC_BYTE = 0x7E; // Must match Python script

void setup() {
  Serial.begin(BAUD_RATE);
  Serial.setTimeout(SERIAL_TIMEOUT);

  FastLED.addLeds<LED_TYPE, DATA_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection(TypicalLEDStrip);
  FastLED.setBrightness(MAX_BRIGHTNESS);

  FastLED.clear();
  FastLED.show();
}

void loop() {
  if (Serial.available() > 0 && Serial.read() == MAGIC_BYTE) {
    // The number of pixels to read is determined by the incoming data stream.
    // We expect NUM_PIXELS from the config, but the code is flexible.
    // For WS2811, each CRGB color (3 bytes) will control 3 physical LEDs.
    
    // Calculate how many bytes (pixels) are available to read from the serial buffer.
    int bytes_to_read = Serial.available();
    int pixels_to_read = bytes_to_read / 3;

    // Ensure we don't read more data than our buffer can hold.
    if (pixels_to_read > NUM_LEDS) {
        pixels_to_read = NUM_LEDS; 
    }

    // Read the available color data directly into the leds array.
    Serial.readBytes((char*)leds, pixels_to_read * 3);

    // Clear the rest of the LED strip.
    // This ensures that if a shorter signal is sent, old data is not displayed.
    for (int i = pixels_to_read; i < NUM_LEDS; i++) {
        leds[i] = CRGB::Black;
    }

    FastLED.show();
  }
}