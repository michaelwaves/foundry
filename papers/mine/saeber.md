LESSWRONG
SAEBER: Sparse Autoencoders for Biological Entity Risk
9 min read
•
Abstract
•
Website
•
Introduction
•
Related Work
•
Sparse AutoEncoders
•
Methods
•
Results
•
Limitations
•
Future Work
•
Conclusion
+
AI
Frontpage
8
SAEBER: Sparse Autoencoders for Biological Entity Risk
by michaelwaves
28th Apr 2026
TLDR: Sparse Autoencoders (SAEs) trained on protein folding and design models find features correlated with virulent proteins, while logistic regression probes trained on both SAE encoded and raw model activations approach SOTA classifiers on virulent vs benign proteins

Abstract
Protein design and folding models are powerful tools that could be misused to design virulent or toxic proteins. Existing biosecurity screens operate on sequence similarity or structural homology and offer little insight into why a protein is flagged as hazardous. We apply mechanistic interpretability techniques to RFDiffusion3 and RoseTTAFold3 for the first time, training Matryoshka BatchTopK Sparse Autoencoders (SAEs) on intermediate activations collected during the diffusion and folding processes. Using a length-matched dataset of 275 sequences drawn from SafeProtein and UniProt, we train logistic regression probes on both raw and SAE-encoded activations to classify designs as virulent or benign, and we score individual SAE features for hazard association using univariate AUROC with Benjamini-Hochberg FDR correction. Our best probe, trained on SAE features from block 12 of RFDiffusion3, achieves an AUROC of 0.817 ± 0.10 under homology-clustered splits, outperforming the corresponding raw-activation probe by +0.054 AUROC. We also identify individual SAE features that fire on virulent designs at up to ~0.8 AUROC, with feature quality increasing with layer depth. While our classifier does not surpass the current SOTA (DTVF, 0.92 AUROC), it is the first method to provide structural, feature-level explanations for virulence predictions in a protein design model, opening the door to runtime monitoring, steering, and interpretable guardrails during generation.

Activations
RFD3
RF3
SAEs:
RF3
RFD3
Probes
Homology Clustered (RFD3 + RF3)
Random (RFD3 + RFD)
Website

image.png


Introduction
Protein folding and design models are powerful tools but can be misused, for instance to assist in the generation of virulent or toxic proteins. Previous works screen proteins based on sequence similarity and structure, or at the DNA level. Unfortunately, these methods are often not explainable.

In this work, we apply interpretability techniques to RFDiffusion3 (RFD3) and RoseTTAFold3 (RF3) to classify and interpret model behavior on virulent proteins. We build a framework to collect the intermediate calculations (activations) during the diffusion process and train classifiers on both raw and SAE activations to determine if the model is designing around virulent motifs.

We also train Matryoshka BatchTopK Sparse AutoEncoders (SAEs) to attribute which structural features of proteins are associated with virulence. 

Finally, we benchmark the efficacy of using SAE activations vs raw activations to classify proteins as harmful or benign, as well as against other methods.

Our contributions are the following:

A suite of SAEs trained on RFD3 and RF3.
A small database of SAE features correlated with virulence in proteins.
Benchmarking raw vs SAE activations for harmful protein classification.
Related Work
FoldSAE is the closest work, where the authors trained SAEs on RFDiffusion. However, they mainly discovered simple features predicting secondary structure (alpha helices and beta sheets). Also, RFDiffusion3 shares no code with its predecessor and operates on individual atoms instead of only on tokens (amino acids). Our work extends FoldSAE to all atom diffusion models for the first time and uses it to predict virulence features. 

InterProt and InterPLM are trained on protein language models such as ESM, but not diffusion based protein design models. Goodfire has trained SAEs on Evo 2, and done similar diffusion generation interpretability on MatterGen, a materials design model.

The existing SOTA for virulence classification is DTVF (2024). They used a benchmark dataset containing 576 VFs and 576 non-VFs for independent testing, following DeepVF's method to construct the same independent test set. They achieved an AUROC of 0.92, which represents a significant 8.57% improvement over the latest VF-Pred model released in 2024. Across four metrics of accuracy, F1-Score, specificity, and AUROC, the DTVF model surpasses the most recent models, with 1% increase in accuracy and 3.89% enhancement in specificity compared to VF-Pred.

VirulentHunter (2025) also shows strong performance with AUC improvements of 48% and 68% over MP4 and DeepVF respectively, though it doesn't report absolute AUROC values for direct comparison with DTVF's 0.92.

Sparse AutoEncoders
A Sparse Autoencoder is an autoencoder that projects activations into a higher dimension and back to the original dimension, decomposing polysemantic activation vector positions into sparse, ideally monosemantic features. It is trained with both a reconstruction loss and sparsity penalty for regularization. Formally, it consists of an encoder matrix  and decoder matrix  with an activation function , where . Let  be the input activation vector from RFD3 or RF3, z be the sparse activation vector after projection through  and activation function, and 
 be the reconstructed vector.

Then the forward pass is

And the reconstruction loss is

The sparsity penalty is typically implemented as a regularization term:

where λ is the sparsity coefficient that controls the trade-off between reconstruction quality and sparsity. Conceptually, the model could just use all the channels of z to trivially reconstruct 
, but this defeats the purpose of finding sparse feature activations. Therefore, we give it a constraint by penalizing usage of many channels in z, at the cost of some reconstruction quality.

The total loss function is:

Matryoshka BatchTopK SAEs are an SAE variant that trains multiple nested subsets of the decoder columns and uses a top-k activation function. Given a list of p dictionary sizes  where , the model optimizes multiple reconstruction losses, each reconstructing 
 using a truncated subset of the columns in  and corresponding entries in z.

, the activation function, is the BatchTopK(X) function, where only the top K activations across the entire batch are kept active, with the rest set to zero. During training, it is the function

where τ (X) is the (B × K)th largest value in X across the batch of activations, ⊙ is element-wise multiplication, and 1[·] is the indicator function. However, during inference it is replaced with a learnable threshold theta to have consistent behavior regardless of batch.

This approach provides more direct control over sparsity levels and can mitigate feature absorption. They offer competitive performance to JumpReLU SAEs while being easier to train.

Methods
We use the foundry repository from RoseTTACommons to run RFD3 and RF3 and modify engine.py to optionally collect activations using user specified hooks.

All experiments can be run on a single L40 GPU or equivalent with at least 48GB VRAM.

We used SafeProtein (virulent only) + UniProt with filters NOT KW-0800 NOT KW-0843 NOT taxonomy_id:10239 AND length:100 TO 300 to construct positive and negative length-matched datasets for virulence. After filtering to sequences under 300 residues long (due to compute constraints), we have n=275 sequences.

We use the PDBs of the associated sequences as input motifs to RFDiffusion3, and set partial_t=5 to noise the motifs by 5 angstroms, denoising it back to a structure highly similar to the original motif. This simulates the activation distribution the model would output when denoising toxin-virus resembling proteins from scratch.

For RF3, we simply fold the sequences. We then wrote an ActivationBuffer to stream activations from hooks to disk in activations.h5.  

We collect activations from middle layer transition blocks of the diffusion transformer in RFD3 (blocks 6, 8, 12) and RF3 (blocks 12, 16). We then train Matryoshka BatchTopK SAEs.

We now have 2 activation caches saved to disk

RF3 activations (2 hooks)
diffusion_module.diffusion_transformer.blocks.12.conditioned_transition_block
diffusion_module.diffusion_transformer.blocks.16.conditioned_transition_block
RFD3 activations  (3 hooks)
diffusion_module.diffusion_transformer.blocks.6.transition_block
diffusion_module.diffusion_transformer.blocks.8.transition_block
diffusion_module.diffusion_transformer.blocks.12.transition_block
And 3 variables to sweep across

Hook point (2 for RF3, 3 for RFDiffusion)
Raw or SAE activations
Homologous clustering or not
We train 20 logistic regression probes (binary cross entropy with L2 weight decay) on per-design feature vectors, using n=220 out of the full 275 designs, reserving 55 for the test set. We also generate a homology clustered version of the splits with mmseqs2 easy-cluster at 30% sequence identity. This is to check that the model is not simply remembering proteins from similar evolutionary lineages. We also do a simple baseline regression on sequence length to check the that classifier is not relying on a trivial signal.

image.png


image.png


Independent of the probe sweep, we score every SAE feature against the full labels CSV using univariate AUROC. For the top-200 features by |AUROC - 0.5| we compute Mann-Whitney U p-values, then apply Benjamini-Hochberg FDR (False Discovery Rate) correction across all non-constant features to get q-values. BH correction matters because the dictionary has 12288 features and most carry no class information; without it the raw p-values would overstate significance. We treat features with q < 0.05 as discoveries.

For the top hazard-firing features we use PyMOL to render PNGs that highlight residues where the feature fires most strongly. We read the CIF, parse it with biotite, and map token index to (chain, residue) by chain order. Token count equals residue count for our full-protein partial-diffusion designs (no ligands or nucleic acids).

Results
image.png


As shown in Figure 1, the best performing classifier, controlling for family memorization with homologous clustering, was trained on RFD3 Block 12 SAE, with AUROC of 0.817 ± 0.10. This increases to 0.877 ± 0.03 without clustering, showing memorization of family folds in RFD3. Notably, performance on RFD3 block 6 decreases sharply to nearly random for homology clustering, suggesting this block strongly learns family representations. Also note that this is lower than the current SOTA of DTVF at 0.92. 

RFD3 memorizes more than RF3. In Figure 2, RFD3 has an average decrease of around 0.10 AUROC when controlling with clustering, while RF3 AUROC barely changes. However, overall they perform equally within the error bars.


image.png


Figure 3 shows the performance of classifiers trained on SAE activations vs raw activations. SAE activations underperform in most blocks, possibly due to the sparse activation vector having lower effective dimensionality than the dense, raw activations. Surprisingly, for block12 of RFD3 cluster split SAE activations outperform raw activations by +0.054 AUROC (0.817 vs 0.763). We hypothesize this is due to block 12 untangling complex polysemantic features that provide signal to the logistic regression probe, and this polysemanticity increases at later layers. Further work could investigate other deeper layers of RFD3 for interesting features.

image.png
Certain features fire above chance on positive class designs, up to ~0.8 AUROC. Also, the AUROC increases with layer depth, especially for RFD3, showing deeper layers have learned more meaningful features representing virulent proteins.

Limitations
The number of samples is very small due to time and compute constraints, only 220 designs in the train dataset and 55 in the test dataset, lowering statistical significance and perhaps causing underfitting
The layer selection was based on LLM transformer SAE literature, future work should do ablations and find hookpoints in more principled ways. For example, try to noise and denoise 100 virulent structures, then systematically knock out layers and see which one results in the biggest pLDDT (predicted Local Distance Difference Test) decrease.
Scope limitations. Due to limited GPU compute, we filtered to sequences <300 amino acids long, filtering out longer proteins from SafeProtein.
It would be interesting to breakdown the per category AUROC classification ( / etc.) but SafeProtein doesn't ship category labels, perhaps we could generate labels with external PFAM/InterPro
SAE feature classification/interpretation is extremely time consuming and requires lots of expert labor to look at highlighted PyMOL rendered PNGs and generate labels. Could perhaps use VLMs (vision language models) or crowdsource
The SAE feature scoring could be improved
i.e. Per-variant probe weight, per-fold attribution, diff-of-means visualization.
Future Work
Extend to more datasets such as Virulence Factor Database (VFDB), NCBI Viral,  or even new threat categories like toxicity prediction (ToxinPred3) and immune response (VaxiJen Series)
Optimize SAE trainer parameters like dict_size, k, and group_fractions, and benchmark different SAE types
Rerun experiments with more structures and bigger datasets, more layers
Explore steering and guardrails during protein design
Prevention and runtime monitoring: If we notice RFDiffusion3 is producing latents indicating it’s designing a potentially viral or toxic motif, we can terminate harmful diffusing trajectories 
Steering: We can steer away from viral/toxic directions in latent space to generate safer proteins
Use SAE activations like sparse embeddings to screen large datasets of sequences, as demonstrated by data centric interpretability work like Jiang et al and HypotheSAEs
Extend the SAE feature database to build something like Neuronpedia but for biology models
Cleanup the codebase and make documentation
Conclusion
Protein model interpretability is still an early and exciting research field. In this work, we show raw and SAE encoded activations from RF3 and RFD3 are useful for classifying virulent and benign proteins, with a maximum AUROC of 0.88. Although below SOTA methods such as DTVF for classification, this method pioneers interpretable classification that attributes virulence and toxicity of proteins to structural features of proteins. Future work includes using activations and SAE features to steer diffusion of protein design models away from harmful directions in latent space, finely control the design of proteins, and scan protein datasets.

Disclaimer: This research was done in 48 hours as part of the Apart Research AIxBIO Hackathon, and might be a little scuffed. Please let me know in the comments if there are any errors, improvements, or suggestions for future work!



8
New Comment



Moderation Log
More from michaelwaves
54
Your Mom is a Chimera
michaelwaves
18d
1
40
The Economics of Replacing Call Center Workers With AIs
michaelwaves
5mo
9
35
AI Teddy Bears: A Brief Investigation
michaelwaves
5mo
2
View more
Curated and popular this week
321
Forecasting is Way Overrated, and We Should Stop Funding It
mabramov
4d
63
237
10 non-boring ways I've used AI in the last month
habryka
9d
38
176
Your Supplies Probably Won't Be Stolen in a Disaster
jefftk
7d
5
0
Comments
xSAEBER: Sparse Autoencoders for Biological Entity Risk — LessWrong
