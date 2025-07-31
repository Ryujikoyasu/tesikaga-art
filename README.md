屈斜路の響き - インタラクティブ・ライトアート

(▲ シミュレーション実行中のスクリーンショット。左が鳥の思考や位置を示すデバッグビュー、右が物理LEDでの見た目を忠実に再現したアーティスティックビュー)

北海道・弟子屈町の自然をテーマにした、来場者参加型のインタラクティブアート作品のシミュレーション兼制御ソフトウェアです。来場者の動きを（最終的には）LiDARで検知し、その存在が「小鳥」として表現される光と音の群れに影響を与えます。

テクノロジーを通じて、人と自然の、繊細で詩的な関わり合いを体験してもらうことを目指します。
✨ こだわりのポイント (Features & Highlights)

このプロジェクトは、単なるシミュレーターではありません。物理的な制約とどう向き合い、生命感をいかにしてコードに宿らせるか、その探求の記録でもあります。
1. ハイブリッドAI：2Dの自由と、1D（物理LED）の制約が生むリアリティ

メディアアートにおける最大の挑戦は、シミュレーション空間の自由さと、物理世界の厳格な制約をどう結びつけるかです。このプロジェクトでは、鳥のAIに両方を理解させる「ハイブリッドAI」を実装しました。

    問題: 鳥たちは2D空間を自由に飛び回りますが、LEDテープは物理的に固定された「1本の線」です。テープがU字にカーブしている場所では、鳥同士が2D空間では近くても、LEDテープ上では遠い、という矛盾が生まれます。逆に、スイッチバックしている場所では、2Dでは遠くてもLED上では隣接し、意図せず色が混ざってしまいます。

    解決策: 鳥のAIは、毎フレーム2種類の距離を計算します。

        他の鳥との「2D空間での距離」

        LEDテープ上での「1Dピクセル距離」

    そして、configで定義されたpixel_personal_space（縄張り意識）に基づき、LEDテープ上で近すぎると判断した場合にのみ、2D空間で相手を避けるように反発力を発生させます。これは、まさに「物理世界からのフィードバック」をAIの意思決定に組み込むアプローチです。

    結果: これにより、鳥たちは互いの光のオーラが混ざり合う前にスッと距離を取るようになり、一羽一羽が独立した存在として尊重されます。「ピンク色のオジロワシ」問題は完全に解決され、観客は混乱することなく、それぞれの鳥の個性を認識できます。

2. 光の表現：物理LEDで「伝わる」ための工夫

LEDは「光る点」ですが、私たちが表現したいのは「生命の気配」です。このギャップを埋めるため、光の表現にいくつもの工夫を凝らしました。

    シミュレーションと物理の完全同期:
    当初は、高解像度のシミュレーション結果を物理LED（3LED=1ピクセル）にダウンサンプリングしていましたが、これは「シミュレーションと物理がリンクしない」という哲学的な問題を生んでいました。現在の実装では、シミュレーション自体を物理ピクセル単位で構築しています。計算も描画も全て300ピクセルを基準に行い、Artistic Viewではそのピクセルを少し大きく描画することで、物理的な見た目を忠実に再現します。What You See Is What You Get. これがこの作品の誠実さです。

    「黒」と「茶色」という挑戦:
    LEDは黒や茶色を発光できません。この課題に対し、私たちは色を「翻訳」しました。クマゲラの「黒」は、完全な消灯ではなく[35, 35, 50]という**「限りなく黒に近い、深い濃紺」に。ノゴマの「茶色」は[140, 115, 90]という「温かみのあるオレンジブラウン」**に。これにより、鳥のイメージを保ちつつ、光としての存在感を失わない、絶妙なバランスを実現しました。

    「消える光」から「広がるオーラ」へ:
    鳥の光の端が暗すぎて物理LEDでは見えなくなる問題に対し、光の減衰計算式を改良しました。光の端でも明るさが0になるのではなく、最低光量（30%）を保証します。これにより、光は「消えていく」のではなく、中心から外側へ「柔らかく広がるオーラ」のように見え、鳥のフォルムが明確に知覚できるようになりました。

3. Audio-Sync Generator：鳴き声に「魂」を宿す光

鳥の鳴き声と光の明滅を、手作業で同期させるのは困難で、音楽的ではありません。

    解決策: scripts/audio_sync_generator.pyは、Pythonの音声解析ライブラリlibrosaを用いて、鳥の音声ファイル（.mp3）の**音の立ち上がり（Onset）**を自動で検出します。そして、そのタイミングとリズムに完璧に同期した輝度のアニメーションパターン（chirp_pattern）を計算し、src/config.pyに自動で書き出します。

    結果: クマゲラの鋭いドラミングの連打や、オオルリの長く伸びる美声が、音楽的に、そしてフレーム単位で正確に光の明滅として表現されます。これはもはや同期ではなく、**音と光の「共演」**です。

4. Artistic Path Generator：作者の「筆跡」を刻む

LEDの物理的な配置は、作品の印象を決定づける「キャンバス」そのものです。

    解決策: scripts/artistic_path_generator.pyは、アーティストが対話的に「一筆書き」で描いた芸術的な曲線を、物理的な制約（全長、電源位置）を満たすようにコンピュータが微調整する、人間と機械の協調作業を可能にします。

    結果: 生成されるled_positions_...csvには、作者ならではの「筆跡」や「ゆらぎ」が宿ります。これにより、作品は無機質な工業製品ではなく、手触りのあるアート作品としての個性を持ちます。

📂 ファイル構成
Generated code

      
tesikaga-art/
├── main.py                 # シミュレーションのみを実行（開発用）
├── main_real.py            # Arduinoへリアルタイムでデータを送信（本番用）
├── settings.yaml           # ★ユーザーが編集する主要な設定ファイル
├── requirements.txt        # 必要なPythonライブラリ
├── README.md               # このファイル
│
├── src/                    # ソースコードの心臓部
│   ├── objects.py          # HumanとBirdのクラス定義（ハイブリッドAIの実装箇所）
│   ├── simulation.py       # Worldクラス（物理法則とシミュレーションの管理）
│   ├── config.py           # 【自動生成】される設定ファイル。直接編集しないこと！
│   └── config_structure.py # 鳥のパラメータの原本。編集後、ジェネレータの実行が必要。
│
├── assets/                 # プログラムが使用する素材
│   ├── sounds/             # 鳥の鳴き声の音声ファイル (.mp3)
│   └── data/               # LEDの物理的な座標データファイル (.csv)
│
├── scripts/                # 補助的なスクリプト群
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

    Arduino IDEのライブラリマネージャから**FastLEDライブラリ**をインストールします。

    arduino/tesikaga_led_controller.inoを開き、NUM_PHYSICAL_LEDSやDATA_PINをあなたの環境に合わせて正しく設定します。

    スケッチをArduino Uno（または互換機）に書き込みます。

3. プロジェクトの設定

    settings.yaml を開き、あなたの環境に合わせてserial_portなどを正しく設定します。

    テストを行う場合はenable_test_modeをtrueにし、test_strip_led_countに使用する物理LEDの数を設定します。

4. 【最重要】 実行手順

この順番で実行することが非常に重要です。

    LEDレイアウトの生成（初回、またはデザイン変更時）
    scripts/artistic_path_generator.pyを実行し、画面の指示に従って対話的にLEDの配置をデザインし、保存します。
    Generated bash

      
python scripts/artistic_path_generator.py

    

IGNORE_WHEN_COPYING_START
Use code with caution. Bash
IGNORE_WHEN_COPYING_END

設定ファイルの生成（初回、または鳥のパラメータ・音声変更時）
scripts/audio_sync_generator.pyを実行します。これにより、src/config_structure.pyと音声ファイルが解析され、最新の**src/config.pyが自動生成されます。**
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

    Librosa: 音声ファイルの解析とOnset検出

    PyYAML / Matplotlib / PySerial: ユーティリティ

    Arduino / C++ with FastLED: 堅牢なLEDコントローラー

🔮 次のステップ

    LiDARセンサーとの接続を実装し、マウス操作を現実世界の人の動きに置き換える。