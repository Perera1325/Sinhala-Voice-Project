def classify_command(text):
    """
    Takes a transcribed text (English or Sinhala) and returns (device_id, action).
    If it cannot determine either, it returns (None, None).
    """
    text_sinhala = text.lower()
    
    # Translate the text to English for a reliable fallback layer
    from deep_translator import GoogleTranslator
    try:
        text_english = GoogleTranslator(source='si', target='en').translate(text).lower()
    except:
        text_english = ""
    
    device_id = None
    action = None
    
    # 1. Determine Device (Check Sinhala first, then English)
    if "ලයිට්" in text_sinhala or "light" in text_english or "light" in text_sinhala:
        device_id = "light_1"
    elif "ෆෑන්" in text_sinhala or "fan" in text_english or "fan" in text_sinhala or "sam" in text_sinhala or "sam" in text_english:
        device_id = "fan_1"
        
    # 2. Determine Action (Check Sinhala first, then English)
    if "දාන්න" in text_sinhala or "on" in text_english or "on" in text_sinhala or "ඔන්" in text_sinhala:
        action = "ON"
    elif "නිවන්න" in text_sinhala or "ඕෆ්" in text_sinhala or "off" in text_english or "off" in text_sinhala:
        action = "OFF"
        
    # Default fallback: If the user says "Turn it off" without mentioning the light, assume it's the light
    if device_id is None and action is not None:
        device_id = "light_1"
        
    return device_id, action
