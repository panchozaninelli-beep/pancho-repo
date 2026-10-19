"""Carga del proyecto (proyecto.json) con valores por defecto."""
import copy
import json
import os
import re
import unicodedata

DEFAULTS = {
    "carpeta_origen": None,
    "carpeta_salida": None,
    "secciones": [],
    "entrada": {
        "carpeta": "Entrada",
        "archivo": None,              # None = primera toma de la carpeta
        "momento_puerta": None,       # "2:13.5": segundo de la toma en que cruza la puerta
        "compases_despues_del_boom": 4,
        "segundos_max_antes_del_boom": 40,
    },
    "temas": [],
    "estilo": {
        "compases_por_toma": 2,
        "compases_min": 1,
        "compases_max": 4,
        "segundos_min_toma": 1.5,
        "max_seguidas_mismo_tipo": 2,
        "ventana_intercalado": 4,
        "posicion_en_toma": 0.3,      # 0 = apenas se estabiliza, 0.5 = centro de la parte estable
        "riser_compases": 2,
        "riser_archivo": None,
        "riser_volumen": 0.5,
        "fundido_salida_compases": 1,
        "compases_min_ultimo_tema": 8,
    },
    "estabilidad": {
        "fps_analisis": 10,
        "recorte_min_inicio": 0.4,
        "recorte_min_fin": 0.4,
        "umbral_base": 0.04,          # ancho de cuadro por segundo
        "factor_mediana": 2.0,
        "ventana_estable": 0.8,
        "duracion_min_util": 1.2,
    },
    "salida": {
        "resolucion": "3840x2160",
        "fps": 30,
        "codec": "auto",              # auto | hevc_videotoolbox | hevc_nvenc | libx265 | prores
        "audio_camara": True,
        "procesos": 2,
        "borrador": True,
    },
    "procesos_analisis": 0,           # 0 = automático
}


def _mezclar(base, extra):
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _mezclar(base[k], v)
        else:
            base[k] = v
    return base


def cargar(ruta):
    ruta = os.path.abspath(ruta)
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    cfg = _mezclar(copy.deepcopy(DEFAULTS), datos)
    cfg["_dir"] = os.path.dirname(ruta)
    if not cfg["carpeta_origen"]:
        raise SystemExit("Falta 'carpeta_origen' en el proyecto (la carpeta del evento en el pendrive).")
    cfg["carpeta_origen"] = resolver(cfg, cfg["carpeta_origen"])
    if not cfg["carpeta_salida"]:
        cfg["carpeta_salida"] = os.path.join(cfg["_dir"], "salida")
    cfg["carpeta_salida"] = resolver(cfg, cfg["carpeta_salida"])
    os.makedirs(trabajo(cfg), exist_ok=True)
    return cfg


def resolver(cfg, ruta):
    ruta = os.path.expanduser(ruta)
    if os.path.isabs(ruta):
        return ruta
    for base in (cfg["_dir"], cfg.get("carpeta_origen") or ""):
        candidato = os.path.join(base, ruta)
        if os.path.exists(candidato):
            return os.path.abspath(candidato)
    return os.path.abspath(os.path.join(cfg["_dir"], ruta))


def trabajo(cfg, *partes):
    return os.path.join(cfg["carpeta_salida"], "trabajo", *partes)


def normalizar(texto):
    """Para comparar nombres de carpetas sin importar mayúsculas, tildes ni espacios dobles."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().lower()


def segundos(valor):
    """'2:13.5' -> 133.5, '1:02:03' -> 3723, 12 -> 12.0, None -> None."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    total = 0.0
    for parte in str(valor).strip().split(":"):
        total = total * 60 + float(parte.replace(",", "."))
    return total


def mmss(t):
    t = max(0.0, float(t))
    m, s = divmod(t, 60)
    return f"{int(m):02d}:{s:05.2f}"
