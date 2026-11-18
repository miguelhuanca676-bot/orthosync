# entrenamiento · modelos de la CNN

Se entrena en **Kaggle** (GPU gratis) con el dataset público **BTXRD**, más los casos que corrige el traumatólogo en Orthosync (botón «Exportar casos valorados (ZIP)» en Validación).

```
codigo/      preparar_datos, entrenar_clasificador (lesión y malignidad), entrenar_hueso,
             entrenar_aspecto, entrenar_detector (YOLO), evaluar, exportar_onnx
cuaderno/    orthosync_entrenamiento_kaggle.ipynb (se importa en Kaggle) y el script que lo genera
```

1. Kaggle → **Create → Notebook → File → Import Notebook** → `cuaderno/orthosync_entrenamiento_kaggle.ipynb`.
2. Panel derecho: **Accelerator → GPU T4 x2**. **Internet → On**.
3. **Save Version → Save & Run All**. Tarda unas horas.
4. Pestaña **Output** → descarga `orthosync_modelos.zip` → sigue [docs/despliegue.md](../docs/despliegue.md#7-modelos-nuevos-de-kaggle).

Si cambias algo en `codigo/`, regenera el cuaderno con `python cuaderno/construir_cuaderno.py`.
