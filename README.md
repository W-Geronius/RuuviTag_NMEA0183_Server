# RuuviTag NMEA TCP Server

A TCP server that transmits RuuviTag sensor data as NMEA0183 sentences for use with marine navigation and monitoring systems.

## Overview

This server connects to your RuuviTag sensors via Bluetooth, collects their environmental data (temperature, humidity, pressure), and broadcasts them as NMEA sentences over a configurable TCP port. This allows you to integrate RuuviTag sensors with marine navigation software, home automation systems, or any application that can process NMEA-formatted data.

The server supports two output formats:
- Standard NMEA0183 XDR format
- ESP32NMEA2K format for integration with Open Boat Project's N2K Gateway / OBPxx Displays

## Features

- ⏱️ Individual polling frequencies for each sensor
- 🔄 Multiple output formats (NMEA0183 or ESP32NMEA2K)
- 🔍 Option to use distinct transducer IDs for different sensor types
- 📊 Calibration offsets for temperature, humidity, and pressure

## Prerequisites

- Python 3.7+
- Bluetooth adapter compatible with the [ruuvitag-sensor](https://github.com/ttu/ruuvitag-sensor) library
- RuuviTag sensors within range

## Installation

1. Ensure you have the ruuvitag-sensor library installed:

```bash
pip install ruuvitag-sensor
```

2. Clone or download this repository:

```bash
git clone https://github.com/yourusername/ruuvitag-nmea-server.git
cd ruuvitag-nmea-server
```

3. Create a `config.json` file (see Configuration section)

## Configuration

Create a `config.json` file in the same directory as the script with your RuuviTag information. Here's an example:

```json
{
    "tcp_port": 2000,
    "distinct_id": true,
    "output_format": "NMEA0183",
    "sensors": [
        {
            "mac": "AA:BB:CC:DD:EE:FF",
            "id": "RU1",
            "location": "Inside",
            "polling_frequency": 5,
            "calibration": {
                "temperature": 0.5,
                "humidity": -2.0,
                "pressure": 0.0
            }
        },
        {
            "mac": "11:22:33:44:55:66",
            "id": "RU2",
            "location": "Outside",
            "polling_frequency": 30,
            "calibration": {
                "temperature": -0.5,
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
| `distinct_id` | Whether to append measurement type to sensor ID (e.g., "RU1T", "RU1H", "RU1P") | false |
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

With a custom config file:

```bash
python ruuvitag_nmea_server.py --config my_config.json
```

With debug logging:

```bash
python ruuvitag_nmea_server.py --debug
```

## Output Formats

### NMEA0183

In NMEA0183 format, the server outputs:
- Temperature in Kelvin
- Humidity as percentage
- Pressure in bar

Example output:
```
$GPXDR,C,295.35,K,RU1*42
$GPXDR,H,35.5,P,RU1*5B
$GPXDR,P,1.01325,B,RU1*60
```

### ESP32NMEA2K

In ESP32NMEA2K format, the server outputs:
- Temperature in Celsius with 1 decimal place
- Humidity as integer percentage
- Pressure in hPa as integer

This format uses the generic sensor type "G" and requires distinct transducer IDs:
```
$GPXDR,G,22.2,C,RU1C*1A
$GPXDR,G,35,P,RU1H*1D
$GPXDR,G,1013,H,RU1P*45
```

## Client Applications

You can connect to this server with:
- AvNav
- Multifunction displays OBP60 and derivates
- NMEA2000 gateway with M5Stack Atom
- OpenCPN
- SignalK
- iNavX
- Any NMEA-compatible navigation software that supports TCP connections
- Home automation systems with NMEA parsers

## Troubleshooting

### Bluetooth Issues
- Ensure Bluetooth is enabled
- Run with `--debug` flag to see detailed Bluetooth scanning information
- Verify the MAC addresses in your config.json

### No Data Received
- Check that your RuuviTags are within range and have battery power
- Increase the polling frequency to check for intermittent connections
- Verify your client application is correctly connecting to the TCP port

## Based On

This project uses the [ruuvitag-sensor](https://github.com/ttu/ruuvitag-sensor) library to communicate with RuuviTag devices.

## License

MIT License
