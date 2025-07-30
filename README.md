屈斜路の響き - インタラクティブ・ライトアート

![alt text](httpss://i.imgur.com/your-screenshot-url.png)

<!-- ここにシミュレーターのスクリーンショット画像を貼ると見栄えが良くなります -->

北海道・弟子屈町の自然をテーマにした、来場者参加型のインタラクティブアート作品のシミュレーション兼制御ソフトウェアです。来場者の動きを（最終的には）LiDARで検知し、その存在が「小鳥」として表現される光と音の群れに影響を与えます。

テクノロジーを通じて、人と自然の繊細な関わり合いを詩的に表現することを目指します。
✨ こだわりのポイント (Features & Highlights)

このプロジェクトは、単なるシミュレーターではなく、アーティスティックな表現と技術的な堅牢性を両立させるための様々な工夫が凝らされています。
1. 生命感を生むALifeシミュレーションエンジン

鳥たちは、単にランダムに動くのではありません。src/objects.pyで定義されたステートマシンに基づき、それぞれが持つ個性（好奇心、警戒心など）に従って自律的に行動します。人間が静かにしていれば近づき、急に動けば驚いて飛び去る。その場の状況に応じて行動を決定するAIが、予測不能で生命感あふれるインタラクションを生み出します。
2. 作者の筆跡を宿すLEDレイアウト生成

LEDテープの物理的な配置は、scripts/artistic_path_generator.pyによって対話的に生成されます。これは、アーティストが「一筆書き」で描いた芸術的な曲線を、物理的な制約（全長、電源位置）を満たすようにコンピュータがリアルタイムで補正する、人間と機械の協調作業です。これにより、作品には作者ならではの「筆跡」や意図が宿ります。
3. 音楽と完全に同期する光の自動生成

scripts/audio_sync_generator.pyは、librosaライブラリを用いて鳥の音声ファイルを自動で解析し、鳴き声のリズムや音の山に合わせた輝度パターンをsrc/config.pyに自動生成します。クマゲラのドラミングの連打や、オオルリの伸びやかな美声が、手作業では不可能なレベルで音楽的に光の明滅として表現されます。
4. 堅牢な3層設定アーキテクチャ

プロジェクトの設定は、役割に応じて明確に分離され、安全かつ柔軟な運用を可能にしています。

    settings.yaml: PC環境やハードウェア固有の設定（シリアルポートなど）。ユーザーが環境に合わせて編集します。

    src/config_structure.py: 鳥の性格や色など、作品の根幹をなす芸術的パラメータの「原本」。

    src/config.py: 上記2つを元にaudio_sync_generator.pyが自動生成する最終設定ファイル。手動編集によるミスを防ぎ、誰でも安全に環境を再現できます。

5. 高性能・高信頼なリアルタイム通信

PCとArduino間の通信は、長時間の安定稼働を前提に設計されています。

    非同期書き込み (Python): main_real.pyのSerialWriterThreadが、シリアル通信を別スレッドで実行。これにより、描画ループが通信遅延の影響を受けず、60fpsを安定して維持します。

    フレーム同期 (Arduino): Arduino側では、各データフレームの先頭に付与されたMAGIC_BYTEを常に監視。万が一データが欠落しても、次のフレームから自動的に同期を回復し、表示の破綻を防ぎます。

📂 ファイル構成
Generated code

      
tesikaga-art/
├── README.md
├── main.py                 # シミュレーションのみを実行（開発用）
├── main_real.py            # シミュレーションとArduinoへのリアルタイム送信を実行（本番用）
├── settings.yaml           # ★ユーザーが編集する主要な設定ファイル
├── requirements.txt        # 必要なPythonライブラリ
│
├── assets/
│   ├── data/               # led_positions_...csv (LED座標データ)
│   └── sounds/             # 鳥の鳴き声の音声ファイル (.mp3)
│
├── src/                    # メインのソースコード
│   ├── objects.py          # HumanとBirdクラスの定義 (AIの心臓部)
│   ├── simulation.py       # Worldクラスの定義 (物理法則・境界などのルール)
│   ├── config.py           # 【自動生成】される設定ファイル (編集しない)
│   └── config_structure.py # 鳥のパラメータの原本
│
├── scripts/                # 補助的なユーティリティスクリプト
│   ├── artistic_path_generator.py # LEDの座標データを対話的に生成
│   └── audio_sync_generator.py    # 音声ファイルを解析してconfig.pyを生成
│
└── arduino/                # Arduino用のスケッチ
    └── tesikaga_led_controller.ino

    

IGNORE_WHEN_COPYING_START
Use code with caution.
IGNORE_WHEN_COPYING_END
🚀 使い方 (Setup & Usage)
1. Python環境のセットアップ

requirements.txtに記載されたライブラリをインストールします。
Generated bash

      
pip install -r requirements.txt

    

IGNORE_WHEN_COPYING_START
Use code with caution. Bash
IGNORE_WHEN_COPYING_END
2. Arduinoのセットアップ

    Arduino IDEにFastLEDライブラリをインストールします。

    arduino/tesikaga_led_controller.inoを開き、NUM_PHYSICAL_LEDSとDATA_PINを自分のハードウェア構成に合わせて正しく設定します。

    スケッチをArduinoに書き込みます。

    LEDテープを正しく接続します（データ線、12V電源、GND共通化）。

3. プロジェクトの設定

    settings.yaml を開き、自分の環境に合わせてserial_portとbaud_rateを正しく設定します。

    テストを行う場合はenable_test_modeをtrueにし、test_strip_led_countに使用するLEDの数を設定します。

4. 実行手順

この順番で実行することが非常に重要です。

    LEDレイアウトの生成（初回、またはデザイン変更時）
    scripts/artistic_path_generator.pyを実行し、画面の指示に従って対話的にLEDの配置をデザインし、保存します。
    Generated bash

      
python scripts/artistic_path_generator.py

    

IGNORE_WHEN_COPYING_START
Use code with caution. Bash
IGNORE_WHEN_COPYING_END

設定ファイルの生成（初回、または鳥パラメータ/音声ファイル変更時）
scripts/audio_sync_generator.pyを実行します。これにより、音声ファイルが解析され、最新のsrc/config.pyが自動生成されます。
Generated bash

      
python scripts/audio_sync_generator.py

    

IGNORE_WHEN_COPYING_START
Use code with caution. Bash
IGNORE_WHEN_COPYING_END

シミュレーションの実行

    ハードウェアなしで動きを確認する場合：
    Generated bash

      
python main.py

    

IGNORE_WHEN_COPYING_START
Use code with caution. Bash
IGNORE_WHEN_COPYING_END

Arduinoに接続してLEDをリアルタイムで光らせる場合：
Generated bash

      
python main_real.py

    

IGNORE_WHEN_COPYING_START

        Use code with caution. Bash
        IGNORE_WHEN_COPYING_END

🛠️ 主要技術スタック

    Python 3.11+

    Pygame-ce: シミュレーションの描画と音声再生

    NumPy: 高速なベクトル・配列計算

    Matplotlib: LEDパスの対話的生成

    Librosa: 音声ファイルの解析

    PyYAML: 設定ファイルの管理

    PySerial: Arduinoとのシリアル通信

    Arduino / C++: LEDコントローラー

    FastLED: 高速なLED駆動ライブラリ

🔮 次のステップ (Future Work)

    LiDARセンサーとの接続を実装し、マウス操作を現実世界の人の動きに置き換える。

    人の数や密集度に応じた、群れ全体のインタラクションを追加する。