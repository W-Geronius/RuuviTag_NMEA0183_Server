# RuuviTag NMEA TCP Server

A TCP server that transmits RuuviTag sensor data as NMEA0183 sentences for use with marine navigation and monitoring systems.

## Overview

This server connects to your RuuviTag sensors via Bluetooth, collects their environmental data (temperature, humidity, pressure), calculates dewpoint and broadcasts them as NMEA sentences over a configurable TCP port. This allows you to integrate RuuviTag sensors with marine navigation software, home automation systems, or any application that can process NMEA-formatted data.

The server supports two output formats:
- Standard NMEA0183 XDR format
- ESP32NMEA2K format for integration with Open Boat Project's N2K Gateway / OBPxx Displays

## Features

- ⏱️ Individual polling frequencies for each sensor
- 🔄 Multiple output formats (NMEA0183 or ESP32NMEA2K)
- 🔍 Option to use distinct transducer IDs for different sensor types
- 📊 Calibration offsets for temperature, humidity, and pressure
- 💧 Calculated dewpoint from temperature and humidity
- 📝 Configurable logging levels and log file output

## Prerequisites

- Python 3.7+
- Bluetooth adapter compatible with the [ruuvitag-sensor](https://github.com/ttu/ruuvitag-sensor) library
- RuuviTag sensors within range

## Installation

### Standard Installation

1. Ensure you have the ruuvitag-sensor library installed:

```bash
pip install ruuvitag-sensor
```

2. Clone or download this repository:

```bash
git clone https://github.com/yourusername/ruuvitag-nmea-server.git
cd ruuvitag-nmea-server
```

3. Create a config.json file (see Configuration section)

### Raspberry Pi Installation

1. Update your Raspberry Pi:

```bash
sudo apt update
sudo apt full-upgrade
```

2. Install required packages:

```bash
sudo apt install python3-pip bluetooth bluez bluez-tools
```

3. Install the ruuvitag-sensor library:

```bash
pip3 install ruuvitag-sensor
```

4. Clone the repository:

```bash
git clone https://github.com/yourusername/ruuvitag-nmea-server.git
cd ruuvitag-nmea-server
```

5. Create a config.json file with your RuuviTag information (see Configuration section)

6. Test that your RuuviTags are discoverable:

```bash
sudo hcitool lescan
```

7. Set up auto-start (optional):

```bash
# Create a systemd service file
sudo nano /etc/systemd/system/ruuvitag-nmea.service

# Add the following content:
[Unit]
Description=RuuviTag NMEA TCP Server
After=bluetooth.service network.target

[Service]
User=pi
WorkingDirectory=/home/pi/ruuvitag-nmea-server
ExecStart=/usr/bin/python3 /home/pi/ruuvitag-nmea-server/ruuvitag_nmea_server.py --log-file /var/log/ruuvitag-nmea.log --log-level info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Save the file and enable the service:
sudo systemctl enable ruuvitag-nmea.service
sudo systemctl start ruuvitag-nmea.service
```

## Configuration

Create a config.json file in the same directory as the script with your RuuviTag information. Here's an example:

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
| `distinct_id` | Whether to append measurement type to sensor ID (e.g., "RU1C", "RU1H", "RU1P", "RU1D") | false |
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

### Basic Usage

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

## Improving Bluetooth Reception on Raspberry Pi

If you're having trouble with Bluetooth reception on your Raspberry Pi, try these steps:

1. **Positioning**:
   - Elevate your Raspberry Pi above obstacles
   - Move it away from metal objects and other electronics
   - Place it closer to your RuuviTag sensors

2. **Update Bluetooth Configuration**:
   ```bash
   sudo nano /etc/bluetooth/main.conf
   ```
   Add or modify these lines:
   ```
   # Increase power
   Class = 0x000100
   ControllerMode = dual
   [Policy]
   AutoEnable=true
   ```

3. **Reset Bluetooth**:
   ```bash
   sudo hciconfig hci0 reset
   sudo hciconfig hci0 up
   sudo systemctl restart bluetooth
   ```

4. **Use an External Adapter**:
   - Consider using a USB Bluetooth adapter with an external antenna for better range

## Troubleshooting

### Bluetooth Issues
- Check if RuuviTags are visible: `sudo hcitool lescan`
- Verify the MAC addresses in your config.json
- Reset the Bluetooth adapter: `sudo hciconfig hci0 reset`
- Check Bluetooth service status: `sudo systemctl status bluetooth`

### No Data Received
- Check that your RuuviTags are within range and have battery power
- Increase the polling frequency to check for intermittent connections
- Run with higher log level: `--log-level debug`

### Checking Logs
- For systemd service: `sudo journalctl -u ruuvitag-nmea.service`
- For log file: `tail -f /path/to/logfile.log`

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