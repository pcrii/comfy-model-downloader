#!/usr/bin/env python3
"""
ComfyUI Model Downloader & Manager TUI
Supports Hugging Face downloads, presets (Flux.2 Klein 9B, GGUF text encoders),
custom node verification (Manager, KJNodes, Civicomfy, RunpodDirect, GGUF),
and multi-threaded downloads with aria2c.
"""

import os
import sys
import shutil
import subprocess
import urllib.request
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
    "flux2-klein-9b": {
        "id": "flux2-klein-9b",
        "name": "FLUX.2 Klein 9B (Uncensored GGUF Text Encoder + FP8 UNet + VAE)",
        "description": "FLUX.2 Klein 9B with Ponpoke Q8_0 GGUF text encoder, FP8 UNet, and renamed VAE",
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
                "name": "Text Encoder (Q8_0 GGUF Uncensored)",
                "url": "https://huggingface.co/ponpoke/flux2-klein-9b-uncensored-text-encoder/resolve/main/flux2-klein-9b-uncensored-q8_0.gguf",
                "filename": "flux2-klein-9b-uncensored-q8_0.gguf",
                "symlink_to": "clip",  # Also creates symlink in models/clip for older custom nodes
            },
            {
                "category": "diffusion_models",
                "name": "Diffusion Model (FP8 UNet)",
                "url": "https://huggingface.co/black-forest-labs/FLUX.2-klein-9b-fp8/resolve/main/flux-2-klein-9b-fp8.safetensors",
                "filename": "flux-2-klein-9b-fp8.safetensors",
            },
            {
                "category": "vae",
                "name": "VAE (Renamed from diffusion_pytorch_model.safetensors)",
                "url": "https://huggingface.co/black-forest-labs/FLUX.2-klein-9B/resolve/main/vae/diffusion_pytorch_model.safetensors",
                "filename": "flux2_vae.safetensors",
            },
        ],
    }
}


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
            "-c",                     # resume support
            "-x", "16",               # max connections per server
            "-s", "16",               # split connections
            "-k", "1M",               # min split size
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

    # Install pip requirements if specified
    py_exec = get_python_exec()
    for pkg in pip_packages:
        print(f"    Verifying python package: {pkg}...")
        subprocess.run([py_exec, "-m", "pip", "install", "--no-cache-dir", pkg], check=False)

    # Check for requirements.txt in the custom node
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

    # Step 1: Check Hugging Face token (useful for gated BFL models)
    hf_token = get_hf_token()
    if not hf_token:
        print(f"  {YELLOW}Notice:{RESET} Some Hugging Face models (like Black Forest Labs) may require a token.")
        user_input = input(f"  Enter your Hugging Face Token {DIM}(press Enter to skip){RESET}: ").strip()
        if user_input:
            hf_token = user_input
            os.environ["HF_TOKEN"] = user_input

    # Step 2: Install / verify custom nodes
    for node in preset.get("custom_nodes", []):
        verify_custom_node(node)

    # Step 3: Download model files
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


def custom_download_wizard():
    print(f"\n{BOLD}{CYAN}=== Custom Hugging Face / Direct Download ==={RESET}\n")

    # Step 1: URL input
    url = input(f"  Enter Model URL (HuggingFace resolve/blob or direct link):\n  > ").strip()
    if not url:
        print(f"  {RED}Download cancelled.{RESET}")
        return

    # Convert HF blob URL to resolve/main
    if "huggingface.co" in url and "/blob/" in url:
        url = url.replace("/blob/", "/resolve/")
        print(f"  {DIM}Converted URL to direct resolve link:{RESET} {url}")

    # Step 2: Category selection
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

    # Step 3: Filename
    default_name = url.split("?")[0].split("/")[-1]
    name_input = input(f"\n  Filename [{default_name}] (press Enter to keep, or type new name): ").strip()
    filename = name_input if name_input else default_name

    # Step 4: Token
    hf_token = get_hf_token()
    if not hf_token and "huggingface.co" in url:
        tok = input(f"  HF Token (press Enter to skip): ").strip()
        if tok:
            hf_token = tok

    # Execute download
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
        print(f"  [{CYAN}1{RESET}] Download Preset: {BOLD}FLUX.2 Klein 9B{RESET} (Uncensored GGUF + FP8 + VAE)")
        print(f"  [{CYAN}2{RESET}] Custom Model Download (Hugging Face URL + Folder Chooser)")
        print(f"  [{CYAN}3{RESET}] Install / Update Essential Custom Nodes (Manager, KJNodes, Civicomfy, RunpodDirect, GGUF)")
        print(f"  [{CYAN}4{RESET}] Launch ComfyUI")
        print(f"  [{CYAN}q{RESET}] Exit")
        print()

        choice = input(f"  Choice [1-4/q]: ").strip().lower()

        if choice == "1":
            run_preset("flux2-klein-9b")
            input(f"\n  {DIM}Press Enter to continue...{RESET}")
        elif choice == "2":
            custom_download_wizard()
            input(f"\n  {DIM}Press Enter to continue...{RESET}")
        elif choice == "3":
            install_all_default_nodes()
            input(f"\n  {DIM}Press Enter to continue...{RESET}")
        elif choice == "4":
            launch_comfyui()
            break
        elif choice in ["q", "exit"]:
            print(f"\n  Exiting. Happy generating!\n")
            break


def main():
    parser = argparse.ArgumentParser(description="ComfyUI Model Downloader TUI")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), help="Directly run a preset non-interactively")
    parser.add_argument("--launch", action="store_true", help="Launch ComfyUI after finishing preset download")
    parser.add_argument("--install-nodes", action="store_true", help="Install/update default custom nodes")
    args = parser.parse_args()

    if args.install_nodes:
        install_all_default_nodes()

    if args.preset:
        run_preset(args.preset)
        if args.launch:
            launch_comfyui()
    elif not args.install_nodes:
        interactive_menu()


if __name__ == "__main__":
    main()
