"""Música: pulso, compases, detección del 'boom', riser y mezcla."""
import json
import os
import subprocess
import wave

import numpy as np

from . import config

SR_ANALISIS = 22050
SR_SALIDA = 48000
HOP = 512
NFFT = 2048


def cargar(ruta, sr=SR_ANALISIS, canales=1):
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-i", ruta, "-map", "0:a:0",
           "-f", "f32le", "-ac", str(canales), "-ar", str(sr), "-"]
    datos = subprocess.run(cmd, capture_output=True)
    if datos.returncode != 0:
        raise SystemExit(f"No pude leer el audio {ruta}: {datos.stderr.decode(errors='ignore').strip()}")
    x = np.frombuffer(datos.stdout, np.float32)
    return x.reshape(-1, canales) if canales > 1 else x


def _espectro(x):
    n = 1 + max(0, (len(x) - NFFT) // HOP)
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n)[:, None]
    marcos = x[idx] * np.hanning(NFFT)[None, :]
    return np.abs(np.fft.rfft(marcos, axis=1))


def _flujo(mag):
    log = np.log1p(100 * mag)
    d = np.maximum(0, np.diff(log, axis=0)).sum(axis=1)
    d = np.concatenate([[0], d])
    k = 16
    d = d - np.convolve(d, np.ones(k) / k, mode="same")
    d = np.maximum(d, 0)
    return d / (d.std() + 1e-9)


def _tempo(onset, bpm_fijo=None):
    fps = SR_ANALISIS / HOP
    if bpm_fijo:
        return 60 * fps / bpm_fijo
    ac = np.correlate(onset, onset, mode="full")[len(onset) - 1:]
    lags = np.arange(len(ac))
    bpms = np.where(lags > 0, 60 * fps / np.maximum(lags, 1), 0)
    validos = (bpms >= 60) & (bpms <= 190)
    prior = np.exp(-0.5 * (np.log2(np.maximum(bpms, 1) / 120) / 0.9) ** 2)
    puntaje = np.where(validos, ac * prior, 0)
    return float(lags[np.argmax(puntaje)])


def _pulsos(onset, periodo, rigidez=100.0):
    """Seguimiento de pulsos por programación dinámica (Ellis, 2007)."""
    n = len(onset)
    sigma = max(1.0, periodo / 32)
    g = np.exp(-0.5 * (np.arange(-int(4 * sigma), int(4 * sigma) + 1) / sigma) ** 2)
    local = np.convolve(onset, g, mode="same")
    acum = local.copy()
    atras = np.full(n, -1)
    lo, hi = int(round(periodo / 2)), int(round(2 * periodo))
    for t in range(lo, n):
        ps = np.arange(max(0, t - hi), t - lo + 1)
        if len(ps) == 0:
            continue
        costo = -rigidez * np.log((t - ps) / periodo) ** 2
        cand = acum[ps] + costo
        j = int(np.argmax(cand))
        acum[t] = local[t] + cand[j]
        atras[t] = ps[j]
    cola = max(0, n - int(round(2 * periodo)))
    t = cola + int(np.argmax(acum[cola:]))
    pulsos = [t]
    while atras[t] >= 0:
        t = atras[t]
        pulsos.append(t)
    return np.array(pulsos[::-1])


def analizar_tema(ruta, boom_manual=None, bpm_fijo=None):
    x = cargar(ruta)
    dur = len(x) / SR_ANALISIS
    mag = _espectro(x)
    onset = _flujo(mag)
    periodo = _tempo(onset, bpm_fijo)
    marcos = _pulsos(onset, periodo)
    t_marco = lambda f: (f * HOP + NFFT / 2) / SR_ANALISIS
    pulsos = t_marco(marcos)

    # Energía por pulso y graves (bombo) para encontrar el "uno" de cada compás.
    frec = np.fft.rfftfreq(NFFT, 1 / SR_ANALISIS)
    graves = _flujo(mag[:, frec < 150])
    energia = np.sqrt((mag ** 2).mean(axis=1))
    fase = None
    if boom_manual is not None:
        cerca = int(np.argmin(np.abs(pulsos - boom_manual)))
        fase = cerca % 4
        if abs(pulsos[cerca] - boom_manual) < 0.2:
            pulsos[cerca] = boom_manual
    if fase is None:
        fase = int(np.argmax([graves[marcos[p::4]].sum() for p in range(4)]))
    compases = pulsos[fase::4]

    boom = boom_manual if boom_manual is not None else _buscar_boom(compases, energia, t_marco)
    return {
        "archivo": ruta,
        "duracion": dur,
        "bpm": round(60 * SR_ANALISIS / HOP / periodo, 1),
        "pulsos": [round(float(p), 4) for p in pulsos],
        "compases": [round(float(c), 4) for c in compases],
        "boom": round(float(boom), 3) if boom is not None else None,
        "boom_manual": boom_manual is not None,
    }


def _buscar_boom(compases, energia, t_marco):
    """El 'boom' = el inicio de compás donde la energía salta más fuerte y se queda alta."""
    if len(compases) < 10:
        return None
    tiempos = t_marco(np.arange(len(energia)))
    def media(a, b):
        m = (tiempos >= a) & (tiempos < b)
        return energia[m].mean() if m.any() else 0.0
    tope = energia.max() + 1e-9
    mejor, t_mejor = 0.0, None
    for i in range(4, len(compases) - 4):
        antes = media(compases[i - 4], compases[i])
        despues = media(compases[i], compases[i + 4])
        puntaje = (despues / (antes + 1e-9)) * (despues / tope)
        if puntaje > mejor:
            mejor, t_mejor = puntaje, compases[i]
    return t_mejor


def analizar_temas(cfg, log=print):
    dir_cache = config.trabajo(cfg, "cache_musica")
    os.makedirs(dir_cache, exist_ok=True)
    salida = []
    for i, tema in enumerate(cfg["temas"]):
        ruta = config.resolver(cfg, tema["archivo"])
        if not os.path.exists(ruta):
            raise SystemExit(f"No encuentro el tema: {ruta}")
        boom = config.segundos(tema.get("boom"))
        bpm = tema.get("bpm")
        clave = f"{os.path.basename(ruta)}_{os.path.getsize(ruta)}_{boom}_{bpm}".replace(" ", "_")
        cache = os.path.join(dir_cache, clave + ".json")
        if os.path.exists(cache):
            with open(cache, encoding="utf-8") as f:
                a = json.load(f)
        else:
            a = analizar_tema(ruta, boom, bpm)
            with open(cache, "w", encoding="utf-8") as f:
                json.dump(a, f)
        a["archivo"] = ruta
        salida.append(a)
        marca = "(indicado por vos)" if a["boom_manual"] else "(detectado)"
        boom_txt = config.mmss(a["boom"]) if a["boom"] is not None else "-"
        log(f"  {i + 1}. {os.path.basename(ruta)}: {a['bpm']} BPM, {config.mmss(a['duracion'])}, "
            f"boom {boom_txt} {marca}")
    return salida


def riser(duracion, sr=SR_SALIDA, semilla=7):
    """Riser sintético: ruido que se abre hacia los agudos + barrido ascendente."""
    n = max(1, int(duracion * sr))
    t = np.linspace(0, 1, n, endpoint=False)
    rng = np.random.default_rng(semilla)
    # Ruido filtrado por bloques (FFT): una banda que sube de ~300 Hz a ~8 kHz.
    bloque, salto = 4096, 2048
    ventana = np.hanning(bloque)[:, None]
    frec = np.fft.rfftfreq(bloque, 1 / sr)[:, None]
    filtrado = np.zeros((n + bloque, 2))
    for ini in range(0, n, salto):
        p = ini / n
        centro = 300 * (8000 / 300) ** p
        forma = np.exp(-0.5 * (np.log2((frec + 1) / centro) / 1.2) ** 2)
        trozo = np.fft.rfft(rng.standard_normal((bloque, 2)) * ventana, axis=0) * forma
        filtrado[ini: ini + bloque] += np.fft.irfft(trozo, n=bloque, axis=0) * ventana
    filtrado = filtrado[:n]
    f = 180 * (12 ** t)  # de 180 Hz a ~2,1 kHz
    fase = 2 * np.pi * np.cumsum(f) / sr
    barrido = (np.sin(fase) + 0.5 * np.sin(fase * 1.5)) * 0.25
    señal = 0.6 * filtrado / (np.abs(filtrado).max() + 1e-9) + barrido[:, None]
    env = t ** 2.2
    env[-int(0.01 * sr):] *= np.linspace(1, 0, int(0.01 * sr))
    return (señal * env[:, None]).astype(np.float32)


def escribir_wav(ruta, x, sr=SR_SALIDA):
    x = np.clip(x, -1, 1)
    datos = (x * 32767).astype("<i2")
    with wave.open(ruta, "wb") as w:
        w.setnchannels(x.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(datos.tobytes())
