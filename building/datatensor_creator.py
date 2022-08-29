from PIL import Image
import pandas as pd
import copy
from torchvision.datasets import CocoCaptions
from transformers import (
  DistilBertTokenizer, DistilBertForMaskedLM, DistilBertConfig,
  CLIPProcessor, CLIPModel as CLIP, CLIPConfig
)
import torch
from torch.utils.data import DataLoader
from torch import nn, optim
import tqdm
import matplotlib.pyplot as plt
import os
import sys

if torch.cuda.is_available():
  dev = "cuda:0"
else:
  dev = "cpu"
device = torch.device(dev)
print("using device: ", dev)

# # download pretrained model and tokenizer
# def save_model_tokenizer(tokenizer_class, model_class, name):
#   if tokenizer_class is not None:
#     tokenizer = tokenizer_class.from_pretrained(name)
#     tokenizer.save_pretrained(f"./tokenizers/{name}-local")
#   if model_class is not None:
#     model = model_class.from_pretrained(name)
#     model.save_pretrained(f"./models/{name}-local/")

# save_model_tokenizer(CLIPProcessor, CLIP, "openai/clip-vit-base-patch32")

# hyperparameters
BATCH_SIZE = 16
MAX_LENGTH = 128 # max text length
LEARNING_RATE = 5e-5
EPOCH_NUM = 1
ROUNDING_WEIGHT = 0.3 # weight of rounding term, the probability of regenerated sequence 

# diffusion hyperparameter
BETA_MIN = 0.0001
BETA_MAX = 0.02
STEP_TOT = 2000 # total noise adding steps
COSIN_SCHEDULE = True # if alpha sequence is scheduled in cosin instead of linear patten
SAMPLE_SIZE = 3 # number of sample steps in each diffuse sequence
X_0_PREDICTION = True # if model predicts x_0 or x_{t-1}

clip_processor = CLIPProcessor.from_pretrained("./tokenizers/openai/clip-vit-base-patch32-local")
clip = CLIP.from_pretrained("./models/openai/clip-vit-base-patch32-local")

class Flickr8kCLIPDataset(torch.utils.data.Dataset):
  def __init__(self, dir, clip_processor, clip) -> None:
    self.dir = dir
    self.caption = pd.read_csv(f"{dir}/captions.txt")

    self.clip = clip
    self.clip_processor = clip_processor

  def __len__(self):
    return len(self.caption)

  def __getitem__(self, idx):
    sample = self.caption.loc[idx]

    inputs = self.clip_processor(text=sample["caption"], images=Image.open(f"{self.dir}/images/{sample['image']}"), return_tensors="pt", padding=True)
    outputs = self.clip(**inputs)

    return outputs.text_embeds, outputs.image_embeds

# if dict on clip (4.5 s/batch 3.5h), dict on image (4.7 s/batch 3.5h), load on request (4.5 ) better
# try on load on request in colect func
train_dataset = Flickr8kCLIPDataset("flickr8k/", clip_processor, clip)
# train_loader = DataLoader(train_dataset, shuffle=True, batch_size=BATCH_SIZE, collate_fn=train_dataset.collate_fn)

image_all = torch.tensor([]).reshape((0, 512))
text_all = torch.tensor([]).reshape((0, 512))
# start = 1000 * int(sys.argv[1])
# end = start + 1000
start = 40000
end = len(train_dataset)
# print(f"start loading on cnt = {sys.argv[1]}")
with tqdm.tqdm(range(start, end)) as process:
  for i in process:
    image, text = train_dataset[i]
    image_all = torch.vstack([image_all, image])
    text_all = torch.vstack([text_all, text])

# torch.save(image_all, f"image_all_{sys.argv[1]}.pickle")
# torch.save(text_all, f"text_all_{sys.argv[1]}.pickle")
torch.save(image_all, f"image_all_40.pickle")
torch.save(text_all, f"text_all_40.pickle")
