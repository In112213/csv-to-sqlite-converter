# CSV to SQLite High-Performance Converter

A lightweight, robust Python tool designed to automate the process of converting, validating, and cleaning raw CSV data into a structured SQLite database. Built based on a real commercial task from Upwork.

## Features
* **Automated Data Validation:** Automatically normalizes table headers (lowercases, cleans invalid characters, fixes leading digits).
* **Robust Error Handling:** Custom exception layers for safe file import.
* **Modern Architecture:** Built using Python's modern ecosystem (`dataclasses`, `pathlib`, strict typing).
* **Production-Ready:** Includes full environment configuration templates.

## Tech Stack
* **Language:** Python 3.12
* **Database:** SQLite3
* **Libraries:** argparse, pathlib, dataclasses

## How to Use

1. Clone the repository:
```bash
   git clone [https://github.com/In112213/csv-to-sqlite-converter.git](https://github.com/In112213/csv-to-sqlite-converter.git)
