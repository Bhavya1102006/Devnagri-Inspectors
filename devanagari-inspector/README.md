# Devanagari Transliteration Inspector

An NLP college project that converts Romanized Hindi and Marathi into Devanagari, checks words against a small dictionary, and offers spelling suggestions. The interface is called **Script Swapper Checker**.

## Setup

Requires Python 3.10 or newer.

```powershell
cd devanagari-inspector
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). To run the test suite:

```powershell
python -m pytest
```

Set `FLASK_DEBUG=1` to enable Flask debug mode during local development. Debug mode is off by default.

## Screenshot

![Application screenshot](docs/screenshot.png)

The screenshot can be captured after starting the application; the image is not included in this project bundle.

## Pipeline

1. **Preprocess:** lowercase words, separate punctuation at word boundaries, and skip empty tokens.
2. **Script detection:** retain words that already contain Devanagari characters.
3. **Dictionary check:** canonical entries are checked for the selected language. Known spellings from every dataset row resolve through the variant index.
4. **Transliteration:** unmatched words receive an ITRANS-to-Devanagari fallback, with a trailing halant removed.
5. **Suggestion:** `difflib.get_close_matches` searches canonical spellings at a configurable 0.6 cutoff and returns up to three scored matches.
6. **Output:** known and variant forms use stored Devanagari; a suggestion uses its best match; an unknown word uses the transliteration fallback.

With Auto selected, the language with more canonical or variant matches in the input is selected. Ties default to Hindi. Roman words use the Latin-script ITRANS transliteration convention for fallback conversion.

## Dataset

`data/roman_devanagari_words.csv` contains canonical word rows and known variants. Canonical rows build each language's spell-check dictionary; all valid rows build the direct variant lookup. `data/roman_devanagari_sentences.csv` supplies example phrases. Both files are read as UTF-8 with BOM support. The included CSVs are a compact, hand-made starter dataset for the required examples, not an exhaustive language resource. Missing or malformed required datasets produce a clear application/API error.

## Limitations

- The included word and sentence datasets are small and hand-made; coverage and spelling conventions are limited.
- ITRANS fallback is weak for everyday Hindi and cannot infer context reliably.
- Many Roman spellings are shared by Hindi and Marathi. Auto selection uses dictionary-match counts, not sentence-level language identification.
- Similarity suggestions are spelling-based and may be linguistically incorrect; review them before use.

## API

- `POST /api/transliterate` accepts `{"text": "mera naam", "language": "hi"}`. Language can be `hi`, `mr`, or `auto`; input is limited to 500 characters.
- `GET /api/examples` returns up to eight random dataset sentences.
- `GET /api/stats` returns canonical counts, variant counts, and category totals.