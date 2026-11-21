"""HL7 v2 helpers: build ADT/SIU/ORM/ORU, validate, build ACK/NACK, MLLP framing."""
import uuid
from datetime import datetime

import hl7

SB, EB, CR = b"\x0b", b"\x1c", b"\r"   # MLLP: <VT> message <FS><CR>


def _ts(dt=None):
    return (dt or datetime.now()).strftime("%Y%m%d%H%M%S")


def esc(v):
    """Escape HL7 delimiters and strip line breaks in free text."""
    s = str(v if v is not None else "")
    for a, b in (("\\", "\\E\\"), ("|", "\\F\\"), ("^", "\\S\\"), ("&", "\\T\\"), ("~", "\\R\\")):
        s = s.replace(a, b)
    return s.replace("\r", " ").replace("\n", " ")


def _msh(msg_type, trigger, sending="ONCOSPHERE", receiving="EMR"):
    return f"MSH|^~\\&|{sending}|HOSPITAL|{receiving}|HOSPITAL|{_ts()}||{msg_type}^{trigger}|{uuid.uuid4().hex[:12]}|P|2.5"


def _pid(p):
    return (f"PID|1||{esc(p['mrn'])}^^^ONCOSPHERE^MR||{esc(p.get('last', ''))}^{esc(p.get('first', ''))}"
            f"||{p.get('dob', '')}|{p.get('gender', '')}|||||{esc(p.get('phone', ''))}")


def build_adt(trigger, p):
    """ADT^A04 (register) / ADT^A08 (update). p: dict(mrn,last,first,dob 'YYYYMMDD',gender,phone)"""
    return "\r".join([_msh("ADT", trigger), f"EVN|{trigger}|{_ts()}", _pid(p)])


def build_siu(trigger, a):
    """SIU^S12 new / S14 modified / S15 cancelled. a: dict(id, mrn, start 'YYYYMMDDHHMM', minutes, doctor, reason, ...)"""
    return "\r".join([
        _msh("SIU", trigger),
        f"SCH|{a['id']}||||||{esc(a.get('reason', ''))}||{a['minutes']}|min|^^{a['minutes']}^{a['start']}",
        _pid(a),
        f"AIP|1||{esc(a['doctor'])}"])


def build_siu_s12(a):
    return build_siu("S12", a)


def build_orm(o):
    """ORM^O01 new order. o: patient fields + order_id, order_type"""
    return "\r".join([_msh("ORM", "O01"), _pid(o), f"ORC|NW|{o['order_id']}", f"OBR|1|{o['order_id']}||{esc(o['order_type'])}"])


def build_oru(r):
    """ORU^R01 result. r: patient fields + order_id, order_type, result_text"""
    return "\r".join([_msh("ORU", "R01"), _pid(r), f"OBR|1|{r['order_id']}||{esc(r['order_type'])}",
                      f"OBX|1|TX|{esc(r['order_type'])}||{esc(r['result_text'])}||||||F"])


REQUIRED = {"ADT": ["EVN", "PID"], "SIU": ["SCH", "PID"], "ORM": ["PID", "ORC"], "ORU": ["PID", "OBR", "OBX"]}


def validate(raw):
    """Return (ok, error_text). Checks MSH fields, supported type and required segments."""
    try:
        m = hl7.parse(raw)
    except Exception as e:
        return False, f"Unparseable HL7: {e}"
    try:
        msh = m.segment("MSH")
        mtype = str(msh[9][0][0])
        control = str(msh[10])
    except Exception:
        return False, "Invalid MSH segment"
    if not control:
        return False, "Missing MSH-10 control id"
    if mtype not in REQUIRED:
        return False, f"Unsupported message type {mtype}"
    present = {str(s[0]) for s in m}
    missing = [s for s in REQUIRED[mtype] if s not in present]
    if missing:
        return False, f"Missing segments: {', '.join(missing)}"
    return True, ""


def control_id(raw):
    return str(hl7.parse(raw).segment("MSH")[10])


def build_ack(raw, ok, error=""):
    """AA on success, AE with ERR text on failure."""
    try:
        control = control_id(raw)
    except Exception:
        control = "UNKNOWN"
    code = "AA" if ok else "AE"
    segs = [f"MSH|^~\\&|EMR|HOSPITAL|ONCOSPHERE|HOSPITAL|{_ts()}||ACK|{uuid.uuid4().hex[:12]}|P|2.5",
            f"MSA|{code}|{control}" + ("" if ok else f"|{error}")]
    if not ok:
        segs.append(f"ERR||||{error}")
    return "\r".join(segs)


def frame(msg):
    return SB + msg.encode() + EB + CR


def unframe(data):
    return data.strip(SB + EB + CR).decode()
