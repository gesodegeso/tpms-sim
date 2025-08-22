# TPMS Sensor Data Simulator v2.1

## 概要
このプログラムは、TPMS（タイヤ空気圧監視システム）センサーの出力データをシミュレートし、ClickHouseデータベースに直接インポート可能なParquet形式で出力します。

**v2.1の新機能:**
- 🆕 車輪番号体系を業界標準に準拠
- 🆕 センサーIDプレフィクスを`sensor`に統一

**v2.0の機能:**
- 停止中モード（速度0）のサポート - 整備工場や車庫での車両監視に対応
- GPS出力頻度の最適化 - 圧力/温度レコード2回ごとに1回出力

## 機能
- 複数車両のセンサーデータを同時生成
- 実際の道路距離計算（OpenStreetMap使用）
- 走行による温度上昇のシミュレーション（移動時のみ）
- 停止中モードでの車両監視データ生成
- 標準的なVIN形式での車両識別番号生成
- ClickHouse互換のParquet形式出力
- GPS出力頻度の調整（データ量最適化）

## インストール

### 1. リポジトリのクローンまたはダウンロード
```bash
git clone <repository-url>
cd tpms-simulator
```

### 2. Pythonパッケージのインストール

#### オプション A: 最小構成（推奨）
```bash
pip install -r requirements-minimal.txt
```
最小限の依存パッケージのみインストール。道路距離は簡易計算（直線距離×1.2）を使用。

#### オプション B: フル機能
```bash
pip install -r requirements.txt
```
OpenStreetMapを使用した実際の道路距離計算を含む全機能をインストール。

### 3. 仮想環境の使用（推奨）
```bash
# 仮想環境の作成
python -m venv venv

# アクティベート
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# パッケージのインストール
pip install -r requirements-minimal.txt
```

## 使用方法

### 基本的な使用例

#### 走行モード（通常の使用）
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

#### 🆕 停止中モード（整備工場/車庫での監視）
```bash
python tpms_simulator.py \
  --vehicles 5 \
  --wheels 4 \
  --start "Chicago, IL" \
  --end "Detroit, MI" \
  --speed 0 \
  --temp 68 \
  --type regular \
  --tenant "maintenance_shop"
```
**注意:** 速度を0に設定すると停止中モードになります。車両は開始地点に留まり、温度変化なし、圧力の微小変動のみをシミュレートします。

#### Heavy Duty車両の長距離輸送
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
| パラメータ | 説明 | 例 |
|-----------|------|-----|
| `--vehicles` | 車両台数 | `4` |
| `--wheels` | 車輪数（4, 6, 8, 10） | `4` |
| `--start` | 出発地点 | `"Chicago, IL"` |
| `--end` | 到着地点 | `"Detroit, MI"` |
| `--speed` | 平均速度（mph）<br>**0で停止中モード** | `60` または `0` |
| `--temp` | 平均外気温（華氏） | `75` |
| `--type` | 車両タイプ | `regular` or `heavy_duty` |

#### オプションパラメータ
| パラメータ | 説明 | デフォルト |
|-----------|------|-----------|
| `--tenant` | テナント名 | 自動生成 |
| `--interval` | データ更新間隔（分） | `5` |
| `--output` | 出力ファイル名 | 自動生成 |

## 動作モード

### 走行モード（速度 > 0）
- 車両は開始地点から終了地点へ移動
- タイヤ温度は走行により上昇（最大+10°F）
- 圧力は±0.5 PSIの範囲で変動
- GPSは実際の移動経路を記録

### 🆕 停止中モード（速度 = 0）
- 車両は開始地点に留まる
- タイヤ温度は外気温のまま（変化なし）
- 圧力は±0.2 PSIの微小変動のみ
- データ生成期間は法定速度での移動時間を使用
  - 州内移動: 55 mph
  - 州間移動: 65 mph
- 用途: 整備工場、車庫、駐車場での車両監視

## データ出力仕様

### GPS出力頻度
- 🆕 圧力/温度レコード2回ごとに1回GPS位置情報を出力
- 例（5分間隔の場合）:
  - 0分: 圧力・温度
  - 5分: 圧力・温度
  - 10分: 圧力・温度・**GPS**
  - 15分: 圧力・温度
  - 20分: 圧力・温度・**GPS**

### 車輪番号の割り当て
- **4輪**: 11(左前), 14(右前), 21(左後), 24(右後)
- **6輪**: 11(左前), 14(右前), 21(後左外), 22(後左内), 23(後右内), 24(後右外)
- **8輪**: 11(左前), 14(右前), 21(2軸目左), 24(2軸目右), 31(3軸目左外), 32(3軸目左内), 33(3軸目右内), 34(3軸目右外)
- **10輪**: 11(左前), 14(右前), 21(2軸目左外), 22(2軸目左内), 23(2軸目右内), 24(2軸目右外), 31(3軸目左外), 32(3軸目左内), 33(3軸目右内), 34(3軸目右外)

### センサーIDの形式
- タイヤ圧力: `sensor{位置番号}_pressure`
- タイヤ温度: `sensor{位置番号}_temperature`
- 緯度: `latitude`
- 経度: `longitude`

## データフォーマット

### 出力カラム
| カラム名 | データ型 | 説明 |
|---------|---------|------|
| tenant | String | テナント識別子 |
| sensor_id | String | センサーID |
| vin | String | 17桁の車両識別番号 |
| read_at | DateTime | 読み取り時刻 |
| trigger | String | トリガー（空文字） |
| reading | Float64 | 測定値 |
| ingested_at | DateTime | 取り込み時刻（read_at + 2分） |

### 圧力値の範囲
- **普通車**: 31-35 PSI
  - 走行中: ±0.5 PSI変動
  - 停止中: ±0.2 PSI変動
- **Heavy Duty**: 85-120 PSI
  - 走行中: ±0.5 PSI変動
  - 停止中: ±0.2 PSI変動

### 温度値の特性
- **走行モード**: 外気温から最大+10°F上昇
- **停止中モード**: 外気温±1°F（変化なし）

## ClickHouseへのインポート

```sql
-- テーブルへのインポート
INSERT INTO v1__sensor_reading 
SELECT * FROM file('path/to/tpms_data_*.parquet', 'Parquet');

-- データの確認
SELECT 
    sensor_id,
    count() as record_count,
    avg(reading) as avg_reading
FROM v1__sensor_reading
GROUP BY sensor_id
ORDER BY sensor_id;
```

## 使用例

### 例1: 整備工場での24時間監視
```bash
python tpms_simulator.py \
  --vehicles 10 \
  --wheels 4 \
  --start "Denver, CO" \
  --end "Salt Lake City, UT" \
  --speed 0 \
  --temp 65 \
  --type regular \
  --tenant "denver_maintenance" \
  --interval 30  # 30分ごとの記録
```

### 例2: 配送トラックの都市内走行
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
  --interval 2  # 頻繁な更新
```

### 例3: 長距離トラック輸送
```bash
python tpms_simulator.py \
  --vehicles 5 \
  --wheels 10 \
  --start "Seattle, WA" \
  --end "Portland, OR" \
  --speed 55 \
  --temp 60 \
  --type heavy_duty \
  --tenant "interstate_logistics"
```

## トラブルシューティング

### "Could not find coordinates" エラー
- 地点名が正しいか確認
- 米国内の地点であることを確認
- インターネット接続を確認

### OSMnx関連のエラー
- `requirements.txt`でフル機能版をインストール
- または`requirements-minimal.txt`で簡易計算モードを使用

### メモリ不足エラー
- 車両数を減らして実行
- または仮想メモリを増やす: `ulimit -v unlimited`

### 停止中モードでデータが生成されない
- 速度が正確に0に設定されているか確認
- 開始地点と終了地点が異なることを確認（距離計算のため）

## Python実行例

```python
from tpms_simulator import TPMSSimulator

# 停止中モードのシミュレータ
stationary_sim = TPMSSimulator(
    num_vehicles=3,
    num_wheels=4,
    start_location="Phoenix, AZ",
    end_location="Tucson, AZ",
    avg_speed_mph=0,  # 停止中モード
    avg_temp_f=95,
    vehicle_type="regular",
    tenant="repair_shop"
)

# データ生成と保存
df = stationary_sim.generate_dataset()
stationary_sim.save_to_parquet(df, "stationary_monitoring.parquet")
```

## バージョン履歴

### v2.1 (Current)
- 車輪番号体系を業界標準に準拠（前輪右: 14、4輪車後輪右: 24など）
- センサーIDプレフィクスを`tire`から`sensor`に変更
- 車輪番号体系の詳細ドキュメント追加

### v2.0
- 停止中モード（速度0）のサポート
- GPS出力頻度の最適化（2:1比率）
- 停止中の圧力変動を現実的に調整

### v1.0
- 初期リリース
- 基本的なTPMSデータシミュレーション
- OpenStreetMap統合

## ライセンス
このプログラムはデモンストレーション目的で提供されています。

## サポート
問題が発生した場合は、以下を確認してください：
1. Pythonバージョン3.7以上
2. 必要なパッケージがインストールされている
3. インターネット接続が利用可能（ジオコーディング用）