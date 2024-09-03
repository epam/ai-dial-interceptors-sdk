from pathlib import Path


def generate_response_message_handler():
    base_path = Path("aidial_interceptors_sdk/chat_completion/")

    source = base_path / "request_message_handler.py"
    target = base_path / "response_message_handler.py"

    if not source.exists():
        raise RuntimeError(f"{source!r} does not exist")

    source_content = source.read_text()
    target_content = (
        source_content.replace("request", "response")
        .replace("Request", "Response")
        .lstrip()
    )

    prelude = (
        '"""\n'
        f"CODE-GENERATED from {source} module.\n"
        "DO NOT MODIFY THIS FILE.\n"
    )

    if target_content.startswith('"""'):
        target_content = prelude + target_content[len('"""') :]
    else:
        target_content = prelude + '"""\n\n' + target_content

    target.write_text(target_content)

    print(f"Generated  : {target}")
    print(f"From source: {source}")


def main():
    print("Running code generation...")
    generate_response_message_handler()


if __name__ == "__main__":
    main()
