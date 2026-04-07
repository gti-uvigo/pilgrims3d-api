import torch
from diffusers import StableDiffusion3Pipeline
from transformers import AutoModelForCausalLM, AutoTokenizer
from torch.nn.functional import softmax
import os
from huggingface_hub import snapshot_download
import gc
import GPUtil


model_path = "/models/Qwen3-8B"
model = None
tokenizer = None

def get_vram_free_mb():
    try:
        gpus = GPUtil.getGPUs()
        if not gpus:
            print("No se encontraron GPUs NVIDIA.")
            exit()
        print("Información de memoria de la(s) GPU(s) NVIDIA:")
        for i, gpu in enumerate(gpus):
            print(f"\n--- GPU {gpu.id} ({gpu.name}) ---")
            mem_libre_mb = gpu.memoryFree
            mem_usada_mb = gpu.memoryUsed
            mem_total_mb = gpu.memoryTotal
            print(f"  Memoria Libre: {mem_libre_mb:.2f} MB")
            print(f"  Memoria Usada: {mem_usada_mb:.2f} MB")
            print(f"  Memoria Total: {mem_total_mb:.2f} MB")
        return mem_libre_mb
    except Exception as e:
        print(f"Ocurrió un error al obtener la información de la GPU: {e}")
        print("Asegúrate de tener los drivers de NVIDIA instalados y actualizados.")
   
    
def generate_image_SD35(prompt: str = None):
    if prompt is None:
        raise ValueError("Prompt cannot be None.")

    torch.cuda.empty_cache()
    gc.collect()

    model_id = "/models/stable-diffusion-3.5-m"
    pipe = StableDiffusion3Pipeline.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        use_safetensors=True,
        variant="fp16"
    ).to("cuda")

    pipe.enable_attention_slicing()

    image = pipe(
        prompt,
        num_inference_steps=12,  
        guidance_scale=5.5,      
        height=512,
        width=512,
        generator=torch.Generator("cuda").manual_seed(42)
    ).images[0]

    pipe = None

    del pipe
    torch.cuda.empty_cache()
    gc.collect()

    return image

def load_model():
    global tokenizer, model
    if model is not None and tokenizer is not None:
        print("Model already loaded.")
        return True

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16,  
        device_map="cuda",
        attn_implementation="flash_attention_2"
    )
    return True


def unload_model():
    global tokenizer, model
    del model
    del tokenizer
    model = None
    tokenizer = None
    torch.cuda.empty_cache()


def ensure_model():
    if not os.path.exists(model_path):
        print("🔽 Downloading model...")
        snapshot_download(
            repo_id="Qwen/Qwen3-8B",
            local_dir=model_path,
            local_dir_use_symlinks=False
        )
        print("✅ Model downloaded")
    # if not os.path.exists(image_model_path):
    #     print("🔽 Downloading image model...")
    #     snapshot_download(
    #         repo_id="black-forest-labs/FLUX.1-schnell",
    #         local_dir=image_model_path,
    #         local_dir_use_symlinks=False
    #     )
    #     print("✅ Image model downloaded")


def generate_text(prompt: str = "testtt"):
    global tokenizer, model
    if model is None or tokenizer is None:
        return "Model not loaded. Please load the model first."
    if prompt is None or prompt.strip() == "":
        return "No prompt provided"
    

    # prepare the model input
    messages = [
        {"role": "user", "content": prompt}
    ]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False 
    )
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=512,
    )
    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist() 

    try:
        index = len(output_ids) - output_ids[::-1].index(151668)
    except ValueError:
        index = 0

    thinking_content = tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
    content = tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")

    print("thinking content:", thinking_content)
    print("content:", content)
    return content


def moderate_text(text: str):
    """
    Analiza un texto y devuelve etiquetas / probabilidades de contenido inapropiado.
    """
    model_id = "/models/shieldgemma-9b"
    tokenizer_moderate = AutoTokenizer.from_pretrained(model_id)
    model_moderate = AutoModelForCausalLM.from_pretrained(
        model_id,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )

    safety_policy = """
        * "No Harassment": The text must not include insults, bullying, intimidation, or content that humiliates or targets individuals or groups (e.g., physical threats, denial of tragic events, mocking victims of violence).
        * "No Hate Speech": The text must not promote or justify hatred, discrimination, or violence based on race, ethnicity, nationality, gender, religion, sexual orientation, or any other identity.
        * "No Sexual or Vulgar Content": The text must not contain sexually explicit, suggestive, or pornographic language, nor crude or obscene expressions.
        * "No Violent or Gory Content": The text must not describe or glorify violence, injury, or death.
        * "No Offensive or Inappropriate Language": The text must not include profanity, slurs, or expressions that are considered rude, inappropriate, or disrespectful in English or Spanish.
        """

    prompt = f"""
        You are a multilingual policy and content moderation expert.
        Your goal is to determine whether a given user text (in English or Spanish)
        violates the safety principles defined below. The text may be a title or
        description of a Point of Interest (POI), such as a place, monument, restaurant,
        or attraction.

        <start_of_turn>
        User text: {text.strip()}
        <end_of_turn>

        Safety Principles:
        {safety_policy.strip()}

        Question: Does the user text violate any of the safety principles above?
        Your answer must:
        1. Start with 'Yes' or 'No'.
        2. Provide a short justification explaining which policy (if any) is violated.
        3. Be strict — even mild or indirect sexual, hateful, or vulgar expressions count as violations.
        4. Consider both English and Spanish meanings and slang.
        """
    
    inputs = tokenizer_moderate(prompt, return_tensors="pt").to("cuda")

    with torch.no_grad():
        logits = model_moderate(**inputs).logits

    print("Logits:", logits)
    vocab = tokenizer_moderate.get_vocab()
    selected_logits = logits[0, -1, [vocab['Yes'], vocab['No']]]

    probabilities = softmax(selected_logits, dim=0)

    score = probabilities[0].item()

    del tokenizer_moderate
    del model_moderate
    torch.cuda.empty_cache()
    gc.collect()

    if score > 0.01:
        return {"reject": True, "scores": score}
    else:
        return {"reject": False, "scores": score}
