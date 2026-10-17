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

El juego está en **castellano e inglés**: el idioma se elige con el selector ES / EN del menú (la primera vez se toma el del navegador).

**Modo celular:** en pantallas táctiles el auto se endereza solo y se inclina hacia la zona cuando frenás con ▲, cae un 28% más lento y los límites de aterrizaje son más amplios (18°, 15 m/s de caída, 16 m/s de deriva). En computadora el manejo es el original.

El HUD mide cuántos segundos usaste cada propulsor, el gas restante y la actitud del auto. En celular aparecen botones táctiles.

## Ranking mundial abierto (sitio propio)

En claude.ai el ranking usa la base de datos del artifact, donde solo el dueño y sus colaboradores pueden guardar. Para que cualquiera pueda entrar al ranking:

1. **Supabase**: ya configurado en el proyecto `roadster` (región São Paulo). `index.html` apunta a él con su clave pública *anon* (es pública por diseño; la tabla solo se escribe a través de `submit_score`). `supabase.sql` tiene el esquema por si hay que recrearlo.
2. **GitHub Pages + dominio**: el juego se publica en **https://roadsterplay.com** (archivo `CNAME`). En el DNS del dominio (GoDaddy): 4 registros `A` en `@` → `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`, y un `CNAME` en `www` → `panchozaninelli-beep.github.io`. En *Settings → Pages*: rama `claude/trusting-maxwell-2w1suw`, carpeta `/`, dominio `roadsterplay.com`, *Enforce HTTPS*.

Cada nombre lo "reclama" el primer dispositivo que lo usa; nadie más puede guardar puntajes con ese nombre. Los puntajes los calcula el navegador, así que alguien con conocimientos técnicos podría inventar uno: para un ranking competitivo serio haría falta validar las partidas en el servidor.

---
© 2026 Toma Uno Studio. Todos los derechos reservados (ver `LICENSE`).
