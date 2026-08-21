from typing import List, Optional
from domains import World, Place, NPC, Player, GameState, TurnSummary

class ContextBuilder:
    """Clase responsable de extraer información y construir el contexto final en formato Markdown."""

    @staticmethod
    def build_classifier_context(world_state, game_state: GameState, player_input: str) -> str:
        """Genera el contexto para el Clasificador semántico."""
        current_place = game_state.current_place
        places_in_current_location = []
        if current_place:
            for location in world_state.world.locations:
                if any(p.id == current_place.id for p in location.places):
                    places_in_current_location = location.places
                    break

        md = "## LUGARES EN LA LOCALIZACIÓN\n"
        if places_in_current_location:
            for p in places_in_current_location:
                md += f"- `{p.id}`: {p.name}\n"
        else:
            md += "- (Ninguno)\n"

        md += "\n## NPCS EN LA LOCALIZACIÓN\n"
        if world_state.npcs:
            for npc in world_state.npcs.values():
                md += f"- `{npc.id}`: {npc.name}\n"
        else:
            md += "- (Ninguno)\n"

        md += f"\n* **player_input**: \"{player_input}\""
        return md

    @staticmethod
    def build_narrative_context(world_state, game_state: GameState, player_input: str) -> str:
        """Genera el contexto narrativo detallado para el Narrador (Dungeon Master)."""
        current_place = game_state.current_place

        md = "# CONTEXTO DEL MUNDO (AAdventure)\n"
        md += "Aquí se describe el lugar actual y quién está presente.\n\n"

        if current_place:
            md += "## LUGAR ACTUAL\n"
            md += f"* **Nombre**: {current_place.name}\n"
            md += f"* **Descripción**: {current_place.description}\n\n"

            md += "### Conexiones disponibles (salidas):\n"
            if current_place.connections:
                for direction, conn_name in current_place.connections.items():
                    md += f"- Al **{direction}**: {conn_name}\n"
            else:
                md += "- No hay salidas visibles desde este lugar.\n"
        else:
            md += "## LUGAR ACTUAL\n* Desconocido\n"

        md += "\n## PERSONAJES PRESENTES\n"
        md += "En este lugar se encuentran los siguientes personajes:\n"
        
        has_npcs = False
        if current_place:
            for entity_id in current_place.visible_entities:
                if entity_id in world_state.npcs:
                    npc = world_state.npcs[entity_id]
                    md += f"- **{npc.name}** (ID: `{npc.id}`): {npc.description}\n"
                    has_npcs = True
        
        if not has_npcs:
            md += "- No hay nadie más aquí.\n"

        # Historial de turnos
        md += "\n## HISTORIAL RECIENTE DE LA AVENTURA (Últimos Turnos)\n"
        if game_state.prev_turns:
            for turn in game_state.prev_turns:
                md += f"* **Jugador**: {turn.player_input}\n"
                md += f"* **Narración**: {turn.narration}\n"
        else:
            md += "* (La aventura acaba de comenzar)\n"

        md += f"\n* **player_input**: \"{player_input}\""
        return md

    @staticmethod
    def build_dialogue_context(world_state, game_state: GameState, npc: NPC, player_input: str) -> str:
        """Genera el contexto de diálogo, filtrando servicios y lore dinámico según afinidad y quests."""
        # 1. Filtrar servicios por afinidad
        unlocked_services = []
        for service in npc.services:
            if npc.affinity >= service.min_affinity and npc.affinity <= service.max_affinity:
                unlocked_services.append(service)

        # 2. Filtrar lore dinámico por afinidad y quests completadas
        unlocked_lore = []
        player = world_state.player
        for lb in npc.dynamic_lore:
            # Comprobar afinidad mínima
            if npc.affinity < lb.required_affinity:
                continue

            # Comprobar misiones requeridas
            quests_satisfied = True
            if lb.required_quests:
                for q_req in lb.required_quests:
                    if q_req not in player.completed_quests:
                        quests_satisfied = False
                        break

            if quests_satisfied:
                unlocked_lore.append(lb)

        # Renderizar en Markdown
        md = "## NPC CON EL QUE HABLAS\n"
        md += f"* **Nombre**: {npc.name} (ID: `{npc.id}`)\n"
        md += f"* **Descripción**: {npc.description}\n"
        md += f"* **Afinidad actual**: {npc.affinity:.2f} (rango: 0.0 - 1.0)\n"

        if unlocked_lore:
            md += "\n## INFORMACIÓN / LORE ADICIONAL DESBLOQUEADO\n"
            for lb in unlocked_lore:
                md += f"* {lb.content}\n"

        if unlocked_services:
            md += "\n## SERVICIOS QUE OFRECE ESTE NPC\n"
            for s in unlocked_services:
                md += f"* `{s.id}` (tipo: {s.type}): {s.description}"
                if s.cost is not None:
                    md += f" (costo: {s.cost} oro)"
                md += "\n"

        md += "\n## HISTORIAL DE CONVERSACIÓN\n"
        conv = npc.conversation
        if conv and conv.msg:
            for line in conv.msg:
                sender = list(line.keys())[0]
                text = line[sender]
                md += f"* **{sender}**: {text}\n"
        else:
            md += "* (No hay mensajes previos)\n"

        md += f"\n* **player_input**: \"{player_input}\""
        return md
