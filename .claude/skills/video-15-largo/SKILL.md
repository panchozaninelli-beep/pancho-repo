---
name: video-15-largo
description: Arma el video largo (20-30 min) de un 15 o evento a partir de carpetas de tomas (iPhone + drone) y temas elegidos por el usuario. Recorta inicio/fin inestables, ordena cronológicamente, intercala tipos de toma, corta en compases, pone la entrada en el boom, engancha temas con risers y exporta para CapCut. Usar cuando el usuario pida el "video largo", el "video de 20/30 minutos" o armar el evento completo desde el pendrive.
---

# Video largo de un evento

Herramienta: el paquete `video15` en la raíz de este repo (`python3 -m video15 ...`). Leé `README.md` si necesitás el detalle de opciones.

El usuario edita sus videos en **CapCut Pro** y graba con **iPhone 17 Pro Max** (modo Cine 1x / 2x y gran angular 0,5) y un drone para las tomas iniciales. Hablale en español rioplatense, sin tecnicismos.

## Flujo

1. **Chequeos previos**
   - `ffmpeg -version`, `python3 -c "import numpy"`. Si falta algo, instalalo (ver README) o pedile permiso.
   - Ubicá el pendrive: en Mac `ls /Volumes`; en Windows, las letras de unidad. Listá las carpetas del evento y confirmá que coinciden con el orden que te dio. Por defecto es: Drone, Inicio afuera, Habitación, Maquillaje 1, Primeras tomas salón, Maquillaje 2, Luces salón, Entrada, Lo que queda.
   - Si el pendrive es lento o hay espacio en el disco, sugerí copiar la carpeta al disco antes de analizar.
   - `carpeta_salida` siempre en el disco de la computadora.

2. **Proyecto**: copiá `proyecto.ejemplo.json` a `proyecto.json` y completalo con lo que diga el usuario. Si todavía no eligió los temas, podés correr `analizar` igual.

3. **Analizar**: `python3 -m video15 analizar --proyecto proyecto.json`. Revisá `trabajo/reporte_tomas.csv` y contale cuántas tomas quedaron usables y cuáles no.

4. **Mirar y etiquetar las tomas** (esto es el "criterio"). Mirá las imágenes de `trabajo/fichas/`: cada una tiene 3 cuadros de la parte útil de una toma. Si son muchas, hacelo por carpeta. Escribí `trabajo/etiquetas.json`:
   - `tipo`: `quinceanera`, `familia`, `invitados`, `salon`, `detalle` o `drone`. Esto es lo que se intercala: que no vayan más de 2 seguidas del mismo tipo.
   - `estrella: true` para las tomas lindas o importantes (momentos clave, emoción, la quinceañera bien encuadrada).
   - `descartar: true` para las inservibles (desenfocadas, tapadas, repetidas casi iguales, el piso, el bolsillo).
   - Ante la duda, no descartes: el video largo usa casi todas las tomas.
   - Clave: `"Carpeta/ARCHIVO.MOV"` o solo `"ARCHIVO.MOV"`.

5. **Momento de la puerta**: la primera toma de la carpeta Entrada dura unos 3 minutos y en algún momento ella cruza la puerta. Si el usuario no te dio el segundo:
   `python3 -m video15 fotogramas "<ruta de la toma>" --cada 1 --proyecto proyecto.json`
   Mirá los cuadros, encontrá el cruce y afiná con `--desde/--hasta --cada 0.25` alrededor. **Confirmalo con el usuario** antes de seguir: es el momento más importante del video. Ponelo en `entrada.momento_puerta`.

6. **Música**: los temas los elige el usuario. Con `python3 -m video15 musica --proyecto proyecto.json` ves el BPM y el boom detectado de cada uno. Para el tema de la entrada pedile el segundo exacto del boom, o verificalo vos con la energía del audio, y ponelo en `boom`. Asigná cada tema a dónde empieza (`empieza_con`: carpeta o archivo). Por ejemplo, el vals arranca en la primera toma del vals dentro de la carpeta Entrada.

7. **Armar**: `python3 -m video15 armar --proyecto proyecto.json`. Leé `guia_de_cortes.txt` y los avisos:
   - Si faltan temas ("faltan ~X de música"), decile cuántos minutos le faltan a ese bloque para usar todas las tomas.
   - Si la duración total no está entre 20 y 30 minutos, proponé ajustar `compases_por_toma` o agregar o quitar temas.

8. **Exportar**: `python3 -m video15 exportar --proyecto proyecto.json`. Puede tardar (son tomas 4K). Al terminar, explicale:
   - En CapCut: importar la carpeta `tomas_para_capcut`, ordenar por nombre, seleccionar todo y arrastrar a la línea de tiempo.
   - Poner `musica_completa.wav` en la pista de audio desde el segundo 0.
   - Revisar antes `borrador_720p.mp4` si quiere ver el ritmo rápido.

## Estilo de este video (no confundir con sus reels de 2-3 min)

- Largo, tranquilo, "sin tanto wow": tomas de ~2 compases, cortes en el inicio de compás.
- Casi todas las tomas adentro, en orden cronológico.
- La **entrada de la quinceañera en el boom** es obligatoria.
- Drone y tomas de afuera al principio.

## Cuando el usuario pide cambios

- "Esta toma no va" → `descartar` en etiquetas → `armar` + `exportar` (solo re-exporta lo que cambió).
- "Más ritmo" → bajar `compases_por_toma` a 1. "Más calmo" → subir a 3.
- "Recorta de más" o "quedan temblores" → ajustar `estabilidad.umbral_base` y volver a `analizar`. El análisis se rehace solo si cambian esos parámetros.
