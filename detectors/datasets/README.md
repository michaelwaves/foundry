  Positives (hazards):

  ┌─────────────────────────┬──────────────┬──────────────┬──────────────────────────────────┐
  │         Script          │    Source    │    Count     │              Notes               │
  ├─────────────────────────┼──────────────┼──────────────┼──────────────────────────────────┤
  │                         │              │              │ The exact SafeBench-Seq positive │
  │ download_safeprotein.sh │ SafeProtein  │ 429 proteins │  class — sequences shipped in    │
  │                         │              │              │ the JSON, no UniProt round-trip  │
  ├─────────────────────────┼──────────────┼──────────────┼──────────────────────────────────┤
  │ download_toxinpred3.sh  │ ToxinPred 3  │ 5,518        │ Has both classes                 │
  │                         │              │ peptides     │                                  │
  ├─────────────────────────┼──────────────┼──────────────┼──────────────────────────────────┤
  │                         │              │ 1.9–8.2K     │                                  │
  │ download_toxinpred2.sh  │ ToxinPred 2  │ proteins per │ Has both classes                 │
  │                         │              │  split       │                                  │
  ├─────────────────────────┼──────────────┼──────────────┼──────────────────────────────────┤
  │ download_vfdb.sh        │ VFDB         │ 4,623 (core) │ Bacterial virulence factors      │
  ├─────────────────────────┼──────────────┼──────────────┼──────────────────────────────────┤
  │ download_ncbi_viral.sh  │ NCBI viral   │ hundreds of  │ Pure viral; large download (~106 │
  │                         │ RefSeq       │ K            │  MB)                             │
  └─────────────────────────┴──────────────┴──────────────┴──────────────────────────────────┘

  Negatives (benigns):

  ┌─────────────────────────────┬───────────────────────────────┬──────────────────────────────┐
  │           Script            │            Filter             │            Notes             │
  ├─────────────────────────────┼───────────────────────────────┼──────────────────────────────┤
  │                             │ reviewed:true NOT KW-0800     │ Tested, paginates 500/page,  │
  │ download_uniprot_benigns.sh │ (Toxin) NOT KW-0843           │ matches SafeBench-Seq + your │
  │                             │ (Virulence) NOT               │  stricter virulence          │
  │                             │ taxonomy:10239 (Viruses)      │ exclusion                    │
  ├─────────────────────────────┼───────────────────────────────┼──────────────────────────────┤
  │ ToxinPred negatives         │ NOT keyword:toxin             │ Already balanced with their  │
  │                             │                               │ positives                    │
  └─────────────────────────────┴───────────────────────────────┴──────────────────────────────┘