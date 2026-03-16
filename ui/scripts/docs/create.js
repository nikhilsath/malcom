// Documentation Create page controller

const form = document.getElementById("docs-create-form");
const feedback = document.getElementById("docs-create-form-feedback");

if (form) {
  form.addEventListener("submit", (event) => {
    event.preventDefault();

    if (!feedback) {
      return;
    }

    feedback.textContent = "Documentation entry saved.";
    feedback.className = "api-form-feedback api-form-feedback--success";
    form.reset();
  });
}
