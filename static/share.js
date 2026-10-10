// Shares the finished PDF as a real file (WhatsApp receives it as a document, so quality is untouched).
const cache = {};
document.querySelectorAll("[data-u]").forEach(b => {
  fetch(b.dataset.u, {credentials: "same-origin"}).then(async r => {
    if (!r.ok) throw new Error(`PDF request failed (${r.status})`);
    const type = (r.headers.get("content-type") || "").split(";", 1)[0].trim().toLowerCase();
    if (type !== "application/pdf") throw new Error("Server did not return a PDF");
    const blob = await r.blob();
    if (blob.size < 5 || await blob.slice(0, 5).text() !== "%PDF-") throw new Error("Invalid PDF file");
    return blob;
  }).then(x => {
    cache[b.dataset.u] = new File([x], b.dataset.n, {type: "application/pdf"});
    b.classList.add("ready"); b.textContent = (navigator.canShare && navigator.canShare({files: [cache[b.dataset.u]]})) ? "Send PDF" : "Download PDF";
  }).catch(error => {
    b.classList.add("error");
    b.dataset.error = "Could not prepare a valid PDF. Reload the CV and try again.";
    b.title = b.dataset.error;
    b.textContent = "PDF unavailable";
  });
  b.addEventListener("click", e => {
    e.preventDefault();
    const f = cache[b.dataset.u];
    if (!f) { alert(b.dataset.error || "Preparing the PDF… tap again in a moment."); return; }
    if (navigator.canShare && navigator.canShare({files: [f]})) navigator.share({files: [f]}).catch(() => {});
    else { const a = document.createElement("a"); a.href = URL.createObjectURL(f); a.download = f.name; a.click(); }
  });
});
