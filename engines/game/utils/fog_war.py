"""Sistema de Niebla de Guerra (Fog of War) para exploración del mundo."""

from typing import Dict, Iterable, List, Optional, Set, Tuple, Union
from domains.npcs import NPC
from domains.world import Place, World


class PlaceItem(str):
    """
    Subclase de str que representa el nombre de un lugar junto con su estado en la niebla de guerra.
    Al heredar de str es 100% compatible con código que espere strings simples,
    pero permite acceder a atributos como .status ('visited' | 'visible' | 'hidden').
    """

    status: str
    name: str

    def __new__(cls, name: str, status: str = "visited"):
        obj = super().__new__(cls, name)
        obj.status = status
        obj.name = name
        return obj

    def get(self, key: str, default=None):
        if key == "name":
            return str(self)
        if key == "status":
            return self.status
        return default

    def to_dict(self) -> dict:
        return {"name": str(self), "status": self.status}


class FogWar:
    """
    Controlador de la Niebla de Guerra (Fog of War).
    
    Reglas de visibilidad:
    1. Lugares visitados ('visited'):
       - Lugares donde el jugador ha estado físicamente.
       - Permanecen visitados permanentemente.
       - Revelan tanto el lugar como todos los NPCs que habitan en él.
    2. Lugares visibles ('visible'):
       - Lugares colindantes (conectados directamente a un lugar visitado) pero aún no visitados.
       - Son visibles para el jugador en el mapa/árbol, pero NO revelan sus NPCs hasta que
         el jugador viaje hasta ellos.
    3. Lugares ocultos ('hidden'):
       - Lugares no conectados a ningún lugar visitado. Están sumergidos en la niebla y no se listan.
    """

    def __init__(
        self,
        places: Optional[Dict[str, Place]] = None,
        initial_place: Optional[Union[str, Place]] = None,
        visited_places: Optional[Iterable[str]] = None,
        world: Optional[World] = None,
        npcs: Optional[Dict[str, NPC]] = None,
    ):
        self._places_by_name: Dict[str, Place] = {}
        self._places_by_id: Dict[str, Place] = {}
        self._visited_names: Set[str] = set()
        self._world: Optional[World] = None
        self._npcs: Dict[str, NPC] = {}
        self._npcs_by_name: Dict[str, NPC] = {}

        if world:
            self.set_world(world, npcs)
        elif places:
            self.set_places(places)

        if npcs:
            self.set_npcs(npcs)

        if visited_places:
            for p in visited_places:
                self.visit(p)

        if initial_place:
            self.visit(initial_place)

    def set_world(self, world: World, npcs: Optional[Dict[str, NPC]] = None) -> None:
        """Configura el mundo completo y extrae los índices de lugares."""
        self._world = world
        self._places_by_name.clear()
        self._places_by_id.clear()

        for location in world.locations:
            for place in location.places:
                self._places_by_name[place.name] = place
                self._places_by_id[place.id] = place

        if npcs:
            self.set_npcs(npcs)

    def set_places(self, places: Dict[str, Place]) -> None:
        """Configura el diccionario de lugares por nombre o id."""
        self._places_by_name.clear()
        self._places_by_id.clear()
        for p in places.values():
            self._places_by_name[p.name] = p
            self._places_by_id[p.id] = p

    def set_npcs(self, npcs: Dict[str, NPC]) -> None:
        """Configura el catálogo de NPCs disponibles."""
        self._npcs = dict(npcs)
        self._npcs_by_name = {npc.name: npc for npc in npcs.values()}

    def _resolve_place(self, place_or_name_or_id: Union[str, Place]) -> Optional[Place]:
        """Resuelve un Place a partir de su instancia, nombre o id."""
        if not place_or_name_or_id:
            return None
        if isinstance(place_or_name_or_id, Place):
            return place_or_name_or_id
        if place_or_name_or_id in self._places_by_name:
            return self._places_by_name[place_or_name_or_id]
        if place_or_name_or_id in self._places_by_id:
            return self._places_by_id[place_or_name_or_id]

        target_clean = str(place_or_name_or_id).strip().lower()
        for name, p in self._places_by_name.items():
            if name.lower() == target_clean:
                return p
        for pid, p in self._places_by_id.items():
            if pid.lower() == target_clean:
                return p

        return None

    def visit(self, place: Union[str, Place]) -> bool:
        """
        Marca un lugar como visitado de forma permanente.
        Retorna True si es un lugar nuevo que no había sido visitado previamente.
        """
        p = self._resolve_place(place)
        canonical_name = p.name if p else str(place).strip()
        if not canonical_name:
            return False

        if canonical_name not in self._visited_names:
            self._visited_names.add(canonical_name)
            return True
        return False

    def is_visited(self, place: Union[str, Place]) -> bool:
        """Comprueba si el lugar ya ha sido visitado."""
        p = self._resolve_place(place)
        name = p.name if p else str(place).strip()
        return name in self._visited_names

    def is_visible(self, place: Union[str, Place]) -> bool:
        """
        Comprueba si el lugar es colindante a algún lugar visitado pero aún no visitado.
        """
        if self.is_visited(place):
            return False

        p = self._resolve_place(place)
        if not p:
            return False

        # Verificar si algún lugar visitado conecta hacia este lugar
        target_name = p.name
        target_id = p.id

        for visited_name in self._visited_names:
            v_place = self._places_by_name.get(visited_name) or self._places_by_id.get(visited_name)
            if not v_place:
                continue

            for conn in v_place.connections.values():
                if conn.target in (target_name, target_id):
                    return True

        # Verificar también si este lugar tiene conexiones salientes hacia un lugar visitado
        for conn in p.connections.values():
            if conn.target in self._visited_names:
                return True
            resolved_target = self._resolve_place(conn.target)
            if resolved_target and resolved_target.name in self._visited_names:
                return True

        return False

    def is_hidden(self, place: Union[str, Place]) -> bool:
        """Comprueba si el lugar está completamente oculto en la niebla."""
        return not self.is_visited(place) and not self.is_visible(place)

    def get_place_status(self, place: Union[str, Place]) -> str:
        """
        Retorna el estado del lugar: 'visited', 'visible' o 'hidden'.
        """
        if self.is_visited(place):
            return "visited"
        if self.is_visible(place):
            return "visible"
        return "hidden"

    def get_visited_places(self) -> List[str]:
        """Retorna la lista ordenada de nombres de todos los lugares visitados."""
        return sorted(list(self._visited_names))

    def get_visible_places(self) -> List[str]:
        """
        Retorna la lista ordenada de nombres de todos los lugares colindantes a los visitados,
        excluyendo los que ya fueron visitados.
        """
        visible = set()
        for p in self._places_by_name.values():
            if p.name not in self._visited_names and self.is_visible(p):
                visible.add(p.name)
        return sorted(list(visible))

    def get_hidden_places(self) -> List[str]:
        """Retorna la lista de lugares aún no descubiertos."""
        visited = self._visited_names
        visible = set(self.get_visible_places())
        hidden = []
        for p in self._places_by_name.values():
            if p.name not in visited and p.name not in visible:
                hidden.append(p.name)
        return sorted(hidden)

    def get_all_discovered_places(self) -> List[str]:
        """Retorna la lista de todos los lugares descubiertos (visitados + visibles)."""
        visited = set(self.get_visited_places())
        visible = set(self.get_visible_places())
        return sorted(list(visited | visible))

    def get_visible_npcs(self, place_name_or_id: Optional[Union[str, Place]] = None) -> List[str]:
        """
        Retorna los nombres de los NPCs visibles.
        - Si se especifica un lugar: solo retorna sus NPCs si ese lugar ha sido visitado.
          Si el lugar solo es 'visible' o 'hidden', retorna lista vacía.
        - Si no se especifica lugar: retorna todos los NPCs que habitan en lugares visitados.
        """
        npcs_dict = self._npcs
        npcs_by_name = self._npcs_by_name

        if place_name_or_id is not None:
            p = self._resolve_place(place_name_or_id)
            if not p or not self.is_visited(p):
                return []

            place_npcs = []
            for ent_id in p.visible_entities:
                npc = npcs_dict.get(ent_id) or npcs_by_name.get(ent_id)
                if npc:
                    place_npcs.append(npc.name)
            return sorted(place_npcs)

        # Todos los NPCs de lugares visitados
        visible_npcs = set()
        for v_name in self._visited_names:
            p = self._places_by_name.get(v_name) or self._places_by_id.get(v_name)
            if not p:
                continue
            for ent_id in p.visible_entities:
                npc = npcs_dict.get(ent_id) or npcs_by_name.get(ent_id)
                if npc:
                    visible_npcs.add(npc.name)
        return sorted(list(visible_npcs))

    def get_entities_hierarchy(
        self,
        world: Optional[World] = None,
        npcs: Optional[Dict[str, NPC]] = None,
        filter_by_fog: bool = True,
    ) -> List[dict]:
        """
        Construye la estructura jerárquica de localizaciones, lugares y NPCs para la UI.
        
        Si filter_by_fog es True:
        - Solo incluye lugares que sean 'visited' o 'visible'.
        - Para lugares 'visited': los marca con status='visited' y revela sus NPCs.
        - Para lugares 'visible': los marca con status='visible' y NO revela sus NPCs.
        - Si una localización no contiene ningún lugar descubierto, no se incluye.
        """
        w = world or self._world
        if not w:
            return []

        npcs_dict = npcs if npcs is not None else self._npcs
        npcs_by_name = {n.name: n for n in npcs_dict.values()}

        hierarchy = []

        for loc in w.locations:
            places_list: List[PlaceItem] = []
            visited_in_loc: List[str] = []
            visible_in_loc: List[str] = []
            npcs_in_loc: List[str] = []
            seen_loc_npcs: Set[str] = set()

            for place in loc.places:
                status = self.get_place_status(place)

                if status == "visited":
                    item = PlaceItem(place.name, status="visited")
                    places_list.append(item)
                    visited_in_loc.append(place.name)

                    # Revelar NPCs solo de lugares visitados
                    for ent_id in place.visible_entities:
                        npc = npcs_dict.get(ent_id) or npcs_by_name.get(ent_id)
                        if npc and npc.name not in seen_loc_npcs:
                            npcs_in_loc.append(npc.name)
                            seen_loc_npcs.add(npc.name)

                elif status == "visible":
                    item = PlaceItem(place.name, status="visible")
                    places_list.append(item)
                    visible_in_loc.append(place.name)
                    # NPCs NO se revelan para lugares solo visibles

                elif not filter_by_fog:
                    item = PlaceItem(place.name, status="hidden")
                    places_list.append(item)

            if filter_by_fog and not places_list:
                # Localización completamente desconocida
                continue

            hierarchy.append({
                "location_name": loc.name,
                "places": sorted(places_list, key=lambda p: p.name),
                "visited_places": sorted(visited_in_loc),
                "visible_places": sorted(visible_in_loc),
                "npcs": sorted(npcs_in_loc),
            })

        return hierarchy

    def export_state(self) -> dict:
        """Serializa el estado de la niebla para guardado."""
        return {
            "visited_places": self.get_visited_places(),
            "visible_places": self.get_visible_places(),
        }

    def import_state(self, data: dict) -> None:
        """Restaura el estado de lugares visitados a partir de un diccionario."""
        visited = data.get("visited_places", [])
        for v in visited:
            self.visit(v)


# Alias por compatibilidad
fog_war = FogWar
