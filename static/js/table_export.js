(function () {
  "use strict";

  const CSV_SEPARATOR = ";";

  function sanitizeFileName(value) {
    return (value || "tableau")
      .toString()
      .trim()
      .toLowerCase()
      .replace(/\s+/g, "-")
      .replace(/[^a-z0-9\-_]/g, "") || "tableau";
  }

  function escapeCsvValue(value) {
    const text = (value ?? "").toString().replace(/\s+/g, " ").trim();
    const escaped = text.replace(/"/g, '""');
    return `"${escaped}"`;
  }

  function getRowsFromTable(table) {
    return Array.from(table.querySelectorAll("tr"))
      .map((row) => Array.from(row.querySelectorAll("th, td")).map((cell) => cell.innerText))
      .filter((cells) => cells.length > 0);
  }

  function buildCsvContent(rows) {
    return rows
      .map((cells) => cells.map((value) => escapeCsvValue(value)).join(CSV_SEPARATOR))
      .join("\n");
  }

  function downloadCsv(table) {
    const rows = getRowsFromTable(table);
    if (!rows.length) {
      return;
    }

    const csv = buildCsvContent(rows);
    const dateStamp = new Date().toISOString().slice(0, 10);
    const fileName = `${sanitizeFileName(table.dataset.csvFilename)}-${dateStamp}.csv`;
    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function createExportButton(table) {
    const controls = document.createElement("div");
    controls.className = "table-export-controls";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn btn-ghost table-export-btn";
    button.textContent = "Exporter en CSV";
    button.addEventListener("click", function () {
      downloadCsv(table);
    });

    controls.appendChild(button);
    return controls;
  }

  function mountExportButtons() {
    const tables = document.querySelectorAll("table");

    tables.forEach((table, index) => {
      if (table.dataset.csvExportReady === "true") {
        return;
      }

      if (!table.dataset.csvFilename) {
        table.dataset.csvFilename = `tableau-${index + 1}`;
      }

      const controls = createExportButton(table);
      table.parentElement.insertBefore(controls, table);
      table.dataset.csvExportReady = "true";
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountExportButtons);
  } else {
    mountExportButtons();
  }
})();
