# Actualización de ramas locales

## Descripción

Este directorio contiene una utilidad opcional para facilitar la actualización de las ramas locales del repositorio mediante Git.

El script `update-branches.sh` permite recorrer las ramas locales e integrar los cambios disponibles en sus respectivas ramas remotas, siempre que exista una configuración de seguimiento (*upstream*) válida.

Esta herramienta es independiente del funcionamiento principal de Vulcano Engine. Su utilización es completamente opcional.

## Requisitos

- Git instalado.
- Bash o Git Bash.
- Un repositorio Git con acceso al remoto `origin`.

## Uso

Se recomienda ejecutar el script desde la rama `main` y desde el directorio raíz del repositorio.

En Git Bash o Linux:

```bash
bash scripts/update-branches.sh
```

## Funcionamiento

El script realiza las siguientes operaciones:

1. Identifica la rama local activa para regresar a ella al finalizar.
2. Recorre todas las ramas locales, independientemente de su nomenclatura.
3. Comprueba si cada rama tiene configurado un upstream.
4. Si una rama no tiene upstream, comprueba si existe una rama remota equivalente en `origin` y consulta al usuario si desea configurar el seguimiento.
5. Omite las ramas que tengan cambios locales pendientes, sin modificar esos cambios.
6. Actualiza las ramas que tienen upstream mediante `git pull --ff-only`.
7. Si una rama presenta divergencias o algún error durante la actualización, registra la situación y continúa con las demás.
8. Al finalizar, intenta regresar a la rama desde la que se inició la ejecución.
9. Presenta un resumen de los resultados.

## Seguridad y restricciones

Esta utilidad está diseñada exclusivamente para actualizar ramas locales.

**El script no debe realizar ninguna de las siguientes operaciones:**

- `git add`
- `git commit`
- `git push`
- `git reset --hard`
- `git stash`
- `git clean`

Tampoco debe descartar, sobrescribir ni eliminar cambios locales del usuario.

Las ramas remotas no deben modificarse. La configuración de upstream, cuando el usuario la autorice, afecta únicamente a la configuración local de Git.

## Consideraciones

- Las ramas con modificaciones locales pendientes se omiten para proteger el trabajo en curso.
- Las ramas que estén adelantadas respecto de su upstream no deben considerarse sucias por ese motivo.
- Las divergencias no se resuelven automáticamente.
- La herramienta no es necesaria para ejecutar ni desarrollar Vulcano Engine.

## Carácter opcional

Este script es una herramienta auxiliar destinada a facilitar el mantenimiento de las ramas locales de los colaboradores.

Su presencia en el repositorio no implica que deba ejecutarse durante la instalación, configuración o ejecución de la aplicación.
