# Video15 — video largo de un 15 (20 a 30 minutos)

Arma automáticamente el **primer corte** del video largo de un evento:

1. **Lee las carpetas en orden** (Drone → Inicio afuera → Habitación → … → Lo que queda) y ordena las tomas de cada carpeta por la hora en que se grabaron.
2. **Recorta el principio y el final inestables de cada toma.** Mide cuadro por cuadro cuánto se mueve la cámara y se queda solo con la parte estable.
3. **Descarta lo inservible** (sin parte estable, demasiado corta, muy borrosa o muy oscura, si hace falta lugar).
4. **Intercala tipos de toma** (gran angular 0,5 / 1x / 2x según el lente que guarda el iPhone, o las etiquetas que se le pongan) para que no vayan más de 2 seguidas iguales, sin romper el orden cronológico.
5. **Corta sobre la música:** cada corte cae en el inicio de un compás. La duración típica es de 2 compases por toma (≈ 4 s), porque es un video largo y tranquilo.
6. **Entrada de la quinceañera:** el momento en que cruza la puerta cae **exactamente en el boom** del tema de entrada.
7. **Engancha los temas con un riser** (sintético o el tuyo) y un fundido.
8. **Exporta para CapCut:** una carpeta con las tomas ya recortadas y numeradas, más la música completa en un solo archivo.

## Lo que entrega (en la carpeta de salida)

| Archivo | Para qué |
|---|---|
| `tomas_para_capcut/0001_drone_IMG_0001.mov`, … | Las tomas recortadas, en orden. En CapCut: importás la carpeta, seleccionás todo, lo arrastrás a la línea de tiempo y queda en orden, una pegada a la otra. |
| `musica_completa.wav` | Todos los temas ya enganchados con risers. Va en la pista de audio **desde el segundo 0**: los cortes ya coinciden con la música. |
| `guia_de_cortes.txt` | Minuto a minuto: qué toma va, dónde arranca cada tema, dónde están los risers y los booms, y avisos. |
| `borrador_720p.mp4` | El video completo en baja calidad con la música, para revisar el ritmo sin abrir CapCut. |
| `trabajo/reporte_tomas.csv` | Por cada toma: dónde se cortó el principio y el final, cuántos segundos útiles tiene, si se usa. |
| `trabajo/fichas/` | Una imagen por toma (3 cuadros) para mirarlas rápido. |

En CapCut, después, aplicás tus presets de color, efectos y sonidos de la versión Pro, y cambiás o movés lo que quieras.

---

## Instalación (una sola vez)

Hacen falta **Python 3**, **ffmpeg** y **numpy**.

**Mac** (en la Terminal):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"   # si no tenés Homebrew
brew install python ffmpeg
pip3 install numpy
```

**Windows** (en PowerShell):
```powershell
winget install Python.Python.3.12
winget install Gyan.FFmpeg
pip install numpy
```

Después bajás este repositorio (con Claude Code en tu compu se hace solo).

## Uso

1. Copiá `proyecto.ejemplo.json` como `proyecto.json` y completalo:
   - `carpeta_origen`: la carpeta del evento en el pendrive. En Mac es algo como `/Volumes/KINGSTON/Quince Sofia`; en Windows, `E:/Quince Sofia`.
   - `carpeta_salida`: dónde querés el resultado. **Conviene el disco de la compu**, no el pendrive.
   - `secciones`: los nombres de las carpetas, en orden. No importan mayúsculas ni tildes.
   - `entrada.momento_puerta`: el minuto y segundo **de la toma de entrada** en que ella cruza la puerta (ver más abajo).
   - `temas`: la música, en orden (ver más abajo).
2. Corré:
   ```bash
   python3 -m video15 todo --proyecto proyecto.json
   ```
   O paso a paso: `analizar`, `musica`, `armar`, `exportar`. El análisis queda guardado, así que si cambiás la música o el estilo, `armar` y `exportar` no vuelven a analizar las tomas.

### La música (`temas`)

Cada tema puede tener:
- `archivo`: mp3, wav, m4a, etc.
- `empieza_con`: el nombre de una carpeta o de una toma (ej. `"IMG_4521.MOV"`). El tema arranca justo en esa toma. Los temas sin `empieza_con` siguen a continuación del anterior, dentro del mismo bloque.
- `boom`: el segundo del tema donde está el boom (ej. `"1:04.5"`). Si no lo ponés, lo detecta solo, pero **para el tema de la entrada conviene ponerlo a mano**.
- `desde` / `hasta`: para usar solo una parte del tema (ej. saltear una intro larga).
- `bpm`: solo si la detección del tempo falla.

El tema cuyo `empieza_con` es la carpeta `Entrada` se toma como **el tema de la entrada**.

Si en un bloque hay más tomas que música, primero se acortan las tomas y después se dejan afuera las de peor calidad, y avisa. Si querés usar casi todas, agregá otro tema a ese bloque.

### Encontrar el momento de la puerta

```bash
python3 -m video15 fotogramas "/Volumes/KINGSTON/Quince Sofia/Entrada/IMG_4500.MOV" --desde 1:30 --hasta 3:00 --cada 0.5 --proyecto proyecto.json
```
Saca un cuadro cada medio segundo. Cada imagen se llama con su minuto y segundo, así ves en cuál cruza la puerta.

### Etiquetas (opcional, mejora mucho el intercalado)

`trabajo/etiquetas.json` permite marcar tomas a mano (o lo hace Claude mirando las fichas):
```json
{
  "Entrada/IMG_4502.MOV": { "tipo": "quinceanera", "estrella": true },
  "IMG_4530.MOV": { "tipo": "salon" },
  "IMG_4531.MOV": { "descartar": true }
}
```
Tipos sugeridos: `quinceanera`, `familia`, `invitados`, `salon`, `detalle`, `drone`. Una toma **estrella** nunca se descarta y dura un compás más.

### Ajustes de estilo (`estilo`)

| Opción | Por defecto | Qué hace |
|---|---|---|
| `compases_por_toma` | 2 | Largo típico de cada toma. |
| `compases_min` / `compases_max` | 1 / 4 | Límites. |
| `max_seguidas_mismo_tipo` | 2 | Cuántas tomas del mismo tipo pueden ir seguidas. |
| `posicion_en_toma` | 0.3 | Qué parte de la toma estable se usa (0 = apenas se estabiliza, 0.5 = el centro). |
| `riser_compases` | 2 | Largo del riser entre temas. |
| `riser_archivo` | null | Tu propio riser (wav/mp3). Si no hay, se genera uno. |

### Ajustes de estabilidad (`estabilidad`)

Si recorta de más o de menos, se calibra con:
- `recorte_min_inicio` / `recorte_min_fin` (0.4 s): lo mínimo que se saca siempre.
- `umbral_base` (0.04): cuánto movimiento se tolera. Si deja temblores, bajalo. Si recorta tomas buenas con movimiento intencional, subilo.
- `ventana_estable` (0.8 s): cuánto tiempo tiene que estar quieta para considerar que ya se estabilizó.

## Sobre el iPhone 17 Pro Max

- Graba en HDR (HLG / Dolby Vision). Las tomas exportadas mantienen 10 bits y la información de color HLG; la metadata Dolby Vision se pierde, como en cualquier recodificación. El borrador 720p es solo para revisar ritmo: los colores ahí pueden verse lavados.
- Las tomas se exportan en HEVC 10 bits. En Mac usa el chip de Apple (rápido); en Windows usa NVIDIA si hay, y si no, el procesador (más lento).
- El desenfoque del modo Cine queda fijo como se grabó.

## Prueba sin material real

```bash
python3 pruebas/generar_material.py evento_prueba
python3 -m video15 todo --proyecto evento_prueba/proyecto.json
```
