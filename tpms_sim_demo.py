#!/usr/bin/env python3
"""
TPMS Simulator - Example Usage Script
This script demonstrates various usage patterns of the TPMS simulator
"""

from tpms_simulator import TPMSSimulator
import pandas as pd

def example_regular_vehicle():
    """Example: Regular vehicles (cars) simulation"""
    print("=" * 60)
    print("Example 1: Regular Vehicles (4-wheel cars)")
    print("=" * 60)
    
    simulator = TPMSSimulator(
        num_vehicles=3,
        num_wheels=4,
        start_location="San Diego, CA",
        end_location="Los Angeles, CA",
        avg_speed_mph=65,
        avg_temp_f=75,
        vehicle_type="regular",
        tenant="car_rental_company"
    )
    
    df = simulator.generate_dataset()
    filename = simulator.save_to_parquet(df, "regular_vehicles_example.parquet")
    
    # Display sample data
    print("\nSample data (first 10 records):")
    print(df.head(10))
    
    # Display statistics
    print("\nData Statistics:")
    print(f"Total records: {len(df)}")
    print(f"Unique VINs: {df['vin'].nunique()}")
    print(f"Date range: {df['read_at'].min()} to {df['read_at'].max()}")
    print(f"Pressure range: {df[df['sensor_id'].str.contains('pressure')]['reading'].min():.1f} - "
          f"{df[df['sensor_id'].str.contains('pressure')]['reading'].max():.1f} PSI")
    
    return df

def example_heavy_duty_vehicle():
    """Example: Heavy duty vehicles (trucks) simulation"""
    print("\n" + "=" * 60)
    print("Example 2: Heavy Duty Vehicles (10-wheel trucks)")
    print("=" * 60)
    
    simulator = TPMSSimulator(
        num_vehicles=2,
        num_wheels=10,
        start_location="Phoenix, AZ",
        end_location="Albuquerque, NM",
        avg_speed_mph=55,
        avg_temp_f=95,  # Hot desert conditions
        vehicle_type="heavy_duty",
        tenant="trucking_logistics",
        update_interval_min=10  # Less frequent updates for long-haul
    )
    
    df = simulator.generate_dataset()
    filename = simulator.save_to_parquet(df, "heavy_duty_example.parquet")
    
    # Display wheel configuration
    print("\nWheel Configuration for 10-wheel truck:")
    wheel_sensors = df[df['sensor_id'].str.contains('tire')]['sensor_id'].unique()
    wheel_positions = sorted(set([s.split('_')[0] for s in wheel_sensors]))
    for pos in wheel_positions:
        print(f"  {pos}")
    
    # Display pressure by wheel position
    print("\nAverage pressure by wheel position:")
    pressure_df = df[df['sensor_id'].str.contains('pressure')].copy()
    pressure_df['wheel_pos'] = pressure_df['sensor_id'].str.extract(r'tire(\d+)_')
    avg_pressure = pressure_df.groupby('wheel_pos')['reading'].mean().sort_index()
    for pos, pressure in avg_pressure.items():
        print(f"  Wheel {pos}: {pressure:.1f} PSI")
    
    return df

def example_mixed_fleet():
    """Example: Mixed fleet with 6-wheel delivery trucks"""
    print("\n" + "=" * 60)
    print("Example 3: Mixed Fleet (6-wheel delivery trucks)")
    print("=" * 60)
    
    simulator = TPMSSimulator(
        num_vehicles=4,
        num_wheels=6,
        start_location="Chicago, IL",
        end_location="Milwaukee, WI",
        avg_speed_mph=60,
        avg_temp_f=68,
        vehicle_type="heavy_duty",
        tenant="delivery_service"
    )
    
    df = simulator.generate_dataset()
    filename = simulator.save_to_parquet(df, "mixed_fleet_example.parquet")
    
    # Analyze temperature rise during trip
    print("\nTemperature Analysis (first vehicle):")
    first_vin = df['vin'].unique()[0]
    temp_df = df[(df['vin'] == first_vin) & (df['sensor_id'].str.contains('temperature'))]
    
    # Get start and end temperatures for front and rear wheels
    front_temp_start = temp_df[temp_df['sensor_id'] == 'tire11_temperature']['reading'].iloc[0]
    front_temp_end = temp_df[temp_df['sensor_id'] == 'tire11_temperature']['reading'].iloc[-1]
    rear_temp_start = temp_df[temp_df['sensor_id'] == 'tire21_temperature']['reading'].iloc[0]
    rear_temp_end = temp_df[temp_df['sensor_id'] == 'tire21_temperature']['reading'].iloc[-1]
    
    print(f"  Front wheel temperature rise: {front_temp_start:.1f}°F → {front_temp_end:.1f}°F "
          f"(+{front_temp_end - front_temp_start:.1f}°F)")
    print(f"  Rear wheel temperature rise: {rear_temp_start:.1f}°F → {rear_temp_end:.1f}°F "
          f"(+{rear_temp_end - rear_temp_start:.1f}°F)")
    
    return df

def example_stationary_monitoring():
    """Example: Stationary monitoring in maintenance shop"""
    print("\n" + "=" * 60)
    print("Example 4: Stationary Monitoring (maintenance shop)")
    print("=" * 60)
    
    simulator = TPMSSimulator(
        num_vehicles=3,
        num_wheels=4,
        start_location="Phoenix, AZ",
        end_location="Tucson, AZ",
        avg_speed_mph=0,  # STATIONARY MODE
        avg_temp_f=72,
        vehicle_type="regular",
        tenant="repair_shop",
        update_interval_min=15  # Less frequent updates for stationary monitoring
    )
    
    df = simulator.generate_dataset()
    filename = simulator.save_to_parquet(df, "stationary_monitoring_example.parquet")
    
    # Analyze pressure stability in stationary mode
    print("\nPressure Stability Analysis (stationary mode):")
    first_vin = df['vin'].unique()[0]
    pressure_df = df[(df['vin'] == first_vin) & (df['sensor_id'].str.contains('pressure'))]
    
    for sensor in pressure_df['sensor_id'].unique()[:2]:  # Show first 2 wheels
        sensor_data = pressure_df[pressure_df['sensor_id'] == sensor]['reading']
        print(f"  {sensor}:")
        print(f"    Mean: {sensor_data.mean():.2f} PSI")
        print(f"    Std Dev: {sensor_data.std():.3f} PSI")
        print(f"    Range: {sensor_data.min():.2f} - {sensor_data.max():.2f} PSI")
    
    # Verify no temperature change
    temp_df = df[(df['vin'] == first_vin) & (df['sensor_id'].str.contains('temperature'))]
    temp_ranges = temp_df.groupby('sensor_id')['reading'].agg(['min', 'max'])
    print("\nTemperature Stability (should be minimal change):")
    print(temp_ranges.head(2))
    
    # Check GPS output frequency
    gps_count = len(df[(df['vin'] == first_vin) & (df['sensor_id'] == 'latitude')])
    pressure_count = len(df[(df['vin'] == first_vin) & (df['sensor_id'].str.contains('pressure'))]) / 4  # Divide by number of wheels
    print(f"\nGPS Output Frequency:")
    print(f"  Pressure readings: {int(pressure_count)}")
    print(f"  GPS readings: {gps_count}")
    print(f"  Ratio: 1 GPS per {pressure_count/gps_count:.1f} pressure readings")
    
    return df

def example_short_trip():
    """Example: Short urban trip with frequent updates"""
    print("\n" + "=" * 60)
    print("Example 5: Short Urban Trip (frequent updates)")
    print("=" * 60)
    
    simulator = TPMSSimulator(
        num_vehicles=5,
        num_wheels=4,
        start_location="Manhattan, NY",
        end_location="Brooklyn, NY",
        avg_speed_mph=25,  # City driving speed
        avg_temp_f=72,
        vehicle_type="regular",
        tenant="taxi_company",
        update_interval_min=2  # More frequent updates for city driving
    )
    
    df = simulator.generate_dataset()
    filename = simulator.save_to_parquet(df, "short_trip_example.parquet")
    
    # Show GPS track for first vehicle
    print("\nGPS Track Sample (first vehicle, first 5 points):")
    first_vin = df['vin'].unique()[0]
    gps_df = df[(df['vin'] == first_vin) & (df['sensor_id'].isin(['latitude', 'longitude']))]
    
    # Reshape to have lat/lon in columns
    gps_pivot = gps_df.pivot_table(
        index='read_at', 
        columns='sensor_id', 
        values='reading'
    ).reset_index()
    
    print(gps_pivot.head())
    
    return df

def verify_clickhouse_compatibility(df):
    """Verify that the DataFrame is compatible with ClickHouse schema"""
    print("\n" + "=" * 60)
    print("ClickHouse Compatibility Check")
    print("=" * 60)
    
    required_columns = ['tenant', 'sensor_id', 'vin', 'read_at', 'trigger', 'reading', 'ingested_at']
    
    print("Column validation:")
    for col in required_columns:
        if col in df.columns:
            print(f"  ✓ {col}: {df[col].dtype}")
        else:
            print(f"  ✗ {col}: MISSING")
    
    # Check data types
    print("\nData type validation:")
    print(f"  tenant: {'✓' if df['tenant'].dtype == 'object' else '✗'} (should be string)")
    print(f"  sensor_id: {'✓' if df['sensor_id'].dtype == 'object' else '✗'} (should be string)")
    print(f"  vin: {'✓' if df['vin'].dtype == 'object' else '✗'} (should be string)")
    print(f"  trigger: {'✓' if df['trigger'].dtype == 'object' else '✗'} (should be string)")
    print(f"  reading: {'✓' if pd.api.types.is_numeric_dtype(df['reading']) else '✗'} (should be numeric)")
    print(f"  read_at: {'✓' if pd.api.types.is_datetime64_any_dtype(df['read_at']) else '✗'} (should be datetime)")
    print(f"  ingested_at: {'✓' if pd.api.types.is_datetime64_any_dtype(df['ingested_at']) else '✗'} (should be datetime)")
    
    # Check VIN format
    print("\nVIN format validation:")
    vin_lengths = df['vin'].str.len().unique()
    if len(vin_lengths) == 1 and vin_lengths[0] == 17:
        print(f"  ✓ All VINs are 17 characters")
    else:
        print(f"  ✗ VIN lengths vary: {vin_lengths}")
    
    # Check trigger is empty
    if df['trigger'].eq('').all():
        print("  ✓ All trigger values are empty")
    else:
        print("  ✗ Some trigger values are not empty")

def main():
    """Run all examples"""
    print("TPMS Simulator - Demonstration Examples")
    print("=" * 60)
    
    # Run examples
    df1 = example_regular_vehicle()
    df2 = example_heavy_duty_vehicle()
    df3 = example_mixed_fleet()
    df4 = example_stationary_monitoring()  # New stationary mode example
    df5 = example_short_trip()
    
    # Verify ClickHouse compatibility for the last generated dataset
    verify_clickhouse_compatibility(df5)
    
    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("Generated files:")
    print("  - regular_vehicles_example.parquet")
    print("  - heavy_duty_example.parquet")
    print("  - mixed_fleet_example.parquet")
    print("  - stationary_monitoring_example.parquet")
    print("  - short_trip_example.parquet")
    print("\nThese files can be imported directly into ClickHouse.")

if __name__ == "__main__":
    main()