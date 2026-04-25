                                                                                                  
  - L = number of atoms (atom14 expansion: ~14 entries per residue, with virtual placeholders)    
  - I = number of tokens (one per residue / nucleotide / ligand atom)                             
  - atom_to_token_map: [L,] is the bridge between them.                                           
                                                                                                  
  Sources: configs/model/components/rfd3_net.yaml:22-43 (the embedder feature lists),             
  transforms/util_transforms.py, transforms/design_transforms.py, transforms/conditioning_base.py,
   and model/layers/encoders.py.                                                                  
                                                                  
  Bridge / indexing

  ┌───────────────────┬─────────┬─────────────────────────────────────────────────────────────┐   
  │        key        │  shape  │                           meaning                           │
  ├───────────────────┼─────────┼─────────────────────────────────────────────────────────────┤   
  │ atom_to_token_map │ [L,]    │ maps each atom → its token id; the only key that lets you   │
  │                   │ int     │ cross between the two axes                                  │
  └───────────────────┴─────────┴─────────────────────────────────────────────────────────────┘   
  
  Token-level (shape [I, ...])                                                                    
                                                                  
  Identity & chain layout                                                                         
  
  ┌───────────────┬────────┬───────────────────────────────────────────────────────────────────┐  
  │      key      │ shape  │                              meaning                              │
  ├───────────────┼────────┼───────────────────────────────────────────────────────────────────┤
  │ restype       │ [I,    │ AF3 token-vocab index (20 AAs + 4 NA bases + ligand/special);     │
  │               │ 32]    │ also the GT target for the sequence head                          │
  ├───────────────┼────────┼───────────────────────────────────────────────────────────────────┤  
  │ residue_index │ [I,]   │ residue number within chain (PDB-style numbering)                 │
  ├───────────────┼────────┼───────────────────────────────────────────────────────────────────┤  
  │ token_index   │ [I,]   │ global token index                                                │
  ├───────────────┼────────┼───────────────────────────────────────────────────────────────────┤  
  │ asym_id       │ [I,]   │ chain id (asymmetric unit)                                        │
  ├───────────────┼────────┼───────────────────────────────────────────────────────────────────┤  
  │ entity_id     │ [I,]   │ distinct biological-entity id; copies of the same chain share     │
  │               │        │ this                                                              │  
  ├───────────────┼────────┼───────────────────────────────────────────────────────────────────┤
  │ sym_id        │ [I,]   │ symmetry-mate id within an entity                                 │  
  ├───────────────┼────────┼───────────────────────────────────────────────────────────────────┤
  │ terminus_type │ [I, 2] │ one-hot of (is_C_terminus, is_N_terminus)                         │
  │               │        │ (util_transforms.py:461-489)                                      │  
  └───────────────┴────────┴───────────────────────────────────────────────────────────────────┘
                                                                                                  
  Molecule-type one-hots                                                                          
  
  ┌──────────────────────────┬─────────┬──────────────────────────────────────────────────────┐   
  │           key            │  shape  │                       meaning                        │
  ├──────────────────────────┼─────────┼──────────────────────────────────────────────────────┤
  │ is_protein, is_rna,      │ [I,]    │ mutually-exclusive token class flags                 │
  │ is_dna, is_ligand        │ bool    │                                                      │
  ├──────────────────────────┼─────────┼──────────────────────────────────────────────────────┤   
  │ is_polar                 │ [I,]    │ polar residue flag (broadcast to atoms via tok_idx   │   
  │                          │ bool    │ in DiffusionLoss, losses.py:101)                     │   
  └──────────────────────────┴─────────┴──────────────────────────────────────────────────────┘   
                                                                  
  Motif / conditioning at the token level                                                         
  
  ┌───────────────────────────────────────┬───────┬───────────────────────────────────────────┐   
  │                  key                  │ shape │                  meaning                  │
  ├───────────────────────────────────────┼───────┼───────────────────────────────────────────┤
  │                                       │ [I,]  │ motif token whose residue index is not    │
  │ is_motif_token_unindexed              │ bool  │ fixed (free-floating placement) — set in  │
  │                                       │       │ conditioning_base.py:506                  │   
  ├───────────────────────────────────────┼───────┼───────────────────────────────────────────┤
  │ is_motif_token_with_fully_fixed_coord │ [I,]  │ every atom in the token has a fixed coord │   
  │                                       │ bool  │  (design_transforms.py:484)               │   
  ├───────────────────────────────────────┼───────┼───────────────────────────────────────────┤
  │ is_central                            │ [I,]  │ "central" token mask (used as a           │   
  │                                       │ bool  │ representative atom indicator)            │   
  ├───────────────────────────────────────┼───────┼───────────────────────────────────────────┤
  │                                       │       │ 3-class motif type (regular /             │   
  │ ref_motif_token_type                  │ [I,   │ indexed-motif / unindexed-motif), see     │   
  │                                       │ 3]    │ design_transforms.py:211-214; embedded as │
  │                                       │       │  a token 1d feature (rfd3_net.yaml:23)    │   
  ├───────────────────────────────────────┼───────┼───────────────────────────────────────────┤ 
  │ ref_plddt                             │ [I,   │ per-token pLDDT prior (used as            │
  │                                       │ 1]    │ conditioning)                             │   
  ├───────────────────────────────────────┼───────┼───────────────────────────────────────────┤
  │                                       │ [I,   │ rigid-backbone hint, values {-1, 0, 1}    │   
  │ is_non_loopy                          │ 1]    │ (ppi_transforms.py:135-143) — what your   │   
  │                                       │       │ selected line in the YAML toggles         │
  └───────────────────────────────────────┴───────┴───────────────────────────────────────────┘   
                                                                                                
  Atom-level (shape [L, ...])                                                                     
  
  Reference chemistry (the "what kind of atom is this")                                           
                                                                                                
  ┌─────────────────────────┬──────────────────┬──────────────────────────────────────────────┐   
  │           key           │      shape       │                   meaning                    │ 
  ├─────────────────────────┼──────────────────┼──────────────────────────────────────────────┤
  │                         │ [L, 4, 64] →     │ one-hot of the 4 ASCII chars of the atom     │
  │ ref_atom_name_chars     │ reshaped to [L,  │ name (e.g. " CA ")                           │
  │                         │ 256] at line 178 │                                              │   
  ├─────────────────────────┼──────────────────┼──────────────────────────────────────────────┤
  │ ref_element             │ [L, 128]         │ one-hot of element symbol                    │   
  ├─────────────────────────┼──────────────────┼──────────────────────────────────────────────┤ 
  │ ref_charge              │ [L, 1]           │ formal charge                                │   
  ├─────────────────────────┼──────────────────┼──────────────────────────────────────────────┤
  │                         │                  │ idealized reference coordinates (used in     │   
  │ ref_pos                 │ [L, 3]           │ ref_pos_embedder for relative-distance pair  │ 
  │                         │                  │ features)                                    │   
  ├─────────────────────────┼──────────────────┼──────────────────────────────────────────────┤ 
  │ ref_mask                │ [L, 1] bool      │ atom is valid/present in the reference       │
  ├─────────────────────────┼──────────────────┼──────────────────────────────────────────────┤   
  │                         │                  │ reference-space partition id; pairs with     │
  │ ref_space_uid           │ [L,] int         │ same uid share a reference frame (used by    │   
  │                         │                  │ ref_pos_embedder_tok, encoders.py:203)       │ 
  ├─────────────────────────┼──────────────────┼──────────────────────────────────────────────┤   
  │ ref_pos_is_ground_truth │ [L,] bool        │ distinguishes GT-derived reference coords    │ 
  │                         │                  │ from idealized templates                     │   
  ├─────────────────────────┼──────────────────┼──────────────────────────────────────────────┤
  │ has_zero_occupancy      │ [L, 1] bool      │ atom has zero occupancy in the source PDB    │   
  └─────────────────────────┴──────────────────┴──────────────────────────────────────────────┘   
  
  Structural categories                                                                           
                                                                                                
  ┌──────────────┬─────────┬──────────────────────────────────────────────────────────────────┐
  │     key      │  shape  │                             meaning                              │
  ├──────────────┼─────────┼──────────────────────────────────────────────────────────────────┤   
  │ is_backbone  │ [L,]    │ N, CA, C, O                                                      │
  │              │ bool    │                                                                  │   
  ├──────────────┼─────────┼──────────────────────────────────────────────────────────────────┤ 
  │ is_sidechain │ [L,]    │ sidechain atoms (excluding virtual; see losses.py:104-105)       │   
  │              │ bool    │                                                                  │
  ├──────────────┼─────────┼──────────────────────────────────────────────────────────────────┤   
  │ is_virtual   │ [L,]    │ virtual placeholder atoms (V0...V8); element name VX per         │ 
  │              │ bool    │ constants.py:178                                                 │   
  ├──────────────┼─────────┼──────────────────────────────────────────────────────────────────┤ 
  │ is_ca        │ [L,]    │ alpha-carbon mask — heavily used to project atom features down   │
  │              │ bool    │ to one-per-residue                                               │   
  └──────────────┴─────────┴──────────────────────────────────────────────────────────────────┘
                                                                                                  
  Atom-level motif / conditioning                                                                 
  
  ┌────────────────────────────────────┬────────┬─────────────────────────────────────────────┐   
  │                key                 │ shape  │                   meaning                   │ 
  ├────────────────────────────────────┼────────┼─────────────────────────────────────────────┤
  │ ref_is_motif_atom_with_fixed_coord │ [L, 1] │ reference-frame motif mask, used as 1d      │
  │                                    │  bool  │ embedding feature (rfd3_net.yaml:34)        │
  ├────────────────────────────────────┼────────┼─────────────────────────────────────────────┤   
  │ ref_is_motif_atom_unindexed        │ [L, 1] │ reference-frame mask for unindexed motif    │
  │                                    │  bool  │ atoms                                       │   
  ├────────────────────────────────────┼────────┼─────────────────────────────────────────────┤ 
  │ is_motif_atom_with_fixed_coord     │ [L,]   │ runtime mask used by sampler to freeze      │   
  │                                    │ bool   │ coords (inference_sampler.py:164)           │   
  ├────────────────────────────────────┼────────┼─────────────────────────────────────────────┤
  │ is_motif_atom_with_fixed_seq       │ [L,]   │ sequence-fixed motif (atoms whose residue   │   
  │                                    │ bool   │ identity is conditioning)                   │   
  ├────────────────────────────────────┼────────┼─────────────────────────────────────────────┤
  │ is_motif_atom_unindexed            │ [L,]   │ unindexed motif at atom level               │   
  │                                    │ bool   │                                             │   
  ├────────────────────────────────────┼────────┼─────────────────────────────────────────────┤
  │ motif_pos                          │ [L, 3] │ GT motif coordinates (zeroed for non-motif; │   
  │                                    │        │  design_transforms.py:220-221, 306)         │   
  └────────────────────────────────────┴────────┴─────────────────────────────────────────────┘
                                                                                                  
  Guided / task-specific hints (the "design knobs")                                               
  
  ┌───────────────────────┬──────────┬────────────────────────────────────────────────────────┐   
  │          key          │  shape   │                        meaning                         │ 
  ├───────────────────────┼──────────┼────────────────────────────────────────────────────────┤
  │ ref_atomwise_rasa     │ [L, 3]   │ one-hot bin of relative accessible surface area (used  │
  │                       │          │ to bias core/surface design)                           │
  ├───────────────────────┼──────────┼────────────────────────────────────────────────────────┤   
  │ active_donor          │ [L, 1]   │ atom is an active H-bond donor (NA-binding tasks)      │
  │                       │ bool     │                                                        │   
  ├───────────────────────┼──────────┼────────────────────────────────────────────────────────┤ 
  │ active_acceptor       │ [L, 1]   │ atom is an active H-bond acceptor                      │   
  │                       │ bool     │                                                        │   
  ├───────────────────────┼──────────┼────────────────────────────────────────────────────────┤
  │ is_atom_level_hotspot │ [L, 1]   │ hotspot atom (PPI design — ppi_transforms.py:300)      │   
  │                       │ bool     │                                                        │   
  └───────────────────────┴──────────┴────────────────────────────────────────────────────────┘
                                                                                                  
  These four are the optional channels the ARCHITECTURE.md calls out: PPI tasks use               
  hotspot/donor/acceptor; monomer design uses neither; RASA is a generic surface-vs-core knob.
                                                                                                  
  Pair-level                                                                                    

  ┌──────────────────────┬────────┬───────────────────────────────────────────────────────────┐
  │         key          │ shape  │                          meaning                          │
  ├──────────────────────┼────────┼───────────────────────────────────────────────────────────┤   
  │ token_bonds          │ [I, I] │ bonded token pairs; embedded into Z_init_II via           │
  │                      │  bool  │ process_token_bonds (encoders.py:198-200)                 │   
  ├──────────────────────┼────────┼───────────────────────────────────────────────────────────┤   
  │                      │        │ pairs where exactly one side is unindexed (so the model   │
  │ unindexing_pair_mask │ [I, I] │ can ignore positional comparisons across that boundary) — │   
  │                      │  bool  │  built in conditioning_base.py:444-453 and stored at line │ 
  │                      │        │  505                                                      │   
  └──────────────────────┴────────┴───────────────────────────────────────────────────────────┘ 

  Quick mental model

  - Atom-level features answer "what atom is this and is its position/identity locked?"           
  - Token-level features answer "what residue/unit is this, what chain does it belong to, and is
  its identity/position constrained?"                                                             
  - *_motif_* keys are the conditioning surface — pick which atoms/tokens you're keeping fixed, 
  indexed vs. unindexed, coord-only vs. coord+seq.                                                
  - ref_* keys are the static reference frame (idealized geometry, chemistry, GT-ness flags).   
  - Guided keys (active_donor, active_acceptor, is_atom_level_hotspot, ref_atomwise_rasa,         
  ref_plddt, is_non_loopy) are optional dials that turn on per-task — that's why your             
  ppi_tutorial.yaml line 10 sets is_non_loopy: true: it's flipping a token-level conditioning     
  feature that the embedder reads.                                                                
                                                                                         