export const meta = {
  name: 'economy-base-layer-audit-round2',
  description: 'Round 2 re-audit of the fixed economy base layer: verify each Round 1 finding resolved, adversarially confirm end-to-end money/goods conservation, hunt for new issues from the conservation and trade rewrites, synthesize a convergence verdict',
  phases: [
    { title: 'Reaudit', detail: 'per-module: verify each Round 1 finding resolved + hunt new issues' },
    { title: 'Conserve', detail: 'dedicated end-to-end money/goods conservation verifier' },
    { title: 'Verify', detail: 'adversarially confirm any new finding two ways' },
    { title: 'Synthesize', detail: 'convergence verdict' },
  ],
}

const REPO = '/Users/mauriziomocci/Documents/workspace/Opensource/epocha'

const MODULES = [
  {
    key: 'production',
    path: 'epocha/apps/economy/production.py',
    r1: 'PROD-1 (INCORRECT): CES Leontief limit returned A*min(alpha_i*X_i) instead of A*min(X_i) (10x error, discontinuity at sigma=0.05). PROD-4 (UNJUSTIFIED): 0.5 capital/natural_resources/knowledge baselines untagged.',
    fix: 'Leontief branch now returns scale*min(x for _,x in pairs); baselines tagged tunable. Commit cf69d75.',
  },
  {
    key: 'monetary',
    path: 'epocha/apps/economy/monetary.py',
    r1: 'PROD-3 (INCONSISTENT): compute_mood_delta docstring said "linear" but code is a flat step. PROD-4 (MISSING): compute_inflation is an unweighted Carli-index mean with undocumented upward bias.',
    fix: 'Docstrings fixed (step function, Carli bias disclosed). New live-M helper compute_circulating_money_supply, aggregate_system_prices, derive_mood_thresholds, and compute_mood_delta gained a poverty_threshold param. Commits 3527d4b, f1e8538.',
  },
  {
    key: 'market',
    path: 'epocha/apps/economy/market.py',
    r1: 'MKT-2 (INCORRECT): execute_trades N*M double loop fabricated goods (no running totals). MKT-5 (UNJUSTIFIED): discretionary demand misused elasticity as a divisor, unsourced 0.1, no cross-good budget. MKT-6 (INCONSISTENT): price-ceiling anchor differed between branches.',
    fix: 'execute_trades rewritten as O(n+m) two-pointer sweep with running totals (sum(buys)=sum(sells)=min(supply,demand)); discretionary demand now budget-constrained across goods (spend_fraction of cash, inverse-elasticity weights, sums to <= budget); single base_prices anchor in both ceiling branches. Commit 84e1cfe.',
  },
  {
    key: 'distribution',
    path: 'epocha/apps/economy/distribution.py',
    r1: 'PROD-2 / CM-1 (INCORRECT): rent and wages each distributed the full output value V, engine injected both as new cash (>2V/tick from nothing).',
    fix: 'Approach A: partition_output_value splits the single output value V into rent (rent_share 0.15) + wages (wage_share 0.6) + profit (residual 0.25) summing to V; owner double-pay branch removed; engine credits factor incomes summing to V with per-factor ledger entries; profit transaction type added. Commit cb19e7c.',
  },
  {
    key: 'initialization',
    path: 'epocha/apps/economy/initialization.py',
    r1: 'PROD-1/PROD-2 / CM-4 (INCONSISTENT): per-good scale hardcoded 5.0 (dead default_scale), sim_config omitted default_scale (engine fell back to 1.0), calibrated 2.0 dead everywhere (template documents 5.0 as unphysical flood).',
    fix: 'Per-good scale hardcode dropped so production.py default_scale fallback applies; default_scale written into sim_config production_config so the engine receives the calibrated 2.0. Commit 0ee32c9.',
  },
]

const FINDINGS_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['module', 'resolutions', 'new_findings'],
  properties: {
    module: { type: 'string' },
    resolutions: {
      type: 'array', description: 'one entry per Round 1 finding for this module',
      items: {
        type: 'object', additionalProperties: false, required: ['finding', 'status', 'evidence'],
        properties: {
          finding: { type: 'string', description: 'the Round 1 finding id/name' },
          status: { type: 'string', enum: ['RESOLVED', 'PARTIALLY_RESOLVED', 'NOT_RESOLVED', 'REGRESSED'] },
          evidence: { type: 'string', description: 'file:line and what the fixed code now does' },
        },
      },
    },
    new_findings: {
      type: 'array', description: 'NEW issues introduced by the fixes (empty if none)',
      items: {
        type: 'object', additionalProperties: false, required: ['id', 'category', 'claim', 'location', 'evidence', 'severity'],
        properties: {
          id: { type: 'string' },
          category: { type: 'string', enum: ['INCORRECT', 'UNJUSTIFIED', 'INCONSISTENT', 'MISSING'] },
          claim: { type: 'string' },
          location: { type: 'string' },
          evidence: { type: 'string' },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
      },
    },
  },
}

const CONSERVE_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['money_conserved', 'goods_conserved', 'findings', 'reasoning'],
  properties: {
    money_conserved: { type: 'string', enum: ['YES', 'NO', 'BOUNDED_INJECTION_ONLY'], description: 'BOUNDED_INJECTION_ONLY = net injection per tick equals output value V (legitimate income creation), no >V double-injection' },
    goods_conserved: { type: 'string', enum: ['YES', 'NO'] },
    findings: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false, required: ['id', 'category', 'claim', 'location', 'evidence', 'severity'],
        properties: {
          id: { type: 'string' }, category: { type: 'string', enum: ['INCORRECT', 'UNJUSTIFIED', 'INCONSISTENT', 'MISSING'] },
          claim: { type: 'string' }, location: { type: 'string' }, evidence: { type: 'string' }, severity: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
      },
    },
    reasoning: { type: 'string' },
  },
}

const VERDICT_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['survives', 'confidence', 'reasoning'],
  properties: {
    survives: { type: 'boolean' }, confidence: { type: 'string', enum: ['high', 'medium', 'low'] }, reasoning: { type: 'string' },
  },
}

const SYNTHESIS_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['per_module', 'overall_verdict', 'summary'],
  properties: {
    per_module: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false, required: ['module', 'verdict', 'unresolved', 'new_confirmed', 'note'],
        properties: {
          module: { type: 'string' }, verdict: { type: 'string', enum: ['CONVERGED', 'NOT CONVERGED'] },
          unresolved: { type: 'integer' }, new_confirmed: { type: 'integer' }, note: { type: 'string' },
        },
      },
    },
    overall_verdict: { type: 'string', enum: ['CONVERGED', 'NOT CONVERGED'] },
    summary: { type: 'string' },
  },
}

function reauditPrompt(m) {
  return `You are a HOSTILE adversarial scientific reviewer running a ROUND 2 re-audit for the Epocha project. A Round 1 audit found defects in this module; they were fixed. Your job: (1) verify EACH Round 1 finding is genuinely resolved in the CURRENT code, and (2) hunt for NEW defects the fixes introduced. Be adversarial — a fix that trades one error for another, or that resolves the letter but not the substance, must be caught.

Repository: ${REPO}
Module: ${m.path}

Round 1 findings for this module:
${m.r1}

Claimed fix:
${m.fix}

Read the CURRENT ${REPO}/${m.path} (and any caller you need, e.g. engine.py) and verify against the cited scientific sources (Arrow et al. 1961 CES; Fisher 1911; Walras 1874/Scarf 1960; Ricardo 1817; national-accounting factor-income identity). For each Round 1 finding, give a status (RESOLVED / PARTIALLY_RESOLVED / NOT_RESOLVED / REGRESSED) with file:line evidence of what the fixed code now does. Then hunt for NEW findings introduced by the fix (e.g. the CES Leontief fix — is it now continuous AND correct at the boundary? the conservation partition — do the shares REALLY sum to V with no residual, and is the profit-residual attribution sound? the trade sweep — does it truly conserve under all buyer/seller configurations including leftover remainders? the live-M aggregate — is the deposits/cash double-count decision correct? the mood thresholds — is the median-relative scheme sound and are the source claims accurate?). Every new finding needs a file:line and concrete evidence. Return the structured result.`
}

function conservePrompt() {
  return `You are an adversarial conservation auditor for the Epocha economy base layer (${REPO}/epocha/apps/economy/). The Round 1 audit found two conservation defects that were the load-bearing reason the layer was NOT CONVERGED: (CM-1) rent and wages each distributed the full output value V and the engine injected both as new cash (>2V/tick from nothing); (CM-3) execute_trades fabricated goods via an N*M double loop.

The fixes: distribution.py now partitions V into rent+wages+profit summing to V (approach A), engine credits factor incomes summing to V; market.py execute_trades is an O(n+m) two-pointer sweep conserving quantity.

Your job: adversarially verify, by reading the ACTUAL code end-to-end (distribution.py partition_output_value, engine.py steps 4/5/6 rent/wage/profit credits, market.py execute_trades, engine.py trade settlement, monetary.py compute_circulating_money_supply and the Fisher wiring), whether:
1. MONEY conservation: per economic tick, is the net cash injected by the rent/wages/profit step exactly the zone output value V (a bounded, legitimate income injection), with NO path that injects more than V or double-credits? Trace every from_agent=None credit and every debit. Does the tax step stay conservative? Is the profit residual credited exactly once? Are there rounding/leakage paths?
2. GOODS conservation: does execute_trades + the engine settlement move exactly min(supply,demand) of each good from sellers to buyers, with sum(goods out of sellers) == sum(goods into buyers), no fabrication, no seller floored below zero while a buyer is over-credited?
3. Does the live money-supply aggregate M now actually track circulating cash, and does check_fisher_consistency run so the MV=PQ diagnostic would catch any residual creation?

Read the code; do not rule from the description. Report money_conserved (YES / NO / BOUNDED_INJECTION_ONLY where net injection == V), goods_conserved (YES/NO), any remaining conservation findings with file:line, and your reasoning tracing the money and goods flows.`
}

function verifyPrompt(f) {
  return `Adversarial verifier for a Round 2 economy audit. Refute this NEW finding (default survives=false when uncertain). Read the actual code at ${REPO}/${f.location} before deciding.

Finding: [${f.category}/${f.severity}] ${f.claim}
Location: ${f.location}
Evidence: ${f.evidence}

Is this a real, defensible, actionable defect after adversarial scrutiny (checking both source-accuracy and materiality)? Return survives, confidence, reasoning.`
}

// Phase 1: per-module re-audit
phase('Reaudit')
const reaudits = await parallel(
  MODULES.map((m) => () => agent(reauditPrompt(m), { label: `reaudit:${m.key}`, phase: 'Reaudit', schema: FINDINGS_SCHEMA, effort: 'high' })
    .then((r) => ({ m, r })))
)

// Phase 2: dedicated conservation verifier (runs concurrently conceptually, but as its own barrier item)
phase('Conserve')
const conserve = await agent(conservePrompt(), { label: 'conservation', phase: 'Conserve', schema: CONSERVE_SCHEMA, effort: 'high' })

// Gather new findings (module-level + conservation-level)
const newFindings = []
for (const x of reaudits.filter(Boolean)) {
  for (const nf of (x.r.new_findings || [])) newFindings.push({ ...nf, _module: x.m.key })
}
for (const cf of (conserve.findings || [])) newFindings.push({ ...cf, _module: 'conservation' })

// Phase 3: adversarially verify each new finding
phase('Verify')
const verified = await parallel(
  newFindings.map((f) => () => agent(verifyPrompt(f), { label: `verify:${f.id}`, phase: 'Verify', schema: VERDICT_SCHEMA, effort: 'high' })
    .then((v) => ({ ...f, survives: v?.survives === true, verdict: v })))
)
const confirmedNew = verified.filter((f) => f && f.survives)

// Unresolved Round 1 findings
const unresolved = []
for (const x of reaudits.filter(Boolean)) {
  for (const res of (x.r.resolutions || [])) {
    if (res.status !== 'RESOLVED') unresolved.push({ module: x.m.key, ...res })
  }
}

log(`Round 2: ${unresolved.length} Round-1 findings not fully resolved; ${confirmedNew.length}/${newFindings.length} new findings survived verification; conservation money=${conserve.money_conserved} goods=${conserve.goods_conserved}.`)

// Phase 4: synthesize
phase('Synthesize')
const synthesis = await agent(
  `You are the lead auditor synthesizing the Round 2 re-audit verdict for the Epocha economy base layer.

Per-module Round 1 resolution status (only non-RESOLVED shown):
${JSON.stringify(unresolved, null, 2)}

New findings that SURVIVED adversarial verification:
${JSON.stringify(confirmedNew.map((f) => ({ module: f._module, id: f.id, category: f.category, severity: f.severity, claim: f.claim, location: f.location })), null, 2)}

Conservation verdict: money=${conserve.money_conserved}, goods=${conserve.goods_conserved}. Reasoning: ${conserve.reasoning}

A module is CONVERGED if all its Round 1 findings are RESOLVED and it has no surviving new INCORRECT/UNJUSTIFIED finding (INCONSISTENT/MISSING may be documented). The overall layer is CONVERGED only if all five modules converge AND money/goods conservation holds (money = YES or BOUNDED_INJECTION_ONLY, goods = YES). Give per-module verdicts, the overall verdict, and an honest summary of the remaining state (what, if anything, still blocks promotion from whitepaper §8.2 to §4 Methods).`,
  { label: 'synthesize', phase: 'Synthesize', schema: SYNTHESIS_SCHEMA, effort: 'high' }
)

return { unresolved, confirmedNew, conserve, synthesis }
