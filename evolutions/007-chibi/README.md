# 007-chibi — Chibi / super-deformed

Does it handle stylized proportions (big head, tiny body) cleanly?

| version | what changed | why | verdict |
|---|---|---|---|
| [v01](v01/) | Initial prompt | Round 1 style survey: same subject, only the style wording differs. | Works well: clean ~3-head proportions, full body with shoes, still clearly the same character and scene. It pulled the camera back to show the whole figure. |
| [v02](v02/) | Subject becomes a {subject} slot filled from subjects.json (6 subjects, seed 1001) | User wants every style tested on 1 male + 1 female, each in modern / sci-fi space / D&D fantasy (1 seed each). |  |
