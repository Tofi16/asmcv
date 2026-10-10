// "Send files on WhatsApp": hands the original document files to the phone's share sheet (WhatsApp gets real files, not links).
const files = [];
let loaded = false;
function loadDocs() {
  if (loaded) return;
  loaded = true;
  document.querySelectorAll("[data-sf]").forEach(a => fetch(a.dataset.sf).then(r => r.blob()).then(b => files.push(new File([b], a.dataset.n, {type: b.type}))));
}
const sd = document.getElementById("sendDocs");
if (sd && !navigator.canShare) sd.style.display = "none";
if (sd) sd.addEventListener("click", e => {
  e.preventDefault();
  loadDocs();
  if (!files.length) { alert("Preparing the files… tap again in a moment."); return; }
  if (navigator.canShare && navigator.canShare({files})) navigator.share({files}).catch(() => {});
  else location.href = document.getElementById("zipLink").href;
});
