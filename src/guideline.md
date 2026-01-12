# Source Directory Guidelines

## Purpose

The `src/` directory contains all core application logic for the refactoring swarm system.

## Organization Rules

### Root Level (`src/`)

Place the following directly in `src/`:

- **Agent definitions** — LLM agent configurations, prompts, and behaviors
- **Graph/workflow logic** — State machines and agent orchestration
- **Tools** — Utility functions that agents use (file operations, code parsing, test execution)

### Utilities Subfolder (`src/utils/`)

Place the following in `src/utils/`:

- **Logging** — Experiment tracking and structured logging
- **Helpers** — Shared utility functions not specific to agents
- **Configuration** — Config loaders and validators
