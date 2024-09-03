import pytest

from examples.utils.markdown import escape_table_cell

test_cases = [
    ("Simple text", "Simple text"),
    ("Text with\nnew line", "Text with<br>new line"),
    (
        "```python\ndef foo():\n    pass\n```",
        "<pre>def foo():<br>    pass<br></pre>",
    ),
    (
        "```\ndef foo():\n    pass\n```",
        "<pre>def foo():<br>    pass<br></pre>",
    ),
    (
        "Text before\n```\ndef foo():\n    pass\n```\nText after",
        "Text before<br><pre>def foo():<br>    pass<br></pre>Text after",
    ),
    ("Text with inline ```code```", "Text with inline ```code```"),
    (
        "```\nmultiline code block\nwith text\n```",
        "<pre>multiline code block<br>with text<br></pre>",
    ),
    (
        "Text with\n```\ncode block\n```\nand text after",
        "Text with<br><pre>code block<br></pre>and text after",
    ),
    (
        "````\ncode block\nwith different backticks\n````",
        "````<br>code block<br>with different backticks<br>````",
    ),  # Incorrectly formatted code block
    (
        "Text with mixed ```code```\nand regular text",
        "Text with mixed ```code```<br>and regular text",
    ),
    (
        "```markdown\n# Heading\nThis is markdown code\n```",
        "<pre># Heading<br>This is markdown code<br></pre>",
    ),
    (
        "```\nUnclosed code block\n",
        "<pre>Unclosed code block<br>",
    ),  # Unclosed code block
]


@pytest.mark.parametrize("input_text, expected_output", test_cases)
def test_escape_table_cell(input_text, expected_output):
    assert escape_table_cell(input_text) == expected_output
