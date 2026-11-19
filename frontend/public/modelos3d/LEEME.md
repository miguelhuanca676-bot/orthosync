# Modelos 3D anatómicos

Huesos del lado derecho en formato glTF binario (`.glb`, comprimido con meshopt). Los usa el visor
(`frontend/src/hueso3d.ts`); si un archivo falta, el visor usa la versión simple hecha con geometría.

**Origen y licencia:** BodyParts3D, © The Database Center for Life Science (DBCLS),
licencia Creative Commons Atribución-CompartirIgual 2.1 Japón (CC BY-SA 2.1 JP):
https://creativecommons.org/licenses/by-sa/2.1/jp/deed.en

**Cambios:** orientados y escalados a la convención del visor, suavizados (Taubin) y remallados
en alta resolución por Juan Miguel Huanca Uruña con `herramientas/modelos3d/preparar_huesos.py`.
Estos archivos modificados se distribuyen con la misma licencia CC BY-SA 2.1 JP.
