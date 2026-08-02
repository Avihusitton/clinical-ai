import pytest
from evaluation.wave9.run_wave9_4r_closure import extract_bundle_section, normalize_marker_path, normalize_text

def make_bundle(lines, line_ending='\n'):
    """Utility to create a bundle string from a list of lines using specified line ending."""
    return line_ending.join(lines) + line_ending


def test_forward_slash_marker_extraction():
    bundle = make_bundle([
        "BEGIN FILE: tests/example.py",
        "content line1",
        "content line2",
        "END FILE: tests/example.py",
    ])
    result = extract_bundle_section(bundle, "tests/example.py")
    assert result["success"] is True
    assert result["begin_line"] == 1
    assert result["end_line"] == 4
    assert result["raw_content"] == "content line1\ncontent line2\n"

def test_backslash_marker_extraction():
    bundle = make_bundle([
        "BEGIN FILE: tests\\example.py",
        "line A",
        "line B",
        "END FILE: tests\\example.py",
    ])
    result = extract_bundle_section(bundle, "tests/example.py")
    assert result["success"] is True
    assert result["raw_content"] == "line A\nline B\n"

def test_missing_begin_marker():
    bundle = make_bundle([
        "END FILE: tests/missing.py",
    ])
    result = extract_bundle_section(bundle, "tests/missing.py")
    assert result["success"] is False
    assert result["failure_reason"] == "Incorrect number of begin markers"

def test_missing_end_marker():
    bundle = make_bundle([
        "BEGIN FILE: tests/missing.py",
        "some content",
    ])
    result = extract_bundle_section(bundle, "tests/missing.py")
    assert result["success"] is False
    assert result["failure_reason"] == "Incorrect number of end markers"

def test_duplicate_begin_markers():
    bundle = make_bundle([
        "BEGIN FILE: tests/dup.py",
        "content1",
        "END FILE: tests/dup.py",
        "BEGIN FILE: tests/dup.py",
        "content2",
        "END FILE: tests/dup.py",
    ])
    result = extract_bundle_section(bundle, "tests/dup.py")
    assert result["success"] is False
    assert result["failure_reason"] == "Incorrect number of begin markers"

def test_mismatched_end_path():
    bundle = make_bundle([
        "BEGIN FILE: tests/a.py",
        "data",
        "END FILE: tests/b.py",
    ])
    result = extract_bundle_section(bundle, "tests/a.py")
    assert result["success"] is False
    assert result["failure_reason"] == "Incorrect number of end markers"

def test_nested_begin_marker_before_end():
    bundle = make_bundle([
        "BEGIN FILE: tests/nested.py",
        "inner line",
        "BEGIN FILE: tests/nested.py",
        "more",
        "END FILE: tests/nested.py",
        "END FILE: tests/nested.py",
    ])
    result = extract_bundle_section(bundle, "tests/nested.py")
    assert result["success"] is False
    assert result["failure_reason"] == "Incorrect number of begin markers"

def test_empty_section():
    bundle = make_bundle([
        "BEGIN FILE: tests/empty.py",
        "END FILE: tests/empty.py",
    ])
    result = extract_bundle_section(bundle, "tests/empty.py")
    assert result["success"] is False
    assert result["failure_reason"] == "Empty content"

def test_content_preservation_without_strip():
    bundle = make_bundle([
        "BEGIN FILE: tests/preserve.py",
        "   spaced line   ",
        "\tTabbed line\t",
        "END FILE: tests/preserve.py",
    ], line_ending='\r\n')
    result = extract_bundle_section(bundle, "tests/preserve.py")
    assert result["success"] is True
    expected = "   spaced line   \r\n\tTabbed line\t\r\n"
    assert result["raw_content"] == expected

def test_separator_after_begin_excluded():
    bundle = make_bundle([
        "BEGIN FILE: tests/sep_after_begin.py",
        "====================================================================================================",
        "actual line 1",
        "actual line 2",
        "END FILE: tests/sep_after_begin.py",
    ])
    result = extract_bundle_section(bundle, "tests/sep_after_begin.py")
    assert result["success"] is True
    assert result["begin_framing_removed"] is True
    assert result["end_framing_removed"] is False
    assert result["framing_lines_removed"] is True
    assert result["raw_content"] == "actual line 1\nactual line 2\n"

def test_separator_before_end_excluded():
    bundle = make_bundle([
        "BEGIN FILE: tests/sep_before_end.py",
        "actual line 1",
        "actual line 2",
        "----------------------------------------------------------------------------------------------------",
        "END FILE: tests/sep_before_end.py",
    ])
    result = extract_bundle_section(bundle, "tests/sep_before_end.py")
    assert result["success"] is True
    assert result["begin_framing_removed"] is False
    assert result["end_framing_removed"] is True
    assert result["framing_lines_removed"] is True
    assert result["raw_content"] == "actual line 1\nactual line 2\n"

def test_separator_inside_source_content_preserved():
    bundle = make_bundle([
        "BEGIN FILE: tests/sep_inside.py",
        "====================================================================================================",
        "def foo():",
        "    # ==========================================",
        "    return 42",
        "END FILE: tests/sep_inside.py",
    ])
    result = extract_bundle_section(bundle, "tests/sep_inside.py")
    assert result["success"] is True
    assert result["begin_framing_removed"] is True
    assert result["end_framing_removed"] is False
    assert result["raw_content"] == "def foo():\n    # ==========================================\n    return 42\n"

def test_no_separator_bundle_remains_unchanged():
    bundle = make_bundle([
        "BEGIN FILE: tests/nosep.py",
        "import os",
        "print('hello')",
        "END FILE: tests/nosep.py",
    ])
    result = extract_bundle_section(bundle, "tests/nosep.py")
    assert result["success"] is True
    assert result["begin_framing_removed"] is False
    assert result["end_framing_removed"] is False
    assert result["framing_lines_removed"] is False
    assert result["raw_content"] == "import os\nprint('hello')\n"

def test_crlf_and_lf_behavior():
    lines = [
        "BEGIN FILE: tests/crlf.py",
        "==========================",
        "line 1",
        "line 2",
        "END FILE: tests/crlf.py",
    ]
    bundle_lf = make_bundle(lines, line_ending='\n')
    bundle_crlf = make_bundle(lines, line_ending='\r\n')

    res_lf = extract_bundle_section(bundle_lf, "tests/crlf.py")
    res_crlf = extract_bundle_section(bundle_crlf, "tests/crlf.py")

    assert res_lf["success"] is True
    assert res_crlf["success"] is True

    assert res_lf["begin_framing_removed"] is True
    assert res_crlf["begin_framing_removed"] is True

    assert res_lf["raw_content"] == "line 1\nline 2\n"
    assert res_crlf["raw_content"] == "line 1\r\nline 2\r\n"

def test_normalize_text_no_final_newline():
    assert normalize_text("abc\ndef") == "abc\ndef\n"

def test_normalize_text_one_final_newline():
    assert normalize_text("abc\ndef\n") == "abc\ndef\n"

def test_normalize_text_two_final_newlines():
    assert normalize_text("abc\ndef\n\n") == "abc\ndef\n"

def test_normalize_text_multiple_internal_blank_lines():
    input_text = "line1\n\n\nline2\n\nline3\n\n\n"
    expected = "line1\n\n\nline2\n\nline3\n"
    assert normalize_text(input_text) == expected

def test_normalize_text_crlf_input():
    assert normalize_text("line1\r\nline2\r\n\r\n") == "line1\nline2\n"

def test_normalize_text_utf8_bom():
    assert normalize_text("\ufeffline1\nline2\n") == "line1\nline2\n"
