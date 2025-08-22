#!/usr/bin/env python3
"""
TPMS (Tire Pressure Monitoring System) Sensor Data Simulator
Generates simulated tire pressure and temperature data in Parquet format for ClickHouse import
Version 3.0 - Added traffic events and data anomaly simulation for testing
"""

import argparse
import random
import string
import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
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

class TrafficEvent:
    """Class to represent traffic events"""
    def __init__(self, event_type: str, start_time: datetime, duration_min: int, severity: float = 1.0):
        self.event_type = event_type  # 'congestion', 'signal', 'breakdown', 'accident'
        self.start_time = start_time
        self.duration_min = duration_min
        self.end_time = start_time + timedelta(minutes=duration_min)
        self.severity = severity  # 0-1 scale for impact severity

class AnomalyGenerator:
    """Class to generate various data anomalies for testing"""
    
    @staticmethod
    def missing_sensor(records: List[Dict], sensor_id: str) -> List[Dict]:
        """Remove specific sensor data"""
        return [r for r in records if r['sensor_id'] != sensor_id]
    
    @staticmethod
    def missing_all_sensors(records: List[Dict], timestamp: datetime) -> List[Dict]:
        """Remove all sensor data at specific timestamp"""
        return [r for r in records if r['read_at'] != timestamp]
    
    @staticmethod
    def random_missing(records: List[Dict], rate: float) -> List[Dict]:
        """Randomly remove records"""
        return [r for r in records if random.random() > rate]
    
    @staticmethod
    def out_of_range(record: Dict) -> Dict:
        """Generate out-of-range values"""
        if 'pressure' in record['sensor_id']:
            # Generate extreme pressure values
            record['reading'] = random.choice([-10, 0, 999, 1500])
        elif 'temperature' in record['sensor_id']:
            # Generate extreme temperature values
            record['reading'] = random.choice([-50, 0, 300, 500])
        elif record['sensor_id'] == 'latitude':
            record['reading'] = random.choice([-999, 999])
        elif record['sensor_id'] == 'longitude':
            record['reading'] = random.choice([-999, 999])
        record['trigger'] = '1'  # Mark as anomaly
        return record
    
    @staticmethod
    def null_value(record: Dict) -> Dict:
        """Generate null/NaN values"""
        record['reading'] = None  # Will become NaN in DataFrame
        record['trigger'] = '1'
        return record
    
    @staticmethod
    def duplicate_record(records: List[Dict], record_index: int) -> List[Dict]:
        """Duplicate a specific record"""
        if 0 <= record_index < len(records):
            duplicate = records[record_index].copy()
            duplicate['trigger'] = '1'
            records.insert(record_index + 1, duplicate)
        return records
    
    @staticmethod
    def timestamp_reversal(record: Dict, prev_timestamp: datetime) -> Dict:
        """Create timestamp reversal"""
        record['read_at'] = prev_timestamp - timedelta(minutes=random.randint(1, 10))
        record['trigger'] = '1'
        return record
    
    @staticmethod
    def future_timestamp(record: Dict) -> Dict:
        """Create future timestamp"""
        record['read_at'] = datetime.now() + timedelta(days=random.randint(1, 365))
        record['trigger'] = '1'
        return record
    
    @staticmethod
    def ingested_before_read(record: Dict) -> Dict:
        """Make ingested_at before read_at"""
        record['ingested_at'] = record['read_at'] - timedelta(minutes=random.randint(1, 60))
        record['trigger'] = '1'
        return record
    
    @staticmethod
    def invalid_vin(record: Dict) -> Dict:
        """Generate invalid VIN"""
        record['vin'] = random.choice([
            'INVALID_VIN_123',
            '00000000000000000',
            'XXXXXXXXXXXXXXXXX',
            ''.join(random.choices('!@#$%^&*()', k=17))
        ])
        record['trigger'] = '1'
        return record
    
    @staticmethod
    def invalid_sensor_id(record: Dict) -> Dict:
        """Generate invalid sensor ID"""
        record['sensor_id'] = random.choice([
            'invalid_sensor',
            'sensor99_unknown',
            'corrupted_#$%',
            ''
        ])
        record['trigger'] = '1'
        return record
    
    @staticmethod
    def corrupted_data(record: Dict) -> Dict:
        """Generate corrupted/garbled data"""
        if random.random() < 0.5:
            # Corrupt sensor_id
            record['sensor_id'] = ''.join(random.choices('!@#$%^&*()_+', k=10))
        else:
            # Corrupt tenant
            record['tenant'] = ''.join(random.choices('!@#$%^&*()_+', k=10))
        record['trigger'] = '1'
        return record

class TPMSSimulator:
    def __init__(self, num_vehicles: int, num_wheels: int, start_location: str, 
                 end_location: str, avg_speed_mph: float, avg_temp_f: float, 
                 vehicle_type: str, tenant: Optional[str] = None, 
                 update_interval_min: int = 5,
                 enable_traffic_events: bool = False,
                 enable_data_anomalies: bool = False,
                 anomaly_rate: float = 0.05,
                 anomaly_mode: str = 'mixed'):
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
            enable_traffic_events: Enable traffic event simulation
            enable_data_anomalies: Enable data anomaly generation
            anomaly_rate: Rate of anomaly occurrence (0-1)
            anomaly_mode: 'mixed' or 'single' anomaly types
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
        self.enable_traffic_events = enable_traffic_events
        self.enable_data_anomalies = enable_data_anomalies
        self.anomaly_rate = anomaly_rate
        self.anomaly_mode = anomaly_mode
        
        # Validate inputs
        if num_wheels not in [4, 6, 8, 10]:
            raise ValueError("Number of wheels must be 4, 6, 8, or 10")
        if num_wheels % 2 != 0:
            raise ValueError("Number of wheels must be even")
        if vehicle_type.lower() not in ["regular", "heavy_duty", "heavy duty"]:
            raise ValueError("Vehicle type must be 'regular' or 'heavy_duty'")
        if anomaly_mode not in ['mixed', 'single']:
            raise ValueError("Anomaly mode must be 'mixed' or 'single'")
        
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
        
        # Initialize anomaly generator
        self.anomaly_gen = AnomalyGenerator()
        
        # Select anomaly types for single mode
        if self.anomaly_mode == 'single' and self.enable_data_anomalies:
            self.selected_anomaly = random.choice([
                'missing_sensor', 'missing_all', 'random_missing',
                'out_of_range', 'null_value', 'duplicate',
                'timestamp_reversal', 'future_timestamp', 'ingested_before_read',
                'invalid_vin', 'invalid_sensor_id', 'corrupted_data'
            ])
            print(f"Single anomaly mode selected: {self.selected_anomaly}")
    
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
            # 4-wheel: FL(11), FR(14), RL(21), RR(24)
            return ['11', '14', '21', '24']
        elif self.num_wheels == 6:
            # 6-wheel: FL(11), FR(14), RL-outer(21), RL-inner(22), RR-inner(23), RR-outer(24)
            return ['11', '14', '21', '22', '23', '24']
        elif self.num_wheels == 8:
            # 8-wheel: FL(11), FR(14), 2nd-L(21), 2nd-R(24), 
            #         3rd-L-outer(31), 3rd-L-inner(32), 3rd-R-inner(33), 3rd-R-outer(34)
            return ['11', '14', '21', '24', '31', '32', '33', '34']
        elif self.num_wheels == 10:
            # 10-wheel: FL(11), FR(14), 
            #          2nd-L-outer(21), 2nd-L-inner(22), 2nd-R-inner(23), 2nd-R-outer(24),
            #          3rd-L-outer(31), 3rd-L-inner(32), 3rd-R-inner(33), 3rd-R-outer(34)
            return ['11', '14', '21', '22', '23', '24', '31', '32', '33', '34']
    
    def _generate_traffic_events(self, trip_duration_hours: float, start_time: datetime) -> List[TrafficEvent]:
        """Generate random traffic events during the trip"""
        events = []
        
        if not self.enable_traffic_events or self.stationary_mode:
            return events
        
        trip_duration_min = trip_duration_hours * 60
        
        # Generate congestion events (1-3 per trip)
        num_congestions = random.randint(1, 3)
        for _ in range(num_congestions):
            event_start = start_time + timedelta(minutes=random.uniform(10, trip_duration_min - 30))
            duration = random.randint(5, 30)  # 5-30 minutes
            events.append(TrafficEvent('congestion', event_start, duration, severity=random.uniform(0.2, 0.3)))
        
        # Generate signal stops (based on trip duration)
        num_signals = int(trip_duration_min / random.randint(5, 10))  # Every 5-10 minutes
        for _ in range(num_signals):
            event_start = start_time + timedelta(minutes=random.uniform(2, trip_duration_min - 2))
            duration = random.uniform(0.5, 2)  # 30 seconds to 2 minutes
            events.append(TrafficEvent('signal', event_start, duration, severity=1.0))
        
        # Generate breakdown (10% chance)
        if random.random() < 0.1:
            event_start = start_time + timedelta(minutes=random.uniform(20, trip_duration_min - 20))
            duration = random.randint(10, 30)  # 10-30 minutes
            breakdown_type = random.choice(['tire_puncture', 'engine_failure', 'sensor_failure'])
            events.append(TrafficEvent(f'breakdown_{breakdown_type}', event_start, duration, severity=1.0))
        
        # Generate accident (5% chance)
        if random.random() < 0.05:
            event_start = start_time + timedelta(minutes=random.uniform(10, trip_duration_min - 10))
            events.append(TrafficEvent('accident', event_start, 999, severity=1.0))  # Trip ends
        
        # Sort events by start time
        events.sort(key=lambda x: x.start_time)
        
        return events
    
    def _apply_traffic_event(self, event: TrafficEvent, current_speed: float, 
                            wheel_pressures: Dict, wheel_temps: Dict) -> Tuple[float, Dict, Dict, bool]:
        """Apply traffic event effects"""
        continue_trip = True
        
        if 'congestion' in event.event_type:
            # Reduce speed to 20-30% of normal
            current_speed = self.avg_speed_mph * event.severity
            
        elif 'signal' in event.event_type:
            # Complete stop
            current_speed = 0
            # Temperature slightly decreases during stop
            for pos in wheel_temps:
                wheel_temps[pos] -= random.uniform(0.5, 1.5)
                
        elif 'breakdown_tire_puncture' in event.event_type:
            # Random tire loses pressure rapidly
            affected_wheel = random.choice(list(wheel_pressures.keys()))
            wheel_pressures[affected_wheel] = random.uniform(5, 15)  # Severe pressure loss
            current_speed = 0
            
        elif 'breakdown_engine_failure' in event.event_type:
            # Complete stop
            current_speed = 0
            
        elif 'breakdown_sensor_failure' in event.event_type:
            # Sensor sends erratic data (handled in anomaly generation)
            pass
            
        elif 'accident' in event.event_type:
            # Sudden changes and trip termination
            for pos in wheel_pressures:
                wheel_pressures[pos] += random.uniform(-10, 10)  # Erratic pressure changes
            for pos in wheel_temps:
                wheel_temps[pos] += random.uniform(-5, 15)  # Temperature spikes
            current_speed = 0
            continue_trip = False  # Stop data generation
        
        return current_speed, wheel_pressures, wheel_temps, continue_trip
    
    def _apply_data_anomalies(self, records: List[Dict]) -> List[Dict]:
        """Apply data anomalies to records"""
        if not self.enable_data_anomalies or len(records) == 0:
            return records
        
        num_anomalies = int(len(records) * self.anomaly_rate)
        
        if self.anomaly_mode == 'single':
            # Apply only one type of anomaly
            anomaly_type = self.selected_anomaly
            
            if anomaly_type == 'missing_sensor':
                # Remove random sensor completely
                sensor_ids = list(set([r['sensor_id'] for r in records]))
                if sensor_ids:
                    sensor_to_remove = random.choice(sensor_ids)
                    records = self.anomaly_gen.missing_sensor(records, sensor_to_remove)
                    
            elif anomaly_type == 'missing_all':
                # Remove all sensors at random timestamps
                timestamps = list(set([r['read_at'] for r in records]))
                for _ in range(min(num_anomalies, len(timestamps) // 10)):
                    if timestamps:
                        ts_to_remove = random.choice(timestamps)
                        records = self.anomaly_gen.missing_all_sensors(records, ts_to_remove)
                        
            elif anomaly_type == 'random_missing':
                records = self.anomaly_gen.random_missing(records, self.anomaly_rate)
                
            else:
                # Apply value-based anomalies
                for _ in range(num_anomalies):
                    if records:
                        idx = random.randint(0, len(records) - 1)
                        if anomaly_type == 'out_of_range':
                            records[idx] = self.anomaly_gen.out_of_range(records[idx])
                        elif anomaly_type == 'null_value':
                            records[idx] = self.anomaly_gen.null_value(records[idx])
                        elif anomaly_type == 'duplicate':
                            records = self.anomaly_gen.duplicate_record(records, idx)
                        elif anomaly_type == 'timestamp_reversal' and idx > 0:
                            records[idx] = self.anomaly_gen.timestamp_reversal(
                                records[idx], records[idx-1]['read_at'])
                        elif anomaly_type == 'future_timestamp':
                            records[idx] = self.anomaly_gen.future_timestamp(records[idx])
                        elif anomaly_type == 'ingested_before_read':
                            records[idx] = self.anomaly_gen.ingested_before_read(records[idx])
                        elif anomaly_type == 'invalid_vin':
                            records[idx] = self.anomaly_gen.invalid_vin(records[idx])
                        elif anomaly_type == 'invalid_sensor_id':
                            records[idx] = self.anomaly_gen.invalid_sensor_id(records[idx])
                        elif anomaly_type == 'corrupted_data':
                            records[idx] = self.anomaly_gen.corrupted_data(records[idx])
        else:
            # Mixed mode - apply various anomalies randomly
            anomaly_types = [
                'missing_sensor', 'random_missing', 'out_of_range', 'null_value',
                'duplicate', 'timestamp_reversal', 'future_timestamp',
                'ingested_before_read', 'invalid_vin', 'invalid_sensor_id', 'corrupted_data'
            ]
            
            for _ in range(num_anomalies):
                if records:
                    anomaly_type = random.choice(anomaly_types)
                    idx = random.randint(0, len(records) - 1)
                    
                    if anomaly_type == 'missing_sensor':
                        sensor_ids = list(set([r['sensor_id'] for r in records]))
                        if sensor_ids:
                            sensor_to_remove = random.choice(sensor_ids)
                            # Remove only a few instances
                            for i in range(min(5, len(records))):
                                random_idx = random.randint(0, len(records) - 1)
                                if records[random_idx]['sensor_id'] == sensor_to_remove:
                                    records[random_idx]['trigger'] = '1'
                                    records.pop(random_idx)
                                    
                    elif anomaly_type == 'random_missing':
                        if random.random() < 0.5:
                            records[idx]['trigger'] = '1'
                            records.pop(idx)
                            
                    elif anomaly_type == 'out_of_range':
                        records[idx] = self.anomaly_gen.out_of_range(records[idx])
                        
                    elif anomaly_type == 'null_value':
                        records[idx] = self.anomaly_gen.null_value(records[idx])
                        
                    elif anomaly_type == 'duplicate':
                        records = self.anomaly_gen.duplicate_record(records, idx)
                        
                    elif anomaly_type == 'timestamp_reversal' and idx > 0:
                        records[idx] = self.anomaly_gen.timestamp_reversal(
                            records[idx], records[idx-1]['read_at'])
                            
                    elif anomaly_type == 'future_timestamp':
                        records[idx] = self.anomaly_gen.future_timestamp(records[idx])
                        
                    elif anomaly_type == 'ingested_before_read':
                        records[idx] = self.anomaly_gen.ingested_before_read(records[idx])
                        
                    elif anomaly_type == 'invalid_vin':
                        records[idx] = self.anomaly_gen.invalid_vin(records[idx])
                        
                    elif anomaly_type == 'invalid_sensor_id':
                        records[idx] = self.anomaly_gen.invalid_sensor_id(records[idx])
                        
                    elif anomaly_type == 'corrupted_data':
                        records[idx] = self.anomaly_gen.corrupted_data(records[idx])
        
        return records
    
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
        
        # Generate traffic events
        traffic_events = self._generate_traffic_events(self.trip_duration_hours, start_time)
        
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
        current_speed = self.avg_speed_mph
        continue_trip = True
        
        for i in range(num_points):
            if not continue_trip:
                break  # Stop generating data after accident
                
            read_at = current_time
            ingested_at = current_time + timedelta(minutes=2)
            
            # Check for active traffic events
            active_events = [e for e in traffic_events if e.start_time <= read_at < e.end_time]
            for event in active_events:
                current_speed, wheel_pressures, wheel_temps, continue_trip = \
                    self._apply_traffic_event(event, current_speed, wheel_pressures, wheel_temps)
                if not continue_trip:
                    print(f"Vehicle {vin}: Trip ended due to accident at {read_at}")
                    break
            
            # Current position
            current_lat = lat_points[i]
            current_lon = lon_points[i]
            
            # Progress through trip (0 to 1)
            progress = i / max(num_points - 1, 1)
            
            # Generate tire pressure and temperature records
            for pos in wheel_positions:
                trigger_value = ''  # Default: no anomaly
                
                # Check if there's a breakdown affecting this sensor
                sensor_failure = any('sensor_failure' in e.event_type for e in active_events)
                
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
                    # Adjust based on current speed
                    if current_speed > 0:
                        # Simulate pressure changes (small variations)
                        pressure_variation = random.uniform(-0.5, 0.5)
                        wheel_pressures[pos] = max(
                            self.pressure_range[0], 
                            min(self.pressure_range[1], 
                                wheel_pressures[pos] + pressure_variation)
                        )
                        
                        # Simulate temperature increase during driving
                        # Temperature rises more at the beginning and stabilizes
                        speed_factor = current_speed / self.avg_speed_mph
                        temp_rise = 10 * speed_factor * (1 - np.exp(-3 * progress))
                        temp_variation = random.uniform(-1, 1)
                        wheel_temps[pos] = self.avg_temp_f + temp_rise + temp_variation
                        
                        # Add noise to rear wheels (they typically run slightly hotter)
                        # Check if it's a rear wheel (2nd or 3rd axle)
                        if pos[0] in ['2', '3']:  # 2nd and 3rd axle wheels
                            wheel_temps[pos] += random.uniform(0, 2)
                    else:
                        # Vehicle stopped (signal or breakdown)
                        wheel_temps[pos] -= random.uniform(0, 0.5)  # Slight cooling
                
                # Handle sensor failure
                if sensor_failure and random.random() < 0.3:
                    # 30% chance of erratic reading during sensor failure
                    wheel_pressures[pos] = random.uniform(0, 200)
                    wheel_temps[pos] = random.uniform(-50, 300)
                    trigger_value = '1'
                
                # Pressure record
                records.append({
                    'tenant': self.tenant,
                    'sensor_id': f'sensor{pos}_pressure',
                    'vin': vin,
                    'read_at': read_at,
                    'trigger': trigger_value,
                    'reading': round(wheel_pressures[pos], 1),
                    'ingested_at': ingested_at
                })
                
                # Temperature record
                records.append({
                    'tenant': self.tenant,
                    'sensor_id': f'sensor{pos}_temperature',
                    'vin': vin,
                    'read_at': read_at,
                    'trigger': trigger_value,
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
        
        # Apply data anomalies if enabled
        if self.enable_data_anomalies:
            records = self._apply_data_anomalies(records)
        
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
        print(f"Sensor ID format: sensor{'{position}'}_pressure/temperature")
        print(f"GPS output frequency: Every {self.update_interval_min * 2} minutes")
        
        if self.enable_traffic_events:
            print(f"Traffic events: ENABLED")
        if self.enable_data_anomalies:
            print(f"Data anomalies: ENABLED (rate: {self.anomaly_rate:.1%}, mode: {self.anomaly_mode})")
        
        all_records = []
        start_time = datetime.now().replace(microsecond=0, second=0)
        
        for idx, vin in enumerate(self.vins):
            print(f"Generating data for vehicle {idx + 1}/{self.num_vehicles} (VIN: {vin})")
            vehicle_records = self._generate_sensor_data(vin, start_time)
            all_records.extend(vehicle_records)
        
        # Create DataFrame
        df = pd.DataFrame(all_records)
        
        if len(df) == 0:
            print("Warning: No data generated. Check your settings.")
            return df
        
        # Convert datetime columns to proper format
        df['read_at'] = pd.to_datetime(df['read_at'])
        df['ingested_at'] = pd.to_datetime(df['ingested_at'])
        
        # Sort by ingested_at, then vin, then sensor_id
        df = df.sort_values(['ingested_at', 'vin', 'sensor_id'])
        
        return df
    
    def save_to_parquet(self, df: pd.DataFrame, filename: str = None):
        """Save DataFrame to Parquet file"""
        if len(df) == 0:
            print("Warning: DataFrame is empty. No file saved.")
            return None
            
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            mode_suffix = 'stationary' if self.stationary_mode else 'moving'
            if self.enable_traffic_events:
                mode_suffix += '_traffic'
            if self.enable_data_anomalies:
                mode_suffix += '_anomalies'
            filename = f'tpms_data_{mode_suffix}_{timestamp}.parquet'
        
        # Ensure data types match ClickHouse schema
        df['tenant'] = df['tenant'].astype(str)
        df['sensor_id'] = df['sensor_id'].astype(str)
        df['vin'] = df['vin'].astype(str)
        df['trigger'] = df['trigger'].astype(str)
        # Handle potential None/NaN values in reading
        df['reading'] = pd.to_numeric(df['reading'], errors='coerce')
        
        # Save to Parquet
        df.to_parquet(filename, engine='pyarrow', compression='snappy', index=False)
        print(f"Data saved to {filename}")
        print(f"Total records: {len(df)}")
        
        # Show statistics
        if 'sensor_id' in df.columns:
            gps_records = df[df['sensor_id'].isin(['latitude', 'longitude'])]
            pressure_records = df[df['sensor_id'].str.contains('pressure', na=False)]
            anomaly_records = df[df['trigger'] == '1']
            
            print(f"Pressure/Temperature records: {len(pressure_records)}")
            print(f"GPS records: {len(gps_records)}")
            if len(gps_records) > 0:
                print(f"Ratio: 1 GPS pair per {len(pressure_records) / (len(gps_records) / 2):.1f} pressure readings")
            print(f"Anomaly records: {len(anomaly_records)} ({len(anomaly_records)/len(df)*100:.1f}%)")
        
        return filename

def main():
    parser = argparse.ArgumentParser(description='TPMS Sensor Data Simulator v3.0')
    
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
    
    # Traffic event simulation
    parser.add_argument('--enable-traffic-events', action='store_true',
                       help='Enable traffic event simulation (congestion, signals, breakdowns, accidents)')
    
    # Data anomaly generation
    parser.add_argument('--enable-data-anomalies', action='store_true',
                       help='Enable data anomaly generation for testing')
    parser.add_argument('--anomaly-rate', type=float, default=0.05,
                       help='Rate of anomaly occurrence (0-1, default: 0.05)')
    parser.add_argument('--anomaly-mode', type=str, default='mixed',
                       choices=['mixed', 'single'],
                       help='Anomaly mode: mixed (various types) or single (one type only)')
    
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
        update_interval_min=args.interval,
        enable_traffic_events=args.enable_traffic_events,
        enable_data_anomalies=args.enable_data_anomalies,
        anomaly_rate=args.anomaly_rate,
        anomaly_mode=args.anomaly_mode
    )
    
    # Generate dataset
    df = simulator.generate_dataset()
    
    # Save to Parquet
    if len(df) > 0:
        simulator.save_to_parquet(df, args.output)
    else:
        print("No data generated. Check your settings.")

if __name__ == "__main__":
    main()