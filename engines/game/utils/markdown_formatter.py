"""Formateador de datos y entidades del juego a representaciones Markdown."""

from typing import Any, Dict, List, Optional, Union
from domains.base import Entity
from domains.npcs import NPC
from domains.world import Place


class MarkdownFormatter:
    """Transforma datos y entidades del juego a Markdown para su inyección en prompts."""

    @staticmethod
    def format_conversation(
        history: List[Dict[str, str]],
        current_input: Optional[str] = None,
        default_speaker: str = "Player",
    ) -> str:
        """Formatea el historial de conversación añadiendo la consulta actual."""
        lines = []
        for item in history:
            for speaker, msg in item.items():
                speaker_display = "Dungeon Master" if speaker in ["DM", "Dungeon Master"] else speaker
                lines.append(f"* **{speaker_display}**: {msg}")

        if current_input:
            lines.append(f"* **{default_speaker}**: {current_input}")
        elif not lines:
            lines.append(f"* **{default_speaker}**: Interactúa en busca de información.")
        return "\n".join(lines)

    @staticmethod
    def format_npc(npc: Any, detailed: bool = False) -> str:
        """Formatea los datos de un personaje no jugador."""
        if not npc:
            return "* **NPC**: Desconocido"

        name = getattr(npc, "name", "Desconocido")
        occupation = getattr(npc, "occupation", "Desconocida") or "Desconocida"
        description = getattr(npc, "description", "")

        lines = []
        if detailed and hasattr(npc, "id"):
            lines.append("* **Tipo**: Personaje (NPC)")
            lines.append(f"* **Nombre**: {name} (ID: {npc.id})")
        else:
            lines.append(f"* **Nombre**: {name}")

        lines.append(f"* **Ocupación**: {occupation}")

        if detailed:
            lines.append(f"* **Estado actual**: {getattr(npc, 'state', 'none')}")
            lines.append(f"* **Afinidad actual**: {getattr(npc, 'affinity', 0.5)}")

        lines.append(f"* **Descripción**: {description}")

        motivations = getattr(npc, "motivations", None)
        if motivations:
            likes = ", ".join(motivations.likes) if motivations.likes else "(Ninguno)"
            dislikes = ", ".join(motivations.dislikes) if motivations.dislikes else "(Ninguno)"
            lines.append("* **Motivaciones**:")
            lines.append(f"  * Likes: {likes}")
            lines.append(f"  * Dislikes: {dislikes}")

        services = getattr(npc, "services", [])
        if detailed and services:
            lines.append("* **Servicios ofrecidos**:")
            for svc in services:
                cost_str = f"{svc.cost} monedas" if getattr(svc, "cost", None) is not None else "Gratuito"
                min_aff = getattr(svc, "min_affinity", 0.0)
                lines.append(f"  * {svc.type} ({cost_str}): {svc.description} [Afinidad mín: {min_aff}]")

        return "\n".join(lines)

    @staticmethod
    def format_place(
        place: Optional[Place],
        include_connections: bool = False,
        include_visible: bool = False,
    ) -> str:
        """Formatea la información de un lugar o entorno."""
        if not place:
            return "* **Lugar**: Desconocido"

        lines = []
        if include_connections and hasattr(place, "id"):
            lines.append("* **Tipo**: Lugar (Place)")
            lines.append(f"* **Nombre**: {place.name} (ID: {place.id})")
            lines.append(f"* **Descripción**: {place.description}")
        else:
            lines.append(f"* **Lugar**: {place.name}")
            lines.append(f"* **Descripción**: {place.description}")

        if include_visible:
            vis = ", ".join(place.visible_entities) if place.visible_entities else "(Ninguna entidad visible)"
            lines.append(f"* **Entidades / NPCs presentes**: {vis}")

        if include_connections:
            if place.connections:
                lines.append("* **Caminos y conexiones de salida**:")
                for direction, conn in place.connections.items():
                    lines.append(
                        f"  * Salida hacia '{direction}': lleva a '{conn.target}' "
                        f"({conn.distance} m, terreno: {conn.terrain_type})"
                    )
            else:
                lines.append("* **Caminos y conexiones de salida**: Ninguna salida conectada.")

        return "\n".join(lines)

    @staticmethod
    def format_path(intermediate_places: List[Place], estimated_time: int = 0) -> str:
        """Formatea los lugares intermedios y tiempo estimado de viaje."""
        lines = []
        if intermediate_places:
            names = [p.name for p in intermediate_places]
            lines.append(f"* **Lugares intermedios**: {', '.join(names)}")
            for p in intermediate_places:
                lines.append(f"  * **{p.name}**: {p.description}")
        else:
            lines.append("* **Lugares intermedios**: Transición directa (lugares colindantes)")

        if estimated_time > 0:
            lines.append(f"* **Tiempo estimado de viaje**: {estimated_time} minutos")
        return "\n".join(lines)

    @staticmethod
    def format_entity(entity: Optional[Union[Place, NPC, Entity]]) -> str:
        """Formatea polimórficamente cualquier entidad con sus atributos."""
        if not entity:
            return "* **Entidad**: No especificada o entorno general."

        if isinstance(entity, NPC):
            return MarkdownFormatter.format_npc(entity, detailed=True)

        if isinstance(entity, Place):
            return MarkdownFormatter.format_place(entity, include_connections=True, include_visible=True)

        lines = [
            "* **Tipo**: Objeto / Entidad",
            f"* **Nombre**: {entity.name} (ID: {entity.id})",
            f"* **Descripción**: {entity.description}",
        ]
        extra_data = {
            k: v
            for k, v in entity.model_dump().items()
            if k not in {"id", "name", "description", "dynamic_lore"} and v is not None
        }
        if extra_data:
            lines.append("* **Propiedades adicionales**:")
            for k, v in extra_data.items():
                lines.append(f"  * {k}: {v}")

        return "\n".join(lines)

    @classmethod
    def dialogue_tags(cls, ctx: Any) -> Dict[str, str]:
        """Genera tags runtime para la plantilla de diálogo."""
        directive_str = (
            f"- {ctx.directive}"
            if ctx.directive
            else "- Responde al jugador según tu personalidad y motivaciones."
        )
        return {
            "npc_info": cls.format_npc(ctx.npc, detailed=False),
            "npc_conversation": cls.format_conversation(ctx.conversation_history, ctx.player_input),
            "npc_agenda": directive_str,
            "player_input": ctx.player_input or "",
        }

    @classmethod
    def move_tags(cls, ctx: Any) -> Dict[str, str]:
        """Genera tags runtime para la plantilla de movimiento."""
        directive_str = (
            f"- {ctx.directive}"
            if ctx.directive
            else "- Describe la transición física y la atmósfera del lugar de destino."
        )
        return {
            "origin_info": cls.format_place(ctx.origin_place),
            "path_info": cls.format_path(ctx.path_taken, ctx.estimated_travel_time),
            "destination_info": cls.format_place(ctx.destination_place),
            "move_agenda": directive_str,
            "player_input": ctx.player_input or "",
        }

    @classmethod
    def explain_look_tags(cls, ctx: Any) -> Dict[str, str]:
        """Genera tags runtime para la plantilla de inspección."""
        directive_lines = []
        if ctx.directive:
            directive_lines.append(f"- {ctx.directive}")

        if getattr(ctx, "failed_reason", None):
            directive_lines.append(
                f"- [FALLO/IMPEDIMENTO]: La acción solicitada no fue posible ({ctx.failed_reason}). "
                f"Explica inmersivamente el motivo."
            )

        if not directive_lines:
            directive_lines.append(
                "- Responde a la pregunta del jugador y profundiza con detalles concretos basándote en la información de la entidad."
            )

        return {
            "entity_info": cls.format_entity(ctx.entity),
            "conversation_history": cls.format_conversation(ctx.inspection_history, ctx.player_input),
            "dm_agenda": "\n".join(directive_lines),
            "player_input": ctx.player_input or "",
        }

    @classmethod
    def dialogue_markdown(cls, ctx: Any) -> str:
        """Formatea el contexto completo de diálogo en Markdown de respaldo."""
        directive_block = f"## DIRECTIVA ACTUAL\n{ctx.directive}\n\n" if ctx.directive else ""
        return (
            f"## NPC\n{cls.format_npc(ctx.npc, detailed=False)}\n\n"
            f"{directive_block}"
            f"## CONVERSACIÓN\n{cls.format_conversation(ctx.conversation_history, ctx.player_input)}"
        )

    @classmethod
    def move_markdown(cls, ctx: Any) -> str:
        """Formatea el contexto completo de movimiento en Markdown de respaldo."""
        directive_block = f"## DIRECTIVA ACTUAL\n{ctx.directive}\n\n" if ctx.directive else ""
        return (
            f"# TRANSICIÓN DE MOVIMIENTO\n\n"
            f"## ORIGEN\n{cls.format_place(ctx.origin_place)}\n\n"
            f"## CAMINO RECORRIDO\n{cls.format_path(ctx.path_taken, ctx.estimated_travel_time)}\n\n"
            f"## DESTINO\n{cls.format_place(ctx.destination_place)}\n\n"
            f"{directive_block}"
            f'## ACCIÓN DEL JUGADOR\n"{ctx.player_input or ""}"'
        )

    @classmethod
    def explain_look_markdown(cls, ctx: Any) -> str:
        """Formatea el contexto completo de inspección en Markdown de respaldo."""
        directive_block = f"## DIRECTIVA ACTUAL\n{ctx.directive}\n\n" if ctx.directive else ""
        failed_block = f"## AVISO DE FALLO\n{ctx.failed_reason}\n\n" if getattr(ctx, "failed_reason", None) else ""
        return (
            f"# EXPLICACIÓN / INSPECCIÓN DE ENTIDAD\n\n"
            f"## ENTIDAD\n{cls.format_entity(ctx.entity)}\n\n"
            f"{directive_block}"
            f"{failed_block}"
            f"## CONVERSACIÓN\n{cls.format_conversation(ctx.inspection_history, ctx.player_input)}"
        )

    @classmethod
    def render(cls, ctx: Any) -> str:
        """Despacha y renderiza cualquier modelo de contexto a Markdown."""
        ctx_name = ctx.__class__.__name__
        if "Dialogue" in ctx_name:
            return cls.dialogue_markdown(ctx)
        if "Move" in ctx_name:
            return cls.move_markdown(ctx)
        if "Explain" in ctx_name or "Look" in ctx_name:
            return cls.explain_look_markdown(ctx)
        if hasattr(ctx, "to_markdown") and callable(getattr(ctx, "to_markdown")):
            return ctx.to_markdown()
        return str(ctx)
