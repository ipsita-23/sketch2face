import pytest
import torch

from sketch2face.model import Matcher, contrastive_loss, load_checkpoint


def test_pair_loss_rewards_correct_correspondence():
    features = torch.eye(4, requires_grad=True)
    good = contrastive_loss(features, features)
    bad = contrastive_loss(features, features.flip(0))
    assert good < bad
    good.backward()
    assert torch.isfinite(features.grad).all()
    with pytest.raises(ValueError):
        contrastive_loss(features[:1], features[:1])


def test_embeddings_and_checkpoint_roundtrip(tmp_path):
    torch.set_num_threads(2)
    model = Matcher(pretrained=False).eval()
    image = torch.randn(2, 3, 64, 64)
    with torch.inference_mode():
        expected = model(image, "sketch")
    assert expected.shape == (2, 256)
    assert torch.allclose(expected.norm(dim=1), torch.ones(2), atol=1e-5)
    path = tmp_path / "model.pt"
    torch.save(
        {"schema_version": 1, "state_dict": model.state_dict(), "model_config": model.config}, path
    )
    restored, _ = load_checkpoint(path, torch.device("cpu"))
    with torch.inference_mode():
        assert torch.allclose(restored(image, "sketch"), expected)
