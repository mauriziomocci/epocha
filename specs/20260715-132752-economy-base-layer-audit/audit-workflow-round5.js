export const meta = {
  name: 'economy-base-layer-audit-round5',
  description: 'Round 5 targeted re-audit: verify the Round 4 findings (R4-DET-1/2 iteration orders, R4-FISH-1 Fisher rewire, wash-trade trade-off note, ownerless-sale whitepaper sync, loan_repayment ledger type, template fallback, M-scope caveats, seam docstring arithmetic) resolved or documented, hunt for new issues, deliver the convergence verdict',
  phases: [
    { title: 'Reaudit', detail: 'per-area: verify each Round 4 finding closed + hunt new issues' },
    { title: 'Conserve', detail: 'end-to-end conservation + full determinism trace' },
    { title: 'Verify', detail: 'adversarially confirm any new finding' },
    { title: 'Synthesize', detail: 'convergence verdict' },
  ],
}

const REPO = '/Users/mauriziomocci/Documents/workspace/Opensource/epocha'

const AREAS = [
  {
    key: 'determinism-sweep',
    path: 'epocha/apps/economy/engine.py',
    r4: 'R4-DET-1 (INCORRECT/medium): the zone loop was built from an unordered ZoneEconomy queryset while feeding order-sensitive state (credit/property block after the first non-empty zone; cross-zone factor incomes). R4-DET-2 (INCORRECT/medium): property-market buyer iteration came from an unordered DecisionLog queryset and equal-price listings had no id tiebreak. Conservation verifier also flagged: unordered Loan querysets in service_loans/process_maturity/process_defaults; broadcast_banking_concern sampling an unordered agent list; expectations.py retaining the last-zone-wins price merge; step-8 unordered float sums (all_agents, property values) leaving M/median ULP-unstable; goods/currencies catalogs unordered.',
    fix: 'Commit d6341db: zone_economies, goods, currencies, all_agents, per-zone agents/properties, property_values_by_owner, Loan querysets (3x), and the banking broadcast pool are all order_by("id"); property-market buyers order_by("agent_id","id") and listing selection order_by("asking_price","id"); expectations.py aggregates prices with monetary.aggregate_system_prices over an id-ordered queryset (same CM-5 fix as the engine) with regression test test_first_expectation_uses_cross_zone_mean_price; listing tiebreak regression test test_equal_price_listings_resolve_by_lowest_id.',
  },
  {
    key: 'fisher-rewire',
    path: 'epocha/apps/economy/monetary.py',
    r4: 'R4-FISH-1 (INCONSISTENT/medium): with velocity measured as volume/M, M cancels out of MV identically so the check could never detect an M error, and the turnover volume (trades + factor incomes) was compared against income-form PQ, firing spurious warnings whenever trade volume exceeded ~25% of nominal output in a perfectly conserved economy. Also: compute_circulating_money_supply docstring claimed numeric identity with BankingState.total_deposits (which sums ALL currencies while M is per-currency); banking loan issuance/repayment money creation/destruction was absent from the M-scope disclosure.',
    fix: 'Commit d6341db: engine.py step 8a now tracks factor_income_volume (rent+wages+profit credits) separately and passes income_velocity = factor_income_volume / M to check_fisher_consistency, so MV equals the tick\'s factor-income injection and PQ the nominal output value -- divergence is exactly the CM-1 conservation-defect signature; the tautology of measured-velocity MV=PQ is documented in both engine comment and check_fisher_consistency docstring; the turnover velocity remains on Currency.cached_velocity as a metric only. The M docstring now carries the single-currency scope caveat versus the all-currency deposits mirror and the deliberate Diamond-Dybvig credit-money expansion/contraction disclosure. Regression test test_fisher_mv_equals_factor_income_injection (MV == PQ in the conserved fixture).',
  },
  {
    key: 'credit-property-ledger',
    path: 'epocha/apps/economy/credit.py',
    r4: 'Round 4 confirmed: full principal repayment ledgered as transaction_type="loan_interest" (misclassification); the credit/banking template-config fallback read EconomyTemplate.objects.all()[:1], an unordered simulation-agnostic pick; the R3-2 self-demand skip lacked a documented trade-off note (net excess demand shifted, budget share dropped); whitepaper section 4.2.3 and the section 3.3 treasury-contract table still described the pre-R3-3 behavior (sale always credits the seller, no ownerless/treasury branch) in both languages; the TestLeontiefSeamBound docstring misstated the seam arithmetic (rho=-19 belongs to sigma=0.05, not 0.06).',
    fix: 'Commit d6341db: repayment ledgered as "loan_repayment" (new TRANSACTION_TYPES choice + migration 0007) with RED-first test test_full_repayment_ledgered_as_loan_repayment; fallback now order_by("id")[:1] with a comment documenting the simulation-agnostic legacy limitation and the unreachable-for-initialized-simulations primary path; the R3-2 comment in market.py now documents the demand-signal and dropped-budget-share trade-offs; both whitepapers updated (treasury table row names the property_market caller; the 4.2.3 algorithm paragraph describes the ownerless-treasury branch, the no-Government skip, and the deterministic buyer/listing ordering); the test docstring arithmetic corrected (rho=-19 at the 0.05 threshold, -15.67 at the 0.06 used).',
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
  return `You are a HOSTILE adversarial scientific reviewer running the ROUND 5 re-audit for the Epocha economy base layer. The Round 4 re-audit confirmed the findings below; they were then fixed or documented (branch tip commit d6341db). Your job: (1) verify EACH Round 4 finding is genuinely closed in the CURRENT code (RESOLVED for behavioral fixes, DOCUMENTED for honest disclosures), and (2) hunt for NEW defects the fixes introduced. Be adversarial but PROPORTIONATE: this is round 5 of a convergence loop -- flag only defects that are real, material and actionable, not stylistic preferences or restatements of already-documented trade-offs.

Repository: ${REPO}
Primary file: ${a.path} (read every other file you need across epocha/apps/economy/ and docs/whitepaper/)

Round 4 findings for this area:
${a.r4}

Claimed fix:
${a.fix}

Specific adversarial angles: does the income-velocity Fisher rewire keep Currency.cached_velocity semantics coherent with its consumers (check who reads cached_velocity)? Does the expectations aggregation change any documented behavior 4.2.1 relies on (whitepaper doc-sync)? Is the loan_repayment migration consistent (choices change only, no data backfill needed for historical loan_interest rows -- is that acceptable and documented)? Any iteration order still unpinned that feeds order-sensitive state (trace the full tick once more)? Every new finding needs file:line and concrete evidence. Return the structured result.`
}

function conservePrompt() {
  return `You are an adversarial conservation-and-reproducibility auditor for the Epocha economy base layer (${REPO}/epocha/apps/economy/), Round 5 (branch tip commit d6341db). All prior conservation invariants held at Round 4 (money=BOUNDED_INJECTION_ONLY, goods=YES, tax=YES); determinism failed on: unordered zone loop, property-market buyer/listing order, loan querysets, banking broadcast pool, expectations last-zone-wins merge, step-8 float-sum order. All were fixed with order pins and the aggregate_system_prices reuse.

Verify by reading the ACTUAL current code end-to-end, tracing the full tick once more (engine.py steps 0-9 plus every helper it calls: expectations, market, distribution, credit, banking, property_market, monetary):
1. MONEY/GOODS/TAX invariants still hold after the Round 4 changes.
2. DETERMINISM: enumerate every remaining iteration over querysets, dicts, or sets that feeds order-sensitive state (cash mutations, matching, sampling, float accumulation into persisted values) and confirm each is pinned or provably order-insensitive. Sets of Python ints are deterministically ordered for identical contents; str-keyed dicts preserve insertion order from pinned inputs -- apply these facts precisely rather than flagging every dict.
3. The rewired Fisher diagnostic reads ~zero divergence in a conserved economy and fires on an injection != V defect.

Report money_conserved, goods_conserved, tax_conserved, deterministic, remaining findings with file:line, and your reasoning. Be proportionate: round 5 of a convergence loop -- only real, material, actionable defects.`
}

function verifyPrompt(f) {
  return `Adversarial verifier for the Round 5 economy audit. Refute this NEW finding (default survives=false when uncertain). Read the actual code at ${REPO}/${f.location} before deciding.

Finding: [${f.category}/${f.severity}] ${f.claim}
Location: ${f.location}
Evidence: ${f.evidence}

Survival requires BOTH source-accuracy AND materiality: a finding that restates an already-documented trade-off, or whose impact is not observable in simulation state or published documentation, does not survive. Return survives, confidence, reasoning.`
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

log(`Round 5: ${unresolved.length} Round-4 findings not closed; ${confirmedNew.length}/${newFindings.length} new findings survived; conservation money=${conserve.money_conserved} goods=${conserve.goods_conserved} tax=${conserve.tax_conserved} deterministic=${conserve.deterministic}.`)

phase('Synthesize')
const synthesis = await agent(
  `You are the lead auditor synthesizing the Round 5 re-audit verdict for the Epocha economy base layer.

Round 4 findings not closed (only non-RESOLVED/non-DOCUMENTED shown):
${JSON.stringify(unresolved, null, 2)}

New findings that SURVIVED adversarial verification:
${JSON.stringify(confirmedNew.map((f) => ({ area: f._area, id: f.id, category: f.category, severity: f.severity, claim: f.claim, location: f.location })), null, 2)}

Conservation/reproducibility verdict: money=${conserve.money_conserved}, goods=${conserve.goods_conserved}, tax=${conserve.tax_conserved}, deterministic=${conserve.deterministic}. Reasoning: ${conserve.reasoning}

Convergence criterion: all Round 4 findings RESOLVED or honestly DOCUMENTED; no surviving new INCORRECT/UNJUSTIFIED finding; money=YES or BOUNDED_INJECTION_ONLY; goods=YES; tax=YES; deterministic=YES. Surviving new INCONSISTENT/MISSING items must be listed with an explicit assessment of whether they are documentation-grade (closable by a same-branch doc pass) or model defects. Give per-module verdicts (production, monetary, market, distribution, conservation), the overall verdict, and an honest summary of what, if anything, still blocks promotion of whitepaper section 8.2 to a section 4.x Methods chapter.`,
  { label: 'synthesize', phase: 'Synthesize', schema: SYNTHESIS_SCHEMA, effort: 'high' }
)

return { unresolved, confirmedNew, conserve, synthesis }
