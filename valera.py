"""Старая реализация Валеры. С ней можно запускать те же тесты через --impl valera."""
import inspect
from functools import wraps

from chat_parser import ParseError, parse_command

RANK = {None: 0, "member": 1, "officer": 2, "master": 3}


def requires_role(min_role):
    def decorate(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            bound = inspect.signature(function).bind(*args, **kwargs)
            player = bound.arguments["state"]["players"][bound.arguments["sender"]]
            role = player["role"]
            result = function(*args, **kwargs)
            if RANK[role] < RANK[min_role]:
                return {"status": "denied", "reason": "forbidden"}
            return result
        return wrapper
    return decorate


def audit(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        bound = inspect.signature(function).bind(*args, **kwargs)
        result = function(*args, **kwargs)
        if result["status"] == "ok":
            bound.arguments["log"].append({
                "sender": bound.arguments["sender"], "raw": bound.arguments["raw"],
                "status": "ok", "reason": None, "error": None,
            })
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
    player["messages"].append({"sender": sender, "text": text.strip()})
    return {"status": "ok", "reason": None}


@requires_role("officer")
def kick(state, sender, target):
    target_id, player = _find(state, target)
    if player is None:
        return {"status": "denied", "reason": "player_not_found"}
    actor = state["players"][sender]
    same_guild = player["guild"] is not None and player["guild"] == actor["guild"]
    if player["guild"] is not None:
        state["guilds"][player["guild"]]["members"].remove(target_id)
    player["guild"] = None
    player["role"] = None
    if not same_guild:
        return {"status": "denied", "reason": "forbidden"}
    return {"status": "ok", "reason": None}


@requires_role("master")
def disband(state, sender):
    guild_id = state["players"][sender]["guild"]
    if guild_id is None:
        return {"status": "denied", "reason": "forbidden"}
    for player_id in state["guilds"][guild_id]["members"]:
        state["players"][player_id]["guild"] = None
        state["players"][player_id]["role"] = None
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
        return handler(state, sender, *args)
    except TypeError:
        return {"status": "denied", "reason": "bad_arguments"}
