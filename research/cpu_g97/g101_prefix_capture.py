#!/usr/bin/env python3
"""G101 development-only: compact prefix-KV capture from normal full prefill.

This is a causal mechanism primitive, not an original GPT-2 inference adapter,
performance result, held-out execution, or production cache implementation.
The caller must account for the full prefill, extraction, copies, and retention.
"""
from research.cpu_g96.g96_admission import BYTE_LIMIT


class PrefixCaptureError(ValueError):
    """The GPT-2 KV shape, memory, or ownership contract is violated."""


def _meta(tensor, expected_length):
    needed = ("shape", "numel", "element_size", "data_ptr", "detach")
    if any(not hasattr(tensor, name) for name in needed):
        raise PrefixCaptureError("G101_NOT_TENSOR")
    shape = tuple(tensor.shape)
    if (len(shape) != 4 or any(type(x) is not int or x <= 0 for x in shape)
            or shape[-2] != expected_length):
        raise PrefixCaptureError("G101_BAD_CACHE_LAYOUT")
    numel, size = tensor.numel(), tensor.element_size()
    if type(numel) is not int or type(size) is not int or numel <= 0 or size <= 0:
        raise PrefixCaptureError("G101_BAD_STORAGE_METADATA")
    return shape, numel * size


def capture_prefix_from_full_prefill(full_past, prefix_tokens, *,
                                      expected_bytes=None, byte_limit=BYTE_LIMIT):
    """Copy the causal prefix slice, with *no* additional model forward.

    GPT-2 past is a nonempty sequence of (key,value) tensor pairs shaped
    (batch, heads, full_seq, head_width). Strictly validate every tensor and
    the full projected budget *before* allocating prefix copies.
    """
    if type(prefix_tokens) is not int or prefix_tokens <= 0:
        raise PrefixCaptureError("G101_INVALID_PREFIX_LENGTH")
    if type(byte_limit) is not int or byte_limit <= 0:
        raise PrefixCaptureError("G101_INVALID_MEMORY_LIMIT")
    if not isinstance(full_past, (tuple, list)) or not full_past:
        raise PrefixCaptureError("G101_INVALID_KV_TREE")
    if expected_bytes is not None and (type(expected_bytes) is not int or expected_bytes <= 0):
        raise PrefixCaptureError("G101_INVALID_EXPECTED_BYTES")
    full_length, planned_bytes, checked = None, 0, []
    for layer in full_past:
        if not isinstance(layer, (tuple, list)) or len(layer) != 2:
            raise PrefixCaptureError("G101_INVALID_LAYER_PAIR")
        shapes = []
        for tensor in layer:
            if not hasattr(tensor, "shape") or len(tensor.shape) != 4:
                raise PrefixCaptureError("G101_BAD_CACHE_LAYOUT")
            length = tensor.shape[-2]
            shape, _ = _meta(tensor, length)
            if full_length is None:
                full_length = length
            if length != full_length or prefix_tokens > length:
                raise PrefixCaptureError("G101_CONTEXT_LENGTH_MISMATCH")
            shapes.append(shape)
            planned_bytes += shape[0] * shape[1] * prefix_tokens * shape[3] * tensor.element_size()
        if shapes[0] != shapes[1]:
            raise PrefixCaptureError("G101_MISMATCHED_KV_SHAPES")
        checked.append(layer)
    if expected_bytes is not None and planned_bytes != expected_bytes:
        raise PrefixCaptureError("G101_EXPECTED_BYTES_DRIFT")
    if planned_bytes > byte_limit:
        raise PrefixCaptureError("G101_MEMORY_CAP_EXCEEDED")

    source_pointers = {t.data_ptr() for pair in checked for t in pair}
    owned_pointers, output = set(), []
    for layer in checked:
        pair = []
        for tensor in layer:
            # A clone, never a view: no hidden retention of full prompt storage.
            copied = tensor[..., :prefix_tokens, :].detach().clone()
            shape, logical_bytes = _meta(copied, prefix_tokens)
            if shape != tuple(tensor.shape[:2]) + (prefix_tokens, tensor.shape[-1]):
                raise PrefixCaptureError("G101_COPY_SHAPE_DRIFT")
            ptr = copied.data_ptr()
            if ptr in source_pointers or ptr in owned_pointers:
                raise PrefixCaptureError("G101_UNSAFE_STORAGE_ALIAS")
            owned_pointers.add(ptr)
            if hasattr(copied, "untyped_storage"):
                if copied.untyped_storage().nbytes() != logical_bytes:
                    raise PrefixCaptureError("G101_NONCOMPACT_CLONE")
            pair.append(copied)
        output.append(tuple(pair))
    return tuple(output)


def prefill_and_capture(model, full_input_ids, prefix_tokens, *,
                        expected_bytes=None, byte_limit=BYTE_LIMIT):
    """Exactly one full-input forward. The caller must reuse this prefill output.

    The full-prompt output is the decoding input for this request; captured
    prefix KV is only for subsequent exact-prefix reuse. No model calls or
    timing are concealed by this helper.
    """
    output = model(input_ids=full_input_ids, use_cache=True)
    if not hasattr(output, "past_key_values"):
        raise PrefixCaptureError("G101_MISSING_FULL_PREFILL_KV")
    return output, capture_prefix_from_full_prefill(
        output.past_key_values, prefix_tokens,
        expected_bytes=expected_bytes, byte_limit=byte_limit)
