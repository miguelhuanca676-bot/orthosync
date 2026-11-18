// DATOS DE LA CLÍNICA que aparecen en las páginas legales y en el pie de página.
// Edita este archivo con los datos reales (está en interfaz/dist/clinica.js y en interfaz/public/clinica.js).
window.CLINICA = {
  nombre: "SpineBolivia",
  razon_social: "[Razón social de la clínica]",
  nit: "[NIT]",
  direccion: "[Dirección de la clínica]",
  ciudad: "[Ciudad], Bolivia",
  correo: "[correo de contacto]",
  telefono: "[teléfono de contacto]",
  responsable_datos: "[Nombre del responsable de protección de datos]",
  autor: "Juan Miguel Huanca Uruña",
  universidad: "Universidad Privada del Valle (UNIVALLE)",
  repositorio: "[enlace al repositorio con el código fuente]",
  actualizado: "16 de noviembre de 2026",
};
document.querySelectorAll("[data-clinica]").forEach(function (el) {
  var v = window.CLINICA[el.getAttribute("data-clinica")];
  if (v) el.textContent = v;
});
