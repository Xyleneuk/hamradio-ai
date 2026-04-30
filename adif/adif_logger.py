import os
from datetime import datetime, timezone

LOG_DIR  = os.path.join(os.path.expanduser('~'), '.hamradio_ai')
LOG_FILE = os.path.join(LOG_DIR, 'qso_log.adi')


def log_qso(qso_data, config):
    """Write a single QSO to the ADIF log file"""
    if not qso_data.get('callsign'):
        print("No callsign - skipping log entry")
        return

    os.makedirs(LOG_DIR, exist_ok=True)

    now      = datetime.now(timezone.utc)
    date_str = now.strftime('%Y%m%d')
    time_str = now.strftime('%H%M')

    def field(tag, value):
        value = str(value) if value else ''
        if value:
            return f"<{tag}:{len(value)}>{value}"
        return ''

    callsign   = qso_data.get('callsign', '')
    band       = qso_data.get('band', '')
    freq       = str(qso_data.get('frequency', ''))
    rst_sent   = qso_data.get('rst_sent', '59')
    rst_rcvd   = qso_data.get('rst_rcvd', '59')
    name       = qso_data.get('name', '')
    qth        = qso_data.get('qth', '')
    serial_s   = str(qso_data.get('serial_sent', ''))
    serial_r   = str(qso_data.get('serial_rcvd', ''))
    operator   = config.get('operator_name', '')
    station    = config.get('callsign', '')
    locator    = config.get('locator', '')

    record = (
        field('CALL',             callsign) +
        field('QSO_DATE',         date_str) +
        field('TIME_ON',          time_str) +
        field('BAND',             band)     +
        field('FREQ',             freq)     +
        field('MODE',             'SSB')    +
        field('RST_SENT',         rst_sent) +
        field('RST_RCVD',         rst_rcvd) +
        field('NAME',             name)     +
        field('QTH',              qth)      +
        field('OPERATOR',         operator) +
        field('STATION_CALLSIGN', station)  +
        field('MY_GRIDSQUARE',    locator)  +
        field('STX',              serial_s) +
        field('SRX',              serial_r) +
        '<EOR>\n'
    )

    # Write ADIF header if new file
    write_header = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, 'a') as f:
        if write_header:
            f.write(
                '<ADIF_VER:5>3.1.0'
                '<PROGRAMID:12>HamRadioAI'
                '<PROGRAMVERSION:3>1.0'
                '<EOH>\n'
            )
        f.write(record)

    print(f"QSO logged: {callsign} to {LOG_FILE}")


def load_all_qsos():
    """
    Read all QSOs from the ADIF log file.
    Returns a list of dicts, one per QSO.
    """
    if not os.path.exists(LOG_FILE):
        return []

    qsos = []

    with open(LOG_FILE, 'r') as f:
        content = f.read()

    # Split on <EOR> records
    import re
    records = content.upper().split('<EOR>')

    for record in records:
        if not record.strip():
            continue
        if '<EOH>' in record:
            continue

        qso = {}
        # Find all field tags
        matches = re.findall(r'<(\w+):(\d+)>([^<]*)', record)
        for tag, length, value in matches:
            qso[tag.upper()] = value[:int(length)].strip()

        if 'CALL' in qso:
            qsos.append({
                'callsign':  qso.get('CALL', ''),
                'date':      qso.get('QSO_DATE', ''),
                'time':      qso.get('TIME_ON', ''),
                'band':      qso.get('BAND', ''),
                'frequency': qso.get('FREQ', ''),
                'rst_sent':  qso.get('RST_SENT', '59'),
                'rst_rcvd':  qso.get('RST_RCVD', '59'),
                'name':      qso.get('NAME', ''),
                'qth':       qso.get('QTH', ''),
                'serial_sent': qso.get('STX', ''),
                'serial_rcvd': qso.get('SRX', ''),
            })

    return qsos


if __name__ == '__main__':
    # Test loading
    qsos = load_all_qsos()
    print(f"Found {len(qsos)} QSOs in log")
    for q in qsos:
        print(
            f"  {q['date']} {q['time']}Z  {q['callsign']:<12} "
            f"{q['band']:<6} RST {q['rst_sent']}/{q['rst_rcvd']}  "
            f"{q['name']}  {q['qth']}"
        )