# 001-plain-anime — Plain 'anime' baseline

Baseline: what Qwen 2.1 does with just the word 'anime' and no style guidance.

| version | what changed | why | verdict |
|---|---|---|---|
| [v01](v01/) | Initial prompt | Round 1 style survey: same subject, only the style wording differs. | Clean, polished modern anime by default, with good hands and a readable fence. Default look is glossy digital. Seed 2002 picked a low angle that drifts toward a skirt-focused framing. |
| [v02](v02/) | Subject becomes a {subject} slot filled from subjects.json (6 subjects, seed 1001) | User wants every style tested on 1 male + 1 female, each in modern / sci-fi space / D&D fantasy (1 seed each). |  |
