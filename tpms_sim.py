#!/usr/bin/env python3
"""
TPMS (Tire Pressure Monitoring System) Sensor Data Simulator
Generates simulated tire pressure and temperature data in Parquet format for ClickHouse import
Version 2.0 - Added stationary mode support and GPS output frequency control
"""

import argparse
import random
import string
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import warnings
warnings.filterwarnings('ignore')

# Try to import OSMnx for route distance calculation
try:
    import osmnx as ox
    import networkx as nx
    OSMNX_AVAILABLE = True
except ImportError:
    OSMNX_AVAILABLE = False
    print("Warning: OSMnx not available. Will use simplified distance calculation.")

class TPMSSimulator:
    def __init__(self, num_vehicles: int, num_wheels: int, start_location: str, 
                 end_location: str, avg_speed_mph: float, avg_temp_f: float, 
                 vehicle_type: str, tenant: Optional[str] = None, 
                 update_interval_min: int = 5):
        """
        Initialize TPMS Simulator
        
        Args:
            num_vehicles: Number of vehicles to simulate
            num_wheels: Number of wheels per vehicle (4, 6, 8, or 10)
            start_location: Starting location (format: "City, State")
            end_location: Ending location (format: "City, State")
            avg_speed_mph: Average speed in miles per hour (0 for stationary mode)
            avg_temp_f: Average ambient temperature in Fahrenheit
            vehicle_type: Type of vehicle ("regular" or "heavy_duty")
            tenant: Tenant name (optional)
            update_interval_min: Data update interval in minutes (default: 5)
        """
        self.num_vehicles = num_vehicles
        self.num_wheels = num_wheels
        self.start_location = start_location
        self.end_location = end_location
        self.avg_speed_mph = avg_speed_mph
        self.avg_temp_f = avg_temp_f
        self.vehicle_type = vehicle_type.lower().replace(" ", "_")
        self.tenant = tenant or f"test{random.randint(1000000000, 9999999999)}"
        self.update_interval_min = update_interval_min
        self.stationary_mode = (avg_speed_mph == 0)
        
        # Validate inputs
        if num_wheels not in [4, 6, 8, 10]:
            raise ValueError("Number of wheels must be 4, 6, 8, or 10")
        if num_wheels % 2 != 0:
            raise ValueError("Number of wheels must be even")
        if vehicle_type.lower() not in ["regular", "heavy_duty", "heavy duty"]:
            raise ValueError("Vehicle type must be 'regular' or 'heavy_duty'")
        
        # Set pressure ranges based on vehicle type
        if self.vehicle_type == "regular":
            self.pressure_range = (31, 35)  # PSI for regular vehicles
        else:
            self.pressure_range = (85, 120)  # PSI for heavy duty vehicles
        
        # Initialize geolocator
        self.geolocator = Nominatim(user_agent="tpms_simulator")
        
        # Get coordinates for start and end locations
        self.start_coords = self._get_coordinates(start_location)
        self.end_coords = self._get_coordinates(end_location)
        
        # Calculate route distance
        self.route_distance_miles = self._calculate_route_distance()
        
        # Calculate trip duration
        if self.stationary_mode:
            # Use legal speed limit for duration calculation in stationary mode
            legal_speed = self._get_legal_speed()
            self.trip_duration_hours = self.route_distance_miles / legal_speed
            print(f"Stationary mode: Using legal speed {legal_speed} mph for duration calculation")
        else:
            self.trip_duration_hours = self.route_distance_miles / avg_speed_mph
        
        # Generate VINs for all vehicles
        self.vins = [self._generate_vin() for _ in range(num_vehicles)]
    
    def _get_legal_speed(self) -> float:
        """Get default legal speed based on start and end locations"""
        # Check if interstate (different states)
        start_state = self.start_location.split(',')[-1].strip()
        end_state = self.end_location.split(',')[-1].strip()
        
        if start_state != end_state:
            # Interstate travel - use highway speed
            return 65.0
        else:
            # Intrastate travel - use state road speed
            return 55.0
    
    def _get_coordinates(self, location: str) -> Tuple[float, float]:
        """Get coordinates for a location string"""
        location_full = f"{location}, USA"
        try:
            loc = self.geolocator.geocode(location_full)
            if loc:
                return (loc.latitude, loc.longitude)
            else:
                raise ValueError(f"Could not find coordinates for {location}")
        except Exception as e:
            print(f"Error getting coordinates for {location}: {e}")
            raise
    
    def _calculate_route_distance(self) -> float:
        """Calculate actual route distance between start and end points"""
        # Try to use OSMnx for actual route distance
        if OSMNX_AVAILABLE:
            try:
                # Download road network
                G = ox.graph_from_point(self.start_coords, dist=1000000, network_type='drive')
                
                # Find nearest nodes
                orig_node = ox.nearest_nodes(G, self.start_coords[1], self.start_coords[0])
                dest_node = ox.nearest_nodes(G, self.end_coords[1], self.end_coords[0])
                
                # Calculate shortest path
                route = nx.shortest_path(G, orig_node, dest_node, weight='length')
                
                # Calculate route distance
                edge_lengths = ox.utils_graph.get_route_edge_attributes(G, route, 'length')
                route_distance_m = sum(edge_lengths)
                route_distance_miles = route_distance_m * 0.000621371
                
                print(f"Calculated actual route distance: {route_distance_miles:.2f} miles")
                return route_distance_miles
            except Exception as e:
                print(f"OSMnx calculation failed: {e}. Using simplified calculation.")
        
        # Fallback: Use geodesic distance with multiplier
        straight_distance = geodesic(self.start_coords, self.end_coords).miles
        estimated_distance = straight_distance * 1.2  # Add 20% for road curvature
        print(f"Using estimated route distance: {estimated_distance:.2f} miles")
        return estimated_distance
    
    def _generate_vin(self) -> str:
        """Generate a valid-looking VIN number"""
        # VIN structure: WMI (3) + VDS (6) + VIS (8) = 17 characters
        # Example: 1HGBH41JXMN109186
        
        # WMI (World Manufacturer Identifier)
        wmi = ''.join(random.choices('123456789', k=1)) + \
              ''.join(random.choices('ABCDEFGHJKLMNPRSTUVWXYZ', k=2))
        
        # VDS (Vehicle Descriptor Section)
        vds = ''.join(random.choices('ABCDEFGHJKLMNPRSTUVWXYZ0123456789', k=5))
        
        # Check digit (position 9)
        check = random.choice('0123456789X')
        
        # VIS (Vehicle Identifier Section)
        # Year (position 10)
        year = random.choice('ABCDEFGHJKLMNPRSTVWXY123456789')
        # Plant code (position 11)
        plant = random.choice('ABCDEFGHJKLMNPRSTUVWXYZ0123456789')
        # Sequential number (positions 12-17)
        sequential = ''.join(random.choices('0123456789', k=6))
        
        vin = wmi + vds + check + year + plant + sequential
        return vin
    
    def _get_wheel_positions(self) -> List[str]:
        """Get wheel position codes based on number of wheels"""
        if self.num_wheels == 4:
            # Standard 4-wheel: FL, FR, RL, RR
            return ['11', '12', '21', '22']
        elif self.num_wheels == 6:
            # 6-wheel: FL, FR, RL-inner, RL-outer, RR-inner, RR-outer
            return ['11', '12', '21', '22', '31', '32']
        elif self.num_wheels == 8:
            # 8-wheel: FL, FR, RL1-inner, RL1-outer, RL2-inner, RL2-outer, RR1-inner, RR1-outer
            return ['11', '12', '21', '22', '31', '32', '41', '42']
        elif self.num_wheels == 10:
            # 10-wheel: FL, FR, RL1-inner, RL1-outer, RL2-inner, RL2-outer, 
            #          RR1-inner, RR1-outer, RR2-inner, RR2-outer
            return ['11', '12', '21', '22', '31', '32', '41', '42', '51', '52']
    
    def _generate_sensor_data(self, vin: str, start_time: datetime) -> List[Dict]:
        """Generate sensor data for one vehicle"""
        records = []
        wheel_positions = self._get_wheel_positions()
        
        # Initialize pressure and temperature for each wheel
        wheel_pressures = {}
        wheel_temps = {}
        
        for pos in wheel_positions:
            # Initial pressure with slight variation
            if self.vehicle_type == "regular":
                base_pressure = random.uniform(32, 34)
            else:
                base_pressure = random.uniform(90, 110)
            wheel_pressures[pos] = base_pressure
            
            # Initial temperature close to ambient
            wheel_temps[pos] = self.avg_temp_f + random.uniform(-2, 2)
        
        # Calculate number of data points
        trip_duration_min = self.trip_duration_hours * 60
        num_points = int(trip_duration_min / self.update_interval_min) + 1
        
        # Generate interpolated coordinates for the trip (or fixed for stationary)
        if self.stationary_mode:
            # Vehicle stays at start location
            lat_points = [self.start_coords[0]] * num_points
            lon_points = [self.start_coords[1]] * num_points
        else:
            # Vehicle moves from start to end
            lat_points = np.linspace(self.start_coords[0], self.end_coords[0], num_points)
            lon_points = np.linspace(self.start_coords[1], self.end_coords[1], num_points)
        
        current_time = start_time
        gps_output_counter = 0  # Counter for GPS output frequency
        
        for i in range(num_points):
            read_at = current_time
            ingested_at = current_time + timedelta(minutes=2)
            
            # Current position
            current_lat = lat_points[i]
            current_lon = lon_points[i]
            
            # Progress through trip (0 to 1)
            progress = i / max(num_points - 1, 1)
            
            # Generate tire pressure and temperature records
            for pos in wheel_positions:
                if self.stationary_mode:
                    # Stationary mode: minimal pressure variation, no temperature change
                    pressure_variation = random.uniform(-0.2, 0.2)  # Smaller variation
                    wheel_pressures[pos] = max(
                        self.pressure_range[0], 
                        min(self.pressure_range[1], 
                            wheel_pressures[pos] + pressure_variation)
                    )
                    # Temperature stays constant (minor variations only)
                    wheel_temps[pos] = self.avg_temp_f + random.uniform(-1, 1)
                else:
                    # Moving mode: normal variations
                    # Simulate pressure changes (small variations)
                    pressure_variation = random.uniform(-0.5, 0.5)
                    wheel_pressures[pos] = max(
                        self.pressure_range[0], 
                        min(self.pressure_range[1], 
                            wheel_pressures[pos] + pressure_variation)
                    )
                    
                    # Simulate temperature increase during driving
                    # Temperature rises more at the beginning and stabilizes
                    temp_rise = 10 * (1 - np.exp(-3 * progress))  # Asymptotic rise to ~10°F
                    temp_variation = random.uniform(-1, 1)
                    wheel_temps[pos] = self.avg_temp_f + temp_rise + temp_variation
                    
                    # Add noise to rear wheels (they typically run slightly hotter)
                    if pos[0] in ['2', '3', '4', '5']:  # Rear wheels
                        wheel_temps[pos] += random.uniform(0, 2)
                
                # Pressure record
                records.append({
                    'tenant': self.tenant,
                    'sensor_id': f'tire{pos}_pressure',
                    'vin': vin,
                    'read_at': read_at,
                    'trigger': '',
                    'reading': round(wheel_pressures[pos], 1),
                    'ingested_at': ingested_at
                })
                
                # Temperature record
                records.append({
                    'tenant': self.tenant,
                    'sensor_id': f'tire{pos}_temperature',
                    'vin': vin,
                    'read_at': read_at,
                    'trigger': '',
                    'reading': round(wheel_temps[pos], 1),
                    'ingested_at': ingested_at
                })
            
            # Add GPS records every 2 pressure/temperature updates
            # Counter increments each time we process all wheels
            gps_output_counter += 1
            if gps_output_counter % 2 == 1:  # Output GPS on 1st, 3rd, 5th... iterations (1-indexed)
                records.append({
                    'tenant': self.tenant,
                    'sensor_id': 'latitude',
                    'vin': vin,
                    'read_at': read_at,
                    'trigger': '',
                    'reading': round(current_lat, 6),
                    'ingested_at': ingested_at
                })
                
                records.append({
                    'tenant': self.tenant,
                    'sensor_id': 'longitude',
                    'vin': vin,
                    'read_at': read_at,
                    'trigger': '',
                    'reading': round(current_lon, 6),
                    'ingested_at': ingested_at
                })
            
            # Advance time
            current_time += timedelta(minutes=self.update_interval_min)
        
        return records
    
    def generate_dataset(self) -> pd.DataFrame:
        """Generate complete dataset for all vehicles"""
        print(f"Generating TPMS data for {self.num_vehicles} vehicles...")
        if self.stationary_mode:
            print(f"Mode: STATIONARY (vehicles remain at {self.start_location})")
            legal_speed = self._get_legal_speed()
            print(f"Legal speed for duration calculation: {legal_speed} mph")
        else:
            print(f"Mode: MOVING (speed: {self.avg_speed_mph} mph)")
        print(f"Route: {self.start_location} to {self.end_location}")
        print(f"Distance: {self.route_distance_miles:.2f} miles")
        print(f"Duration for data generation: {self.trip_duration_hours:.2f} hours")
        print(f"Vehicle type: {self.vehicle_type}")
        print(f"Number of wheels per vehicle: {self.num_wheels}")
        print(f"GPS output frequency: Every {self.update_interval_min * 2} minutes")
        
        all_records = []
        start_time = datetime.now().replace(microsecond=0, second=0)
        
        for idx, vin in enumerate(self.vins):
            print(f"Generating data for vehicle {idx + 1}/{self.num_vehicles} (VIN: {vin})")
            vehicle_records = self._generate_sensor_data(vin, start_time)
            all_records.extend(vehicle_records)
        
        # Create DataFrame
        df = pd.DataFrame(all_records)
        
        # Convert datetime columns to proper format
        df['read_at'] = pd.to_datetime(df['read_at'])
        df['ingested_at'] = pd.to_datetime(df['ingested_at'])
        
        # Sort by ingested_at, then vin, then sensor_id
        df = df.sort_values(['ingested_at', 'vin', 'sensor_id'])
        
        return df
    
    def save_to_parquet(self, df: pd.DataFrame, filename: str = None):
        """Save DataFrame to Parquet file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            mode_suffix = 'stationary' if self.stationary_mode else 'moving'
            filename = f'tpms_data_{mode_suffix}_{timestamp}.parquet'
        
        # Ensure data types match ClickHouse schema
        df['tenant'] = df['tenant'].astype(str)
        df['sensor_id'] = df['sensor_id'].astype(str)
        df['vin'] = df['vin'].astype(str)
        df['trigger'] = df['trigger'].astype(str)
        df['reading'] = df['reading'].astype(float)
        
        # Save to Parquet
        df.to_parquet(filename, engine='pyarrow', compression='snappy', index=False)
        print(f"Data saved to {filename}")
        print(f"Total records: {len(df)}")
        
        # Show GPS record statistics
        gps_records = df[df['sensor_id'].isin(['latitude', 'longitude'])]
        pressure_records = df[df['sensor_id'].str.contains('pressure')]
        print(f"Pressure/Temperature records: {len(pressure_records)}")
        print(f"GPS records: {len(gps_records)}")
        print(f"Ratio: 1 GPS pair per {len(pressure_records) / (len(gps_records) / 2):.1f} pressure readings")
        
        return filename

def main():
    parser = argparse.ArgumentParser(description='TPMS Sensor Data Simulator')
    
    # Required arguments
    parser.add_argument('--vehicles', type=int, required=True, 
                       help='Number of vehicles')
    parser.add_argument('--wheels', type=int, required=True, choices=[4, 6, 8, 10],
                       help='Number of wheels per vehicle (4, 6, 8, or 10)')
    parser.add_argument('--start', type=str, required=True,
                       help='Starting location (format: "City, State")')
    parser.add_argument('--end', type=str, required=True,
                       help='Ending location (format: "City, State")')
    parser.add_argument('--speed', type=float, required=True,
                       help='Average speed in mph (0 for stationary mode)')
    parser.add_argument('--temp', type=float, required=True,
                       help='Average ambient temperature in Fahrenheit')
    parser.add_argument('--type', type=str, required=True, 
                       choices=['regular', 'heavy_duty'],
                       help='Vehicle type (regular or heavy_duty)')
    
    # Optional arguments
    parser.add_argument('--tenant', type=str, default=None,
                       help='Tenant name (optional)')
    parser.add_argument('--interval', type=int, default=5,
                       help='Data update interval in minutes (default: 5)')
    parser.add_argument('--output', type=str, default=None,
                       help='Output filename for Parquet file')
    
    args = parser.parse_args()
    
    # Create simulator
    simulator = TPMSSimulator(
        num_vehicles=args.vehicles,
        num_wheels=args.wheels,
        start_location=args.start,
        end_location=args.end,
        avg_speed_mph=args.speed,
        avg_temp_f=args.temp,
        vehicle_type=args.type,
        tenant=args.tenant,
        update_interval_min=args.interval
    )
    
    # Generate dataset
    df = simulator.generate_dataset()
    
    # Save to Parquet
    simulator.save_to_parquet(df, args.output)

if __name__ == "__main__":
    main()