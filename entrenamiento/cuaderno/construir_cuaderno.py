import nbformat as nbf, os
AQUI = os.path.dirname(os.path.abspath(__file__))
nb = nbf.v4.new_notebook(); C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s)); code = lambda s: C.append(nbf.v4.new_code_cell(s))

md("""# Orthosync · Entrenamiento de los modelos (Kaggle, GPU gratuita)
**Proyecto de grado de Juan Miguel Huanca Uruña** · Sistema de apoyo al diagnóstico de tumores óseos

Este cuaderno entrena los cinco modelos con el dataset BTXRD y los deja listos para el servidor web:

1. Normal vs. lesión (ResNet18)
2. Benigno vs. maligno (ResNet18)
3. Hueso de la radiografía (ResNet18, para el visor 3D)
4. Aspecto de la lesión: crece hacia afuera, lítica o mixta (ResNet18, decide cómo se dibuja en 3D)
5. Localización de la lesión (YOLO11s a 1024 px)

### Casos corregidos por el médico (opcional)
Si exportaste casos desde Orthosync (*Validación → Exportar casos corregidos*), súbelos a Kaggle como un dataset
(*Add Input → Upload → New Dataset*, sube el ZIP tal cual) y agrégalo a este cuaderno. Se suman solo al entrenamiento;
la prueba sigue siendo BTXRD para que los resultados se puedan comparar.

### Antes de ejecutar (panel derecho de Kaggle → *Settings*)
- **Accelerator:** GPU T4 x2 (o P100)
- **Internet:** On (Kaggle pide verificar tu teléfono la primera vez)

### Cómo ejecutarlo
Botón **Save Version → Save & Run All (Commit)**. Así corre en segundo plano aunque cierres la pestaña.
Al terminar, abre la versión guardada → pestaña **Output** → descarga **orthosync_modelos.zip**.""")

code("""import os, sys, subprocess, torch
BASE = '/kaggle/working' if os.path.isdir('/kaggle/working') else os.getcwd()
IA = os.path.join(BASE, 'ia'); os.makedirs(IA, exist_ok=True)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'ultralytics', 'onnx', 'onnxruntime', 'openpyxl'])
print('GPU disponible:', torch.cuda.is_available(), '|', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'SIN GPU: activa el acelerador en Settings')""")

md("## 1. Código del entrenamiento\nCada celda guarda un archivo del proyecto. No hace falta modificarlas.")
for f in ["nucleo.py", "preparar_datos.py", "entrenar_clasificador.py", "entrenar_hueso.py", "entrenar_aspecto.py",
          "entrenar_detector.py", "evaluar.py", "exportar_onnx.py", "entrenar_todo.py"]:
    src = open(os.path.join(AQUI, "..", "codigo", f), encoding="utf-8").read()
    code("%%writefile " + "{IA}/" + f + "\n" + src)

md("""## 2. Dataset BTXRD
Se descarga solo desde figshare. Si la descarga falla, sube tu `BTXRD.zip` a Kaggle
(*Add Input → Upload → New Dataset*), agrégalo a este cuaderno y vuelve a ejecutar: el cuaderno lo encontrará en `/kaggle/input`.""")
code("""import requests, zipfile

def buscar_tabla(raiz):
    for d, _, archivos in os.walk(raiz):
        if any(a.lower() in ('dataset.xlsx', 'dataset.csv') for a in archivos):
            return d
    return None

def buscar_casos(raiz):
    # carpetas con casos corregidos exportados desde Orthosync (contienen casos.csv)
    return sorted({d for d, _, archivos in os.walk(raiz) if 'casos.csv' in archivos}) if os.path.isdir(raiz) else []

DATOS = os.environ.get('ORTHOSYNC_DATOS') or (buscar_tabla('/kaggle/input') if os.path.isdir('/kaggle/input') else None)
CASOS = buscar_casos('/kaggle/input')
for z in [os.path.join(d, a) for d, _, archivos in os.walk('/kaggle/input') for a in archivos
          if a.startswith('orthosync_casos') and a.endswith('.zip')] if os.path.isdir('/kaggle/input') else []:
    destino = os.path.join(BASE, 'casos', os.path.splitext(os.path.basename(z))[0])
    with zipfile.ZipFile(z) as zz:
        zz.extractall(destino)
    CASOS.append(destino)
print('Casos corregidos por el médico:', CASOS or 'ninguno')
if not DATOS:
    destino = os.path.join(BASE, 'BTXRD'); os.makedirs(destino, exist_ok=True)
    DATOS = buscar_tabla(destino)
    if not DATOS:
        cab = {'User-Agent': 'Mozilla/5.0'}
        info = requests.get('https://api.figshare.com/v2/articles/27865398', headers=cab, timeout=60).json()
        for f in info['files']:
            print('Descargando', f['name'], round(f['size'] / 1e6), 'MB')
            ruta = os.path.join(destino, f['name'])
            with requests.get(f['download_url'], headers=cab, stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(ruta, 'wb') as out:
                    for parte in r.iter_content(1 << 20):
                        out.write(parte)
            if ruta.endswith('.zip'):
                with zipfile.ZipFile(ruta) as z:
                    z.extractall(destino)
                os.remove(ruta)
        DATOS = buscar_tabla(destino)
assert DATOS, 'No se encontró el dataset. Súbelo a Kaggle como se indica arriba.'
print('Dataset en:', DATOS)""")

md("""## 3. Entrenar
`MODO = 'completo'` entrena todo (con GPU T4, calculo entre 3 y 6 horas: el detector ahora es más grande).
`MODO = 'rapido'` es una prueba de pocos minutos para comprobar que todo corre; sus resultados no sirven.""")
code("""MODO = os.environ.get('ORTHOSYNC_MODO', 'completo')
orden = [sys.executable, 'entrenar_todo.py', '--datos', DATOS] + (['--rapido'] if MODO == 'rapido' else []) + (['--extra', *CASOS] if CASOS else [])
p = subprocess.Popen(orden, cwd=IA, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace')
for linea in p.stdout:
    if '━' not in linea and 'it/s' not in linea:   # oculta las barras de progreso de YOLO
        print(linea, end='')
assert p.wait() == 0, 'El entrenamiento terminó con error; revisa el mensaje de arriba.'""")

md("## 4. Resultados")
code("""from IPython.display import Image, display
print(open(os.path.join(IA, 'resultados', 'informe_resultados.txt'), encoding='utf-8').read())
for f in ['curvas_roc.png', 'matriz_etapa1.png', 'matriz_etapa3.png', 'matriz_sistema.png']:
    ruta = os.path.join(IA, 'resultados', f)
    if os.path.exists(ruta):
        display(Image(ruta, width=420))""")

md("## 5. Empaquetar para descargar\nGenera `orthosync_modelos.zip` con los modelos y las métricas, y borra los archivos temporales.")
code("""import shutil
paquete = os.path.join(BASE, '_paquete'); shutil.rmtree(paquete, ignore_errors=True)
shutil.copytree(os.path.join(IA, 'modelos'), os.path.join(paquete, 'modelos'))
shutil.copytree(os.path.join(IA, 'resultados'), os.path.join(paquete, 'resultados'))
shutil.copytree(os.path.join(IA, 'ejemplos_prueba'), os.path.join(paquete, 'ejemplos_prueba'))
shutil.make_archive(os.path.join(BASE, 'orthosync_modelos'), 'zip', paquete)
for sobra in [paquete, os.path.join(IA, 'datos_preparados'), os.path.join(BASE, 'BTXRD')]:
    shutil.rmtree(sobra, ignore_errors=True)
print('Listo:', os.path.join(BASE, 'orthosync_modelos.zip'), round(os.path.getsize(os.path.join(BASE, 'orthosync_modelos.zip')) / 1e6), 'MB')""")

nb["cells"] = C
nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3"}, "language_info": {"name": "python"}}
nbf.write(nb, os.path.join(AQUI, "orthosync_entrenamiento_kaggle.ipynb"))
print("cuaderno generado,", len(C), "celdas")
