"""Genera un evento de prueba: carpetas con tomas que tiemblan al principio y al final,
y temas con un 'boom' conocido. Sirve para probar la herramienta sin el material real.

    python pruebas/generar_material.py /tmp/evento_prueba
"""
import json
import os
import subprocess
import sys
import wave

import numpy as np

CARPETAS = [("Drone", 2, 8), ("Inicio afuera", 3, 7), ("Habitacion", 4, 6),
            ("Entrada", 5, 7), ("Lo que queda", 8, 6)]
FOCALES = [13, 24, 48]


def fondo(destino):
    """Imagen fija con textura (escena quieta): así lo único que se mueve es la 'cámara'."""
    ruta = os.path.join(os.path.dirname(os.path.dirname(destino)), ".fondo.png")
    if not os.path.exists(ruta):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "mandelbrot=size=1280x720:start_scale=0.4",
                        "-frames:v", "1", ruta], check=True)
    return ruta


def toma(destino, dur, fecha, focal, temblor_ini=1.2, temblor_fin=1.0, semilla=0):
    # una imagen fija con textura, recortada con un desplazamiento que tiembla al inicio y al final
    x = (f"200+if(lt(t,{temblor_ini}),60*sin(t*31+{semilla})*sin(t*7),"
         f"if(gt(t,{dur - temblor_fin}),60*sin(t*29)*sin(t*5),0))+3*t")
    y = (f"120+if(lt(t,{temblor_ini}),40*cos(t*23+{semilla}),"
         f"if(gt(t,{dur - temblor_fin}),40*cos(t*19),0))")
    cmd = ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", "30", "-t", str(dur), "-i", fondo(destino),
           "-f", "lavfi", "-i", f"sine=frequency={300 + semilla * 40}:duration={dur}",
           "-filter_complex", f"[0:v]crop=800:450:'{x}':'{y}',scale=640:360,"
                              f"drawtext=text='{os.path.basename(destino)}':x=10:y=10:fontsize=24:fontcolor=white[v]",
           "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
           "-c:a", "aac", "-shortest",
           "-metadata", f"creation_time={fecha}",
           "-metadata", f"com.apple.quicktime.camera.focal_length.35mm_equivalent={focal}",
           "-movflags", "use_metadata_tags", destino]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        # sin drawtext (falta de fuentes) también sirve
        i = cmd.index("-filter_complex") + 1
        cmd[i] = cmd[i].split(",drawtext")[0] + "[v]"
        subprocess.run(cmd, check=True)


def tema(destino, bpm, dur, boom, semilla):
    sr = 44100
    n = int(dur * sr)
    t = np.arange(n) / sr
    x = np.zeros(n)
    beat = 60 / bpm
    rng = np.random.default_rng(semilla)
    for k in range(int(dur / beat)):
        a = int(k * beat * sr)
        fuerte = k * beat >= boom
        m = min(n - a, int(0.25 * sr))
        tt = np.arange(m) / sr
        if fuerte or k % 4 == 0:
            amp = 0.9 if fuerte else 0.15
            x[a:a + m] += amp * np.sin(2 * np.pi * (50 + 80 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 12)
        h = min(n - a, int(0.05 * sr))
        x[a:a + h] += 0.05 * rng.standard_normal(h) * np.exp(-np.arange(h) / sr * 60)
    x += np.where(t >= boom, 0.25, 0.06) * np.sin(2 * np.pi * 110 * t)
    x /= np.abs(x).max()
    with wave.open(destino, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((x * 30000).astype("<i2").tobytes())


def main(base):
    origen = os.path.join(base, "PENDRIVE", "Quince Prueba")
    os.makedirs(origen, exist_ok=True)
    minuto = 0
    for c, (carpeta, cantidad, dur) in enumerate(CARPETAS):
        d = os.path.join(origen, carpeta)
        os.makedirs(d, exist_ok=True)
        for i in range(cantidad):
            minuto += 3
            larga = carpeta == "Entrada" and i == 0
            fecha = f"2026-09-20T{20 + minuto // 60:02d}:{minuto % 60:02d}:00Z"
            toma(os.path.join(d, f"IMG_{1000 + c * 100 + i}.MOV"), 40 if larga else dur, fecha,
                 FOCALES[i % 3], semilla=c * 10 + i)
        # basura típica de macOS en pendrives
        open(os.path.join(d, f"._IMG_{1000 + c * 100}.MOV"), "wb").write(b"\0" * 100)
    musica = os.path.join(base, "musica")
    os.makedirs(musica, exist_ok=True)
    tema(os.path.join(musica, "01_inicio.wav"), 100, 45, 16, 1)
    tema(os.path.join(musica, "02_entrada.wav"), 124, 60, 23.2, 2)
    tema(os.path.join(musica, "03_fiesta.wav"), 128, 70, 15, 3)
    proyecto = {
        "carpeta_origen": origen,
        "carpeta_salida": os.path.join(base, "salida"),
        "secciones": ["Drone", "Inicio afuera", "Habitación", "Entrada", "Lo que queda"],
        "entrada": {"carpeta": "Entrada", "momento_puerta": "0:20"},
        "temas": [
            {"archivo": os.path.join(musica, "01_inicio.wav"), "empieza_con": "Drone"},
            {"archivo": os.path.join(musica, "02_entrada.wav"), "empieza_con": "Entrada"},
            {"archivo": os.path.join(musica, "03_fiesta.wav"), "empieza_con": "Lo que queda"},
        ],
        "salida": {"resolucion": "1280x720", "fps": 30},
    }
    with open(os.path.join(base, "proyecto.json"), "w", encoding="utf-8") as f:
        json.dump(proyecto, f, indent=2, ensure_ascii=False)
    print(os.path.join(base, "proyecto.json"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "evento_prueba")
