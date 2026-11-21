"""HL7 sender.  python client.py [host] [port]   (sends a sample ADT^A04, a SIU^S12 and one invalid message)"""
import socket, sys
import hl7
from hl7_core import build_adt, build_siu_s12, frame, unframe


def send(msg, host="127.0.0.1", port=2575, timeout=5):
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall(frame(msg))
        data = b""
        while not data.endswith(b"\x1c\r"):
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
    ack = hl7.parse(unframe(data))
    return str(ack.segment("MSA")[1]), unframe(data)


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 2575
    adt = build_adt("A04", dict(mrn="MRN-1001", last="Hassan", first="Omar", dob="19850402", gender="M", phone="01000000000"))
    siu = build_siu_s12(dict(id="77", mrn="MRN-1001", start="202611170900", minutes=30, doctor="EG-ONC-001", reason="Follow-up"))
    bad = adt.replace("PID", "XXX")  # PID segment missing -> expect NACK
    for name, m in [("ADT^A04", adt), ("SIU^S12", siu), ("INVALID ADT", bad)]:
        code, _ = send(m, host, port)
        print(f"{name:12} -> {code}")
