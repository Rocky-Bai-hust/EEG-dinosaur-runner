# Data protocol

## Arduino input

The parser expects `AA AA length payload checksum`. Length must be 1–169 bytes, and checksum is `255 - (sum(payload) & 0xFF)`.

Only two payload layouts are recognized:

- Raw packet: length 4, bytes `[0x80, 0x02, high, low]`; high/low form a signed 16-bit sample.
- Digest packet: length 32, payload[0]=0x02, payload[1]=SIG, payload[28]=0x04, payload[29]=ATT, payload[30]=0x05, payload[31]=MED.

Digest updates produce a text frame. Raw samples produce a blink frame on an upward crossing of absolute amplitude >=1050, with a minimum 350 ms interval between candidates. Blink processing requires SIG <=50 and a digest with ATT>0 or MED>0. This is an artifact-sensitive threshold heuristic, not a general-purpose EEG classifier.

The parser blocks while waiting for bytes, has no packet-read timeout, and does not implement general ThinkGear TLV/EXCODE parsing. Modules with different layouts require code adaptation.

## Arduino output / Python input

57600 baud text frames terminate with a newline (`Serial.println` emits CRLF):

```text
ATT:65,MED:48,SIG:0,BLINK:1,COUNT:3
```

| Field | Meaning |
| --- | --- |
| ATT | Module attention indicator, typically 0–100 |
| MED | Module meditation indicator, typically 0–100 |
| SIG | Poor-signal indicator; lower is better, 200 commonly indicates poor contact |
| BLINK | 1 latches a one-shot jump candidate; 0 does not clear a pending event |
| COUNT | Firmware's cumulative blink-candidate count since startup |

`parse_line()` splits on commas and colons, uppercases keys, converts integers and ignores malformed fragments. It does not enforce required fields, known keys or physiological bounds. Missing fields retain their previous values. Nonempty parsed input marks the reader connected, even when it does not include a recognized field.

`consume_blink()` returns True once then clears the pending boolean. Multiple events arriving between game frames may coalesce into one pending jump; COUNT can still indicate their cumulative number.

## Quality and freshness

Default desktop gameplay gating uses SIG <=10 and `connected=True`. Startup additionally requires SIG=0 stable for 2000 ms. Firmware blink gating uses SIG <=50. All are implementation settings, not validated scientific quality criteria.

The reader stores a timestamp but the game does not apply an inactivity cutoff. A silent serial link can therefore retain stale values and a connected flag. Explicit read failures set connected=False, but there is no automatic port reopen.

See `examples/serial_frames.txt` for synthetic input; no human EEG recordings are bundled.
