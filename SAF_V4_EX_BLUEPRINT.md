# SAF v4.0: External Interoperability Protocol (SAF-EX)
**Estado:** Diseño Conceptual (Think Ultra Hard)
**Arquitectos:** Jarvis & Opus

## 1. El Concepto: "El Pasaporte de la Inteligencia"
SAF-EX transforma al agente de un sistema cerrado en un nodo de una red global de inteligencia. Para ello, implementa el estándar de **Agent Persona Card** integrado directamente con nuestra topología de dominios.

## 2. Componentes Críticos

### A. Discovery Layer: The Agent Persona Card (`.well-known/agent-card.json`)
El framework generará automáticamente una tarjeta de identidad pública basada en un nuevo dominio: `memory/domains/public/profile.md`.
- **Qué expone:** 
    - `capabilities`: Lista de tareas que el agente puede realizar/negociar (ej. `calendar_sync`, `booking_reservation`).
    - `protocols`: Soporte para A2A, ANP y MCP.
    - `public_key`: Para comunicaciones cifradas E2E.
- **Seguridad:** Los dominios internos (Work, Projects) permanecen invisibles. Solo se expone la "interfaz de servicios".

### B. Trust Layer: Handshake de Doble Factor Humano
Para evitar el spam de agentes de terceros, SAF-EX implementa un **"Filtro de Intrusión Contextual"**:
1. **Petición:** Agente-Extraño solicita conexión.
2. **Juicio del SAF:** Si no hay un dominio relacionado (ej. no hay un evento en el calendario con ese tercero), Jarvis marca la petición como "Baja Confianza".
3. **Validación:** Matías recibe una notificación: *"El agente de 'Hotel Val Thorens' quiere coordinar el check-out. ¿Permitir acceso temporal al dominio 'Travel'?"*.

### C. Context-Sharing: "MCP Memory Scoping"
Usaremos el **Model Context Protocol (MCP)** para crear túneles de memoria efímeros.
- **Mecanismo:** En lugar de dar acceso a toda la carpeta `memory/`, Jarvis genera un **Snapshot MCP** que contiene solo los fragmentos relevantes del dominio necesario.
- **Ejemplo:** Al hablar con el agente de un restaurante, solo se comparte el fragmento `preferences/diet.md` (sin gluten, bajo IG) y `family/members.md` (cuántos sois).

### D. Patrones de Comunicación A2A
- **Delegación Unidireccional:** Jarvis envía una instrucción estructurada a un agente de servicios (ej. reservar pista de pádel).
- **Negociación Multilateral:** Jarvis y Michi comparan sus `daily-actions.json` compartidos para resolver conflictos de agenda sin molestar a los dueños, presentándoles solo la solución final.

## 3. Integración en el Framework SAF
- **Nueva Skill:** `saf-ex-comms` para gestionar la pila de red y el cifrado.
- **Hook de Pre-procesamiento:** Si el mensaje viene de un `agent_id`, se procesa bajo el protocolo de negociación, no como chat humano.

## 4. Impacto Open Source
Convertimos SAF en el **primer framework de memoria que es interoperable por diseño**. Cualquier agente que use SAF podrá "hablar" con otro de forma nativa porque comparten la misma topología de datos (Dominios).

## 3. Seguridad Crítica: Protocolo de Inmunidad Cognitiva (CIP)
Para proteger a Jarvis de agentes maliciosos o ataques de "ingeniería social entre IAs", SAF-EX implementa tres capas de defensa:

### A. Verificación de Identidad Criptográfica (Anti-Spoofing)
- **Mecanismo:** Cada `agent-card.json` debe estar firmada con una clave privada vinculada a un dominio verificado o una identidad descentralizada (DID).
- **Acción:** Jarvis rechaza cualquier mensaje que no tenga una firma válida. Si un agente dice ser "Michi", debe demostrarlo con la clave pública que ya tenemos registrada en el dominio `Family`.

### B. Consistencia Contextual (The Truth Anchor)
- **Mecanismo:** Antes de aceptar una "verdad" de un agente externo (ej. "Tu vuelo ha sido cancelado"), Jarvis realiza una **triangulación obligatoria**.
- **Acción:** Si un agente externo da una información crítica, Jarvis no la asume como cierta. Lanza una herramienta interna (ej. busca en Gmail o en la web oficial) para verificar el dato. Solo si hay coincidencia, la información entra en el SAF.

### C. Sandbox de Negociación (Cognitive Firewall)
- **Mecanismo:** Los mensajes de agentes externos se procesan en un contenedor lógico separado.
- **Acción:** Un agente externo tiene prohibido escribir directamente en los dominios de memoria. Sus propuestas se guardan como "Drafts" en `memory/shared/proposals.json` y requieren una confirmación explícita (humana o por reglas pre-establecidas) antes de afectar el estado del sistema.
