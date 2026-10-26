# IteraStruct — ETABS MCP Server & ML Structural Assistant

**IteraStruct** es una prueba de concepto y metodología de investigación aplicada que integra **ETABS**, la **API de Python** y **modelos sustitutos de Machine Learning (Surrogate Models)** para acelerar el proceso de diseño estructural preliminar[cite: 1].

## 🎯 Objetivo del Proyecto

En el diseño estructural tradicional, la evaluación de configuraciones es altamente iterativa[cite: 1]. **IteraStruct** no busca reemplazar el criterio del ingeniero ni el análisis numérico de ETABS, sino predecir indicadores globales de respuesta (derivas, respuestas torsionales, periodos y cortante basal) para priorizar y recomendar qué alternativas de diseño valen la pena analizar completamente[cite: 1, 3].

---

## 🏗️ Arquitectura del Sistema

El flujo metodológico de IteraStruct se compone de las siguientes capas[cite: 2, 4]:

1. **ETABS + API de Python:** Extracción automatizada de geometría, propiedades y respuestas de modelos base reales[cite: 2].
2. **Dataset & Feature Engineering:** Transformación de la distribución resistente en variables con significado físico (densidad de muros, simetría, excentricidad, rigidez relativa X/Y)[cite: 3].
3. **Modelo Predictivo (Surrogate ML):** Entrenamiento de algoritmos (Gradient Boosting / Random Forest) para estimar derivas y respuestas antes de ejecutar el análisis completo[cite: 3].
4. **Reglas Técnicas y Agente MCP:** Sistema de orquestación que aplica restricciones normativas, genera un *ranking* de candidatos y solicita la verificación final en ETABS[cite: 4].

---

## ⚙️ Principios Clave

* **Criterio de Priorización:** Evalúa configuraciones preliminares para reducir iteraciones de diseño sin perder precisión en la selección final[cite: 1, 5].
* **Validación Anti-fuga (Anti-leakage):** Separación rigurosa por familias de layouts estructurales para garantizar la generalización del modelo[cite: 4].
* **El Ingeniero Conserva la Decisión:** El modelo ML estima y filtra; ETABS verifica y el profesional decide[cite: 1, 4].

---

> *Este proyecto fue desarrollado en el marco de la 2.ª generación de AECODE AI Talent (Línea de Investigación Aplicada).*[cite: 1]
