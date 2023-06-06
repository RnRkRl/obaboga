from modules.logging_colors import logger


def patch_falcon_rotary_embedding(model):
    """The `modelling_RW.py` provided with some of the Falcon models has a bug in its rotary embedding code where it doesn't respect the incoming datatypes. This causes a crash such as `RuntimeError: Expected query, key, and value to have the same dtype, but got query.dtype: float key.dtype: float and value.dtype: c10::Half instead.` when using a custom dtype.

    Our fix is to monkeypatch `RotaryEmbedding.forward` to wrap the original implementation to cast the result back to the incoming dtype. This will have no effect if the original implementation is correct (since we'd convert from the same dtype to the same dtype which is a no-op.)
    """

    if model.__class__.__name__ != 'RWForCausalLM':
        return model

    # Since the code is downloaded dynamically, it's easiest to find the RotaryEmbedding module by name.
    for name, child in model.named_modules():
        if child.__class__.__name__ != 'RotaryEmbedding':
            continue

        logger.info(f"Found Falcon RotaryEmbedding. Patching...")
        original_forward = child.__class__.forward

        def falcon_rotary_forward_wrapper(self, q, k):
            out_q, out_k = original_forward(self, q, k)
            return out_q.to(q.dtype), out_k.to(k.dtype)

        child.__class__.forward = falcon_rotary_forward_wrapper
        # Since we're patching the class (not the instance), all instances will be patched.
        break

    return model
