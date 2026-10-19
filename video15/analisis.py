"""Análisis de cada toma: movimiento de cámara, parte estable, nitidez, brillo y ficha visual."""
import concurrent.futures as cf
import csv
import hashlib
import json
import os
import subprocess

import numpy as np

from . import config, medios

ANCHO, ALTO = 192, 108


def leer_cuadros(ruta, fps, inicio=0.0, duracion=None):
    cmd = ["ffmpeg", "-v", "error", "-nostdin"]
    if inicio:
        cmd += ["-ss", f"{inicio:.3f}"]
    cmd += ["-i", ruta]
    if duracion:
        cmd += ["-t", f"{duracion:.3f}"]
    cmd += ["-map", "0:v:0", "-vf", f"fps={fps},scale={ANCHO}:{ALTO},format=gray",
            "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    datos = subprocess.run(cmd, capture_output=True).stdout
    n = len(datos) // (ANCHO * ALTO)
    return np.frombuffer(datos[: n * ANCHO * ALTO], np.uint8).reshape(n, ALTO, ANCHO).astype(np.float32)


_VENTANA = np.outer(np.hanning(ALTO), np.hanning(ANCHO)).astype(np.float32)


def desplazamientos(cuadros):
    """Desplazamiento global (px) entre cuadros consecutivos por correlación de fase.
    Mide el movimiento de la cámara, no el de la gente."""
    if len(cuadros) < 2:
        return np.zeros(0), np.zeros(0)
    movs, confianza = [], []
    anterior = np.fft.rfft2((cuadros[0] - cuadros[0].mean()) * _VENTANA)
    for c in cuadros[1:]:
        actual = np.fft.rfft2((c - c.mean()) * _VENTANA)
        r = anterior * np.conj(actual)
        r /= np.abs(r) + 1e-6
        corr = np.fft.irfft2(r, s=(ALTO, ANCHO))
        y, x = np.unravel_index(np.argmax(corr), corr.shape)
        dy = y - ALTO if y > ALTO // 2 else y
        dx = x - ANCHO if x > ANCHO // 2 else x
        movs.append(np.hypot(dx, dy))
        confianza.append(corr.max())
        anterior = actual
    return np.array(movs), np.array(confianza)


def nitidez(cuadro):
    lap = (cuadro[1:-1, :-2] + cuadro[1:-1, 2:] + cuadro[:-2, 1:-1] + cuadro[2:, 1:-1]
           - 4 * cuadro[1:-1, 1:-1])
    return float(lap.var())


def ventana_estable(vel, fps, duracion, est):
    """Devuelve (inicio, fin) en segundos de la parte estable, o None si no hay."""
    n = len(vel)
    if n < 3:
        return None
    k = max(1, int(round(fps * 0.5)))
    suave = np.convolve(vel, np.ones(k) / k, mode="same")
    centro = suave[int(n * 0.25): max(int(n * 0.75), int(n * 0.25) + 1)]
    umbral = max(est["umbral_base"], est["factor_mediana"] * float(np.median(centro)))
    quieto = suave <= umbral
    largo = max(1, int(round(est["ventana_estable"] * fps)))

    # quieto_desde[i] = cuántas muestras seguidas quietas hay a partir de i
    racha = np.zeros(n + 1, int)
    for i in range(n - 1, -1, -1):
        racha[i] = racha[i + 1] + 1 if quieto[i] else 0
    i0 = int(np.ceil(est["recorte_min_inicio"] * fps))
    ini = next((i for i in range(i0, n) if racha[i] >= largo), None)
    if ini is None:
        return None
    # desde el final hacia atrás
    racha_atras = np.zeros(n + 1, int)
    for i in range(n):
        racha_atras[i + 1] = racha_atras[i] + 1 if quieto[i] else 0
    i1 = n - int(np.ceil(est["recorte_min_fin"] * fps))
    fin = next((i for i in range(i1, ini, -1) if racha_atras[i] >= largo), None)
    if fin is None or fin <= ini:
        return None
    # vel[i] es el movimiento entre el cuadro i y el i+1 -> tiempos de cuadro
    t_ini = (ini + 1) / fps
    t_fin = min(duracion - est["recorte_min_fin"], (fin + 0.5) / fps)
    return (t_ini, t_fin) if t_fin - t_ini > 0 else None


def analizar_toma(clip, cfg, dir_fichas):
    est = cfg["estabilidad"]
    fps = est["fps_analisis"]
    cuadros = leer_cuadros(clip["ruta"], fps)
    movs, conf = desplazamientos(cuadros)
    vel = movs * fps / ANCHO  # en anchos de cuadro por segundo
    ventana = ventana_estable(vel, fps, clip["duracion"], est)
    muestras = cuadros[:: max(1, fps // 2)]
    res = dict(clip)
    res.update({
        "muestras_analizadas": int(len(cuadros)),
        "movimiento_mediano": float(np.median(vel)) if len(vel) else None,
        "nitidez": float(np.median([nitidez(c) for c in muestras])) if len(muestras) else 0.0,
        "brillo": float(np.mean([c.mean() for c in muestras]) / 255) if len(muestras) else 0.0,
        "entrada": None, "salida": None, "util": 0.0,
    })
    if ventana:
        res["entrada"], res["salida"] = round(ventana[0], 3), round(ventana[1], 3)
        res["util"] = round(ventana[1] - ventana[0], 3)
        dentro = vel[int(ventana[0] * fps): int(ventana[1] * fps)]
        res["movimiento_util"] = float(np.median(dentro)) if len(dentro) else None
    res["usable"] = res["util"] >= est["duracion_min_util"]
    res["ficha"] = hacer_ficha(res, dir_fichas)
    return res


def hacer_ficha(clip, dir_fichas):
    """Tres cuadros de la parte útil, uno al lado del otro, para mirar la toma de un vistazo."""
    os.makedirs(dir_fichas, exist_ok=True)
    nombre = clave(clip)[:10] + "_" + os.path.splitext(clip["archivo"])[0] + ".jpg"
    destino = os.path.join(dir_fichas, nombre)
    a = clip["entrada"] if clip["entrada"] is not None else 0.0
    b = clip["salida"] if clip["salida"] is not None else clip["duracion"]
    tiempos = [a + (b - a) * f for f in (0.15, 0.5, 0.85)]
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-y"]
    for t in tiempos:
        cmd += ["-ss", f"{max(0.0, t):.3f}", "-i", clip["ruta"]]
    filtro = "".join(f"[{i}:v:0]scale=320:180,setsar=1[c{i}];" for i in range(3))
    filtro += "[c0][c1][c2]hstack=inputs=3"
    cmd += ["-filter_complex", filtro, "-frames:v", "1", "-q:v", "5", destino]
    ok = subprocess.run(cmd, capture_output=True).returncode == 0
    return destino if ok else None


def clave(clip):
    base = f"{clip['ruta']}|{clip['tamano']}|{clip['mtime']}"
    return hashlib.md5(base.encode()).hexdigest()


def _parametros(cfg):
    return json.dumps(cfg["estabilidad"], sort_keys=True)


def analizar(cfg, log=print):
    dir_cache = config.trabajo(cfg, "cache_analisis")
    dir_fichas = config.trabajo(cfg, "fichas")
    os.makedirs(dir_cache, exist_ok=True)
    secciones = medios.listar(cfg)

    clips = []
    for nombre, rutas in secciones:
        tomas = []
        for r in rutas:
            try:
                i = medios.info(r, nombre)
            except RuntimeError as e:
                log(f"  ! {e}")
                continue
            if i:
                tomas.append(i)
        tomas.sort(key=lambda c: (c["fecha"], c["archivo"]))
        log(f"  {nombre}: {len(tomas)} tomas")
        clips.extend(tomas)

    procesos = cfg["procesos_analisis"] or max(1, (os.cpu_count() or 2) // 2)
    params = _parametros(cfg)
    resultados = [None] * len(clips)

    def trabajo_de(i):
        c = clips[i]
        cache = os.path.join(dir_cache, clave(c) + ".json")
        if os.path.exists(cache):
            with open(cache, encoding="utf-8") as f:
                guardado = json.load(f)
            if guardado.get("_params") == params and guardado.get("ruta") == c["ruta"]:
                guardado.update({"carpeta": c["carpeta"], "tipo": c["tipo"]})
                return i, guardado
        r = analizar_toma(c, cfg, dir_fichas)
        r["_params"] = params
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(r, f)
        return i, r

    with cf.ThreadPoolExecutor(procesos) as pool:
        for hechas, fut in enumerate(cf.as_completed([pool.submit(trabajo_de, i) for i in range(len(clips))]), 1):
            i, r = fut.result()
            resultados[i] = r
            if hechas % 10 == 0 or hechas == len(clips):
                log(f"  analizadas {hechas}/{len(clips)}")

    for i, r in enumerate(resultados):
        r["orden"] = i
    with open(config.trabajo(cfg, "analisis.json"), "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=1, ensure_ascii=False)
    escribir_reporte(cfg, resultados)
    return resultados


def cargar(cfg):
    ruta = config.trabajo(cfg, "analisis.json")
    if not os.path.exists(ruta):
        raise SystemExit("Primero hay que correr: analizar")
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def escribir_reporte(cfg, clips):
    ruta = config.trabajo(cfg, "reporte_tomas.csv")
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["orden", "carpeta", "archivo", "duracion", "corta_inicio_en", "corta_final_en",
                    "segundos_utiles", "usable", "tipo_lente", "nitidez", "brillo", "ficha"])
        for c in clips:
            w.writerow([c["orden"], c["carpeta"], c["archivo"], f"{c['duracion']:.2f}",
                        "" if c["entrada"] is None else f"{c['entrada']:.2f}",
                        "" if c["salida"] is None else f"{c['salida']:.2f}",
                        f"{c['util']:.2f}", "si" if c["usable"] else "NO", c["tipo"],
                        f"{c['nitidez']:.1f}", f"{c['brillo']:.2f}", c.get("ficha") or ""])
    return ruta
