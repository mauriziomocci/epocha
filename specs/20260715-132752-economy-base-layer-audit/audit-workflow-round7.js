export const meta = {
  name: 'economy-base-layer-audit-round7',
  description: 'Round 7 targeted re-audit: verify the Round 6 findings (R6-ENG-1 first-zone lost update, R6-NEW-1/R6-ROLL-1 single interest charge + affordability-gated rollover, R6-NEW-2/R6-CASC-1 net cascade losses evaluated once, R6-COLL-1/R6-PROP-1 collateral lock + lien, R6-DET-1/2/3 + R6-RNG-1 determinism sweep, R6-MIG-1 backfill, R6-MISS-1 payee creation, R6-DOC-1) resolved or documented, hunt for new issues, deliver the convergence verdict',
  phases: [
    { title: 'Reaudit', detail: 'per-area: verify each Round 6 finding closed + hunt new issues' },
    { title: 'Conserve', detail: 'end-to-end conservation + determinism sweep' },
    { title: 'Verify', detail: 'adversarially confirm any new finding' },
    { title: 'Synthesize', detail: 'convergence verdict' },
  ],
}

const REPO = '/Users/mauriziomocci/Documents/workspace/Opensource/epocha'

const AREAS = [
  {
    key: 'engine-consistency',
    path: 'epocha/apps/economy/engine.py',
    r6: 'R6-ENG-1 (INCORRECT/high, the Round 6 blocker): the first zone\'s factor-income and tax writes (steps 4/5/5b/6) mutated AgentInventory instances loaded BEFORE the step-3 credit/property block, which reloads and saves the SAME rows -- the stale instances then overwrote the block\'s cash changes (interest debits, property-sale transfers), a lost update creating/destroying money outside every ledgered flow, invisible to the Fisher diagnostic (which checks flows, not the M base). R6-ENG-2 (low): the first zone\'s properties list fed the rent/profit partition with pre-block owners. R6-MISS-1 (low): a living factor-income payee with no AgentInventory row was silently skipped by the extended payee lookup.',
    fix: 'Commit be260db: after the credit/property block the engine re-reads the zone\'s AgentInventory rows into inv_cache and re-fetches the properties list, so downstream writes build on the block\'s committed state; the extended payee lookup now CREATES an inventory row for living payees that lack one. Regression tests: test_credit_debits_survive_factor_income_writes (ledger-based conservation identity: final agent cash == initial + factor income - taxes - banking interest), test_out_of_zone_owner_without_inventory_row_is_paid.',
  },
  {
    key: 'credit-lifecycle',
    path: 'epocha/apps/economy/credit.py',
    r6: 'R6-NEW-1 (INCORRECT/medium): on a maturity tick, service_loans charged one period\'s interest and the rollover branch charged the identical amount again (double charge, double loan_interest ledger row, double M-contraction for banking loans). R6-ROLL-1 (INCONSISTENT/medium): the rollover proceeded even when the borrower could not pay the rollover interest, contradicting the documented Minsky semantics. R6-NEW-2 (INCONSISTENT/medium): interior BFS levels propagated GROSS remaining_balance ignoring collateral, inconsistent with the net-of-collateral seed measure. R6-CASC-1 (INCORRECT/medium): a cascade-defaulted loan\'s loss was threshold-evaluated twice (in-tick BFS, then again at t+1 when its settlement records re-seeded the cascade), instantly defaulting fresh loans issued to already-cascaded lenders. R6-COLL-1 (INCORRECT/medium): find_best_unpledged_property excluded only ACTIVE-loan collateral, so pending-default collateral could be double-pledged. R6-MIG-1 (MISSING/medium): migration 0008 shipped no backfill, so pre-existing processed defaults would be re-processed once post-upgrade.',
    fix: 'Commit be260db: service_loans excludes loans with due_at_tick == tick (maturity handles them entirely); the rollover branch requires interest affordability, otherwise the loan falls through to default; interior cascade levels net the collateral value (select_related collateral); cascade-forced defaults carry the new cascade_origin flag (migration 0010) and their settlement records are skipped by the cascade seed filter; find_best_unpledged_property excludes status in [active, defaulted]; migration 0010 backfills pre-0008 processed defaults (status defaulted AND remaining_balance == 0 -> default_settled). Regression tests: TestMaturityInterestSingleCharge (2), TestCascadeLossMeasure (2), TestPendingDefaultCollateralLock.',
  },
  {
    key: 'property-lien',
    path: 'epocha/apps/economy/property_market.py',
    r6: 'R6-PROP-1 (MISSING/medium): nothing prevented listing and selling a property pledged as collateral for an active loan -- the lender\'s security could vanish through the property market while the loan stayed outstanding.',
    fix: 'Commit be260db: the matching query excludes listings whose property collateralizes an active or pending-default loan, and the sell_property handler in simulation/engine.py applies the same exclusion at listing creation (id-ordered pick). Whitepaper 4.2.2 documents the lien in both languages. Regression test: test_pledged_property_cannot_be_sold; the behavioral integration fixture gained a higher-value estate so the borrow-then-sell scenario pledges the estate and legitimately sells the lien-free mansion.',
  },
  {
    key: 'determinism-init',
    path: 'epocha/apps/economy/initialization.py',
    r6: 'R6-DET-2/R6-INIT-1 (UNJUSTIFIED/medium): initial agent cash was drawn with the module-global random.uniform over an unordered Agent queryset -- identically-seeded simulations diverged at tick 0, falsifying the whitepaper 3.4 seeded-RNG claim. R6-RNG-1 (low): the banking broadcast derived its RNG with an ad-hoc raw string instead of the project\'s sha256 scheme. R6-DET-1 (low): political_feedback iterated unordered ZoneEconomy/PriceHistory querysets. R6-DET-3 (low): initialize_economy marked EVERY template currency is_primary=True and the primary resolution used an unordered .first(). R6-DOC-1 (low): the M-scope disclosure overstated what total_loans_outstanding tracks (interest does not touch it).',
    fix: 'Commit be260db: new epocha/apps/economy/rng.py helper mirroring demography/rng.py (sha256 over sim_id:seed:tick:phase; phases initialization + banking_concern; module docstring records the epocha/common consolidation as a future refactor); initialization draws cash from the seeded RNG over an id-ordered agent list; banking broadcast uses the helper; political_feedback pins zone and price-history iteration; only the first template currency is primary and every primary resolution is id-ordered; the monetary disclosure now says interest is a pure M-contracting flow that does not touch the outstanding-principal aggregate. Regression tests: test_initial_cash_does_not_consume_global_random, test_only_first_template_currency_is_primary, TestBankingConcernBroadcastReproducibility (pre-existing).',
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
  return `You are a HOSTILE adversarial scientific reviewer running the ROUND 7 re-audit for the Epocha economy base layer. The Round 6 re-audit confirmed the findings below; they were then fixed or documented (branch tip commit be260db). Your job: (1) verify EACH Round 5 finding is genuinely closed in the CURRENT code (RESOLVED for behavioral fixes, DOCUMENTED for honest disclosures), and (2) hunt for NEW defects the fixes introduced. Be adversarial: a fix that trades one error for another must be caught. Keep proportion: this layer has been through six audit rounds -- do not re-litigate previously adjudicated design decisions (approach-A factor partition, deposits outside M, Carli index disclosure, essential-first settlement, primary-currency demand sizing, treasury-outside-M boundary); hunt only for genuine defects introduced by the LATEST two commits or missed by all prior rounds.

Repository: ${REPO}
Primary file: ${a.path} (read every other file you need: engine.py, credit.py, banking.py, monetary.py, expectations.py, models.py, migrations, tests/, docs/whitepaper/)

Round 6 findings for this area:
${a.r6}

Claimed fix:
${a.fix}

Specific adversarial angles: does the same-tick missed-interest default interact correctly with process_maturity (a loan both missing interest AND maturing this tick must not be double-processed)? Does the default_settled terminal state leak into any query that expects "defaulted" (solvency checks, Minsky classification, find_best_unpledged_property's active-loan exclusion, default_dead_agent_loans)? Does the derived broadcast RNG produce adequate dispersion across ticks (seed string collisions)? Do the migrations 0008/0009 carry any data risk for existing rows? Every new finding needs file:line and concrete evidence. Return the structured result.`
}

function conservePrompt() {
  return `You are an adversarial conservation-and-reproducibility auditor for the Epocha economy base layer (${REPO}/epocha/apps/economy/), Round 7 -- the convergence check after six rounds of fixes. Current branch tip: commit be260db (first-zone lost-update repair, credit lifecycle hardening, determinism sweep) on top of the Round 5 batch.

Verify by reading the ACTUAL current code end-to-end:
1. MONEY: net cash injected by rent/wages/profit equals zone output value V (or strictly less only via the documented wage-cap clip); taxation and property sales (including ownerless-to-treasury) are pure transfers; credit flows (issuance, interest, repayment, rollover, default write-off) are either two-legged or documented inside-money flows tracked against BankingState; defaults are processed exactly once (terminal default_settled state).
2. GOODS: trades, settlement scaling, collateral seizure move goods/property conservatively, exactly once.
3. DETERMINISM: sweep EVERY iteration order feeding order-sensitive state in the whole tick (engine zone loop, goods, currencies, agents, properties, trades, payees, tax set, credit loan querysets, cascade BFS order, banking aggregations, broadcast RNG, expectations, property market buyers/listings, all_agents/step-8 sums): is each pinned or provably order-insensitive? Would two identically-seeded runs with different PYTHONHASHSEED and different DB heap orders produce identical final state?
4. The Fisher diagnostic: MV (income velocity * M = factor income) vs PQ (sum of per-zone V_z) -- verify they are independently measured and equal under conservation in BOTH single-zone and multi-zone regimes, so divergence is a genuine defect signature.

Report money_conserved, goods_conserved, tax_conserved, deterministic, remaining findings with file:line, and your reasoning.`
}

function verifyPrompt(f) {
  return `Adversarial verifier for the Round 7 economy audit. Refute this NEW finding (default survives=false when uncertain). Read the actual code at ${REPO}/${f.location} before deciding. This layer has been through five audit rounds: previously adjudicated design decisions (approach-A partition, deposits outside M, Carli disclosure, essential-first settlement, primary-currency sizing, treasury outside M, inside-money credit flows) are settled -- a finding that re-litigates one of them does not survive. Materiality bar: a finding must either break an invariant (conservation, determinism, exactly-once), misstate model behavior in code comments/whitepaper, or leave a formula/constant unsourced and untagged.

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

log(`Round 7: ${unresolved.length} Round-6 findings not closed; ${confirmedNew.length}/${newFindings.length} new findings survived; conservation money=${conserve.money_conserved} goods=${conserve.goods_conserved} tax=${conserve.tax_conserved} deterministic=${conserve.deterministic}.`)

phase('Synthesize')
const synthesis = await agent(
  `You are the lead auditor synthesizing the Round 7 re-audit verdict for the Epocha economy base layer.

Round 6 findings not closed (only non-RESOLVED/non-DOCUMENTED shown):
${JSON.stringify(unresolved, null, 2)}

New findings that SURVIVED adversarial verification:
${JSON.stringify(confirmedNew.map((f) => ({ area: f._area, id: f.id, category: f.category, severity: f.severity, claim: f.claim, location: f.location })), null, 2)}

Conservation/reproducibility verdict: money=${conserve.money_conserved}, goods=${conserve.goods_conserved}, tax=${conserve.tax_conserved}, deterministic=${conserve.deterministic}. Reasoning: ${conserve.reasoning}

Convergence criterion: all Round 6 findings RESOLVED or honestly DOCUMENTED; no surviving new INCORRECT/UNJUSTIFIED finding; money=YES or BOUNDED_INJECTION_ONLY; goods=YES; tax=YES; deterministic=YES. Surviving new INCONSISTENT/MISSING must be listed: documentation-grade ones must be called out for a same-branch doc pass, and the verdict may be CONVERGED only if none misstates model behavior in a way that would mislead the whitepaper Methods chapter. Give per-module verdicts (production, monetary, market, distribution, conservation), the overall verdict, and an honest summary of what, if anything, still blocks promotion of whitepaper section 8.2 to a section 4.x Methods chapter.`,
  { label: 'synthesize', phase: 'Synthesize', schema: SYNTHESIS_SCHEMA, effort: 'high' }
)

return { unresolved, confirmedNew, conserve, synthesis }
