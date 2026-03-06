from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .config import GenerationRequest, OPEN_SOURCE_MODELS


@dataclass
class ResolvedModelSelection:
    mode: str
    model_id: str
    vae_model_id: str | None


def resolve_model_selection(req: GenerationRequest) -> ResolvedModelSelection:
    mode = "image2video" if req.image_path is not None else "text2video"
    model_key = "image_to_video" if mode == "image2video" else "text_to_video"

    model_entry = OPEN_SOURCE_MODELS.get(model_key)
    if not model_entry or not model_entry.get("model_id"):
        raise ValueError(
            f"No model configured for mode '{mode}'. Expected OPEN_SOURCE_MODELS['{model_key}']['model_id']."
        )

    model_id = str(model_entry["model_id"])

    if req.vae_model_id:
        vae_entry = OPEN_SOURCE_MODELS.get("vae")
        configured_vae = vae_entry.get("model_id") if isinstance(vae_entry, dict) else None
        if configured_vae and req.vae_model_id != configured_vae:
            raise ValueError(
                f"Unsupported VAE model '{req.vae_model_id}'. Supported VAE: '{configured_vae}'."
            )
        if mode == "text2video":
            raise ValueError(
                "VAE override is currently only supported for image2video mode. "
                "Remove --vae for text2video or switch to image2video."
            )

    return ResolvedModelSelection(mode=mode, model_id=model_id, vae_model_id=req.vae_model_id)


def validated_model_catalog() -> dict:
    text_req = GenerationRequest(prompt="catalog")
    image_req = GenerationRequest(prompt="catalog", image_path=Path("placeholder.png"))

    text_selection = asdict(resolve_model_selection(text_req))
    image_selection = asdict(resolve_model_selection(image_req))

    return {
        "catalog": OPEN_SOURCE_MODELS,
        "validated": {
            "text2video": text_selection,
            "image2video": image_selection,
            "constraints": {
                "vae_override_supported_modes": ["image2video"],
            },
        },
    }
