const status = document.querySelector("[data-pdf-status]");

document.querySelectorAll("[data-pdf-share]").forEach(button => {
  let file;

  fetch(button.dataset.u, {credentials: "same-origin"})
    .then(response => {
      if (!response.ok || !response.headers.get("content-type")?.includes("application/pdf")) {
        throw new Error("PDF request failed");
      }
      return response.blob();
    })
    .then(blob => {
      file = new File([blob], button.dataset.n, {type: "application/pdf"});
      const canShareFile = navigator.share && navigator.canShare && navigator.canShare({files: [file]});
      button.hidden = !canShareFile;
      status.textContent = canShareFile
        ? "PDF ready to share."
        : "PDF ready. Download it to save or attach on this device.";
    })
    .catch(() => {
      button.hidden = true;
      status.textContent = "Sharing could not prepare the PDF. Download PDF is available.";
    });

  button.addEventListener("click", async () => {
    if (!file || !navigator.share || !navigator.canShare || !navigator.canShare({files: [file]})) {
      status.textContent = "File sharing is unavailable. Use Download PDF instead.";
      return;
    }
    try {
      await navigator.share({files: [file], title: file.name});
    } catch (error) {
      if (error.name !== "AbortError") status.textContent = "Could not open sharing. Use Download PDF instead.";
    }
  });
});
