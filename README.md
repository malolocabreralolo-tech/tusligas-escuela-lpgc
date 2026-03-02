# TusLigas Escuela LPGC

Calendario y resultados de la liga escolar de fútbol de Las Palmas de Gran Canaria.

🌐 **[Ver calendario en vivo](https://malolocabreralolo-tech.github.io/tusligas-escuela-lpgc)**

## Cómo funciona

El `index.html` es un fichero estático generado automáticamente por el script Python. No requiere servidor ni base de datos.

## Estructura

```
index.html          # Calendario generado (publicado en GitHub Pages)
scripts/
  generate.py       # Script Python que genera el index.html
.github/workflows/
  update.yml        # Actualización automática vía GitHub Actions
```

## Regenerar el calendario manualmente

```bash
cd scripts
python generate.py
```

Esto sobreescribe `index.html` con los datos más recientes.

## Despliegue

El calendario se publica automáticamente en GitHub Pages. El workflow de GitHub Actions ejecuta el script y actualiza el sitio periódicamente.
