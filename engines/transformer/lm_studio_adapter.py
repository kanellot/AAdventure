"""Adaptador para interactuar con un servidor local de LM Studio."""

import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Union
from engines.transformer.base_adapter import BaseLLMAdapter


class LMStudioAdapter(BaseLLMAdapter):
    """Adaptador para conectarse a un servidor local de LM Studio vía API HTTP."""

    def __init__(self, config: Union[str, Dict[str, Any]]):
        if isinstance(config, str):
            with open(config, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        elif isinstance(config, dict):
            self.config = config
        else:
            raise ValueError(f"Configuración inválida provista a LMStudioAdapter: {type(config)}")

        lm_config = self.config.get("lm_studio", {})
        self.base_url = lm_config.get("base_url", self.config.get("base_url", "http://localhost:1234/v1")).rstrip("/")
        self.api_key = lm_config.get("api_key", self.config.get("api_key", "lm-studio"))
        self.model = lm_config.get("model", self.config.get("model", "gemma-4-e2b-it-qat"))
        self.timeout = lm_config.get("timeout", self.config.get("timeout", 60))
        self.n_ctx = lm_config.get("n_ctx", self.config.get("n_ctx", 4096))
        self.n_gpu_layers = lm_config.get("n_gpu_layers", self.config.get("n_gpu_layers", -1))
        self.n_threads = lm_config.get("n_threads", self.config.get("n_threads", 4))
        self.auto_reload = lm_config.get("auto_reload_lm_studio", self.config.get("auto_reload_lm_studio", True))
        self.inference_profiles = self.config.get("inference_profiles", {})

        if self.auto_reload:
            self.reload_server_model()

        self._check_server_connection()

    def reload_server_model(
        self,
        model_name: Optional[str] = None,
        context_length: Optional[int] = None,
        gpu_layers: Optional[int] = None,
        threads: Optional[int] = None,
    ) -> bool:
        """Recarga el modelo en el servidor de LM Studio aplicando los parámetros configurados."""
        target_model = model_name or self.model
        target_ctx = context_length or self.n_ctx
        target_gpu = gpu_layers if gpu_layers is not None else self.n_gpu_layers
        target_threads = threads if threads is not None else self.n_threads

        lms_path = shutil.which("lms")
        if not lms_path:
            default_path = os.path.expanduser(r"~/.lmstudio/bin/lms.exe")
            if os.path.exists(default_path):
                lms_path = default_path

        if not lms_path:
            return False

        gpu_arg = "max" if (target_gpu == -1 or target_gpu > 0) else "off"

        try:
            subprocess.run([lms_path, "unload", target_model], capture_output=True, encoding="utf-8", errors="ignore")
            subprocess.run([lms_path, "unload", f"{target_model}:2"], capture_output=True, encoding="utf-8", errors="ignore")

            load_cmd = [lms_path, "load", target_model, "-c", str(target_ctx), "--gpu", gpu_arg, "-y"]
            if target_threads:
                load_cmd += ["--parallel", str(target_threads)]

            res = subprocess.run(load_cmd, capture_output=True, encoding="utf-8", errors="ignore")
            return res.returncode == 0
        except Exception:
            return False

    def _check_server_connection(self) -> None:
        """Verifica preliminarmente la conectividad con el servidor de LM Studio."""
        try:
            v0_url = f"{self.base_url.replace('/v1', '')}/api/v0/models"
            req = urllib.request.Request(
                v0_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    return
        except Exception:
            pass

        models_url = f"{self.base_url}/models"
        try:
            req = urllib.request.Request(
                models_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    available_models = [m.get("id") for m in data.get("data", []) if "id" in m]
                    if self.model and available_models and self.model not in available_models:
                        matching = [m for m in available_models if self.model in m or m in self.model]
                        if matching:
                            self.model = matching[0]
                        else:
                            self.model = available_models[0]
        except Exception:
            pass

    def _clean_json_markdown(self, raw_text: str) -> str:
        """Remueve bloques delimitadores de código markdown si existen."""
        text = raw_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def generate(
        self,
        prompt: str,
        profile_name: str = "narrator",
        response_schema: Optional[dict] = None,
        schema_name: Optional[str] = None,
    ) -> dict:
        """Envía el prompt a LM Studio y retorna la respuesta en formato diccionario."""
        profile = self.inference_profiles.get(profile_name)
        if not profile:
            for key in self.inference_profiles:
                if key in profile_name or profile_name in key:
                    profile = self.inference_profiles[key]
                    break
        if not profile:
            profile = {}

        temperature = profile.get("temperature", self.config.get("temperature", 0.7))
        max_tokens = profile.get("max_tokens", self.config.get("max_tokens", 1536))

        messages = [
            {
                "role": "system",
                "content": "Eres un motor de juego de rol estructurado. Tu salida debe ser estrictamente el objeto JSON solicitado, sin explicaciones, rodeos ni comentarios adicionales.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if self.model:
            payload["model"] = self.model

        if response_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name or "structured_output",
                    "strict": True,
                    "schema": response_schema,
                },
            }

        chat_url = f"{self.base_url}/chat/completions"
        json_data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        content_text = ""
        try:
            req = urllib.request.Request(chat_url, data=json_data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                response_json = json.loads(resp.read().decode("utf-8"))

            choices = response_json.get("choices", [])
            if not choices:
                raise ValueError(f"El servidor LM Studio no devolvió ninguna opción de respuesta: {response_json}")

            choice = choices[0]
            finish_reason = choice.get("finish_reason")
            content_text = choice.get("message", {}).get("content", "")

            if not content_text:
                reasoning = choice.get("message", {}).get("reasoning_content", "")
                if reasoning and "{" in reasoning and "}" in reasoning:
                    match = re.search(r"\{.*\}", reasoning, re.DOTALL)
                    if match:
                        try:
                            candidate = json.loads(self._clean_json_markdown(match.group(0)))
                            return candidate
                        except Exception:
                            pass

                if finish_reason == "length":
                    raise ValueError(
                        f"El modelo LM Studio agotó los tokens máximos (finish_reason='length') antes de generar la respuesta final. "
                        f"Aumenta 'max_tokens' para el perfil '{profile_name}' en llm_config.json."
                    )
                raise ValueError("El modelo LM Studio retornó una respuesta de texto vacía.")

            cleaned_text = self._clean_json_markdown(content_text)
            return json.loads(cleaned_text)

        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Error HTTP {he.code} del servidor LM Studio en '{chat_url}': {err_body}")
        except urllib.error.URLError as ue:
            raise RuntimeError(
                f"No se pudo conectar con el servidor de LM Studio en '{self.base_url}': {ue.reason}.\n"
                f"Asegúrate de que LM Studio esté en ejecución y con el servidor local activo."
            )
        except json.JSONDecodeError as jde:
            raise ValueError(f"El modelo LM Studio generó un texto que no es un JSON válido:\n{content_text}\nDetalle: {jde}")
        except Exception as e:
            raise RuntimeError(f"Ocurrió un error inesperado durante la inferencia con LM Studio: {e}")
