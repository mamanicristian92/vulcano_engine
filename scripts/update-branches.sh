#!/usr/bin/env bash

set -u

REMOTE="origin"
MAIN_BRANCH="main"

updated=()
current=()
dirty=()
without_upstream=()
without_remote=()
diverged=()
errors=()

# Verificar que estamos dentro de un repositorio Git.
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: no estás dentro de un repositorio Git."
    exit 1
fi

# Guardar la rama inicial.
INITIAL_BRANCH=$(git branch --show-current)

if [[ -z "$INITIAL_BRANCH" ]]; then
    echo "Error: no se puede ejecutar desde un estado detached HEAD."
    exit 1
fi

# No iniciar si hay operaciones Git incompletas.
GIT_DIR=$(git rev-parse --git-dir)

if [[ -f "$GIT_DIR/MERGE_HEAD" ||
      -d "$GIT_DIR/rebase-merge" ||
      -d "$GIT_DIR/rebase-apply" ||
      -f "$GIT_DIR/CHERRY_PICK_HEAD" ||
      -f "$GIT_DIR/REVERT_HEAD" ]]; then
    echo "Error: hay una operación Git en curso."
    exit 1
fi

# Verificar que el directorio de trabajo esté limpio.
if [[ -n "$(git status --porcelain)" ]]; then
    echo
    echo "========================================"
    echo "        ACTUALIZACIÓN INTERRUMPIDA"
    echo "========================================"
    echo
    echo "Rama actual: $INITIAL_BRANCH"
    echo
    echo "Motivo:"
    echo "Se detectaron cambios locales sin commit."
    echo
    echo "¿Por qué no se pudo continuar?"
    echo "Git comparte el directorio de trabajo entre las ramas."
    echo "Cambiar de rama con modificaciones pendientes podría"
    echo "interferir con los archivos de otras ramas."
    echo
    echo "Solución recomendada:"
    echo "1. Revisa tus cambios con: git status"
    echo "2. Guarda tu trabajo mediante un commit o resguarda"
    echo "   manualmente los archivos modificados."
    echo "3. Vuelve a ejecutar el script."
    echo
    echo "No se modificaron ni descartaron tus cambios locales."
    echo "========================================"
    exit 1
fi

# Verificar el remoto.
if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
    echo "Error: no existe el remoto '$REMOTE'."
    exit 1
fi

# Actualizar las referencias remotas.
echo "Actualizando referencias de $REMOTE..."

if ! git fetch "$REMOTE"; then
    echo "Error: no se pudieron actualizar las referencias remotas."
    exit 1
fi

# Obtener las ramas locales, priorizando main.
branches=()

if git show-ref --verify --quiet "refs/heads/$MAIN_BRANCH"; then
    branches+=("$MAIN_BRANCH")
fi

while IFS= read -r branch; do
    [[ "$branch" == "$MAIN_BRANCH" ]] && continue
    branches+=("$branch")
done < <(git for-each-ref --format='%(refname:short)' refs/heads)

# Recorrer las ramas.
for branch in "${branches[@]}"; do
    echo
    echo "Procesando rama: $branch"

    # Cambiar de rama.
    if ! switch_output=$(git switch --quiet "$branch" 2>&1); then
        echo "No se pudo cambiar a $branch:"
        printf '%s\n' "$switch_output"
        errors+=("$branch: no se pudo cambiar de rama")
        continue
    fi

    # Omitir ramas con cambios locales.
    if [[ -n "$(git status --porcelain)" ]]; then
        echo "Omitida: tiene cambios locales sin commit."
        dirty+=("$branch")
        continue
    fi

    # Comprobar upstream.
    upstream=$(git for-each-ref \
        --format='%(upstream:short)' "refs/heads/$branch")

    if [[ -z "$upstream" ]]; then

        # Comprobar si existe una rama equivalente en origin.
        if git show-ref --verify --quiet \
            "refs/remotes/$REMOTE/$branch"; then

            if [[ -t 0 && -t 1 ]]; then
                while true; do
                    read -r -p \
                        "¿Configurar $REMOTE/$branch como upstream de $branch? [s/n]: " answer

                    case "$answer" in
                        [sS])
                            if git branch --set-upstream-to="$REMOTE/$branch" "$branch"; then
                                upstream="$REMOTE/$branch"
                            else
                                errors+=("$branch: no se pudo configurar upstream")
                                break
                            fi
                            break
                            ;;
                        [nN])
                            without_upstream+=("$branch")
                            break
                            ;;
                        *)
                            echo "Respuesta inválida. Escribe s o n."
                            ;;
                    esac
                done

            else
                echo "Omitida: no hay terminal interactiva para configurar upstream."
                without_upstream+=("$branch")
                continue
            fi

            [[ -z "$upstream" ]] && continue

        else
            echo "Omitida: no tiene upstream ni rama equivalente en $REMOTE."
            without_remote+=("$branch")
            continue
        fi
    fi

    # Actualizar exclusivamente mediante fast-forward.
    echo "Actualizando $branch..."

    local_before=$(git rev-parse HEAD)

    if git pull --ff-only; then
        if [[ -n "$(git status --porcelain)" ]]; then
            errors+=("$branch: el árbol de trabajo quedó con cambios")
        else
            # Comprobar si hubo una actualización real.
            if [[ "$(git rev-parse HEAD)" != "$local_before" ]]; then
                updated+=("$branch")
            else
                current+=("$branch")
            fi
        fi
    else
        # Diferenciar divergencia de otros errores.
        if git merge-base --is-ancestor "$upstream" HEAD ||
           git merge-base --is-ancestor HEAD "$upstream"; then
            errors+=("$branch: falló git pull --ff-only")
        else
            echo "Omitida: la rama tiene commits divergentes."
            diverged+=("$branch")
        fi
    fi

done

# Regresar a la rama inicial.
echo
echo "Regresando a la rama inicial: $INITIAL_BRANCH"

if ! git switch --quiet "$INITIAL_BRANCH"; then
    echo "ADVERTENCIA: no se pudo regresar a $INITIAL_BRANCH."
    echo "Rama actual: $(git branch --show-current)"
    errors+=("$INITIAL_BRANCH: no se pudo restaurar la rama inicial")
fi

# Mostrar resumen.
echo
echo "======================================"
echo "         RESUMEN DE ACTUALIZACIÓN"
echo "======================================"

show_results() {
    local title="$1"
    shift
    local -a items=("$@")

    echo
    echo "$title: ${#items[@]}"

    if ((${#items[@]} > 0)); then
        printf '  - %s\n' "${items[@]}"
    fi
}

show_results "Actualizadas" "${updated[@]}"
show_results "Sin cambios" "${current[@]}"
show_results "Omitidas por cambios locales" "${dirty[@]}"
show_results "Sin upstream" "${without_upstream[@]}"
show_results "Sin rama remota equivalente" "${without_remote[@]}"
show_results "Divergentes" "${diverged[@]}"
show_results "Errores" "${errors[@]}"

echo
echo "Proceso finalizado."
