"""Exporta: tomas recortadas numeradas (para CapCut), música mezclada, guía de cortes y borrador."""
import concurrent.futures as cf
import hashlib
import json
import os
import re
import subprocess

import numpy as np

from . import audio, config


def _encoders():
    r = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True)
    return r.stdout


def elegir_codec(cfg):
    pedido = cfg["salida"]["codec"]
    if pedido != "auto":
        return pedido
    disponibles = _encoders()
    for c in ("hevc_videotoolbox", "hevc_nvenc", "libx265"):
        if re.search(rf"\b{c}\b", disponibles) and _funciona(c):
            return c
    return "libx264"


def _funciona(codec):
    """Un códec puede figurar en la lista y no andar (p. ej. NVIDIA sin placa): probamos un cuadro."""
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-f", "lavfi", "-i", "color=c=black:s=256x144:d=0.1",
           "-frames:v", "1"] + _args_codec(codec, 256) + ["-f", "null", "-"]
    return subprocess.run(cmd, capture_output=True).returncode == 0


def _args_codec(codec, ancho):
    br = "80M" if ancho >= 3000 else "30M"
    if codec == "hevc_videotoolbox":
        return ["-c:v", codec, "-profile:v", "main10", "-pix_fmt", "p010le", "-b:v", br, "-tag:v", "hvc1"]
    if codec == "hevc_nvenc":
        return ["-c:v", codec, "-profile:v", "main10", "-pix_fmt", "p010le", "-preset", "p5",
                "-rc", "vbr", "-cq", "18", "-b:v", "0", "-tag:v", "hvc1"]
    if codec == "libx265":
        return ["-c:v", codec, "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p10le",
                "-tag:v", "hvc1", "-x265-params", "log-level=error"]
    if codec == "prores":
        return ["-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p"]


def _slug(texto):
    return re.sub(r"[^a-z0-9]+", "-", config.normalizar(texto)).strip("-")[:24]


def nombre_toma(t):
    return f"{t['n']:04d}_{_slug(t['carpeta'])}_{os.path.splitext(t['archivo'])[0]}.mov"


def exportar_toma(t, cfg, codec, destino):
    ancho, alto = map(int, cfg["salida"]["resolucion"].lower().split("x"))
    fps = cfg["salida"]["fps"]
    vf = (f"scale={ancho}:{alto}:force_original_aspect_ratio=decrease,"
          f"pad={ancho}:{alto}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}")
    usar_audio = cfg["salida"]["audio_camara"] and t["audio"]
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-y", "-ss", f"{t['entrada_en_original']:.4f}", "-i", t["ruta"]]
    if not usar_audio:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    cmd += ["-map", "0:v:0", "-map", "0:a:0" if usar_audio else "1:a:0", "-vf", vf,
            "-frames:v", str(t["cuadros"]), "-t", f"{t['duracion']:.4f}"]
    cmd += _args_codec(codec, ancho)
    for opcion, clave in (("-color_primaries", "color_primaries"), ("-color_trc", "color_trc"),
                          ("-colorspace", "colorspace")):
        if t.get(clave) and t[clave] != "unknown":
            cmd += [opcion, t[clave]]
    cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", destino]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Falló la exportación de {t['archivo']}: {r.stderr.strip()[-500:]}")


def exportar_tomas(plan, cfg, log=print):
    carpeta = os.path.join(cfg["carpeta_salida"], "tomas_para_capcut")
    os.makedirs(carpeta, exist_ok=True)
    codec = elegir_codec(cfg)
    log(f"  códec: {codec}")
    manifiesto_ruta = config.trabajo(cfg, "exportadas.json")
    manifiesto = {}
    if os.path.exists(manifiesto_ruta):
        with open(manifiesto_ruta, encoding="utf-8") as f:
            manifiesto = json.load(f)
    validos = {nombre_toma(t) for t in plan["tomas"]}
    for viejo in os.listdir(carpeta):
        if viejo.endswith(".mov") and viejo not in validos:
            os.remove(os.path.join(carpeta, viejo))

    def firma(t):
        datos = {k: t[k] for k in ("ruta", "entrada_en_original", "cuadros")}
        datos.update(salida=cfg["salida"], codec=codec)
        return hashlib.md5(json.dumps(datos, sort_keys=True).encode()).hexdigest()

    pendientes = []
    for t in plan["tomas"]:
        destino = os.path.join(carpeta, nombre_toma(t))
        if os.path.exists(destino) and manifiesto.get(nombre_toma(t)) == firma(t):
            continue
        pendientes.append((t, destino))
    log(f"  {len(plan['tomas']) - len(pendientes)} ya estaban, exporto {len(pendientes)}")

    with cf.ThreadPoolExecutor(cfg["salida"]["procesos"]) as pool:
        futuros = {pool.submit(exportar_toma, t, cfg, codec, d): t for t, d in pendientes}
        for n, fut in enumerate(cf.as_completed(futuros), 1):
            t = futuros[fut]
            fut.result()
            manifiesto[nombre_toma(t)] = firma(t)
            if n % 5 == 0 or n == len(pendientes):
                with open(manifiesto_ruta, "w", encoding="utf-8") as f:
                    json.dump(manifiesto, f)
                log(f"  exportadas {n}/{len(pendientes)}")
    return carpeta


def mezclar_musica(plan, cfg, log=print):
    sr = audio.SR_SALIDA
    est = cfg["estilo"]
    total = int(round(plan["duracion"] * sr))
    mezcla = np.zeros((total, 2), np.float32)
    riser_externo = None
    if est.get("riser_archivo"):
        riser_externo = audio.cargar(config.resolver(cfg, est["riser_archivo"]), sr, 2)
    cache = {}
    musica = plan["musica"]
    risers = []
    for i, m in enumerate(musica):
        if m["archivo"] not in cache:
            cache[m["archivo"]] = audio.cargar(m["archivo"], sr, 2)
        x = cache[m["archivo"]][int(m["desde"] * sr): int(m["hasta"] * sr)].copy()
        a = int(round(m["inicio"] * sr))
        x = x[: max(0, total - a)]
        n = len(x)
        entrada = int((0.01 if m["desde"] < 0.05 or i == 0 else 0.15) * sr)
        x[:entrada] *= np.linspace(0, 1, min(entrada, n))[:, None]
        if i + 1 < len(musica):
            fundido = min(n // 2, int(est["fundido_salida_compases"] * m["compas"] * sr))
            x[n - fundido:] *= np.linspace(1, 0, fundido)[:, None] ** 1.5
            dur_r = min(m["hasta"] - m["desde"], est["riser_compases"] * m["compas"], 8.0)
            r = riser_externo[-int(dur_r * sr):] if riser_externo is not None else audio.riser(dur_r)
            fin = a + n
            r = r[: fin - max(0, fin - len(r))]
            mezcla[fin - len(r): fin] += r * est["riser_volumen"]
            risers.append(round((fin - len(r)) / sr, 3))
        else:
            fundido = min(n // 2, int(2.0 * sr))
            x[n - fundido:] *= np.linspace(1, 0, fundido)[:, None]
        mezcla[a: a + n] += x
    pico = np.abs(mezcla).max()
    if pico > 0.98:
        mezcla *= 0.98 / pico
    ruta = os.path.join(cfg["carpeta_salida"], "musica_completa.wav")
    audio.escribir_wav(ruta, mezcla, sr)
    plan["risers"] = risers
    return ruta


def escribir_guia(plan, cfg):
    ruta = os.path.join(cfg["carpeta_salida"], "guia_de_cortes.txt")
    eventos = [(t["inicio"], "toma", t) for t in plan["tomas"]]
    eventos += [(m["inicio"], "tema", m) for m in plan["musica"]]
    for m in plan["musica"]:
        if m.get("boom") is not None and m["desde"] <= m["boom"] < m["hasta"]:
            eventos.append((m["inicio"] + m["boom"] - m["desde"], "boom", m))
    eventos += [(r, "riser", None) for r in plan.get("risers", [])]
    eventos.sort(key=lambda e: (e[0], {"tema": 0, "riser": 1, "boom": 2, "toma": 3}[e[1]]))
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(f"VIDEO LARGO - duración {config.mmss(plan['duracion'])} - "
                f"{plan['tomas_usadas']} tomas de {plan['tomas_disponibles']}\n")
        f.write("Importá la carpeta tomas_para_capcut ordenada por nombre y musica_completa.wav desde el segundo 0.\n\n")
        for t, tipo, d in eventos:
            if tipo == "tema":
                f.write(f"\n{config.mmss(t)}  ♪ TEMA {d['indice'] + 1}: {os.path.basename(d['archivo'])} "
                        f"(desde {config.mmss(d['desde'])})\n")
            elif tipo == "riser":
                f.write(f"{config.mmss(t)}  ↗ riser\n")
            elif tipo == "boom":
                f.write(f"{config.mmss(t)}  ★ BOOM\n")
            else:
                extra = f"  <-- {d['nota']}" if d["nota"] else ""
                estrella = " ★" if d["estrella"] else ""
                f.write(f"{config.mmss(t)}  {nombre_toma(d)}  ({d['duracion']:.2f}s, {d['tipo']}{estrella}){extra}\n")
        if plan["avisos"]:
            f.write("\nAVISOS\n")
            for a in plan["avisos"]:
                f.write(f"- {a}\n")
    return ruta


def borrador(plan, cfg, carpeta_tomas, musica, log=print):
    """Video de control en 720p con la música, para revisar ritmo y orden sin abrir CapCut."""
    lista = config.trabajo(cfg, "lista_borrador.txt")
    with open(lista, "w", encoding="utf-8") as f:
        for t in plan["tomas"]:
            ruta = os.path.join(carpeta_tomas, nombre_toma(t)).replace("'", "'\\''")
            f.write(f"file '{ruta}'\n")
    destino = os.path.join(cfg["carpeta_salida"], "borrador_720p.mp4")
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "concat", "-safe", "0", "-i", lista, "-i", musica,
           "-map", "0:v", "-map", "1:a", "-vf", "scale=1280:720,format=yuv420p", "-c:v", "libx264",
           "-preset", "veryfast", "-crf", "26", "-c:a", "aac", "-b:a", "160k", "-shortest", destino]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        log(f"  ! no pude armar el borrador: {r.stderr.strip()[-300:]}")
        return None
    return destino
