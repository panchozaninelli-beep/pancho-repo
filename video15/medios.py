"""Lectura de carpetas y metadatos de las tomas (ffprobe)."""
import datetime as dt
import json
import os
import re
import subprocess

from . import config

EXT_VIDEO = {".mov", ".mp4", ".m4v", ".mts", ".mxf"}


def ffprobe(ruta):
    salida = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", ruta],
        capture_output=True, text=True,
    )
    if salida.returncode != 0:
        raise RuntimeError(f"ffprobe no pudo leer {ruta}: {salida.stderr.strip()}")
    return json.loads(salida.stdout)


def _fecha(texto):
    if not texto:
        return None
    texto = texto.strip().replace("Z", "+00:00")
    texto = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", texto)  # -0300 -> -03:00
    try:
        fecha = dt.datetime.fromisoformat(texto)
    except ValueError:
        return None
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=dt.timezone.utc)
    return fecha.timestamp()


def _fps(texto):
    try:
        num, den = texto.split("/")
        return float(num) / float(den) if float(den) else 0.0
    except (ValueError, AttributeError):
        return 0.0


def _rotacion(stream):
    for sd in stream.get("side_data_list", []) or []:
        if "rotation" in sd:
            return int(round(float(sd["rotation"])))
    try:
        return int(stream.get("tags", {}).get("rotate", 0))
    except ValueError:
        return 0


def tipo_por_lente(focal35, carpeta):
    if "dron" in config.normalizar(carpeta):
        return "drone"
    if not focal35:
        return "sin_dato"
    if focal35 <= 18:
        return "abierto"      # gran angular 0,5
    if focal35 >= 40:
        return "cerrado"      # 2x / cine 2x
    return "medio"            # 1x


def info(ruta, carpeta):
    datos = ffprobe(ruta)
    fmt = datos.get("format", {})
    tags = {k.lower(): v for k, v in (fmt.get("tags") or {}).items()}
    video = next((s for s in datos.get("streams", [])
                  if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")), None)
    if video is None:
        return None
    audio = any(s.get("codec_type") == "audio" for s in datos.get("streams", []))
    for k, v in (video.get("tags") or {}).items():
        tags.setdefault(k.lower(), v)

    fecha = (_fecha(tags.get("com.apple.quicktime.creationdate"))
             or _fecha(tags.get("creation_time"))
             or os.path.getmtime(ruta))
    try:
        focal35 = float(tags.get("com.apple.quicktime.camera.focal_length.35mm_equivalent", 0)) or None
    except ValueError:
        focal35 = None
    rot = _rotacion(video)
    ancho, alto = int(video.get("width", 0)), int(video.get("height", 0))
    if abs(rot) in (90, 270):
        ancho, alto = alto, ancho
    duracion = float(fmt.get("duration") or video.get("duration") or 0)
    return {
        "ruta": ruta,
        "carpeta": carpeta,
        "archivo": os.path.basename(ruta),
        "fecha": fecha,
        "duracion": duracion,
        "ancho": ancho,
        "alto": alto,
        "fps": _fps(video.get("avg_frame_rate")) or _fps(video.get("r_frame_rate")),
        "audio": audio,
        "lente": tags.get("com.apple.quicktime.camera.lens_model"),
        "focal35": focal35,
        "tipo": tipo_por_lente(focal35, carpeta),
        "color_primaries": video.get("color_primaries"),
        "color_trc": video.get("color_transfer"),
        "colorspace": video.get("color_space"),
        "tamano": os.path.getsize(ruta),
        "mtime": os.path.getmtime(ruta),
    }


def buscar_carpeta(origen, nombre):
    buscado = config.normalizar(nombre)
    for entrada in sorted(os.listdir(origen)):
        if config.normalizar(entrada) == buscado and os.path.isdir(os.path.join(origen, entrada)):
            return os.path.join(origen, entrada)
    return None


def videos_de(carpeta):
    rutas = []
    for raiz, dirs, archivos in os.walk(carpeta):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for a in archivos:
            # macOS deja archivos "._algo.MOV" en pendrives: no son videos.
            if a.startswith(".") or os.path.splitext(a)[1].lower() not in EXT_VIDEO:
                continue
            rutas.append(os.path.join(raiz, a))
    return rutas


def listar(cfg):
    """Todas las tomas, en el orden de 'secciones' y por fecha de grabación dentro de cada carpeta."""
    origen = cfg["carpeta_origen"]
    if not os.path.isdir(origen):
        raise SystemExit(f"No encuentro la carpeta del evento: {origen}\n¿Está conectado el pendrive?")
    secciones = cfg["secciones"] or sorted(
        d for d in os.listdir(origen) if os.path.isdir(os.path.join(origen, d)) and not d.startswith("."))
    faltan = [s for s in secciones if not buscar_carpeta(origen, s)]
    if faltan:
        existentes = ", ".join(sorted(d for d in os.listdir(origen) if not d.startswith(".")))
        raise SystemExit(f"No encuentro estas carpetas: {faltan}\nEn {origen} hay: {existentes}")
    salida = []
    for nombre in secciones:
        salida.append((nombre, videos_de(buscar_carpeta(origen, nombre))))
    return salida
