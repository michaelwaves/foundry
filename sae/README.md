# sae

Activation-collection utilities for Foundry models. Registers forward hooks on a
target model (e.g. the EMA shadow of RFD3), subsamples dynamic denoising-step
activations, and flushes them to an HDF5 store alongside per-design metadata.

Installed as an optional extra of the parent project:

```bash
uv sync --extra sae
```

 ## run

  rfd3 design inputs=rfd3_na_tutorial.json out_dir=outputs/1 'activation_collection={out_dir: ./activations, hooks: [{name: s_trunk, module_path:
  token_initializer.process_s_trunk, hook_type: static}, {name: block12, module_path:
  diffusion_module.diffusion_transformer.blocks.12.transition_block, hook_type: dynamic,
  collect_every_n_steps: 20}]}'

 How the hooks work in the forward pass

  The trainer's validation_step (trainer/rfd3.py:220) calls model.forward(input=...,
  coord_atom_lvl_to_be_noised=...). model is the EMA wrapper — in eval mode, it dispatches to
  self.shadow (EMA.py:64-67). So PyTorch register_forward_hook calls on
  shadow.token_initializer.process_s_trunk and
  shadow.diffusion_module.diffusion_transformer.blocks.12.transition_block fire naturally inside
  the existing inference loop — no need to bypass validation_step.

  Shadow is reached via self.trainer.state["model"]._forward_module.shadow (Fabric wraps EMA in
  _FabricModule).

  - models/rfd3/src/rfd3/engine.py:
    - RFD3InferenceConfig.activation_collection: dict | None = None (schema: {out_dir, hooks:
  [{name, module_path, hook_type, collect_every_n_steps}]})
    - _run_multi wraps the batch loop in _maybe_activation_buffer(), calling
  on_design_start/on_design_end around each _model_forward.
    - _get_shadow_model() resolves the EMA shadow through the Fabric wrapper. sae is imported
  lazily so rfd3 still runs without the extra.

## train

```sh
python -m sae.train  activations_path=/mnt/nw/home/m.yu/repos/foundry/tutorials/rfd3_na_tutorial/activations/activations.h5 architecture=matryoshka_batch_top_k hook_name=block12 use_wandb=true save_checkpoints=true
```
## eval
```sh
python -m sae.eval checkpoint_path=/mnt/nw/home/m.yu/repos/foundry/outputs/matryoshka_batch_top_k/block12/2026-04-13_06-11-59/final.pt num_features=12 top_residues=5
```