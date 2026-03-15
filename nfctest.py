"""
nfctest.py — standalone NFC read/write test
Cycles: read 3 times, then write once, repeat.
Run on the Pi: python nfctest.py
"""
import time
import board
import busio
from adafruit_pn532.i2c import PN532_I2C


def read_blocks(pn532):
    full_message = ""
    for block_num in range(4, 40):
        try:
            data = pn532.ntag2xx_read_block(block_num)
            if data is None:
                break
            chunk = "".join([chr(b) if 32 <= b <= 126 else "" for b in data])
            if not chunk.strip() and block_num > 10:
                break
            full_message += chunk
        except Exception:
            break
    return full_message.strip()


def write_blocks(pn532, text):
    while len(text) % 4 != 0:
        text += " "
    current_block = 4
    for i in range(0, len(text), 4):
        pn532.ntag2xx_write_block(current_block, bytearray(text[i:i + 4], "utf-8"))
        current_block += 1
        time.sleep(0.1)
    empty = bytearray(4)
    while current_block <= 15:
        pn532.ntag2xx_write_block(current_block, empty)
        current_block += 1
        time.sleep(0.1)


def wait_for_tag(pn532, prompt):
    print(prompt, end=" ", flush=True)
    while True:
        uid = pn532.read_passive_target(timeout=0.5)
        if uid is not None:
            print(f"[UID: {uid.hex().upper()}]")
            return uid


def wait_for_removal(pn532):
    print("  (remove tag...)", end=" ", flush=True)
    while True:
        uid = pn532.read_passive_target(timeout=0.5)
        if uid is None:
            print("gone.")
            return
        time.sleep(0.1)


# --- Init ---
print("Initialising PN532...")
i2c = busio.I2C(board.SCL, board.SDA)
pn532 = PN532_I2C(i2c, debug=False)
pn532.SAM_configuration()
print("PN532 ready.\n")

cycle = 0
while True:
    cycle += 1
    print(f"========== Cycle {cycle} ==========")

    # Three reads
    for i in range(1, 4):
        wait_for_tag(pn532, f"[READ {i}/3] Touch tag...")
        content = read_blocks(pn532)
        print(f"  Content: '{content}'")
        wait_for_removal(pn532)

    # One write
    write_text = f"stonies:test{cycle:03d}"
    print(f"\n[WRITE]   Will write: '{write_text}'")
    wait_for_tag(pn532, "          Touch tag to write...")
    try:
        write_blocks(pn532, write_text)
        readback = read_blocks(pn532)
        if readback.strip() == write_text.strip():
            print(f"  Write OK — verified: '{readback.strip()}'")
        else:
            print(f"  MISMATCH — wrote '{write_text}', read back '{readback}'")
    except Exception as e:
        print(f"  Write FAILED: {e}")
    wait_for_removal(pn532)
    print()
