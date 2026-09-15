# Guía: subir el proyecto a GitHub y montar el tablero

Pensada para ejecutarse una sola vez. El repositorio del grupo ya existe y está
definido en el Avance 01: `https://github.com/WillRider2003/RedesDefProyecto`.

## Paso 1. Instalar lo necesario

Necesitas Git y el GitHub CLI. En Windows, desde PowerShell:

```powershell
winget install --id Git.Git -e
winget install --id GitHub.cli -e
```

Cierra y vuelve a abrir la terminal, y luego autentícate:

```bash
gh auth login
```

Elige GitHub.com, HTTPS y autenticación por navegador.

## Paso 2. Conectar tu carpeta local con el repo del grupo

Desde la carpeta `SDN_Proyecto`:

```bash
git init
git branch -M main
git remote add origin https://github.com/WillRider2003/RedesDefProyecto.git
git fetch origin
```

Si el repo remoto ya tiene contenido, intégralo antes de subir lo tuyo:

```bash
git pull origin main --allow-unrelated-histories
```

Si hay conflictos, resuélvelos con calma antes de continuar. Si el repo remoto
está vacío, este paso no hace nada y puedes seguir de frente.

## Paso 3. Primer commit

```bash
git add .
git commit -m "chore(repo): estructura de documentacion, contratos y plantillas del Ex1"
git push -u origin main
```

## Paso 4. Rama de integración

```bash
git checkout -b develop
git push -u origin develop
```

De aquí en adelante nadie trabaja directamente sobre `main` ni sobre `develop`.
Cada tarea sale de `develop`:

```bash
git checkout develop
git pull
git checkout -b feature/hld-r3-deteccion
# ... trabajas, commiteas ...
git push -u origin feature/hld-r3-deteccion
gh pr create --base develop --title "docs(r3): diseno logico de deteccion" --fill
```

## Paso 5. Proteger `main`

Esto lo tiene que hacer Willian, que es el dueño del repo. En la web:
Settings, Branches, Add branch protection rule, patrón `main`, y marcar
"Require a pull request before merging" con al menos una aprobación.

Sirve para dos cosas: evita que alguien rompa la rama buena por accidente, y
genera el historial de revisiones que la rúbrica del Ex1 califica con peso 20
bajo el criterio de "evidencia de trabajo coordinado".

## Paso 6. Crear el tablero desde la rúbrica

```bash
bash scripts/crear-issues-ex1.sh WillRider2003/RedesDefProyecto
```

Esto crea las etiquetas, el milestone `Ex1-Parcial` con fecha límite, y unos
cuarenta issues, uno por cada criterio de la rúbrica con su peso en el título.

Después, en la web del repo: Projects, New project, plantilla Board, y en el
tablero usa "Add item" para traer todos los issues del milestone. Columnas
sugeridas: Por hacer, En curso, En revisión, Hecho.

Asignación sugerida según los roles del Avance 01:

| Etiqueta | Responsable natural |
|---|---|
| `arquitectura` | Eduardo, arquitecto de solución |
| `docs` de R1, R2, R3 | Eduardo con apoyo de Jairo |
| `codigo` | Jeanpier, codificador |
| `pruebas` | Eva María, testeador y QA |
| `bloqueante` y coordinación | Willian, líder |

## Paso 7. Generar los PDF de entrega

Los documentos se escriben en Markdown y se exportan recién al entregar:

```bash
bash scripts/md-a-pdf.sh docs/02-arquitectura.md entregables/ex1/Arquitectura-G5.pdf
```

Para el avance semanal, respeta el nombre exacto que pide el enunciado:

```bash
bash scripts/md-a-pdf.sh entregables/avances/AVZ05.md \
     entregables/avances/AVZ05-TEL354_2026-2_G5.pdf
```

## Qué no subir nunca

El perfil de conexión al VNRT, certificados, llaves y cualquier archivo con
credenciales. El `.gitignore` ya los bloquea y el CI falla si alguno se cuela.
El repositorio debería ser privado, con los cinco integrantes como colaboradores
y el coach invitado con permiso de lectura.

## Flujo semanal sugerido

Lunes se revisa el tablero y se reparten los issues de la semana. Durante la
semana cada uno trabaja en su rama y abre PR. El sábado se cierra el avance
`AVZ[N].md` a partir de lo que se mergeó esa semana, se exporta a PDF y Willian
lo sube a Paideia. El domingo a las 5 PM se muestra al coach lo que está en
`develop`, no diapositivas sueltas.
