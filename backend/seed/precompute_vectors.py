"""Precompute normalized MiniLM interests for the fictional demo residents.

Run from the repository root with the local, ignored model directory::

    .tools/Python311/python.exe backend/seed/precompute_vectors.py

The script never downloads a model. Deployment needs only the resulting JSON,
not Torch or sentence-transformers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL_DIR = ROOT / ".tools" / "all-MiniLM-L6-v2"
DEFAULT_OUTPUT = SEED_DIR / "interest_embeddings.json"


def seed_members() -> tuple[list[dict], dict[str, str]]:
    people: list[dict] = []
    seed_hashes: dict[str, str] = {}
    for name in ("hydepark", "quarry"):
        path = SEED_DIR / f"{name}.json"
        raw = path.read_bytes()
        seed_hashes[path.name] = hashlib.sha256(raw).hexdigest()
        people.extend(json.loads(raw)["members"])
    ids = [person["id"] for person in people]
    if len(people) != 70 or len(set(ids)) != 70:
        raise ValueError(f"Expected 70 unique fictional seed members, found {len(people)}")
    return people, seed_hashes


def generate(model_dir: Path = DEFAULT_MODEL_DIR,
             output: Path = DEFAULT_OUTPUT) -> dict:
    model_dir = model_dir.resolve()
    if not (model_dir / "modules.json").is_file():
        raise FileNotFoundError(f"Local MiniLM model unavailable: {model_dir}")

    from sentence_transformers import SentenceTransformer

    people, seed_hashes = seed_members()
    model = SentenceTransformer(str(model_dir), local_files_only=True, device="cpu")
    texts = [", ".join(person["interests"]) for person in people]
    vectors = model.encode(texts, batch_size=16, normalize_embeddings=True,
                           show_progress_bar=False)
    records = {}
    for person, text, vector in zip(people, texts, vectors):
        values = [round(float(value), 9) for value in vector]
        if len(values) != 384 or not math.isclose(
            math.sqrt(sum(value * value for value in values)), 1.0,
            rel_tol=0, abs_tol=0.00001,
        ):
            raise ValueError(f"Invalid MiniLM vector for {person['id']}")
        records[person["id"]] = {
            "interests": person["interests"],
            "text": text,
            "vector": values,
        }
    if len(records) != len(people):
        raise ValueError("A seed member is missing a vector")
    artifact = {
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "dimensions": 384,
        "normalized": True,
        "seed_sha256": seed_hashes,
        "members": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, ensure_ascii=False,
                                 separators=(",", ":")) + "\n", encoding="utf-8")
    return artifact


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR,
                        help="Local model folder; downloads are disabled")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = generate(args.model_dir, args.output)
    print(f"Wrote {len(result['members'])} vectors of {result['dimensions']} dimensions "
          f"to {args.output}")
