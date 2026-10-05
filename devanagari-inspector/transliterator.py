"""Dataset-backed Romanized Hindi/Marathi transliteration and spell checking."""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any

import pandas as pd
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate


DATA_DIR = Path(__file__).resolve().parent / "data"
SUGGESTION_CUTOFF = 0.6
PUNCTUATION = ".,!;:\"'()"
DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097f]")
REQUIRED_WORD_COLUMNS = {
    "roman_input", "devanagari", "canonical_roman", "language", "is_canonical", "category"
}


class DatasetError(RuntimeError):
    """Raised when the required project CSV datasets are unavailable or invalid."""


_DICTIONARIES: dict[str, dict[str, str]] = {}
_VARIANTS: dict[str, dict[str, tuple[str, str]]] = {}


def load_datasets() -> None:
    """Load word and sentence CSVs, building canonical and variant lookups."""
    words_path = DATA_DIR / "roman_devanagari_words.csv"
    sentences_path = DATA_DIR / "roman_devanagari_sentences.csv"
    missing = [path.name for path in (words_path, sentences_path) if not path.is_file()]
    if missing:
        raise DatasetError("Required dataset file(s) missing from data/: " + ", ".join(missing))

    try:
        words = pd.read_csv(words_path, encoding="utf-8-sig", dtype=str).fillna("")
        pd.read_csv(sentences_path, encoding="utf-8-sig")
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        raise DatasetError(f"Could not read dataset CSV: {error}") from error

    missing_columns = REQUIRED_WORD_COLUMNS - set(words.columns)
    if missing_columns:
        raise DatasetError("Word dataset is missing columns: " + ", ".join(sorted(missing_columns)))

    dictionaries: dict[str, dict[str, str]] = {"hi": {}, "mr": {}}
    variants: dict[str, dict[str, tuple[str, str]]] = {"hi": {}, "mr": {}}
    for row in words.to_dict("records"):
        language = row["language"].strip().lower()
        roman_input = row["roman_input"].strip().lower()
        canonical_roman = row["canonical_roman"].strip().lower()
        devanagari = row["devanagari"].strip()
        if language not in dictionaries or not roman_input or not devanagari or not canonical_roman:
            continue
        variants[language][roman_input] = (devanagari, canonical_roman)
        if row["is_canonical"].strip().lower() == "true":
            dictionaries[language][canonical_roman] = devanagari

    _DICTIONARIES.clear()
    _DICTIONARIES.update(dictionaries)
    _VARIANTS.clear()
    _VARIANTS.update(variants)


def _require_datasets() -> None:
    if not _DICTIONARIES:
        load_datasets()


def _parts(token: str) -> tuple[str, str, str]:
    """Return leading punctuation, normalized word, and trailing punctuation."""
    normalized = token.lower().strip(PUNCTUATION)
    if not normalized:
        return token, "", ""
    leading_count = len(token) - len(token.lstrip(PUNCTUATION))
    trailing_count = len(token) - len(token.rstrip(PUNCTUATION))
    leading = token[:leading_count]
    trailing = token[len(token) - trailing_count:] if trailing_count else ""
    return leading, normalized, trailing


def _fallback(word: str) -> str:
    """Transliterate ITRANS text and suppress a final inherent-vowel halant."""
    try:
        converted = transliterate(word, sanscript.ITRANS, sanscript.DEVANAGARI)
    except (ValueError, KeyError):
        converted = word
    return converted.removesuffix("\u094d")


def _auto_language(words: list[str]) -> str:
    """Choose the language with more known canonical or variant matches."""
    scores = {
        language: sum(
            word in _DICTIONARIES[language] or word in _VARIANTS[language]
            for word in words
        )
        for language in ("hi", "mr")
    }
    return "mr" if scores["mr"] > scores["hi"] else "hi"


def _suggestions(word: str, language: str) -> list[dict[str, Any]]:
    keys = list(_DICTIONARIES[language])
    matches = difflib.get_close_matches(
        word, keys, n=3, cutoff=SUGGESTION_CUTOFF
    )
    return [
        {
            "roman": match,
            "devanagari": _DICTIONARIES[language][match],
            "score": difflib.SequenceMatcher(None, word, match).ratio(),
        }
        for match in matches
    ]


def inspect_text(text: str, language: str = "auto") -> dict[str, Any]:
    """Inspect Romanized text and return word-level results and the final sentence."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Please enter some text to convert.")
    if len(text) > 500:
        raise ValueError("Text must be 500 characters or fewer.")
    if language not in {"hi", "mr", "auto"}:
        raise ValueError("Language must be auto, hi, or mr.")
    _require_datasets()

    token_parts = [_parts(token) for token in text.split()]
    normalized_words = [word for _, word, _ in token_parts if word]
    selected_language = _auto_language(normalized_words) if language == "auto" else language
    results: list[dict[str, Any]] = []
    output_tokens: list[str] = []
    correct = corrected = unknown = 0

    for token, (leading, word, trailing) in zip(text.split(), token_parts):
        if not word:
            continue
        original_devanagari = bool(DEVANAGARI_PATTERN.search(word))
        suggestions: list[dict[str, Any]] = []
        suggestion = ""
        if original_devanagari:
            status = "already_devanagari"
            devanagari = word
            final_word = word
        elif word in _DICTIONARIES[selected_language]:
            status = "correct"
            devanagari = _DICTIONARIES[selected_language][word]
            final_word = devanagari
        elif word in _VARIANTS[selected_language]:
            devanagari, canonical = _VARIANTS[selected_language][word]
            status = "variant"
            suggestion = canonical
            final_word = devanagari
        else:
            devanagari = _fallback(word)
            suggestions = _suggestions(word, selected_language)
            if suggestions:
                status = "suggestion"
                suggestion = suggestions[0]["roman"]
                final_word = suggestions[0]["devanagari"]
            else:
                status = "unknown"
                final_word = devanagari

        if status == "correct":
            correct += 1
        elif status in {"variant", "suggestion"}:
            corrected += 1
        elif status == "unknown":
            unknown += 1

        final_token = leading + final_word + trailing
        output_tokens.append(final_token)
        results.append({
            "original": token,
            "roman": word,
            "devanagari": devanagari,
            "status": status,
            "suggestion": suggestion,
            "suggestions": suggestions,
            "final_word": final_token,
            "language": selected_language,
        })

    total = len(results)
    note = (
        "Dictionary matches are high confidence; unknown words use ITRANS transliteration."
        if unknown else "All words matched a dictionary entry or a known spelling variant."
    )
    return {
        "words": results,
        "final_sentence": " ".join(output_tokens),
        "language": selected_language,
        "summary": {
            "total_words": total,
            "correct": correct,
            "corrected": corrected,
            "unknown": unknown,
        },
        "confidence_note": note,
    }