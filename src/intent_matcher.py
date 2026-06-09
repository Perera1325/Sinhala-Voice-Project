import re

# Define the dictionary of commands
# We map variations of Singlish and English to the strict Hardware IoT constants
INTENT_MAP = {
    "LIGHT_ON": [
        r"(light|lait).*?(on|danna|daanna|daapan|daapn)",
        r"(turn on|switch on).*?(light|lait)"
    ],
    "LIGHT_OFF": [
        r"(light|lait).*?(off|niwanna|niwapn|niwapan)",
        r"(turn off|switch off).*?(light|lait)"
    ],
    "FAN_ON": [
        r"(fan|pan|sam).*?(on|danna|daanna|daapan|daapn)",
        r"(turn on|switch on).*?(fan|pan|sam)"
    ],
    "FAN_OFF": [
        r"(fan|pan|sam).*?(off|niwanna|niwapn|niwapan)",
        r"(turn off|switch off).*?(fan|pan|sam)"
    ],
    "CURTAIN_OPEN": [
        r"(curtain|redee|redi).*?(open|arinna|arapn|arapan)",
        r"(open).*?(curtain|redee)"
    ],
    "CURTAIN_CLOSE": [
        r"(curtain|redee|redi).*?(close|wahanna|wahapan|wahapn)",
        r"(close|shut).*?(curtain|redee)"
    ]
}

def extract_intent(spoken_text):
    """
    Analyzes the transcribed text (from Vosk) and returns the corresponding hardware command.
    Returns "UNKNOWN" if no intent matched.
    """
    text = spoken_text.lower().strip()
    
    # We remove filler words to make regex simpler
    # Singlish fillers: eka, ek, poddak
    # English fillers: the, please, can you
    fillers = ["eka ", "ek ", "the ", "please ", "can you ", "poddak "]
    for filler in fillers:
        text = text.replace(filler, "")

    print(f"🧠 NLP Processing clean text: '{text}'")

    for intent, patterns in INTENT_MAP.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return intent
                
    return "UNKNOWN"

# Example Tests (Run this script directly to test)
if __name__ == "__main__":
    test_cases = [
        "Light eka danna", 
        "Turn on the light",
        "Fan eka off krnna",
        "curtain eka arinna",
        "can you close the curtain please",
        "random sentence here"
    ]
    
    for t in test_cases:
        print(f"Input: {t} --> Output: {extract_intent(t)}")
