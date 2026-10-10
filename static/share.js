// Shares the finished PDF as a real file (WhatsApp receives it as a document, so quality is untouched).
const cache = {};
document.querySelectorAll("[data-u]").forEach(b => {
  fetch(b.dataset.u).then(r => r.blob()).then(x => {
    cache[b.dataset.u] = new File([x], b.dataset.n, {type: "application/pdf"});
    b.classList.add("ready"); b.textContent = "Share PDF";
  });
  b.addEventListener("click", e => {
    e.preventDefault();
    const f = cache[b.dataset.u];
    if (!f) { alert("Preparing the PDF… tap again in a moment."); return; }
    if (navigator.canShare && navigator.canShare({files: [f]})) navigator.share({files: [f]}).catch(() => {});
    else { const a = document.createElement("a"); a.href = URL.createObjectURL(f); a.download = f.name; a.click(); }
  });
});
