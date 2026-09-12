from typing import Optional, Union
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt
from domains.projections import GameStateProjection
from domains.system.system_domains import GameState


class GameStateInspector(QTreeWidget):
    """
    Inspector visual que desglosa el GameState actual del juego en tiempo real
    a partir de proyecciones DTO inmutables (GameStateProjection).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Inspector del GameState")
        self.setColumnCount(1)
        self.setAlternatingRowColors(True)

    def update_state(
        self,
        game_state: Union[GameStateProjection, GameState],
        formatted_time: Optional[str] = None,
    ) -> None:
        """Limpia y reconstruye el árbol con la información del GameStateProjection actual."""
        self.clear()
        if not game_state:
            return

        if isinstance(game_state, GameStateProjection):
            self._render_dto_state(game_state)
        else:
            self._render_legacy_state(game_state, formatted_time or "")

    def _render_dto_state(self, state: GameStateProjection) -> None:
        """Renderiza el estado a partir del DTO canónico GameStateProjection."""
        # 1. PARÁMETROS DE RUNTIME STATE
        item_state = QTreeWidgetItem(self)
        item_state.setText(0, f"player_state: {state.player_state}")

        item_target = QTreeWidgetItem(self)
        item_target.setText(0, f"player_target: '{state.player_target or ''}'")

        if state.player_state.upper() == "TALK" and state.active_npc_affinity is not None:
            item_aff = QTreeWidgetItem(self)
            pct = int(round(state.active_npc_affinity * 100))
            item_aff.setText(0, f"active_npc_affinity: {state.active_npc_affinity:.2f} ({pct}%)")

        item_curr = QTreeWidgetItem(self)
        item_curr.setText(0, f"current_place: {state.current_place or 'Ninguno'}")

        item_prev = QTreeWidgetItem(self)
        item_prev.setText(0, f"prev_place: {state.prev_place or 'Ninguno'}")

        item_speed = QTreeWidgetItem(self)
        item_speed.setText(0, f"travel_speed: {state.travel_speed} km/h")

        item_time = QTreeWidgetItem(self)
        item_time.setText(0, f"Tiempo Transcurrido: {state.formatted_time} ({state.elapsed_time} min)")

        # Separador visual
        sep = QTreeWidgetItem(self)
        sep.setText(0, "-" * 40)
        sep.setFlags(sep.flags() & ~Qt.ItemIsEnabled)

        # 1.5 SECCIÓN: CONVERSACIÓN ACTIVA (si estamos en TALK)
        if state.player_state.upper() == "TALK" and state.player_target:
            item_conv = QTreeWidgetItem(self)
            item_conv.setText(0, f"💬 Conversación Activa: {state.player_target}")

            npc_child = QTreeWidgetItem(item_conv)
            npc_child.setText(0, f"NPC: {state.player_target}")

            if state.active_npc_affinity is not None:
                aff_child = QTreeWidgetItem(item_conv)
                pct = int(round(state.active_npc_affinity * 100))
                if state.active_npc_affinity >= 0.7:
                    mood = "Amigable"
                elif state.active_npc_affinity <= 0.3:
                    mood = "Hostil / Desconfiado"
                else:
                    mood = "Neutral"
                aff_child.setText(0, f"Afinidad actual: {state.active_npc_affinity:.2f} ({pct}%) [{mood}]")

            sep_conv = QTreeWidgetItem(self)
            sep_conv.setText(0, "-" * 40)
            sep_conv.setFlags(sep_conv.flags() & ~Qt.ItemIsEnabled)

        # 2. SECCIÓN: JUGADOR (Player)
        player = state.player
        if player:
            item_player = QTreeWidgetItem(self)
            item_player.setText(0, f"Jugador: {player.name}")

            id_child = QTreeWidgetItem(item_player)
            id_child.setText(0, f"ID: {player.id}")

            desc_child = QTreeWidgetItem(item_player)
            desc_child.setText(0, f"Descripción: {player.description}")

            gold_child = QTreeWidgetItem(item_player)
            gold_child.setText(0, f"Oro: {player.gold} monedas")

            quest_child = QTreeWidgetItem(item_player)
            quest_child.setText(0, f"Misión Activa: {player.active_quest or 'Ninguna'}")

            completed_child = QTreeWidgetItem(item_player)
            completed_child.setText(0, f"Misiones Completadas: {len(player.completed_quests)}")

            inv_child = QTreeWidgetItem(item_player)
            inv_text = ", ".join(player.inventory) if player.inventory else "(Vacío)"
            inv_child.setText(0, f"Inventario: {inv_text}")

            visited_child = QTreeWidgetItem(item_player)
            visited_child.setText(0, f"Lugares Visitados: {len(player.visited_places)}")

        # 3. SECCIÓN: LUGAR DETALLADO (Place)
        place_detail = state.current_place_detail
        if place_detail:
            item_place = QTreeWidgetItem(self)
            item_place.setText(0, f"Lugar Actual: {place_detail.name}")

            pid_child = QTreeWidgetItem(item_place)
            pid_child.setText(0, f"ID: {place_detail.id}")

            pdesc_child = QTreeWidgetItem(item_place)
            pdesc_child.setText(0, f"Descripción: {place_detail.description}")

            pnpcs_child = QTreeWidgetItem(item_place)
            ents_text = ", ".join(place_detail.visible_entities) if place_detail.visible_entities else "Ninguno"
            pnpcs_child.setText(0, f"Entidades visibles: {ents_text}")

            if place_detail.connections:
                conn_group = QTreeWidgetItem(item_place)
                conn_group.setText(0, "Conexiones de salida:")
                for conn in place_detail.connections:
                    c_child = QTreeWidgetItem(conn_group)
                    c_child.setText(0, f"[{conn.direction}] -> {conn.target} ({conn.distance}m, {conn.terrain_type})")

        # 4. SECCIÓN: RESUMEN DE PERCEPCIÓN (Niebla de guerra)
        item_fog = QTreeWidgetItem(self)
        item_fog.setText(0, "Percepción del Jugador (Fog of War)")

        disc_child = QTreeWidgetItem(item_fog)
        disc_child.setText(0, f"Lugares Descubiertos: {len(state.discovered_places)}")

        npcs_child = QTreeWidgetItem(item_fog)
        npcs_text = ", ".join(state.visible_npcs) if state.visible_npcs else "(Ninguno)"
        npcs_child.setText(0, f"NPCs Visibles: {len(state.visible_npcs)} [{npcs_text}]")

        self.expandAll()

    def _render_legacy_state(self, game_state: GameState, formatted_time: str) -> None:
        """Renderizado de respaldo para objetos GameState no proyectados."""
        state = game_state.state
        if state:
            item_state = QTreeWidgetItem(self)
            item_state.setText(0, f"player_state: {state.player_state}")

            item_target = QTreeWidgetItem(self)
            item_target.setText(0, f"player_target: '{state.player_target or ''}'")

            aff = getattr(game_state, "active_npc_affinity", None)
            if aff is None and hasattr(state, "active_npc_affinity"):
                aff = state.active_npc_affinity
            if state.player_state.upper() == "TALK" and aff is not None:
                item_aff = QTreeWidgetItem(self)
                item_aff.setText(0, f"active_npc_affinity: {aff:.2f} ({int(round(aff * 100))}%)")

            curr_place_name = state.current_place.name if state.current_place else "Ninguno"
            item_curr = QTreeWidgetItem(self)
            item_curr.setText(0, f"current_place: {curr_place_name}")

            prev_place_name = state.prev_place.name if state.prev_place else "Ninguno"
            item_prev = QTreeWidgetItem(self)
            item_prev.setText(0, f"prev_place: {prev_place_name}")

            item_speed = QTreeWidgetItem(self)
            item_speed.setText(0, f"travel_speed: {state.travel_speed} km/h")

            item_time = QTreeWidgetItem(self)
            item_time.setText(0, f"Tiempo Transcurrido: {formatted_time} ({state.elapsed_time} min)")

        sep = QTreeWidgetItem(self)
        sep.setText(0, "-" * 40)
        sep.setFlags(sep.flags() & ~Qt.ItemIsEnabled)

        player = game_state.player
        if player:
            item_player = QTreeWidgetItem(self)
            item_player.setText(0, f"Jugador: {player.name}")
            id_child = QTreeWidgetItem(item_player)
            id_child.setText(0, f"ID: {player.id}")
            desc_child = QTreeWidgetItem(item_player)
            desc_child.setText(0, f"Descripción: {player.description}")
            gold_child = QTreeWidgetItem(item_player)
            gold_child.setText(0, f"Oro: {player.gold} monedas")

        place = game_state.place
        if place:
            item_place = QTreeWidgetItem(self)
            item_place.setText(0, f"Lugar Actual: {place.name}")
            pid_child = QTreeWidgetItem(item_place)
            pid_child.setText(0, f"ID: {place.id}")
            pdesc_child = QTreeWidgetItem(item_place)
            pdesc_child.setText(0, f"Descripción: {place.description}")

        self.expandAll()
