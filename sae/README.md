# sae

Activation-collection utilities for Foundry models. Registers forward hooks on a
target model (e.g. the EMA shadow of RFD3), subsamples dynamic denoising-step
activations, and flushes them to an HDF5 store alongside per-design metadata.

Installed as an optional extra of the parent project:

```bash
uv sync --extra sae
```
