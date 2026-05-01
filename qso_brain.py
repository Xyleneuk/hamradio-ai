import re
import anthropic
import json

client = anthropic.Anthropic()

_PHONETICS = {
    'A': 'Alpha',   'B': 'Bravo',   'C': 'Charlie', 'D': 'Delta',
    'E': 'Echo',    'F': 'Foxtrot', 'G': 'Golf',    'H': 'Hotel',
    'I': 'India',   'J': 'Juliet',  'K': 'Kilo',    'L': 'Lima',
    'M': 'Mike',    'N': 'November','O': 'Oscar',   'P': 'Papa',
    'Q': 'Quebec',  'R': 'Romeo',   'S': 'Sierra',  'T': 'Tango',
    'U': 'Uniform', 'V': 'Victor',  'W': 'Whiskey', 'X': 'X-ray',
    'Y': 'Yankee',  'Z': 'Zulu',
    '0': 'Zero',  '1': 'One',   '2': 'Two',   '3': 'Three',
    '4': 'Four',  '5': 'Five',  '6': 'Six',   '7': 'Seven',
    '8': 'Eight', '9': 'Nine',
}

# Matches standard amateur callsigns: prefix (1-3 chars) + digit + suffix (1-4 letters)
_CALLSIGN_RE  = re.compile(r'^([A-Z0-9]{1,3}[0-9][A-Z]{1,4})$')
# Doubled RST: "5959" → sent=59, rcvd=59
_RST_DOUBLE_RE = re.compile(r'\b([1-5][1-9])([1-5][1-9])\b')
_RST_RE        = re.compile(r'\b([1-5][1-9])\b')
# Name: "my name is John", "name John", "I'm John", "name's John"
_NAME_RE       = re.compile(
    r"(?:my\s+name(?:'s|\s+is)?\s+|name(?:\s+is)?\s+|I'?m\s+|I\s+am\s+)([A-Za-z]\w*)",
    re.IGNORECASE
)
# QTH: "QTH Maidenhead", "QTH is London", "located in X", "from X", "location X"
_QTH_RE        = re.compile(
    r"(?:QTH\s+(?:is\s+)?|located\s+in\s+|location\s+(?:is\s+)?|I'?m\s+in\s+|from\s+)"
    r"([A-Za-z][A-Za-z\s]{1,29}?)"
    r"(?:\s*[,.]|\s+(?:QSL|over|73|out|my)|$)",
    re.IGNORECASE
)
_CONFIRM_RE    = re.compile(
    r"\b(QSL|confirmed?|correct|affirmative|yes|roger|copy|copied|that'?s\s+right)\b",
    re.IGNORECASE
)
# Contest serial: 1-3 digit number (e.g. "023", "142")
_SERIAL_RE     = re.compile(r'\b(\d{1,3})\b')


def _phonetic_callsign(cs):
    return ' '.join(_PHONETICS.get(c, c) for c in cs.upper())


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
- Speech recognition may split callsigns across words (e.g. "2E1AV X" = "2E1AVX") - merge adjacent letters/digits to reconstruct
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
            'rst_sent':  None,
            'rst_rcvd':  None,
            'name':      None,
            'qth':       None,
            'complete':  False
        }
        self.our_callsign  = 'MX0MXO'
        self.operator_name = 'James'
        self.qth           = 'London Heathrow'

    def reset(self):
        self.conversation_history = []
        self.qso_data = {
            'callsign': None,
            'rst_sent':  None,
            'rst_rcvd':  None,
            'name':      None,
            'qth':       None,
            'complete':  False
        }

    def _parse(self, raw, system=None):
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
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=100,
            system=system or SYSTEM_PROMPT,
            messages=messages
        )
        return self._parse(response.content[0].text, system)

    def _call_claude_streaming(self, messages, system=None):
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
        """Generate CQ call from template — no API call needed."""
        cs_phonetic = _phonetic_callsign(self.our_callsign)
        speech = (
            f"CQ CQ, this is {cs_phonetic} stroke AI. "
            f"Please respond with your callsign and I will come back to you. QRZ"
        )
        result = {'action': 'transmit', 'speech': speech, 'qso_data': self.qso_data.copy()}
        self.conversation_history.append({
            'role': 'assistant', 'content': json.dumps(result)
        })
        return result

    def build_confirmation_request(self, their_callsign):
        """Ask the station to confirm their callsign."""
        speech = (
            f"I copied {their_callsign}. Is that correct? "
            f"Please say QSL to confirm, or repeat your callsign. Over."
        )
        result = {'action': 'transmit', 'speech': speech, 'qso_data': self.qso_data.copy()}
        self.conversation_history.append({
            'role': 'assistant', 'content': json.dumps(result)
        })
        return result

    def parse_confirmation(self, heard):
        """
        Strict confirmation parser.
        Returns confirmed/corrected callsign string, or None if not confirmed.
        Requires either:
          - An explicit confirmation word (QSL, yes, correct, roger, etc.), OR
          - A recognisable callsign (possibly correcting ours), OR
          - Phonetic letters that extend the current partial callsign (e.g. "Foxtrot Papa" → M0JFP)
        Random audio ("RST over", silence, etc.) returns None.
        """
        if not heard or not heard.strip():
            return None

        upper    = heard.upper()
        our_cs   = self.our_callsign.upper()
        existing = (self.qso_data.get('callsign') or '').upper()

        # Build reverse phonetic map: "FOXTROT" → "F"
        phonetic_rev = {v.upper(): k for k, v in _PHONETICS.items()}

        # --- 1. Try phonetic extension of the partial callsign we already have ---
        if existing:
            extension = ''
            for w in upper.split():
                clean = re.sub(r'[^A-Z]', '', w)
                if clean in phonetic_rev:
                    extension += phonetic_rev[clean]
                elif len(clean) == 1:
                    extension += clean
            if extension:
                candidate = existing + extension
                if _CALLSIGN_RE.fullmatch(candidate) and candidate != our_cs:
                    return candidate

        # --- 2. Try to find a complete callsign (may be a correction) ---
        words = [re.sub(r'[^A-Z0-9]', '', w) for w in upper.split()]
        best  = None
        for i, w in enumerate(words):
            if not w:
                continue
            if _CALLSIGN_RE.fullmatch(w) and w != our_cs:
                if best is None or len(w) > len(best):
                    best = w
            if i + 1 < len(words) and words[i + 1]:
                for take in range(1, min(5, len(words[i + 1]) + 1)):
                    candidate = w + words[i + 1][:take]
                    if _CALLSIGN_RE.fullmatch(candidate) and candidate != our_cs:
                        if best is None or len(candidate) > len(best):
                            best = candidate
        if best:
            return best

        # --- 3. Explicit confirmation word → keep existing callsign ---
        if existing and _CONFIRM_RE.search(heard):
            return existing

        # Nothing useful — caller must retry
        return None

    def build_callsign_response(self, their_callsign):
        """Template: callsign confirmed — give our RST and ask for theirs + name + QTH."""
        self.qso_data['callsign'] = their_callsign
        self.qso_data['rst_sent'] = '59'
        speech = (
            f"{their_callsign} de {self.our_callsign}, "
            f"you are 59 in {self.qth}. "
            f"Please go ahead with my RST, your name, and your location. Over."
        )
        result = {'action': 'transmit', 'speech': speech, 'qso_data': self.qso_data.copy()}
        self.conversation_history.append({
            'role': 'assistant', 'content': json.dumps(result)
        })
        return result

    def build_farewell(self, their_callsign, rst_rcvd='59'):
        """Template farewell after RST exchange."""
        self.qso_data['callsign'] = their_callsign
        self.qso_data['rst_rcvd'] = rst_rcvd
        self.qso_data['rst_sent'] = self.qso_data.get('rst_sent') or '59'
        self.qso_data['complete'] = True
        name = self.qso_data.get('name')
        name_part = f", {name}" if name else ""
        speech = (
            f"{their_callsign} thank you for the {rst_rcvd}{name_part}, "
            f"73 and good DX. {their_callsign} de {self.our_callsign}."
        )
        result = {'action': 'log_and_end', 'speech': speech, 'qso_data': self.qso_data.copy()}
        self.conversation_history.append({
            'role': 'assistant', 'content': json.dumps(result)
        })
        return result

    def _extract_qso_data(self, text):
        """
        Fast local regex extraction of callsign/RST/name/QTH before calling Claude.
        Handles Whisper splitting callsigns across word boundaries (e.g. "2E1AV X" → "2E1AVX").
        """
        upper  = text.upper()
        our_cs = self.our_callsign.upper()

        if not self.qso_data['callsign']:
            # Strip punctuation and try single words + two-word merges,
            # preferring the longest valid callsign found.
            words = [re.sub(r'[^A-Z0-9]', '', w) for w in upper.split()]
            best  = None
            for i, w in enumerate(words):
                if not w:
                    continue
                if _CALLSIGN_RE.fullmatch(w) and w != our_cs:
                    if best is None or len(w) > len(best):
                        best = w
                # Try extending with the start of the next word (handles split callsigns)
                if i + 1 < len(words) and words[i + 1]:
                    for take in range(1, min(5, len(words[i + 1]) + 1)):
                        candidate = w + words[i + 1][:take]
                        if _CALLSIGN_RE.fullmatch(candidate) and candidate != our_cs:
                            if best is None or len(candidate) > len(best):
                                best = candidate
            if best:
                self.qso_data['callsign'] = best

        if not self.qso_data['rst_rcvd']:
            m = _RST_DOUBLE_RE.search(upper)
            if m:
                self.qso_data['rst_rcvd'] = m.group(1)
            else:
                m = _RST_RE.search(upper)
                if m:
                    self.qso_data['rst_rcvd'] = m.group(1)

        if not self.qso_data['name']:
            m = _NAME_RE.search(text)
            if m:
                self.qso_data['name'] = m.group(1).capitalize()

        if not self.qso_data['qth']:
            m = _QTH_RE.search(text)
            if m:
                self.qso_data['qth'] = m.group(1).strip().title()

    def process_received_transmission(self, transcribed_text):
        self._extract_qso_data(transcribed_text)

        self.conversation_history.append({
            'role':    'user',
            'content': (
                f"Received: \"{transcribed_text}\"\n"
                f"Extracted: {json.dumps(self.qso_data)}\n"
                f"One sentence reply. log_and_end after RST exchange."
            )
        })
        result = self._call_claude_streaming(self.conversation_history)
        self.conversation_history.append({
            'role': 'assistant', 'content': json.dumps(result)
        })
        return result

    def build_contest_response(self, their_callsign, our_serial, heard=''):
        """Template contest exchange — no Claude needed."""
        self.qso_data['callsign']    = their_callsign
        self.qso_data['rst_sent']    = '59'
        self.qso_data['rst_rcvd']    = '59'
        self.qso_data['serial_sent'] = f"{our_serial:03d}"

        their_serial = None
        m = _SERIAL_RE.search(heard)
        if m:
            their_serial = f"{int(m.group(1)):03d}"
            self.qso_data['serial_rcvd'] = their_serial

        their_serial_str = f" {their_serial}" if their_serial else ""
        speech = (
            f"{their_callsign}{their_serial_str}, "
            f"you are 59 {our_serial:03d}. {self.our_callsign}."
        )
        return {'action': 'log_and_end', 'speech': speech, 'qso_data': self.qso_data.copy()}

    def process_contest_exchange(self, transcribed_text, serial_number):
        self._extract_qso_data(transcribed_text)
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
