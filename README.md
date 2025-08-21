# TPMS Sensor Data Simulator

## 概要
このプログラムは、TPMS（タイヤ空気圧監視システム）センサーの出力データをシミュレートし、ClickHouseデータベースに直接インポート可能なParquet形式で出力します。

## 機能
- 複数車両のセンサーデータを同時生成
- 実際の道路距離計算（OpenStreetMap使用）
- 走行による温度上昇のシミュレーション
- 標準的なVIN形式での車両識別番号生成
- ClickHouse互換のParquet形式出力

## インストール

### 必須パッケージ
```bash
pip install pandas numpy geopy pyarrow
```

### オプションパッケージ（実際の道路距離計算用）
```bash
pip install osmnx networkx
```

注意: osmnxがインストールされていない場合、プログラムは自動的に直線距離×1.2の簡易計算にフォールバックします。

## 使用方法

### 基本的な使用例

#### 普通車4台、4輪、ニューヨークからボストンへ
```bash
python tpms_simulator.py \
  --vehicles 4 \
  --wheels 4 \
  --start "New York, NY" \
  --end "Boston, MA" \
  --speed 60 \
  --temp 75 \
  --type regular
```

#### Heavy Duty車両2台、10輪、ロサンゼルスからサンフランシスコへ
```bash
python tpms_simulator.py \
  --vehicles 2 \
  --wheels 10 \
  --start "Los Angeles, CA" \
  --end "San Francisco, CA" \
  --speed 55 \
  --temp 80 \
  --type heavy_duty \
  --tenant "logistics_company" \
  --interval 10
```

### パラメータ詳細

#### 必須パラメータ
- `--vehicles`: 車両台数（整数）
- `--wheels`: 車輪数（4, 6, 8, 10のいずれか）
- `--start`: 出発地点（形式: "都市名, 州名"）
- `--end`: 到着地点（形式: "都市名, 州名"）
- `--speed`: 平均速度（mph）
- `--temp`: 平均外気温（華氏）
- `--type`: 車両タイプ（regular または heavy_duty）

#### オプションパラメータ
- `--tenant`: テナント名（省略時は自動生成）
- `--interval`: データ更新間隔（分、デフォルト: 5）
- `--output`: 出力ファイル名（省略時は自動生成）

## 車輪番号の割り当て

### 4輪車
- 11: 前左、12: 前右
- 21: 後左、22: 後右

### 6輪車
- 11: 前左、12: 前右
- 21: 後左内側、22: 後左外側
- 31: 後右内側、32: 後右外側

### 8輪車
- 11: 前左、12: 前右
- 21: 後左1内側、22: 後左1外側
- 31: 後左2内側、32: 後左2外側
- 41: 後右1内側、42: 後右1外側

### 10輪車
- 11: 前左、12: 前右
- 21: 後左1内側、22: 後左1外側
- 31: 後左2内側、32: 後左2外側
- 41: 後右1内側、42: 後右1外側
- 51: 後右2内側、52: 後右2外側

## データフォーマット

### 出力カラム
- `tenant`: テナント名（LowCardinality(String)）
- `sensor_id`: センサーID（String）
- `vin`: 車両識別番号（String）
- `read_at`: 読み取り時刻（DateTime64(3)）
- `trigger`: トリガー（空文字列）
- `reading`: 測定値（Float64）
- `ingested_at`: 取り込み時刻（DateTime64(3)）

### センサーIDの形式
- タイヤ圧力: `tire{位置番号}_pressure`（例: tire11_pressure）
- タイヤ温度: `tire{位置番号}_temperature`（例: tire11_temperature）
- 緯度: `latitude`
- 経度: `longitude`

## ClickHouseへのインポート

生成されたParquetファイルは以下のコマンドでClickHouseにインポートできます：

```sql
INSERT INTO v1__sensor_reading 
SELECT * FROM file('path/to/tpms_data_*.parquet', 'Parquet');
```

## データの特徴

### 圧力値
- 普通車: 31-35 PSI範囲で変動
- Heavy Duty: 85-120 PSI範囲で変動
- 走行中は±0.5 PSIの微小変動

### 温度値
- 走行開始時: 外気温±2°F
- 走行中: 徐々に上昇（最大約10°F）
- 後輪は前輪より若干高温

### 更新頻度
- デフォルト5分間隔
- ingested_atはread_atの2分後

## トラブルシューティング

### "Could not find coordinates" エラー
- 地点名が正しいか確認してください
- 米国内の地点であることを確認してください
- インターネット接続を確認してください

### OSMnx関連のエラー
- osmnxパッケージがインストールされていない場合、自動的に簡易計算モードに切り替わります
- 簡易計算では直線距離の1.2倍を道路距離として使用します

### メモリ不足エラー
- 大量の車両を生成する場合、メモリ使用量に注意してください
- 必要に応じて車両数を分割して実行してください

## Python実行例

```python
from tpms_simulator import TPMSSimulator

# シミュレータを初期化
simulator = TPMSSimulator(
    num_vehicles=5,
    num_wheels=4,
    start_location="Chicago, IL",
    end_location="Detroit, MI",
    avg_speed_mph=65,
    avg_temp_f=70,
    vehicle_type="regular",
    tenant="my_company"
)

# データセットを生成
df = simulator.generate_dataset()

# Parquetファイルに保存
simulator.save_to_parquet(df, "output.parquet")
```

## ライセンス
このプログラムはデモンストレーション目的で提供されています。