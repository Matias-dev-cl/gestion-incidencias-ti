# Alcance y flujo de uso

Este documento responde dos preguntas: **qué puede hacer cada rol** y **cómo recorre el sistema una incidencia**, desde que alguien la reporta hasta que se cierra.

## Quién hace qué

```mermaid
flowchart LR
    U(("👤<br/>Usuario"))
    T(("🔧<br/>Técnico"))
    A(("🛠️<br/>Admin"))

    subgraph Reportar
        C1[Crear ticket]
        C2[Comentar]
        C3[Ver sus tickets]
        C4[Reabrir su ticket]
        C5[Ver sus equipos<br/>y los compartidos]
    end

    subgraph Atender
        G1[Ver todos los tickets]
        G2[Tomar un ticket]
        G3[Cambiar estado y prioridad]
        G4[Escribir notas internas]
        G5[Ver todo el inventario]
    end

    subgraph Administrar
        D1[Reasignar a otro técnico]
        D2[Crear y editar equipos]
        D3[Panel de Django Admin]
    end

    U --> Reportar
    T --> Reportar
    T --> Atender
    A --> Reportar
    A --> Atender
    A --> Administrar
```

Los permisos son acumulativos hacia arriba: el técnico puede todo lo del usuario más lo suyo, y el admin puede todo. La única excepción es que un técnico **no** reasigna tickets a terceros — se los toma.

## El recorrido de una incidencia

```mermaid
sequenceDiagram
    actor U as Usuario
    participant S as Sistema
    actor T as Técnico

    U->>S: Reporta la incidencia<br/>(título, categoría, prioridad, equipo)
    Note over S: Estado ABIERTO<br/>Se escribe la traza inicial<br/>El equipo pasa a EN REPARACIÓN
    S-->>U: Ticket #13 creado

    T->>S: Ve la cola completa y toma el ticket
    Note over S: Estado EN PROGRESO<br/>Queda como técnico asignado
    T->>S: Comenta el avance
    T->>S: Escribe una nota interna
    Note over S: La nota no le llega al solicitante

    T->>S: Marca RESUELTO
    Note over S: Se sella la fecha de cierre<br/>El equipo vuelve a OPERATIVO

    alt La solución funcionó
        U->>S: No hace nada
        T->>S: Marca CERRADO
    else El problema reapareció
        U->>S: Reabre indicando qué sigue fallando
        Note over S: Vuelve a EN PROGRESO<br/>con el mismo técnico<br/>Se limpia la fecha de cierre
    end
```

Todo lo marcado como *Note over Sistema* ocurre en `apps/tickets/signals.py`, no en las vistas: pasa igual si el cambio viene de la interfaz, del panel de administración o de un comando.

## Qué ve cada rol al entrar

| Pantalla | Usuario | Técnico / Admin |
|---|---|---|
| Dashboard | Sus propias cifras | Cifras globales, tickets sin asignar y equipos en reparación |
| Tickets | Solo los que él reportó | La cola completa, con filtro "solo míos" |
| Inventario | "Mis equipos": los suyos y los compartidos | "Inventario de equipos": los 7 del ejemplo, con el conteo de incidencias abiertas |
| Detalle de ticket | Histórico sin notas internas | Histórico completo y panel de gestión |

## Los cinco estados

```mermaid
stateDiagram-v2
    [*] --> ABIERTO
    ABIERTO --> EN_PROGRESO
    EN_PROGRESO --> EN_ESPERA
    EN_ESPERA --> EN_PROGRESO
    EN_PROGRESO --> RESUELTO
    RESUELTO --> CERRADO
    RESUELTO --> EN_PROGRESO : reabierto
    CERRADO --> EN_PROGRESO : reabierto
    CERRADO --> [*]
```

`EN_ESPERA` existe para el caso concreto de la mesa de ayuda: el técnico ya diagnosticó pero depende de un repuesto o de un proveedor. Sin ese estado, esos tickets se ven idénticos a los que nadie ha tocado, y la cola deja de decir la verdad.
