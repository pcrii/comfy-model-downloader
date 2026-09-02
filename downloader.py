#!/usr/bin/env python3
"""
ComfyUI Model Downloader & Manager (TUI & CLI)
Supports:
- Interactive TUI menu (when run with no args)
- Direct CLI flags for any folder: --unet, --clip, --vae, --lora, --checkpoint, etc.
- In-line renaming: --vae "https://.../model.safetensors:new_name.safetensors"
- Chaining multiple downloads: --lora <url1> --lora <url2>
- Custom node installation: --custom-node <git_url>
- Presets:
    * klein-9b (Distilled FLUX.2 Klein 9B + Ponpoke Q8 GGUF + VAE)
    * klein-9b-base (Undistilled FLUX.2 Klein 9B Base + Ponpoke Q8 GGUF + VAE)
- Output export: --zip-output (with Taildrop support)
- Auto-launch: --launch
"""

import os
import sys
import shutil
import subprocess
import urllib.request
import datetime
import argparse
from pathlib import Path

# ANSI Color codes
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
DIM = "\033[2m"
RESET = "\033[0m"

# Default paths
WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", "/workspace"))
COMFY_DIR = Path(os.environ.get("COMFY_DIR", WORKSPACE_DIR / "ComfyUI"))
MODELS_DIR = COMFY_DIR / "models"
CUSTOM_NODES_DIR = COMFY_DIR / "custom_nodes"
VENV_DIR = Path(os.environ.get("VENV_DIR", WORKSPACE_DIR / "venv"))

# Shared URLs
PONPOKE_TEXT_ENCODER_URL = "https://huggingface.co/ponpoke/flux2-klein-9b-uncensored-text-encoder/resolve/main/flux2-klein-9b-uncensored-q8_0.gguf"
BFL_VAE_URL = "https://huggingface.co/black-forest-labs/FLUX.2-klein-9B/resolve/main/vae/diffusion_pytorch_model.safetensors"

# Available model categories and their relative paths inside ComfyUI/models
CATEGORY_PATHS = {
    "1": ("checkpoints", "models/checkpoints"),
    "2": ("diffusion_models", "models/diffusion_models"),
    "3": ("text_encoders", "models/text_encoders"),
    "4": ("clip", "models/clip"),
    "5": ("vae", "models/vae"),
    "6": ("loras", "models/loras"),
    "7": ("controlnet", "models/controlnet"),
    "8": ("unet", "models/unet"),
    "9": ("upscale_models", "models/upscale_models"),
}

# Default recommended custom nodes
DEFAULT_NODES = [
    {
        "name": "ComfyUI-Manager",
        "repo": "https://github.com/Comfy-Org/ComfyUI-Manager.git",
    },
    {
        "name": "ComfyUI-KJNodes",
        "repo": "https://github.com/kijai/ComfyUI-KJNodes.git",
    },
    {
        "name": "Civicomfy",
        "repo": "https://github.com/MoonGoblinDev/Civicomfy.git",
    },
    {
        "name": "ComfyUI-RunpodDirect",
        "repo": "https://github.com/MadiatorLabs/ComfyUI-RunpodDirect.git",
    },
    {
        "name": "ComfyUI-GGUF",
        "repo": "https://github.com/city96/ComfyUI-GGUF.git",
        "pip_packages": ["gguf"],
    },
]

# Presets configuration
PRESETS = {
    "klein-9b": {
        "id": "klein-9b",
        "name": "FLUX.2 Klein 9B",
        "description": "FLUX.2 Klein 9B (Distilled) with Ponpoke Q8_0 GGUF text encoder, FP8 UNet, and renamed VAE",
        "custom_nodes": [
            {
                "name": "ComfyUI-GGUF",
                "repo": "https://github.com/city96/ComfyUI-GGUF.git",
                "pip_packages": ["gguf"],
            }
        ],
        "files": [
            {
                "category": "text_encoders",
                "name": "Text Encoder (Q8_0 GGUF)",
                "url": PONPOKE_TEXT_ENCODER_URL,
                "filename": "flux2-klein-9b-uncensored-q8_0.gguf",
                "symlink_to": "clip",
            },
            {
                "category": "diffusion_models",
                "name": "Diffusion Model (Distilled FP8 UNet)",
                "url": "https://huggingface.co/black-forest-labs/FLUX.2-klein-9b-fp8/resolve/main/flux-2-klein-9b-fp8.safetensors",
                "filename": "flux-2-klein-9b-fp8.safetensors",
            },
            {
                "category": "vae",
                "name": "VAE (flux2_vae.safetensors)",
                "url": BFL_VAE_URL,
                "filename": "flux2_vae.safetensors",
            },
        ],
    },
    "klein-9b-base": {
        "id": "klein-9b-base",
        "name": "FLUX.2 Klein 9B Base",
        "description": "FLUX.2 Klein 9B Base (Undistilled) with Ponpoke Q8_0 GGUF text encoder, FP8 UNet, and renamed VAE",
        "custom_nodes": [
            {
                "name": "ComfyUI-GGUF",
                "repo": "https://github.com/city96/ComfyUI-GGUF.git",
                "pip_packages": ["gguf"],
            }
        ],
        "files": [
            {
                "category": "text_encoders",
                "name": "Text Encoder (Q8_0 GGUF)",
                "url": PONPOKE_TEXT_ENCODER_URL,
                "filename": "flux2-klein-9b-uncensored-q8_0.gguf",
                "symlink_to": "clip",
            },
            {
                "category": "diffusion_models",
                "name": "Diffusion Model (Base Undistilled FP8 UNet)",
                "url": "https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9b-fp8/resolve/main/flux-2-klein-base-9b-fp8.safetensors",
                "filename": "flux-2-klein-base-9b-fp8.safetensors",
            },
            {
                "category": "vae",
                "name": "VAE (flux2_vae.safetensors)",
                "url": BFL_VAE_URL,
                "filename": "flux2_vae.safetensors",
            },
        ],
    },
    "qwen-image": {
        "id": "qwen-image",
        "name": "Qwen-Image 2512 (Text-to-Image)",
        "description": "Qwen-Image-2512 Q4_K_M GGUF DiT with Qwen2.5-VL 7B text encoder, mmproj, and VAE",
        "custom_nodes": [
            {
                "name": "ComfyUI-GGUF",
                "repo": "https://github.com/city96/ComfyUI-GGUF.git",
                "pip_packages": ["gguf"],
            }
        ],
        "files": [
            {
                "category": "diffusion_models",
                "name": "DiT (Qwen-Image-2512 Q4_K_M GGUF)",
                "url": "https://huggingface.co/unsloth/Qwen-Image-2512-GGUF/resolve/main/qwen-image-2512-Q4_K_M.gguf",
                "filename": "qwen-image-2512-Q4_K_M.gguf",
                "symlink_to": "unet",
            },
            {
                "category": "text_encoders",
                "name": "Text Encoder (Qwen2.5-VL-7B-Instruct Q4_K_XL GGUF)",
                "url": "https://huggingface.co/unsloth/Qwen2.5-VL-7B-Instruct-GGUF/resolve/main/Qwen2.5-VL-7B-Instruct-UD-Q4_K_XL.gguf",
                "filename": "Qwen2.5-VL-7B-Instruct-UD-Q4_K_XL.gguf",
                "symlink_to": "clip",
            },
            {
                "category": "text_encoders",
                "name": "Vision Tower (Qwen2.5-VL-7B mmproj BF16 GGUF)",
                "url": "https://huggingface.co/unsloth/Qwen2.5-VL-7B-Instruct-GGUF/resolve/main/mmproj-BF16.gguf",
                "filename": "Qwen2.5-VL-7B-Instruct-mmproj-BF16.gguf",
                "symlink_to": "clip",
            },
            {
                "category": "vae",
                "name": "VAE (qwen_image_vae.safetensors)",
                "url": "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors",
                "filename": "qwen_image_vae.safetensors",
            },
        ],
    },
    "qwen-image-edit": {
        "id": "qwen-image-edit",
        "name": "Qwen-Image Edit 2511 (Image-to-Image / Inpainting)",
        "description": "Qwen-Image-Edit-2511 Q4_K_M GGUF DiT with Qwen2.5-VL 7B text encoder, mmproj, and VAE",
        "custom_nodes": [
            {
                "name": "ComfyUI-GGUF",
                "repo": "https://github.com/city96/ComfyUI-GGUF.git",
                "pip_packages": ["gguf"],
            }
        ],
        "files": [
            {
                "category": "diffusion_models",
                "name": "DiT (Qwen-Image-Edit-2511 Q4_K_M GGUF)",
                "url": "https://huggingface.co/unsloth/Qwen-Image-Edit-2511-GGUF/resolve/main/qwen-image-edit-2511-Q4_K_M.gguf",
                "filename": "qwen-image-edit-2511-Q4_K_M.gguf",
                "symlink_to": "unet",
            },
            {
                "category": "text_encoders",
                "name": "Text Encoder (Qwen2.5-VL-7B-Instruct Q4_K_XL GGUF)",
                "url": "https://huggingface.co/unsloth/Qwen2.5-VL-7B-Instruct-GGUF/resolve/main/Qwen2.5-VL-7B-Instruct-UD-Q4_K_XL.gguf",
                "filename": "Qwen2.5-VL-7B-Instruct-UD-Q4_K_XL.gguf",
                "symlink_to": "clip",
            },
            {
                "category": "text_encoders",
                "name": "Vision Tower (Qwen2.5-VL-7B mmproj BF16 GGUF)",
                "url": "https://huggingface.co/unsloth/Qwen2.5-VL-7B-Instruct-GGUF/resolve/main/mmproj-BF16.gguf",
                "filename": "Qwen2.5-VL-7B-Instruct-mmproj-BF16.gguf",
                "symlink_to": "clip",
            },
            {
                "category": "vae",
                "name": "VAE (qwen_image_vae.safetensors)",
                "url": "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors",
                "filename": "qwen_image_vae.safetensors",
            },
        ],
    },
    "qwen-image-all": {
        "id": "qwen-image-all",
        "name": "Qwen-Image Complete Bundle (2512 + Edit 2511)",
        "description": "Downloads both Qwen-Image-2512 and Qwen-Image-Edit-2511 DiTs with shared Qwen2.5-VL text encoder, mmproj, and VAE",
        "custom_nodes": [
            {
                "name": "ComfyUI-GGUF",
                "repo": "https://github.com/city96/ComfyUI-GGUF.git",
                "pip_packages": ["gguf"],
            }
        ],
        "files": [
            {
                "category": "diffusion_models",
                "name": "DiT (Qwen-Image-2512 Q4_K_M GGUF)",
                "url": "https://huggingface.co/unsloth/Qwen-Image-2512-GGUF/resolve/main/qwen-image-2512-Q4_K_M.gguf",
                "filename": "qwen-image-2512-Q4_K_M.gguf",
                "symlink_to": "unet",
            },
            {
                "category": "diffusion_models",
                "name": "DiT (Qwen-Image-Edit-2511 Q4_K_M GGUF)",
                "url": "https://huggingface.co/unsloth/Qwen-Image-Edit-2511-GGUF/resolve/main/qwen-image-edit-2511-Q4_K_M.gguf",
                "filename": "qwen-image-edit-2511-Q4_K_M.gguf",
                "symlink_to": "unet",
            },
            {
                "category": "text_encoders",
                "name": "Text Encoder (Qwen2.5-VL-7B-Instruct Q4_K_XL GGUF)",
                "url": "https://huggingface.co/unsloth/Qwen2.5-VL-7B-Instruct-GGUF/resolve/main/Qwen2.5-VL-7B-Instruct-UD-Q4_K_XL.gguf",
                "filename": "Qwen2.5-VL-7B-Instruct-UD-Q4_K_XL.gguf",
                "symlink_to": "clip",
            },
            {
                "category": "text_encoders",
                "name": "Vision Tower (Qwen2.5-VL-7B mmproj BF16 GGUF)",
                "url": "https://huggingface.co/unsloth/Qwen2.5-VL-7B-Instruct-GGUF/resolve/main/mmproj-BF16.gguf",
                "filename": "Qwen2.5-VL-7B-Instruct-mmproj-BF16.gguf",
                "symlink_to": "clip",
            },
            {
                "category": "vae",
                "name": "VAE (qwen_image_vae.safetensors)",
                "url": "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors",
                "filename": "qwen_image_vae.safetensors",
            },
        ],
    },
    "z-image": {
        "id": "z-image",
        "name": "Z-Image 6B (Base)",
        "description": "Z-Image 6B S3-DiT with Qwen 3 4B FP8 Mixed text encoder and AE VAE from Comfy-Org",
        "files": [
            {
                "category": "diffusion_models",
                "name": "DiT (z_image_int8_convrot.safetensors - 8-Bit Quantized)",
                "url": "https://huggingface.co/Comfy-Org/z_image/resolve/main/split_files/diffusion_models/z_image_int8_convrot.safetensors",
                "filename": "z_image_int8_convrot.safetensors",
            },
            {
                "category": "text_encoders",
                "name": "Text Encoder (qwen_3_4b_fp8_mixed.safetensors)",
                "url": "https://huggingface.co/Comfy-Org/z_image/resolve/main/split_files/text_encoders/qwen_3_4b_fp8_mixed.safetensors",
                "filename": "qwen_3_4b_fp8_mixed.safetensors",
                "symlink_to": "clip",
            },
            {
                "category": "vae",
                "name": "VAE (ae.safetensors)",
                "url": "https://huggingface.co/Comfy-Org/z_image/resolve/main/split_files/vae/ae.safetensors",
                "filename": "ae.safetensors",
            },
        ],
    },
    "z-image-turbo": {
        "id": "z-image-turbo",
        "name": "Z-Image 6B Turbo (8-Step Fast Inference)",
        "description": "Z-Image 6B Turbo S3-DiT with Qwen 3 4B FP8 Mixed text encoder and AE VAE from Comfy-Org",
        "files": [
            {
                "category": "diffusion_models",
                "name": "DiT (z_image_turbo_int8_convrot.safetensors - 8-Bit Quantized Turbo)",
                "url": "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_int8_convrot.safetensors",
                "filename": "z_image_turbo_int8_convrot.safetensors",
            },
            {
                "category": "text_encoders",
                "name": "Text Encoder (qwen_3_4b_fp8_mixed.safetensors)",
                "url": "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/text_encoders/qwen_3_4b_fp8_mixed.safetensors",
                "filename": "qwen_3_4b_fp8_mixed.safetensors",
                "symlink_to": "clip",
            },
            {
                "category": "vae",
                "name": "VAE (ae.safetensors)",
                "url": "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/vae/ae.safetensors",
                "filename": "ae.safetensors",
            },
        ],
    },
    "trellis-2": {
        "id": "trellis-2",
        "name": "TRELLIS 2 (Image-to-3D Asset Generator)",
        "description": "Microsoft TRELLIS.2 4B image-to-3D model with int8_convrot DiT, DINOv3 vision tower, and dual shape/texture VAEs for Blender/GLB export",

        "files": [
            {
                "category": "diffusion_models",
                "name": "DiT (trellis_2_int8_convrot.safetensors - 5.2GB 8-Bit)",
                "url": "https://huggingface.co/Comfy-Org/TRELLIS.2/resolve/main/diffusion_models/trellis_2_int8_convrot.safetensors",
                "filename": "trellis_2_int8_convrot.safetensors",
            },
            {
                "category": "clip_vision",
                "name": "Vision Tower (dino_v3_vit_l.safetensors - 1.2GB)",
                "url": "https://huggingface.co/Comfy-Org/TRELLIS.2/resolve/main/clip_vision/dino_v3_vit_l.safetensors",
                "filename": "dino_v3_vit_l.safetensors",
            },
            {
                "category": "vae",
                "name": "Shape VAE (trellis_2_shape_vae_bf16.safetensors - 1.1GB)",
                "url": "https://huggingface.co/Comfy-Org/TRELLIS.2/resolve/main/vae/trellis_2_shape_vae_bf16.safetensors",
                "filename": "trellis_2_shape_vae_bf16.safetensors",
            },
            {
                "category": "vae",
                "name": "Texture VAE (trellis_2_texture_vae_bf16.safetensors - 0.95GB)",
                "url": "https://huggingface.co/Comfy-Org/TRELLIS.2/resolve/main/vae/trellis_2_texture_vae_bf16.safetensors",
                "filename": "trellis_2_texture_vae_bf16.safetensors",
            },
        ],
    },
}

# Aliases for backward compatibility
PRESETS["flux2-klein-9b"] = PRESETS["klein-9b"]
PRESETS["flux2-klein-9b-uncensored"] = PRESETS["klein-9b"]
PRESETS["flux2-klein-base-9b"] = PRESETS["klein-9b-base"]
PRESETS["flux2-klein-9b-base"] = PRESETS["klein-9b-base"]
PRESETS["trellis2"] = PRESETS["trellis-2"]




def patch_comfy_kitchen():
    """Patches comfy_kitchen eager/na.py and sage_attention.py for PyTorch compatibility."""
    import glob
    search_dirs = [
        "/usr/local/lib/python*/dist-packages",
        str(WORKSPACE_DIR / "venv/lib/python*/site-packages"),
        "/workspace/venv/lib/python*/site-packages",
    ]
    for sdir in search_dirs:
        for p in glob.glob(f"{sdir}/comfy_kitchen/backends/eager/na.py"):
            try:
                with open(p, "r") as f:
                    content = f.read()
                if "kernel_size: list[int]" in content:
                    content = "import typing\n" + content.replace(
                        "kernel_size: list[int]", "kernel_size: typing.List[int]"
                    ).replace("is_causal: list[bool]", "is_causal: typing.List[bool]")
                    with open(p, "w") as f:
                        f.write(content)
                    print(f"  {GREEN}✔ Patched comfy_kitchen na.py at {p}{RESET}")
            except Exception:
                pass
        for p in glob.glob(f"{sdir}/comfy_kitchen/sage_attention.py"):
            try:
                with open(p, "r") as f:
                    content = f.read()
                if "scale: float | None" in content:
                    if content.startswith("import typing\n"):
                        content = content[len("import typing\n"):]
                    content = content.replace("from __future__ import annotations", "# from __future__ import annotations\nimport typing")
                    content = content.replace("scale: float | None", "scale: typing.Optional[float]")
                    with open(p, "w") as f:
                        f.write(content)
                    print(f"  {GREEN}✔ Patched comfy_kitchen sage_attention.py at {p}{RESET}")
            except Exception:
                pass

def clear_screen():
    print("\033[H\033[J", end="")


def print_banner():
    print(f"{CYAN}{BOLD}")
    print("  ╔══════════════════════════════════════════════════════════════╗")
    print("  ║             ComfyUI Model Downloader & TUI                   ║")
    print("  ║         Fast Multi-Threaded Downloads (HF / aria2)           ║")
    print("  ╚══════════════════════════════════════════════════════════════╝")
    print(f"{RESET}")
    print(f"  {DIM}Workspace:{RESET} {WORKSPACE_DIR}")
    print(f"  {DIM}ComfyUI:{RESET}   {COMFY_DIR}\n")


def get_python_exec():
    """Returns the python executable to use (workspace venv if exists, else sys.executable)."""
    venv_py = VENV_DIR / "bin" / "python"
    if venv_py.exists():
        return str(venv_py)
    return sys.executable


def get_hf_token():
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    return token.strip() if token else None


def parse_target(arg_value: str):
    """Parses 'url' or 'url:custom_filename' or 'url::custom_filename'."""
    arg_value = arg_value.strip()
    if "::" in arg_value:
        url, custom_name = arg_value.split("::", 1)
        return clean_url(url.strip()), custom_name.strip()

    last_slash = arg_value.rfind("/")
    if last_slash != -1:
        after_slash = arg_value[last_slash + 1 :]
        if ":" in after_slash:
            sub = after_slash.split(":", 1)
            base_url = arg_value[: last_slash + 1] + sub[0]
            return clean_url(base_url.strip()), sub[1].strip()

    return clean_url(arg_value), None


def clean_url(url: str) -> str:
    """Converts Hugging Face blob links to direct resolve/main links."""
    if "huggingface.co" in url and "/blob/" in url:
        return url.replace("/blob/", "/resolve/")
    return url


def download_file(url: str, dest_path: Path, hf_token: str = None):
    """Downloads a file using aria2c if available, falling back to curl."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if dest_path.exists() and dest_path.stat().st_size > 0:
        print(f"  {GREEN}✔ [Already Exists]{RESET} {dest_path.name} ({dest_path.stat().st_size / (1024*1024):.1f} MB)")
        return True

    print(f"\n  {YELLOW}⬇ Downloading:{RESET} {dest_path.name}")
    print(f"    {DIM}URL:{RESET} {url}")
    print(f"    {DIM}Target:{RESET} {dest_path}")

    # Prefer aria2c for multi-connection fast downloads
    if shutil.which("aria2c"):
        cmd = [
            "aria2c",
            "-c",
            "-x", "16",
            "-s", "16",
            "-k", "1M",
            "--file-allocation=none",
            "--summary-interval=5",
            "-d", str(dest_path.parent),
            "-o", dest_path.name,
            url,
        ]
        if hf_token:
            cmd.insert(1, f"--header=Authorization: Bearer {hf_token}")

        res = subprocess.run(cmd)
        if res.returncode == 0:
            print(f"  {GREEN}✔ Completed:{RESET} {dest_path.name}")
            return True
        else:
            print(f"  {RED}✖ aria2c failed with code {res.returncode}. Falling back to curl...{RESET}")

    # Fallback to curl
    cmd = ["curl", "-L", "-C", "-", "-o", str(dest_path), url]
    if hf_token:
        cmd.extend(["-H", f"Authorization: Bearer {hf_token}"])
    cmd.append("--progress-bar")

    res = subprocess.run(cmd)
    if res.returncode == 0:
        print(f"  {GREEN}✔ Completed:{RESET} {dest_path.name}")
        return True
    else:
        print(f"  {RED}✖ Download failed for {dest_path.name}{RESET}")
        return False


def verify_custom_node(node_info: dict):
    """Verifies that a custom node repo is cloned and its dependencies installed."""
    name = node_info["name"]
    repo = node_info["repo"]
    pip_packages = node_info.get("pip_packages", [])

    CUSTOM_NODES_DIR.mkdir(parents=True, exist_ok=True)
    target_dir = CUSTOM_NODES_DIR / name

    print(f"\n  {CYAN}▸ Checking Custom Node:{RESET} {BOLD}{name}{RESET}")
    if not (target_dir / ".git").exists():
        print(f"    {YELLOW}Cloning {name} from {repo}...{RESET}")
        subprocess.run(["git", "clone", repo, str(target_dir)], check=True)
    else:
        print(f"    {GREEN}✔ {name} already installed in {target_dir}{RESET}")
        subprocess.run(["git", "-C", str(target_dir), "pull", "--ff-only"], check=False)

    py_exec = get_python_exec()
    for pkg in pip_packages:
        print(f"    Verifying python package: {pkg}...")
        subprocess.run([py_exec, "-m", "pip", "install", "--no-cache-dir", pkg], check=False)

    req_file = target_dir / "requirements.txt"
    if req_file.exists():
        subprocess.run([py_exec, "-m", "pip", "install", "--no-cache-dir", "-r", str(req_file)], check=False)


def install_all_default_nodes():
    print(f"\n{BOLD}{CYAN}=== Installing / Updating Recommended Custom Nodes ==={RESET}")
    for node in DEFAULT_NODES:
        verify_custom_node(node)
    print(f"\n{GREEN}{BOLD}✔ All recommended custom nodes are verified and updated!{RESET}\n")


def run_preset(preset_key: str):
    preset = PRESETS.get(preset_key)
    if not preset:
        print(f"{RED}Unknown preset: {preset_key}{RESET}")
        return

    print(f"\n{BOLD}{CYAN}=== Executing Preset: {preset['name']} ==={RESET}\n")

    hf_token = get_hf_token()
    if not hf_token and not sys.stdin.isatty():
        pass
    elif not hf_token:
        print(f"  {YELLOW}Notice:{RESET} Some Hugging Face models (like Black Forest Labs) may require a token.")
        user_input = input(f"  Enter your Hugging Face Token {DIM}(press Enter to skip){RESET}: ").strip()
        if user_input:
            hf_token = user_input
            os.environ["HF_TOKEN"] = user_input

    for node in preset.get("custom_nodes", []):
        verify_custom_node(node)

    for item in preset.get("files", []):
        cat = item["category"]
        filename = item["filename"]
        url = item["url"]
        dest_dir = COMFY_DIR / "models" / cat
        dest_path = dest_dir / filename

        success = download_file(url, dest_path, hf_token)
        if success and item.get("symlink_to"):
            symlink_cat = item["symlink_to"]
            symlink_dir = COMFY_DIR / "models" / symlink_cat
            symlink_dir.mkdir(parents=True, exist_ok=True)
            symlink_path = symlink_dir / filename
            if not symlink_path.exists():
                try:
                    symlink_path.symlink_to(dest_path)
                    print(f"  {DIM}Linked {filename} -> models/{symlink_cat}/{RESET}")
                except Exception:
                    pass

    print(f"\n{GREEN}{BOLD}🎉 Preset '{preset['name']}' setup completed successfully!{RESET}\n")


def download_category_items(items: list, category: str, symlink_to: str = None):
    """Downloads a list of URL/URL:name strings to a specific model subfolder."""
    hf_token = get_hf_token()
    dest_dir = COMFY_DIR / "models" / category
    dest_dir.mkdir(parents=True, exist_ok=True)

    for item_str in items:
        url, custom_name = parse_target(item_str)
        default_name = url.split("?")[0].split("/")[-1]
        filename = custom_name if custom_name else default_name
        dest_path = dest_dir / filename

        success = download_file(url, dest_path, hf_token)
        if success and symlink_to:
            symlink_dir = COMFY_DIR / "models" / symlink_to
            symlink_dir.mkdir(parents=True, exist_ok=True)
            symlink_path = symlink_dir / filename
            if not symlink_path.exists():
                try:
                    symlink_path.symlink_to(dest_path)
                    print(f"  {DIM}Linked {filename} -> models/{symlink_to}/{RESET}")
                except Exception:
                    pass


def zip_outputs():
    """Zips the ComfyUI outputs folder and offers Taildrop / direct HTTP download."""
    output_dir = COMFY_DIR / "output"
    if not output_dir.exists() or not any(output_dir.iterdir()):
        print(f"\n  {RED}✖ No generated images found in {output_dir}{RESET}\n")
        return None

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"comfyui_output_{timestamp}"
    zip_dest = WORKSPACE_DIR / base_name

    print(f"\n  {YELLOW}📦 Compressing outputs from {output_dir}...{RESET}")
    archive_path = shutil.make_archive(str(zip_dest), "zip", str(output_dir))
    zip_file = Path(archive_path)

    size_mb = zip_file.stat().st_size / (1024 * 1024)
    print(f"  {GREEN}✔ Created archive:{RESET} {BOLD}{zip_file}{RESET} ({size_mb:.2f} MB)")

    # Check for Tailscale and Taildrop option
    if shutil.which("tailscale"):
        print(f"\n  {CYAN}▸ Tailscale detected! Send archive via Taildrop?{RESET}")
        target = input(f"    Enter target machine name (e.g. laptop, or press Enter to skip): ").strip()
        if target:
            res = subprocess.run(["tailscale", "file", "cp", str(zip_file), f"{target}:"])
            if res.returncode == 0:
                print(f"  {GREEN}✔ Sent via Taildrop to {target}! Check your target machine's downloads.{RESET}")
            else:
                print(f"  {RED}✖ Taildrop transfer failed. File remains safe at {zip_file}{RESET}")

    print(f"\n  {BOLD}Alternative Download Options:{RESET}")
    print(f"    1. RunPod Jupyter Lab: Find {zip_file.name} in file manager -> Right Click -> Download")
    print(f"    2. Quick HTTP Server: {CYAN}python3 -m http.server 8189 -d /workspace{RESET}\n")
    return zip_file


def custom_download_wizard():
    print(f"\n{BOLD}{CYAN}=== Custom Hugging Face / Direct Download ==={RESET}\n")

    url = input(f"  Enter Model URL (HuggingFace resolve/blob or direct link):\n  > ").strip()
    if not url:
        print(f"  {RED}Download cancelled.{RESET}")
        return

    url = clean_url(url)

    print(f"\n  Select ComfyUI Target Folder:")
    for key, (name, path) in CATEGORY_PATHS.items():
        print(f"    [{key}] {BOLD}{name:<18}{RESET} ({path})")

    choice = input(f"  Choose folder [1-9]: ").strip()
    if choice in CATEGORY_PATHS:
        folder_name, rel_path = CATEGORY_PATHS[choice]
        dest_dir = COMFY_DIR / rel_path
    else:
        print(f"  {RED}Invalid choice.{RESET}")
        return

    default_name = url.split("?")[0].split("/")[-1]
    name_input = input(f"\n  Filename [{default_name}] (press Enter to keep, or type new name): ").strip()
    filename = name_input if name_input else default_name

    hf_token = get_hf_token()
    if not hf_token and "huggingface.co" in url:
        tok = input(f"  HF Token (press Enter to skip): ").strip()
        if tok:
            hf_token = tok

    dest_path = dest_dir / filename
    download_file(url, dest_path, hf_token)


def launch_comfyui():
    """Starts ComfyUI."""
    main_py = COMFY_DIR / "main.py"
    if not main_py.exists():
        print(f"{RED}Error: ComfyUI not found at {main_py}{RESET}")
        return

    py_exec = get_python_exec()
    port = os.environ.get("PORT", "8188")
    extra_args = os.environ.get("COMFY_EXTRA_ARGS", "--preview-method auto").split()

    print(f"\n{GREEN}{BOLD}🚀 Launching ComfyUI on port {port}...{RESET}")
    cmd = [py_exec, str(main_py), "--listen", "0.0.0.0", "--port", str(port)] + extra_args
    os.chdir(COMFY_DIR)
    os.execv(py_exec, cmd)


def interactive_menu():
    while True:
        clear_screen()
        print_banner()

        print(f"  {BOLD}Select an Option:{RESET}")
        print(f"  [{CYAN}1{RESET}] Preset: {BOLD}FLUX.2 Klein 9B{RESET}")
        print(f"  [{CYAN}2{RESET}] Preset: {BOLD}FLUX.2 Klein 9B Base{RESET}")
        print(f"  [{CYAN}3{RESET}] Custom Model Download (Hugging Face URL + Folder Chooser)")
        print(f"  [{CYAN}4{RESET}] Install / Update Essential Custom Nodes (Manager, KJNodes, Civicomfy, RunpodDirect, GGUF)")
        print(f"  [{CYAN}5{RESET}] 📦 Zip & Export Outputs (/workspace/ComfyUI/output)")
        print(f"  [{CYAN}6{RESET}] Launch ComfyUI")
        print(f"  [{CYAN}q{RESET}] Exit")
        print()

        choice = input(f"  Choice [1-6/q]: ").strip().lower()

        if choice == "1":
            run_preset("klein-9b")
            input(f"\n  {DIM}Press Enter to continue...{RESET}")
        elif choice == "2":
            run_preset("klein-9b-base")
            input(f"\n  {DIM}Press Enter to continue...{RESET}")
        elif choice == "3":
            custom_download_wizard()
            input(f"\n  {DIM}Press Enter to continue...{RESET}")
        elif choice == "4":
            install_all_default_nodes()
            input(f"\n  {DIM}Press Enter to continue...{RESET}")
        elif choice == "5":
            zip_outputs()
            input(f"\n  {DIM}Press Enter to continue...{RESET}")
        elif choice == "6":
            launch_comfyui()
            break
        elif choice in ["q", "exit"]:
            print(f"\n  Exiting. Happy generating!\n")
            break


def main():
    parser = argparse.ArgumentParser(
        description="ComfyUI Model Downloader & Manager CLI",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  comfy-dl --preset klein-9b --launch
  comfy-dl --preset klein-9b-base --launch
  comfy-dl --zip-output
  comfy-dl --unet https://huggingface.co/.../model.safetensors
  comfy-dl --clip https://huggingface.co/.../encoder.gguf --vae https://.../model.safetensors:flux2_vae.safetensors
  comfy-dl --lora https://civitai.com/api/download/models/12345:my_lora.safetensors
        """
    )
    # Direct folder flags
    parser.add_argument("--unet", "--diffusion-model", dest="unet", action="append", help="Download to models/diffusion_models (supports url:custom_name)")
    parser.add_argument("--clip", "--text-encoder", dest="clip", action="append", help="Download to models/text_encoders & symlink to models/clip")
    parser.add_argument("--vae", dest="vae", action="append", help="Download to models/vae (supports url:custom_name)")
    parser.add_argument("--checkpoint", "--ckpt", dest="checkpoint", action="append", help="Download to models/checkpoints")
    parser.add_argument("--lora", dest="lora", action="append", help="Download to models/loras")
    parser.add_argument("--controlnet", dest="controlnet", action="append", help="Download to models/controlnet")
    parser.add_argument("--upscale", dest="upscale", action="append", help="Download to models/upscale_models")
    parser.add_argument("--custom-node", dest="custom_node", action="append", help="Clone a custom node Git repository into custom_nodes/")

    # Presets & automated actions
    parser.add_argument("--preset", choices=list(PRESETS.keys()), help="Directly run a preset bundle non-interactively")
    parser.add_argument("--install-nodes", action="store_true", help="Install/update default custom nodes")
    parser.add_argument("--zip-output", action="store_true", help="Compress /workspace/ComfyUI/output into a zip archive")
    parser.add_argument("--launch", action="store_true", help="Launch ComfyUI after finishing downloads")

    args = parser.parse_args()
    patch_comfy_kitchen()

    cli_action_taken = False

    if args.install_nodes:
        install_all_default_nodes()
        cli_action_taken = True

    if args.preset:
        run_preset(args.preset)
        cli_action_taken = True

    if args.zip_output:
        zip_outputs()
        cli_action_taken = True

    if args.unet:
        download_category_items(args.unet, "diffusion_models", symlink_to="unet")
        cli_action_taken = True
    if args.clip:
        download_category_items(args.clip, "text_encoders", symlink_to="clip")
        cli_action_taken = True
    if args.vae:
        download_category_items(args.vae, "vae")
        cli_action_taken = True
    if args.checkpoint:
        download_category_items(args.checkpoint, "checkpoints")
        cli_action_taken = True
    if args.lora:
        download_category_items(args.lora, "loras")
        cli_action_taken = True
    if args.controlnet:
        download_category_items(args.controlnet, "controlnet")
        cli_action_taken = True
    if args.upscale:
        download_category_items(args.upscale, "upscale_models")
        cli_action_taken = True
    if args.custom_node:
        for node_repo in args.custom_node:
            node_name = node_repo.split("/")[-1].replace(".git", "")
            verify_custom_node({"name": node_name, "repo": node_repo})
        cli_action_taken = True

    if args.launch:
        launch_comfyui()
    elif not cli_action_taken:
        interactive_menu()


if __name__ == "__main__":
    main()
