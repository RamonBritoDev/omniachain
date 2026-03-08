"""OmniaChain pipeline — sequencial, paralelo, condicional e roteamento."""

from omniachain.pipeline.sequential import SequentialPipeline
from omniachain.pipeline.parallel import ParallelPipeline
from omniachain.pipeline.conditional import ConditionalPipeline
from omniachain.pipeline.router import RouterPipeline

__all__ = ["SequentialPipeline", "ParallelPipeline", "ConditionalPipeline", "RouterPipeline"]
