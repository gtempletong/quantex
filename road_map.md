# Hoja de Ruta Maestra de Quantex (Versión Actualizada)

## Visión General
Este documento describe el plan de desarrollo para evolucionar Quantex bajo una estrategia de dos pilares paralelos:

* **Pilar A (Inteligencia Analítica):** Expandir y profundizar la capacidad de Quantex para generar inteligencia de mercado de élite.
* **Pilar B (Plataforma Cognitiva):** Evolucionar la tecnología subyacente para hacerla más potente, interactiva y autónoma.

---
## Pilar A: Inteligencia Analítica (Los "Productos")

#### Fase 0 a 4: La Fundación Robusta
* **Estado:** ✅ **COMPLETADO**
* **Resumen del Logro (Actualizado):** Se ha construido y depurado una arquitectura de IA de nivel profesional. El sistema opera sobre una base de separación clara de responsabilidades (`load_data` como recolector vs. `run` como sintetizador). Se ha consolidado el `Dossier` como un contenedor de evidencia estandarizado. Se han perfeccionado flujos críticos como el ciclo de "memoria" de la IA (`expert_context`), el mecanismo de "consumo único" para el `Briefing Estratégico` y el motor del Comité Técnico v2.0 con análisis multi-timeframe. La base es ahora excepcionalmente robusta para la expansión.

#### Fase 4.5: Refinamiento de la Calidad de Síntesis
* **Estado:** 🟡 **EN PROGRESO**
* **Objetivo:** Evolucionar la calidad de los informes de "muy buenos" a "excelentes" mediante la mejora de la lógica de razonamiento de los agentes Oráculo.

* **Paso 4.5.1: Enriquecer la Narrativa con "Color" de Noticias**
    * **Estado:** 🟡 **EN PROGRESO**
    * **Acción:** Aplicar el patrón del `Analista de Coyuntura` (usado actualmente para las noticias de SMM) a la inteligencia recolectada por el `Autonomous Researcher`. Esto estructurará los resúmenes de noticias en una tesis del día y puntos de evidencia clave, haciendo los informes más vívidos y creíbles.

* **Paso 4.5.2: Incorporar Análisis de Escenarios (El "Plan B")**
    * **Estado:** ⬜️ **PENDIENTE**
    * **Acción:** Modificar los prompts de los Oráculos para que, además de la tesis principal, generen un escenario alternativo clave, cuantificando el riesgo para el cliente.

#### Fase 5: Expansión a Nuevos Dominios y Capacidades
* **Estado:** ⬜️ **PENDIENTE**
* **Objetivo:** Aumentar el repertorio de análisis de Quantex.

* **Paso 5.1: El Trader Táctico (Sistema de Convicción Asimétrica)**
    * **Descripción:** Implementar el `Sistema de Convicción Asimétrica (SCA)`, un motor de decisiones de alto calibre basado en un riguroso proceso de veto secuencial de dos etapas: un Filtro de Probabilidad Cuantitativa y un Filtro de Contexto Estratégico.

* **Paso 5.2: Expansión del Comité Técnico al IPSA**
    * **Descripción:** Aplicar el motor existente del Comité Técnico v2.0 para analizar el universo de acciones del IPSA. El desafío principal es la ingeniería de datos para la ingesta y el procesamiento a escala.

* **Paso 5.3: El Analista de Crédito (Renta Fija)**

* **Paso 5.4: El Investigador Corporativo (Research de Empresas)**

#### Fase 6: El Laboratorio de Simulación (Análisis Interactivo)
* **Estado:** 🟡 **PARCIALMENTE COMPLETADO (BACKEND)**
* **Objetivo:** Transformar el informe estático en una experiencia interactiva.

* **Paso 6.1: Implementar Trazabilidad ("¿Por qué?")**
    * **Estado:** 🟡 **PARCIALMENTE COMPLETADO**
    * **Logro Actual:** El flujo de backend `trace_evidence_for_conclusion` ya está implementado y es funcional. El sistema puede, a nivel lógico, rastrear y citar la evidencia para una conclusión.
    * **Acción Pendiente:** Desarrollar la interfaz de usuario que permita al cliente hacer clic en una conclusión del informe para activar este flujo.

* **Paso 6.2: Activar la Simulación Estratégica ("¿Qué pasaría si...?")**
    * **Estado:** ⬜️ **PENDIENTE**
    * **Acción:** Desarrollar un flujo que permita al usuario plantear escenarios hipotéticos y la IA re-evaluará sus conclusiones dinámicamente.

---
## Pilar B: Plataforma Cognitiva y Crecimiento (El "Motor")

#### Fase Ágora 1: Fundación del Pipeline
* **Estado:** ✅ **COMPLETADO**
* **Resumen del Logro:** Se ha establecido un flujo de datos funcional para la gestión y activación inicial de prospectos (CSV -> Supabase -> Airtable) y la distribución de informes (Airtable -> Brevo), incluyendo el seguimiento de interacciones vía webhooks.

#### Fase Ágora 2: El Motor de Crecimiento Inteligente
* **Estado:** ⬜️ **PENDIENTE**
* **Objetivo:** Evolucionar Quantex Agora de un simple gestor a un motor de crecimiento proactivo y autónomo.

* **Paso 2.1: Desarrollar Quantex Agora 2.0 (CRM Proactivo)**
    * **Descripción:** Crear un módulo 100% autónomo para el manejo de interacciones, con integraciones directas (ej. Gmail) para gestionar secuencias de comunicación y nutrir prospectos de forma inteligente.

* **Paso 2.2: Activar el Publicador Autónomo (Integración con Redes Sociales)**

#### Fase Ágora 3: La Plataforma como Producto
* **Estado:** ⬜️ **PENDIENTE**
* **Objetivo:** Abstraer las tecnologías centrales de Quantex para posicionar la plataforma misma como un producto.

* **Paso 3.1: Abstraer el Núcleo de Quantex**

* **Paso 3.2: Desarrollar una API de Servicios Cognitivos**