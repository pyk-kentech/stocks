# FX-aware Portfolio / Risk Layer Design

## Scope

Use stored or manually supplied FX rates to interpret account-currency inputs
while preserving the existing trading-currency sizing and hard-risk engines.
No external FX lookup, network request, order execution, or hard-risk policy
change is introduced.

## Data Flow

The CLI builds one `PortfolioCurrencyContext` before starting a paper pipeline.
Account equity and cash are converted into trading currency and passed to the
existing pipeline unchanged. Generated TradePlan, BasketPlan, allocation,
paper result, PipelineRun, report, notification, and dashboard records receive
nullable FX metadata and account-currency equivalents.

If account and trading currencies match, rate 1.0 is used. Manual rates take
priority over SQLite. Database lookup uses the latest row on or before the
as-of date and can invert the opposite pair. Stale rates remain usable with a
WARNING. Missing rates preserve legacy trading-currency behavior, leave
account conversions null, and record warnings.

## Persistence And Compatibility

New model fields are nullable or defaulted. Existing SQLite databases gain
nullable columns through safe migration helpers. PipelineRun remains stored in
its existing JSON record. Existing USD-only defaults produce the same sizing
and basket behavior.
