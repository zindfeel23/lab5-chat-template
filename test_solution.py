import pytest


def test_whisper_ok(impl, state, log):
    registry = impl.build_registry()
    result = impl.dispatch(state, "lina", '/w "Sir Lancelot" привет',
                           registry=registry, log=log)
    assert result == {"status": "ok", "reason": None}
    assert state["players"]["lancelot"]["messages"] == [
        {"sender": "lina", "text": "привет"}
    ]


def test_whisper_preserves_text(impl, state, log):
    registry = impl.build_registry()
    impl.dispatch(state, "lina", '/w Ada   привет " /guild disband',
                  registry=registry, log=log)
    assert state["players"]["ada"]["messages"] == [
        {"sender": "lina", "text": '  привет " /guild disband'}
    ]


def test_whisper_unknown_player(impl, state, log):
    registry = impl.build_registry()
    result = impl.dispatch(state, "lina", '/w "Nobody" привет',
                           registry=registry, log=log)
    assert result == {"status": "denied", "reason": "player_not_found"}
    assert state["players"]["lina"]["messages"] == []


def test_kick_by_officer(impl, state, log):
    registry = impl.build_registry()
    result = impl.dispatch(state, "marat", '/guild kick "Ada"',
                           registry=registry, log=log)
    assert result == {"status": "ok", "reason": None}
    assert "ada" not in state["guilds"]["dawn"]["members"]
    assert state["players"]["ada"]["guild"] is None
    assert state["players"]["ada"]["role"] is None


def test_member_cannot_kick(impl, state, log):
    registry = impl.build_registry()
    result = impl.dispatch(state, "ada", '/guild kick "Marat"',
                           registry=registry, log=log)
    assert result == {"status": "denied", "reason": "forbidden"}
    assert "marat" in state["guilds"]["dawn"]["members"]
    assert state["players"]["marat"]["guild"] == "dawn"


def test_cannot_kick_self(impl, state, log):
    registry = impl.build_registry()
    result = impl.dispatch(state, "lina", '/guild kick "Lina"',
                           registry=registry, log=log)
    assert result == {"status": "denied", "reason": "forbidden"}
    assert "lina" in state["guilds"]["dawn"]["members"]


def test_cannot_kick_master(impl, state, log):
    registry = impl.build_registry()
    result = impl.dispatch(state, "marat", '/guild kick "Lina"',
                           registry=registry, log=log)
    assert result == {"status": "denied", "reason": "forbidden"}
    assert "lina" in state["guilds"]["dawn"]["members"]


def test_kick_other_guild(impl, state, log):
    registry = impl.build_registry()
    result = impl.dispatch(state, "lina", '/guild kick "Mira"',
                           registry=registry, log=log)
    assert result == {"status": "denied", "reason": "forbidden"}
    assert "mira" in state["guilds"]["night"]["members"]


def test_disband_by_master(impl, state, log):
    registry = impl.build_registry()
    result = impl.dispatch(state, "lina", "/guild disband",
                           registry=registry, log=log)
    assert result == {"status": "ok", "reason": None}
    assert "dawn" not in state["guilds"]
    assert state["players"]["lina"]["guild"] is None
    assert state["players"]["marat"]["guild"] is None


def test_disband_by_officer_denied(impl, state, log):
    registry = impl.build_registry()
    result = impl.dispatch(state, "marat", "/guild disband",
                           registry=registry, log=log)
    assert result == {"status": "denied", "reason": "forbidden"}
    assert "dawn" in state["guilds"]


def test_unknown_command(impl, state, log):
    registry = impl.build_registry()
    result = impl.dispatch(state, "lina", "/foo bar", registry=registry, log=log)
    assert result == {"status": "denied", "reason": "unknown_command"}


def test_parse_error(impl, state, log):
    registry = impl.build_registry()
    result = impl.dispatch(state, "lina", "не команда", registry=registry, log=log)
    assert result == {"status": "denied", "reason": "parse_error"}


def test_bad_arguments(impl, state, log):
    registry = impl.build_registry()
    result = impl.dispatch(state, "lina", "/guild kick", registry=registry, log=log)
    assert result == {"status": "denied", "reason": "bad_arguments"}


def test_audit_logs_denied(impl, state, log):
    registry = impl.build_registry()
    impl.dispatch(state, "ada", '/guild kick "Marat"', registry=registry, log=log)
    assert len(log) == 1
    assert log[0]["sender"] == "ada"
    assert log[0]["raw"] == '/guild kick "Marat"'
    assert log[0]["status"] == "denied"
    assert log[0]["reason"] == "forbidden"
    assert log[0]["error"] is None


def test_one_log_entry_per_call(impl, state, log):
    registry = impl.build_registry()
    impl.dispatch(state, "lina", '/w "Sir Lancelot" привет', registry=registry, log=log)
    impl.dispatch(state, "lina", '/w "Sir Lancelot" ещё', registry=registry, log=log)
    assert len(log) == 2


def test_error_propagates(impl, state, log):
    def broken(state, sender):
        raise TypeError("boom")

    registry = {"broken": broken}
    with pytest.raises(TypeError):
        impl.dispatch(state, "lina", "/broken", registry=registry, log=log)
    assert len(log) == 1
    assert log[0]["status"] == "error"
    assert log[0]["error"] == "TypeError"


def test_decorator_order(impl, state, log):
    calls = []

    def probe(state, sender, raw, *, registry, log):
        calls.append(sender)
        return {"status": "ok", "reason": None}

    audit_outside = impl.audit(impl.requires_role("officer")(probe))
    role_outside = impl.requires_role("officer")(impl.audit(probe))

    log1 = []
    audit_outside(state, "ada", "/x", registry={}, log=log1)
    log2 = []
    role_outside(state, "ada", "/x", registry={}, log=log2)

    assert len(log1) == 1
    assert log1[0]["status"] == "denied"
    assert len(log2) == 0
    assert calls == []

    log3 = []
    audit_outside(state, "lina", "/x", registry={}, log=log3)
    log4 = []
    role_outside(state, "lina", "/x", registry={}, log=log4)

    assert calls == ["lina", "lina"]
    assert len(log3) == 1
    assert len(log4) == 1
