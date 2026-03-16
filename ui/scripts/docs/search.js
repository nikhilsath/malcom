// Documentation Search page controller

const form = document.getElementById("docs-search-form");
const resultsContainer = document.getElementById("docs-search-results");

if (form) {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = document.getElementById("docs-search-query-input")?.value.trim() || "";

    if (!resultsContainer) {
      return;
    }

    if (!query) {
      resultsContainer.textContent = "";
      return;
    }

    resultsContainer.textContent = `No results found for "${query}".`;
  });
}
