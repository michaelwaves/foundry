
  # 1. positives (429 hazards, ~50 MB of PDBs)
  datasets/download_safeprotein.sh
  tutorials/sae_data_rfd3_partial/fetch_safeprotein_pdbs.sh

  # 2. benigns (~200 length-matched, ~5–20 MB of PDBs)

  datasets/download_uniprot_pdb_benigns.sh 500 100 300
  //n_pdbs, min_len, max_len


  # 3. merge into one sources.csv
  tail -n +2 detesure lctors/datasets/uniprot_pdb_benigns/sources.csv \
    >> tutorials/sae_data_rfd3_partial/sources.csv

    3b. filter to <300 residues to prevent oom on l40

  # 4. run partial-diffusion collection (5 Å noise default)
  PARTIAL_T=5.0 tutorials/sae_data_rfd3_partial/collect_train.sh 