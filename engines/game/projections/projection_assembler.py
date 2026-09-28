"""Ensamblador de Proyecciones DTO para clientes de juego y depuración."""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
from domains.lore import EntityCondition
from domains.projections import (
    AvailableActionsProjection,
    ConnectionProjection,
    GameStateProjection,
    InventoryItemDTO,
    InventoryProjection,
    LocationHierarchyProjection,
    LoreBlockDetailProjection,
    LoreConditionDetailProjection,
    LoreGraphProjection,
    MapItemDTO,
    MapLocationDTO,
    MapNPCDTO,
    MapPlaceDTO,
    MoveOptionProjection,
    NotebookProjection,
    PlaceDetailProjection,
    PlaceProjection,
    PlayerSummaryProjection,
    RagEvaluationProjection,
    TurnDebugProjection,
    TurnOutput,
    TurnResultProjection,
    UIStateProjection,
    WorldHierarchyProjection,
    WorldMapProjection,
)
from engines.game.lore.condition_evaluator import LoreConditionEvaluator
from engines.game.state_controller import GameStateController
from engines.game.utils.lore_formatter import LoreGraphFormatter


class ProjectionAssembler:
    """Construye proyecciones desacopladas a partir del estado vivo del juego."""

    @classmethod
    def build_turn_result(
        cls,
        output: TurnOutput,
        ctrl: GameStateController,
        prompt_text: Optional[str] = None,
        rag_eval: Optional[RagEvaluationProjection] = None,
    ) -> TurnResultProjection:
        """Construye la proyección consolidada única de un turno."""
        world_map = cls.build_world_map_projection(ctrl)
        inventory = cls.build_inventory_projection(ctrl)
        notebook = NotebookProjection(quests=list(ctrl.game_state.notebook))
        turn_debug = TurnDebugProjection(
            prompt=prompt_text,
            engine_result=output.msg,
            rag_evaluation=rag_eval,
        )
        return TurnResultProjection(
            output=output,
            map=world_map,
            inventory=inventory,
            notebook=notebook,
            debug=turn_debug,
        )

    @classmethod
    def build_world_map_projection(cls, ctrl: GameStateController) -> WorldMapProjection:
        """Construye el mapa consolidado según la niebla de guerra: entidades solo al visitarse."""
        locations_dto: List[MapLocationDTO] = []
        for loc in ctrl.game_state.entity_map:
            places_dto: List[MapPlaceDTO] = []
            for p in loc.places:
                entities_dto: List[Union[MapNPCDTO, MapItemDTO]] = []
                if p.status == "visited":
                    for it in p.items:
                        if it.visible:
                            entities_dto.append(MapItemDTO(id=it.id, name=it.name, visible=it.visible))
                    for npc in p.npcs:
                        entities_dto.append(MapNPCDTO(id=npc.id, name=npc.name, status=npc.status))

                places_dto.append(
                    MapPlaceDTO(
                        id=p.id,
                        name=p.name,
                        status=p.status,
                        entities=entities_dto,
                    )
                )
            locations_dto.append(MapLocationDTO(id=loc.id, name=loc.name, places=places_dto))

        return WorldMapProjection(locations=locations_dto)

    @classmethod
    def build_inventory_projection(cls, ctrl: GameStateController) -> InventoryProjection:
        """Construye el inventario enriquecido con descripciones y saldo de oro."""
        items_dto: List[InventoryItemDTO] = []
        for it_id in ctrl.game_state.inventory.items:
            it_obj = ctrl.items_by_id.get(it_id)
            name = it_obj.name if it_obj else it_id
            desc = it_obj.description if it_obj else ""
            items_dto.append(InventoryItemDTO(id=it_id, name=name, description=desc))

        return InventoryProjection(items=items_dto, gold=ctrl.game_state.gold)

    @classmethod
    def build_ui_state_projection(cls, ctrl: GameStateController) -> UIStateProjection:
        """Construye la proyección consolidada para el HUD."""
        gs = ctrl.game_state
        curr_p = ctrl.places_by_id.get(gs.current_location)
        loc_name = curr_p.name if curr_p else gs.current_location
        active_aff = ctrl.get_npc_affinity(gs.player_target) if gs.player_target in ctrl.npcs_by_id else None
        return UIStateProjection(
            player_name=gs.player_name,
            gold=gs.gold,
            current_location=loc_name,
            formatted_time=gs.current_time or "Día 1, 08:00",
            game_state=gs.player_state,
            player_target=gs.player_target,
            active_npc_affinity=active_aff,
            can_send_message=(gs.player_state in ("TALK", "LOOK")),
            allowed_actions=["MOVE", "LOOK", "TALK"],
        )

    @classmethod
    def build_available_actions_projection(cls, ctrl: GameStateController) -> AvailableActionsProjection:
        """Devuelve las opciones y acciones accesibles en el turno actual."""
        curr_p = ctrl.places_by_id.get(ctrl.game_state.current_location)
        moves: List[MoveOptionProjection] = []
        if curr_p:
            for direction_or_id, conn in curr_p.connections.items():
                target_p = ctrl.places_by_id.get(conn.target) or ctrl.places_by_id.get(direction_or_id)
                dest_name = target_p.name if target_p else conn.target
                moves.append(
                    MoveOptionProjection(
                        direction=direction_or_id,
                        target=dest_name,
                        distance=conn.distance,
                        terrain=conn.terrain_type,
                    )
                )

        npcs_here: List[str] = []
        look_tgts: List[str] = [ctrl.game_state.current_location]
        for loc in ctrl.game_state.entity_map:
            for p in loc.places:
                if p.id == ctrl.game_state.current_location:
                    for npc in p.npcs:
                        npcs_here.append(npc.name)
                        look_tgts.append(npc.id)
                    for it in p.items:
                        if it.visible:
                            look_tgts.append(it.id)

        for it_id in ctrl.game_state.inventory.items:
            look_tgts.append(it_id)

        return AvailableActionsProjection(
            moves=moves,
            npcs=npcs_here,
            look_targets=look_tgts,
        )

    @classmethod
    def build_navigation_hierarchy(cls, ctrl: GameStateController) -> WorldHierarchyProjection:
        """Devuelve la jerarquía de lugares descubiertos bajo la niebla de guerra."""
        locs: List[LocationHierarchyProjection] = []
        for loc in ctrl.game_state.entity_map:
            places_dto: List[PlaceProjection] = []
            npcs_here: List[str] = []
            for p in loc.places:
                if p.status != "hidden":
                    places_dto.append(PlaceProjection(id=p.id, name=p.name, status=p.status))
                    if p.status == "visited":
                        for npc in p.npcs:
                            npcs_here.append(npc.name)
            if places_dto:
                locs.append(LocationHierarchyProjection(location_name=loc.name, places=places_dto, npcs=npcs_here))
        return WorldHierarchyProjection(locations=locs)

    @classmethod
    def build_entities_hierarchy(cls, ctrl: GameStateController) -> WorldHierarchyProjection:
        """Devuelve la jerarquía completa del mundo para depuración."""
        locs: List[LocationHierarchyProjection] = []
        for loc in ctrl.game_state.entity_map:
            places_dto: List[PlaceProjection] = []
            npcs_here: List[str] = []
            for p in loc.places:
                places_dto.append(PlaceProjection(id=p.id, name=p.name, status=p.status))
                for npc in p.npcs:
                    npcs_here.append(npc.name)
            locs.append(LocationHierarchyProjection(location_name=loc.name, places=places_dto, npcs=npcs_here))
        return WorldHierarchyProjection(locations=locs)

    @classmethod
    def build_lore_graph_projection(cls, ctrl: GameStateController) -> LoreGraphProjection:
        """Construye el grafo detallado de LoreBlocks para el depurador visual."""
        blocks: List[LoreBlockDetailProjection] = []
        active_ids = {b.get("id") for b in ctrl.game_state.loreblocks.active}
        done_ids = {b.get("id") for b in ctrl.game_state.loreblocks.done}

        categories = [
            ("active", ctrl.game_state.loreblocks.active),
            ("done", ctrl.game_state.loreblocks.done),
            ("unknown", ctrl.game_state.loreblocks.unknown),
        ]

        for state_name, cat_list in categories:
            for blk in cat_list:
                parent_id = blk.get("parent_id")
                is_acc = (
                    True
                    if state_name in ("active", "done")
                    else (not parent_id or parent_id in active_ids or parent_id in done_ids)
                )

                cond_projections = cls._build_condition_projections(blk.get("active_conditions", []) or [], ctrl)
                exit_cond_projections = cls._build_condition_projections(blk.get("done_conditions", []) or [], ctrl)

                blocks.append(
                    LoreBlockDetailProjection(
                        id=blk.get("id", ""),
                        name=blk.get("name", blk.get("id", "")),
                        title=blk.get("title", blk.get("name", "")),
                        type=blk.get("type") or "Chapter",
                        description=blk.get("description") or "",
                        state=state_name,
                        is_accessible=is_acc,
                        parent_id=blk.get("parent_id"),
                        rag_enabled=blk.get("rag_enabled", False),
                        trigger_phrases=list(blk.get("trigger_phrases", []) or []),
                        active_conditions=list(blk.get("active_conditions", []) or []),
                        done_conditions=list(blk.get("done_conditions", []) or []),
                        effects=list(blk.get("effects", []) or []),
                        conditions=cond_projections,
                        exit_conditions=exit_cond_projections,
                        directive=blk.get("directive", ""),
                    )
                )

        return LoreGraphProjection(
            blocks=blocks,
            total_count=len(blocks),
            active_count=len(ctrl.game_state.loreblocks.active),
            done_count=len(ctrl.game_state.loreblocks.done),
            unknown_count=len(ctrl.game_state.loreblocks.unknown),
        )

    @classmethod
    def _build_condition_projections(
        cls,
        groups: List[Any],
        ctrl: GameStateController,
    ) -> List[LoreConditionDetailProjection]:
        projections: List[LoreConditionDetailProjection] = []
        for grp in groups:
            grp_dict = grp if isinstance(grp, dict) else (grp.model_dump() if hasattr(grp, "model_dump") else {})
            for cond in grp_dict.get("conditions", []) or []:
                c_dict = cond if isinstance(cond, dict) else (cond.model_dump() if hasattr(cond, "model_dump") else {})
                c_obj = cond if isinstance(cond, EntityCondition) else EntityCondition(**c_dict)
                is_met = LoreConditionEvaluator.is_single_condition_met(c_dict, ctrl)
                if c_dict.get("is_negated"):
                    is_met = not is_met
                disp = LoreGraphFormatter.format_condition_display(c_obj, is_met, ctrl)
                projections.append(
                    LoreConditionDetailProjection(
                        entity_type=c_dict.get("entity_type", ""),
                        entity_id=c_dict.get("entity_id", ""),
                        sub_condition=c_dict.get("sub_condition", ""),
                        value=c_dict.get("value"),
                        is_negated=c_dict.get("is_negated", False),
                        is_met=is_met,
                        display_text=disp,
                    )
                )
        return projections

    @classmethod
    def build_game_state_projection(cls, ctrl: GameStateController, travel_speed: float = 4.5) -> GameStateProjection:
        """Devuelve la instantánea detallada del estado para el inspector visual."""
        gs = ctrl.game_state
        curr_p = ctrl.places_by_id.get(gs.current_location)
        conns_dto: List[ConnectionProjection] = []
        if curr_p:
            for d, c in curr_p.connections.items():
                conns_dto.append(
                    ConnectionProjection(
                        direction=d,
                        target=c.target,
                        distance=c.distance,
                        terrain_type=c.terrain_type,
                    )
                )

        detail = (
            PlaceDetailProjection(
                id=gs.current_location,
                name=curr_p.name if curr_p else gs.current_location,
                description=curr_p.description if curr_p else "",
                visible_entities=[
                    npc.name for loc in gs.entity_map for p in loc.places if p.id == gs.current_location for npc in p.npcs
                ],
                connections=conns_dto,
            )
            if curr_p
            else None
        )

        player_summary = PlayerSummaryProjection(
            id="player",
            name=gs.player_name,
            description="Protagonista",
            gold=gs.gold,
            player_location=gs.current_location,
            state=gs.player_state,
            active_quest=gs.notebook[0].name if gs.notebook else None,
            completed_quests=[q.name for q in gs.notebook if q.status == "done"],
            inventory=list(gs.inventory.items),
            visited_places=[p.id for loc in gs.entity_map for p in loc.places if p.status == "visited"],
        )

        active_aff = ctrl.get_npc_affinity(gs.player_target) if gs.player_target in ctrl.npcs_by_id else None
        return GameStateProjection(
            player=player_summary,
            player_state=gs.player_state,
            player_target=gs.player_target or "",
            active_npc_affinity=active_aff,
            current_place=gs.current_location,
            current_place_detail=detail,
            prev_place=None,
            travel_speed=travel_speed,
            elapsed_time=0,
            formatted_time=gs.current_time or "Día 1, 08:00",
            discovered_places=[p.id for loc in gs.entity_map for p in loc.places if p.status != "hidden"],
            visible_npcs=[
                npc.name for loc in gs.entity_map for p in loc.places if p.status != "hidden" for npc in p.npcs
            ],
            active_lore_blocks=[b.get("id", "") for b in gs.loreblocks.active],
            done_lore_blocks=[b.get("id", "") for b in gs.loreblocks.done],
        )
