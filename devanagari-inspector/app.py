"""Flask application for the Devanagari Transliteration Inspector."""

import os
import random

import pandas as pd
from flask import Flask, jsonify, render_template, request

from transliterator import DatasetError, DATA_DIR, inspect_text, load_datasets


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
    try:
        load_datasets()
        app.config["DATASET_ERROR"] = None
    except DatasetError as error:
        app.config["DATASET_ERROR"] = str(error)

    @app.get("/")
    def index():
        return render_template("index.html", dataset_error=app.config["DATASET_ERROR"])

    @app.post("/api/transliterate")
    def transliterate_route():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Send a JSON object with text and language."}), 400

        text = payload.get("text")
        language = payload.get("language", "auto")
        if not isinstance(text, str) or not text.strip():
            return jsonify({"error": "Please enter some text to convert."}), 400
        if len(text) > 500:
            return jsonify({"error": "Text must be 500 characters or fewer."}), 400
        if language not in {"hi", "mr", "auto"}:
            return jsonify({"error": "Language must be auto, hi, or mr."}), 400

        try:
            return jsonify(inspect_text(text, language))
        except DatasetError as error:
            return jsonify({"error": str(error)}), 503
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

    @app.get("/api/examples")
    def examples_route():
        try:
            sentence_path = DATA_DIR / "roman_devanagari_sentences.csv"
            sentences = pd.read_csv(sentence_path, encoding="utf-8-sig").to_dict("records")
            return jsonify(random.sample(sentences, min(8, len(sentences))))
        except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
            return jsonify({"error": f"Could not load example sentences: {error}"}), 503

    @app.get("/api/stats")
    def stats_route():
        try:
            words_path = DATA_DIR / "roman_devanagari_words.csv"
            words = pd.read_csv(words_path, encoding="utf-8-sig", dtype=str).fillna("")
            canonical = words[words["is_canonical"].str.lower() == "true"]
            variants = words[words["is_canonical"].str.lower() != "true"]
            return jsonify({
                "words_per_language": canonical.groupby("language")["canonical_roman"].nunique().to_dict(),
                "variants_per_language": variants.groupby("language").size().to_dict(),
                "categories": words["category"].value_counts().to_dict(),
                "total_entries": int(len(words)),
            })
        except (OSError, KeyError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
            return jsonify({"error": f"Could not load dataset statistics: {error}"}), 503

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "The requested resource was not found."}), 404

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({"error": "Request body is too large."}), 413

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify({"error": "An unexpected server error occurred."}), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")