# Test 47 — aterrizaje con succión y gas frío

Juego en un solo archivo (`index.html`, sin dependencias). Abrilo en el navegador.

Al entrar hay una pantalla de carga con el auto volando y un menú con START, niveles, ranking y sonido. ESC vuelve al menú durante el juego.

El ranking mundial usa la base de datos del artifact publicado en claude.ai; abriendo el archivo local se muestra solo tu puntaje.

**Objetivo:** subir la rampa, salir boca abajo y estabilizar el auto con los propulsores para que caiga con las 4 ruedas (< 12° de inclinación, < 12 m/s vertical, < 13 m/s horizontal) dentro de la zona de aterrizaje verde.

Hay 7 niveles: la zona queda más lejos o más chica, hay menos gas y aparece viento. La línea punteada muestra dónde vas a caer si no tocás nada.

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
| —     | 1–7              | Elegir un nivel ya desbloqueado                |

El HUD mide cuántos segundos usaste cada propulsor, el gas restante y la actitud del auto. En celular aparecen botones táctiles.
