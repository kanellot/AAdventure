"""Cálculo de rutas y caminos mínimos en el grafo de lugares del mundo."""

import heapq
from typing import Dict, List, Optional, Tuple
from domains.world import Connection, Place


class PathCalculator:
    """Calculador de caminos mínimos y rutas sobre el grafo de lugares (Places)."""

    @staticmethod
    def _build_place_lookups(places: Dict[str, Place]) -> Tuple[Dict[str, Place], Dict[str, Place]]:
        """Construye índices rápidos por nombre y por id."""
        by_name: Dict[str, Place] = {}
        by_id: Dict[str, Place] = {}
        for p in places.values():
            by_name[p.name] = p
            by_id[p.id] = p
        return by_name, by_id

    @classmethod
    def resolve_place(cls, places: Dict[str, Place], identifier: str) -> Optional[Place]:
        """Resuelve un Place por nombre o por id dentro del diccionario."""
        if not identifier:
            return None
        if identifier in places:
            return places[identifier]
        by_name, by_id = cls._build_place_lookups(places)
        if identifier in by_name:
            return by_name[identifier]
        if identifier in by_id:
            return by_id[identifier]
        return None

    @classmethod
    def find_shortest_path(
        cls,
        places: Dict[str, Place],
        start_name_or_id: str,
        end_name_or_id: str,
        only_passable: bool = True,
    ) -> Tuple[List[Connection], List[Place]]:
        """Encuentra la ruta con menor distancia acumulada entre dos lugares usando Dijkstra."""
        by_name, by_id = cls._build_place_lookups(places)
        start_place = cls.resolve_place(places, start_name_or_id)
        end_place = cls.resolve_place(places, end_name_or_id)

        if not start_place or not end_place:
            return [], []

        if start_place.id == end_place.id:
            return [], [start_place]

        distances: Dict[str, float] = {p.id: float("inf") for p in by_id.values()}
        distances[start_place.id] = 0.0

        queue: List[Tuple[float, str, List[Connection], List[Place]]] = [
            (0.0, start_place.id, [], [start_place])
        ]

        shortest_conns: Optional[List[Connection]] = None
        shortest_places: Optional[List[Place]] = None

        while queue:
            dist, current_id, conns_path, places_path = heapq.heappop(queue)

            if dist > distances[current_id]:
                continue

            if current_id == end_place.id:
                shortest_conns = conns_path
                shortest_places = places_path
                break

            current_place = by_id[current_id]
            for _, conn in current_place.connections.items():
                if only_passable and not getattr(conn, "passable", True):
                    continue

                neighbor_place = by_name.get(conn.target) or by_id.get(conn.target)
                if not neighbor_place:
                    continue

                new_dist = dist + conn.distance
                if new_dist < distances[neighbor_place.id]:
                    distances[neighbor_place.id] = new_dist
                    heapq.heappush(
                        queue,
                        (
                            new_dist,
                            neighbor_place.id,
                            conns_path + [conn],
                            places_path + [neighbor_place],
                        ),
                    )

        if shortest_conns is None or shortest_places is None:
            return [], []

        return shortest_conns, shortest_places

    @classmethod
    def calculate_navigation_route(
        cls,
        places: Dict[str, Place],
        start_name_or_id: str,
        end_name_or_id: str,
    ) -> Tuple[str, List[Connection], List[Place], Optional[Place], Optional[Connection]]:
        """
        Calcula la ruta de navegación entre origen y destino teniendo en cuenta bloqueos de paso.
        Retorna:
            status: 'complete' (llega al destino),
                    'blocked' (se detiene antes de una conexión cerrada),
                    'unreachable' (destino inalcanzable en el grafo).
            conns: Lista de conexiones transitadas hasta el destino o lugar de detención.
            places_path: Lista de lugares transitados (incluyendo origen y destino/detención).
            stopping_place: Lugar donde el jugador se detiene si está bloqueado.
            blocked_conn: Conexión que impidió continuar el avance.
        """
        # 1. Intentar ruta completamente abierta
        open_conns, open_places = cls.find_shortest_path(
            places, start_name_or_id, end_name_or_id, only_passable=True
        )
        if open_places:
            return "complete", open_conns, open_places, None, None

        # 2. Si no hay ruta abierta, buscar el camino ideal ignorando bloqueos
        all_conns, all_places = cls.find_shortest_path(
            places, start_name_or_id, end_name_or_id, only_passable=False
        )
        if not all_places:
            return "unreachable", [], [], None, None

        # 3. Recorrer la ruta desde el origen hasta hallar la primera conexión bloqueada
        traversed_conns: List[Connection] = []
        traversed_places: List[Place] = [all_places[0]]

        for idx, conn in enumerate(all_conns):
            if not getattr(conn, "passable", True):
                stopping_place = all_places[idx]
                blocked_conn = conn
                return "blocked", traversed_conns, traversed_places, stopping_place, blocked_conn
            traversed_conns.append(conn)
            traversed_places.append(all_places[idx + 1])

        return "complete", traversed_conns, traversed_places, None, None

    @classmethod
    def find_intermediate_places(
        cls,
        places: Dict[str, Place],
        start_name_or_id: str,
        end_name_or_id: str,
        only_passable: bool = True,
    ) -> List[Place]:
        """Retorna los lugares intermedios entre origen y destino."""
        _, full_places = cls.find_shortest_path(
            places, start_name_or_id, end_name_or_id, only_passable=only_passable
        )
        if len(full_places) <= 2:
            return []
        return full_places[1:-1]

    @classmethod
    def find_full_path(
        cls,
        places: Dict[str, Place],
        start_name_or_id: str,
        end_name_or_id: str,
        only_passable: bool = True,
    ) -> List[Place]:
        """Retorna la lista completa de lugares desde el origen hasta el destino."""
        _, full_places = cls.find_shortest_path(
            places, start_name_or_id, end_name_or_id, only_passable=only_passable
        )
        return full_places


