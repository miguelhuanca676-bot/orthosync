// Verificación pública de informes. El código llega después de "#" en la dirección del QR.
(function () {
  var huella = null;
  var $ = function (id) { return document.getElementById(id); };
  var fecha = function (f) {
    if (!f) return "-";
    if (f.length > 10) { var d = new Date(f.endsWith("Z") ? f : f + "Z"); return d.toLocaleString("es-BO", { dateStyle: "long", timeStyle: "short" }); }
    return f.split("-").reverse().join("/");
  };
  function mostrar(html, ok) {
    var r = $("resultado");
    r.className = "mt-6 rounded-xl border px-5 py-4 " + (ok ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-red-200 bg-red-50 text-red-900");
    r.innerHTML = html;
  }
  function texto(s) { var d = document.createElement("div"); d.textContent = s == null ? "" : String(s); return d.innerHTML; }
  function verificar(codigo) {
    codigo = (codigo || "").trim();
    if (!codigo) return;
    $("codigo").value = codigo;
    fetch("/api/verificar/" + encodeURIComponent(codigo), { headers: { "X-Orthosync": "1" }, cache: "no-store" })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (x) {
        if (!x.ok) {
          huella = null; $("archivo").classList.add("hidden");
          mostrar("<p class='font-semibold'>No encontramos un informe con ese código.</p><p class='mt-1 text-sm'>Revisa que esté bien escrito. Si lo escaneaste del QR y aun así no aparece, el documento no fue emitido por Orthosync.</p>", false);
          return;
        }
        var d = x.d; huella = d.huella;
        mostrar("<p class='font-semibold'>Informe auténtico emitido por " + texto(d.sistema) + " para " + texto(d.clinica) + ".</p>" +
          "<dl class='mt-3 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2'>" +
          "<div><dt class='opacity-70'>Tipo</dt><dd class='font-medium'>" + texto(d.tipo) + "</dd></div>" +
          "<div><dt class='opacity-70'>Emitido</dt><dd class='font-medium'>" + texto(fecha(d.emitido_en)) + "</dd></div>" +
          "<div><dt class='opacity-70'>Expediente</dt><dd class='font-medium'>" + texto(d.expediente) + "</dd></div>" +
          "<div><dt class='opacity-70'>Estudio del</dt><dd class='font-medium'>" + texto(fecha(d.fecha_estudio)) + "</dd></div></dl>", true);
        $("archivo").classList.remove("hidden");
      })
      .catch(function () { mostrar("<p class='font-semibold'>No se pudo conectar con el servidor.</p><p class='mt-1 text-sm'>Intenta de nuevo en unos minutos.</p>", false); });
  }
  $("formulario").addEventListener("submit", function (e) { e.preventDefault(); verificar($("codigo").value); });
  $("pdf").addEventListener("change", function () {
    var f = this.files && this.files[0], p = $("comparacion");
    if (!f || !huella) return;
    if (!window.crypto || !crypto.subtle) { p.className = "mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900"; p.textContent = "Tu navegador no permite comprobar el archivo (se necesita una conexión segura, https)."; return; }
    f.arrayBuffer().then(function (b) { return crypto.subtle.digest("SHA-256", b); }).then(function (h) {
      var hex = Array.prototype.map.call(new Uint8Array(h), function (x) { return ("0" + x.toString(16)).slice(-2); }).join("");
      var igual = hex === huella;
      p.className = "mt-3 rounded-lg px-3 py-2 text-sm " + (igual ? "bg-emerald-50 text-emerald-900" : "bg-red-50 text-red-900");
      p.textContent = igual ? "El archivo es idéntico al que emitió Orthosync: no fue modificado." : "El archivo NO coincide con el original: fue modificado o es otro informe.";
    });
  });
  if (location.hash.length > 1) verificar(decodeURIComponent(location.hash.slice(1)));
})();
