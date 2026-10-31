"""Demo stand-ins for the GIFs: friendly faces imagined by SD-Turbo (no real person)."""
import os, sys, torch
from diffusers import AutoPipelineForText2Image
OUT = os.path.dirname(os.path.abspath(__file__))
dev = "mps" if torch.backends.mps.is_available() else "cpu"
dtype = torch.float16 if dev == "mps" else torch.float32
kw = {"variant": "fp16"} if dtype == torch.float16 else {}
pipe = AutoPipelineForText2Image.from_pretrained("stabilityai/sd-turbo", torch_dtype=dtype, **kw).to(dev)
pipe.enable_attention_slicing(); pipe.set_progress_bar_config(disable=True)
PROMPTS = {
 "woman": "phone selfie photo, head and shoulders of a friendly woman in her thirties with brown hair, looking straight into the camera, neutral expression, cozy living room at night, warm lamp light, natural skin, photorealistic",
 "man": "phone selfie photo, head and shoulders of a friendly bearded man in his thirties, looking straight into the camera, neutral expression, cozy living room at night, warm lamp light, natural skin, photorealistic",
}
for name, p in PROMPTS.items():
    for seed in range(4):
        g = torch.Generator("cpu").manual_seed(100 + seed)
        img = pipe(prompt=p, num_inference_steps=4, guidance_scale=0.0, width=512, height=512, generator=g).images[0]
        if sum(img.convert("L").getextrema()) < 5 and dev == "mps":
            pipe = pipe.to(torch.float32); img = pipe(prompt=p, num_inference_steps=4, guidance_scale=0.0, width=512, height=512, generator=g).images[0]
        img.save(os.path.join(OUT, f"face_{name}_{seed}.png")); print("saved", name, seed, flush=True)
print("DONE", flush=True)
