import pyautogui
import time
import os
import sys
from datetime import datetime

# Ensure screenshots directory exists
os.makedirs("screenshots", exist_ok=True)

if len(sys.argv) > 1:
    custom_name = sys.argv[1].replace(" ", "_")
else:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    custom_name = f"capture_{timestamp}"

# Give user 3 seconds to switch to the window they want to screenshot
print(f"📸 Taking screenshot for '{custom_name}' in 3 seconds...")
print("Quick! Switch to the window you want to capture!")
time.sleep(3)

# Take screenshot
screenshot = pyautogui.screenshot()

# Generate filename
filename = f"screenshots/{custom_name}.png"

# Save
screenshot.save(filename)
print(f"✅ Screenshot successfully saved to: {filename}")
