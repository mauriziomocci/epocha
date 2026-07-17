export const meta = {
  name: 'economy-base-layer-audit-round8',
  description: 'Round 8 targeted re-audit: verify the Round 7 findings (R7-NEW-1 final-period interest on repayment, R7-VAL-1 borrow boundary validation, R7-COLL-1 issue_loan guards, R7-PROP-1/2 seizure listing withdrawal + expropriation collateral clearing, R7-DET-1 SQL-sum pinning, R7-RNG-1 stream namespacing, R7-DOC-1/2 whitepaper sync and anchors) resolved or documented, hunt for new issues, deliver the convergence verdict',
  phases: [
    { title: 'Reaudit', detail: 'per-area: verify each Round 7 finding closed + hunt new issues' },
    { title: 'Conserve', detail: 'end-to-end conservation + determinism sweep' },
    { title: 'Verify', detail: 'adversarially confirm any new finding' },
    { title: 'Synthesize', detail: 'convergence verdict' },
  ],
}

const REPO = '/Users/mauriziomocci/Documents/workspace/Opensource/epocha'

const AREAS = [
  {
    key: 'maturity-interest',
    path: 'epocha/apps/economy/credit.py',
    r7: 'R7-NEW-1 (INCONSISTENT/medium): the R6 maturing-loan exclusion removed the final-period interest from the full-repayment path, so the same period was interest-bearing on rollover and interest-free on repayment (lender forfeited final interest, banking M-contraction vanished). Also: the Round 7 synthesis dismissed as a FALSE POSITIVE the claim that .exclude(due_at_tick=tick) starves open-ended NULL-due loans, and asked for a pinning regression test.',
    fix: 'Commit 21f503b: full repayment now requires and collects balance*(1+rate) -- principal ledgered as loan_repayment, final-period interest as loan_interest -- so exactly one interest charge per loan-tick holds in every maturity branch (repay, rollover, default); a borrower who can cover the balance but not the final interest falls to the rollover gate (interest affordable) or default. Pinning test test_open_ended_loans_still_serviced asserts NULL-due loans stay serviced. Regression tests: test_full_repayment_collects_final_period_interest, updated test_full_repayment_ledgered_as_loan_repayment (principal row + interest row).',
  },
  {
    key: 'borrow-boundary',
    path: 'epocha/apps/economy/credit.py',
    r7: 'R7-VAL-1 (INCORRECT/medium): the borrow amount reached evaluate_credit_request and issue_loan with no positivity/finiteness guard -- a negative amount passed the credit-limit gate trivially and DECREMENTED total_loans_outstanding at issuance (phantom capacity); NaN was approved (nan > limit is False), poisoning interest rate, cash, deposits, money supply, the solvency check and the Fisher diagnostic irreversibly. R7-COLL-1 (MISSING/low): issue_loan accepted any Property as collateral -- double-pledge prevention lived only in the engine path helper.',
    fix: 'Commit 21f503b: evaluate_credit_request rejects non-finite or non-positive amounts up front; the orchestrator borrow handler (simulation/engine.py) validates the parsed LLM target with math.isfinite/positivity and falls back to the collateral heuristic; issue_loan itself refuses invalid amounts and collateral already pledged to an active or pending-default loan (returns None, logged). Regression tests: TestBorrowAmountValidation (parametrized -100/0/nan/inf), TestIssueLoanCollateralExclusivity.',
  },
  {
    key: 'property-consistency',
    path: 'epocha/apps/economy/property_market.py',
    r7: 'R7-PROP-1 (MISSING/medium): collateral seizure did not withdraw the seized property\'s active listings, so a stale listing could sell it from under the new owner once the loan settled. R7-PROP-2/R7-XMOD-1 (INCONSISTENT/medium): process_expropriation nationalized a pledged property and defaulted its loan WITHOUT clearing the collateral FK, so the next tick\'s settlement re-seized the nationalized property FOR the lender, silently reversing the expropriation.',
    fix: 'Commit 21f503b: process_defaults withdraws live listings of every seized property; process_expropriation clears the collateral FK on the loans it defaults (the state took the security, the lender\'s loss is the gross remaining balance, which is exact since the collateral is gone). Regression tests: test_seizure_withdraws_active_listing, test_expropriation_clears_collateral_claim.',
  },
  {
    key: 'determinism-final',
    path: 'epocha/apps/economy/banking.py',
    r7: 'R7-DET-1 (INCONSISTENT/medium): SQL-side float aggregations (adjust_interest_rate per-borrower Sum, classify_minsky income Sum + unordered loan sums, evaluate_credit_request debt Sum, compute_gordon_valuation/_compute_rent_growth rent Sums) accumulate in heap-scan order, so identically-seeded runs were not bit-identical; the interest-rate path compounds ULP differences multiplicatively. R7-RNG-1 (INCONSISTENT/low): economy/rng.py derived the byte-identical key as demography/rng.py and both apps reserve the phase "initialization", so two independent model domains consumed the IDENTICAL stream. R7-DOC-1/R7-DOC-2 (low): whitepaper 4.2.2 semantics and file:line anchors were stale in the working tree.',
    fix: 'Commit 21f503b: all five SQL aggregation sites are id-ordered Python sums with determinism-pin comments; the economy RNG key is namespaced with an "economy:" prefix (regression test test_economy_and_demography_streams_differ asserts the two helpers produce different streams for the same simulation/tick/phase). The whitepaper 4.2.2 updates (single-charge servicing exclusion, affordability-gated rollover, repayment interest, cascade_origin, lien, refreshed anchors) live in the WORKING TREE in both languages: they intentionally ship inside the gated section-4.8 promotion commit that lands immediately after this audit converges -- evaluate the working-tree whitepaper text, and do NOT file the uncommitted state itself as a finding.',
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
  return `You are a HOSTILE adversarial scientific reviewer running the ROUND 8 re-audit for the Epocha economy base layer. The Round 7 re-audit confirmed the findings below; they were then fixed or documented (branch tip commit 21f503b). Your job: (1) verify EACH Round 5 finding is genuinely closed in the CURRENT code (RESOLVED for behavioral fixes, DOCUMENTED for honest disclosures), and (2) hunt for NEW defects the fixes introduced. Be adversarial: a fix that trades one error for another must be caught. Keep proportion: this layer has been through seven audit rounds -- do not re-litigate previously adjudicated design decisions (approach-A factor partition, deposits outside M, Carli index disclosure, essential-first settlement, primary-currency demand sizing, treasury-outside-M boundary); hunt only for genuine defects introduced by the LATEST two commits or missed by all prior rounds.

Repository: ${REPO}
Primary file: ${a.path} (read every other file you need: engine.py, credit.py, banking.py, monetary.py, expectations.py, models.py, migrations, tests/, docs/whitepaper/)

Round 7 findings for this area:
${a.r7}

Claimed fix:
${a.fix}

Specific adversarial angles: does the same-tick missed-interest default interact correctly with process_maturity (a loan both missing interest AND maturing this tick must not be double-processed)? Does the default_settled terminal state leak into any query that expects "defaulted" (solvency checks, Minsky classification, find_best_unpledged_property's active-loan exclusion, default_dead_agent_loans)? Does the derived broadcast RNG produce adequate dispersion across ticks (seed string collisions)? Do the migrations 0008/0009 carry any data risk for existing rows? Every new finding needs file:line and concrete evidence. Return the structured result.`
}

function conservePrompt() {
  return `You are an adversarial conservation-and-reproducibility auditor for the Epocha economy base layer (${REPO}/epocha/apps/economy/), Round 8 -- the convergence check after seven rounds of fixes. Current branch tip: commit 21f503b (final-period interest symmetry, borrow-boundary validation, seizure/expropriation consistency, SQL-sum pinning) on top of the Round 6 batch.

Verify by reading the ACTUAL current code end-to-end:
1. MONEY: net cash injected by rent/wages/profit equals zone output value V (or strictly less only via the documented wage-cap clip); taxation and property sales (including ownerless-to-treasury) are pure transfers; credit flows (issuance, interest, repayment, rollover, default write-off) are either two-legged or documented inside-money flows tracked against BankingState; defaults are processed exactly once (terminal default_settled state).
2. GOODS: trades, settlement scaling, collateral seizure move goods/property conservatively, exactly once.
3. DETERMINISM: sweep EVERY iteration order feeding order-sensitive state in the whole tick (engine zone loop, goods, currencies, agents, properties, trades, payees, tax set, credit loan querysets, cascade BFS order, banking aggregations, broadcast RNG, expectations, property market buyers/listings, all_agents/step-8 sums): is each pinned or provably order-insensitive? Would two identically-seeded runs with different PYTHONHASHSEED and different DB heap orders produce identical final state?
4. The Fisher diagnostic: MV (income velocity * M = factor income) vs PQ (sum of per-zone V_z) -- verify they are independently measured and equal under conservation in BOTH single-zone and multi-zone regimes, so divergence is a genuine defect signature.

Report money_conserved, goods_conserved, tax_conserved, deterministic, remaining findings with file:line, and your reasoning.`
}

function verifyPrompt(f) {
  return `Adversarial verifier for the Round 8 economy audit. Refute this NEW finding (default survives=false when uncertain). Read the actual code at ${REPO}/${f.location} before deciding. This layer has been through five audit rounds: previously adjudicated design decisions (approach-A partition, deposits outside M, Carli disclosure, essential-first settlement, primary-currency sizing, treasury outside M, inside-money credit flows) are settled -- a finding that re-litigates one of them does not survive. Materiality bar: a finding must either break an invariant (conservation, determinism, exactly-once), misstate model behavior in code comments/whitepaper, or leave a formula/constant unsourced and untagged.

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

log(`Round 8: ${unresolved.length} Round-7 findings not closed; ${confirmedNew.length}/${newFindings.length} new findings survived; conservation money=${conserve.money_conserved} goods=${conserve.goods_conserved} tax=${conserve.tax_conserved} deterministic=${conserve.deterministic}.`)

phase('Synthesize')
const synthesis = await agent(
  `You are the lead auditor synthesizing the Round 8 re-audit verdict for the Epocha economy base layer.

Round 7 findings not closed (only non-RESOLVED/non-DOCUMENTED shown):
${JSON.stringify(unresolved, null, 2)}

New findings that SURVIVED adversarial verification:
${JSON.stringify(confirmedNew.map((f) => ({ area: f._area, id: f.id, category: f.category, severity: f.severity, claim: f.claim, location: f.location })), null, 2)}

Conservation/reproducibility verdict: money=${conserve.money_conserved}, goods=${conserve.goods_conserved}, tax=${conserve.tax_conserved}, deterministic=${conserve.deterministic}. Reasoning: ${conserve.reasoning}

Convergence criterion: all Round 7 findings RESOLVED or honestly DOCUMENTED; no surviving new INCORRECT/UNJUSTIFIED finding; money=YES or BOUNDED_INJECTION_ONLY; goods=YES; tax=YES; deterministic=YES. Surviving new INCONSISTENT/MISSING must be listed: documentation-grade ones must be called out for a same-branch doc pass, and the verdict may be CONVERGED only if none misstates model behavior in a way that would mislead the whitepaper Methods chapter. Give per-module verdicts (production, monetary, market, distribution, conservation), the overall verdict, and an honest summary of what, if anything, still blocks promotion of whitepaper section 8.2 to a section 4.x Methods chapter.`,
  { label: 'synthesize', phase: 'Synthesize', schema: SYNTHESIS_SCHEMA, effort: 'high' }
)

return { unresolved, confirmedNew, conserve, synthesis }
