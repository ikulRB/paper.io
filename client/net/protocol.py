import sys
import os
import time

try:
    from net import paper_pb2 as pb
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    import paper_pb2 as pb  # type: ignore

PROTOCOL_VERSION = 2
MAX_MSG_SEQ = 2**63 - 1


def now_ms() -> int:
    return int(time.monotonic() * 1000)


def vec2(x: float, y: float):
    v = pb.Vec2()
    v.x = float(x)
    v.y = float(y)
    return v


def player_state_to_dict(ps) -> dict:
    head = (0.0, 0.0)
    try:
        if ps.HasField("head"):
            head = (ps.head.x, ps.head.y)
    except ValueError:
        if ps.head.x != 0.0 or ps.head.y != 0.0:
            head = (ps.head.x, ps.head.y)
    return {
        "player_id": ps.player_id,
        "name": ps.name,
        "role": ps.role,
        "status": ps.status,
        "score": ps.score,
        "head": head,
        "angle": ps.angle,
        "trail": [(p.x, p.y) for p in ps.trail],
        "territory": [(p.x, p.y) for p in ps.territory],
    }