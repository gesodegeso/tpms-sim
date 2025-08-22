# TPMS Simulator - サンプル出力データ構造

## データ出力例

### 4輪車の出力例（5分間隔、最初の2サイクル）

```
時刻: 2025-08-22 10:00:00
├── sensor11_pressure: 32.5 PSI
├── sensor11_temperature: 75.2 °F
├── sensor14_pressure: 32.8 PSI
├── sensor14_temperature: 75.5 °F
├── sensor21_pressure: 33.1 PSI
├── sensor21_temperature: 75.8 °F
├── sensor24_pressure: 33.0 PSI
└── sensor24_temperature: 75.7 °F

時刻: 2025-08-22 10:05:00
├── sensor11_pressure: 32.6 PSI
├── sensor11_temperature: 76.1 °F
├── sensor14_pressure: 32.9 PSI
├── sensor14_temperature: 76.3 °F
├── sensor21_pressure: 33.2 PSI
├── sensor21_temperature: 77.2 °F
├── sensor24_pressure: 33.1 PSI
└── sensor24_temperature: 77.1 °F

時刻: 2025-08-22 10:10:00  ★GPSデータ出力
├── sensor11_pressure: 32.7 PSI
├── sensor11_temperature: 77.5 °F
├── sensor14_pressure: 33.0 PSI
├── sensor14_temperature: 77.8 °F
├── sensor21_pressure: 33.3 PSI
├── sensor21_temperature: 78.9 °F
├── sensor24_pressure: 33.2 PSI
├── sensor24_temperature: 78.8 °F
├── latitude: 40.712776
└── longitude: -74.005974
```

### 6輪車の車輪配置とセンサーID

```
         前方
    [11]      [14]      sensor11: 左前輪
      |        |        sensor14: 右前輪
      |        |        
  [21][22]  [23][24]    sensor21: 後左外輪
         後方           sensor22: 後左内輪
                       sensor23: 後右内輪
                       sensor24: 後右外輪
```

### 10輪車のセンサーID一覧

| 位置 | センサーID | 説明 |
|------|------------|------|
| 11 | sensor11_pressure/temperature | 左前輪 |
| 14 | sensor14_pressure/temperature | 右前輪 |
| 21 | sensor21_pressure/temperature | 第2軸左外輪 |
| 22 | sensor22_pressure/temperature | 第2軸左内輪 |
| 23 | sensor23_pressure/temperature | 第2軸右内輪 |
| 24 | sensor24_pressure/temperature | 第2軸右外輪 |
| 31 | sensor31_pressure/temperature | 第3軸左外輪 |
| 32 | sensor32_pressure/temperature | 第3軸左内輪 |
| 33 | sensor33_pressure/temperature | 第3軸右内輪 |
| 34 | sensor34_pressure/temperature | 第3軸右外輪 |

## Parquetファイル構造

```python
# カラム定義
columns = {
    'tenant': str,           # テナントID (例: "test1234567890")
    'sensor_id': str,        # センサーID (例: "sensor11_pressure")
    'vin': str,              # 車両識別番号 (例: "1HGBH41JXMN109186")
    'read_at': datetime64,   # 読取時刻
    'trigger': str,          # トリガー (空文字)
    'reading': float64,      # 測定値
    'ingested_at': datetime64 # 取込時刻
}
```

## データパターン例

### 走行モード（通常走行）
- 圧力変動: ±0.5 PSI
- 温度上昇: 最大 +10°F
- GPS更新: 2回の圧力/温度更新ごとに1回

### 停止中モード（速度=0）
- 圧力変動: ±0.2 PSI（微小）
- 温度変動: ±1°F（ほぼ一定）
- GPS位置: 開始地点で固定
- データ生成期間: 法定速度での移動時間

## CSVエクスポート例

```csv
tenant,sensor_id,vin,read_at,trigger,reading,ingested_at
test5543672913,sensor11_pressure,1HGBH41JXMN109186,2025-08-22 10:00:00,,32.5,2025-08-22 10:02:00
test5543672913,sensor11_temperature,1HGBH41JXMN109186,2025-08-22 10:00:00,,75.2,2025-08-22 10:02:00
test5543672913,sensor14_pressure,1HGBH41JXMN109186,2025-08-22 10:00:00,,32.8,2025-08-22 10:02:00
test5543672913,sensor14_temperature,1HGBH41JXMN109186,2025-08-22 10:00:00,,75.5,2025-08-22 10:02:00
test5543672913,sensor21_pressure,1HGBH41JXMN109186,2025-08-22 10:00:00,,33.1,2025-08-22 10:02:00
test5543672913,sensor21_temperature,1HGBH41JXMN109186,2025-08-22 10:00:00,,75.8,2025-08-22 10:02:00
test5543672913,sensor24_pressure,1HGBH41JXMN109186,2025-08-22 10:00:00,,33.0,2025-08-22 10:02:00
test5543672913,sensor24_temperature,1HGBH41JXMN109186,2025-08-22 10:00:00,,75.7,2025-08-22 10:02:00
```

## データ検証クエリ

### センサーIDの確認
```sql
SELECT DISTINCT sensor_id 
FROM v1__sensor_reading 
WHERE sensor_id LIKE 'sensor%'
ORDER BY sensor_id;
```

### 車輪番号の抽出
```sql
SELECT 
    DISTINCT SUBSTRING(sensor_id, 7, 2) as wheel_number
FROM v1__sensor_reading
WHERE sensor_id LIKE 'sensor%'
ORDER BY wheel_number;
```

### GPS出力頻度の確認
```sql
WITH gps_counts AS (
    SELECT 
        vin,
        COUNT(CASE WHEN sensor_id = 'latitude' THEN 1 END) as gps_count,
        COUNT(CASE WHEN sensor_id LIKE 'sensor%_pressure' THEN 1 END) as pressure_count
    FROM v1__sensor_reading
    GROUP BY vin
)
SELECT 
    vin,
    gps_count,
    pressure_count,
    ROUND(pressure_count::FLOAT / gps_count, 1) as readings_per_gps
FROM gps_counts;
```