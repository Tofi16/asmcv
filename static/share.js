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
      const canShareFile = typeof navigator.share === "function"
        && typeof navigator.canShare === "function"
        && navigator.canShare({files: [file]});
      button.disabled = !canShareFile;
      button.textContent = canShareFile ? "Share PDF" : "System share unavailable";
      status.textContent = canShareFile
        ? "PDF ready. Tap Share PDF to choose an app."
        : "This browser cannot share PDF files to system apps. Open this page in a browser that supports file sharing.";
    })
    .catch(() => {
      button.disabled = true;
      button.textContent = "Share PDF unavailable";
      status.textContent = "Could not prepare the PDF for sharing. Reload the page and try again.";
    });

  button.addEventListener("click", async () => {
    if (!file || button.disabled) return;
    try {
      await navigator.share({files: [file], title: file.name});
    } catch (error) {
      if (error.name !== "AbortError") status.textContent = "Could not open the system share sheet. Try again.";
    }
  });
});
