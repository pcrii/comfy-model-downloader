# ComfyUI Model Downloader TUI

A lightweight, interactive Terminal UI (TUI) and CLI tool for downloading Hugging Face models and setting up custom nodes in **ComfyUI** before launching.

Built for **RunPod**, local Linux, and GPU cloud environments with high-speed multi-threaded downloads via `aria2c`.

---

## ✨ Features

- 🎯 **One-Click Presets:**
  - **FLUX.2 Klein 9B:**
    - Text Encoder: [Ponpoke Uncensored Q8_0 GGUF](https://huggingface.co/ponpoke/flux2-klein-9b-uncensored-text-encoder) -> `models/text_encoders/` & symlinked to `models/clip/`
    - Diffusion Model: [Black Forest Labs FLUX.2 Klein 9B FP8](https://huggingface.co/black-forest-labs/FLUX.2-klein-9b-fp8) -> `models/diffusion_models/`
    - VAE: [BFL VAE](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B) -> saved and renamed to `flux2_vae.safetensors` in `models/vae/`
- 🧩 **Automatic Custom Node Verification:**
  - Automatically checks and clones [`ComfyUI-GGUF`](https://github.com/city96/ComfyUI-GGUF) and installs `gguf` python package.
- ⚡ **Blazing Fast Downloads:**
  - Uses `aria2c` with 16 connections per file and automatic resume.
  - Automatically falls back to `curl` if `aria2c` is not installed.
- 🔑 **Hugging Face Authentication:**
  - Supports gated repos (e.g., Black Forest Labs) via `HF_TOKEN` environment variable or interactive prompt.
- 📂 **Custom Download Wizard:**
  - Paste any Hugging Face URL and choose from standard ComfyUI folders (`checkpoints`, `diffusion_models`, `text_encoders`, `vae`, `loras`, etc.).

---

## 🚀 Usage

### 1. Interactive TUI Mode
Simply run:

```bash
./comfy-dl
# or
python3 downloader.py
```

### 2. Headless / Automated Preset Mode
Great for startup scripts or RunPod pod launches:

```bash
# Download the FLUX.2 Klein 9B preset and immediately launch ComfyUI
python3 downloader.py --preset flux2-klein-9b --launch
```

---

## 📦 Push to GitHub as a Standalone Repo

To make this its own repository on your GitHub:

```bash
cd /home/phaulty/Work/comfy-model-downloader
git init
git add .
git commit -m "Initial commit of comfy-model-downloader"
# Create a repo on GitHub, then link and push:
# git remote add origin git@github.com:<your-username>/comfy-model-downloader.git
# git push -u origin main
```
