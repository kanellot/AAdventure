from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt
from domains import GameState

class GameStateInspector(QTreeWidget):
    """
    Inspector visual que desglosa el GameState actual del juego en tiempo real.
    Muestra los parámetros del RuntimeState en la raíz y organiza el
    resto del estado en nodos secundarios.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Inspector del GameState")
        self.setColumnCount(1)
        self.setAlternatingRowColors(True)

    def update_state(self, game_state: GameState, formatted_time: str):
        """
        Limpia y reconstruye el árbol con la información del GameState actual.
        """
        self.clear()
        if not game_state:
            return

        # 1. PARÁMETROS DE RUNTIME STATE (Desglosados en el nivel raíz)
        state = game_state.state
        if state:
            # Player State
            item_state = QTreeWidgetItem(self)
            item_state.setText(0, f"Estado del Jugador (player_state): {state.player_state}")
            
            # Player Target
            item_target = QTreeWidgetItem(self)
            item_target.setText(0, f"Objetivo del Jugador (player_target): '{state.player_target or ''}'")
            
            # Current Place (Proyección)
            curr_place_name = state.current_place.name if state.current_place else "Ninguno"
            item_curr = QTreeWidgetItem(self)
            item_curr.setText(0, f"Lugar Actual (current_place): {curr_place_name}")
            
            # Prev Place (Proyección)
            prev_place_name = state.prev_place.name if state.prev_place else "Ninguno"
            item_prev = QTreeWidgetItem(self)
            item_prev.setText(0, f"Lugar Anterior (prev_place): {prev_place_name}")
            
            # Travel Speed
            item_speed = QTreeWidgetItem(self)
            item_speed.setText(0, f"Velocidad de Viaje (travel_speed): {state.travel_speed} km/h")
            
            # Elapsed Time (Minutos y Formateado)
            item_time = QTreeWidgetItem(self)
            item_time.setText(0, f"Tiempo Transcurrido: {formatted_time} ({state.elapsed_time} min)")

        # Separador visual
        sep = QTreeWidgetItem(self)
        sep.setText(0, "-" * 40)
        sep.setFlags(sep.flags() & ~Qt.ItemIsEnabled) # Deshabilitado para clic

        # 2. SECCIÓN: JUGADOR (Player)
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
            
            quest_child = QTreeWidgetItem(item_player)
            quest_child.setText(0, f"Misión Activa: {player.active_quest or 'Ninguna'}")
            
            completed_child = QTreeWidgetItem(item_player)
            completed_child.setText(0, f"Misiones Completadas: {len(player.completed_quests)}")

        # 3. SECCIÓN: LUGAR DETALLADO (Place)
        place = game_state.place
        if place:
            item_place = QTreeWidgetItem(self)
            item_place.setText(0, f"Lugar Actual: {place.name}")
            
            pid_child = QTreeWidgetItem(item_place)
            pid_child.setText(0, f"ID: {place.id}")
            
            pdesc_child = QTreeWidgetItem(item_place)
            pdesc_child.setText(0, f"Descripción: {place.description}")
            
            pnpcs_child = QTreeWidgetItem(item_place)
            pnpcs_child.setText(0, f"NPCs en este lugar: {', '.join(place.visible_entities) if place.visible_entities else 'Ninguno'}")
            
            # Conexiones
            if place.connections:
                conn_group = QTreeWidgetItem(item_place)
                conn_group.setText(0, "Conexiones de salida:")
                for direction, conn in place.connections.items():
                    c_child = QTreeWidgetItem(conn_group)
                    c_child.setText(0, f"[{direction}] -> {conn.target} ({conn.distance}m, {conn.terrain_type})")

        # 4. SECCIÓN: NPCs CARGADOS
        npcs = game_state.npcs
        if npcs:
            item_npcs_group = QTreeWidgetItem(self)
            item_npcs_group.setText(0, f"NPCs Cargados en Memoria ({len(npcs)})")
            
            for npc_id, npc in npcs.items():
                npc_item = QTreeWidgetItem(item_npcs_group)
                npc_item.setText(0, f"NPC: {npc.name} ({npc_id})")
                
                ndesc = QTreeWidgetItem(npc_item)
                ndesc.setText(0, f"Descripción: {npc.description}")
                
                nstate = QTreeWidgetItem(npc_item)
                nstate.setText(0, f"Estado: {npc.state}")
                
                naff = QTreeWidgetItem(npc_item)
                naff.setText(0, f"Afinidad: {npc.affinity}")
                
                if npc.motivations:
                    nmot = QTreeWidgetItem(npc_item)
                    nmot.setText(0, f"Likes: {', '.join(npc.motivations.likes)}")
                    ndis = QTreeWidgetItem(npc_item)
                    ndis.setText(0, f"Dislikes: {', '.join(npc.motivations.dislikes)}")

        self.expandAll()
