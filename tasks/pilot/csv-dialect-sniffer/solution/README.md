# Reference Solution for csv-dialect-sniffer

This directory contains the complete implementation of the CSV dialect sniffer and parser.

## Files

- `csv_sniffer.py` - Complete implementation with:
  - `sniff_delimiter(sample, candidates)` - Detects CSV delimiter from sample text
  - `parse_tabular_data(text, delimiter)` - Parses CSV text into list of dictionaries