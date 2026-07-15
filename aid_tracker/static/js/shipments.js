// Lets the user add or remove cargo item rows when building a shipment.

document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("itemRows");
  const addBtn = document.getElementById("addItemRow");
  if (!container || !addBtn) return;

  addBtn.addEventListener("click", () => {
    const firstRow = container.querySelector(".item-row");
    const clone = firstRow.cloneNode(true);
    clone.querySelectorAll("input").forEach(input => (input.value = ""));
    clone.querySelector("select").selectedIndex = 0;
    container.appendChild(clone);
  });

  container.addEventListener("click", (e) => {
    if (e.target.classList.contains("remove-row")) {
      const rows = container.querySelectorAll(".item-row");
      if (rows.length > 1) {
        e.target.closest(".item-row").remove();
      }
    }
  });
});
