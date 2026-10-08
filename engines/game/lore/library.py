"""Biblioteca canónica inmutable de LoreBlocks (definiciones de autoría)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class LoreLibrary:
    """Almacena todas las definiciones de LoreBlock de una aventura indexadas por ID."""

    def __init__(self, blocks: Optional[List[Any]] = None):
        self._blocks: Dict[str, Dict[str, Any]] = {}
        if blocks:
            for b in blocks:
                self.register(b)

    def register(self, block: Any) -> None:
        """Registra o actualiza una definición de LoreBlock en la biblioteca."""
        if isinstance(block, dict):
            bid = block.get("id")
            if bid:
                self._blocks[bid] = dict(block)
        elif hasattr(block, "id"):
            bid = getattr(block, "id")
            if bid:
                self._blocks[bid] = block.model_dump() if hasattr(block, "model_dump") else block.__dict__

    def get(self, block_id: str, default: Any = None) -> Optional[Dict[str, Any]]:
        """Obtiene la definición de un bloque por ID."""
        return self._blocks.get(block_id, default)

    def __getitem__(self, block_id: str) -> Dict[str, Any]:
        return self._blocks[block_id]

    def __contains__(self, block_id: str) -> bool:
        return block_id in self._blocks

    def __len__(self) -> int:
        return len(self._blocks)

    def get_all(self) -> List[Dict[str, Any]]:
        """Retorna todas las definiciones de LoreBlocks registradas."""
        return list(self._blocks.values())

    def get_depth(self, block_id: str) -> int:
        """Calcula la profundidad jerárquica del bloque (0 para bloques raíz)."""
        depth = 0
        curr_id = block_id
        visited = set()
        while curr_id and curr_id not in visited:
            visited.add(curr_id)
            blk = self._blocks.get(curr_id)
            if not blk:
                break
            parent_id = blk.get("parent_id")
            if not parent_id:
                break
            depth += 1
            curr_id = parent_id
        return depth

    def get_children_ids(self, block_id: str) -> List[str]:
        """Retorna los IDs de todos los hijos directos del bloque."""
        return [bid for bid, blk in self._blocks.items() if blk.get("parent_id") == block_id]

    def is_container(self, block_id: str) -> bool:
        """Determina si un bloque es un contenedor estructural (Chapter o Quest)."""
        blk = self._blocks.get(block_id)
        return bool(blk and blk.get("type") in ("Chapter", "Quest"))
