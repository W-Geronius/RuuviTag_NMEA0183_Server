#!/usr/bin/env python3
"""
RuuviTag NMEA0183/ESP32NMEA2K TCP Server

This script creates a TCP server to provide RuuviTag temperature sensor data and dewpoint as NMEA sentences.
 It reads configuration from a config.json file, including TCP port, sensor MACs, polling frequency,
sensor IDs, locations, calibration factors, and output format.

Features:
- Configurable TCP port
- Individual polling frequencies for each sensor
- Multiple output formats, set output_format in config.json
  - NMEA0183: Temperature in Kelvin, pressure in bar
  - ESP32NMEA2K: Temperature in Celsius, pressure in hPa
- Option to use distinct IDs for different measurement types, set distinct_id in config.json
- Calibration factors for temperature, humidity, and pressure

Usage:
    python ruuvitag_nmea_server.py [--config CONFIG_FILE] [--log-level {quiet,error,warning,info,debug}]
"""

import argparse
import asyncio
import json
import logging
import signal
import socket
import sys
import time
import math
import os
from datetime import datetime, timezone
from typing import Dict, List
from logging.handlers import RotatingFileHandler

from ruuvitag_sensor.ruuvi import RuuviTagSensor
from ruuvitag_sensor.ruuvi_types import SensorData
import ruuvitag_sensor.log

# Set up logging
ruuvitag_sensor.log.enable_console()
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ruuvitag_nmea_server")

# Default configuration file path
DEFAULT_CONFIG_FILE = "config.json"

class NMEAFormatter:
    """
    Formats sensor data as NMEA sentences with support for different output formats
    """
    
    @staticmethod
    def calculate_checksum(sentence: str) -> str:
        """Calculate the checksum for an NMEA sentence"""
        # The checksum is calculated as the XOR of all characters between $ and *
        checksum = 0
        for char in sentence:
            checksum ^= ord(char)
        return f"{checksum:02X}"
    
    @staticmethod
    def calculate_dewpoint(temp_c: float, humidity: float) -> float:
        """
        Calculate dewpoint temperature using Magnus-Tetens formula
        
        Args:
            temp_c: Temperature in Celsius
            humidity: Relative humidity as percentage (0-100)
            
        Returns:
            Dewpoint temperature in Celsius
        """
        # Constants for Magnus-Tetens approximation
        a = 17.27
        b = 237.7
        
        # Calculate alpha term in Magnus-Tetens formula
        # Ensure humidity is within valid range to prevent math domain errors
        humidity = max(0.1, min(100, humidity))
        alpha = ((a * temp_c) / (b + temp_c)) + math.log(humidity / 100.0)
        
        # Calculate dewpoint
        dewpoint = (b * alpha) / (a - alpha)
        
        return dewpoint
    
    @staticmethod
    def format_xdr(sensor_data: SensorData, sensor_id: str, 
                   calibration: Dict[str, float], distinct_id: bool = False,
                   output_format: str = "NMEA0183") -> List[str]:
        """
        Format sensor data as NMEA XDR sentences
        
        Args:
            sensor_data: Data from RuuviTag sensor
            sensor_id: Sensor identifier
            calibration: Calibration offsets
            distinct_id: Whether to append transducer type to sensor ID
            output_format: Output format, either "NMEA0183" or "ESP32NMEA2K"
            
        Returns:
            List of NMEA XDR sentences
        """
        sentences = []
        
        # Get calibrated temperature and humidity for dewpoint calculation
        temp_c = None
        humidity = None
        
        # Temperature (applying calibration)
        if "temperature" in sensor_data:
            raw_temp = sensor_data["temperature"]
            calibration_value = calibration.get("temperature", 0.0)
            
            # Apply calibration to temperature
            temp_c = raw_temp + calibration_value
            
            # Use distinct ID if requested
            temp_id = f"{sensor_id}C" if distinct_id else sensor_id
            
            # Format temperature according to output format
            if output_format == "ESP32NMEA2K":
                # ESP32NMEA2K: Use G for generic sensor type, temperature in Celsius with 1 decimal place
                temp_str = f"$GPXDR,G,{temp_c:.1f},C,{temp_id}"
            else:
                # NMEA0183: Temperature in Kelvin with 2 decimal places
                temp_k = temp_c + 273.15
                temp_str = f"$GPXDR,C,{temp_k:.2f},K,{temp_id}"
                
            checksum = NMEAFormatter.calculate_checksum(temp_str[1:])
            sentences.append(f"{temp_str}*{checksum}")
        
        # Humidity (applying calibration)
        if "humidity" in sensor_data:
            raw_humidity = sensor_data["humidity"]
            calibration_value = calibration.get("humidity", 0.0)
            
            # Apply calibration
            humidity = raw_humidity + calibration_value
            
            # Clamp humidity to 0-100%
            original_humidity = humidity
            humidity = max(0, min(100, humidity))
            
            # Use distinct ID if requested
            hum_id = f"{sensor_id}H" if distinct_id else sensor_id
            
            # Format humidity according to output format
            if output_format == "ESP32NMEA2K":
                # ESP32NMEA2K: Use G for generic sensor type, humidity with 1 decimal place
                hum_str = f"$GPXDR,G,{humidity:.1f},P,{hum_id}"
            else:
                # NMEA0183: Humidity with 1 decimal place
                hum_str = f"$GPXDR,H,{humidity:.1f},P,{hum_id}"
                
            checksum = NMEAFormatter.calculate_checksum(hum_str[1:])
            sentences.append(f"{hum_str}*{checksum}")
        
        # Calculate and format dewpoint if we have both temperature and humidity
        if temp_c is not None and humidity is not None:
            # Calculate dewpoint using calibrated values
            dewpoint_c = NMEAFormatter.calculate_dewpoint(temp_c, humidity)
            
            # Use distinct ID if requested
            dewpoint_id = f"{sensor_id}D" if distinct_id else sensor_id
            
            # Format dewpoint according to output format
            if output_format == "ESP32NMEA2K":
                # ESP32NMEA2K: Use G for generic sensor type, dewpoint in Celsius with 1 decimal place
                dewpoint_str = f"$GPXDR,G,{dewpoint_c:.1f},C,{dewpoint_id}"
            else:
                # NMEA0183: Dewpoint in Kelvin with 2 decimal places (same format as temperature)
                dewpoint_k = dewpoint_c + 273.15
                dewpoint_str = f"$GPXDR,C,{dewpoint_k:.2f},K,{dewpoint_id}"
                
            checksum = NMEAFormatter.calculate_checksum(dewpoint_str[1:])
            sentences.append(f"{dewpoint_str}*{checksum}")
        
        # Pressure (applying calibration)
        if "pressure" in sensor_data:
            raw_pressure = sensor_data["pressure"]
            calibration_value = calibration.get("pressure", 0.0)
            
            # Format pressure according to output format
            if output_format == "ESP32NMEA2K":
                # ESP32NMEA2K: Use G for generic sensor type, pressure in hPa as integer
                pressure_hpa = raw_pressure + calibration_value
                press_id = f"{sensor_id}P" if distinct_id else sensor_id
                press_str = f"$GPXDR,G,{int(pressure_hpa)},H,{press_id}"
            else:
                # NMEA0183: Pressure in bar with 5 decimal places
                pressure_bar = (raw_pressure / 1000.0) + calibration_value
                press_id = f"{sensor_id}P" if distinct_id else sensor_id
                press_str = f"$GPXDR,P,{pressure_bar:.5f},B,{press_id}"
            
            checksum = NMEAFormatter.calculate_checksum(press_str[1:])
            sentences.append(f"{press_str}*{checksum}")
        
        return sentences

class TCPServer:
    """
    TCP server that sends NMEA sentences to connected clients
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 2000):
        self.host = host
        self.port = port
        self.clients = []
        self.server = None
        self.running = True
    
    async def start(self):
        """Start the TCP server"""
        self.server = await asyncio.start_server(
            self.handle_client, self.host, self.port)
        
        addr = self.server.sockets[0].getsockname()
        logger.info(f'NMEA TCP server started on {addr}')
    
    async def handle_client(self, reader, writer):
        """Handle a client connection"""
        try:
            addr = writer.get_extra_info('peername')
            logger.info(f'New client connected: {addr}')
            
            self.clients.append(writer)
            
            # Keep connection open and wait for client to disconnect
            while self.running:
                try:
                    data = await asyncio.wait_for(reader.read(100), timeout=1.0)
                    if not data:
                        break
                except asyncio.TimeoutError:
                    # This is expected - we're just checking if client disconnected
                    continue
        except ConnectionResetError:
            pass
        except ConnectionError as e:
            logger.error(f"Connection error: {e}")
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            if writer in self.clients:
                self.clients.remove(writer)
            logger.info(f'Client disconnected: {addr}')
    
    async def send_to_all(self, data: str):
        """Send data to all connected clients"""
        if not self.clients:
            return
                    
        # Send to all clients and handle disconnections
        disconnected_clients = []
        for writer in self.clients:
            try:
                writer.write(f"{data}\r\n".encode())
                await writer.drain()
            except (ConnectionResetError, BrokenPipeError):
                disconnected_clients.append(writer)
        
        # Clean up disconnected clients
        for writer in disconnected_clients:
            if writer in self.clients:
                self.clients.remove(writer)
    
    async def stop(self):
        """Stop the server"""
        self.running = False
        
        # Close all client connections
        for writer in self.clients:
            writer.close()
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("TCP server stopped")

class RuuviTagNMEAServer:
    """
    Main server class that reads RuuviTag data and sends it as NMEA sentences
    """
    
    def __init__(self, config_file: str = DEFAULT_CONFIG_FILE):
        self.config_file = config_file
        self.config = None
        self.tcp_server = None
        self.running = True
        self.sensor_next_poll = {}  # Track when each sensor should be polled next
    
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
                            
            # Validate config
            if "tcp_port" not in self.config:
                self.config["tcp_port"] = 10110
                
            # Default polling frequency if not specified at the sensor level
            if "polling_frequency" not in self.config:
                self.config["polling_frequency"] = 10
                
            # Add output_format default if not present
            if "output_format" not in self.config:
                self.config["output_format"] = "NMEA0183"
            elif self.config["output_format"] not in ["NMEA0183", "ESP32NMEA2K"]:
                logger.error(f"Unknown output format '{self.config['output_format']}', using NMEA0183")
                self.config["output_format"] = "NMEA0183"
            
            # Add distinct_id default if not present
            if "distinct_id" not in self.config:
                self.config["distinct_id"] = False
            
            # Force distinct_id to True when output_format is ESP32NMEA2K
            if self.config["output_format"] == "ESP32NMEA2K":
                if not self.config["distinct_id"]:
                    logger.warning("Setting distinct_id to True for ESP32NMEA2K output format")
                    self.config["distinct_id"] = True
                
            if "sensors" not in self.config or not self.config["sensors"]:
                raise ValueError("No sensors defined in config file")
            
                
            # Validate each sensor has required fields
            for i, sensor in enumerate(self.config["sensors"]):
                
                if "mac" not in sensor:
                    raise ValueError(f"Sensor {i+1} missing MAC address")
                
                # Normalize MAC address format (uppercase with colons)
                sensor["mac"] = sensor["mac"].upper()
                
                if "id" not in sensor:
                    sensor["id"] = sensor["mac"].replace(":", "")
                    
                if "calibration" not in sensor:
                    sensor["calibration"] = {}
                
                # Set sensor-specific polling frequency or use global default
                if "polling_frequency" not in sensor:
                    sensor["polling_frequency"] = self.config["polling_frequency"]
                
                # Initialize next poll time for each sensor
                self.sensor_next_poll[sensor["mac"]] = 0  # Poll immediately on startup
            
            logger.info(f"Loaded configuration: {len(self.config['sensors'])} sensors, output format: {self.config['output_format']}")
            return True
            
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error loading config: {e}")
            return False
        
    async def poll_sensors(self):
        """Poll RuuviTag sensors and send data as NMEA sentences"""
        
        while self.running:
            try:
                # Get current time
                current_time = time.time()
                
                # Determine which sensors need to be polled now
                sensors_to_poll = []
                min_wait_time = float('inf')
                
                for sensor in self.config["sensors"]:
                    mac = sensor["mac"]
                    next_poll_time = self.sensor_next_poll.get(mac, 0)
                    
                    
                    if current_time >= next_poll_time:
                        sensors_to_poll.append(sensor)
                    else:
                        # Update min_wait_time for the next closest poll
                        wait_time = next_poll_time - current_time
                        min_wait_time = min(min_wait_time, wait_time)
                
                # If no sensors need polling, sleep until next poll time
                if not sensors_to_poll:
                    # Use a reasonable sleep time, with a maximum cap
                    sleep_time = min(min_wait_time, 1.0) 
                    await asyncio.sleep(sleep_time)
                    continue
                
                # Get MACs of sensors that need polling
                macs_to_poll = [sensor["mac"] for sensor in sensors_to_poll]
                
                # Get data for these sensors
                if macs_to_poll:
                    # Use a reasonable search duration
                    search_duration = 2.0                    
                    data = await RuuviTagSensor.get_data_for_sensors_async(
                        macs=macs_to_poll, 
                        search_duration_sec=search_duration
                    )
                                        
                    # Process each sensor's data
                    for sensor in sensors_to_poll:
                        mac = sensor["mac"]
                        # Update next poll time regardless of whether data was received
                        self.sensor_next_poll[mac] = current_time + sensor["polling_frequency"]
                        
                        if data and mac in data:
                            # Debug sensor data
                            self.debug_sensor_data(sensor["id"], mac, data[mac])
                            
                            # Generate NMEA sentences for this sensor
                            nmea_sentences = NMEAFormatter.format_xdr(
                                data[mac], 
                                sensor["id"],
                                sensor.get("calibration", {}),
                                self.config["distinct_id"],
                                self.config["output_format"]
                            )
                            
                            # Send each sentence to clients
                            for sentence in nmea_sentences:
                                await self.tcp_server.send_to_all(sentence)
                            
                            # Log data
                            logger.info(f"Sensor {sensor['id']} ({mac}): "
                                       f"Temp: {data[mac].get('temperature')}°C, "
                                       f"Humidity: {data[mac].get('humidity')}%, "
                                       f"Pressure: {data[mac].get('pressure')} hPa")
                        else:
                            logger.error(f"No data received for sensor {sensor['id']} ({mac})")
                else:
                    logger.warning("No sensors due for polling")
            
            except Exception as e:
                logger.error(f"Error polling sensors: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            # Sleep for a short time to avoid tight loop
            await asyncio.sleep(0.1)
    
    def debug_sensor_data(self, sensor_id, mac, data):
        """Print detailed debug information about all sensor measurements"""
        logger.debug(f"=== Detailed Sensor Data: {sensor_id} ({mac}) ===")
        logger.debug(f"Data keys: {list(data.keys())}")
        
        # Check for each measurement type
        measurements = {
            "temperature": {"unit": "°C", "alt_keys": ["temp"]},
            "humidity": {"unit": "%", "alt_keys": ["humid", "hum"]},
            "pressure": {"unit": "hPa", "alt_keys": ["pres", "air_pressure"]}
        }
        
        for measure, info in measurements.items():
            if measure in data:
                logger.debug(f"{measure.capitalize()}: {data[measure]} {info['unit']}")
            else:
                # Check for alternative keys
                found = False
                for alt_key in info['alt_keys']:
                    if alt_key in data:
                        logger.debug(f"{measure.capitalize()} (as {alt_key}): {data[alt_key]} {info['unit']}")
                        found = True
                        break
                
                if not found:
                    logger.debug(f"{measure.capitalize()}: Not found in sensor data")
    
    async def run(self):
        """Run the server"""
        # Load configuration
        if not self.load_config():
            logger.error("Failed to load configuration, aborting")
            return
        
        # Set up TCP server
        self.tcp_server = TCPServer(port=self.config["tcp_port"])
        await self.tcp_server.start()
        
        # Start polling sensors with graceful shutdown support
        try:
            await self.poll_sensors()
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        if not self.running:
            return
            
        logger.info("Shutting down...")
        self.running = False
        
        if self.tcp_server:
            await self.tcp_server.stop()
        
        logger.info("Server shutdown complete")

class LoggerWriter:
    """Helper class to redirect stdout/stderr to logger"""
    def __init__(self, level):
        self.level = level
        self.logger = logging.getLogger("stdout_stderr")
        
    def write(self, message):
        if message and not message.isspace():
            self.logger.log(self.level, message)
            
    def flush(self):
        pass

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="RuuviTag NMEA TCP Server")
    parser.add_argument("--config", default=DEFAULT_CONFIG_FILE,
                        help=f"Configuration file path (default: {DEFAULT_CONFIG_FILE})")
    parser.add_argument("--log-level", choices=["quiet", "error", "warning", "info", "debug"], 
                        default="info", help="Set logging level - debug shows library details (default: info)")
    parser.add_argument("--log-file", help="Log file path (if not specified, logs to console only)")
    args = parser.parse_args()
    
    # Map string log levels to logging module levels
    log_level_map = {
        "quiet": logging.CRITICAL + 1,
        "error": logging.ERROR,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG
    }
    
    # Get the log level from arguments
    log_level = log_level_map[args.log_level]
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if log file is specified
    if args.log_file:
        try:
            # Create log directory if it doesn't exist
            log_dir = os.path.dirname(args.log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            # Set up rotating file handler (10MB max, keep 3 backups)
            file_handler = RotatingFileHandler(
                args.log_file, maxBytes=10*1024*1024, backupCount=3)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
            # Configure ruuvitag_sensor logging - need to set level for all loggers
            ruuvitag_sensor.log.enable_console(level=log_level)

            # Explicitly set level for all ruuvitag loggers
            logging.getLogger("ruuvitag_sensor").setLevel(log_level)
            logging.getLogger("ruuvitag_sensor.ruuvi").setLevel(log_level)
            logging.getLogger("ruuvitag_sensor.log").setLevel(log_level)

            # Also check for and remove any file handlers the library might have added
            for logger_name in ["ruuvitag_sensor", "ruuvitag_sensor.ruuvi", "ruuvitag_sensor.log"]:
                lib_logger = logging.getLogger(logger_name)
                for handler in lib_logger.handlers[:]:
                    if isinstance(handler, logging.FileHandler):
                        lib_logger.removeHandler(handler)

            # Redirect stdout and stderr to the log file as well
            # This ensures all print statements and error messages go to the log
            sys.stdout = LoggerWriter(logging.INFO)
            sys.stderr = LoggerWriter(logging.ERROR)
            
            logger.info(f"Logging to file: {args.log_file}")
        except Exception as e:
            logger.error(f"Failed to set up file logging: {e}")
    
    # Configure ruuvitag_sensor logging
    ruuvitag_sensor.log.enable_console(level=log_level)

    # Create server instance
    server = RuuviTagNMEAServer(args.config)
    
    # Set Windows-specific event loop policy if needed
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Use a separate function to run the server with proper interrupt handling
    def run_with_interrupt_handling():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Create a task for the server
        server_task = loop.create_task(server.run())
        
        try:
            # Run until the server task is complete or interrupted
            loop.run_until_complete(server_task)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            # Mark the server as not running
            server.running = False
            
            # Cancel the server task
            server_task.cancel()
            
            try:
                # Run the loop a bit more to allow cleanup tasks to complete
                loop.run_until_complete(asyncio.sleep(1))
            except asyncio.CancelledError:
                pass
        finally:
            # Clean up the loop
            loop.close()
    
    try:
        run_with_interrupt_handling()
        return 0
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
