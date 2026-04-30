import anthropic
import json

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an experienced amateur radio operator working for the club station MX0MXO 
located in the United Kingdom. You are conducting SSB voice contacts on amateur radio bands.

Your behaviour:
- Follow correct amateur radio QSO procedure at all times
- Always identify with MX0MXO when transmitting
- Give signal reports in RS format for SSB (e.g. 59, 57, 55)
- Be friendly but concise - radio contacts are brief
- Always try to get the other station's callsign, signal report, name and QTH
- End contacts politely with 73 (best regards)
- Use phonetic alphabet when saying callsigns on air

CRITICAL RESPONSE FORMAT:
You must ONLY respond with a single valid JSON object. 
No other text before or after. No markdown. No code blocks. No explanations.
Just raw JSON in exactly this format:

{
  "action": "transmit",
  "speech": "exactly what to say on air using phonetics for callsigns",
  "qso_data": {
    "callsign": null,
    "rst_sent": null,
    "rst_rcvd": null,
    "name": null,
    "qth": null,
    "complete": false
  }
}

Action must be one of:
- "transmit" - you have something to say, speech will be spoken on air
- "listen" - you are waiting for a reply, speech will be spoken then we listen
- "log_and_end" - QSO is complete, log it and end"""


class QSOBrain:
    def __init__(self):
        self.conversation_history = []
        self.qso_data = {
            'callsign': None,
            'rst_sent': None,
            'rst_rcvd': None,
            'name': None,
            'qth': None,
            'complete': False
        }
        self.our_callsign = 'MX0MXO'

    def reset(self):
        """Reset for a new QSO"""
        self.conversation_history = []
        self.qso_data = {
            'callsign': None,
            'rst_sent': None,
            'rst_rcvd': None,
            'name': None,
            'qth': None,
            'complete': False
        }

    def _call_claude(self, messages):
        """Make API call to Claude and return parsed result"""
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=messages
        )

        raw = response.content[0].text.strip()

        # Clean up any accidental markdown
        raw = raw.replace('```json', '').replace('```', '').strip()

        try:
            parsed = json.loads(raw)

            # Update master qso_data with any new non-null values
            if 'qso_data' in parsed:
                for key, value in parsed['qso_data'].items():
                    if value is not None:
                        self.qso_data[key] = value

            # Always return the latest qso_data
            parsed['qso_data'] = self.qso_data.copy()
            return parsed

        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON parse error: {e}")
            print(f"Raw response was: {raw}")
            # Return a safe default
            return {
                'action': 'listen',
                'speech': '',
                'qso_data': self.qso_data.copy()
            }

    def get_cq_call(self, frequency_mhz):
        """Generate a CQ call for the current frequency"""
        band = self._get_band(frequency_mhz)

        messages = [{
            "role": "user",
            "content": (
                f"Generate a CQ call for {frequency_mhz:.4f} MHz on the {band} band. "
                f"Call CQ 3 times maximum. End with MX0MXO over."
            )
        }]

        result = self._call_claude(messages)

        # Add to conversation history
        self.conversation_history.append(messages[0])
        self.conversation_history.append({
            "role": "assistant",
            "content": json.dumps(result)
        })

        return result

    def process_received_transmission(self, transcribed_text):
        """Process what was heard and generate a response"""

        self.conversation_history.append({
            "role": "user",
            "content": (
                f"You just received this transmission on the radio (transcribed from audio): "
                f"\"{transcribed_text}\"\n"
                f"Current QSO data collected so far: {json.dumps(self.qso_data)}\n"
                f"Respond appropriately. If you have callsign, rst_sent, rst_rcvd and the "
                f"contact is wrapping up, use action log_and_end."
            )
        })

        result = self._call_claude(self.conversation_history)

        # Add response to history
        self.conversation_history.append({
            "role": "assistant",
            "content": json.dumps(result)
        })

        return result

    def _get_band(self, freq_mhz):
        """Identify amateur band from frequency"""
        bands = {
            (1.8, 2.0): '160m',
            (3.5, 4.0): '80m',
            (7.0, 7.3): '40m',
            (10.1, 10.15): '30m',
            (14.0, 14.35): '20m',
            (18.068, 18.168): '17m',
            (21.0, 21.45): '15m',
            (24.89, 24.99): '12m',
            (28.0, 29.7): '10m',
            (50.0, 52.0): '6m',
            (144.0, 148.0): '2m',
            (430.0, 440.0): '70cm',
        }
        for (low, high), band in bands.items():
            if low <= freq_mhz <= high:
                return band
        return 'unknown band'


# Test it
if __name__ == '__main__':
    brain = QSOBrain()

    print("Testing CQ call generation...")
    freq = 144.300
    result = brain.get_cq_call(freq)
    print(f"Action : {result['action']}")
    print(f"Speech : {result['speech']}")
    print(f"QSO Data: {result['qso_data']}")

    print("\nTesting response to incoming call...")
    brain.reset()
    result = brain.process_received_transmission(
        "MX0MXO this is Golf Four Alpha Bravo Charlie calling you, "
        "you are five nine here in London, my name is John. Over"
    )
    print(f"Action : {result['action']}")
    print(f"Speech : {result['speech']}")
    print(f"QSO Data: {result['qso_data']}")

    print("\nTesting follow up exchange...")
    result = brain.process_received_transmission(
        "Thank you MX0MXO, you are also five nine here, "
        "my QTH is London, thanks for the contact, 73"
    )
    print(f"Action : {result['action']}")
    print(f"Speech : {result['speech']}")
    print(f"QSO Data: {result['qso_data']}")