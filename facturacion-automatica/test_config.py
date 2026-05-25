"""
Verificá que todo esté configurado antes de ejecutar run.py.

Uso:  python test_config.py
"""

import sys

OK = "\033[92m✔\033[0m"
FAIL = "\033[91m✘\033[0m"


def check(label: str, fn):
    try:
        result = fn()
        print(f"  {OK}  {label}" + (f"  →  {result}" if result and result is not True else ""))
        return True
    except Exception as e:
        print(f"  {FAIL}  {label}  →  {e}")
        return False


def test_env() -> bool:
    from config import (
        AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET,
        USER_EMAIL, ANTHROPIC_API_KEY,
    )
    missing = [
        name for name, val in [
            ("AZURE_TENANT_ID", AZURE_TENANT_ID),
            ("AZURE_CLIENT_ID", AZURE_CLIENT_ID),
            ("AZURE_CLIENT_SECRET", AZURE_CLIENT_SECRET),
            ("USER_EMAIL", USER_EMAIL),
            ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY),
        ] if not val
    ]
    if missing:
        raise ValueError(f"Variables faltantes en .env: {', '.join(missing)}")
    return True


def test_auth() -> str:
    from auth import get_token
    token = get_token()
    return f"token OK ({len(token)} chars)"


def test_email() -> str:
    from auth import get_token
    from email_watcher import get_unread_oc_emails
    token = get_token()
    emails = get_unread_oc_emails(token)
    return f"{len(emails)} OC(s) sin leer en bandeja"


def test_anthropic() -> str:
    import anthropic
    from config import ANTHROPIC_API_KEY
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=5,
        messages=[{"role": "user", "content": "Responde: OK"}],
    )
    return msg.content[0].text.strip()


if __name__ == "__main__":
    print("\nVerificando configuración...\n")
    steps = [
        ("Variables de entorno (.env)", test_env),
        ("Autenticación Microsoft 365", test_auth),
        ("Acceso a buzón de correo",    test_email),
        ("Conexión con Anthropic API",  test_anthropic),
    ]
    results = []
    for label, fn in steps:
        ok = check(label, fn)
        results.append(ok)
        if not ok and label == "Variables de entorno (.env)":
            print("\n  Corregí el .env antes de continuar.\n")
            sys.exit(1)

    print()
    if all(results):
        print("Todo OK. Ejecutá:  python run.py\n")
    else:
        print("Corregí los errores y volvé a ejecutar este test.\n")
        sys.exit(1)
