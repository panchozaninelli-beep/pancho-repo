# Roadster — aterrizaje con succión y gas frío

Juego en un solo archivo (`index.html`, sin dependencias). Abrilo en el navegador.

Al entrar hay una pantalla roja que se abre en círculo hacia la pantalla de carga con el auto volando y un menú con START, niveles, ranking y sonido. ESC vuelve al menú durante el juego.

El ranking mundial usa la base de datos del artifact publicado en claude.ai; abriendo el archivo local se muestra solo tu puntaje.

**Objetivo:** subir la rampa, salir boca abajo y estabilizar el auto con los propulsores para que caiga con las 4 ruedas (< 12° de inclinación, < 12 m/s vertical, < 13 m/s horizontal) dentro de la zona de aterrizaje verde.

Hay 8 niveles: la zona queda más lejos o más chica, hay menos gas y aparece viento. Los niveles 1–4 tienen cámara lenta de ayuda. La línea punteada muestra dónde vas a caer si no tocás nada.

| Fase  | Tecla            | Acción                                         |
|-------|------------------|------------------------------------------------|
| Rampa | ↑ / W            | Acelerar                                       |
| Rampa | ↓ / S            | Frenar                                         |
| Rampa | Espacio          | Prende/apaga la succión (arranca prendida; necesaria en pared y techo, gasta gas)|
| Aire  | ↑ / W            | Propulsor principal (empuja hacia el techo del auto) |
| Aire  | ← → / A D        | Propulsores de giro                            |
| Aire  | Espacio          | Cámara lenta 5 s, una vez por intento (solo niveles 1–3) |
| —     | Espacio / R      | Reiniciar / siguiente test                     |
| —     | M                | Sonido on/off                                  |
| —     | 1–8              | Elegir un nivel ya desbloqueado                |
| —     | P                | Pausa                                          |
| —     | Esc              | Volver al menú                                 |

El HUD mide cuántos segundos usaste cada propulsor, el gas restante y la actitud del auto. En celular aparecen botones táctiles.

## Ranking mundial abierto (sitio propio)

En claude.ai el ranking usa la base de datos del artifact, donde solo el dueño y sus colaboradores pueden guardar. Para que cualquiera pueda entrar al ranking:

1. **Supabase** (gratis): creá un proyecto en https://supabase.com, abrí *SQL Editor*, pegá el contenido de `supabase.sql` y ejecutalo.
2. En *Project Settings → API* copiá la **Project URL** y la clave **anon public**, y pegalas en `SUPABASE_URL` y `SUPABASE_KEY` al principio del ranking en `index.html`. La clave anon es pública por diseño; la tabla solo se puede escribir a través de `submit_score`.
3. **GitHub Pages**: en el repo, *Settings → Pages → Build and deployment*, elegí *Deploy from a branch* y la rama con `index.html` (carpeta `/`). El juego queda en `https://<usuario>.github.io/<repo>/`.

Cada nombre lo "reclama" el primer dispositivo que lo usa; nadie más puede guardar puntajes con ese nombre. Los puntajes los calcula el navegador, así que alguien con conocimientos técnicos podría inventar uno: para un ranking competitivo serio haría falta validar las partidas en el servidor.

---
© 2026 Toma Uno Studio. Todos los derechos reservados (ver `LICENSE`).
