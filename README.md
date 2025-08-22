# TPMS Sensor Data Simulator v3.0

## 概要
このプログラムは、TPMS（タイヤ空気圧監視システム）センサーの出力データをシミュレートし、ClickHouseデータベースに直接インポート可能なParquet形式で出力します。v3.0では、リアルな交通状況のシミュレーションとデータ異常系テストのための機能を追加しました。

**v3.0の新機能:**
- 🚦 **交通イベントシミュレーション**: 渋滞、信号停止、故障、事故を再現
- 🔧 **データ異常系テスト**: 欠損、異常値、重複などのテストデータ生成
- ⚠️ **異常マーキング**: 異常データをtrigger列で識別

**v2.1の機能:**
- 車輪番号体系を業界標準に準拠
- センサーIDプレフィクスを`sensor`に統一

**v2.0の機能:**
- 停止中モード（速度0）のサポート
- GPS出力頻度の最適化

## 機能詳細

### 交通イベントシミュレーション
リアルな走行状況を再現するための各種イベント：

| イベント | 説明 | 影響 |
|---------|------|------|
| **渋滞** | 速度が20-30%に低下 | 5-30分継続、温度上昇が緩やか |
| **信号停止** | 完全停止 | 30秒-2分、温度がわずかに低下 |
| **タイヤパンク** | タイヤ故障 | 圧力が5-15 PSIに急低下、異常値継続 |
| **エンジン故障** | エンジン停止 | 完全停止、異常値継続 |
| **センサー故障** | センサー異常 | ランダムな異常値を送信 |
| **事故** | 車両事故 | 急激な変化後、データ生成停止 |

### データ異常系テスト機能
データパイプラインのテストに使用できる各種異常：

| 異常タイプ | 説明 | trigger値 |
|-----------|------|-----------|
| **欠損系** | | |
| 特定センサー欠損 | 特定センサーのデータが欠落 | 1 |
| 全センサー欠損 | 特定時刻の全データが欠落 | 1 |
| ランダム欠損 | ランダムにデータが欠落 | 1 |
| **異常値系** | | |
| 範囲外の値 | 負値や極端な値（-10, 999 PSI等） | 1 |
| Null/NaN | Null値やNaN | 1 |
| **重複系** | | |
| レコード重複 | 同一レコードが複数存在 | 1 |
| **時系列異常** | | |
| タイムスタンプ逆転 | 時刻が過去に戻る | 1 |
| 未来の日付 | 未来のタイムスタンプ | 1 |
| ingested_at異常 | ingested_at < read_at | 1 |
| **その他** | | |
| 不正なVIN | 無効なVIN番号 | 1 |
| 不正なセンサーID | 存在しないセンサーID | 1 |
| データ破損 | 文字化けデータ | 1 |

## インストール

### 1. 依存パッケージのインストール

#### 最小構成（推奨）
```bash
pip install -r requirements-minimal.txt
```

#### フル機能（OpenStreetMap対応）
```bash
pip install -r requirements.txt
```

### 2. 仮想環境の使用（推奨）
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-minimal.txt
```

## 使用方法

### 基本的な使用例

#### 通常の走行シミュレーション
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

#### 交通イベント付きシミュレーション
```bash
python tpms_simulator.py \
  --vehicles 3 \
  --wheels 6 \
  --start "Los Angeles, CA" \
  --end "San Diego, CA" \
  --speed 65 \
  --temp 80 \
  --type heavy_duty \
  --enable-traffic-events
```

#### データ異常系テスト（混合モード）
```bash
python tpms_simulator.py \
  --vehicles 2 \
  --wheels 4 \
  --start "Chicago, IL" \
  --end "Detroit, MI" \
  --speed 55 \
  --temp 70 \
  --type regular \
  --enable-data-anomalies \
  --anomaly-rate 0.1 \
  --anomaly-mode mixed
```

#### データ異常系テスト（単一異常タイプ）
```bash
python tpms_simulator.py \
  --vehicles 2 \
  --wheels 4 \
  --start "Phoenix, AZ" \
  --end "Tucson, AZ" \
  --speed 60 \
  --temp 95 \
  --type regular \
  --enable-data-anomalies \
  --anomaly-rate 0.05 \
  --anomaly-mode single
```

#### 完全なテストシナリオ
```bash
python tpms_simulator.py \
  --vehicles 5 \
  --wheels 10 \
  --start "Seattle, WA" \
  --end "Portland, OR" \
  --speed 55 \
  --temp 65 \
  --type heavy_duty \
  --tenant "test_company" \
  --interval 3 \
  --enable-traffic-events \
  --enable-data-anomalies \
  --anomaly-rate 0.08 \
  --anomaly-mode mixed
```

### パラメータ詳細

#### 必須パラメータ
| パラメータ | 説明 | 例 |
|-----------|------|-----|
| `--vehicles` | 車両台数 | `4` |
| `--wheels` | 車輪数（4, 6, 8, 10） | `4` |
| `--start` | 出発地点 | `"Chicago, IL"` |
| `--end` | 到着地点 | `"Detroit, MI"` |
| `--speed` | 平均速度（mph）、0で停止中モード | `60` |
| `--temp` | 平均外気温（華氏） | `75` |
| `--type` | 車両タイプ | `regular` or `heavy_duty` |

#### オプションパラメータ
| パラメータ | 説明 | デフォルト |
|-----------|------|-----------|
| `--tenant` | テナント名 | 自動生成 |
| `--interval` | データ更新間隔（分） | `5` |
| `--output` | 出力ファイル名 | 自動生成 |
| **交通イベント** | | |
| `--enable-traffic-events` | 交通イベント有効化 | 無効 |
| **データ異常** | | |
| `--enable-data-anomalies` | データ異常生成有効化 | 無効 |
| `--anomaly-rate` | 異常発生率（0-1） | `0.05` |
| `--anomaly-mode` | 異常モード | `mixed` |

### 異常モードの選択

- **`mixed`**: 様々な種類の異常をランダムに混在させる
- **`single`**: 1種類の異常のみを生成（テスト用）

## データ出力仕様

### trigger列の値
- **空文字列("")**: 正常データ
- **"1"**: 異常データ（交通イベントまたはデータ異常）

### 車輪番号の割り当て
- **4輪**: 11(左前), 14(右前), 21(左後), 24(右後)
- **6輪**: 11(左前), 14(右前), 21(後左外), 22(後左内), 23(後右内), 24(後右外)
- **8輪**: 11(左前), 14(右前), 21(2軸目左), 24(2軸目右), 31(3軸目左外), 32(3軸目左内), 33(3軸目右内), 34(3軸目右外)
- **10輪**: 11(左前), 14(右前), 21-24(2軸目), 31-34(3軸目)

### センサーIDの形式
- タイヤ圧力: `sensor{位置番号}_pressure`
- タイヤ温度: `sensor{位置番号}_temperature`
- 緯度: `latitude`
- 経度: `longitude`

## 使用例

### 例1: 都市部の配送シミュレーション（信号多数）
```bash
python tpms_simulator.py \
  --vehicles 3 \
  --wheels 6 \
  --start "Manhattan, NY" \
  --end "Brooklyn, NY" \
  --speed 25 \
  --temp 72 \
  --type heavy_duty \
  --tenant "city_delivery" \
  --interval 2 \
  --enable-traffic-events
```

### 例2: データパイプラインの異常系テスト
```bash
# 欠損データのテスト
python tpms_simulator.py \
  --vehicles 1 \
  --wheels 4 \
  --start "Denver, CO" \
  --end "Boulder, CO" \
  --speed 45 \
  --temp 60 \
  --type regular \
  --enable-data-anomalies \
  --anomaly-rate 0.15 \
  --anomaly-mode single
```

### 例3: 長距離輸送の完全シミュレーション
```bash
python tpms_simulator.py \
  --vehicles 10 \
  --wheels 10 \
  --start "Los Angeles, CA" \
  --end "Las Vegas, NV" \
  --speed 65 \
  --temp 85 \
  --type heavy_duty \
  --tenant "logistics_co" \
  --enable-traffic-events \
  --enable-data-anomalies \
  --anomaly-rate 0.03
```

## ClickHouseでのデータ検証

### 異常データの確認
```sql
-- 異常データの統計
SELECT 
    trigger,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
FROM v1__sensor_reading
GROUP BY trigger
ORDER BY trigger;

-- センサー別の異常率
SELECT 
    sensor_id,
    COUNT(CASE WHEN trigger = '1' THEN 1 END) as anomaly_count,
    COUNT(*) as total_count,
    COUNT(CASE WHEN trigger = '1' THEN 1 END) * 100.0 / COUNT(*) as anomaly_rate
FROM v1__sensor_reading
WHERE sensor_id LIKE 'sensor%'
GROUP BY sensor_id
ORDER BY anomaly_rate DESC;
```

### 異常値の検出
```sql
-- 範囲外の圧力値
SELECT *
FROM v1__sensor_reading
WHERE sensor_id LIKE '%pressure'
  AND (reading < 0 OR reading > 200)
ORDER BY read_at;

-- タイムスタンプ異常
SELECT *
FROM v1__sensor_reading
WHERE ingested_at < read_at
   OR read_at > now()
ORDER BY read_at;
```

## トラブルシューティング

### 交通イベントが発生しない
- `--enable-traffic-events`フラグが設定されているか確認
- 停止中モード（速度0）では交通イベントは発生しません

### 異常データが生成されない
- `--enable-data-anomalies`フラグが設定されているか確認
- `--anomaly-rate`の値を確認（0.05 = 5%）

### メモリ不足
- 車両数を減らす
- データ更新間隔を増やす（`--interval 10`）

## Python実行例

```python
from tpms_simulator import TPMSSimulator

# 交通イベントと異常データを含むシミュレーション
simulator = TPMSSimulator(
    num_vehicles=3,
    num_wheels=4,
    start_location="San Francisco, CA",
    end_location="San Jose, CA",
    avg_speed_mph=55,
    avg_temp_f=68,
    vehicle_type="regular",
    tenant="test_fleet",
    enable_traffic_events=True,
    enable_data_anomalies=True,
    anomaly_rate=0.1,
    anomaly_mode='mixed'
)

# データ生成と保存
df = simulator.generate_dataset()
simulator.save_to_parquet(df, "test_data.parquet")

# 異常データの確認
anomalies = df[df['trigger'] == '1']
print(f"異常データ: {len(anomalies)} / {len(df)} ({len(anomalies)/len(df)*100:.1f}%)")
```

## バージョン履歴

### v3.0 (Current)
- 交通イベントシミュレーション（渋滞、信号、故障、事故）
- データ異常系テスト機能（欠損、異常値、重複等）
- trigger列による異常データのマーキング

### v2.1
- 車輪番号体系を業界標準に準拠
- センサーIDプレフィクスを`sensor`に変更

### v2.0
- 停止中モード（速度0）のサポート
- GPS出力頻度の最適化

### v1.0
- 初期リリース

## ライセンス
このプログラムはデモンストレーション目的で提供されています。