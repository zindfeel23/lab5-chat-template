"""Готовый парсер. В решении лабы этот файл менять нельзя."""


class ParseError(ValueError):
    """Строка не соответствует формату команды."""


def _token(raw, start):
    while start < len(raw) and raw[start].isspace():
        start += 1
    if start == len(raw):
        return None, start
    if raw[start] != '"':
        end = start
        while end < len(raw) and not raw[end].isspace():
            if raw[end] == '"':
                raise ParseError("кавычки должны окружать весь аргумент")
            end += 1
        return raw[start:end], end
    chars = []
    pos = start + 1
    while pos < len(raw):
        char = raw[pos]
        if char == '"':
            end = pos + 1
            if end < len(raw) and not raw[end].isspace():
                raise ParseError("после закрывающей кавычки нужен пробел")
            return "".join(chars), end
        if char == "\\" and pos + 1 < len(raw) and raw[pos + 1] in ('"', "\\"):
            pos += 1
            char = raw[pos]
        chars.append(char)
        pos += 1
    raise ParseError("незакрытая кавычка")


def parse_command(raw):
    """Вернуть (имя команды, кортеж строковых аргументов).

    После получателя /w ровно один пробельный символ отделяет текст.
    Всё после него, включая остальные пробелы, возвращается без изменений.
    """
    if not raw.lstrip().startswith("/"):
        raise ParseError("команда должна начинаться со слэша")
    command, end = _token(raw, 0)
    if command is None or not command.startswith("/") or command == "/":
        raise ParseError("команда должна начинаться со слэша")
    command = command[1:]
    if command == "guild":
        subcommand, end = _token(raw, end)
        if subcommand is not None:
            command += " " + subcommand
    if command == "w":
        target, end = _token(raw, end)
        if target is None:
            return command, ()
        if end == len(raw):
            return command, (target,)
        return command, (target, raw[end + 1:])
    args = []
    while True:
        arg, end = _token(raw, end)
        if arg is None:
            return command, tuple(args)
        args.append(arg)
