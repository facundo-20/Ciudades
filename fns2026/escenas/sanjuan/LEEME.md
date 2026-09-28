# Recorrido por San Juan: los dinosaurios muestran la provincia

Siete postales hiperrealistas (Cycles). En cada una, un *Sanjuansaurus gordilloi*, que quiere decir "lagarto de San Juan", presenta un lugar icónico de hoy. Lo acompaña otra especie de Ischigualasto.

```bash
python3 postales_sanjuan.py -- salida/ [--postales hongo bochas alcazar leoncito cuesta catedral bicentenario] [--calidad prueba|media|led]
```

| Postal | Lugar | Hito |
|---|---|---|
| hongo | El Hongo, Valle de la Luna | Meshy (`el_hongo`) + barrancas con estratos |
| bochas | Cancha de Bochas | concreciones de 5 a 90 cm (Meshy `bochas` o a medida) |
| alcazar | Cerro Alcázar, Barreal | Meshy (`cerro_alcazar`), con la cordillera atrás |
| leoncito | Pampa El Leoncito | carro velero sobre el barreal blanco, CASLEO arriba de un cerro, atardecer |
| cuesta | Dique Cuesta del Viento, Rodeo | lago turquesa desde un mirador, Andes nevados |
| catedral | Catedral y campanario (1979) | Meshy (`campanario_catedral`) o a medida |
| bicentenario | Teatro del Bicentenario | arco de 63 m de luz y 6 m de alto, en travertino |

## Cómo está hecho

- **Medidas y colores:** son los reales, con la fuente anotada en `pipeline/lista_modelos.json`. Donde el dato no está confirmado dice **[a confirmar]**.
- **Imágenes:** Google Maps y las fotos se usaron sólo para estudiar formas y colores. No se copian (derechos y términos de uso).
- **Posición del guía y los acompañantes:** es relativa a la cámara (a 11 m, en el tercio izquierdo) y miran hacia el hito, así siempre entran en cuadro.
- **Montañas:**
  - ruido de crestas y pie de monte tendido;
  - nieve sólo en lo plano y en altura;
  - perspectiva aérea: se azulan con la distancia aunque la niebla volumétrica esté apagada.
- **Hitos:** si todavía no hay modelo de Meshy, el hito se arma en Blender con sus medidas. Así la postal sale igual.
- **Afuera a propósito:** la Difunta Correa, porque es un santuario religioso.
