def decapitalize(s: str) -> str:
    if not s:
        return s
    return s[0].lower() + s[1:]
