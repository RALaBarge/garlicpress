# garlicpress

Distributed stateless LLM code evaluation.

**Map → Reduce → Swap**

- **Map**: stateless agents review one file each, emit structured findings JSON
- **Reduce**: hierarchical tree-fold along directory boundaries, detecting cross-file contradictions
- **Swap**: Agent B checks spec expectations against map-phase ground truth

See [EVAL_SPEC.md](../beigebox/EVAL_SPEC.md) for the full architecture.

## Install

```bash
pip install garlicpress
```

## Usage

```bash
export ANTHROPIC_API_KEY=...

# Full run
garlicpress run /path/to/repo --spec CLAUDE.md --spec EVAL_SPEC.md

# Map only
garlicpress map /path/to/repo --output findings/

# Reduce existing findings
garlicpress reduce findings/

# Swap (Agent B) against spec
garlicpress swap findings/ --spec CLAUDE.md

# Only changed files (CI/CD mode)
garlicpress run /path/to/repo --changed-only --spec CLAUDE.md
```

## Options

```
garlicpress run --help
```

| Flag | Default | Description |
|---|---|---|
| `--output` / `-o` | `findings` | Output directory |
| `--concurrency` / `-c` | `5` | Parallel map workers |
| `--map-model` | `claude-sonnet-4-6` | Model for map agents |
| `--reduce-model` | `claude-sonnet-4-6` | Model for reduce agents |
| `--swap-model` | `claude-sonnet-4-6` | Model for Agent B |
| `--spec` / `-s` | — | Spec files for swap (repeatable) |
| `--skip-swap` | false | Skip Agent B pass |
| `--changed-only` | false | Only review git-changed files |
| `--base-ref` | `HEAD~1` | Git base for changed-only |

## Output

```
findings/
  beigebox/
    proxy.py.json          # per-file findings
    main.py.json
    backends/
      router.py.json
      _summary.json        # directory reduce output
    _summary.json
  _summary.json            # root summary
  _swap_report.json        # Agent B output
  skeleton.txt             # generated API surface
```

## License

MIT
