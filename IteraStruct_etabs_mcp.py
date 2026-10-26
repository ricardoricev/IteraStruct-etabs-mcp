import sys
import comtypes.client
from mcp.server.fastmcp import FastMCP

# Instancia del servidor MCP
mcp = FastMCP("IteraStruct ETABS Engine")


def connect_etabs():
    """Conecta a la instancia activa de ETABS via OAPI."""
    try:
        helper = comtypes.client.CreateObject("ETABSv1.Helper")
        helper = helper.QueryInterface(comtypes.gen.ETABSv1.cHelper)
        object_etabs = helper.GetObject("CSI.ETABS.API.ETABSObject")

        if object_etabs is None:
            sys.stderr.write(
                "❌ Error: No se encontró ninguna instancia activa de ETABS abierta.\n"
            )
            return (
                None,
                "Error: No se encontró una instancia activa de ETABS. Por favor, abre ETABS antes de continuar.",
            )

        sapmodel = object_etabs.SapModel
        return sapmodel, None

    except Exception as e:
        error_msg = f"Error al intentar conectar con ETABS: {str(e)}"
        sys.stderr.write(f"❌ {error_msg}\n")
        return None, error_msg


@mcp.tool()
def get_model_info() -> str:
    """Obtiene información básica del archivo activo en ETABS (nombre de archivo y pisos)."""
    sapmodel, err = connect_etabs()
    if err:
        return err

    try:
        filename = sapmodel.GetModelFilename()
        if not filename:
            return "⚠️ Hay una instancia de ETABS abierta, pero no hay ningún modelo cargado."

        num_stories = sapmodel.Story.GetNameList()[0]
        story_names = list(sapmodel.Story.GetNameList()[1])

        return (
            f"📌 **Archivo activo:** `{filename}`\n"
            f"🏢 **Total de niveles:** {num_stories}\n"
            f"📋 **Niveles:** {', '.join(story_names)}"
        )
    except Exception as e:
        return f"Error al leer datos del modelo: {str(e)}"


@mcp.tool()
def get_available_cases_and_combos() -> str:
    """Lista todos los casos de carga y combinaciones disponibles en el modelo activo."""
    sapmodel, err = connect_etabs()
    if err:
        return err

    try:
        cases_count, cases_list, _ = sapmodel.LoadCases.GetNameList()
        combos_count, combos_list, _ = sapmodel.RespCombo.GetNameList()

        cases_str = ", ".join(cases_list) if cases_count > 0 else "Ninguno"
        combos_str = ", ".join(combos_list) if combos_count > 0 else "Ninguna"

        return (
            f"📂 **Casos de Carga Disponibles ({cases_count}):**\n`{cases_str}`\n\n"
            f"🔀 **Combinaciones Disponibles ({combos_count}):**\n`{combos_str}`"
        )
    except Exception as e:
        return f"Error al listar casos y combinaciones: {str(e)}"


@mcp.tool()
def run_analysis() -> str:
    """Ejecuta el análisis estructural en ETABS si el modelo no está bloqueado/analizado."""
    sapmodel, err = connect_etabs()
    if err:
        return err

    try:
        if sapmodel.GetModelIsLocked():
            return "ℹ️ El modelo ya se encuentra analizado y bloqueado (Locked)."

        sys.stderr.write("⏳ Ejecutando análisis en ETABS...\n")
        ret = sapmodel.Analyze.RunAnalysis()

        if ret == 0:
            return "✅ **Análisis completado exitosamente.** El modelo está listo para extracción de resultados."
        else:
            return f"❌ El análisis falló con código de error: {ret}"
    except Exception as e:
        return f"Error al ejecutar el análisis: {str(e)}"


@mcp.tool()
def check_e030_concrete_drifts(
    cases_x: list[str],
    cases_y: list[str],
    r_x: float = 8.0,
    r_y: float = 8.0,
    is_regular_x: bool = True,
    is_regular_y: bool = True,
    already_amplified: bool = False,
) -> str:
    """Verifica las derivas (distorsiones de entrepiso) sísmicas en X e Y según la Norma Peruana E.030 para Concreto Armado (Límite = 0.007).

    Parámetros:
    - cases_x: Casos o combinaciones sísmicas en X (ej. ["SISMO_X"] o ["SPEC_X"]).
    - cases_y: Casos o combinaciones sísmicas en Y (ej. ["SISMO_Y"] o ["SPEC_Y"]).
    - r_x: Factor de reducción de fuerza sísmica R en X (por defecto 8.0).
    - r_y: Factor de reducción de fuerza sísmica R en Y (por defecto 8.0).
    - is_regular_x: True si la estructura es regular en X (multiplica por 0.75*R), False si es irregular (0.85*R).
    - is_regular_y: True si la estructura es regular en Y (multiplica por 0.75*R), False si es irregular (0.85*R).
    - already_amplified: Indicar True si la combinación en ETABS ya incluye la amplificación inelástica (0.75R / 0.85R).
    """
    sapmodel, err = connect_etabs()
    if err:
        return err

    # Comprobar si está analizado; si no, correr análisis automáticamente
    if not sapmodel.GetModelIsLocked():
        run_res = run_analysis()
        if "❌" in run_res:
            return f"No se pueden consultar las derivas porque el modelo no pudo ser analizado.\n{run_res}"

    LIMIT_E030_CONCRETE = 0.007  # Límite E.030 para Concreto Armado

    # Cálculo del factor de amplificación inelástica según E.030 (Art. 31/32)
    factor_x = (
        1.0
        if already_amplified
        else (0.75 * r_x if is_regular_x else 0.85 * r_x)
    )
    factor_y = (
        1.0
        if already_amplified
        else (0.75 * r_y if is_regular_y else 0.85 * r_y)
    )

    all_cases = list(set(cases_x + cases_y))

    try:
        # Seleccionar casos/combos requeridos para reporte
        sapmodel.Results.Setup.DeselectAllCasesAndCombosForOutput()
        for name in all_cases:
            ret_c = sapmodel.Results.Setup.SetCaseSelectedForOutput(name)
            if ret_c != 0:
                sapmodel.Results.Setup.SetComboSelectedForOutput(name)

        # Extraer tabla de Story Drifts
        res = sapmodel.Results.StoryDrifts()
        if not res or res[0] == 0:
            return f"⚠️ No se encontraron resultados de derivas para los casos/combinaciones especificados: `{all_cases}`."

        num_results = res[0]
        stories = res[1]
        load_cases = res[2]
        directions = res[5]
        drifts = res[6]

        summary_rows = []
        max_drift_x = 0.0
        max_drift_y = 0.0
        max_story_x = ""
        max_story_y = ""
        has_failure = False

        for i in range(num_results):
            story = stories[i]
            lc = load_cases[i]
            direction = directions[i]
            drift_elastic = drifts[i]

            # Asignación de dirección y factor de multiplicación
            if lc in cases_x or "X" in direction.upper():
                f_mult = factor_x
                dir_label = "X"
            elif lc in cases_y or "Y" in direction.upper():
                f_mult = factor_y
                dir_label = "Y"
            else:
                f_mult = factor_x
                dir_label = direction

            drift_inelastic = drift_elastic * f_mult
            status = (
                "✅ CUMPLE"
                if drift_inelastic <= LIMIT_E030_CONCRETE
                else "❌ NO CUMPLE"
            )

            if drift_inelastic > LIMIT_E030_CONCRETE:
                has_failure = True

            if dir_label == "X" and drift_inelastic > max_drift_x:
                max_drift_x = drift_inelastic
                max_story_x = story

            if dir_label == "Y" and drift_inelastic > max_drift_y:
                max_drift_y = drift_inelastic
                max_story_y = story

            summary_rows.append(
                f"| {story} | {lc} | {dir_label} | {drift_elastic:.6f} | **{drift_inelastic:.5f}** | {LIMIT_E030_CONCRETE} | {status} |"
            )

        # Construcción del informe final
        header = (
            f"### 📊 Verificación de Derivas - Norma Peruana E.030 (Concreto Armado)\n\n"
            f"- **Límite máximo admisible:** `0.007` (7‰)\n"
            f"- **Factor de Amplificación X:** `{factor_x:.2f}` (R_x={r_x}, Regular={is_regular_x})\n"
            f"- **Factor de Amplificación Y:** `{factor_y:.2f}` (R_y={r_y}, Regular={is_regular_y})\n\n"
            f"| Entrepiso | Caso / Combo | Dir. | Deriva Elástica | Deriva Inelástica | Límite E.030 | Estado |\n"
            f"|---|---|:---:|:---:|:---:|:---:|:---:|\n"
        )

        table_body = "\n".join(summary_rows)

        conclusion = "\n\n### 📝 Resumen de Resultados:\n"
        conclusion += (
            f"- **Deriva Máxima Dir. X:** `{max_drift_x:.5f}` en nivel **{max_story_x}** "
            + (
                "(✅ Cumple)"
                if max_drift_x <= LIMIT_E030_CONCRETE
                else "(❌ Excede el límite)"
            )
            + "\n"
        )
        conclusion += (
            f"- **Deriva Máxima Dir. Y:** `{max_drift_y:.5f}` en nivel **{max_story_y}** "
            + (
                "(✅ Cumple)"
                if max_drift_y <= LIMIT_E030_CONCRETE
                else "(❌ Excede el límite)"
            )
            + "\n\n"
        )

        if not has_failure:
            conclusion += "🎉 **DIAGNÓSTICO FINAL:** La estructura **CUMPLE** en todos sus niveles con los límites de distorsión de entrepiso de la Norma E.030."
        else:
            conclusion += "⚠️ **DIAGNÓSTICO FINAL:** La estructura **NO CUMPLE** en uno o más niveles. Requiere mayor rigidez lateral (aumentar placas/columnas) en las direcciones deficientes."

        return header + table_body + conclusion

    except Exception as e:
        return f"Error procesando la tabla de derivas: {str(e)}"


if __name__ == "__main__":
    mcp.run()