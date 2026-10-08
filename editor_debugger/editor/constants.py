"""Constantes, reglas jerárquicas y metadatos de tipos de LoreBlocks para el Editor."""

from typing import Dict, List, Optional

from domains.lore import LoreBlock, ConditionGroup, LoreEffects

ALLOWED_CHILD_TYPES: Dict[Optional[str], List[str]] = {
    None: ["Chapter", "popup"],
    "": ["Chapter", "popup"],
    "Chapter": ["Quest", "Info", "popup"],
    "Quest": ["Task", "Info", "popup"],
    "Task": ["Event", "ask_permission", "Info", "popup"],
    "Event": ["Event", "ask_permission", "Info", "popup"],
    "Info": ["popup"],
    "ask_permission": ["popup"],
    "popup": [],
}

TYPE_METADATA: Dict[str, Dict[str, str]] = {
    "Chapter": {"icon": "📖", "label": "Capítulo (Chapter)", "color": "#2b6cb0"},
    "Quest": {"icon": "⚔️", "label": "Misión (Quest)", "color": "#b7791f"},
    "Task": {"icon": "📌", "label": "Tarea (Task)", "color": "#2c7a7b"},
    "Event": {"icon": "⚡", "label": "Evento (Event)", "color": "#5c6bc0"},
    "popup": {"icon": "📢", "label": "Aviso Modal (popup)", "color": "#d97706"},
    "Info": {"icon": "💬", "label": "Pista de NPCs (Info)", "color": "#0284c7"},
    "ask_permission": {"icon": "❓", "label": "Pregunta / Permiso (ask_permission)", "color": "#7c3aed"},
}


def get_allowed_child_types(parent_type: Optional[str]) -> List[str]:
    """Retorna los tipos permitidos para un nuevo bloque según el tipo de su padre."""
    if not parent_type:
        return ALLOWED_CHILD_TYPES[None]
    return ALLOWED_CHILD_TYPES.get(parent_type, ["popup"])


def init_preset_loreblock(type_name: str, id_val: str, title: str, parent_id: Optional[str] = None) -> LoreBlock:
    """Instancia e inicializa un LoreBlock básico con los valores por defecto de su tipo/preset."""
    lb = LoreBlock(
        id=id_val,
        name=title,
        title=title,
        type=type_name,
        parent_id=parent_id,
        state="unknown",
    )

    if type_name == "popup":
        lb.active_conditions = [ConditionGroup(conditions=[], rag_enabled=False, trigger_phrases=[])]
        lb.description = "Mensaje del aviso emergente..."
        lb.active_effects = []
        lb.done_conditions = []
        lb.done_effects = []

    elif type_name == "Info":
        lb.active_conditions = []
        lb.active_effects = [
            LoreEffects(action="hook", directive="Indicación o contexto que los NPCs darán al jugador...")
        ]
        lb.done_conditions = []
        lb.done_effects = []

    elif type_name == "ask_permission":
        lb.active_conditions = [ConditionGroup(conditions=[], rag_enabled=False, trigger_phrases=[])]
        lb.active_effects = [
            LoreEffects(action="hook", directive="Describe la entidad y pregunta al jugador si desea interactuar...")
        ]
        lb.done_conditions = [
            ConditionGroup(
                conditions=[],
                rag_enabled=True,
                trigger_phrases=["sí", "interactuar", "confirmar"],
            )
        ]
        lb.done_effects = [
            LoreEffects(action="hook", directive="Narra las consecuencias de la respuesta afirmativa...")
        ]

    else:
        lb.active_conditions = [ConditionGroup(conditions=[], rag_enabled=False, trigger_phrases=[])]
        lb.active_effects = []
        lb.done_conditions = [ConditionGroup(conditions=[], rag_enabled=False, trigger_phrases=[])]
        lb.done_effects = []

    return lb
