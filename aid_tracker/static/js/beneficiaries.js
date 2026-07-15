// Shows/hides subtype-specific fields depending on the selected beneficiary type.

document.addEventListener("DOMContentLoaded", () => {
  const typeSelect = document.getElementById("beneficiaryType");
  if (!typeSelect) return;

  const fields = document.querySelectorAll(".subtype-field");

  function syncFields() {
    const selected = typeSelect.value;
    fields.forEach(field => {
      const matches = field.dataset.type === selected;
      field.hidden = !matches;
      field.querySelectorAll("input, select").forEach(input => {
        input.disabled = !matches;
      });
    });
  }

  typeSelect.addEventListener("change", syncFields);
  syncFields();
});
