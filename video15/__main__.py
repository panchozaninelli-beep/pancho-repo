"""Uso:  python -m video15 <comando> [--proyecto proyecto.json]

Comandos:
  analizar    lee las carpetas, detecta la parte estable de cada toma y hace las fichas
  musica      analiza los temas (BPM, compases, boom)
  armar       arma la línea de tiempo (plan.json + guía de cortes)
  exportar    exporta las tomas recortadas para CapCut, la música mezclada y el borrador
  todo        los cuatro pasos seguidos
  fotogramas  saca un cuadro por segundo de una toma (para ubicar la entrada por la puerta)
"""
import argparse
import os
import subprocess
import sys
import time

from . import analisis, audio, config, plan, render


def main(argv=None):
    p = argparse.ArgumentParser(prog="video15", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("comando", choices=["analizar", "musica", "armar", "exportar", "todo", "fotogramas"])
    p.add_argument("archivo", nargs="?", help="(fotogramas) la toma a revisar")
    p.add_argument("--proyecto", default="proyecto.json")
    p.add_argument("--cada", type=float, default=1.0, help="(fotogramas) segundos entre cuadros")
    p.add_argument("--desde", default="0", help="(fotogramas) desde qué segundo, ej. 1:30")
    p.add_argument("--hasta", default=None, help="(fotogramas) hasta qué segundo")
    a = p.parse_args(argv)

    cfg = config.cargar(a.proyecto)
    inicio = time.time()

    if a.comando == "fotogramas":
        return fotogramas(cfg, a)
    if a.comando in ("analizar", "todo"):
        print("== Analizando tomas")
        clips = analisis.analizar(cfg)
        usables = sum(c["usable"] for c in clips)
        print(f"  {usables} de {len(clips)} tomas tienen una parte estable útil")
        print(f"  reporte: {config.trabajo(cfg, 'reporte_tomas.csv')}")
        print(f"  fichas:  {config.trabajo(cfg, 'fichas')}")
    if a.comando in ("musica", "armar", "todo"):
        print("== Analizando música")
        temas = audio.analizar_temas(cfg)
    if a.comando in ("armar", "todo"):
        print("== Armando la línea de tiempo")
        pl = plan.planear(analisis.cargar(cfg), temas, cfg)
        print(f"  duración: {config.mmss(pl['duracion'])}  |  tomas: {pl['tomas_usadas']} de {pl['tomas_disponibles']}")
        guia = render.escribir_guia(pl, cfg)
        print(f"  guía: {guia}")
        for av in pl["avisos"]:
            print(f"  ! {av}")
    if a.comando in ("exportar", "todo"):
        pl = plan.cargar(cfg)
        print("== Mezclando música")
        musica = render.mezclar_musica(pl, cfg)
        print(f"  {musica}")
        render.escribir_guia(pl, cfg)
        print("== Exportando tomas")
        carpeta = render.exportar_tomas(pl, cfg)
        print(f"  {carpeta}")
        if cfg["salida"]["borrador"]:
            print("== Armando borrador 720p")
            b = render.borrador(pl, cfg, carpeta, musica)
            if b:
                print(f"  {b}")
    print(f"Listo en {config.mmss(time.time() - inicio)}")


def fotogramas(cfg, a):
    if not a.archivo:
        raise SystemExit("Indicá la toma: python -m video15 fotogramas \"/ruta/a/la/toma.MOV\"")
    ruta = a.archivo if os.path.exists(a.archivo) else config.resolver(cfg, a.archivo)
    nombre = os.path.splitext(os.path.basename(ruta))[0]
    destino = config.trabajo(cfg, "fotogramas", nombre)
    os.makedirs(destino, exist_ok=True)
    desde = config.segundos(a.desde) or 0.0
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-y", "-ss", f"{desde}", "-i", ruta]
    if a.hasta:
        cmd += ["-t", f"{config.segundos(a.hasta) - desde}"]
    # el nombre de cada imagen es su segundo en la toma original
    cmd += ["-map", "0:v:0", "-vf", f"fps=1/{a.cada}:round=down,scale=640:-2", "-q:v", "4",
            "-start_number", "0", os.path.join(destino, "cuadro_%06d.jpg")]
    subprocess.run(cmd, check=True)
    for f in sorted(os.listdir(destino)):
        if f.startswith("cuadro_"):
            n = int(f[7:13])
            nuevo = os.path.join(destino, f"t_{config.mmss(desde + n * a.cada).replace(':', 'm')}s.jpg")
            os.replace(os.path.join(destino, f), nuevo)
    print(f"Cuadros en {destino} (el nombre es el minuto y segundo de la toma)")


if __name__ == "__main__":
    sys.exit(main())
