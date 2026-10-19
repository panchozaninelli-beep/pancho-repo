"""Arma la línea de tiempo: orden, intercalado, duración de cada toma sobre los compases y música."""
import json
import math
import os

import numpy as np

from . import config


# ---------------------------------------------------------------- etiquetas

def cargar_etiquetas(cfg):
    ruta = config.trabajo(cfg, "etiquetas.json")
    if not os.path.exists(ruta):
        return {}
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _etiqueta(etiquetas, clip):
    return (etiquetas.get(f"{clip['carpeta']}/{clip['archivo']}")
            or etiquetas.get(clip["archivo"]) or {})


def preparar_tomas(clips, cfg, avisos):
    etiquetas = cargar_etiquetas(cfg)
    nit = np.array([c["nitidez"] for c in clips]) if clips else np.zeros(0)
    escala = np.median(nit) + 1e-9 if len(nit) else 1.0
    tomas = []
    for c in clips:
        e = _etiqueta(etiquetas, c)
        if e.get("descartar"):
            continue
        t = dict(c)
        t["estrella"] = bool(e.get("estrella"))
        t["tipo"] = e.get("tipo") or c["tipo"]
        t["nota"] = e.get("nota", "")
        if not c["usable"]:
            if not t["estrella"]:
                continue
            t["entrada"], t["salida"] = c["duracion"] * 0.2, c["duracion"] * 0.8
            t["util"] = t["salida"] - t["entrada"]
            avisos.append(f"{c['archivo']}: no tiene parte estable, pero está marcada como estrella; se usa igual.")
        puntaje = math.log((c["nitidez"] + 1e-9) / escala)
        if c["brillo"] < 0.08 or c["brillo"] > 0.92:
            puntaje -= 1.0
        t["puntaje"] = puntaje + (5 if t["estrella"] else 0)
        tomas.append(t)
    return tomas


# ---------------------------------------------------------------- intercalado

def intercalar(tomas, max_seguidas, ventana):
    """Mantiene el orden cronológico pero evita más de N tomas seguidas del mismo tipo,
    adelantando una toma cercana (como mucho 'ventana' posiciones) de otro tipo."""
    pendientes, salida = list(tomas), []
    while pendientes:
        elegida = 0
        ultimos = [t["tipo"] for t in salida[-max_seguidas:]]
        if len(ultimos) == max_seguidas and len(set(ultimos)) == 1 and pendientes[0]["tipo"] == ultimos[0]:
            for j in range(1, min(ventana + 1, len(pendientes))):
                if pendientes[j]["tipo"] != ultimos[0]:
                    elegida = j
                    break
        salida.append(pendientes.pop(elegida))
    return salida


# ---------------------------------------------------------------- bloques

def _es_entrada(tema, cfg):
    if "es_entrada" in tema:
        return bool(tema["es_entrada"])
    return config.normalizar(tema.get("empieza_con") or "") == config.normalizar(cfg["entrada"]["carpeta"])


def _indice_inicio(tomas, ref):
    n = config.normalizar(ref)
    for i, t in enumerate(tomas):
        if config.normalizar(t["carpeta"]) == n or config.normalizar(t["archivo"]) == n:
            return i
    return None


def armar_bloques(tomas, temas_cfg, temas, cfg):
    """Cada bloque = tomas desde donde arranca un tema 'anclado' hasta el siguiente anclado."""
    inicios = []
    for j, tema in enumerate(temas_cfg):
        ref = tema.get("empieza_con")
        if j == 0:
            inicios.append((0, j))
            continue
        if not ref:
            continue
        if _es_entrada(tema, cfg) and cfg["entrada"].get("archivo"):
            ref = cfg["entrada"]["archivo"]
        i = _indice_inicio(tomas, ref)
        if i is None:
            raise SystemExit(f"El tema {j + 1} dice empieza_con '{ref}', pero no hay ninguna toma usable ahí.")
        if inicios and i <= inicios[-1][0]:
            raise SystemExit(f"El tema {j + 1} ('{ref}') arranca antes o junto con el tema anterior. Revisá el orden.")
        inicios.append((i, j))
    bloques = []
    for b, (i, j) in enumerate(inicios):
        i_fin = inicios[b + 1][0] if b + 1 < len(inicios) else len(tomas)
        j_fin = inicios[b + 1][1] if b + 1 < len(inicios) else len(temas_cfg)
        bloques.append({
            "tomas": tomas[i:i_fin],
            "temas": [dict(temas[k], indice=k, cfg=temas_cfg[k]) for k in range(j, j_fin)],
            "entrada": _es_entrada(temas_cfg[j], cfg) and j > 0,
        })
    return bloques


# ---------------------------------------------------------------- un bloque

def _compas_medio(tema):
    c = np.diff(tema["compases"])
    return float(np.median(c)) if len(c) else 2.0


def planear_bloque(bloque, cfg, avisos):
    est = cfg["estilo"]
    temas = bloque["temas"]
    tomas = bloque["tomas"]
    compas = float(np.median([_compas_medio(t) for t in temas]))

    ancla = None
    if bloque["entrada"]:
        ancla, tomas = tomas[0], tomas[1:]
    tomas = intercalar(tomas, est["max_seguidas_mismo_tipo"], est["ventana_intercalado"])

    # duración deseada de cada toma (en compases)
    for t in tomas:
        kmax = est["compases_max"] + (1 if t["estrella"] else 0)
        kmax = min(kmax, int(t["util"] // compas))
        kmin = min(kmax, max(est["compases_min"], math.ceil(est["segundos_min_toma"] / compas)))
        t["kmin"], t["kmax"] = kmin, kmax
        t["k"] = min(kmax, max(kmin, est["compases_por_toma"] + (1 if t["estrella"] else 0)))
    cortas = [t for t in tomas if t["kmax"] < 1]
    for t in cortas:
        avisos.append(f"{t['archivo']}: su parte estable ({t['util']:.1f}s) es más corta que un compás; queda afuera.")
    tomas = [t for t in tomas if t["kmax"] >= 1]

    # --- segmentos de música
    segmentos = []
    largo_ancla = 0.0
    if ancla:
        ent = cfg["entrada"]
        puerta = config.segundos(ent["momento_puerta"])
        t0 = temas[0]
        if t0["boom"] is None:
            raise SystemExit(f"No encontré el boom de {os.path.basename(t0['archivo'])}; indicalo con \"boom\": \"m:ss\".")
        estable = ancla["entrada"] or 0.0
        previo = min(t0["boom"], puerta - estable, ent["segundos_max_antes_del_boom"])
        if previo < 1.0:
            previo = min(t0["boom"], puerta, ent["segundos_max_antes_del_boom"])
        compases_post = [c for c in t0["compases"] if c > t0["boom"] + 0.05]
        disponible_post = (ancla["salida"] or ancla["duracion"]) - puerta
        n_post = ent["compases_despues_del_boom"]
        while n_post > 1 and compases_post[n_post - 1] - t0["boom"] > disponible_post:
            n_post -= 1
        fin_ancla_tema = compases_post[n_post - 1] if compases_post else t0["boom"] + 4 * compas
        largo_ancla = fin_ancla_tema - (t0["boom"] - previo)
        ancla = dict(ancla, entrada_usada=puerta - previo, previo_boom=previo)
        inicio_tema0 = t0["boom"] - previo
    else:
        inicio_tema0 = config.segundos(temas[0]["cfg"].get("desde")) or 0.0

    necesario = largo_ancla + sum(t["k"] * compas for t in tomas)
    acumulado = 0.0
    for n, tema in enumerate(temas):
        ini = inicio_tema0 if n == 0 else (config.segundos(tema["cfg"].get("desde")) or 0.0)
        tope = config.segundos(tema["cfg"].get("hasta")) or tema["duracion"]
        compases = [c for c in tema["compases"] if ini < c <= tope - 0.05]
        fin_completo = compases[-1] if compases else tope
        disponible = fin_completo - ini
        if acumulado + disponible >= necesario:
            falta = necesario - acumulado
            minimo = est["compases_min_ultimo_tema"] * _compas_medio(tema)
            if n > 0 and falta < minimo and abs(acumulado - necesario) < abs(acumulado + minimo - necesario):
                avisos.append(f"Tema {tema['indice'] + 1} no se usa: sobraba muy poco tiempo para él.")
                break
            objetivo = ini + max(falta, minimo if n > 0 else falta)
            fin = min((c for c in compases), key=lambda c: abs(c - objetivo), default=fin_completo)
            segmentos.append({"tema": tema, "desde": ini, "hasta": fin, "inicio": acumulado})
            acumulado += fin - ini
            for resto in temas[n + 1:]:
                avisos.append(f"Tema {resto['indice'] + 1} no se usa: las tomas de este bloque ya se cubren con los anteriores.")
            break
        segmentos.append({"tema": tema, "desde": ini, "hasta": fin_completo, "inicio": acumulado})
        acumulado += disponible
    else:
        if necesario - acumulado > compas:
            avisos.append(f"Bloque que empieza en '{(ancla or tomas[0])['carpeta']}': faltan ~{config.mmss(necesario - acumulado)} "
                          f"de música para usar todas las tomas a su largo ideal; se acortan tomas o se dejan afuera las peores. "
                          f"Si querés usar todo, agregá otro tema a este bloque.")

    # --- grilla de cortes (inicios de compás) en tiempo del bloque
    # Puntos obligados: comienzo, cambios de tema, fin de la entrada y final. Los compases que caen
    # demasiado cerca de un punto obligado (p. ej. el primer pulso a 0,03 s del inicio) se descartan.
    obligados = {0.0, round(largo_ancla, 4)} if ancla else {0.0}
    opcionales = []
    for s in segmentos:
        obligados.add(round(s["inicio"], 4))
        obligados.add(round(s["inicio"] + s["hasta"] - s["desde"], 4))
        opcionales += [s["inicio"] + c - s["desde"] for c in s["tema"]["compases"] if s["desde"] < c < s["hasta"]]
    distancia = 0.45 * compas
    obl = sorted(obligados)
    grilla = sorted(obl + [round(g, 4) for g in opcionales
                           if min(abs(g - o) for o in obl) >= distancia])
    limpia = [grilla[0]]
    for g in grilla[1:]:
        if g - limpia[-1] >= distancia or g in obligados:
            if g in obligados and g - limpia[-1] < distancia and limpia[-1] not in obligados:
                limpia.pop()
            limpia.append(g)
    grilla = limpia
    s0 = grilla.index(round(largo_ancla, 4)) if ancla else 0
    ranuras = len(grilla) - 1 - s0

    # --- ajustar compases por toma para llenar exactamente la grilla
    descartadas = []
    while sum(t["k"] for t in tomas) > ranuras:
        achicables = [t for t in tomas if t["k"] > t["kmin"]]
        if achicables:
            max(achicables, key=lambda t: (t["k"], -t["puntaje"]))["k"] -= 1
            continue
        candidatas = [t for t in tomas if not t["estrella"]] or tomas
        peor = min(candidatas, key=lambda t: t["puntaje"])
        tomas.remove(peor)
        descartadas.append(peor)
    while sum(t["k"] for t in tomas) < ranuras:
        estirables = [t for t in tomas if t["k"] < t["kmax"]]
        if not estirables:
            break
        min(estirables, key=lambda t: (t["k"], -t["puntaje"]))["k"] += 1

    # --- recorrer la grilla real (los compases no miden todos igual)
    pos, sobrante, colocadas = s0, 0, []
    for t in tomas:
        k = t["k"]
        while k > 1 and grilla[min(pos + k, len(grilla) - 1)] - grilla[pos] > t["util"]:
            k -= 1
            sobrante += 1
        while sobrante and k < t["kmax"] and pos + k + 1 < len(grilla) and grilla[pos + k + 1] - grilla[pos] <= t["util"]:
            k += 1
            sobrante -= 1
        if pos + k >= len(grilla):
            k = len(grilla) - 1 - pos
        if k <= 0:
            descartadas.append(t)
            continue
        colocadas.append(dict(t, inicio_bloque=grilla[pos], duracion_bloque=grilla[pos + k] - grilla[pos]))
        pos += k
    largo = grilla[pos]
    if pos < len(grilla) - 1:
        avisos.append(f"Bloque '{(ancla or tomas[0])['carpeta']}': la música se corta en {config.mmss(largo)} (un inicio de compás) "
                      f"porque no alcanzan las tomas.")
    for t in descartadas:
        avisos.append(f"{t['archivo']} ({t['carpeta']}): queda afuera para que entre la música (es de las de menor calidad).")

    # recortar segmentos de música al largo final
    musica = []
    for s in segmentos:
        if s["inicio"] >= largo - 1e-3:
            continue
        hasta = min(s["hasta"], s["desde"] + largo - s["inicio"])
        musica.append({"archivo": s["tema"]["archivo"], "indice": s["tema"]["indice"], "desde": s["desde"],
                       "hasta": hasta, "inicio": s["inicio"], "compas": _compas_medio(s["tema"]),
                       "boom": s["tema"]["boom"]})
    if ancla:
        colocadas.insert(0, dict(ancla, inicio_bloque=0.0, duracion_bloque=largo_ancla, es_entrada=True))
    return {"tomas": colocadas, "musica": musica, "largo": largo}


# ---------------------------------------------------------------- todo junto

def planear(clips, temas, cfg):
    avisos = []
    if not cfg["temas"]:
        raise SystemExit("Falta la lista de 'temas' en el proyecto.")
    tomas = preparar_tomas(clips, cfg, avisos)
    if not tomas:
        raise SystemExit("No quedó ninguna toma usable.")
    hay_entrada = any(_es_entrada(t, cfg) for t in cfg["temas"][1:])
    if hay_entrada and config.segundos(cfg["entrada"]["momento_puerta"]) is None:
        raise SystemExit(
            "Falta 'momento_puerta' en 'entrada': el segundo exacto de la toma de entrada en que la quinceañera "
            "cruza la puerta (ej. \"2:13.5\"). Podés buscarlo con:  python -m video15 fotogramas <toma>")

    fps = cfg["salida"]["fps"]
    bloques = armar_bloques(tomas, cfg["temas"], temas, cfg)
    plan_tomas, plan_musica, t0 = [], [], 0.0
    for b in bloques:
        r = planear_bloque(b, cfg, avisos)
        for t in r["tomas"]:
            t["inicio"] = t0 + t["inicio_bloque"]
            t["fin"] = t["inicio"] + t["duracion_bloque"]
            plan_tomas.append(t)
        for m in r["musica"]:
            m["inicio"] += t0
            plan_musica.append(m)
        t0 += r["largo"]

    # redondear cortes a cuadros (sin arrastrar error)
    salida = []
    pos_toma = cfg["estilo"]["posicion_en_toma"]
    for n, t in enumerate(plan_tomas, 1):
        f_ini, f_fin = round(t["inicio"] * fps), round(t["fin"] * fps)
        dur = (f_fin - f_ini) / fps
        if t.get("es_entrada"):
            entrada = t["entrada_usada"] + (f_ini / fps - t["inicio"])
            nota = (f"ENTRADA: cruza la puerta en {config.mmss(t['inicio'] + t['previo_boom'])} "
                    f"= boom del tema")
        else:
            libre = max(0.0, t["util"] - dur)
            entrada = t["entrada"] + libre * pos_toma
            if dur > t["util"] + 1e-3:
                entrada = max(0.0, t["entrada"] - (dur - t["util"]) / 2)
            nota = t.get("nota", "")
        salida.append({
            "n": n, "ruta": t["ruta"], "carpeta": t["carpeta"], "archivo": t["archivo"],
            "tipo": t["tipo"], "estrella": t.get("estrella", False),
            "cuadro_inicio": f_ini, "cuadros": f_fin - f_ini,
            "inicio": f_ini / fps, "duracion": dur, "entrada_en_original": round(entrada, 4),
            "nota": nota, "color_primaries": t.get("color_primaries"),
            "color_trc": t.get("color_trc"), "colorspace": t.get("colorspace"), "audio": t.get("audio", True),
        })
    duracion = salida[-1]["inicio"] + salida[-1]["duracion"]
    for m in plan_musica:
        m["inicio"] = round(m["inicio"] * fps) / fps
    plan = {"fps": fps, "duracion": duracion, "tomas": salida, "musica": plan_musica,
            "avisos": avisos, "tomas_disponibles": len(clips), "tomas_usadas": len(salida)}
    with open(config.trabajo(cfg, "plan.json"), "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=1, ensure_ascii=False)
    return plan


def cargar(cfg):
    ruta = config.trabajo(cfg, "plan.json")
    if not os.path.exists(ruta):
        raise SystemExit("Primero hay que correr: armar")
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)
