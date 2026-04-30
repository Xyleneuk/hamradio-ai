import os
import csv
from datetime import datetime, timezone

LOG_DIR  = os.path.join(os.path.expanduser('~'), '.hamradio_ai')
LOG_FILE = os.path.join(LOG_DIR, 'repeater_log.csv')


def log_repeater_contact(callsign, request_type, request_text, config):
    """Log a repeater contact"""
    os.makedirs(LOG_DIR, exist_ok=True)

    now      = datetime.now(timezone.utc)
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H%MZ')

    write_header = not os.path.exists(LOG_FILE)

    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow([
                'DATE', 'TIME UTC', 'CALLSIGN',
                'REQUEST TYPE', 'REQUEST TEXT',
                'REPEATER', 'OPERATOR'
            ])
        writer.writerow([
            date_str,
            time_str,
            callsign.upper() if callsign else 'UNKNOWN',
            request_type,
            request_text[:100],
            config.get('repeater_callsign', config.get('callsign', '')),
            config.get('operator_name', '')
        ])

    print(f"Repeater contact logged: {callsign} - {request_type}")


def load_repeater_log():
    """Load all repeater contacts"""
    if not os.path.exists(LOG_FILE):
        return []
    contacts = []
    with open(LOG_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            contacts.append(row)
    return contacts