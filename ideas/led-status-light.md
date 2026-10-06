# Feature: Status light on the box

## Why
Tapping a sticker gives no feedback until the speaker starts, which can take a few
seconds, so kids tap again or think it's broken. A small light next to the sticker
spot answers "did it see my sticker?" straight away, and shows when something is wrong.

## Hardware (per box, about £2)
- One 5mm **diffused common-cathode RGB LED** (diffused so it glows, not dazzles)
- Resistors: **220Ω** for red, **100Ω** for green and blue (the Pi's pins are 3.3V)
- 4 jumper wires (female–female if using header pins), or solder
- A hole or light pipe in the case next to the sticker spot

### Wiring
The PN532 reader already uses the I2C pins (3 and 5) plus a power pin and a ground.
The LED uses three free GPIOs and its own ground, so nothing moves.

```
Pi Zero 2 W header                         RGB LED (common cathode)
--------------------                       ------------------------
Pin 11  GPIO 17  ---[ 220Ω ]------------>  R
Pin 13  GPIO 27  ---[ 100Ω ]------------>  G
Pin 15  GPIO 22  ---[ 100Ω ]------------>  B
Pin 14  GND      ------------------------>  common (the longest leg)

Already in use by the reader: pin 1 or 2 (power), 3 (SDA), 5 (SCL), a GND (e.g. 6 or 9)
```

Check the power and ground pins your reader actually uses before wiring; any GND pin works for the LED.

## What the light means

The light is **off when nothing is happening**. A bedroom box must not glow all night.

| When | Light | Notes |
|---|---|---|
| Box starting up | slow blue pulse | until the web app and reader are ready |
| Ready after start-up | one green blink | then off |
| Sticker seen | instant short white blink | before anything else, so kids know it was read |
| Playing started | two green blinks | after the speaker confirms |
| Couldn't play (speaker not found, cast failed) | three red blinks | |
| Sticker not recognised / song deleted | two amber blinks | amber = red + green |
| Quiet mode (sticker read, not playing) | one long white | |
| Waiting to write a sticker | purple pulse | until a sticker is held there or it times out |
| Sticker written | long green | |
| Sticker write failed | three red blinks | |
| Reader not working | one red blink a minute | so a broken reader is noticed |
| Control stickers (future) | own short pattern each | e.g. Stop = one red, Pause = one amber |

At night (from the sleep timer's "after" time) everything is shown at low brightness.

## Software plan
1. **`led.py`**: a `StatusLight` class with one method, `signal(event)`. A small
   background thread plays the patterns, so the NFC loop is never slowed down. Events
   arriving mid-pattern replace the current one. If there is no GPIO (no LED fitted, or
   running on Windows), it does nothing, the same way a missing PN532 is handled.
2. **GPIO library**: use gpiozero's `RGBLED` (PWM, for brightness and pulsing) with the
   **RPi.GPIO** backend that is already installed, not lgpio. lgpio is the package
   that failed to build on rose.
3. **Hooks** (all in existing code):
   - `main.py`: start-up pulse, then ready
   - `nfc_daemon.py`: sticker seen, playing / failed (inside `_do_cast`), not recognised,
     quiet mode, writing / written / failed
   - the reader self-healing code: reader not working
4. **Settings** (`config.json` + Settings screen): light on/off, brightness, and
   "dim at night" on by default. A **Test light** button runs through every pattern.
5. **API**: `POST /api/led/test`, and the light's state in `/api/box` for the
   "Is it working?" screen.
6. **Tests**: unit-test the event → pattern mapping with a fake LED; `tools/led_test.py`
   on the Pi to check the wiring colour by colour.

## Rollout
1. Wire one LED on Ollie's box and run `tools/led_test.py`.
2. Ship the software to beta. Boxes without an LED behave exactly as now.
3. Live with it for a week, adjust patterns and brightness, then wire rose and move to stable.

## Later
- A ring of LEDs (NeoPixel) around the sticker spot for a nicer "reading…" spin.
  It needs 5V level shifting and a different pin, so start with the single LED.
