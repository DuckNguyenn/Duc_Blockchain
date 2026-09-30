import unittest

from iot_code.gateway.mqtt_subscriber import parse_payload


class MqttGatewayTests(unittest.TestCase):
    def test_parse_json_telemetry(self):
        row = parse_payload(
            b'{"device_id":"HRC-ESP32-01","timestamp_ms":1000,"distance_cm":24.6}'
        )
        self.assertEqual(row["distance_cm"], "24.6")
        self.assertEqual(row["timestamp"], "1970-01-01T00:00:01+00:00")

    def test_rejects_invalid_or_negative_distance(self):
        self.assertIsNone(parse_payload(b"not-json"))
        self.assertIsNone(parse_payload(b'{"distance_cm":-1}'))
        self.assertIsNone(parse_payload(b'{"state":"SAFE"}'))

    def test_accepts_explicit_measurement_timestamp(self):
        row = parse_payload(
            '{"measured_at":"2026-09-30T00:00:00Z","distance_cm":80,"dt_s":0.2}'
        )
        self.assertEqual(row["timestamp"], "2026-09-30T00:00:00Z")
        self.assertEqual(row["dt_s"], "0.2")


if __name__ == "__main__":
    unittest.main()
