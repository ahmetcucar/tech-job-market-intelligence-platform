# Working Agreement

This project is being built as a learning project, not a speedrun.

## Collaboration Style

- Move slowly and step by step.
- Explain the purpose of each change before making it.
- Keep code changes small, digestible, and easy to review.
- Prefer one concept or project layer at a time.
- Do not scaffold large chunks of the application without discussion.
- After each meaningful change, pause to review what changed and why.

## Documentation Standard

- Every code file should start with a module docstring that explains what the file owns.
- Every public function should have a docstring that explains what it does, what inputs it expects, what it returns, and any important behavior or failure mode.
- Use inline comments for non-obvious decisions only. Avoid comments that restate simple code.
- Keep documentation current as part of each code change, not as a cleanup task for later.

## Current Build Philosophy

Start with the smallest useful data product loop:

1. Understand the source.
2. Ingest one source.
3. Store raw data.
4. Normalize one layer.
5. Add simple querying.
6. Add UI only after the data path makes sense.

The goal is to learn the engineering decisions behind the project, not just produce files.
