# Evaluation notes

GoldenSet Factory is evaluated as a benchmark-lifecycle system.

A useful run should:

1. identify underrepresented failure modes,
2. surface novel and difficult cases,
3. reduce duplicate-like additions,
4. preserve broad failure-mode coverage,
5. create a reproducible candidate set and version manifest,
6. keep human approval as the promotion boundary.

The synthetic current benchmark deliberately underrepresents selected failure modes so the coverage machinery can be tested.

No candidate is automatically promoted into a trusted benchmark.
