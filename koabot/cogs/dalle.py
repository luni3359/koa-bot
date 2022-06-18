import random
import shutil
from datetime import datetime
from functools import partial
from pathlib import Path

import jax
import jax.numpy as jnp
import numpy as np
from dalle_mini import DalleBart, DalleBartProcessor
from discord.ext import commands
from flax.jax_utils import replicate
from flax.training.common_utils import shard_prng_key
from PIL import Image
from tqdm.notebook import trange
from transformers import CLIPProcessor, FlaxCLIPModel
from vqgan_jax.modeling_flax_vqgan import VQModel

from koabot.kbot import KBot

# FROM https://github.com/borisdayma/dalle-mini/blob/main/tools/inference/inference_pipeline.ipynb
# Model references

# dalle-mega
# can be wandb artifact or 🤗 Hub or local folder or google bucket
DALLE_MODEL = "dalle-mini/dalle-mini/mega-1-fp16:latest"
DALLE_COMMIT_ID = None

# if the notebook crashes too often you can use dalle-mini instead by uncommenting below line
# DALLE_MODEL = "dalle-mini/dalle-mini/mini-1:v0"

# VQGAN model
VQGAN_REPO = "dalle-mini/vqgan_imagenet_f16_16384"
VQGAN_COMMIT_ID = "e93a26e7707683d349bf5d5c41c5b0ef69b677a9"


# Load dalle-mini
model, params = DalleBart.from_pretrained(
    DALLE_MODEL, revision=DALLE_COMMIT_ID, dtype=jnp.float16, _do_init=False
)

# Load VQGAN
vqgan, vqgan_params = VQModel.from_pretrained(
    VQGAN_REPO, revision=VQGAN_COMMIT_ID, _do_init=False
)

params = replicate(params)
vqgan_params = replicate(vqgan_params)


# model inference
@partial(jax.pmap, axis_name="batch", static_broadcasted_argnums=(3, 4, 5, 6))
def p_generate(
    tokenized_prompt, key, params, top_k, top_p, temperature, condition_scale
):
    return model.generate(
        **tokenized_prompt,
        prng_key=key,
        params=params,
        top_k=top_k,
        top_p=top_p,
        temperature=temperature,
        condition_scale=condition_scale,
    )


# decode image
@partial(jax.pmap, axis_name="batch")
def p_decode(indices, params):
    return vqgan.decode_code(indices, params=params)


# create a random key
seed = random.randint(0, 2**32 - 1)
key = jax.random.PRNGKey(seed)

# number of predictions per prompt
n_predictions = 9

# We can customize generation parameters (see https://huggingface.co/blog/how-to-generate)
gen_top_k = None
gen_top_p = None
temperature = None
cond_scale = 10.0

processor = DalleBartProcessor.from_pretrained(DALLE_MODEL, revision=DALLE_COMMIT_ID)


class Dalle(commands.Cog):
    def __init__(self, bot: KBot) -> None:
        self.bot = bot
        self.cache_dir = Path(self.bot.CACHE_DIR, "dalle")


    @commands.command(hidden=True)
    @commands.is_owner()
    async def dalle(self, ctx: commands.Context, *, prompt: str):
        prompts = ["sunset over a lake in the mountains", "the Eiffel tower landing on the moon"]
        tokenized_prompts = processor(prompts)
        tokenized_prompt = replicate(tokenized_prompts)

        # generate images
        images = []
        for i in trange(max(n_predictions // jax.device_count(), 1)):
            # get a new key
            key, subkey = jax.random.split(key)
            # generate images
            encoded_images = p_generate(
                tokenized_prompt,
                shard_prng_key(subkey),
                params,
                gen_top_k,
                gen_top_p,
                temperature,
                cond_scale,
            )
            # remove BOS
            encoded_images = encoded_images.sequences[..., 1:]
            # decode images
            decoded_images = p_decode(encoded_images, vqgan_params)
            decoded_images = decoded_images.clip(0.0, 1.0).reshape((-1, 256, 256, 3))
            for decoded_img in decoded_images:
                img = Image.fromarray(np.asarray(decoded_img * 255, dtype=np.uint8))
                images.append(img)
                # display(img)
                filename = f"{random.randrange(100, 999)}@{datetime.now()}"
                print(f"Saving picture '{filename}'")
                with open(Path(self.cache_dir, filename), 'wb') as image_file:
                    shutil.copyfileobj(img, image_file)
                # print()


async def setup(bot: KBot):
    """Initiate cog"""
    await bot.add_cog(Dalle(bot))
