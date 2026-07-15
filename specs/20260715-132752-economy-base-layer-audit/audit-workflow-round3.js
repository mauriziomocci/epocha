export const meta = {
  name: 'economy-base-layer-audit-round3',
  description: 'Round 3 targeted re-audit: verify each Round 2 finding (CM-TAX-1/2, NEW-2/3/4/5, MKT-7, PROD-5) resolved or documented, re-verify end-to-end conservation including the taxation step, hunt for new issues from the payee-lookup and settlement-guard fixes, synthesize the convergence verdict',
  phases: [
    { title: 'Reaudit', detail: 'per-area: verify each Round 2 finding closed + hunt new issues' },
    { title: 'Conserve', detail: 'end-to-end money/goods conservation incl. taxation step' },
    { title: 'Verify', detail: 'adversarially confirm any new finding' },
    { title: 'Synthesize', detail: 'convergence verdict' },
  ],
}

const REPO = '/Users/mauriziomocci/Documents/workspace/Opensource/epocha'

const AREAS = [
  {
    key: 'conservation-tax',
    path: 'epocha/apps/economy/engine.py',
    r2: 'CM-TAX-1 (INCORRECT/medium): the taxation step credited the treasury with compute_taxes total_revenue over ALL imputed incomes while the debit loop only fired for earners present in the zone-local living-agent cache, so income imputed to a dead or out-of-zone rent owner was credited to the treasury with no matching agent debit (money creation). CM-TAX-2 (INCORRECT/low): with a TaxPolicy but no Government, the debit loop still stripped every in-zone earner while the `if gov` guard skipped the treasury credit (money destruction).',
    fix: 'Commit e655683: taxation runs only when a Government exists (no gov -> no tax at all); the treasury is credited with the RUNNING TOTAL of taxes actually debited, never the nominal total_revenue; the debit loop resolves earners through the extended simulation-wide payee lookup. Regression tests: test_treasury_credit_equals_agent_tax_debits, test_no_government_skips_taxation in tests/test_engine.py.',
  },
  {
    key: 'distribution-owners',
    path: 'epocha/apps/economy/engine.py',
    r2: 'NEW-3 (MISSING/medium): rent and profit owed to a living owner resident in another zone (or dead) were silently dropped because the credit lookup used the zone-local is_alive-only inv_cache while Property.owner_id can point outside it. NEW-5 (MISSING/low): land/capital income of goods produced under government/non-agent property was attributed to labourers without a stated assumption.',
    fix: 'Commit e655683: property owners are resolved against the simulation-wide living-agent set; dead owners are excluded from the partition so their share is reallocated by compute_profit\'s no-landlord fallback (partition still sums to V); living out-of-zone owners are paid through an extended simulation-wide payee lookup (payee_invs) also used by wages/profit/tax. Regression tests: test_out_of_zone_owner_receives_rent, test_dead_owner_share_reallocated_not_dropped. NEW-5 closed by documentation (commit a7aa752): distribution.py module docstring + engine.py comment state the modeling assumption that public/ownerless land income accrues to producers via the no-landlord fallback, and that routing it to the treasury would be a deliberate fiscal-policy change.',
  },
  {
    key: 'distribution-invariant',
    path: 'epocha/apps/economy/distribution.py',
    r2: 'NEW-2 (INCONSISTENT/low): the engine\'s wage sanity-cap (100x median) can clip credited cash strictly below V, contradicting the module docstring claim that the credited total "equals V exactly". NEW-4 (INCONSISTENT/low): residual numerical discontinuity between the Leontief branch and the general CES evaluated at sigma=0.05 was undocumented after the Round 1 form fix.',
    fix: 'Commit a7aa752 (documentation): distribution.py module docstring now qualifies the identity as "injection <= V, equal whenever the cap is not binding" with the clipped remainder deliberately not redistributed, and the engine wage-cap comment states the same; production.py documents the bounded seam at the threshold (power mean at rho=-19 vs exact min), the overflow rationale for the limit branch, the threshold as a tunable numerical-stability parameter, and points to the continuity regression test.',
  },
  {
    key: 'market-settlement',
    path: 'epocha/apps/economy/market.py',
    r2: 'MKT-7 (INCONSISTENT/low): discretionary demand is sized at pre-clearing prices (and essential demand is not cash-sized at all) but trades settle at equilibrium prices with no guard on the buyer cash, so realized spend could exceed the documented budget bound and drive buyer cash negative, contradicting the "never exceeds" docstring claim.',
    fix: 'Commit 8255d5f: the engine trade-application loop scales each trade down to the buyer\'s remaining cash (skip when no cash), with the unsold quantity staying with the seller so goods stay conserved; collect_supply_and_demand\'s docstring now states its budget bound holds at the sizing prices and the realized bound is enforced by the settlement guard. Regression test: test_buyer_trade_spend_bounded_by_cash (pins equilibrium price above buyer cash).',
  },
  {
    key: 'monetary-mood',
    path: 'epocha/apps/economy/monetary.py',
    r2: 'PROD-5 (INCONSISTENT/low): compute_mood_delta\'s per-tick boost doubles from _MOOD_BOOST_BASE*0.5 (moderate band) to the full _MOOD_BOOST_BASE exactly at satiation_threshold before decaying -- a non-monotonic upward bump contradicting the Kahneman-Deaton plateau narrative, undisclosed by the Round 1 docstring rewrite.',
    fix: 'Commit a7aa752 (documentation): the docstring now discloses the discontinuity, its magnitude (boost momentarily doubles at the threshold), that it is locally at odds with the plateau narrative while the asymptotic plateau still holds, names the continuous alternative (start the decay branch at _MOOD_BOOST_BASE*0.5), and tags the current form a tunable heuristic kept deliberately.',
  },
]

const FINDINGS_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['area', 'resolutions', 'new_findings'],
  properties: {
    area: { type: 'string' },
    resolutions: {
      type: 'array', description: 'one entry per Round 2 finding for this area',
      items: {
        type: 'object', additionalProperties: false, required: ['finding', 'status', 'evidence'],
        properties: {
          finding: { type: 'string' },
          status: { type: 'string', enum: ['RESOLVED', 'DOCUMENTED', 'PARTIALLY_RESOLVED', 'NOT_RESOLVED', 'REGRESSED'] },
          evidence: { type: 'string', description: 'file:line and what the current code/docs now do' },
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
  type: 'object', additionalProperties: false, required: ['money_conserved', 'goods_conserved', 'tax_conserved', 'findings', 'reasoning'],
  properties: {
    money_conserved: { type: 'string', enum: ['YES', 'NO', 'BOUNDED_INJECTION_ONLY'] },
    goods_conserved: { type: 'string', enum: ['YES', 'NO'] },
    tax_conserved: { type: 'string', enum: ['YES', 'NO'], description: 'YES iff every treasury credit has a matching sum of agent debits and no-gov implies no taxation' },
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
  return `You are a HOSTILE adversarial scientific reviewer running the ROUND 3 re-audit for the Epocha economy base layer. The Round 2 re-audit confirmed the findings below; they were then fixed or documented. Your job: (1) verify EACH Round 2 finding is genuinely closed in the CURRENT code (RESOLVED for behavioral fixes, DOCUMENTED for disclosed simplifications -- a disclosure must be honest, specific and cite what is lost, not hand-waving), and (2) hunt for NEW defects the fixes introduced. Be adversarial: a fix that trades one error for another must be caught.

Repository: ${REPO}
Primary file: ${a.path} (read every other file you need: engine.py, distribution.py, market.py, monetary.py, production.py, tests/test_engine.py)

Round 2 findings for this area:
${a.r2}

Claimed fix:
${a.fix}

Specific adversarial angles to check for new defects: does the simulation-wide payee lookup interact correctly with the multi-zone loop (an owner credited by zone A being re-read fresh when zone B processes, no stale-object lost-update between payee_invs and inv_cache for the SAME in-zone agent)? Does the settlement affordability guard preserve goods conservation and the trade ledger consistency (scaled qty vs recorded price*qty)? Does excluding dead owners from the partition keep sum(rent)+sum(wages)+sum(profit)==V in every branch? Does gating taxation on Government change any documented behavior that other modules rely on? Every new finding needs file:line and concrete evidence. Return the structured result.`
}

function conservePrompt() {
  return `You are an adversarial conservation auditor for the Epocha economy base layer (${REPO}/epocha/apps/economy/), Round 3. Rounds 1-2 fixed: >2V factor-income double-injection (partition summing to V), N*M goods fabrication (two-pointer rationed sweep), and -- in the current branch tip -- the taxation asymmetries (treasury credited more than debited for owners absent from the payee lookup; debits without treasury credit when no Government exists) plus a settlement affordability guard that scales trades to the buyer's remaining cash.

Verify by reading the ACTUAL current code end-to-end (engine.py steps 1-9, distribution.py, market.py, monetary.py):
1. MONEY: per tick, net cash injected by rent/wages/profit equals the zone output value V (or strictly less ONLY via the documented wage-cap clip), with no path injecting more than V and no double-credit. Trace every from_agent=None credit and every debit, including the extended simulation-wide payee lookup for out-of-zone owners and the dead-owner exclusion.
2. TAX: taxation is a pure transfer -- treasury credit == sum of agent debits, always; with no Government nothing is debited or credited. Check the running-total implementation.
3. GOODS: execute_trades + the engine settlement (including the affordability down-scaling) move goods conservatively: nothing fabricated, seller decrements match buyer increments, unsold scaled-off quantity stays with the seller.
4. The live M aggregate and the Fisher diagnostic still run against the post-fix flows.

Report money_conserved (YES/NO/BOUNDED_INJECTION_ONLY), goods_conserved, tax_conserved, remaining findings with file:line, and your reasoning tracing the flows.`
}

function verifyPrompt(f) {
  return `Adversarial verifier for the Round 3 economy audit. Refute this NEW finding (default survives=false when uncertain). Read the actual code at ${REPO}/${f.location} before deciding.

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

log(`Round 3: ${unresolved.length} Round-2 findings not closed; ${confirmedNew.length}/${newFindings.length} new findings survived; conservation money=${conserve.money_conserved} goods=${conserve.goods_conserved} tax=${conserve.tax_conserved}.`)

phase('Synthesize')
const synthesis = await agent(
  `You are the lead auditor synthesizing the Round 3 re-audit verdict for the Epocha economy base layer.

Round 2 findings not closed (only non-RESOLVED/non-DOCUMENTED shown):
${JSON.stringify(unresolved, null, 2)}

New findings that SURVIVED adversarial verification:
${JSON.stringify(confirmedNew.map((f) => ({ area: f._area, id: f.id, category: f.category, severity: f.severity, claim: f.claim, location: f.location })), null, 2)}

Conservation verdict: money=${conserve.money_conserved}, goods=${conserve.goods_conserved}, tax=${conserve.tax_conserved}. Reasoning: ${conserve.reasoning}

Convergence criterion: a module is CONVERGED if all its Round 2 findings are RESOLVED or honestly DOCUMENTED and it has no surviving new INCORRECT/UNJUSTIFIED finding (new INCONSISTENT/MISSING may be documented in a follow-up pass but must be listed). The layer is CONVERGED only if all five modules (production, monetary, market, distribution, conservation-as-cross-cutting) converge AND money=YES or BOUNDED_INJECTION_ONLY, goods=YES, tax=YES. Give per-module verdicts, the overall verdict, and an honest summary of what, if anything, still blocks promotion from whitepaper section 8.2 to a section 4.x Methods chapter.`,
  { label: 'synthesize', phase: 'Synthesize', schema: SYNTHESIS_SCHEMA, effort: 'high' }
)

return { unresolved, confirmedNew, conserve, synthesis }
