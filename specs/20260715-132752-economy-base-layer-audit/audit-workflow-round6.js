export const meta = {
  name: 'economy-base-layer-audit-round6',
  description: 'Round 6 targeted re-audit: verify the Round 5 findings (R5-CRED-1/2/3 default terminal state + cascade loss records + missed-interest wiring, R5-FISH-1/2 per-zone PQ, R5-LED-1 rollover ledger, R5-2 derived broadcast RNG, R5-VEL-1/R5-DISC-1/R5-DOC-1 disclosures and doc-sync, residual order pins) resolved or documented, hunt for new issues, deliver the convergence verdict',
  phases: [
    { title: 'Reaudit', detail: 'per-area: verify each Round 5 finding closed + hunt new issues' },
    { title: 'Conserve', detail: 'end-to-end conservation + determinism sweep' },
    { title: 'Verify', detail: 'adversarially confirm any new finding' },
    { title: 'Synthesize', detail: 'convergence verdict' },
  ],
}

const REPO = '/Users/mauriziomocci/Documents/workspace/Opensource/epocha'

const AREAS = [
  {
    key: 'credit-terminal',
    path: 'epocha/apps/economy/credit.py',
    r5: 'R5-CRED-1 (INCORRECT/high): defaulted loans had no terminal state, so process_defaults re-processed every historical default on every tick (repeated collateral seizure clawing back resold properties, repeated BankingState.total_loans_outstanding decrements, unbounded duplicate reputation memories). R5-CRED-2 (INCORRECT/high): process_default_cascade re-seeded lender losses from the gross principal of ALL-TIME defaults every tick, permanently re-defaulting fragile lenders. R5-CRED-3 (INCORRECT/medium): service_loans returned the ids of loans whose borrower could not pay interest but engine.py discarded the list, so missed interest had zero consequence until maturity, contradicting the docstring and whitepaper 4.2.2. R5-LED-1 (low): the rollover branch of process_maturity moved the interest payment in cash with no EconomicLedger row.',
    fix: 'Commits 7aeb41d + 7ec6548: processed defaults move to the terminal default_settled status (new Loan status choice, migration 0008); the cascade consumes the loss_records returned by process_defaults for the CURRENT tick (net of seized collateral), with the legacy query (now naturally scoped to unsettled defaults, id-ordered) retained for direct callers; the engine marks the service_loans returns defaulted so process_defaults settles them in the same tick; rollover interest is ledgered as loan_interest. Regression tests: TestDefaultTerminalState (3 tests: exactly-once processing, no claw-back after resale, cascade on current-tick records), TestMissedInterestDefault, TestRolloverInterestLedger.',
  },
  {
    key: 'fisher-multizone',
    path: 'epocha/apps/economy/engine.py',
    r5: 'R5-FISH-1/R5-FISH-2 (INCORRECT/medium): the R4-rewired Fisher diagnostic compared MV (factor income credited at per-zone equilibrium prices) against PQ (total system output repriced at the unweighted cross-zone MEAN price), so a perfectly conserved multi-zone economy with price dispersion and asymmetric output fired spurious divergence warnings (counterexample: zone A 190@1, zone B 10@3 -> MV=220 vs PQ=400, 45% > 20% threshold). R5-VEL-1 (doc): Currency.cached_velocity docstring/help_text still claimed it feeds the Fisher check. R5-DISC-1 (doc): the M-scope disclosure omitted banking-type interest as an M-contracting flow.',
    fix: 'Commit 7aeb41d: nominal_output_value is accumulated in the zone loop as the sum of per-zone V_z = sum_g(zone_production_zg * equilibrium_price_zg) -- the same quantity the factor-income partition distributes -- so MV == PQ exactly whenever conservation holds, in every zone regime; regression test test_fisher_pq_sums_per_zone_nominal_output uses a two-zone fixture with ASYMMETRIC output (extra farmers in one zone) and price dispersion. Commit 7ec6548: Currency docstring/help_text now state cached_velocity is a reported turnover metric and the Fisher check uses the engine-computed income velocity (migration 0009); the compute_circulating_money_supply disclosure now covers banking interest as an M-contracting inside-money flow.',
  },
  {
    key: 'determinism-final',
    path: 'epocha/apps/economy/banking.py',
    r5: 'R5-2 (INCORRECT/medium): broadcast_banking_concern sampled agents with the module-global random.sample, whose state depends on every prior consumer of the global stream -- the broadcast set was not a pure function of the seeded simulation state, falsifying the whitepaper claim of seeded reproducibility. Residual unpinned iteration orders: the cascade legacy and per-borrower loan querysets (credit.py), the credit-demand aggregation (banking.adjust_interest_rate), the deposit recalculation (banking.recalculate_deposits), and the expectations goods list. R5-DOC-1 (INCONSISTENT/medium): whitepaper 4.2.1 in both languages still described the expectations price aggregation as a last-write-wins merge after it moved to the cross-zone mean; 4.2.2 described the discarded service_loans list and the seeded-global-random claim.',
    fix: 'Commit 7ec6548: the broadcast samples from random.Random(f"{simulation.seed}:{tick}:banking-concern"), independent of the global stream (regression test TestBankingConcernBroadcastReproducibility wipes and re-runs the same tick and asserts identical recipient sets); all listed querysets/aggregations are id-ordered with determinism-pin comments. Commits 7aeb41d + 7ec6548: whitepaper 4.2.1 (three spots per language) now describes the cross-zone mean via aggregate_system_prices with the historical last-write-wins note; 4.2.2 describes the terminal default state, the loss-record-driven cascade, the same-tick missed-interest wiring, and the derived-RNG broadcast, in both languages.',
  },
]

const FINDINGS_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['area', 'resolutions', 'new_findings'],
  properties: {
    area: { type: 'string' },
    resolutions: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false, required: ['finding', 'status', 'evidence'],
        properties: {
          finding: { type: 'string' },
          status: { type: 'string', enum: ['RESOLVED', 'DOCUMENTED', 'PARTIALLY_RESOLVED', 'NOT_RESOLVED', 'REGRESSED'] },
          evidence: { type: 'string' },
        },
      },
    },
    new_findings: {
      type: 'array',
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
  type: 'object', additionalProperties: false, required: ['money_conserved', 'goods_conserved', 'tax_conserved', 'deterministic', 'findings', 'reasoning'],
  properties: {
    money_conserved: { type: 'string', enum: ['YES', 'NO', 'BOUNDED_INJECTION_ONLY'] },
    goods_conserved: { type: 'string', enum: ['YES', 'NO'] },
    tax_conserved: { type: 'string', enum: ['YES', 'NO'] },
    deterministic: { type: 'string', enum: ['YES', 'NO'] },
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

function reauditPrompt(a) {
  return `You are a HOSTILE adversarial scientific reviewer running the ROUND 6 re-audit for the Epocha economy base layer. The Round 5 re-audit confirmed the findings below; they were then fixed or documented (branch tip commits 7aeb41d and 7ec6548). Your job: (1) verify EACH Round 5 finding is genuinely closed in the CURRENT code (RESOLVED for behavioral fixes, DOCUMENTED for honest disclosures), and (2) hunt for NEW defects the fixes introduced. Be adversarial: a fix that trades one error for another must be caught. Keep proportion: this layer has been through five audit rounds -- do not re-litigate previously adjudicated design decisions (approach-A factor partition, deposits outside M, Carli index disclosure, essential-first settlement, primary-currency demand sizing, treasury-outside-M boundary); hunt only for genuine defects introduced by the LATEST two commits or missed by all prior rounds.

Repository: ${REPO}
Primary file: ${a.path} (read every other file you need: engine.py, credit.py, banking.py, monetary.py, expectations.py, models.py, migrations, tests/, docs/whitepaper/)

Round 5 findings for this area:
${a.r5}

Claimed fix:
${a.fix}

Specific adversarial angles: does the same-tick missed-interest default interact correctly with process_maturity (a loan both missing interest AND maturing this tick must not be double-processed)? Does the default_settled terminal state leak into any query that expects "defaulted" (solvency checks, Minsky classification, find_best_unpledged_property's active-loan exclusion, default_dead_agent_loans)? Does the derived broadcast RNG produce adequate dispersion across ticks (seed string collisions)? Do the migrations 0008/0009 carry any data risk for existing rows? Every new finding needs file:line and concrete evidence. Return the structured result.`
}

function conservePrompt() {
  return `You are an adversarial conservation-and-reproducibility auditor for the Epocha economy base layer (${REPO}/epocha/apps/economy/), Round 6 -- the final convergence check after five rounds of fixes. Current branch tip: commits 7aeb41d + 7ec6548 on top of the Round 4 batch.

Verify by reading the ACTUAL current code end-to-end:
1. MONEY: net cash injected by rent/wages/profit equals zone output value V (or strictly less only via the documented wage-cap clip); taxation and property sales (including ownerless-to-treasury) are pure transfers; credit flows (issuance, interest, repayment, rollover, default write-off) are either two-legged or documented inside-money flows tracked against BankingState; defaults are processed exactly once (terminal default_settled state).
2. GOODS: trades, settlement scaling, collateral seizure move goods/property conservatively, exactly once.
3. DETERMINISM: sweep EVERY iteration order feeding order-sensitive state in the whole tick (engine zone loop, goods, currencies, agents, properties, trades, payees, tax set, credit loan querysets, cascade BFS order, banking aggregations, broadcast RNG, expectations, property market buyers/listings, all_agents/step-8 sums): is each pinned or provably order-insensitive? Would two identically-seeded runs with different PYTHONHASHSEED and different DB heap orders produce identical final state?
4. The Fisher diagnostic: MV (income velocity * M = factor income) vs PQ (sum of per-zone V_z) -- verify they are independently measured and equal under conservation in BOTH single-zone and multi-zone regimes, so divergence is a genuine defect signature.

Report money_conserved, goods_conserved, tax_conserved, deterministic, remaining findings with file:line, and your reasoning.`
}

function verifyPrompt(f) {
  return `Adversarial verifier for the Round 6 economy audit. Refute this NEW finding (default survives=false when uncertain). Read the actual code at ${REPO}/${f.location} before deciding. This layer has been through five audit rounds: previously adjudicated design decisions (approach-A partition, deposits outside M, Carli disclosure, essential-first settlement, primary-currency sizing, treasury outside M, inside-money credit flows) are settled -- a finding that re-litigates one of them does not survive. Materiality bar: a finding must either break an invariant (conservation, determinism, exactly-once), misstate model behavior in code comments/whitepaper, or leave a formula/constant unsourced and untagged.

Finding: [${f.category}/${f.severity}] ${f.claim}
Location: ${f.location}
Evidence: ${f.evidence}

Is this a real, defensible, actionable defect after adversarial scrutiny (source-accuracy AND materiality, both required)? Return survives, confidence, reasoning.`
}

phase('Reaudit')
const reaudits = await parallel(
  AREAS.map((a) => () => agent(reauditPrompt(a), { label: `reaudit:${a.key}`, phase: 'Reaudit', schema: FINDINGS_SCHEMA, effort: 'high' })
    .then((r) => ({ a, r })))
)

phase('Conserve')
const conserve = await agent(conservePrompt(), { label: 'conservation', phase: 'Conserve', schema: CONSERVE_SCHEMA, effort: 'high' })

const newFindings = []
for (const x of reaudits.filter(Boolean)) {
  for (const nf of (x.r.new_findings || [])) newFindings.push({ ...nf, _area: x.a.key })
}
for (const cf of (conserve.findings || [])) newFindings.push({ ...cf, _area: 'conservation' })

phase('Verify')
const verified = await parallel(
  newFindings.map((f) => () => agent(verifyPrompt(f), { label: `verify:${f.id}`, phase: 'Verify', schema: VERDICT_SCHEMA, effort: 'high' })
    .then((v) => ({ ...f, survives: v?.survives === true, verdict: v })))
)
const confirmedNew = verified.filter((f) => f && f.survives)

const unresolved = []
for (const x of reaudits.filter(Boolean)) {
  for (const res of (x.r.resolutions || [])) {
    if (res.status !== 'RESOLVED' && res.status !== 'DOCUMENTED') unresolved.push({ area: x.a.key, ...res })
  }
}

log(`Round 6: ${unresolved.length} Round-5 findings not closed; ${confirmedNew.length}/${newFindings.length} new findings survived; conservation money=${conserve.money_conserved} goods=${conserve.goods_conserved} tax=${conserve.tax_conserved} deterministic=${conserve.deterministic}.`)

phase('Synthesize')
const synthesis = await agent(
  `You are the lead auditor synthesizing the Round 6 re-audit verdict for the Epocha economy base layer.

Round 5 findings not closed (only non-RESOLVED/non-DOCUMENTED shown):
${JSON.stringify(unresolved, null, 2)}

New findings that SURVIVED adversarial verification:
${JSON.stringify(confirmedNew.map((f) => ({ area: f._area, id: f.id, category: f.category, severity: f.severity, claim: f.claim, location: f.location })), null, 2)}

Conservation/reproducibility verdict: money=${conserve.money_conserved}, goods=${conserve.goods_conserved}, tax=${conserve.tax_conserved}, deterministic=${conserve.deterministic}. Reasoning: ${conserve.reasoning}

Convergence criterion: all Round 5 findings RESOLVED or honestly DOCUMENTED; no surviving new INCORRECT/UNJUSTIFIED finding; money=YES or BOUNDED_INJECTION_ONLY; goods=YES; tax=YES; deterministic=YES. Surviving new INCONSISTENT/MISSING must be listed: documentation-grade ones must be called out for a same-branch doc pass, and the verdict may be CONVERGED only if none misstates model behavior in a way that would mislead the whitepaper Methods chapter. Give per-module verdicts (production, monetary, market, distribution, conservation), the overall verdict, and an honest summary of what, if anything, still blocks promotion of whitepaper section 8.2 to a section 4.x Methods chapter.`,
  { label: 'synthesize', phase: 'Synthesize', schema: SYNTHESIS_SCHEMA, effort: 'high' }
)

return { unresolved, confirmedNew, conserve, synthesis }
