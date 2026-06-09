# Implementation Plan: Fix "Light eka niwanna" Offline Voice Command

This plan addresses the issue where the offline voice command "Light eka niwanna" (Sinhala for "Turn off the light") is not working. The small English Vosk ASR engine (`vosk-model-small-en-us-0.15`) fails to recognize the out-of-vocabulary word "niwanna" within its current restricted grammar, resulting in transcriptions being cut short to just "light" or "light eka" and failing the control parser.

## User Review Required

> [!NOTE]
> This change expands the offline ASR phonetic dictionary with naturally heard English word approximations for Sinhala control commands. It will run locally on the PC and is backward-compatible with the voice control loop.

## Proposed Changes

### Voice Recognition & Command Parsing

#### [MODIFY] [offline_recognition.py](file:///c:/Users/Kasundi/Downloads/NoiseRM/offline_recognition.py)
* Expand the restricted Vosk `grammar` list to include: `"like"`, `"van"`, `"fannie"`, `"ek"`, `"data"`, `"no"`, and `"winner"`.
* Update the phonetic mapping logic in `transcribe_offline` to map these words to their target Sinhala phonetic components:
  * `"like"`, `"light"` &rarr; `"light"`
  * `"fan"`, `"van"`, `"fannie"` &rarr; `"fan"`
  * `"echo"`, `"acre"`, `"ek"` &rarr; `"eka"`
  * `"done"`, `"down"`, `"data"` &rarr; `"danna"`
  * `"never"`, `"no"`, `"winner"` &rarr; `"niwanna"`

#### [MODIFY] [offline_recognition.py (Ofline Method)](file:///C:/Users/Kasundi/Ofline%20Method/offline_recognition.py)
* Apply the same grammar and mapping enhancements to the offline evaluation copy.

#### [MODIFY] [main.py](file:///c:/Users/Kasundi/Downloads/NoiseRM/main.py)
* Add `"data"` to the `"ON"` robust phonetic matcher (`["danna", "down", "on", "done", "then", "can", "data"]`).
* Add `"winner"` to the `"OFF"` robust phonetic matcher (`["niwanna", "near", "no", "off", "want", "went", "winner"]`).

#### [MODIFY] [main.py (Ofline Method)](file:///C:/Users/Kasundi/Ofline%20Method/main.py)
* Apply the same parser robustness enhancements to the offline evaluation copy.

---

## Verification Plan

### Automated Tests
* Run `C:\Users\Kasundi\Ofline Method\evaluate_offline.py` and measure the updated accuracy metrics for both "danna" (ON) and "niwanna" (OFF) commands.
* Check the final generated `evaluation_results.csv` to ensure that "niwanna" commands map to the action `OFF` instead of returning `None`.

### Manual Verification
* Run the main program:
  ```powershell
  & C:/Python314/python.exe c:/Users/Kasundi/Downloads/NoiseRM/main.py
  ```
* Enter `1` to select "Registered User" simulation and enter manual commands or speak commands, and verify that "Light eka niwanna" sends an HTTP POST control command to the RPi4 server with `action=OFF`.
