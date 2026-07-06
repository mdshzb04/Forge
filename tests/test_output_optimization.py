"""Tests for the Forge Output Optimization Layer."""

from __future__ import annotations

from forgecli.optimizer.output.optimizer import OutputOptimizer


def test_output_optimizer_off() -> None:
    optimizer = OutputOptimizer(intensity="off")
    raw_text = "line 1\n\n\nline 2\nline 2\n"
    assert optimizer.optimize(raw_text) == raw_text


def test_output_optimizer_lite_collapse_duplicates() -> None:
    optimizer = OutputOptimizer(intensity="lite")
    raw_text = "building...\nbuilding...\nbuilding...\nsuccess!"
    expected = "building... [repeated 3 times]\nsuccess!"
    assert optimizer.optimize(raw_text) == expected


def test_output_optimizer_lite_empty_lines() -> None:
    optimizer = OutputOptimizer(intensity="lite")
    raw_text = "line 1\n\n\n\nline 2\n\nline 3"
    expected = "line 1\n\nline 2\n\nline 3"
    assert optimizer.optimize(raw_text) == expected


def test_output_optimizer_lite_progress_compress() -> None:
    optimizer = OutputOptimizer(intensity="lite")
    raw_text = (
        "Downloading file.zip\n"
        "[  5%] -> speed: 100kb/s\n"
        "[ 20%] -> speed: 120kb/s\n"
        "[ 80%] -> speed: 130kb/s\n"
        "[100%] -> speed: 90kb/s\n"
        "Finished download"
    )
    expected = (
        "Downloading file.zip\n"
        "[  5%] -> speed: 100kb/s\n"
        "  [... collapsed 2 progress updates ...]\n"
        "[100%] -> speed: 90kb/s\n"
        "Finished download"
    )
    assert optimizer.optimize(raw_text) == expected


def test_output_optimizer_full_warnings_grouping() -> None:
    optimizer = OutputOptimizer(intensity="full")
    raw_text = (
        "dep_warning: line 10: deprecated\n"
        "dep_warning: line 20: deprecated\n"
        "dep_warning: line 30: deprecated"
    )
    # The warning normalization replaces digits with N, so they match and group
    expected = "dep_warning: line N: deprecated [repeated 3 times]"
    assert optimizer.optimize(raw_text) == expected


def test_output_optimizer_full_tests_compression() -> None:
    optimizer = OutputOptimizer(intensity="full")
    raw_text = (
        "tests/test_foo.py::test_one PASSED\n"
        "tests/test_foo.py::test_two PASSED\n"
        "tests/test_foo.py::test_three PASSED\n"
        "tests/test_foo.py::test_four FAILED\n"
        "tests/test_foo.py::test_five PASSED"
    )
    # The first 3 PASSED tests should collapse, FAILED is kept, last PASSED is kept
    expected = (
        "  [... 3 successful tests collapsed ...]\n"
        "tests/test_foo.py::test_three PASSED\n"
        "tests/test_foo.py::test_four FAILED\n"
        "tests/test_foo.py::test_five PASSED"
    )
    assert optimizer.optimize(raw_text) == expected


def test_output_optimizer_ultra_successful() -> None:
    optimizer = OutputOptimizer(intensity="ultra")
    raw_text = (
        "Starting build...\n"
        "Step 1/3: init\n"
        "Step 2/3: compile\n"
        "Step 3/3: test\n"
        "Build finished successfully.\n"
        "Done."
    )
    expected = "[Success] Command executed successfully. Collapsed 6 lines of output."
    assert optimizer.optimize(raw_text) == expected


def test_output_optimizer_ultra_failures_intact() -> None:
    optimizer = OutputOptimizer(intensity="ultra")
    raw_text = (
        "Starting build...\n"
        "Step 1/3: init\n"
        "compiler error: file.py line 45: SyntaxError\n"
        "    def foo() -> None\n"
        "                     ^\n"
        "Step 2/3: failed compiling\n"
        "Done."
    )
    # Compiler error and its trace (indented lines) must be kept fully intact,
    # and surrounding successful lines are collapsed.
    assert "compiler error: file.py line 45: SyntaxError" in optimizer.optimize(raw_text)
    assert "def foo() -> None" in optimizer.optimize(raw_text)
    assert "collapsed" in optimizer.optimize(raw_text)
