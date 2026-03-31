import nox

nox.options.reuse_existing_virtualenvs = True

SRC = ["aidial_interceptors_sdk", "tests", "noxfile.py"]


@nox.session
def lint(session: nox.Session):
    """Runs linters and fixers"""
    try:
        session.run("poetry", "install", "--with", "lint", external=True)
        session.run("poetry", "check", "--lock", "--strict", external=True)
        session.run("ruff", "check", *SRC)
        session.run("ruff", "format", "--check", *SRC)
        session.run("pyright", *SRC)
    except Exception:
        session.error(
            "linting has failed. Run 'make format' to fix formatting "
            "and fix other errors manually"
        )


@nox.session
def format(session: nox.Session):
    """Runs linters and fixers"""
    session.run("poetry", "install", "--only", "lint", external=True)
    session.run("ruff", "check", "--fix", *SRC)
    session.run("ruff", "format", *SRC)


@nox.session(python=["3.11", "3.12"])
# Testing against earliest and latest supported versions of the dependencies
@nox.parametrize("pydantic", ["1.10.17", "2.8.2"])
@nox.parametrize("httpx", ["0.25.0", "0.27.0"])
def test(session: nox.Session, pydantic: str, httpx: str) -> None:
    """Runs tests"""
    session.run("poetry", "install", "--all-extras", external=True)
    session.install(f"pydantic=={pydantic}")
    session.install(f"httpx=={httpx}")
    session.run("pytest", "tests/unit_tests/")


@nox.session
def integration_tests(session: nox.Session):
    session.run("pytest", "tests/integration_tests/")
