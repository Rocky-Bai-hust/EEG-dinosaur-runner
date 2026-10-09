# Hardware setup

## Required components

- A TGAM-compatible EEG module producing the exact packet layouts described in [protocol.md](protocol.md) at 57600 baud.
- An Arduino UNO or compatible Nano with the hardware `Serial` interface on D0/RX.
- A USB data cable, a computer and connection wires.
- A power arrangement specified by the particular EEG module vendor. The source does not establish module supply voltage or UART electrical tolerance; verify those specifications before wiring. Do not assume a 5 V Arduino supply is suitable for every TGAM board.

## Wired reference connection

| Module / connection | Arduino / computer |
| --- | --- |
| TGAM TX | Arduino D0/RX |
| TGAM RX | Leave disconnected for this receive-only sketch |
| TGAM GND | Arduino GND |
| Arduino USB | Computer USB port |

The sketch shares one hardware UART: incoming raw data reaches D0/RX while parsed text is sent over Serial TX to the USB serial interface. Do not send arbitrary PC data to the shared RX line during acquisition. Power and logic compatibility depend on the actual module.

## Firmware upload

1. Disconnect the module TX wire from D0/RX before uploading; that pin is also used by the board bootloader.
2. Open `arduino/arduino.ino` in Arduino IDE.
3. Install/select the Arduino AVR board core, the actual UNO/Nano model and the correct USB port. Some Nano clones require a different processor/bootloader selection.
4. Upload and reconnect the module TX wire.
5. For a quick inspection, open the serial monitor at 57600 baud. Expect an initial `ATT:0,MED:0,SIG:200,BLINK:0,COUNT:0` line followed by digest updates and blink events.
6. Close the serial monitor before starting Python.

The sketch uses only Arduino core facilities. It has not been compiled with an AVR toolchain in the release-preparation environment.

## Bluetooth transport

The reference course report describes an HC-05 receiving and forwarding the module's binary stream. The released sketch contains no HC-05 AT configuration or pairing code. Treat Bluetooth as an optional external transparent transport; verify its UART baud rate, role, wiring and module compatibility independently. The reproducible connection documented above is the wired route explicitly described in the sketch.
