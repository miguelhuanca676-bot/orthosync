# frontend · páginas de Orthosync

React 19, TypeScript, Tailwind 4 y Three.js, compilado con Vite. En la nube lo publica **Cloudflare Pages** en cada `git push`.

```
index.html, privacidad.html…  páginas públicas (HTML puro, buen SEO)
app.html + src/               la aplicación (inicio de sesión, roles)
src/paginas/                  una pantalla por archivo
src/componentes.tsx           piezas comunes (menú, encabezados, ventanas)
src/estilos.css               colores, tipografía, modo oscuro
functions/api/[[ruta]].js     función de Cloudflare: reenvía /api al servidor de Oracle
public/_headers               cabeceras de seguridad en Cloudflare
```

```
npm ci          instala (una vez)
npm run dev     desarrollo en http://localhost:5173/app (necesita la API encendida)
npm run build   genera dist/
```
