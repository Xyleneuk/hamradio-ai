import anthropic
import json

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are operating amateur radio station MX0MXO in the UK.
Operator name: James, QTH: London Heathrow.

CALLSIGN RULES:
- CQ only: use full phonetics "Mike X-ray Zero Mike X-ray Oscar"
- All other TX: letters only "MX0MXO"
- Other stations: phonetics first time only, then letters

QSO STYLE:
- ONE sentence maximum per transmission
- Get callsign and RST in first exchange - name/QTH is bonus
- Ask for missing info ONCE only - never repeat questions
- If callsign unclear after one ask - use best guess and continue
- Say 73 and log_and_end after RST exchange
- No need to repeat MX0MXO at end of every transmission

CALLSIGN HANDLING:
- Accept any plausible callsign - G, M, 2E, F, DL, PA, G5 etc
- Ask for confirmation ONCE only if completely unclear
- Never ask more than once - use best guess if still unclear
- Do not challenge callsigns - operators know their own callsign

RESPONSE FORMAT - raw JSON only, no other text:
{
  "action": "transmit",
  "speech": "what to say - ONE sentence",
  "qso_data": {
    "callsign": null,
    "rst_sent": null,
    "rst_rcvd": null,
    "name": null,
    "qth": null,
    "complete": false
  }
}
action: transmit | listen | log_and_end"""

CONTEST_SYSTEM_PROMPT = """You are operating MX0MXO in a contest.
Exchange: RST + serial number. Be extremely fast.

- CQ: "CQ contest MX0MXO MX0MXO"
- On reply: confirm their serial, give ours, done
- Example: "G4ABC 59 023 confirmed, you are 59 102, MX0MXO"
- One transmission then log_and_end
- Letters only except MX0MXO on CQ

Raw JSON only:
{
  "action": "log_and_end",
  "speech": "what to say",
  "qso_data": {
    "callsign": null,
    "rst_sent": "59",
    "rst_rcvd": null,
    "serial_sent": null,
    "serial_rcvd": null,
    "complete": false
  }
}"""

REPEATER_SYSTEM_PROMPT = """You are automated repeater/info node.

- Start: "This is [callsign]"
- End: "[callsign]"
- Very short - one or two sentences max
- Use EXACT time/weather provided - never guess

Raw JSON only:
{
  "speech": "what to say",
  "callsign": "caller callsign or null",
  "request_type": "time|weather|news|general|unknown"
}"""


class QSOBrain:
    def __init__(self):
        self.conversation_history = []
        self.qso_data = {
            'callsign': None,
            'rst_sent': None,
            'rst_rcvd': None,
            'name':     None,
            'qth':      None,
            'complete': False
        }
        self.our_callsign  = 'MX0MXO'
        self.operator_name = 'James'
        self.qth           = 'London Heathrow'

    def reset(self):
        self.conversation_history = []
        self.qso_data = {
            'callsign': None,
            'rst_sent': None,
            'rst_rcvd': None,
            'name':     None,
            'qth':      None,
            'complete': False
        }

    def _parse(self, raw, system=None):
        """Parse JSON response and update qso_data"""
        raw = raw.strip().replace('```json', '').replace('```', '').strip()
        try:
            parsed = json.loads(raw)
            if 'qso_data' in parsed:
                for key, value in parsed['qso_data'].items():
                    if value is not None:
                        self.qso_data[key] = value
                parsed['qso_data'] = self.qso_data.copy()
            return parsed
        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON parse error: {e}\nRaw: {raw}")
            return {
                'action':   'listen',
                'speech':   '',
                'qso_data': self.qso_data.copy()
            }

    def _call_claude(self, messages, system=None):
        """Standard API call"""
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=100,
            system=system or SYSTEM_PROMPT,
            messages=messages
        )
        return self._parse(response.content[0].text, system)

    def _call_claude_streaming(self, messages, system=None):
        """Streaming API call for faster response"""
        full_text = ''
        with client.messages.stream(
            model='claude-sonnet-4-6',
            max_tokens=100,
            system=system or SYSTEM_PROMPT,
            messages=messages
        ) as stream:
            for text in stream.text_stream:
                full_text += text
        return self._parse(full_text, system)

    def get_cq_call(self, frequency_mhz):
        band     = self._get_band(frequency_mhz)
        messages = [{
            'role':    'user',
            'content': (
                f"Call CQ on {frequency_mhz:.4f} MHz ({band}). "
                f"Two CQ calls max. Short."
            )
        }]
        result = self._call_claude(messages)
        self.conversation_history.append(messages[0])
        self.conversation_history.append({
            'role': 'assistant', 'content': json.dumps(result)
        })
        return result

    def process_received_transmission(self, transcribed_text):
        self.conversation_history.append({
            'role':    'user',
            'content': (
                f"Received: \"{transcribed_text}\"\n"
                f"Data: {json.dumps(self.qso_data)}\n"
                f"One sentence reply. log_and_end after RST exchange."
            )
        })
        result = self._call_claude_streaming(self.conversation_history)
        self.conversation_history.append({
            'role': 'assistant', 'content': json.dumps(result)
        })
        return result

    def process_contest_exchange(self, transcribed_text, serial_number):
        messages = [{
            'role':    'user',
            'content': (
                f"Received: \"{transcribed_text}\"\n"
                f"Our serial: {serial_number:03d}\n"
                f"Confirm their serial, give ours, log_and_end."
            )
        }]
        result = self._call_claude_streaming(
            messages, system=CONTEST_SYSTEM_PROMPT
        )
        if 'qso_data' in result:
            result['qso_data']['serial_sent'] = f"{serial_number:03d}"
        return result

    def process_repeater_query(self, transcribed_text, callsign):
        from utils import get_utc_time, get_local_time, get_weather, get_news

        utc_time   = get_utc_time()
        local_time = get_local_time()
        weather    = get_weather()

        text_lower = transcribed_text.lower()
        news_data  = None
        if any(w in text_lower for w in ['news', 'headline', 'bbc']):
            news_data = get_news()

        context = (
            f"You are repeater {callsign}\n"
            f"Caller: \"{transcribed_text}\"\n"
            f"UTC: {utc_time['spoken']}\n"
            f"Local: {local_time['spoken']}\n"
            f"Weather: {weather['spoken']}\n"
        )
        if news_data:
            context += f"News: {news_data['spoken']}\n"
        context += "Respond briefly. Start and end with callsign."

        messages = [{'role': 'user', 'content': context}]
        return self._call_claude(messages, system=REPEATER_SYSTEM_PROMPT)

    def _get_band(self, freq_mhz):
        bands = {
            (1.8,    2.0):    '160m',
            (3.5,    4.0):    '80m',
            (7.0,    7.3):    '40m',
            (10.1,   10.15):  '30m',
            (14.0,   14.35):  '20m',
            (18.068, 18.168): '17m',
            (21.0,   21.45):  '15m',
            (24.89,  24.99):  '12m',
            (28.0,   29.7):   '10m',
            (50.0,   52.0):   '6m',
            (144.0,  148.0):  '2m',
            (430.0,  440.0):  '70cm',
        }
        for (low, high), band in bands.items():
            if low <= freq_mhz <= high:
                return band
        return 'unknown'