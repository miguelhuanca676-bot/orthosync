// Aviso informativo de almacenamiento. Orthosync solo usa almacenamiento técnico necesario
// (sin publicidad ni rastreo), por eso no hay nada que rechazar: el aviso solo informa.
(function () {
  var CLAVE = "orthosync.aviso";
  try { if (localStorage.getItem(CLAVE)) return; } catch (e) { /* sin almacenamiento */ }
  var caja = document.createElement("div");
  caja.setAttribute("role", "region");
  caja.setAttribute("aria-label", "Aviso de almacenamiento");
  caja.style.cssText = "position:fixed;left:16px;right:16px;bottom:16px;z-index:60;max-width:640px;margin:0 auto;" +
    "background:linear-gradient(90deg,#0b3d91,#312e81,#4c1d95);color:#fff;border-radius:16px;padding:16px 18px;" +
    "box-shadow:0 12px 32px rgba(15,23,61,.35);font:14px/1.5 'Segoe UI',system-ui,sans-serif;display:flex;gap:14px;" +
    "align-items:center;flex-wrap:wrap";
  var texto = document.createElement("p");
  texto.style.cssText = "margin:0;flex:1 1 320px";
  texto.innerHTML = "Orthosync solo usa almacenamiento <strong>técnico necesario</strong> para que puedas iniciar sesión. " +
    "No usamos cookies de publicidad ni de seguimiento. <a href=\"/cookies.html\" style=\"color:#bae6fd;text-decoration:underline\">Más información</a>";
  var boton = document.createElement("button");
  boton.type = "button";
  boton.textContent = "Entendido";
  boton.style.cssText = "background:#fff;color:#312e81;border:0;border-radius:10px;padding:9px 18px;font-weight:600;cursor:pointer";
  boton.onclick = function () { try { localStorage.setItem(CLAVE, "1"); } catch (e) { } caja.remove(); };
  caja.appendChild(texto); caja.appendChild(boton);
  (document.body || document.documentElement).appendChild(caja);
})();
