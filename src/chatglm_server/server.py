from fastapi import FastAPI, Request
from transformers import AutoTokenizer, AutoModel
import uvicorn, json, datetime
import torch
from typing import Dict, Tuple, Union, Optional
import os
from torch.nn import Module
from util.app_config import app_config


DEVICE = "cuda"
DEVICE_IDS = ["0", "1"]
CUDA_DEVICES = [f"{DEVICE}:{device_id}" for device_id in DEVICE_IDS] if DEVICE_IDS else [DEVICE]

DEFAULT_MAX_LENGTH = 2048
DEFAULT_TOP_P = 0.7
DEFAULT_TEMPERATURE = 0.95

# Model Path
MODEL_PATH = app_config.CHATGLM_MODEL_PATH

app = FastAPI()


def load_model_on_gpus(checkpoint_path: Union[str, os.PathLike], num_gpus: int = 1,
                       device_map: Optional[Dict[str, int]] = None, **kwargs) -> Module:
    if num_gpus < 2 and device_map is None:
        model = AutoModel.from_pretrained(checkpoint_path, trust_remote_code=True, **kwargs).half().cuda()
    else:
        model = AutoModel.from_pretrained(checkpoint_path, trust_remote_code=True, device_map="auto").half()

    return model


def torch_gc():
    if torch.cuda.is_available():
        for device in CUDA_DEVICES:
            with torch.cuda.device(device):
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()


@app.post("/")
async def create_item(request: Request):
    global model, tokenizer
    json_post_raw = await request.json()
    json_post = json.dumps(json_post_raw)
    json_post_list = json.loads(json_post)
    prompt = json_post_list.get('prompt')
    history = json_post_list.get('history')
    max_length = json_post_list.get('max_length')
    top_p = json_post_list.get('top_p')
    temperature = json_post_list.get('temperature')

    # Ensure history is in the correct format
    if isinstance(history, list):
        for i, item in enumerate(history):
            if isinstance(item, list) and len(item) == 2:
                history[i] = {"role": "user", "content": item[0]}
                history.append({"role": "assistant", "content": item[1]})
            elif not isinstance(item, dict):
                raise ValueError(f"Invalid history item at index {i}: {item}")

    response, history = model.chat(tokenizer,
                                   prompt,
                                   history=history,
                                   max_length=max_length if max_length else DEFAULT_MAX_LENGTH,
                                   top_p=top_p if top_p else DEFAULT_TOP_P,
                                   temperature=temperature if temperature else DEFAULT_TEMPERATURE
                                   )

    now = datetime.datetime.now()
    time = now.strftime("%Y-%m-%d %H:%M:%S")
    answer = {
        "response": response,
        "history": history,
        "status": 200,
        "time": time
    }
    log = "[" + time + "] " + '", prompt:"' + prompt + '", response:"' + repr(response) + '"'
    print(log)
    torch_gc()
    return answer


if __name__ == '__main__':
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    model = load_model_on_gpus(MODEL_PATH, num_gpus=2)
    model.eval()
    uvicorn.run(app, host="0.0.0.0", port=8862)
