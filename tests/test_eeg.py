"""Hardware-independent checks against the supplied implementation."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dinosaur"))
from eeg_serial_reader import EEGSerialReader, parse_line
from eeg_control import attention_speed_bonus, clamp_game_speed, is_signal_good


class ProtocolTests(unittest.TestCase):
    def test_frame_and_case(self):
        self.assertEqual(parse_line(" att :65,MED:48,SIG:0,BLINK:1,COUNT:3\r\n"),
                         dict(ATT=65, MED=48, SIG=0, BLINK=1, COUNT=3))

    def test_malformed_fragments(self):
        self.assertEqual(parse_line("noise,ATT:no,MED:75,SIG:0,BLINK:"), dict(MED=75, SIG=0))
        self.assertEqual(parse_line(""), {})

    def test_partial_update_preserves_previous_fields(self):
        reader = EEGSerialReader("unused", 57600)
        reader._update_from_fields(dict(ATT=65, MED=48, SIG=0))
        reader._update_from_fields(dict(ATT=90))
        self.assertEqual((reader.get_state().attention, reader.get_state().meditation), (90, 48))

    def test_blink_latches_until_consumed(self):
        reader = EEGSerialReader("unused", 57600)
        reader._update_from_fields(dict(BLINK=1, COUNT=1))
        reader._update_from_fields(dict(BLINK=0))
        self.assertTrue(reader.consume_blink())
        self.assertFalse(reader.consume_blink())
        self.assertEqual(reader.get_state().blink_count, 1)

    def test_snapshot_isolation(self):
        reader = EEGSerialReader("unused", 57600)
        reader._update_from_fields(dict(ATT=65))
        snapshot = reader.get_state()
        snapshot.attention = 0
        self.assertEqual(reader.get_state().attention, 65)

    def test_empty_update_does_not_connect(self):
        reader = EEGSerialReader("unused", 57600)
        reader._update_from_fields({})
        self.assertFalse(reader.get_state().connected)


class ControlTests(unittest.TestCase):
    def test_signal_boundary(self):
        self.assertTrue(is_signal_good(10))
        self.assertFalse(is_signal_good(11))
        self.assertFalse(is_signal_good(200))

    def test_speed_bounds(self):
        self.assertEqual(clamp_game_speed(-100), 5)
        self.assertEqual(clamp_game_speed(100), 30)
        self.assertEqual(clamp_game_speed(20.9), 20)

    def test_attention_tiers_are_disabled_in_this_snapshot(self):
        for attention in (0, 49, 50, 64, 65, 79, 80, 100):
            self.assertEqual(attention_speed_bonus(attention), 0)


if __name__ == "__main__":
    unittest.main()
