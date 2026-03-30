# Plan de Revisión Maestro: Auditoría 360° SAF v3.0
**Estado:** Requerido por Primary User
**Objetivo:** Garantizar que la realidad del disco coincida con la promesa del asistente.

## 1. Auditoría de Integridad de Archivos (MANDATORIA)
- **Check 1.1:** Verificar que `memory/domains/` no tenga archivos vacíos o con datos obsoletos de CompanyX (post-renuncia).
- **Check 1.2:** Validar el esquema de `memory/daily-actions.json` contra el log real de mensajes enviados hoy.
- **Check 1.3:** Inspección de `REGRESSIONS.md`: asegurar que los fallos de esta semana estén documentados y con protocolos de prevención activos.

## 2. Validación de Conciencia Temporal (Anti-Hallucination)
- **Prueba 2.1:** Inyectar una instrucción de simulación de tiempo futuro y verificar que el "Temporal Gate v3.1" bloquee la respuesta antes de la salida.
- **Prueba 2.2:** Validar que los briefings en Val Thorens usen CEST (UTC+2) consistentemente.

## 3. Benchmarking de Latencia (Intent Router)
- **Prueba 3.1:** Medir tiempo de respuesta con inyección de memoria total vs. inyección selectiva por `router.py`.
- **Objetivo:** < 1.2s para consultas directas de dominio.

## 4. Auditoría de Liderazgo (Lead Agent Protocol)
- **Verificación 4.1:** Revisar el registro de sub-agentes desplegados.
- **Verificación 4.2:** Validar el "Handshake" entre Jarvis y los modelos sparring (Opus/Sonnet) en los logs de sistema.

---
**Firmado:** Jarvis (Core Engine) bajo supervisión de Opus "Think Ultra Hard".
