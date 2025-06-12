#!/usr/bin/env python3
# nmea_checksum.py

import sys
import argparse

def calculate_nmea_checksum(sentence):
    """Calculate the checksum for an NMEA sentence."""
    # NMEA checksums are calculated on the characters between, but not including,
    # the $ and the * in the sentence
    if sentence.startswith('$'):
        sentence = sentence[1:]
    
    # Remove any existing checksum part
    if '*' in sentence:
        sentence = sentence.split('*')[0]
    
    # Calculate the XOR of all characters
    checksum = 0
    for char in sentence:
        checksum ^= ord(char)
    
    # Format as a two-character hexadecimal value
    return f"{checksum:02X}"

def format_nmea_string(input_str):
    """Format a string according to NMEA0183 standard with checksum."""
    # Handle the $ character properly
    if input_str.startswith('$'):
        clean_str = input_str
    else:
        clean_str = '$' + input_str
    
    # Remove any existing checksum
    if '*' in clean_str:
        clean_str = clean_str.split('*')[0]
    
    # Calculate checksum (excluding the $ character)
    checksum = calculate_nmea_checksum(clean_str)
    
    # Return the formatted NMEA string with checksum
    return f"{clean_str}*{checksum}"

def main():
    parser = argparse.ArgumentParser(description='Calculate NMEA0183 checksum')
    parser.add_argument('nmea_string', type=str, help='NMEA string (with or without $ prefix)')
    parser.add_argument('--add-identifier', type=str, help='Add an NMEA identifier (e.g., GPXDR) if missing')
    
    args = parser.parse_args()
    
    # Get input string
    input_string = args.nmea_string
    
    # Check if we need to add an identifier
    if args.add_identifier:
        # If there's a $ prefix, check what comes after
        if input_string.startswith('$'):
            # If just $ with no identifier, add the identifier
            if len(input_string) == 1 or input_string[1] == ',':
                input_string = '$' + args.add_identifier + input_string[1:]
        else:
            # If no $ prefix, check if it starts with the identifier
            if not input_string.startswith(args.add_identifier):
                input_string = args.add_identifier + ',' + input_string
    
    # Format and output the NMEA string with checksum
    nmea_string = format_nmea_string(input_string)
    print(nmea_string)

if __name__ == "__main__":
    main()