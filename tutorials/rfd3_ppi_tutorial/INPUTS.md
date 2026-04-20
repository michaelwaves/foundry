  Top-level inputs keys                                                                             
                                                                                                    
  ┌─────────────────────────────┬──────────────┬────────────────────────────────────────────────┐   
  │             Key             │     Type     │                    Meaning                     │   
  ├─────────────────────────────┼──────────────┼────────────────────────────────────────────────┤   
  │                             │              │ Unique ID for this design (e.g.                │ 
  │ example_id                  │ str          │ "ppi_tutorial_insulinr_0"). Used for output    │ 
  │                             │              │ filenames.                                     │   
  ├─────────────────────────────┼──────────────┼────────────────────────────────────────────────┤
  │ feats                       │ dict[str,    │ All model input features (see below).          │   
  │                             │ Tensor]      │                                                │
  ├─────────────────────────────┼──────────────┼────────────────────────────────────────────────┤   
  │ t                           │ Tensor       │ Current diffusion timestep (sampled during     │   
  │                             │              │ training; initial timestep at inference).      │
  ├─────────────────────────────┼──────────────┼────────────────────────────────────────────────┤   
  │ noise                       │ Tensor       │ Sampled Gaussian noise added to clean coords   │   
  │                             │              │ to produce the noised input.                   │
  ├─────────────────────────────┼──────────────┼────────────────────────────────────────────────┤   
  │ ground_truth                │ dict         │ GT coordinates + sequence used for loss /      │   
  │                             │              │ reference (see below).                         │
  ├─────────────────────────────┼──────────────┼────────────────────────────────────────────────┤   
  │ coord_atom_lvl_to_be_noised │ Tensor       │ The atom-level coords that will actually be    │   
  │                             │ [N_atoms, 3] │ noised (fixed-motif atoms are excluded).       │
  ├─────────────────────────────┼──────────────┼────────────────────────────────────────────────┤   
  │ sampled_condition_name      │ str/None     │ Which conditioning regime was sampled (e.g.    │
  │                             │              │ for classifier-free guidance). None here.      │   
  ├─────────────────────────────┼──────────────┼────────────────────────────────────────────────┤
  │ atom_array                  │ biotite      │ Structural scaffold for reconstructing         │   
  │                             │ AtomArray    │ outputs; (2483,) = 2483 atoms.                 │   
  ├─────────────────────────────┼──────────────┼────────────────────────────────────────────────┤
  │ specification               │ dict         │ The design spec from the input JSON (what the  │   
  │                             │              │ user asked for).                               │   
  └─────────────────────────────┴──────────────┴────────────────────────────────────────────────┘
                                                                                                    
  specification — what you asked the model to design                                                
   
  ┌─────────────────────────┬──────────────────────┬─────────────────────────────────────────────┐  
  │          Field          │       Example        │                   Meaning                   │
  ├─────────────────────────┼──────────────────────┼─────────────────────────────────────────────┤
  │ input                   │ .../4zxb_cropped.pdb │ Input PDB providing the motif.              │
  Field: contig                                                                                   
  Example: '40-120,/0,E6-155'                                                                       
  Meaning: Contig string: design 40-120 residues, chain break, then fix chain E residues 6–155.     
  ────────────────────────────────────────                                                          
  Field: length                                                                                     
  Example: '190-270'                                                                                
  Meaning: Total designed length range.                                                           
  ────────────────────────────────────────                                                          
  Field: extra                                                                                    
  Example: dict                                                                                     
  Meaning: Sampling bookkeeping: sampled_contig (the concrete contig chosen), num_tokens_in=239,  
    num_residues_in=239, num_chains=2, num_atoms=1682, num_residues=152.                            
  ────────────────────────────────────────                                                        
  Field: select_fixed_atoms                                                                         
  Example: True                                                                                   
  Meaning: Whether fixed-motif atoms are selected for their coords to be hard-fixed.                
  ────────────────────────────────────────                                                        
  Field: select_unfixed_sequence                                                                    
  Example: False                                                  
  Meaning: Whether motif sequence identity is free (here it's kept).                                
  ────────────────────────────────────────
  Field: select_hotspots                                                                            
  Example: {'E64': 'CD2,CZ', ...}                                 
  Meaning: Hotspot atoms on the target the binder should contact.
  ────────────────────────────────────────
  Field: infer_ori_strategy                                                                         
  Example: —
  Meaning: Strategy for inferring orientation of designed chain.                                    
  ────────────────────────────────────────                        
  Field: is_non_loopy                                                                               
  Example: —
  Meaning: Whether to enforce non-loopy (SSE-biased) structure.                                     
                                                                  
  feats — model input features

  Broad groups (2483 atoms, ~N_tokens tokens; batched size 8):                                      
  
  Token identity / indexing                                                                         
  - residue_index, token_index — positional indices.              
  - asym_id, entity_id, sym_id — chain / entity / symmetry IDs.                                     
  - restype — AA type (one-hot or int).                        
  - is_protein, is_rna, is_dna, is_ligand — token-type masks.                                       
  - terminus_type — N-/C-term / internal.                         
  - is_polar — physicochemical bit.                                                                 
                                                                                                    
  Reference (motif) atom info — ref_* features describe the fixed-motif atoms as known priors:      
  - ref_pos [B, N_atoms, 3] — fixed reference coordinates (that torch.Size([8, 2483, 3]) you saw is 
  almost certainly ref_pos or coord_atom_lvl).                                                      
  - ref_mask — which reference atoms are valid.                                                     
  - ref_element, ref_charge, ref_atom_name_chars — chemistry.                                       
  - ref_space_uid — per-residue identity for splitting rigid groups.                                
  - ref_pos_is_ground_truth — marks which ref positions are actual GT (vs. templated).
  - ref_is_motif_atom_with_fixed_coord / ref_is_motif_atom_unindexed / ref_motif_token_type — motif 
  flags on the reference side.                                                                      
  - motif_pos — explicit motif coords.                                                              
  - ref_atomwise_rasa, ref_plddt — per-atom surface area / pLDDT priors.                            
                                                                                                    
  Per-atom role flags                                                                               
  - is_backbone, is_sidechain, is_virtual, is_central, is_ca — atom roles.                          
  - is_motif_atom_with_fixed_coord — atom's coord is hard-fixed.                                    
  - is_motif_atom_with_fixed_seq — atom's residue identity is fixed.                                
  - is_motif_atom_unindexed — motif atom without a specific residue index (free placement).         
  - is_motif_token_with_fully_fixed_coord — token-level flag.                                       
  - is_atom_level_hotspot — derived from your select_hotspots.                                      
  - is_non_loopy — non-loop bias flag.                                                              
                                                                                                    
  Chemistry conditioning                                                                            
  - active_donor, active_acceptor — H-bond donor/acceptor flags.                                    
                                                                                                    
  Graph structure                                                 
  - token_bonds — token-level bond adjacency.                                                       
  - atom_to_token_map — [N_atoms] → token idx (how atoms group into tokens).                        
  
  Masks                                                                                             
  - unindexing_pair_mask, is_motif_token_unindexed, has_zero_occupancy — validity masks.
                                                                                                    
  ground_truth — targets for loss                                 
                                                                                                    
  ┌─────────────────────────────┬────────────────────────────────────────────────────────────────┐  
  │             Key             │                            Meaning                             │
  ├─────────────────────────────┼────────────────────────────────────────────────────────────────┤  
  │ is_original_unindexed_token │ Marks tokens that had no fixed index in the input.             │
  ├─────────────────────────────┼────────────────────────────────────────────────────────────────┤
  │ sequence_gt_I               │ Integer-encoded GT sequence.                                   │  
  ├─────────────────────────────┼────────────────────────────────────────────────────────────────┤
  │ sequence_valid_mask         │ Which positions have valid GT sequence.                        │  
  ├─────────────────────────────┼────────────────────────────────────────────────────────────────┤
  │ coord_atom_lvl              │ GT atom coordinates [B, N_atoms, 3] — this is likely the [8,   │
  │                             │ 2483, 3] tensor.                                               │  
  ├─────────────────────────────┼────────────────────────────────────────────────────────────────┤
  │ mask_atom_lvl               │ Validity mask for GT coords.                                   │  
  ├─────────────────────────────┼────────────────────────────────────────────────────────────────┤
  │ chain_iid_token_lvl         │ Per-token chain instance ID.                                   │
  └─────────────────────────────┴────────────────────────────────────────────────────────────────┘  
  
  Putting it together for your case                                                                 
                                                                  
  - Batch size 8, 2483 atoms, ~152 residues GT / 239 input tokens (motif = chain E 6–155 + target   
  scaffold).                                                      
  - Contig 40-120,/0,E6-155 = "design 40–120-residue binder, chain break, keep the target chain E   
  residues 6–155 fixed."                                                                            
  - 3 hotspots on the target (E64, E88, E96) tell the model where on chain E the binder should
  interact, narrowed to specific sidechain atoms.                                                   
  - At inference, coord_atom_lvl_to_be_noised is what actually gets noised each diffusion step;
  ref_is_motif_atom_with_fixed_coord == True atoms are held fixed throughout.                       
                                                                  
  Step into self._model_forward(pipeline_output) on line 284 to see how these get consumed.    