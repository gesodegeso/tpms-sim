# TPMS車輪番号体系ガイド

## 概要
本ドキュメントでは、TPMSシミュレータで使用する車輪番号の割り当て体系について説明します。

## 車輪番号体系

### 基本ルール
- **第1桁**: 軸番号（1=前軸、2=第2軸、3=第3軸）
- **第2桁**: 位置番号
  - 1: 左側（外側）
  - 2: 左側（内側）※ダブルタイヤの場合
  - 3: 右側（内側）※ダブルタイヤの場合
  - 4: 右側（外側）

### 4輪車（乗用車・小型車両）
```
      前
    [11] [14]     11: 左前輪
       | |        14: 右前輪
       | |        
    [21] [24]     21: 左後輪
      後          24: 右後輪
```

### 6輪車（小型トラック・配送車）
```
      前
    [11] [14]     11: 左前輪（シングル）
       | |        14: 右前輪（シングル）
       | |        
    [21|22]       21: 後左外輪
    [23|24]       22: 後左内輪
      後          23: 後右内輪
                  24: 後右外輪
```

### 8輪車（中型トラック）
```
      前
    [11] [14]     11: 左前輪（シングル）
       | |        14: 右前輪（シングル）
       | |        
    [21] [24]     21: 第2軸左輪（シングル）
       | |        24: 第2軸右輪（シングル）
       | |        
    [31|32]       31: 第3軸左外輪
    [33|34]       32: 第3軸左内輪
      後          33: 第3軸右内輪
                  34: 第3軸右外輪
```

### 10輪車（大型トラック・セミトレーラー）
```
      前
    [11] [14]     11: 左前輪（シングル）
       | |        14: 右前輪（シングル）
       | |        
    [21|22]       21: 第2軸左外輪
    [23|24]       22: 第2軸左内輪
       | |        23: 第2軸右内輪
       | |        24: 第2軸右外輪
    [31|32]       
    [33|34]       31: 第3軸左外輪
      後          32: 第3軸左内輪
                  33: 第3軸右内輪
                  34: 第3軸右外輪
```

## センサーID形式

各車輪のセンサーIDは以下の形式で生成されます：

- **圧力センサー**: `sensor{番号}_pressure`
  - 例: `sensor11_pressure`（左前輪の圧力）
- **温度センサー**: `sensor{番号}_temperature`
  - 例: `sensor14_temperature`（右前輪の温度）

## 使用例

### Python
```python
# 4輪車の車輪位置取得
wheel_positions = ['11', '14', '21', '24']

# センサーIDの生成
for pos in wheel_positions:
    pressure_id = f'sensor{pos}_pressure'
    temperature_id = f'sensor{pos}_temperature'
    print(f"Position {pos}: {pressure_id}, {temperature_id}")
```

### SQL (ClickHouse)
```sql
-- 特定車輪の圧力データ取得
SELECT 
    read_at,
    reading as pressure_psi
FROM v1__sensor_reading
WHERE sensor_id = 'sensor11_pressure'
  AND vin = 'YOUR_VIN_HERE'
ORDER BY read_at;

-- 全車輪の最新圧力値
SELECT 
    sensor_id,
    argMax(reading, read_at) as latest_pressure
FROM v1__sensor_reading
WHERE sensor_id LIKE 'sensor%_pressure'
GROUP BY sensor_id
ORDER BY sensor_id;
```

## 注意事項

1. **番号の飛び**: 4輪車では12, 13が使用されず、11から14に飛びます
2. **ダブルタイヤ**: 後輪のダブルタイヤでは、内側・外側の区別があります
3. **軸の識別**: 第1桁で軸を識別できるため、データ分析時に便利です

## データ分析での活用

### 軸ごとの集計
```sql
-- 軸ごとの平均圧力
SELECT 
    SUBSTRING(sensor_id, 7, 1) as axle,
    AVG(reading) as avg_pressure
FROM v1__sensor_reading
WHERE sensor_id LIKE 'sensor%_pressure'
GROUP BY axle
ORDER BY axle;
```

### 左右バランスの確認
```sql
-- 左右の圧力差確認（4輪車の例）
WITH pressure_data AS (
    SELECT 
        CASE 
            WHEN sensor_id IN ('sensor11_pressure', 'sensor21_pressure') THEN 'left'
            WHEN sensor_id IN ('sensor14_pressure', 'sensor24_pressure') THEN 'right'
        END as side,
        AVG(reading) as avg_pressure
    FROM v1__sensor_reading
    WHERE sensor_id LIKE 'sensor%_pressure'
      AND sensor_id IN ('sensor11_pressure', 'sensor14_pressure', 
                        'sensor21_pressure', 'sensor24_pressure')
    GROUP BY side
)
SELECT 
    MAX(CASE WHEN side = 'left' THEN avg_pressure END) as left_avg,
    MAX(CASE WHEN side = 'right' THEN avg_pressure END) as right_avg,
    ABS(MAX(CASE WHEN side = 'left' THEN avg_pressure END) - 
        MAX(CASE WHEN side = 'right' THEN avg_pressure END)) as difference
FROM pressure_data;
```

## 変更履歴

### v2.1 (現在)
- 車輪番号体系を業界標準に準拠
- センサーIDプレフィクスを`tire`から`sensor`に変更

### v2.0
- 停止中モードの追加
- GPS出力頻度の最適化

### v1.0
- 初期リリース