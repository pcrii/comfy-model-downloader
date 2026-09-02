# comfy-dl

A lightweight, high-speed helper utility for RunPod and cloud GPU pods to fetch ComfyUI models, text encoders, VAEs, and workflows before launching the server.

Uses `aria2c` for fast multi-threaded downloads with automatic fallback to `curl`.

---

## 🚀 Model Presets

Run any preset with `comfy-dl --preset <name>`. Each preset automatically downloads the required models and installs the matching ready-to-use visual workflow into ComfyUI's user workflow library.

| Preset | Description | Models Included |
| :--- | :--- | :--- |
| **`klein-9b`** | FLUX.2 Klein 9B Distilled (4-step fast generation) | FP8 UNet + Ponpoke Q8_0 GGUF text encoder + renamed VAE + visual workflow |
| **`klein-9b-base`** | FLUX.2 Klein 9B Base (20-step high fidelity) | FP8 UNet + Ponpoke Q8_0 GGUF text encoder + renamed VAE + visual workflow |
| **`qwen-image`** | Qwen-Image 2512 Text-to-Image | Q4_K_M GGUF DiT + Qwen2.5-VL 7B text encoder + mmproj vision tower + VAE + official Unsloth workflow |
| **`qwen-image-edit`** | Qwen-Image Edit 2511 | Q4_K_M GGUF DiT + Qwen2.5-VL 7B text encoder + mmproj + VAE + official Unsloth editing workflow |
| **`qwen-image-all`** | Complete Qwen-Image Bundle | Both 2512 and Edit 2511 DiTs + shared text encoder + mmproj + VAE + both workflows |
| **`z-image`** | Z-Image 6B Base Foundation Model | 6.2 GB `int8_convrot` DiT + Qwen 3 4B FP8 Mixed text encoder + AE VAE |
| **`z-image-turbo`** | Z-Image 6B Turbo (8-step fast inference) | 6.2 GB `int8_convrot` DiT + Qwen 3 4B FP8 Mixed text encoder + AE VAE |
| **`trellis-2`** | Microsoft TRELLIS.2 Image-to-3D Generator | 5.2 GB `int8_convrot` DiT + DINOv3 vision tower + Shape VAE + Texture VAE + native 3D GLB/Blender workflow |

---

## ⚙️ RunPod Environment Variables

When deploying your pod, you can configure these environment variables in your RunPod template:

| Environment Variable | Example / Options | Description |
| :--- | :--- | :--- |
| **`MODEL_PRESET`** | `klein-9b`, `qwen-image`, `trellis-2`, `z-image-turbo` | Auto-downloads the complete model bundle on container boot. |
| **`TAILSCALE_AUTHKEY`** | `tskey-auth-...` | Connects pod to your Tailnet with `tailscale serve --bg 8188` enabled. Access at `http://comfy-runpod:8188`. |
| **`TAILSCALE_HOSTNAME`** | `comfy-runpod` | Tailscale hostname. Default: `comfy-runpod`. |
| **`HF_TOKEN`** | `hf_...` | Hugging Face access token for gated models. |
| **`COMFY_DL_ARGS`** | `--lora <url> --controlnet <url>` | Custom arguments passed directly to `comfy-dl` on boot. |
| **`COMFY_EXTRA_ARGS`** | `--preview-method auto --fast` | Custom arguments passed to ComfyUI launch. |

---

## 💻 Manual CLI Usage

```bash
# Interactive TUI Menu
comfy-dl

# Run a preset
comfy-dl --preset klein-9b --launch
comfy-dl --preset trellis-2

# Download specific models
comfy-dl \
  --unet "https://huggingface.co/.../model.safetensors" \
  --clip "https://huggingface.co/.../encoder.gguf" \
  --vae "https://huggingface.co/.../vae.safetensors:flux2_vae.safetensors" \
  --lora "https://civitai.com/api/download/models/12345:style.safetensors"

# Zip all generated outputs for easy download
comfy-dl --zip-output
```
