"""Lector rápido de metadatos de archivos de aventura (.aad) sin extracción a disco."""

import os
import zipfile
import json
from datetime import datetime
from typing import Optional
from adventure_selector.models import AdventureMetadata


def read_adventure_metadata(aad_path: str) -> AdventureMetadata:
    """Inspecciona un archivo .aad directamente en memoria para extraer sus metadatos.

    No descomprime nada en el sistema de archivos temporal, haciéndolo instantáneo.
    """
    file_name = os.path.basename(aad_path)

    if not os.path.exists(aad_path):
        return AdventureMetadata(
            file_path=aad_path,
            file_name=file_name,
            is_valid=False,
            error_message=f"El archivo no existe: {aad_path}",
        )

    try:
        file_stat = os.stat(aad_path)
        size_kb = round(file_stat.st_size / 1024.0, 1)
        mod_time = datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M")

        with zipfile.ZipFile(aad_path, "r") as zf:
            namelist = set(zf.namelist())

            # 1. Leer world.json
            world_title = os.path.splitext(file_name)[0]
            world_desc = ""
            locations_count = 0
            places_count = 0

            if "world.json" in namelist:
                try:
                    w_data = json.loads(zf.read("world.json").decode("utf-8"))
                    world_obj = w_data.get("world", w_data)
                    world_title = world_obj.get("name") or world_obj.get("title") or world_title
                    world_desc = world_obj.get("description", "")
                    locs = world_obj.get("locations", [])
                    locations_count = len(locs)
                    places_count = sum(len(loc.get("places", [])) for loc in locs)
                except Exception as e:
                    world_desc = f"[Aviso al leer world.json: {e}]"

            # 2. Leer player.json
            player_name = "Aventurero"
            player_desc = ""
            initial_place = ""

            if "player.json" in namelist:
                try:
                    p_data = json.loads(zf.read("player.json").decode("utf-8"))
                    player_obj = p_data.get("player", p_data)
                    player_name = player_obj.get("name", player_name)
                    player_desc = player_obj.get("description", "")
                    initial_place = player_obj.get("initial_place") or player_obj.get("player_location", "")
                except Exception:
                    pass

            # 3. Leer npcs.json
            npcs_count = 0
            if "npcs.json" in namelist:
                try:
                    n_data = json.loads(zf.read("npcs.json").decode("utf-8"))
                    npcs = n_data.get("NPCS", n_data.get("npcs", []))
                    npcs_count = len(npcs)
                except Exception:
                    pass

            # 4. Leer objects.json
            objects_count = 0
            if "objects.json" in namelist:
                try:
                    o_data = json.loads(zf.read("objects.json").decode("utf-8"))
                    objs = o_data.get("objects", [])
                    objects_count = len(objs)
                except Exception:
                    pass

            # 5. Leer loreblocks.json
            lore_count = 0
            if "loreblocks.json" in namelist:
                try:
                    l_data = json.loads(zf.read("loreblocks.json").decode("utf-8"))
                    lbs = l_data.get("lore_blocks", [])
                    lore_count = len(lbs)
                except Exception:
                    pass

        return AdventureMetadata(
            file_path=os.path.abspath(aad_path),
            file_name=file_name,
            file_size_kb=size_kb,
            modified_time=mod_time,
            title=world_title,
            description=world_desc,
            player_name=player_name,
            player_description=player_desc,
            initial_place=initial_place,
            locations_count=locations_count,
            places_count=places_count,
            npcs_count=npcs_count,
            objects_count=objects_count,
            lore_blocks_count=lore_count,
            is_valid=True,
        )

    except zipfile.BadZipFile:
        return AdventureMetadata(
            file_path=aad_path,
            file_name=file_name,
            is_valid=False,
            error_message="El archivo no es un archivo .aad / ZIP válido o está dañado.",
        )
    except Exception as exc:
        return AdventureMetadata(
            file_path=aad_path,
            file_name=file_name,
            is_valid=False,
            error_message=f"Error al inspeccionar archivo: {exc}",
        )
