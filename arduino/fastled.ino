/**
 * Tesikaga Interactive Art - Final LED Controller
 * 
 * This sketch works with the Python simulation application.
 * It receives color data for "logical pixels" via Serial and expands it
 * to control a WS2811 (12V) strip where 1 pixel drives 3 physical LEDs.
 * 
 * It is designed to be robust, automatically synchronizing with the data stream.
 */

 #include <FastLED.h>

 // =========================================================================
 // === CONFIGURATION - 環境に合わせてこれらの値を変更してください ===
 // =========================================================================
 
 // --- LED Strip Hardware Settings ---
 // あなたがArduinoに接続している物理的なLEDの総数
 // テスト用ストリップなら 100, 400 など。本番環境なら 900, 1200 など。
 #define NUM_PHYSICAL_LEDS    300      
 
 #define DATA_PIN             6        // Arduinoのデータピン番号
 #define LED_TYPE             WS2811   // LEDストリップのチップセット
 #define COLOR_ORDER          BRG      
 
 // --- Communication Settings ---
 // Pythonのsettings.yamlにある値と完全に一致させる必要があります
 #define BAUD_RATE            921600   // 通信速度
 #define MAGIC_BYTE           0x7E     // '˜' - データフレームの開始を識別するバイト
 
 // =========================================================================
 // === DO NOT EDIT BELOW THIS LINE - 以下のコードは編集不要です ===
 // =========================================================================
 
 // 制御可能なピクセル数を計算 (1ピクセル = 3 LED)
//  const int NUM_PIXELS = (NUM_PHYSICAL_LEDS + 2) / 3;
 const int NUM_PIXELS = NUM_PHYSICAL_LEDS;
 
 // FastLEDライブラリ用のLED配列 (物理LED数で確保)
 CRGB leds[NUM_PHYSICAL_LEDS];
 
 // PCからのデータを受信するためのバッファ (ピクセル数で確保)
 byte buffer[NUM_PIXELS * 3]; 
 
 void setup() {
   // シリアル通信を開始
   Serial.begin(BAUD_RATE);
 
   // FastLEDを初期化
   // 電圧による色補正を無効にするため、テンプレート引数の最後に .setCorrection(Uncorrected) を追加
   FastLED.addLeds<LED_TYPE, DATA_PIN, COLOR_ORDER>(leds, NUM_PHYSICAL_LEDS)
       .setCorrection(TypicalSMD5050); // 標準的な補正
 
   // 明るさの最大値を設定 (安全のため、最初は低い値 (例: 80) を推奨)
   FastLED.setBrightness(80); 
   
   // 起動時にLEDを一度クリア
   FastLED.clear();
   FastLED.show();
 
   // 起動確認用のテストアニメーション (起動時に青い光が走る)
   for(int i = 0; i < NUM_PHYSICAL_LEDS; i++) {
     leds[i] = CRGB::Blue;
     FastLED.show();
     delay(5);
   }
   FastLED.clear();
   FastLED.show();
 }
 
 void loop() {
   // データが利用可能かチェック
   if (Serial.available() > 0) {
     
     // 1. ストリームの同期：マジックバイトを探す
     //    これにより、途中でデータが欠落しても、次のフレームから正しく同期できる
     if (Serial.read() == MAGIC_BYTE) {
       
       // 2. データフレームの受信
       //    readBytesは、指定したバイト数が受信されるか、タイムアウトするまで待機する
       int bytesRead = Serial.readBytes(buffer, NUM_PIXELS * 3);
       
       // 3. データ長の検証
       //    期待通りの長さのデータを受信した場合のみ、LEDを更新する
       if (bytesRead == NUM_PIXELS * 3) {
         
         // 4. ピクセルデータを物理LEDに展開
         for (int i = 0; i < NUM_PIXELS; i++) {
           // バッファからi番目のピクセルの色(R, G, B)を読み込む
           CRGB pixelColor = CRGB(buffer[i * 3], buffer[i * 3 + 1], buffer[i * 3 + 2]);
           
           // 1つのピクセルカラーを、3つの連続した物理LEDにセットする
           int led_index1 = i * 3;
           int led_index2 = i * 3 + 1;
           int led_index3 = i * 3 + 2;
 
           // 配列の範囲外に書き込まないように、安全チェックを行う
           if (led_index1 < NUM_PHYSICAL_LEDS) {
             leds[led_index1] = pixelColor;
           }
           if (led_index2 < NUM_PHYSICAL_LEDS) {
             leds[led_index2] = pixelColor;
           }
           if (led_index3 < NUM_PHYSICAL_LEDS) {
             leds[led_index3] = pixelColor;
           }
         }
         
         // 5. LEDストリップ全体を一度に更新！
         FastLED.show();
       }
     }
     // マジックバイトでなければ、そのデータは無視して次の同期を待つ
   }
 }