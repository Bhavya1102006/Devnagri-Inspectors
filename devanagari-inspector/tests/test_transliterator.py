"""Tests for dataset-backed transliteration and spelling inspection."""

import pytest

from transliterator import inspect_text


def test_required_hindi_sentences():
    result = inspect_text("mera naam shardul hai", "hi")
    assert result["final_sentence"] == "मेरा नाम शार्दुल है"

    result = inspect_text("bharat ek sundar desh hai", "hi")
    assert result["final_sentence"] == "भारत एक सुंदर देश है"


@pytest.mark.parametrize(
    ("word", "expected"),
    [("namste", "नमस्ते"), ("krushna", "कृष्ण")],
)
def test_known_variants(word, expected):
    result = inspect_text(word, "hi")
    assert result["final_sentence"] == expected
    assert result["words"][0]["status"] == "variant"


def test_punctuation_is_preserved():
    result = inspect_text("hai.", "hi")
    assert result["final_sentence"] == "है."


def test_devanagari_is_unchanged():
    result = inspect_text("नमस्ते hai", "hi")
    assert result["final_sentence"] == "नमस्ते है"
    assert result["words"][0]["status"] == "already_devanagari"


def test_empty_input_returns_an_error():
    with pytest.raises(ValueError, match="enter some text"):
        inspect_text("   ", "hi")


def test_nahi_uses_selected_language_dictionary():
    assert inspect_text("nahi", "hi")["final_sentence"] == "नहीं"
    assert inspect_text("nahi", "mr")["final_sentence"] == "नाही"


def test_auto_prefers_language_with_more_dictionary_matches():
    result = inspect_text("majha naav shardul aahe", "auto")
    assert result["language"] == "mr"


def test_unknown_word_uses_fallback():
    result = inspect_text("xyzzy", "hi")
    assert result["words"][0]["status"] == "unknown"
    assert result["summary"]["unknown"] == 1