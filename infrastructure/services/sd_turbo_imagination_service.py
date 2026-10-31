"""SD-Turbo (distilled Stable Diffusion, open weights from Stability AI) imagining photos ON YOUR MAC.
The first run downloads about 2.5 GB from Hugging Face; after that it works offline."""
import sys

import numpy as np

from domain.services.imagination_service import ImaginationService

MODEL = "stabilityai/sd-turbo"
GEN_W, GEN_H = 640, 360               # multiples of 8; scaled up to the TV later


class SdTurboImaginationService(ImaginationService):
    def __init__(self, log=print):
        self.log = log
        self.pipe = None

    def _load(self):
        try:
            import torch
            from diffusers import AutoPipelineForText2Image
        except ImportError:
            sys.exit("The image model libraries are missing. Run: make realistic (it installs them)")
        if torch.backends.mps.is_available():
            device, dtype = "mps", torch.float16
        elif torch.cuda.is_available():
            device, dtype = "cuda", torch.float16
        else:
            device, dtype = "cpu", torch.float32
        self.log(f"Loading {MODEL} on {device} (the first run downloads ~2.5 GB)…")
        kw = {"torch_dtype": dtype}
        if dtype == torch.float16:
            kw["variant"] = "fp16"
        pipe = AutoPipelineForText2Image.from_pretrained(MODEL, **kw).to(device)
        pipe.enable_attention_slicing()       # fits in 8 GB of memory
        pipe.set_progress_bar_config(disable=True)
        self.pipe, self.device, self.torch = pipe, device, torch

    def _run(self, prompt, seed):
        g = self.torch.Generator("cpu").manual_seed(seed)
        img = self.pipe(prompt=prompt, num_inference_steps=4, guidance_scale=0.0, width=GEN_W, height=GEN_H, generator=g).images[0]
        return np.asarray(img.convert("RGB"))

    def imagine(self, prompt, seed):
        if self.pipe is None:
            self._load()
        arr = self._run(prompt, seed)
        if arr.mean() < 3 and self.device == "mps":      # some Macs return a black image in float16: retry in float32
            self.log("  (black image in float16: retrying in float32, a bit slower)")
            self.pipe = self.pipe.to(self.torch.float32)
            arr = self._run(prompt, seed)
        return arr
