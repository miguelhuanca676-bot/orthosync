# inferencia · servicio de la CNN

Recibe una radiografía y devuelve lo que ven los modelos. No guarda nada ni conoce a los pacientes.

| Ruta | Qué hace |
|---|---|
| `GET /salud` | ¿Está vivo? (sin token) |
| `GET /info` | Qué modelos están cargados y sus métricas |
| `POST /analizar` | Imagen → probabilidad de lesión, malignidad, hueso, aspecto, recuadros, mapa de calor |
| `POST /recargar` | Vuelve a leer los modelos de la carpeta |

Todas, salvo `/salud`, exigen la cabecera `X-Token-Interno` si `ORTHOSYNC_INFERENCIA_TOKEN` está definida.

```
cnn/main.py    la API interna
cnn/motor.py   preprocesamiento, ONNX Runtime, recuadros y mapa de calor
modelos/       aquí van los .onnx (ver modelos/LEEME.md)
```

Correr solo la CNN (dentro de `inferencia/`): `.venv\Scripts\python -m uvicorn cnn.main:app --port 8001` → documentación en http://localhost:8001/docs
