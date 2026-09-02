# comfy-dl

A lightweight helper utility for RunPod pods to fetch ComfyUI models, text encoders, and custom nodes before launching the server.

Designed primarily as a startup helper for persistent `/workspace` volumes on GPU cloud instances, using `aria2c` for fast multi-threaded downloads with automatic fallback to `curl`.

---

## Usage

### Interactive Menu
Run without arguments inside a Web Terminal or SSH session:

```bash
comfy-dl
```

### Presets
Built-in bundles for quick setup:

```bash
# FLUX.2 Klein 9B (Distilled) + Ponpoke Q8 GGUF + VAE
comfy-dl --preset klein-9b --launch

# FLUX.2 Klein 9B Base (Undistilled) + Ponpoke Q8 GGUF + VAE
comfy-dl --preset klein-9b-base --launch
```

### Direct Model Flags
Flags map directly to ComfyUI subfolders. Downloads can be chained and optionally renamed using `:custom_name`:

```bash
comfy-dl \
  --unet "https://huggingface.co/.../model.safetensors" \
  --clip "https://huggingface.co/.../encoder.gguf" \
  --vae "https://huggingface.co/.../diffusion_pytorch_model.safetensors:flux2_vae.safetensors" \
  --lora "https://civitai.com/api/download/models/12345:style.safetensors" \
  --launch
```

| Flag | Destination |
| :--- | :--- |
| `--unet` | `models/diffusion_models/` |
| `--clip` | `models/text_encoders/` & `models/clip/` |
| `--vae` | `models/vae/` |
| `--lora` | `models/loras/` |
| `--checkpoint` | `models/checkpoints/` |
| `--controlnet` | `models/controlnet/` |
| `--upscale` | `models/upscale_models/` |
| `--custom-node <git-url>` | Clones repo into `custom_nodes/` & installs requirements |
| `--install-nodes` | Installs default nodes (Manager, KJNodes, Civicomfy, RunpodDirect, GGUF) |
| `--launch` | Starts ComfyUI server after downloads complete |

---

## Authentication

For gated Hugging Face repositories, export an access token:

```bash
export HF_TOKEN="hf_..."
```
