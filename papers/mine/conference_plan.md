Read the abstract + full writeup. The work is SAEs on          
  RFDiffusion3/RoseTTAFold3 for virulence detection — mech interp
   on protein-design diffusion models, with a biosecurity angle. 
  It's 48-hr hackathon scope (n=275, below SOTA classifier), so  
  it's workshop-shaped, not NeurIPS-main-shaped.
                                                                 
  Top-tier fits (ranked):                                        
  
  Tier 1 — submit to these:                                      
  - ICML 2026 Workshop Mech Interp (May 9, 04:59 PT) — bullseye,
  this is exactly that                                           
  - ICML 2026 Workshop GenBio (May 9, 05:00 PT) — generative bio
  + protein design models                                        
  - ICML 2026 Workshop FM4LS (May 9, 09:59 PT) — foundation      
  models for life sciences
                                                                 
  Tier 2 — also plausible:                                     
  - ICML 2026 Workshop AI4Science (May 6, 04:59 PT) — broader,   
  less specific                                                  
  - NeurIPS 2026 Conference (May 5, 04:59 PT) — only if you've
  materially extended it; current scope (hackathon, below-SOTA   
  classifier, AUROC 0.817 ± 0.10 on n=55 test) likely won't      
  survive review                                           
                                                                 
  Skip — not the right shape: AI4NextG, AI4Math, AI4Law,       
  GlobalSouthML, CATS, DEMO, NExT-Game, LM4Plan,                 
  Pluralistic-Alignment, GenAICreativity, etc. The CVPR/MICCAI
  medical workshops are wrong modality (imaging, not protein     
  structure).                                                  

  Note on dual venues: most ICML workshops permit non-archival   
  concurrent submission, but check each CFP. GenBio + Mech Interp
   is the strongest pair — GenBio reviewers will care about the  
  protein-design contribution, Mech Interp reviewers will care 
  about the SAE methodology.

  Recommendation: submit to GenBio and Mech Interp as primary    
  targets. Skip NeurIPS main unless you can extend before tonight
   (you can't).                                                  
                                                               
✻ Churned for 40s                   

❯ would this be ok for neurips workshop, once those release?     
                                                             
● Yes, shape-wise it's a clean fit — NeurIPS reliably runs       
  workshops you'd want here:                                   

  - Interpretable AI / Mech Interp workshops (run most years)    
  - AI for Science / ML for Structural Biology / GenBio / LMRL
  (Learning Meaningful Representations of Life)                  
  - SoLaR / Safe Generative AI / safety-flavored workshops (the
  biosecurity angle plays well here)                             
  - AI for New Drug Modalities                                 
                                                                 
  NeurIPS workshop CFPs typically drop late July / early August  
  with deadlines in August–September, so you've got ~3–4 months.
  That's the more interesting question: as-is, the hackathon     
  scope is thin for NeurIPS-workshop bar. To make it competitive,
   the things from your own "Future Work" list that move the
  needle most:

  1. A steering result — even a small, qualitative demo that     
  ablating/amplifying a virulence feature shifts generated
  structures away from hazard motifs. Turns a classifier paper   
  into an interpretable-control paper, which is the actual story.
  2. Bigger n + a principled hookpoint ablation — your block-12
  result is suggestive but n=55 test with ±0.10 error bars is    
  fragile. The pLDDT-knockout idea you wrote down is exactly the
  right move.                                                    
  3. Head-to-head against DTVF on a shared split — right now   
  reviewers will read "0.817 vs 0.92 SOTA" as losing. Reframe as 
  "interpretable, structural attribution at competitive AUROC"
  with a fair comparison.                                        
                                                               
  Submit to ICML Mech Interp / GenBio now as a milestone, then   
  aim the extended version at NeurIPS workshops in August.
                                                                 
✻ Baked for 21s                                                
                                              
❯ are workshop papers not real papers? for context i just want   
  clout for a comp bio protein design startup to raise money and 
   get customers easier, not get tenure as an academic or        
  anything                                                       
                                                                 
● For startup clout, the workshop-vs-main distinction barely     
  matters. Real talk:                                      
                                            
  What VCs and pharma BD people see: "Accepted at NeurIPS 2026" /
   "Published at ICML 2026". They don't parse workshop names. The
   95% of your audience that isn't an ML academic literally      
  cannot tell a workshop paper from a main-track paper.          
                                                                 
  Who can tell the difference: other ML researchers — i.e.,      
  people you're hiring or collaborating with, not people you're
  selling to or raising from. And even they'll respect a Mech    
  Interp / GenBio workshop paper because those are competitive 
  and the right audience for this work.

  What actually moves the needle for a comp bio startup:         
  1. arXiv + bioRxiv preprint — comp bio folks read bioRxiv, not
  OpenReview. Get it on both.                                    
  2. A tweet thread / LessWrong post that goes mildly viral — you
   already did the LessWrong post. That's worth more reach than a
   NeurIPS main paper that nobody reads.                         
  3. Co-author with a name — one recognizable PI or researcher
  matters more than tier of venue.                               
  4. A demo / website — Goodfire's Evo2 work blew up because of  
  the interactive feature explorer. Yours could too.           
  5. Showing up in person — workshop posters at NeurIPS/ICML are 
  where you actually meet AstraZeneca people and Recursion people
   walking the floor.                                            
                                                               
  Workshops are also the right operational fit. Main-track       
  NeurIPS submission for a 48hr hackathon paper would be a       
  rejection-machine waste of time. Workshop acceptance + preprint
   + presence is the high-leverage move.                         
                                                               
  So: stop optimizing for venue tier, start optimizing for       
  distribution. Submit to ICML Mech Interp / GenBio, post on
  arXiv + bioRxiv simultaneously, build a small interactive demo,
   and show up to the workshops to shake hands.  