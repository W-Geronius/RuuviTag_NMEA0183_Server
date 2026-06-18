# RuuviTag NMEA TCP Server

A TCP server to transmit RuuviTag sensor data as NMEA0183 sentences for use with marine navigation and monitoring systems.

This script has been developed and tested for Raspberry Pi OS (bookworm). Specific code requiring sudo is included to handle BT bugs known for this environment.
However, it should run on other linux systems with little or no modifications


## Overview

This server connects to your RuuviTag sensors via Bluetooth, collects their environmental data (temperature, humidity, pressure), calculates dewpoint and broadcasts them as NMEA sentences over a configurable TCP port. This allows you to integrate RuuviTag sensors with marine navigation software, home automation systems or any application that can process NMEA-formatted data.

The server supports two output formats:
- Standard NMEA0183 XDR format
- ESP32NMEA2K format for integration with Open Boat Project's N2K Gateway / OBPxx Multifunction Displays

## Features

- Individual polling frequencies for each sensor
- Multiple output formats (NMEA0183 or ESP32NMEA2K)
- Option to use distinct transducer IDs for different sensor types
- Calibration offsets for temperature, humidity, and pressure
- Dewpoint calculated from temperature and humidity

## Prerequisites

- Python 3.7+
- Bluetooth adapter compatible with the [ruuvitag-sensor](https://github.com/ttu/ruuvitag-sensor) library
- RuuviTag sensors within range

## Installation

### Standard Installation

1. Setup Virtual environment and ensure you have the ruuvitag-sensor library installed:

```bash
python3 -m venv env
source env/bin/activate
pip install ruuvitag-sensor
```

2. download the python script and sample config file:

```bash
wget https://raw.githubusercontent.com/W-Geronius/RuuviTag_NMEA0183_Server/master/ruuvitag_nmea_server.py
wget https://raw.githubusercontent.com/W-Geronius/RuuviTag_NMEA0183_Server/master/config.json
```

3. Create or modify config.json file in the same directory as the script with your RuuviTag information. Here's an example:

```json
{
    "tcp_port": 2000,
    "distinct_id": true,
    "output_format": "NMEA0183",
    "sensors": [
        {
            "mac": "AA:BB:CC:DD:EE:FF",
            "id": "R1.",
            "location": "Inside",
            "polling_frequency": 5,
            "calibration": {
                "temperature": 0.5,
                "humidity": -20.0,
                "pressure": 0.0
            }
        },
        {
            "mac": "11:22:33:44:55:66",
            "id": "R2.",
            "location": "Outside",
            "polling_frequency": 30,
            "calibration": {
                "temperature": 0.0,
                "humidity": 0.0,
                "pressure": 0.0
            }
        }
    ]
}
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `tcp_port` | TCP port for the NMEA server | 2000 |
| `distinct_id` | Whether to append measurement type to sensor ID e.g., "R1.C", "R1.H", ... | false |
| `output_format` | Output format, either "NMEA0183" or "ESP32NMEA2K" | "NMEA0183" |
| `sensors` | Array of sensor configurations | *required* |

#### Sensor Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `mac` | Bluetooth MAC address of the RuuviTag | *required* |
| `id` | ID to use in NMEA sentences | MAC with colons removed |
| `location` | Descriptive location (for your reference only) | none |
| `polling_frequency` | How often to poll this sensor (in seconds) | 10 |
| `calibration` | Calibration offsets for sensor values | `{}` |

## Usage

Run the server with:

```bash
python ruuvitag_nmea_server.py
```

### Command-line Options

```bash
# With a custom config file
python ruuvitag_nmea_server.py --config my_config.json

# Set logging level (quiet, error, warning, info, debug)
python ruuvitag_nmea_server.py --log-level warning

# Log to a file
python ruuvitag_nmea_server.py --log-file /path/to/logfile.log

# Combine options
python ruuvitag_nmea_server.py --config my_config.json --log-level error --log-file /path/to/logfile.log
```

## Output Formats

### NMEA0183

In NMEA0183 format, the server outputs:
- Temperature in Kelvin
- Humidity as percentage
- Dewpoint in Kelvin
- Pressure in bar

Example output:
```
$GPXDR,C,295.35,K,RU1*42
$GPXDR,H,35.5,P,RU1*5B
$GPXDR,C,287.22,K,RU1*73  # Dewpoint
$GPXDR,P,1.01325,B,RU1*60
```

### ESP32NMEA2K

In ESP32NMEA2K format, the server outputs:
- Temperature in Celsius with 1 decimal place
- Humidity as percentage with 1 decimal place
- Dewpoint in Celsius with 1 decimal place
- Pressure in hPa as integer

This format uses the generic sensor type "G" and requires distinct transducer IDs:
```
$GPXDR,G,22.2,C,RU1C*1A
$GPXDR,G,35.5,P,RU1H*1D
$GPXDR,G,14.1,C,RU1D*54  # Dewpoint
$GPXDR,G,1013,H,RU1P*45
```

## Client Applications

You can connect to this server with:
- AvNav
- Multifunction displays OBP60 and derivates
- NMEA2000 gateway with M5Stack Atom
- Any NMEA-compatible navigation software that supports TCP connections and processes XDR records
- Home automation systems with NMEA parsers

## Based On

This project uses the [ruuvitag-sensor](https://github.com/ttu/ruuvitag-sensor) library to communicate with RuuviTag devices.

## License

MIT License
