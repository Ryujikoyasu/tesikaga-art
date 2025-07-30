# 屈斜路の響き - インタラクティブ・ライトアート

![Artistic View](https://i.imgur.com/your-screenshot-url.png) <!-- ここにシミュレーターのスクリーンショット画像を後で貼ると見栄えが良くなります -->

北海道・弟子屈町の自然をテーマにした、来場者参加型のインタラクティブアート作品のシミュレーション兼制御ソフトウェアです。来場者の動きを（最終的には）LiDARで検知し、その存在が「小鳥」として表現される光と音の群れに影響を与えます。

テクノロジーを通じて、人と自然の繊細な関わり合いを詩的に表現することを目指します。

## ✨ こだわりのポイント (Features & Highlights)

このプロジェクトは、単なるシミュレーターではなく、アーティスティックな表現を探求するための様々な工夫が凝らされています。

#### 1. 生命感を生むALifeシミュレーション
鳥たちは、単にランダムに動くのではありません。`src/objects.py`で定義されたAIに基づき、それぞれが持つ「好奇心」「警戒心」などのパラメータに従って自律的に行動します。人間が静かにしていれば近づいてきたり、急に動けば驚いて飛び去ったりと、まるで本当に生きているかのようなインタラクションを体験できます。

#### 2. 作者の筆跡を宿すLEDレイアウト
LEDテープの物理的な配置は、`scripts/artistic_path_generator.py`によって生成されます。これは、アーティストが対話的に「一筆書き」で描いた芸術的な曲線を、物理的な制約（全長、電源位置）を満たすようにコンピュータが微調整する、人間と機械の協調作業です。これにより、作品には作者ならではの「筆跡」が宿ります。

#### 3. 鳴き声と完全に同期する光の明滅
`scripts/audio_sync_generator.py`は、`librosa`ライブラリを用いて鳥の音声ファイルを自動で解析し、鳴き声のリズムや音の山に合わせた輝度パターンを`config.py`に自動生成します。これにより、クマゲラのドラミングの連打や、オオルリの美声の伸びやかさが、極めて音楽的に光の明滅として表現されます。

#### 4. 物理的制約を逆手に取った色彩表現
12VのWS2811 LEDテープは「3つのLEDが1ピクセル」という制約を持ちますが、これを逆手に取り、より複雑な色彩表現を実現しました。鳥の色は`base_color`（基本色）と`accent_color`（差し色）の組み合わせで定義され、その構成パターン（例：`[ベース, アクセント, ベース]`）も鳥ごとに設計されています。これにより、タンチョウの「白の中に輝く赤」といった、よりシンボリックで洗練された視覚表現を可能にしています。

#### 5. 堅牢な設定管理アーキテクチャ
プロジェクトの設定は、役割に応じて明確に分離されています。
- **`settings.yaml`**: PC環境やハードウェア固有の設定（シリアルポートなど）。ユーザーが環境に合わせて編集します。
- **`src/config_structure.py`**: 鳥の性格や色など、作品の根幹をなす不変のパラメータの原本。
- **`src/config.py`**: 上記2つを元に`audio_sync_generator.py`が**自動生成する設定ファイル**。これにより、手動編集によるミスを防ぎ、誰でも安全に環境を再現できます。

## 📂 ファイル構成

```
tesikaga-art/
├── main.py                 # シミュレーションのみを実行（デバッグ・開発用）
├── main_real.py            # シミュレーションを実行し、Arduinoへリアルタイムでデータを送信（本番用）
├── settings.yaml           # ★ユーザーが編集する主要な設定ファイル
├── requirements.txt        # 必要なPythonライブラリ
├── README.md               # このファイル
│
├── src/                    # ソースコード
│   ├── objects.py          # HumanとBirdのクラス定義（AIの心臓部）
│   ├── config.py           # 【自動生成】される設定ファイル
│   └── config_structure.py # 鳥のパラメータの原本
│
├── assets/                 # プログラムが使用する素材
│   ├── sounds/             # 鳥の鳴き声の音声ファイル
│   └── data/               # LEDの物理的な座標データファイル
│
├── scripts/                # 補助的なスクリプト
│   ├── artistic_path_generator.py # LEDの座標データを対話的に生成
│   └── audio_sync_generator.py    # 音声ファイルを解析してconfig.pyを生成
│
└── arduino/                # Arduino用のスケッチ
    └── tesikaga_led_controller.ino
```

## 🚀 使い方 (Setup & Usage)

#### 1. Python環境のセットアップ
`requirements.txt`に記載されたライブラリをインストールします。（`pygame-ce`, `numpy`, `pyserial`, `pyyaml`, `librosa`, `matplotlib`などが必要です）

```bash
pip install -r requirements.txt```

#### 2. Arduinoのセットアップ
1.  Arduino IDEに`FastLED`ライブラリをインストールします。
2.  `arduino/tesikaga_led_controller.ino`をArduino Uno R4に書き込みます。
3.  LEDテープを正しく接続します（データ線→ピン6, 12V電源, GND共通化）。

#### 3. プロジェクトの設定
1.  **`settings.yaml`** を開き、自分の環境に合わせて`serial_port`などを正しく設定します。
2.  テストを行う場合は`enable_test_mode`を`true`にし、`test_strip_led_count`に使用するLEDの数を設定します。

#### 4. 実行手順
**この順番で実行することが重要です。**

1.  **LEDレイアウトの生成（初回のみ、または変更時）**
    `scripts/artistic_path_generator.py`を実行し、画面の指示に従って対話的にLEDの配置をデザインし、保存します。

    ```bash
    python scripts/artistic_path_generator.py
    ```

2.  **設定ファイルの生成（初回、または音声・鳥パラメータ変更時）**
    `scripts/audio_sync_generator.py`を実行します。これにより、音声ファイルが解析され、最新の`src/config.py`が自動生成されます。

    ```bash
    python scripts/audio_sync_generator.py
    ```

3.  **シミュレーションの実行**
    *   ハードウェアなしで動きを確認する場合：
        ```bash
        python main.py
        ```
    *   Arduinoに接続してLEDをリアルタイムで光らせる場合：
        ```bash
        python main_real.py
        ```

## 🛠️ 主要技術スタック
- **Python 3.11+**
- **Pygame-ce**: シミュレーションの描画と音声再生
- **NumPy**: 高速なベクトル・配列計算
- **Matplotlib**: LEDパスの対話的生成
- **Librosa**: 音声ファイルの解析
- **PyYAML**: 設定ファイルの管理
- **PySerial**: Arduinoとのシリアル通信
- **Arduino / C++**: LEDコントローラー
- **FastLED**: 高速なLED駆動ライブラリ

## 🔮 次のステップ
- [ ] LiDARセンサーとの接続を実装し、マウス操作を現実世界の人の動きに置き換える。