from sae.trainers.standard import StandardTrainer
from sae.trainers.matryoshka_batch_topk import MatryoshkaBatchTopKTrainer

TRAINERS = {
    "standard": StandardTrainer,
    "matryoshka_batch_top_k": MatryoshkaBatchTopKTrainer,
}

__all__ = ["StandardTrainer", "MatryoshkaBatchTopKTrainer", "TRAINERS"]
