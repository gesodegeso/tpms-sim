# TPMS Simulator v3.0 - テストシナリオガイド

## 概要
このガイドでは、TPMS Simulatorを使用した様々なテストシナリオと、その実行方法について説明します。

## 1. 交通イベントのテストシナリオ

### 1.1 都市部走行シミュレーション（信号多数）
```bash
python tpms_simulator.py \
  --vehicles 5 \
  --wheels 4 \
  --start "New York, NY" \
  --end "Newark, NJ" \
  --speed 30 \
  --temp 70 \
  --type regular \
  --enable-traffic-events
```
**期待される結果:**
- 5-10分ごとの信号停止
- 温度の周期的な低下
- 速度変動による圧力の微小変化

### 1.2 高速道路での渋滞シミュレーション
```bash
python tpms_simulator.py \
  --vehicles 3 \
  --wheels 10 \
  --start "Los Angeles, CA" \
  --end "San Diego, CA" \
  --speed 70 \
  --temp 85 \
  --type heavy_duty \
  --enable-traffic-events
```
**期待される結果:**
- 1-3回の渋滞イベント（速度20-30%）
- 渋滞中の温度上昇の鈍化
- 5-30分の渋滞継続

### 1.3 故障シミュレーション
```bash
python tpms_simulator.py \
  --vehicles 10 \
  --wheels 6 \
  --start "Chicago, IL" \
  --end "Milwaukee, WI" \
  --speed 55 \
  --temp 65 \
  --type heavy_duty \
  --enable-traffic-events
```
**期待される結果（10%の確率）:**
- タイヤパンク: 圧力が5-15 PSIに急低下
- エンジン故障: 完全停止
- センサー故障: ランダムな異常値

### 1.4 事故シミュレーション
```bash
python tpms_simulator.py \
  --vehicles 20 \
  --wheels 4 \
  --start "Phoenix, AZ" \
  --end "Tucson, AZ" \
  --speed 75 \
  --temp 100 \
  --type regular \
  --enable-traffic-events
```
**期待される結果（5%の確率）:**
- 急激な圧力・温度変化
- データ生成の突然停止
- trigger='1'のマーキング

## 2. データ異常系のテストシナリオ

### 2.1 データ欠損テスト
```bash
python tpms_simulator.py \
  --vehicles 2 \
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
**生成される異常:**
- 特定センサーの完全欠損
- 特定時刻の全データ欠損
- ランダムなレコード欠損

### 2.2 異常値テスト
```bash
python tpms_simulator.py \
  --vehicles 3 \
  --wheels 8 \
  --start "Seattle, WA" \
  --end "Tacoma, WA" \
  --speed 50 \
  --temp 55 \
  --type heavy_duty \
  --enable-data-anomalies \
  --anomaly-rate 0.10 \
  --anomaly-mode mixed
```
**生成される異常:**
- 負の圧力値（-10 PSI）
- 極端な温度（500°F）
- Null/NaN値
- 範囲外のGPS座標

### 2.3 時系列異常テスト
```bash
python tpms_simulator.py \
  --vehicles 1 \
  --wheels 4 \
  --start "Boston, MA" \
  --end "Providence, RI" \
  --speed 60 \
  --temp 68 \
  --type regular \
  --enable-data-anomalies \
  --anomaly-rate 0.08 \
  --anomaly-mode mixed
```
**生成される異常:**
- タイムスタンプ逆転
- 未来の日付
- ingested_at < read_at

### 2.4 データ破損テスト
```bash
python tpms_simulator.py \
  --vehicles 2 \
  --wheels 6 \
  --start "Miami, FL" \
  --end "Orlando, FL" \
  --speed 65 \
  --temp 88 \
  --type heavy_duty \
  --enable-data-anomalies \
  --anomaly-rate 0.05 \
  --anomaly-mode single
```
**生成される異常:**
- 不正なVIN（INVALID_VIN_123）
- 不正なセンサーID（sensor99_unknown）
- 文字化けデータ（!@#$%^&*）

## 3. 複合テストシナリオ

### 3.1 リアルワールドシミュレーション
```bash
python tpms_simulator.py \
  --vehicles 10 \
  --wheels 10 \
  --start "Dallas, TX" \
  --end "Houston, TX" \
  --speed 65 \
  --temp 92 \
  --type heavy_duty \
  --tenant "logistics_company" \
  --interval 5 \
  --enable-traffic-events \
  --enable-data-anomalies \
  --anomaly-rate 0.03 \
  --anomaly-mode mixed
```
**期待される結果:**
- 現実的な交通パターン
- 3%の異常データ（業界平均）
- 様々な異常タイプの混在

### 3.2 ストレステスト
```bash
python tpms_simulator.py \
  --vehicles 50 \
  --wheels 10 \
  --start "San Francisco, CA" \
  --end "Sacramento, CA" \
  --speed 55 \
  --temp 70 \
  --type heavy_duty \
  --interval 1 \
  --enable-traffic-events \
  --enable-data-anomalies \
  --anomaly-rate 0.20 \
  --anomaly-mode mixed
```
**目的:**
- 大量データ処理能力の確認
- 高頻度更新の処理
- 高異常率での動作確認

### 3.3 エッジケーステスト
```bash
# 極寒環境
python tpms_simulator.py \
  --vehicles 3 \
  --wheels 4 \
  --start "Minneapolis, MN" \
  --end "Duluth, MN" \
  --speed 45 \
  --temp -20 \
  --type regular \
  --enable-traffic-events \
  --enable-data-anomalies \
  --anomaly-rate 0.15

# 極暑環境
python tpms_simulator.py \
  --vehicles 3 \
  --wheels 8 \
  --start "Phoenix, AZ" \
  --end "Yuma, AZ" \
  --speed 70 \
  --temp 120 \
  --type heavy_duty \
  --enable-traffic-events \
  --enable-data-anomalies \
  --anomaly-rate 0.10
```

## 4. データ検証用SQLクエリ

### 4.1 異常データの統計
```sql
-- 異常率の確認
SELECT 
    trigger,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
FROM v1__sensor_reading
GROUP BY trigger;

-- センサー別異常率
SELECT 
    sensor_id,
    COUNT(CASE WHEN trigger = '1' THEN 1 END) * 100.0 / COUNT(*) as anomaly_rate
FROM v1__sensor_reading
GROUP BY sensor_id
ORDER BY anomaly_rate DESC;
```

### 4.2 交通イベントの検出
```sql
-- 速度低下イベント（渋滞）の検出
WITH speed_analysis AS (
    SELECT 
        vin,
        toStartOfHour(read_at) as hour,
        AVG(reading) as avg_pressure,
        STDDEV(reading) as pressure_stddev
    FROM v1__sensor_reading
    WHERE sensor_id LIKE '%pressure%'
    GROUP BY vin, hour
)
SELECT *
FROM speed_analysis
WHERE pressure_stddev < 0.2  -- Low variation indicates stopped/slow
ORDER BY hour;
```

### 4.3 データ品質チェック
```sql
-- Null値の確認
SELECT 
    sensor_id,
    COUNT(*) as null_count
FROM v1__sensor_reading
WHERE reading IS NULL
GROUP BY sensor_id;

-- 範囲外値の確認
SELECT *
FROM v1__sensor_reading
WHERE (sensor_id LIKE '%pressure%' AND (reading < 0 OR reading > 200))
   OR (sensor_id LIKE '%temperature%' AND (reading < -50 OR reading > 300));

-- 重複レコードの確認
SELECT 
    tenant, sensor_id, vin, read_at, reading,
    COUNT(*) as duplicate_count
FROM v1__sensor_reading
GROUP BY tenant, sensor_id, vin, read_at, reading
HAVING duplicate_count > 1;
```

## 5. パフォーマンステスト

### 5.1 大規模データ生成
```bash
# 100台の車両で24時間分のデータ
python tpms_simulator.py \
  --vehicles 100 \
  --wheels 10 \
  --start "New York, NY" \
  --end "Los Angeles, CA" \
  --speed 65 \
  --temp 75 \
  --type heavy_duty \
  --interval 1
```

### 5.2 メモリ使用量の確認
```python
import psutil
import os

# プログラム実行前
process = psutil.Process(os.getpid())
mem_before = process.memory_info().rss / 1024 / 1024  # MB

# シミュレーション実行
# ...

# プログラム実行後
mem_after = process.memory_info().rss / 1024 / 1024  # MB
print(f"Memory usage: {mem_after - mem_before:.2f} MB")
```

## 6. CI/CD統合

### GitHub Actions例
```yaml
name: TPMS Data Generation Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        pip install -r requirements-minimal.txt
    - name: Run test scenarios
      run: |
        # Normal scenario
        python tpms_simulator.py --vehicles 2 --wheels 4 --start "Boston, MA" --end "Cambridge, MA" --speed 30 --temp 70 --type regular
        
        # Anomaly test
        python tpms_simulator.py --vehicles 1 --wheels 4 --start "Boston, MA" --end "Cambridge, MA" --speed 30 --temp 70 --type regular --enable-data-anomalies --anomaly-rate 0.1
        
        # Traffic test
        python tpms_simulator.py --vehicles 1 --wheels 4 --start "Boston, MA" --end "Cambridge, MA" --speed 30 --temp 70 --type regular --enable-traffic-events
    - name: Verify output
      run: |
        ls -la *.parquet
        python -c "import pandas as pd; df = pd.read_parquet('tpms_data_moving_*.parquet'); print(f'Records: {len(df)}')"
```

## 7. トラブルシューティング

### 問題: 異常データが生成されない
```bash
# デバッグモードで実行
python -u tpms_simulator.py \
  --vehicles 1 \
  --wheels 4 \
  --start "Test, CA" \
  --end "Test2, CA" \
  --speed 50 \
  --temp 70 \
  --type regular \
  --enable-data-anomalies \
  --anomaly-rate 0.5  # 50%に増やしてテスト
```

### 問題: メモリ不足
```bash
# 小規模データで段階的にテスト
for i in 1 5 10 20 50; do
  echo "Testing with $i vehicles..."
  python tpms_simulator.py \
    --vehicles $i \
    --wheels 4 \
    --start "LA, CA" \
    --end "SD, CA" \
    --speed 60 \
    --temp 75 \
    --type regular
done
```

## まとめ
このガイドで紹介したテストシナリオを使用することで、TPMSデータパイプラインの包括的なテストが可能です。実際の運用環境に近い条件でのテストを行い、システムの堅牢性を確保してください。