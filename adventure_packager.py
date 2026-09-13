import os
import zipfile
import json
import tempfile
import shutil
from typing import Optional, Dict, Any, List

class AdventurePackager:
    """
    Clase de utilidad para empaquetar y desempaquetar archivos .aad (AAdventure data).
    Un archivo .aad es un contenedor ZIP que contiene 6 archivos JSON:
    - world.json: Localizaciones y Lugares con conexiones.
    - npcs.json: NPCs, afinidad y motivaciones.
    - player.json: Datos de jugador, oro, inventario, active_block y lugar de inicio.
    - objects.json: Objetos e items del mundo.
    - loreblocks.json: Catálogo centralizado de LoreBlocks (HSM).
    - story_config.json: Banderas de simulación (elapsed_time, fog_war).
    """

    @staticmethod
    def pack(
        output_path: str,
        world_data: dict,
        npcs_data: dict,
        player_data: dict,
        objects_data: Optional[dict] = None,
        lore_data: Optional[dict] = None,
        config_data: Optional[dict] = None,
    ):
        """
        Empaqueta los datos de los 6 componentes en un archivo .aad.
        """
        if objects_data is None:
            objects_data = {"objects": []}
        if lore_data is None:
            lore_data = {"lore_blocks": []}
        if config_data is None:
            config_data = {"elapsed_time": True, "fog_war": True}

        temp_dir = tempfile.mkdtemp()
        try:
            files_to_write = {
                "world.json": world_data,
                "npcs.json": npcs_data,
                "player.json": player_data,
                "objects.json": objects_data,
                "loreblocks.json": lore_data,
                "story_config.json": config_data,
            }

            for filename, data in files_to_write.items():
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

            # Comprimir en formato ZIP renombrado a .aad
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for filename in files_to_write.keys():
                    file_path = os.path.join(temp_dir, filename)
                    zip_file.write(file_path, filename)
        finally:
            shutil.rmtree(temp_dir)

    @staticmethod
    def unpack_to_temp(aad_path: str) -> str:
        """
        Desempaqueta un archivo .aad en un directorio temporal y devuelve su ruta.
        Si proviene de una versión anterior de 3 archivos, autogenera los 3 archivos
        faltantes (objects.json, loreblocks.json, story_config.json) garantizando
        compatibilidad total hacia atrás.
        """
        if not os.path.exists(aad_path):
            raise FileNotFoundError(f"No se encontró el archivo de aventura: {aad_path}")

        temp_dir = tempfile.mkdtemp(prefix="aadventure_")
        with zipfile.ZipFile(aad_path, "r") as zip_file:
            zip_file.extractall(temp_dir)

        # 1. Asegurar objects.json
        obj_file = os.path.join(temp_dir, "objects.json")
        if not os.path.exists(obj_file):
            extracted_objects = []
            # Intentar rescatar objetos embebidos en world.json
            world_file = os.path.join(temp_dir, "world.json")
            if os.path.exists(world_file):
                try:
                    with open(world_file, "r", encoding="utf-8") as f:
                        w_data = json.load(f)
                    world_obj = w_data.get("world", {})
                    for loc in world_obj.get("locations", []):
                        for place in loc.get("places", []):
                            for it in place.get("items", []):
                                it_copy = dict(it)
                                it_copy["initial_place"] = place.get("id") or place.get("name")
                                extracted_objects.append(it_copy)
                except Exception:
                    pass
            with open(obj_file, "w", encoding="utf-8") as f:
                json.dump({"objects": extracted_objects}, f, indent=2, ensure_ascii=False)

        # 2. Asegurar loreblocks.json
        lore_file = os.path.join(temp_dir, "loreblocks.json")
        if not os.path.exists(lore_file):
            extracted_lore = []
            # Intentar rescatar dynamic_lore de lugares y npcs
            world_file = os.path.join(temp_dir, "world.json")
            if os.path.exists(world_file):
                try:
                    with open(world_file, "r", encoding="utf-8") as f:
                        w_data = json.load(f)
                    world_obj = w_data.get("world", {})
                    for loc in world_obj.get("locations", []):
                        for place in loc.get("places", []):
                            for lb in place.get("dynamic_lore", []):
                                extracted_lore.append(lb)
                            for it in place.get("items", []):
                                for lb in it.get("dynamic_lore", []):
                                    extracted_lore.append(lb)
                except Exception:
                    pass
            npcs_file = os.path.join(temp_dir, "npcs.json")
            if os.path.exists(npcs_file):
                try:
                    with open(npcs_file, "r", encoding="utf-8") as f:
                        n_data = json.load(f)
                    for n in n_data.get("NPCS", n_data.get("npcs", [])):
                        for lb in n.get("dynamic_lore", []):
                            extracted_lore.append(lb)
                except Exception:
                    pass
            with open(lore_file, "w", encoding="utf-8") as f:
                json.dump({"lore_blocks": extracted_lore}, f, indent=2, ensure_ascii=False)

        # 3. Asegurar story_config.json
        config_file = os.path.join(temp_dir, "story_config.json")
        if not os.path.exists(config_file):
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump({"elapsed_time": True, "fog_war": True}, f, indent=2, ensure_ascii=False)

        return temp_dir
