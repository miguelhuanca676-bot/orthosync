// Aplica el tema (claro u oscuro) antes de dibujar la página, para que no parpadee.
// Se guarda solo en este navegador; si no hay preferencia, sigue la del sistema operativo.
(function () {
  var t = null;
  try { t = localStorage.getItem("orthosync.tema"); } catch (e) { /* sin almacenamiento */ }
  if (!t) t = window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "oscuro" : "claro";
  if (t === "oscuro") document.documentElement.classList.add("oscuro");
  else document.documentElement.classList.add("osh-light");
})();
