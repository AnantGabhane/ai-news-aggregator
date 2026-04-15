import sys
from importlib.machinery import PathFinder
from importlib.util import module_from_spec
from pathlib import Path


SERVICES_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SERVICES_DIR.parent.parent


def _without_services_dir() -> list[str]:
    return [
        entry
        for entry in sys.path
        if Path(entry or ".").resolve() != SERVICES_DIR
    ]


def _load_stdlib_email() -> None:
    spec = PathFinder.find_spec("email", _without_services_dir())
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError("Could not locate Python's stdlib 'email' package")

    module = module_from_spec(spec)
    sys.modules[__name__] = module
    spec.loader.exec_module(module)


if __name__ == "email":
    _load_stdlib_email()
else:
    if __name__ == "__main__":
        # Running this file directly would otherwise shadow Python's stdlib
        # `email` package because the script lives at `app/services/email.py`.
        sys.path[:] = _without_services_dir()
        sys.path.insert(0, str(PROJECT_ROOT))

    from app.services.mailer import digest_to_html, markdown_to_html, send_email, send_email_to_self

    __all__ = [
        "digest_to_html",
        "markdown_to_html",
        "send_email",
        "send_email_to_self",
    ]

    if __name__ == "__main__":
        send_email_to_self("Test from Python", "Hello from my script.")
