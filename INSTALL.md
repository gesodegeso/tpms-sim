# TPMS Simulator v3.0 - インストールガイド

## 🆕 v3.0の新機能
- **交通イベントシミュレーション**: 渋滞、信号停止、故障、事故をリアルに再現
- **データ異常系テスト**: 欠損、異常値、重複などのテストデータ生成
- **異常マーキング**: trigger列で異常データを識別

## 🆕 v2.1の機能
- **車輪番号体系の標準化**: 業界標準に準拠した番号体系
- **センサーID命名規則**: `sensor`プレフィクスに統一

## 🆕 v2.0の機能
- **停止中モード**: 速度を0に設定することで、整備工場や車庫での車両監視データを生成
- **GPS出力最適化**: 圧力/温度レコード2回ごとに1回のGPS出力でデータ量を削減

## クイックスタート

### 最小構成のインストール（推奨）
最小限の依存パッケージのみをインストールします。道路距離計算は簡易モード（直線距離×1.2）になります。

```bash
pip install -r requirements-minimal.txt
```

### フル機能のインストール
OpenStreetMapを使用した実際の道路距離計算を含む、全機能をインストールします。

```bash
pip install -r requirements.txt
```

## インストールオプション

### オプション1: 仮想環境を使用（推奨）

```bash
# 仮想環境の作成
python -m venv tpms_env

# 仮想環境のアクティベート
# Windows:
tpms_env\Scripts\activate
# macOS/Linux:
source tpms_env/bin/activate

# パッケージのインストール
pip install -r requirements.txt

# プログラムの実行
python tpms_simulator.py --help
```

### オプション2: Condaを使用

```bash
# Conda環境の作成
conda create -n tpms python=3.9

# 環境のアクティベート
conda activate tpms

# パッケージのインストール
pip install -r requirements.txt
```

### オプション3: Pipenvを使用

```bash
# Pipenvのインストール（未インストールの場合）
pip install pipenv

# 依存関係のインストールと仮想環境の作成
pipenv install -r requirements.txt

# 仮想環境内でプログラムを実行
pipenv run python tpms_simulator.py --help
```

## 依存パッケージの説明

### 必須パッケージ (requirements-minimal.txt)

| パッケージ | バージョン | 用途 |
|----------|-----------|------|
| pandas | >=1.5.0 | データフレーム操作とParquet出力 |
| numpy | >=1.21.0 | 数値計算と補間 |
| pyarrow | >=10.0.0 | Parquetファイル形式のサポート |
| geopy | >=2.3.0 | 地理座標の取得と距離計算 |

### オプションパッケージ (requirements.txt に含まれる追加パッケージ)

| パッケージ | バージョン | 用途 |
|----------|-----------|------|
| osmnx | >=1.5.0 | OpenStreetMapデータを使用した道路ネットワーク分析 |
| networkx | >=2.8.0 | グラフ理論に基づく最短経路計算 |
| scikit-learn | >=1.0.0 | osmnxの依存関係 |
| matplotlib | >=3.5.0 | osmnxの依存関係（プロット機能） |
| folium | >=0.14.0 | 地図の可視化（osmnxの依存関係） |
| shapely | >=2.0.0 | 地理空間データの処理 |
| geopandas | >=0.12.0 | 地理空間データフレーム |

## トラブルシューティング

### 1. pyarrowのインストールに失敗する場合

```bash
# Condaを使用してインストール
conda install -c conda-forge pyarrow
```

### 2. osmnxのインストールに失敗する場合

osmnxは多くの依存関係があるため、Condaでのインストールが推奨されます：

```bash
conda install -c conda-forge osmnx
```

または、最小構成のみをインストールして簡易距離計算モードで使用してください：

```bash
pip install -r requirements-minimal.txt
```

### 3. Windows環境でのエラー

Windows環境では、一部のパッケージで追加の依存関係が必要な場合があります：

```bash
# Microsoft C++ Build Toolsが必要な場合
# https://visualstudio.microsoft.com/visual-cpp-build-tools/ からインストール

# または、プリビルドされたホイールを使用
pip install --only-binary :all: -r requirements.txt
```

### 4. メモリ不足エラー

大量の車両データを生成する際にメモリ不足になる場合：

```bash
# 仮想メモリを増やす（Linux/macOS）
ulimit -v unlimited

# または、車両数を減らして実行
python tpms_simulator.py --vehicles 10 ...  # 100台ではなく10台に減らす
```

## インストールの確認

インストールが正しく完了したか確認するには：

```bash
# Pythonスクリプトで確認
python -c "
import pandas
import numpy
import pyarrow
import geopy
print('✓ 必須パッケージがインストールされています')

try:
    import osmnx
    import networkx
    print('✓ オプションパッケージもインストールされています（フル機能）')
except ImportError:
    print('△ オプションパッケージはインストールされていません（簡易モード）')
"
```

## アンインストール

```bash
# pipでインストールしたパッケージをアンインストール
pip uninstall -r requirements.txt -y

# 仮想環境を削除（venvの場合）
deactivate
rm -rf tpms_env  # Windows: rmdir /s tpms_env

# Conda環境を削除（Condaの場合）
conda deactivate
conda env remove -n tpms
```

## 次のステップ

インストールが完了したら、以下のコマンドでヘルプを表示できます：

```bash
python tpms_simulator.py --help
```

または、サンプルスクリプトを実行してみてください：

```bash
python example_usage.py
```