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
    * flux2-klein-9b-uncensored (Distilled + Uncensored Q8 GGUF)
    * flux2-klein-base-9b (Undistilled Base + Qwen3-8B Q8 GGUF)
- Auto-launch: --launch
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
    "flux2-klein-9b-uncensored": {
        "id": "flux2-klein-9b-uncensored",
        "name": "FLUX.2 Klein 9B (Distilled + Uncensored Q8 GGUF + FP8 UNet + VAE)",
        "description": "Fast 4-step distilled FLUX.2 Klein 9B with Ponpoke Uncensored Q8_0 GGUF text encoder",
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
                "name": "VAE (Renamed from diffusion_pytorch_model.safetensors)",
                "url": "https://huggingface.co/black-forest-labs/FLUX.2-klein-9B/resolve/main/vae/diffusion_pytorch_model.safetensors",
                "filename": "flux2_vae.safetensors",
            },
        ],
    },
    "flux2-klein-base-9b": {
        "id": "flux2-klein-base-9b",
        "name": "FLUX.2 Klein Base 9B (Undistilled + Qwen3-8B Q8 GGUF + FP8 UNet + VAE)",
        "description": "Full undistilled foundation FLUX.2 Klein Base 9B with official Qwen3-8B Q8_0 GGUF text encoder",
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
                "name": "Text Encoder (Qwen3-8B Q8_0 GGUF)",
                "url": "https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/main/Qwen3-8B-Q8_0.gguf",
                "filename": "Qwen3-8B-Q8_0.gguf",
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
                "name": "VAE (Renamed from diffusion_pytorch_model.safetensors)",
                "url": "https://huggingface.co/black-forest-labs/FLUX.2-klein-9B/resolve/main/vae/diffusion_pytorch_model.safetensors",
                "filename": "flux2_vae.safetensors",
            },
        ],
    },
}

# Alias for backward compatibility
PRESETS["flux2-klein-9b"] = PRESETS["flux2-klein-9b-uncensored"]


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
        print(f"  [{CYAN}1{RESET}] Preset: {BOLD}FLUX.2 Klein 9B (Distilled + Uncensored Q8 GGUF){RESET}")
        print(f"  [{CYAN}2{RESET}] Preset: {BOLD}FLUX.2 Klein Base 9B (Undistilled + Qwen3-8B Q8 GGUF){RESET}")
        print(f"  [{CYAN}3{RESET}] Custom Model Download (Hugging Face URL + Folder Chooser)")
        print(f"  [{CYAN}4{RESET}] Install / Update Essential Custom Nodes (Manager, KJNodes, Civicomfy, RunpodDirect, GGUF)")
        print(f"  [{CYAN}5{RESET}] Launch ComfyUI")
        print(f"  [{CYAN}q{RESET}] Exit")
        print()

        choice = input(f"  Choice [1-5/q]: ").strip().lower()

        if choice == "1":
            run_preset("flux2-klein-9b-uncensored")
            input(f"\n  {DIM}Press Enter to continue...{RESET}")
        elif choice == "2":
            run_preset("flux2-klein-base-9b")
            input(f"\n  {DIM}Press Enter to continue...{RESET}")
        elif choice == "3":
            custom_download_wizard()
            input(f"\n  {DIM}Press Enter to continue...{RESET}")
        elif choice == "4":
            install_all_default_nodes()
            input(f"\n  {DIM}Press Enter to continue...{RESET}")
        elif choice == "5":
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
  comfy-dl --preset flux2-klein-9b-uncensored --launch
  comfy-dl --preset flux2-klein-base-9b --launch
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
    parser.add_argument("--launch", action="store_true", help="Launch ComfyUI after finishing downloads")

    args = parser.parse_args()

    cli_action_taken = False

    if args.install_nodes:
        install_all_default_nodes()
        cli_action_taken = True

    if args.preset:
        run_preset(args.preset)
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
