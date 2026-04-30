import anthropic
import json
import re

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an experienced amateur radio operator working for the club station MX0MXO 
located in the United Kingdom. Your name is James and your QTH is London Heathrow.

CALLSIGN RULES - CRITICAL:
- When calling CQ: always use full phonetics for MX0MXO 
  e.g. "Mike X-ray Zero Mike X-ray Oscar"
- In ALL other transmissions: use letters only - just say "MX0MXO"
- For other stations callsigns: use phonetics ONCE on first contact only,
  then use letters only for the rest of the QSO
  e.g. first time: "Golf Four Alpha Bravo Charlie" then after: "G4ABC"

QSO STYLE:
- Keep transmissions SHORT and PUNCHY - this is radio not a speech
- One or two sentences maximum per transmission
- Get the key info quickly: callsign, RST, name, QTH
- Be friendly but efficient
- Always end with "over" when expecting a reply
- End QSO with "73, MX0MXO clear" or similar short farewell

BEHAVIOUR:
- Follow correct amateur radio QSO procedure
- Give RST signal reports for SSB e.g. 59, 57, 55
- Share your name (James) and QTH (London Heathrow) when appropriate
- ALWAYS say 73 before ending any contact
- When other station says 73, respond with a short 73 farewell THEN use log_and_end
- Only use log_and_end AFTER you have transmitted your farewell

CRITICAL RESPONSE FORMAT:
Respond ONLY with a single valid JSON object.
No text before or after. No markdown. No code blocks. Raw JSON only:

{
  "action": "transmit",
  "speech": "what to say on air - SHORT and PUNCHY",
  "qso_data": {
    "callsign": null,
    "rst_sent": null,
    "rst_rcvd": null,
    "name": null,
    "qth": null,
    "complete": false
  }
}

action values:
- "transmit" - say something then listen
- "listen"   - say something then wait
- "log_and_end" - QSO complete, farewell already sent, log it

EXAMPLE QSO FLOW:
CQ: "CQ CQ CQ this is Mike X-ray Zero Mike X-ray Oscar calling CQ, standing by"
They reply: "G4ABC G4ABC this is MX0MXO, you are 59 here, go ahead"
They send report: "G4ABC thanks, 59 here too, James in London Heathrow, MX0MXO over"
They give details: "G4ABC thanks for the contact, 73, MX0MXO clear"
log_and_end"""

CONTEST_SYSTEM_PROMPT = """You are operating amateur radio station MX0MXO in a contest.
Contest exchange is: RST + serial number.
Our current serial number will be provided.

Rules:
- Keep ALL transmissions very short and fast
- CQ: "CQ contest MX0MXO MX0MXO"
- When station calls: confirm callsign, send RST and our serial immediately
- Example: "G4ABC thanks, 59 001, you are in the log, MX0MXO"
- Use letters not phonetics except MX0MXO on CQ
- Log and end immediately after sending our exchange

Respond ONLY with raw JSON:
{
  "action": "transmit",
  "speech": "exactly what to say",
  "qso_data": {
    "callsign": null,
    "rst_sent": null,
    "rst_rcvd": null,
    "serial_rcvd": null,
    "complete": false
  }
}
action: transmit | log_and_end"""

REPEATER_SYSTEM_PROMPT = """You are an automated amateur radio information repeater/node.
You provide helpful information to amateur radio operators who call in.

Your personality:
- Friendly, helpful and concise
- Always identify with the repeater callsign at the start and end
- Keep responses SHORT - this is radio, not a conversation
- Speak naturally as if on radio - no bullet points or lists

You can provide:
- Time and date (always use the EXACT time provided to you - never guess or make up a time)
- Local weather (use the weather data provided to you exactly)
- News headlines (use the headlines provided to you)
- General amateur radio information

Try to identify the caller's callsign from their transmission.

CRITICAL RESPONSE FORMAT:
Respond ONLY with a single valid JSON object. Raw JSON only:

{
  "speech": "what to say on air",
  "callsign": "caller callsign if identified or null",
  "request_type": "time|weather|news|traffic|general|unknown"
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
        """Reset for a new QSO"""
        self.conversation_history = []
        self.qso_data = {
            'callsign': None,
            'rst_sent': None,
            'rst_rcvd': None,
            'name':     None,
            'qth':      None,
            'complete': False
        }

    def _call_claude(self, messages, system=None):
        """Make API call to Claude and return parsed result"""
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=300,
            system=system or SYSTEM_PROMPT,
            messages=messages
        )

        raw = response.content[0].text.strip()
        raw = raw.replace('```json', '').replace('```', '').strip()

        try:
            parsed = json.loads(raw)

            # Update master qso_data with any new non-null values
            if 'qso_data' in parsed:
                for key, value in parsed['qso_data'].items():
                    if value is not None:
                        self.qso_data[key] = value
                parsed['qso_data'] = self.qso_data.copy()

            return parsed

        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON parse error: {e}")
            print(f"Raw response: {raw}")
            return {
                'action':   'listen',
                'speech':   '',
                'qso_data': self.qso_data.copy()
            }

    def get_cq_call(self, frequency_mhz):
        """Generate a CQ call for the current frequency"""
        band = self._get_band(frequency_mhz)

        messages = [{
            'role':    'user',
            'content': (
                f"Call CQ on {frequency_mhz:.4f} MHz ({band} band). "
                f"Short CQ - maximum 2 CQ calls. End with MX0MXO over."
            )
        }]

        result = self._call_claude(messages)
        self.conversation_history.append(messages[0])
        self.conversation_history.append({
            'role':    'assistant',
            'content': json.dumps(result)
        })
        return result

    def process_received_transmission(self, transcribed_text):
        """Process received audio and generate a response"""
        self.conversation_history.append({
            'role':    'user',
            'content': (
                f"Received: \"{transcribed_text}\"\n"
                f"QSO data so far: {json.dumps(self.qso_data)}\n"
                f"Respond - keep it short. "
                f"Use log_and_end only after you have said 73."
            )
        })

        result = self._call_claude(self.conversation_history)
        self.conversation_history.append({
            'role':    'assistant',
            'content': json.dumps(result)
        })
        return result

  def process_contest_exchange(self, transcribed_text, serial_number):
        """Process a fast contest exchange"""
        messages = [{
            'role':    'user',
            'content': (
                f"Received: \"{transcribed_text}\"\n"
                f"Our serial to send: {serial_number:03d}\n"
                f"Respond fast."
            )
        }]
        result = self._call_claude(messages, system=CONTEST_SYSTEM_PROMPT)
        return result

    def process_repeater_query(self, transcribed_text, callsign):
        """
        Process a query to the repeater/info node.
        Uses accurate real-time data for time, weather, news and traffic.
        """
        from utils import (
            get_utc_time, get_local_time,
            get_weather, get_news, get_traffic
        )

        # Always get time and weather
        utc_time   = get_utc_time()
        local_time = get_local_time()
        weather    = get_weather()

        # Only fetch news/traffic if likely requested
        text_lower   = transcribed_text.lower()
        news_data    = None
        traffic_data = None

        if any(w in text_lower for w in ['news', 'headline', 'bbc']):
            news_data = get_news()
        if any(w in text_lower for w in
               ['traffic', 'road', 'motorway', 'travel', 'm25',
                'm1', 'm6', 'a1', 'a3']):
            traffic_data = get_traffic()

        # Build context for Claude with accurate real-time data
        context = (
            f"Repeater callsign: {callsign}\n"
            f"Caller transmission: \"{transcribed_text}\"\n"
            f"\nACCURATE CURRENT TIME - use exactly as given, "
            f"do not guess or change:\n"
            f"  UTC:      {utc_time['spoken']}\n"
            f"  Local UK: {local_time['spoken']}\n"
            f"\nCurrent weather near repeater:\n"
            f"  {weather['spoken']}\n"
        )

        if news_data:
            context += f"\nLatest news:\n  {news_data['spoken']}\n"
        if traffic_data:
            context += f"\nTraffic:\n  {traffic_data['spoken']}\n"

        context += (
            f"\nRespond to the caller's request using only the data "
            f"provided above. Identify any callsign in their "
            f"transmission. Keep response short and radio-friendly. "
            f"Sign off with {callsign}."
        )

        messages = [{'role': 'user', 'content': context}]
        result   = self._call_claude(messages, system=REPEATER_SYSTEM_PROMPT)
        return result

    def _get_band(self, freq_mhz):
        """Identify amateur band from frequency"""
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


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
if __name__ == '__main__':

    brain = QSOBrain()

    print("=" * 60)
    print("=== Testing CQ call ===")
    result = brain.get_cq_call(144.300)
    print(f"Speech: {result['speech']}")
    print(f"Action: {result['action']}")

    print("\n" + "=" * 60)
    print("=== Testing reply to incoming call ===")
    brain.reset()
    result = brain.process_received_transmission(
        "MX0MXO this is G4ABC you are 59 name is John QTH Bristol over"
    )
    print(f"Speech: {result['speech']}")
    print(f"Action: {result['action']}")
    print(f"Data:   {result['qso_data']}")

    print("\n" + "=" * 60)
    print("=== Testing 73 handling ===")
    result = brain.process_received_transmission(
        "Thanks MX0MXO 73 and good DX"
    )
    print(f"Speech: {result['speech']}")
    print(f"Action: {result['action']}")

    print("\n" + "=" * 60)
    print("=== Testing repeater - time query ===")
    brain.reset()
    result = brain.process_repeater_query(
        "Good evening this is G4ABC what is the time please",
        "MB7UAA"
    )
    print(f"Speech:   {result.get('speech')}")
    print(f"Callsign: {result.get('callsign')}")
    print(f"Request:  {result.get('request_type')}")

    print("\n" + "=" * 60)
    print("=== Testing repeater - weather query ===")
    brain.reset()
    result = brain.process_repeater_query(
        "MB7UAA this is M0XYZ what is the weather like today",
        "MB7UAA"
    )
    print(f"Speech:   {result.get('speech')}")
    print(f"Callsign: {result.get('callsign')}")
    print(f"Request:  {result.get('request_type')}")

    print("\n" + "=" * 60)
    print("=== Testing repeater - news query ===")
    brain.reset()
    result = brain.process_repeater_query(
        "MB7UAA this is G4TEST any news headlines please",
        "MB7UAA"
    )
    print(f"Speech:   {result.get('speech')}")
    print(f"Callsign: {result.get('callsign')}")
    print(f"Request:  {result.get('request_type')}")

    print("\n" + "=" * 60)
    print("=== Testing repeater - traffic query ===")
    brain.reset()
    result = brain.process_repeater_query(
        "MB7UAA this is 2E0ABC any traffic news for the M25 please",
        "MB7UAA"
    )
    print(f"Speech:   {result.get('speech')}")
    print(f"Callsign: {result.get('callsign')}")
    print(f"Request:  {result.get('request_type')}")

    print("\n" + "=" * 60)
    print("All tests complete")