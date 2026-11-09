"""Modality adapters + shared ResNet-18 + normalized projection."""

import torch
from torch import nn
from torch.nn import functional as F
from torchvision.models import ResNet18_Weights, resnet18


class Matcher(nn.Module):
    def __init__(self, embedding_dim=256, pretrained=True, baseline=False, adapters=True):
        super().__init__()
        self.config = {"embedding_dim": embedding_dim, "baseline": baseline, "adapters": adapters}
        self.encoder = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1 if pretrained else None)
        self.encoder.fc = nn.Identity()
        self.adapters = nn.ModuleDict(
            {key: nn.Conv2d(3, 3, 1, bias=False) for key in ("sketch", "photo")}
        )
        for adapter in self.adapters.values():
            nn.init.zeros_(adapter.weight)
        self.projector = nn.Sequential(
            nn.Linear(512, 256), nn.ReLU(), nn.Linear(256, embedding_dim)
        )

    def forward(self, images, modality):
        if modality not in ("sketch", "photo"):
            raise ValueError("Modality must be sketch or photo.")
        if self.config["adapters"] and not self.config["baseline"]:
            images = images + self.adapters[modality](images)
        features = self.encoder(images)
        if not self.config["baseline"]:
            features = self.projector(features)
        return F.normalize(features, dim=1)

    def training_stage(self, fine_tune):
        self.train()
        self.encoder.requires_grad_(False)
        # Freeze BatchNorm statistics: small datasets should not overwrite them.
        self.encoder.eval()
        if fine_tune:
            self.encoder.layer4.requires_grad_(True)


def contrastive_loss(sketches, photos, temperature=0.07):
    if sketches.shape != photos.shape or len(sketches) < 2:
        raise ValueError("Contrastive learning needs at least two distinct paired identities.")
    if temperature <= 0:
        raise ValueError("Temperature must be positive.")
    logits = sketches @ photos.T / temperature
    target = torch.arange(len(sketches), device=sketches.device)
    return (F.cross_entropy(logits, target) + F.cross_entropy(logits.T, target)) / 2


def load_checkpoint(path, device):
    # weights_only prevents arbitrary Python unpickling; use checkpoints from trusted sources.
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported checkpoint format.")
    model = Matcher(pretrained=False, **payload["model_config"])
    model.load_state_dict(payload["state_dict"])
    return model.to(device).eval(), payload
