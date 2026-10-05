"use strict";

const input = document.getElementById("roman-input");
const convertButton = document.getElementById("convert-button");
const errorMessage = document.getElementById("error-message");
const resultsSection = document.getElementById("results");
let currentResult = null;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function setError(message) {
  errorMessage.textContent = message;
  errorMessage.hidden = !message;
}

function setLoading(loading) {
  convertButton.disabled = loading;
  convertButton.classList.toggle("is-loading", loading);
  convertButton.querySelector(".button-label").textContent = loading ? "Checking…" : "Convert & Check";
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "The request could not be completed.");
  return payload;
}

function updateOutput() {
  document.getElementById("output-sentence").textContent = currentResult.words
    .map((word) => word.final_word).join(" ");
}

function renderSummary(summary) {
  const bar = document.getElementById("summary-bar");
  bar.replaceChildren();
  [["total_words", "Total words"], ["correct", "Correct"], ["corrected", "Corrected"], ["unknown", "Unknown"]]
    .forEach(([key, label]) => {
      const item = element("div", "summary-item");
      item.append(element("strong", "summary-value", String(summary[key])));
      item.append(element("span", "summary-label", label));
      bar.append(item);
    });
}

function renderWords(words) {
  const body = document.getElementById("word-results");
  body.replaceChildren();
  words.forEach((word, index) => {
    const row = document.createElement("tr");
    row.append(element("td", "", word.original));
    row.append(element("td", "deva-cell", word.devanagari));
    const statusCell = document.createElement("td");
    statusCell.append(element("span", `status-badge status-${word.status}`, word.status.replaceAll("_", " ")));
    row.append(statusCell);
    const suggestionCell = document.createElement("td");
    if (word.status === "suggestion" && word.suggestions.length) {
      const top = word.suggestions[0];
      suggestionCell.append(element("span", "suggestion-copy", `Did you mean: ${top.roman} → `));
      suggestionCell.append(element("span", "suggestion-deva", top.devanagari));
      const accept = element("button", "accept-button", "Accept");
      accept.type = "button";
      accept.setAttribute("aria-label", `Accept ${top.roman} for ${word.original}`);
      accept.addEventListener("click", () => {
        currentResult.words[index].final_word = word.final_word.replace(word.devanagari, top.devanagari);
        word.status = "suggestion";
        accept.textContent = "Accepted";
        accept.disabled = true;
        updateOutput();
      });
      suggestionCell.append(accept);
    } else if (word.status === "variant" && word.suggestion) {
      suggestionCell.append(element("span", "suggestion-copy", `Did you mean: ${word.suggestion} → `));
      suggestionCell.append(element("span", "suggestion-deva", word.devanagari));
    } else if (word.status === "unknown") {
      suggestionCell.append(element("span", "suggestion-copy", "No close dictionary match"));
    } else {
      suggestionCell.append(element("span", "suggestion-copy", "—"));
    }
    row.append(suggestionCell);
    body.append(row);
  });
}

function renderHighlightedInput(words) {
  const target = document.getElementById("highlighted-input");
  target.replaceChildren();
  words.forEach((word, index) => {
    if (index) target.append(document.createTextNode(" "));
    const span = element("span", ["variant", "suggestion", "unknown"].includes(word.status) ? "highlight-word" : "", word.original);
    target.append(span);
  });
}

async function convertText() {
  setError("");
  if (!input.value.trim()) {
    setError("Add a Hindi or Marathi phrase first, then convert it.");
    input.focus();
    return;
  }
  setLoading(true);
  try {
    currentResult = await requestJson("/api/transliterate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: input.value, language: document.getElementById("language-select").value }),
    });
    updateOutput();
    renderSummary(currentResult.summary);
    renderWords(currentResult.words);
    renderHighlightedInput(currentResult.words);
    document.getElementById("confidence-note").textContent = currentResult.confidence_note;
    resultsSection.hidden = false;
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    setError(error.message || "Something went wrong. Please try again.");
  } finally {
    setLoading(false);
  }
}

async function loadExamples() {
  const container = document.getElementById("example-chips");
  try {
    const examples = await requestJson("/api/examples");
    container.replaceChildren();
    examples.forEach((example) => {
      const chip = element("button", "example-chip", example.roman_sentence);
      chip.type = "button";
      chip.addEventListener("click", () => {
        input.value = example.roman_sentence;
        input.dispatchEvent(new Event("input"));
        input.focus();
      });
      container.append(chip);
    });
  } catch (error) {
    container.replaceChildren(element("span", "muted-copy", error.message));
  }
}

async function loadStats() {
  const container = document.getElementById("dataset-stats");
  try {
    const stats = await requestJson("/api/stats");
    container.replaceChildren();
    const entries = [
      [stats.words_per_language.hi || 0, "Hindi canonical words"],
      [stats.words_per_language.mr || 0, "Marathi canonical words"],
      [Object.values(stats.variants_per_language).reduce((sum, count) => sum + count, 0), "Known variants"],
      [stats.total_entries || 0, "Total word entries"],
    ];
    entries.forEach(([count, label]) => {
      const tile = element("div", "stat-tile");
      tile.append(element("strong", "", String(count)));
      tile.append(element("span", "", label));
      container.append(tile);
    });
  } catch (error) {
    container.replaceChildren(element("span", "muted-copy", error.message));
  }
}

convertButton.addEventListener("click", convertText);
document.getElementById("clear-button").addEventListener("click", () => {
  input.value = "";
  input.dispatchEvent(new Event("input"));
  input.focus();
  setError("");
});
document.getElementById("copy-button").addEventListener("click", async (event) => {
  if (!currentResult) return;
  try {
    await navigator.clipboard.writeText(document.getElementById("output-sentence").textContent);
    event.currentTarget.textContent = "Copied";
    window.setTimeout(() => { event.currentTarget.textContent = "Copy output"; }, 1400);
  } catch (_error) {
    setError("Clipboard access is unavailable in this browser.");
  }
});
input.addEventListener("input", () => {
  document.getElementById("character-count").textContent = `${input.value.length} / 500`;
});
input.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") convertText();
});

loadExamples();
loadStats();