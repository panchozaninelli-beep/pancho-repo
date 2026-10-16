# Test 47 — aterrizaje con succión y gas frío

Juego simple en un solo archivo (`index.html`, sin dependencias). Abrilo en el navegador.

**Objetivo:** subir la rampa, salir boca abajo y estabilizar el auto con los propulsores para que caiga con las 4 ruedas (< 12° de inclinación, < 12 m/s vertical, < 13 m/s horizontal) dentro de la zona de aterrizaje verde.

Hay 7 niveles: la zona queda más lejos o más chica, hay menos gas y aparece viento. La línea punteada muestra dónde vas a caer si no tocás nada.

| Fase  | Tecla            | Acción                                         |
|-------|------------------|------------------------------------------------|
| Rampa | ↑ / W            | Acelerar                                       |
| Rampa | ↓ / S            | Frenar                                         |
| Rampa | Espacio          | Prende/apaga la succión (arranca prendida; necesaria en pared y techo, gasta gas)|
| Aire  | ↑ / W            | Propulsor principal (empuja hacia el techo del auto) |
| Aire  | ← → / A D        | Propulsores de giro                            |
| —     | R / Enter        | Reiniciar / siguiente test                     |
| —     | M                | Sonido on/off                                  |
| —     | 1–7              | Elegir un nivel ya desbloqueado                |

El HUD mide cuántos segundos usaste cada propulsor, el gas restante y la actitud del auto. En celular aparecen botones táctiles.
