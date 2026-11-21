import threading, time, socketserver, unittest
import hl7_core as h, client, server


class T(unittest.TestCase):
    P = dict(mrn="M1", last="A", first="B", dob="19900101", gender="F")

    def test_adt_valid(self):
        self.assertEqual(h.validate(h.build_adt("A04", self.P)), (True, ""))

    def test_siu_valid(self):
        m = h.build_siu_s12(dict(id="1", mrn="M1", start="202611170900", minutes=30, doctor="D"))
        self.assertTrue(h.validate(m)[0])

    def test_missing_segment_nack(self):
        ok, err = h.validate(h.build_adt("A04", self.P).replace("PID", "ZZZ"))
        self.assertFalse(ok); self.assertIn("PID", err)
        self.assertIn("MSA|AE", h.build_ack(h.build_adt("A04", self.P), ok, err))

    def test_garbage(self):
        self.assertFalse(h.validate("not hl7")[0])

    def test_end_to_end_over_socket(self):
        srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), server.Handler)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.assertEqual(client.send(h.build_adt("A04", self.P), port=port)[0], "AA")
        self.assertEqual(client.send(h.build_adt("A04", self.P).replace("EVN", "QQQ"), port=port)[0], "AE")
        srv.shutdown()


if __name__ == "__main__":
    unittest.main()
