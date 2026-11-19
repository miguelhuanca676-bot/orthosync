# Modelos 3D anatómicos (high poly)

`preparar_huesos.py` convierte las mallas reales de **BodyParts3D** (CC BY-SA 2.1 JP) en los
modelos que usa el visor 3D: `frontend/public/modelos3d/<hueso>.glb`.

Qué hace con cada hueso:
1. Lo orienta como el visor (extremo superior arriba, frente hacia +Z; mano y pie con los dedos arriba).
2. Lo escala a 10 unidades de alto.
3. Quita el escalonado del escaneo (suavizado de Taubin, que no encoge el hueso).
4. Lo remalla con triángulos uniformes y pequeños (≈ 45 000 a 110 000 triángulos por modelo).
5. Lo guarda en `.glb` y lo comprime con `gltfpack` (cada modelo pesa entre 0,25 y 0,6 MB).

## Volver a generarlos

```
pip install trimesh pymeshlab numpy
python herramientas/modelos3d/preparar_huesos.py
```

Descarga los STL de GitHub. Para más o menos detalle, cambia la longitud de arista en `HUESOS`
(más chica = más triángulos). Para comprimir hace falta Node.js (`npx gltfpack`); sin él, los
archivos quedan sin comprimir y funcionan igual, solo pesan más.
