import os
import zipfile
import json
import tempfile
import shutil

class AdventurePackager:
    """
    Clase de utilidad para empaquetar y desempaquetar archivos .aad (AAdventure data).
    Un archivo .aad es un contenedor ZIP renombrado que contiene:
    - world.json
    - npcs.json
    - player.json
    """

    @staticmethod
    def pack(output_path: str, world_data: dict, npcs_data: dict, player_data: dict):
        """
        Empaqueta los datos de mundo, npcs y jugador en un archivo .aad.
        """
        # Crear un directorio temporal para escribir los JSON
        temp_dir = tempfile.mkdtemp()
        try:
            world_file = os.path.join(temp_dir, "world.json")
            npcs_file = os.path.join(temp_dir, "npcs.json")
            player_file = os.path.join(temp_dir, "player.json")

            with open(world_file, "w", encoding="utf-8") as f:
                json.dump(world_data, f, indent=2, ensure_ascii=False)
            with open(npcs_file, "w", encoding="utf-8") as f:
                json.dump(npcs_data, f, indent=2, ensure_ascii=False)
            with open(player_file, "w", encoding="utf-8") as f:
                json.dump(player_data, f, indent=2, ensure_ascii=False)

            # Comprimir en formato ZIP
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.write(world_file, "world.json")
                zip_file.write(npcs_file, "npcs.json")
                zip_file.write(player_file, "player.json")
        finally:
            shutil.rmtree(temp_dir)

    @staticmethod
    def unpack_to_temp(aad_path: str) -> str:
        """
        Desempaqueta un archivo .aad en un directorio temporal y devuelve su ruta.
        La persona que llama debe encargarse de borrar este directorio al finalizar.
        """
        if not os.path.exists(aad_path):
            raise FileNotFoundError(f"No se encontró el archivo de aventura: {aad_path}")

        temp_dir = tempfile.mkdtemp(prefix="aadventure_")
        with zipfile.ZipFile(aad_path, "r") as zip_file:
            zip_file.extractall(temp_dir)
        return temp_dir
