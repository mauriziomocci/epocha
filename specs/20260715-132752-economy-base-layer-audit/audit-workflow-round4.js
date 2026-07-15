export const meta = {
  name: 'economy-base-layer-audit-round4',
  description: 'Round 4 targeted re-audit: verify the Round 3 findings (R3-MON-NEW-1/R3-MKT-8 determinism+priority, R3-MKT-9 currency scope, R3-2 wash trades, R3-3 ownerless sale, R3-5 Fisher PQ, R3-ENG-1/R3-TAX-DOC-1 comment, R3-DIST-1 seam claim, R3-4 M scope) resolved or documented, hunt for new issues from the determinism/priority fixes, deliver the convergence verdict',
  phases: [
    { title: 'Reaudit', detail: 'per-area: verify each Round 3 finding closed + hunt new issues' },
    { title: 'Conserve', detail: 'end-to-end conservation + reproducibility sanity' },
    { title: 'Verify', detail: 'adversarially confirm any new finding' },
    { title: 'Synthesize', detail: 'convergence verdict' },
  ],
}

const REPO = '/Users/mauriziomocci/Documents/workspace/Opensource/epocha'

const AREAS = [
  {
    key: 'settlement-determinism',
    path: 'epocha/apps/economy/engine.py',
    r3: 'R3-MON-NEW-1 / R3-MKT-8 (INCORRECT/medium, the Round 3 blocker): the MKT-7 affordability guard made final allocations depend on trade application order, while execute_trades iterated goods via an unordered str set (PYTHONHASHSEED-dependent) and the agent/property querysets were unordered -- identically-seeded runs could diverge, and a cash-constrained buyer\'s access to essential goods was a hash-order lottery. R3-MKT-9 (low): demand was sized on the sum of ALL currencies while settlement debits only the primary currency.',
    fix: 'Commit e4fc120: market.py iterates goods in sorted() order; engine.py orders the per-zone agent and property querysets by id; the engine settlement loop stable-sorts trades by (essential-first, good_code) before applying, so essentials settle before discretionary purchases consume a constrained buyer\'s cash; demand sizing now reads only the primary currency (inv.cash.get(primary)). Regression tests: test_execute_trades_iterates_goods_in_sorted_order, test_settlement_prioritizes_essentials_for_cash_constrained_buyer (adversarial luxury-first trade order via patch), test_demand_sized_on_primary_currency_cash.',
  },
  {
    key: 'wash-and-property',
    path: 'epocha/apps/economy/market.py',
    r3: 'R3-2 (low): an agent could both offer and demand the same non-essential good, so the two-pointer sweep could match it against itself -- a wash trade netting to zero on inventory but inflating measured transaction volume and hence velocity. R3-3 (low): property_market.py debited the buyer of an ownerless (government/public) listing while the seller-guard skipped the credit, destroying money (same class as fixed CM-TAX-2).',
    fix: 'Commit e4fc120: collect_supply_and_demand skips discretionary demand for any good the agent itself offers (documented rationale: a keeper hoards, it does not buy from itself); process_property_listings credits the government treasury for an ownerless sale and skips the sale entirely (failed count) when no Government exists, before any debit. Regression tests: test_agent_does_not_demand_good_it_offers, test_ownerless_sale_credits_treasury, test_ownerless_sale_skipped_without_government.',
  },
  {
    key: 'fisher-and-m-scope',
    path: 'epocha/apps/economy/monetary.py',
    r3: 'R3-5 (low): the Fisher PQ side used the unweighted mean of system prices times the summed heterogeneous physical quantities, conflating price-aggregation error with monetary inconsistency (the 20% warning threshold was meaningless). R3-4 (low): compute_circulating_money_supply\'s docstring did not disclose that measured M excludes the government treasury and dead agents\' cash, so taxation shrinks M by design.',
    fix: 'Commit e4fc120 (engine.py): the engine accumulates per-good system output and computes PQ = sum_g(p_g * q_g) with system_price_level = PQ/Q (output-weighted Paasche-type index), so price_level*output_level reproduces the nominal output value exactly; regression test test_fisher_pq_is_output_weighted_nominal_value. Commit 97d2acc (monetary.py): the docstring now discloses the M scope (living agents only; treasury and dead agents\' cash outside circulation by design, with the inheritance work item named).',
  },
  {
    key: 'doc-precision',
    path: 'epocha/apps/economy/production.py',
    r3: 'R3-ENG-1 / R3-TAX-DOC-1 (low, duplicates): the engine comment attributed a dead owner\'s share reallocation solely to compute_profit\'s no-landlord fallback, but with a surviving co-claimant the share renormalizes to living owners via _distribute_proportional_to_bonus; the fallback only fires when no living property claims the good. R3-DIST-1 (low): production.py claimed the CES branch seam was covered by test_ces_leontief_limit_continuity, but that test evaluates the degenerate all-equal-inputs point where the seam is zero by construction.',
    fix: 'Commit e4fc120 (engine.py comment): the dead-owner comment now names both reallocation paths, with a co-owner regression test (test_dead_owner_share_renormalizes_to_surviving_claimant) asserting the survivor collects rent, the dead owner nothing, and the partition still sums to V. Commit 97d2acc (production.py): the comment distinguishes the degenerate-point continuity test from the new heterogeneous-inputs seam-bound test (test_ces_leontief_seam_bounded_for_heterogeneous_inputs: seam positive and below 1% relative).',
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
    deterministic: { type: 'string', enum: ['YES', 'NO'], description: 'YES iff every iteration order feeding order-sensitive state is pinned (sorted goods, id-ordered querysets, stable trade sort)' },
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
  return `You are a HOSTILE adversarial scientific reviewer running the ROUND 4 re-audit for the Epocha economy base layer. The Round 3 re-audit confirmed the findings below; they were then fixed or documented (branch tip commits e4fc120 and 97d2acc). Your job: (1) verify EACH Round 3 finding is genuinely closed in the CURRENT code (RESOLVED for behavioral fixes, DOCUMENTED for honest disclosures), and (2) hunt for NEW defects the fixes introduced. Be adversarial: a fix that trades one error for another must be caught.

Repository: ${REPO}
Primary file: ${a.path} (read every other file you need: engine.py, distribution.py, market.py, monetary.py, production.py, property_market.py, tests/)

Round 3 findings for this area:
${a.r3}

Claimed fix:
${a.fix}

Specific adversarial angles: does the essential-first stable sort interact correctly with the two-pointer per-good matching order (intra-good order preserved)? Is any remaining iteration order feeding order-sensitive state still unpinned (dict iteration over rents/wages/profits is insertion-ordered from id-ordered inputs -- verify; set(list+list) over int agent ids in the tax step -- is that deterministic in CPython)? Does the primary-currency demand sizing regress any multi-currency behavior other modules rely on? Does skipping self-demand change the tatonnement price signal in a way that contradicts a documented claim? Does the ownerless-sale treasury credit keep the ledger consistent (to_agent None, transaction type)? Every new finding needs file:line and concrete evidence. Return the structured result.`
}

function conservePrompt() {
  return `You are an adversarial conservation-and-reproducibility auditor for the Epocha economy base layer (${REPO}/epocha/apps/economy/), Round 4. Prior rounds fixed: >2V factor-income double-injection (partition summing to V), N*M goods fabrication, taxation asymmetries (running-total treasury credit, gov-gated), settlement overspend (affordability guard), and -- at the branch tip -- settlement nondeterminism (sorted goods, id-ordered querysets, essential-first stable trade sort), wash trades, the ownerless-property sale leak, and the Fisher PQ aggregation.

Verify by reading the ACTUAL current code end-to-end:
1. MONEY: net cash injected by rent/wages/profit equals zone output value V (or strictly less only via the documented wage-cap clip); taxation is a pure transfer; the ownerless property sale now credits the treasury; no remaining from_agent=None credit lacks a documented source.
2. GOODS: execute_trades + settlement (affordability down-scaling, essential-first ordering) move goods conservatively.
3. DETERMINISM: trace every iteration order that feeds order-sensitive state in the tick (goods loops, agent/property querysets, trades application, rents/wages/profits dict iteration, the tax set(list+list) over int ids, payee_invs fetch, all_agents loop) -- is each pinned or provably order-insensitive? Would two identically-seeded runs with different PYTHONHASHSEED produce identical final state?
4. The live M aggregate, velocity, and the corrected Fisher diagnostic run against the post-fix flows.

Report money_conserved, goods_conserved, tax_conserved, deterministic, remaining findings with file:line, and your reasoning.`
}

function verifyPrompt(f) {
  return `Adversarial verifier for the Round 4 economy audit. Refute this NEW finding (default survives=false when uncertain). Read the actual code at ${REPO}/${f.location} before deciding.

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

log(`Round 4: ${unresolved.length} Round-3 findings not closed; ${confirmedNew.length}/${newFindings.length} new findings survived; conservation money=${conserve.money_conserved} goods=${conserve.goods_conserved} tax=${conserve.tax_conserved} deterministic=${conserve.deterministic}.`)

phase('Synthesize')
const synthesis = await agent(
  `You are the lead auditor synthesizing the Round 4 re-audit verdict for the Epocha economy base layer.

Round 3 findings not closed (only non-RESOLVED/non-DOCUMENTED shown):
${JSON.stringify(unresolved, null, 2)}

New findings that SURVIVED adversarial verification:
${JSON.stringify(confirmedNew.map((f) => ({ area: f._area, id: f.id, category: f.category, severity: f.severity, claim: f.claim, location: f.location })), null, 2)}

Conservation/reproducibility verdict: money=${conserve.money_conserved}, goods=${conserve.goods_conserved}, tax=${conserve.tax_conserved}, deterministic=${conserve.deterministic}. Reasoning: ${conserve.reasoning}

Convergence criterion: all Round 3 findings RESOLVED or honestly DOCUMENTED; no surviving new INCORRECT/UNJUSTIFIED finding; money=YES or BOUNDED_INJECTION_ONLY; goods=YES; tax=YES; deterministic=YES. Surviving new INCONSISTENT/MISSING must be listed and assessed: if they are documentation-grade they must be called out for a same-branch documentation pass, and the verdict may be CONVERGED only if none of them misstates model behavior in a way that would mislead the whitepaper Methods chapter. Give per-module verdicts (production, monetary, market, distribution, conservation), the overall verdict, and an honest summary of what, if anything, still blocks promotion of whitepaper section 8.2 to a section 4.x Methods chapter.`,
  { label: 'synthesize', phase: 'Synthesize', schema: SYNTHESIS_SCHEMA, effort: 'high' }
)

return { unresolved, confirmedNew, conserve, synthesis }
