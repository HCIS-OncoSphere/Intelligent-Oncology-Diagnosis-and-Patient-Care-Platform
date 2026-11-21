"""Build, log and (if HL7_ENABLED) send an HL7 message to the EMR. Never raises: HL7 problems must not break the API."""
import logging
import socket

from django.conf import settings

from . import hl7_core as h
from .models import Hl7Ack, Hl7Message

log = logging.getLogger(__name__)


def patient_fields(p):
    u = p.user
    return dict(mrn=p.mrn, last=u.last_name or u.username, first=u.first_name, dob=str(p.date_of_birth).replace("-", "")[:8],
                gender=p.gender, phone=p.phone)


def transmit(msg):
    """Send a logged message over MLLP and record the ACK/NACK."""
    try:
        with socket.create_connection((settings.HL7_HOST, settings.HL7_PORT), timeout=3) as s:
            s.sendall(h.frame(msg.raw_message))
            data = b""
            while h.EB not in data:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
        import hl7
        ack = hl7.parse(h.unframe(data))
        code = str(ack.segment("MSA")[1])
        err = str(ack.segment("MSA")[3]) if code != "AA" else ""
        Hl7Ack.objects.create(message=msg, ack_code=code, error_text=err)
        msg.status = "acked" if code == "AA" else "nacked"
    except Exception as e:  # network down, bad ACK ...
        log.warning("HL7 send failed: %s", e)
        msg.status = "failed"
    msg.save(update_fields=["status"])
    return msg


def dispatch(raw, mtype, trigger, **links):
    ok, err = h.validate(raw)
    if not ok:
        log.error("Refusing to log invalid outbound HL7: %s", err)
        return None
    msg = Hl7Message.objects.create(control_id=h.control_id(raw), message_type=mtype, trigger_event=trigger,
                                    raw_message=raw, **links)
    if settings.HL7_ENABLED:
        transmit(msg)
    return msg
