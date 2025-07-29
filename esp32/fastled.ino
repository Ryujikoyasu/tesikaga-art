#include <FastLED.h>

// --- ハードウェア設定 (ご自身の環境に合わせて変更) ---
#define NUM_LEDS         100  // 今回使用するLEDの数
#define DATA_PIN         13   // ESP32のデータ出力ピン (例: GPIO13)
#define LED_TYPE         WS2812B // 一般的なLEDテープの型番
#define COLOR_ORDER      GRB     // GRBまたはRGB。色が正しくなければここを変更

// --- 通信設定 ---
#define BAUD_RATE        230400 // PCとの通信速度。高速でないとカクつきます
#define SERIAL_TIMEOUT   100   // データ受信のタイムアウト(ミリ秒)

// --- 安全設定 (非常に重要！) ---
#define MAX_BRIGHTNESS   60    // 最大の明るさ (0-255)。最初は低い値(30-60)で！
                               // 300個のLEDをフルパワーで光らせると15A以上流れる可能性があります。
                               // 必ず適切な電源を使用してください。

// FastLEDライブラリ用のLED配列を定義
CRGB leds[NUM_LEDS];

// フレームの開始を告げる「マジックバイト」
const byte MAGIC_BYTE = 0xAB;

void setup() {
  // シリアル通信を開始
  Serial.begin(BAUD_RATE);
  Serial.setTimeout(SERIAL_TIMEOUT);

  // FastLEDを初期化
  FastLED.addLeds<LED_TYPE, DATA_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection(TypicalLEDStrip);
  
  // 安全のための最大輝度設定
  FastLED.setBrightness(MAX_BRIGHTNESS);

  // 起動時にテストパターンを点灯
  for(int i = 0; i < NUM_LEDS; i++) {
    leds[i] = CRGB::Black;
  }
  FastLED.show();
  delay(500);
  for(int i = 0; i < 3; i++) {
    leds[i] = CRGB::Red; leds[NUM_LEDS - 1 - i] = CRGB::Blue;
  }
  FastLED.show();
}

void loop() {
  // 1. フレームの開始（マジックバイト）を待つ
  if (Serial.available() > 0) {
    if (Serial.read() == MAGIC_BYTE) {
      
      // 2. マジックバイトが来たら、LEDデータ(300個 * 3色 = 900バイト)を受信する
      // readBytesは、指定したバイト数を読み込むか、タイムアウトするまで待機します。
      size_t bytesRead = Serial.readBytes((char*)leds, NUM_LEDS * 3);
      
      // 3. 全てのデータを受信できたら、LEDを更新する
      if (bytesRead == NUM_LEDS * 3) {
        FastLED.show();
      }
      // データが足りない場合は、次のマジックバイトまで破棄して同期を取り直す
    }
  }
}