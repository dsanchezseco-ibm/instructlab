import dataclasses
import logging
import math
import os
import io
import sys
import json
from typing import Optional, Sequence, Union

from openai import OpenAI
import copy

StrOrOpenAIObject = Union[str, object]

SYSTEM_PROMPT = "You are Labrador, an AI language model developed by" \
    + "IBM DMF (Data Model Factory) Alignment Team. You are a cautious assistant." \
    + "You carefully follow instructions. You are helpful and harmless and you follow" \
    + "ethical guidelines and promote positive behavior."

# pylint: disable=too-many-instance-attributes
@dataclasses.dataclass
class OpenAIDecodingArguments:
    max_tokens: int = 1800
    temperature: float = 0.2
    top_p: float = 1.0
    n: int = 1
    stream: bool = False
    stop: Optional[Sequence[str]] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    logprobs: Optional[int] = None


def openai_completion(
    prompts: Union[str, Sequence[str], Sequence[dict[str, str]], dict[str, str]],
    decoding_args: OpenAIDecodingArguments,
    model_name="ggml-labrador13B-model-Q4_K_M",
    batch_size=1,
    max_instances=sys.maxsize,
    max_batches=sys.maxsize,
    return_text=False,
    **decoding_kwargs,
) -> Union[
        Union[StrOrOpenAIObject],
        Sequence[StrOrOpenAIObject],
        Sequence[Sequence[StrOrOpenAIObject]],]:
    """Decode with OpenAI API.

    Args:
        prompts: A string or a list of strings to complete. If it is a chat model the strings 
            should be formatted as explained here: 
            https://github.com/openai/openai-python/blob/main/chatml.md. 
            If it is a chat model it can also be a dictionary (or list thereof) as explained here:
            https://github.com/openai/openai-cookbook/blob/main/examples/How_to_format_inputs_to_ChatGPT_models.ipynb
        decoding_args: Decoding arguments.
        model_name: Model name. Can be either in the format of "org/model" or just "model".
        batch_size: Number of prompts to send in a single request. Only for non chat model.
        max_instances: Maximum number of prompts to decode.
        max_batches: Maximum number of batches to decode. This will be deprecated in the future.
        return_text: If True, return text instead of full completion object (e.g. includes logprob).
        decoding_kwargs: Extra decoding arguments. Pass in `best_of` and `logit_bias` if needed.

    Returns:
        A completion or a list of completions. Depending on return_text, return_openai_object, 
        and decoding_args.n, the completion type can be one of:
            - a string (if return_text is True)
            - an openai_object.OpenAIObject object (if return_text is False)
            - a list of objects of the above types (if decoding_args.n > 1)
    """
    is_single_prompt = isinstance(prompts, (str, dict))
    if is_single_prompt:
        prompts = [prompts]

    if max_batches < sys.maxsize:
        logging.warning(
            "`max_batches` will be deprecated in the future, please use `max_instances` instead."
            "Setting `max_instances` to `max_batches * batch_size` for now."
        )
        max_instances = max_batches * batch_size

    prompts = prompts[:max_instances]
    num_prompts = len(prompts)
    prompt_batches = [
        prompts[batch_id * batch_size : (batch_id + 1) * batch_size]
        for batch_id in range(int(math.ceil(num_prompts / batch_size)))
    ]

    completions = []
    for batch_id, prompt_batch in enumerate(prompt_batches):
        batch_decoding_args = copy.deepcopy(decoding_args)  # cloning the decoding_args

        shared_kwargs = {"model": model_name, **batch_decoding_args.__dict__, **decoding_kwargs, }

        client = OpenAI(base_url="http://localhost:8000/v1", api_key="foo")

        messages = [
            {"role": "system",
            "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_batch[batch_id]}
        ]

        # Inference the model
        response = client.chat.completions.create(
            messages=messages,
            **shared_kwargs,
        )

        completions.extend(response.choices)

    if return_text:
        completions = [completion.text for completion in completions]
    if decoding_args.n > 1:
        # make a nested list, where each entry is consecutive decoding_args.n of original entries.
        completions = [
            completions[
                i : i + decoding_args.n]
                for i in range(0, len(completions), decoding_args.n)
            ]
    if is_single_prompt:
        # Return non-tuple if only 1 input and 1 generation.
        (completions,) = completions
    return completions


def _make_w_io_base(f, mode: str):
    if not isinstance(f, io.IOBase):
        f_dirname = os.path.dirname(f)
        if f_dirname != "":
            os.makedirs(f_dirname, exist_ok=True)
        f = open(f, encoding="utf-8", mode=mode)
    return f


def _make_r_io_base(f, mode: str):
    if not isinstance(f, io.IOBase):
        f = open(f, encoding="utf-8", mode=mode)
    return f


def jdump(obj, f, mode="w", indent=4, default=str):
    """Dump a str or dictionary to a file in json format.

    Args:
        obj: An object to be written.
        f: A string path to the location on disk.
        mode: Mode for opening the file.
        indent: Indent for storing json dictionaries.
        default: A function to handle non-serializable entries; defaults to `str`.
    """
    f = _make_w_io_base(f, mode)
    if isinstance(obj, (dict, list)):
        json.dump(obj, f, indent=indent, default=default)
    elif isinstance(obj, str):
        f.write(obj)
    else:
        raise ValueError(f"Unexpected type: {type(obj)}")
    f.close()


def jload(f, mode="r"):
    """Load a .json file into a dictionary."""
    f = _make_r_io_base(f, mode)
    jdict = json.load(f)
    f.close()
    return jdict
