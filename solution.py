import inspect
from functools import wraps

from chat_parser import ParseError, parse_command

RANK = {None: 0, "member": 1, "officer": 2, "master": 3}


def requires_role(min_role):
    def decorate(function):
        @wraps(function)
        def wrapper(state, sender, *args, **kwargs):
            player = state["players"][sender]
            if RANK[player["role"]] < RANK[min_role]:
                return {"status": "denied", "reason": "forbidden"}
            return function(state, sender, *args, **kwargs)
        return wrapper
    return decorate


def audit(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        bound = inspect.signature(function).bind(*args, **kwargs)
        sender = bound.arguments["sender"]
        raw = bound.arguments["raw"]
        log = bound.arguments["log"]
        try:
            result = function(*args, **kwargs)
        except Exception as exc:
            log.append({"sender": sender, "raw": raw, "status": "error",
                        "reason": None, "error": type(exc).__name__})
            raise
        log.append({"sender": sender, "raw": raw, "status": result["status"],
                    "reason": result["reason"], "error": None})
        return result
    return wrapper


def _find(state, nick):
    for player_id, player in state["players"].items():
        if player["nick"] == nick:
            return player_id, player
    return None, None


def whisper(state, sender, target, text):
    _, player = _find(state, target)
    if player is None:
        return {"status": "denied", "reason": "player_not_found"}
    player["messages"].append({"sender": sender, "text": text})
    return {"status": "ok", "reason": None}


@requires_role("officer")
def kick(state, sender, target):
    target_id, target_player = _find(state, target)
    if target_player is None:
        return {"status": "denied", "reason": "player_not_found"}
    actor = state["players"][sender]
    if target_id == sender:
        return {"status": "denied", "reason": "forbidden"}
    if actor["guild"] is None or actor["guild"] != target_player["guild"]:
        return {"status": "denied", "reason": "forbidden"}
    if target_player["role"] == "master":
        return {"status": "denied", "reason": "forbidden"}
    if actor["role"] == "officer" and target_player["role"] != "member":
        return {"status": "denied", "reason": "forbidden"}

    guild_id = actor["guild"]
    state["guilds"][guild_id]["members"].remove(target_id)
    target_player["guild"] = None
    target_player["role"] = None
    return {"status": "ok", "reason": None}


@requires_role("master")
def disband(state, sender):
    actor = state["players"][sender]
    guild_id = actor["guild"]
    if guild_id is None:
        return {"status": "denied", "reason": "forbidden"}
    for member_id in state["guilds"][guild_id]["members"]:
        state["players"][member_id]["guild"] = None
        state["players"][member_id]["role"] = None
    del state["guilds"][guild_id]
    return {"status": "ok", "reason": None}


def build_registry():
    return {"w": whisper, "guild kick": kick, "guild disband": disband}


@audit
def dispatch(state, sender, raw, *, registry, log):
    try:
        name, args = parse_command(raw)
    except ParseError:
        return {"status": "denied", "reason": "parse_error"}
    if name not in registry:
        return {"status": "denied", "reason": "unknown_command"}
    handler = registry[name]
    try:
        inspect.signature(handler).bind(state, sender, *args)
    except TypeError:
        return {"status": "denied", "reason": "bad_arguments"}
    return handler(state, sender, *args)
