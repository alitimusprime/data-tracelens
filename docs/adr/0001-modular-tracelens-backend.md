# ADR 0001: Modular TraceLens backend

## Decision

Run the API and analyzer as separate processes from one Python codebase and domain model.

## Rationale

Analysis should not block request handling, but its models and transactions are tightly related to the API. Internal network services would add failure modes without an independent scaling or ownership need.

## Consequence

Both processes deploy from one image. They can be extracted later if measured load justifies it.
