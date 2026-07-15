// Renders the shipment status doughnut chart on the dashboard.

document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementById("statusChart");
  if (!canvas || typeof Chart === "undefined") return;

  const stats = JSON.parse(canvas.dataset.stats || "{}");
  const labels = Object.keys(stats).map(s => s.replace("_", " "));
  const values = Object.values(stats);

  const palette = {
    "PENDING": "#6C8FC7",
    "IN TRANSIT": "#F2A93B",
    "DELIVERED": "#5BAE6B",
    "DELAYED": "#E0654F",
    "CANCELLED": "#5B6472",
  };
  const colors = labels.map(l => palette[l.toUpperCase()] || "#4FA8A0");

  new Chart(canvas.getContext("2d"), {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors,
        borderColor: "#1A222C",
        borderWidth: 3,
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: "#8B95A1",
            font: { family: "Inter", size: 11 },
            padding: 14,
            usePointStyle: true,
          },
        },
      },
      cutout: "68%",
    },
  });
});
