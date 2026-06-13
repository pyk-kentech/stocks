# Provider Pack #4: Flow Public Data Adapter Design

## Goal

Add a Flow Provider Pack that acquires public HTTP or local-file foreign and
institution flow data, normalizes it through the existing Provider Pack
pipeline, imports it as `FOREIGN_INSTITUTION_FLOW` signals, and uses it only as
a conservative ranking and watching aid.

The feature does not add real orders, automatic trading, private scraping,
credentials, default-on networking, or new Risk Engine hard-risk behavior.

## Architecture

The Flow Provider Pack reuses the existing pipeline:

```text
safe HTTP or local_file
-> raw flow provider file
-> provider_pack_config normalizer and columns
-> GenericFlowCSVNormalizer rich-provider mode
-> Unified Import
-> FOREIGN_INSTITUTION_FLOW signal enrichment
```

`provider_pack_config` remains the single source for connector and normalizer
settings. Each provider entry contains its own `normalizer` and `columns`.
There is no separate `normalizer_config_file`.

## Provider Configuration

Add `flow.providers` to `ProviderPackConfig`.

Each Flow provider requires:

- `ticker`
- `observed_at`
- `source_name`
- at least one of:
  - `foreign_net_buy_amount`
  - `institution_net_buy_amount`
  - `foreign_net_buy_shares`
  - `institution_net_buy_shares`

Optional mappings:

- `retail_net_buy_amount`
- `retail_net_buy_shares`
- `currency`
- `market`
- `title`
- `summary`
- `url`

Example:

```json
{
  "flow": {
    "providers": [
      {
        "provider_name": "sample_flow_provider",
        "local_file": "data/flow.csv",
        "data_kind": "FOREIGN_INSTITUTION_FLOW",
        "output_format": "CSV",
        "allowed_hosts": [],
        "enabled": true,
        "normalizer": "generic-flow-csv",
        "columns": {
          "ticker": "Symbol",
          "observed_at": "ObservedAt",
          "source_name": "Source",
          "foreign_net_buy_amount": "ForeignNetBuyAmount",
          "institution_net_buy_amount": "InstitutionNetBuyAmount"
        }
      }
    ]
  }
}
```

Add:

- `ProviderDataKind.FOREIGN_INSTITUTION_FLOW`
- `ProviderPackType.FLOW`
- `flow: ProviderPackGroup`
- `run_flow_provider_pack`
- `run-flow-provider-pack`

No combined Flow pack is added.

## Normalization

Reuse `GenericFlowCSVNormalizer`.

Legacy mode remains unchanged when rich-provider mappings are absent. Rich
provider mode is selected when `source_name` is mapped and at least one of the
new amount or shares fields is mapped.

Rich normalized records contain:

- `ticker`
- `observed_at`
- `source_name`
- `title`
- `summary`
- `url`
- `sentiment`
- `severity`
- `score_delta`
- `foreign_net_buy_amount`
- `institution_net_buy_amount`
- `retail_net_buy_amount`
- `foreign_net_buy_shares`
- `institution_net_buy_shares`
- `retail_net_buy_shares`
- `currency`
- `market`
- `raw_payload_json`

Optional numeric values are normalized to `float | None`. Missing optional
text values remain `None`. The title is generated from the calculated
direction when no provider title is supplied.

The complete raw provider row is preserved in `raw_payload_json`.

## Amount And Shares Selection

Selection is deterministic and based on the provider config:

1. If either foreign or institution amount mapping exists, use amount fields.
2. Only when neither amount mapping exists, use shares fields.
3. Within the selected pair, missing or blank row values are treated as zero.
4. Do not fall back from amount to shares on individual rows.

This avoids mixing currencies, amounts, and shares within a provider or run.

## Flow Score Mapping

Apply this mapping only to rich Flow Provider Pack normalized results:

| Foreign | Institution | Direction | Severity | Score |
|---|---|---|---|---:|
| `> 0` | `> 0` | POSITIVE | LOW | +2 |
| one `> 0`, other `0` or missing | POSITIVE | LOW | +1 |
| `< 0` | `< 0` | NEGATIVE | MEDIUM | -3 |
| one `< 0`, other `0` or missing | NEGATIVE | LOW | -1 |
| opposite signs | NEUTRAL | LOW | 0 |
| both `0` or missing | NEUTRAL | LOW | 0 |

Flow Provider Pack does not generate HIGH or CRITICAL severity by default.
It does not use absolute thresholds because provider currencies, units, and
market scales differ.

## Import And Enrichment

Unified Import recognizes explicit rich Flow Provider Pack records by their
`score_delta`. It preserves normalized direction, severity, score, source,
title, and raw payload.

Legacy Flow import continues to use the existing common signal scoring path.
The shared `signal_scoring.py` behavior is not changed.

Flow is an auxiliary ranking signal, not a hard-risk input:

- positive Flow can adjust a candidate score
- positive Flow alone cannot promote EXCLUDE or blocked candidates
- negative Flow created by this pack is LOW or MEDIUM and therefore does not
  trigger HIGH-to-WATCH or CRITICAL-to-EXCLUDE rules
- Risk Engine hard-risk rules remain unchanged

## Network Safety

The existing network safety contract is reused:

- public HTTP requires explicit `--enable-network`
- HTTP providers are DISABLED without it
- `allowed_hosts` uses exact matching
- redirect targets are revalidated
- credentials, auth headers, cookies, sessions, private scraping, and Toss
  scraping remain unsupported
- local-file providers require no network
- tests use local files or an injected fake HTTP client only

## CLI

Add:

```bash
python -m stock_risk_mcp.cli run-flow-provider-pack \
  --db data/stock_risk_mcp.sqlite3 \
  --as-of-date 2026-06-13 \
  --provider-pack-config configs/provider_pack.json \
  --output-dir data/provider_outputs \
  --enable-network
```

Existing `provider-pack-runs` and `provider-pack-show` commands inspect FLOW
runs.

## Testing

Tests must cover:

- `flow.providers` load and validation
- missing base required columns
- no amount/shares mapping validation error
- provider-entry-only normalizer and columns
- missing normalizer source failure
- local-file execution without network
- HTTP provider DISABLED without network
- fake HTTP normalize and import flow
- both positive, one positive, both negative, one negative, opposite signs,
  and both zero/missing mappings
- amount config precedence over shares
- shares fallback only when amount mappings are absent
- raw payload preservation
- imported `FOREIGN_INSTITUTION_FLOW` signal
- no default HIGH or CRITICAL Flow signal
- positive Flow does not promote EXCLUDE
- legacy/common signal scoring remains unchanged
- existing Price, FX, News, and Dilution Provider Pack regression coverage
- complete pytest, compileall, diff check, and system smoke verification

## Documentation

README and WORK_SUMMARY will state:

- Flow is a ranking and watching aid, not hard-risk or a buy instruction
- positive Flow cannot promote EXCLUDE or blocked candidates
- the pack uses deterministic sign mapping without absolute thresholds
- amount mappings take precedence over shares mappings
- networking remains explicit, allowlisted, and default-off
- the feature is for paper-trading and research support only
