"""HL7 receiver (acts as the EMR).  python server.py [port]"""
import socketserver, sys
from hl7_core import build_ack, frame, unframe, validate, EB


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        buf = b""
        while EB not in buf:
            chunk = self.request.recv(4096)
            if not chunk:
                return
            buf += chunk
        raw = unframe(buf)
        ok, err = validate(raw)
        ack = build_ack(raw, ok, err)
        print(f"[HL7 IN ] {raw.splitlines()[0][:60]}...  -> {'ACK AA' if ok else 'NACK AE: ' + err}", flush=True)
        self.request.sendall(frame(ack))


if __name__ == "__main__":
    PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2575
    with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), Handler) as s:
        s.allow_reuse_address = True
        print(f"HL7 server listening on {PORT}", flush=True)
        s.serve_forever()
