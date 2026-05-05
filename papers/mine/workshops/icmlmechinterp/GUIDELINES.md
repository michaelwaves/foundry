Call for Papers
We are inviting submissions of short and long papers outlining new research, due May 8th, 2026 (AOE). This year we are accepting both ICML and NeurIPS formats for submissions, but all camera ready papers must be in ICML format. We welcome all submissions that convincingly argue for why they further the field: i.e. which further our ability to use the internal states of neural networks to understand them. Submit on OpenReview.

We require at least one reciprocal reviewer per submission! Each reciprocal reviewer will be assigned 3 papers to review. You can be a reciprocal reviewer on max 3 papers.

We are extremely grateful to all who volunteer as reviewers, you can express interest here.

Details:

The workshop is non-archival.
Authors will be notified of acceptance by June 12th (AOE).
We welcome submissions of papers that have already been accepted to ICML 2026. There will be an option to request a fast-track submission, in which authors will be asked to provide evidence of previous reviews and acceptance. Fast-track submissions are still subject to additional reviews (e.g., theme fit) once all other reviews are completed.
We do not accept submissions of work that has been accepted to an archival venue other than ICML 2026.
Prior submissions to the 2025 Mech Interp Workshop:
Papers previously accepted to the 2025 workshop (including extended/expanded versions) will not be accepted.
Papers previously rejected from the 2025 workshop that have not been meaningfully revised will be desk-rejected.
Submissions undergoing peer review (e.g., COLM, NeurIPS) at the time of the paper submission deadline are welcome.
All submissions must be made via OpenReview
Note: If you do not have an institutional email, be aware that it can take up to 2 weeks to get an OpenReview account approved. Please plan accordingly.
Please use the ICML 2026 LaTeX Template or the NeurIPS 2026 LaTeX Template. The page limit for ICML format is max 4 pages for short papers and max 8 pages for long papers. The page limit for NeurIPS format is 5 pages for short papers and max 9 pages for long papers. All page limits exclude references and appendices, which are unlimited but reviewers are not expected to read. Accepted papers must be converted to the ICML format for the camera ready version.
Accepted papers will be allowed one additional page in the camera ready version, to integrate reviewer feedback.
Long works will be held to a higher standard of rigor and depth than short works.
Authors are encouraged but not required to attend the workshop in person
The reviewing process is double-blind, and authors are responsible for ensuring no identifying details are included
We recommend searching the manuscript for the names, GitHub usernames and HuggingFace username of all core contributors before submission
Authors are strongly encouraged to open source any code, models, prompts, data and interactive demos. Reviewers will specifically be asked to take into account reproducibility, code, and/or data access.
We recommend https://anonymous.4open.science/ to anonymously share a GitHub repo
For larger files like model weights and datasets, we recommend making an anonymous HuggingFace account
For including interactive demos we recommend making an anonymous website or streamlit
We welcome any work that furthers the field of mechanistic interpretability, even if in unconventional ways. In addition to standard empirical work, this includes:
Rigorous negative results
Rigorous replications of important results
Critiques or compelling failed replications of past work
Open source software (e.g. TransformerLens, nnsight, pyvene, or Penzai) and tools (e.g. Neuronpedia or Docent)
Models or datasets that may be of value to the community (e.g. Pythia, MultiBERTs or Gemma Scope)
Educational materials (e.g. the ARENA materials)
Distillations of key and poorly explained concepts (e.g. Ferrando et al)
Position pieces that bring clarity to complex topics and debates (e.g. the ‘strong’ feature hypothesis could be wrong)
Strong empirical works will clearly articulate (i) specific falsifiable hypotheses, and how the evidence provided does and does not support them; or (ii) convincingly show clear practical benefits over well-implemented baselines.

Works that clearly document the strengths and weaknesses of their evidence, and what we can learn from this are welcomed, even if it weakens the narrative or conclusions remain inconclusive. Works that downplay or omit significant limitations will not be accepted.

Authors may find Neel Nanda’s advice on paper writing to be a helpful perspective, especially those new to writing mechanistic interpretability papers.

Topics of Interest
We are particularly interested in, but not limited to, the following directions:

Understanding Model Internals
What can we learn about high-level properties (i.e., representations, feature geometry) of models, as well as how they are used internally?
Can we find evidence for cognitive phenomena such as latent reasoning, implicit planning, search algorithms, or internal world models?
Ex: How are {beliefs, personas, world models, reasoning processes, implicit goals} represented?
Methods for Mechanistic Discovery
How can we effectively uncover and validate internal structures?
How can {circuit analyses, causal methods, attribution graphs, dictionary learning, training-data attributions} be improved? What are other novel paradigms we should consider?
Interpretability for Practical Applications, Development, and Benchmarking
How can interpretability tools and/or insights help us with real-world downstream applications, model development, or evaluations?
How can interpretability help us identify, “debug”, and fix undesirable/unexpected model behaviors?
How can we benchmark our progress in our field?
Interpretability for Safety, Monitoring, and Model Repair
How can interpretability help us develop safer models? How can interpretability help us detect undesirable phenomena such as alignment faking, subliminal learning, or emergent misalignment?
How can such tools help us monitor deployed models?
Scaling, Generalizing, and Automating Interpretability
How can we expand beyond studying controlled, templated domains to more realistic settings, on larger frontier models?
How well do insights from toy settings generalize to scaled-up, more complex models?
How can we automate interpretability efforts, perhaps with the help of recent ML developments (e.g., agents, Activation Oracle-style decoding)?
Interpreting Domain-specific Foundation Models for Knowledge Discovery
Can we reverse-engineer or understand foundation models in other domains to learn from models?
Conceptual & Foundational Work
What is the right framework to characterize model internals? How should concepts like “features” or “circuits” be defined?



## ICML guidelines
ICML 2026 Author Instructions 
 

Paper Submissions
Submitted papers are composed of a main body, which can be up to eight pages long, followed by any number of pages for references and appendices, all in a single PDF file. (Final versions of accepted papers will be published in the same way, with references and appendices included.)  The submission PDF has a maximum size of 50MB while the camera ready version will be limited to 20MB. The required format of the papers is specified in the LaTeX style files and the example paper. There is no support for any typesetting software other than LaTeX. All submissions must be anonymized and follow the required format; otherwise, they will automatically be rejected. In particular, any submission whose main body goes over the 8 page limit will be automatically rejected. (The final version of each accepted paper will be allowed an extra page. See the example paper for further information.)

Authors have the option of uploading extra files as Supplementary Material to provide further details of their work (e.g., code/data that supports experimental findings, other (anonymized) papers of the authors whose results are needed by the submitted paper). It is entirely up to the reviewers to decide whether they wish to consult any of the appendices in the submitted paper or this Supplementary Material. Therefore, if there is material critical to the evaluation of the paper, it needs to be included in the main body of the paper. See below for more details.

Authors are encouraged to submit code to foster reproducibility. Reproducibility of results and easy availability of code will be taken into account in the decision-making process. Authors should not include links to non-anonymized repositories; instead, they should submit the code base itself or anonymized repositories.

Authors will be asked to confirm that their submissions are in accord with the ICML code of conduct.

Submissions will be handled through OpenReview. See the Call for Papers for important dates and deadlines, including the suggested deadline for creating an account on OpenReview.

 

Supplementary Material
ICML 2026 supports the submission of two kinds of supplementary material: supplementary manuscripts and code/data. In particular, if an anonymous reference is made in the paper, authors should upload the referenced papers, so that the reviewers can check the results in the referred paper. The supplementary material must also be anonymized. Note that traditional text appendices to the paper need not be submitted as a separate Supplementary Material; as mentioned above, unlimited appendices are allowed in the main submission file of a paper.

The supplementary code can be submitted as either a zip file or a pdf. For code submissions, we expect authors to anonymize the submitted code. This means that author names and licenses should be removed. Submission of code through anonymous GitHub repositories is also allowed; however, they have to be on a branch that will not be modified after the submission deadline. Please enter the GitHub link in a standalone text file in a submitted zip file. Data submissions (provided that the authors have the right to do so) in anonymous repositories are welcome.

For accepted papers, the originally submitted manuscript and supplementary material will become publicly available on OpenReview. However, there is no option to provide supplementary material with the final, camera-ready version appearing in the proceedings. If authors wish to refer to supplementary code or data in their final version, they are responsible for providing an archival link to a suitable repository.

There is no separate deadline for Supplementary Material: All supplementary material must be submitted by the same deadline as the paper submission.

 

Double-Blind Reviewing
Reviewing for ICML 2026 is double-blind: reviewers will not know the authors’ identities and vice versa. Detailed instructions for anonymizing the submission are contained in the aforementioned example paper. In brief, authors should refer to their prior work in the third person wherever possible. They should refrain from including acknowledgements, grant numbers, or links to public code repositories in their submissions.

Previously published papers with substantial overlap written by the authors must be cited in such a way so as to preserve author anonymity. Differences relative to these earlier papers must be explained in the text of the submission. For example: “This work builds on [reference], which showed that…”. If an anonymous reference is needed in the paper (e.g., for referring to the authors’ own work that is under review elsewhere), include the referred work as Supplementary Material as noted above. Note that anonymizing the submissions is mandatory, and papers that explicitly or implicitly reveal the authors’ identities will be rejected.

It may be possible for reviewers to deduce the authors’ identities by using external resources, such as technical reports published on the internet or elsewhere. The availability of such external resources that may allow reviewers to infer the authors’ identities does not constitute a breach of the double-blind submission policy. Reviewers are explicitly asked not to seek out this information.

Please see the Call for Papers for additional policies concerning double-blind reviewing.

 

Reviewing and Author Response
Submitted papers will not be publicly accessible during the review period. Only accepted papers will be made public through OpenReview. Reviewers are forbidden from sharing papers they receive for review, or using the material in any way other than to provide their review.

After initial reviews, authors will have the opportunity to respond to reviewer comments. During this response period, authors can see the reviews and respond to their content, but these responses will only be visible to the reviewers after this period. During the subsequent discussion period, reviewers and authors will be able to engage in one additional round of communication, to follow up on any remaining questions or concerns.

Any of the authors of a paper can enter/edit the responses. As reviewing is double-blind, the response should not contain information that could reveal the authors’ identities. In addition, the response should not contain non-anonymized URLs, URLs for personal websites, or “shortened” URLs (e.g., as provided via tinyurl, which could log a reviewer’s IP). Reviewers are not expected to follow external URLs in the response.

Keep in mind that there is no need to respond to every minor question or suggestion for improvement. Rather, the response is a good opportunity for addressing issues like a reviewer’s uncertainty about a point, a reviewer making an incorrect assumption, or a reviewer misunderstanding some part of the paper. Responses that use professional and polite language are generally the most effective.

We aim to provide three reviews for every paper, although the precise number may vary. The reviewer IDs uniquely specify the reviewers of the paper but are otherwise arbitrary. The structure of the author response is up to the authors. It is typical to organize the response by reviewers and to use the reviewer IDs to refer to the particular reviews.

There is no option to upload a revised version of the paper during the author feedback period.

 

Camera-Ready Papers and Post-Conference Revisions
Authors of accepted papers will be able to upload non-anonymized “camera-ready” versions of their paper. Authors may choose to (but are not required to) make changes as suggested by the reviewers, as well as other improvements, so long as the essential content of the paper remains unchanged compared to what the reviewers have seen.

Authors must upload a camera-ready version of the paper by the camera-ready deadline prior to the conference; this version of the paper will be made publicly available through OpenReview after this deadline. In addition, to improve accountability, the originally submitted manuscript and supplementary material will also be published on OpenReview, alongside the anonymized reviews, meta-reviews, rebuttal, and reviewer-author discussion.

After the conference, authors will be able to (but are not required to) revise the camera-ready version of their paper (e.g., to incorporate any feedback received during the conference). These revisions must be made by the post-conference revision deadline. After this deadline, the latest camera-ready version of the paper will be published in the ICML 2026 proceedings through PMLR.

 

Additional Policies
Please see the Call for Papers for additional policies concerning dual submissions, use of generative AI tools (including LLMs), ethical conduct for peer review, impact statements, and lay summaries.

 

Accessibility
Authors are encouraged to make their submissions as accessible as possible for everyone including people with disabilities and sensory or neurological differences. For more guidance, please consult Making Accessible Papers and Talks.