export const meta = {
  name: 'economy-base-layer-audit-round9',
  description: 'Round 9 re-audit: verify the Round 8 closures (R8-NEW-1 expropriation pending-default collateral, R8-NEW-2/CTX-1 context DRY twin, R8-DOC-1 maturity docstring, R8-NEW-3 whitepaper banking-interest claim, R8-NEW-4 whitepaper anchor refresh, R8-NEW-5 maturity catch-up) resolved or documented, audit the promoted whitepaper section 4.8, hunt for new issues, deliver the convergence verdict.',
  phases: [
    { title: 'Reaudit', detail: 'per-area: verify each Round 8 closure + hunt new issues' },
    { title: 'Conserve', detail: 'end-to-end conservation + determinism sweep' },
    { title: 'Verify', detail: 'adversarially confirm any new finding' },
    { title: 'Synthesize', detail: 'convergence verdict' },
  ],
}

const REPO = '/Users/mauriziomocci/Documents/workspace/Opensource/epocha'

const AREAS = [
  {
    key: 'expropriation-collateral',
    path: 'epocha/apps/economy/property_market.py',
    r8: 'R8-NEW-1/R8-PROP-1 (INCORRECT/medium): process_expropriation cleared the collateral FK only on loans in status "active". A loan already in the pending "defaulted" state (cascade-marked at tick t, settled by process_defaults at t+1) collateralized by an expropriated property kept its collateral claim, so the next tick re-seized the nationalized property FOR the lender -- silently reversing the nationalization. This was the one lien gate still using the bare "active" instead of the ["active","defaulted"] pair.',
    fix: 'Commit 48031f4: the collateral-clearing filter in process_expropriation is now status__in=["active","defaulted"], matching find_best_unpledged_property (credit.py:896-899), issue_loan (credit.py:301-309), the listing match gate (property_market.py:293) and sell_property (simulation/engine.py:252-254). RED-first regression test test_expropriation_clears_pending_default_collateral: a pending-default loan on the property, expropriate, then process_defaults -- asserts the property stays with the government and the collateral FK is cleared.',
  },
  {
    key: 'maturity-catchup',
    path: 'epocha/apps/economy/credit.py',
    r8: 'R8-NEW-5 (MISSING/low): process_maturity and service_loans matched the maturity tick with exact equality (due_at_tick == tick). The credit block runs only for the first zone with a living agent, so a fully agent-empty tick skips maturity; the loan due that tick was then unmatched by exact equality. (The Round 8 verifier judged the "stranded forever" premise partly refuted because default_dead_agent_loans sweeps dead-borrower loans, but the exact-equality fragility was closed as a robustness fix.)',
    fix: 'Commit 35d642b: process_maturity now matures every loan due at OR BEFORE the current tick (due_at_tick__lte=tick, a catch-up sweep); service_loans excludes the same set (.exclude(due_at_tick__lte=tick)) so the one final period is charged exactly once by the maturity step and never double-charged. RED-first tests TestMaturityCatchUp (overdue loan matures on catch-up; overdue loan not charged interest by servicing).',
  },
  {
    key: 'context-consistency',
    path: 'epocha/apps/economy/context.py',
    r8: 'R8-NEW-2/R8-CTX-1 (INCONSISTENT/low): _build_debt_block computed the best unpledged property excluding only collateralized_loans__status="active" -- a stale DRY twin of find_best_unpledged_property that R6-COLL-1 extended to ["active","defaulted"]. During the pending-default window it advertised a pledged property to the LLM as available collateral the borrow path would refuse. The active-loans queryset feeding the prompt sums was unordered. R8-DOC-1 (INCONSISTENT/low): the process_maturity docstring outcome 1 still said "repay the remaining balance" after the R7-NEW-1 change to remaining_balance*(1+rate).',
    fix: 'Commit 98da17e: context.py excludes collateralized_loans__status__in=["active","defaulted"] and pins the property sort tiebreak (-value, id) and the active-loans queryset order (id). The process_maturity docstring (credit.py) now states remaining_balance*(1+interest_rate) for outcome 1. RED-first test test_no_phantom_credit_for_pending_default_pledged_property; pinning tests for issue_loan and the orchestrator borrow fallback (R8-NEW-4/adfa coverage gap).',
  },
  {
    key: 'whitepaper-doc',
    path: 'docs/whitepaper/epocha-whitepaper.md',
    r8: 'R8-NEW-3 (INCORRECT/medium): the working-tree 4.2.2 Algorithm paragraph claimed service_loans credits banking-loan interest "to the banking system aggregate when lender_type=banking" -- false: service_loans credits the lender only when lender_type=="agent" (credit.py:430-434); for banking loans the interest is deducted and NOT re-credited (an M-contracting sink, disclosed at monetary.py R5-DISC-1 and section 5). R8-NEW-4 (INCONSISTENT/medium): the section 4.2 code anchors mixed two reference frames (some refreshed to the working tree, some still on the pinned commit 8a2bc71).',
    fix: 'Working tree (to be committed with the section-4.8 promotion): the 4.2.2 clause now reads "crediting it to the lender when lender_type=agent (for a banking-system loan the interest is deducted but not re-credited, contracting measured M by design -- see section 5 and R5-DISC-1)" in both languages; every section-4.2 code anchor was refreshed to the current working-tree line ranges (verified against source) so section 4.2 is single-frame, EN and IT anchor-identical.',
    doc: true,
  },
  {
    key: 'promotion-4.8',
    path: 'docs/whitepaper/epocha-whitepaper.md',
    r8: 'The economy base layer is being PROMOTED from section 8.2 (audit-pending) to a new section 4.8 Methods chapter (EN docs/whitepaper/epocha-whitepaper.md line ~1882, IT epocha-whitepaper.it.md line ~1949), template = section 4.7 Factions. Section 8.2 was removed and the residual section-8 count reconciled to Knowledge Graph only, in both languages.',
    fix: 'Verify section 4.8 as a Methods-grade chapter: the CES three branches (general, Cobb-Douglas log-form near sigma=1, Leontief min-of-inputs below sigma=0.05 with the <1% numerical seam), Walrasian tatonnement with the Scarf 1960 non-convergence caveat, the Ricardo 1817 rent+wages+profit partition (shares 0.6/0.15/0.25), and the Fisher 1911 MV=PQ conservation diagnostic (income velocity vs per-zone output value) must each match the code and cite a real source; the parameter table values must match the code constants; the Simplifications must disclose Carli index bias, the wage cap, mood step/discontinuity, ownerless->treasury, M-scope (deposits outside M), wash-trade exclusion, primary-currency demand, essential-first settlement. NOTE: the "round 6 / sei round" wording in the 4.8 Status header and Background line is a known placeholder updated to the real round at the convergence declaration -- do not file it as a scientific finding. The 4.8 Status pin commit is set at merge; do not file the pin SHA as a finding.',
    doc: true,
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
  return `You are a HOSTILE adversarial scientific reviewer running the ROUND 9 re-audit for the Epocha economy base layer. The Round 8 re-audit found the issues below; they were then fixed or documented in this branch (commits 48031f4, 35d642b, 98da17e plus the working-tree whitepaper corrections). Your job: (1) verify EACH Round 8 finding is genuinely closed in the CURRENT code/working tree (RESOLVED for behavioral fixes, DOCUMENTED for honest disclosures), and (2) hunt for NEW defects the latest fixes introduced. Be adversarial: a fix that trades one error for another must be caught. Keep proportion: this layer has been through eight audit rounds -- do not re-litigate previously adjudicated design decisions (approach-A factor partition wage 0.6/rent 0.15/profit 0.25, deposits outside M, Carli index disclosure, essential-first settlement, primary-currency demand sizing, treasury-outside-M boundary, inside-money credit flows, Fisher income-velocity diagnostic, default_settled terminal state, lien pair ["active","defaulted"]); hunt only for genuine defects introduced by the LATEST commits or missed by all prior rounds.

Repository: ${REPO}
Primary file: ${a.path} (read every other file you need: engine.py, credit.py, banking.py, monetary.py, property_market.py, context.py, models.py, migrations, tests/, docs/whitepaper/)

Round 8 finding(s) for this area:
${a.r8}

Claimed fix:
${a.fix}

${a.doc ? 'This is a DOCUMENTATION area: verify the whitepaper text against the ACTUAL code (function behavior, constant values, cited sources). A scientific misstatement that would mislead the Methods chapter is a real finding; a stale file:line anchor is a low-severity finding; do not file the known round-count placeholder or the merge-time pin SHA as findings.' : 'Specific adversarial angles: does the __lte maturity catch-up interact correctly with the same-tick missed-interest default (a loan both missing interest AND overdue must not be double-processed)? Does the expropriation ["active","defaulted"] clearing interact correctly with process_default_cascade (a cascade-marked loan whose collateral was just expropriated must not double-count losses)? Does the context DRY-twin exclusion now match every other lien gate exactly? Does any determinism pin still leave an order-sensitive iteration unpinned? Would two identically-seeded runs with different PYTHONHASHSEED produce identical final state?'}

Every new finding needs file:line and concrete evidence. Return the structured result.`
}

function conservePrompt() {
  return `You are an adversarial conservation-and-reproducibility auditor for the Epocha economy base layer (${REPO}/epocha/apps/economy/), Round 9 -- the convergence check after eight rounds of fixes plus the latest three commits (48031f4 expropriation pending-default collateral, 35d642b maturity __lte catch-up, 98da17e context DRY twin + docstring + guard tests).

Verify by reading the ACTUAL current code end-to-end:
1. MONEY: net cash injected by rent/wages/profit equals zone output value V (or strictly less only via the documented wage-cap clip); taxation and property sales (including ownerless-to-treasury and expropriation) are pure transfers; credit flows (issuance, interest, repayment, rollover, default write-off) are either two-legged or documented inside-money flows; defaults are processed exactly once (terminal default_settled state); the maturity catch-up charges exactly one final period per loan-tick and never double-charges when a tick is skipped.
2. GOODS: trades, settlement scaling, collateral seizure, expropriation move goods/property conservatively, exactly once; the expropriation collateral-FK clearing does not create or destroy a property claim.
3. DETERMINISM: sweep EVERY iteration order feeding order-sensitive state in the whole tick (engine zone loop, goods, currencies, agents, properties, trades, payees, tax set, credit loan querysets, maturity catch-up set, cascade BFS order, banking aggregations, broadcast RNG, expectations, property market buyers/listings, context debt block sums, all_agents/step-8 sums): is each pinned or provably order-insensitive?
4. The Fisher diagnostic: MV (income velocity * M) vs PQ (sum of per-zone V_z) -- independently measured and equal under conservation in single-zone and multi-zone regimes.

Report money_conserved, goods_conserved, tax_conserved, deterministic, remaining findings with file:line, and your reasoning.`
}

function verifyPrompt(f) {
  return `Adversarial verifier for the Round 9 economy audit. Refute this NEW finding (default survives=false when uncertain). Read the actual code at ${REPO}/${f.location} before deciding. This layer has been through eight audit rounds: previously adjudicated design decisions (approach-A partition, deposits outside M, Carli disclosure, essential-first settlement, primary-currency sizing, treasury outside M, inside-money credit flows, Fisher income-velocity diagnostic, default_settled terminal state, lien pair) are settled -- a finding that re-litigates one of them does not survive. The section-4.8 round-count placeholder and the merge-time pin SHA are not findings. Materiality bar: a finding must either break an invariant (conservation, determinism, exactly-once), misstate model behavior in code comments/whitepaper in a way that would mislead the Methods chapter, or leave a formula/constant unsourced and untagged.

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

log(`Round 9: ${unresolved.length} Round-8 findings not closed; ${confirmedNew.length}/${newFindings.length} new findings survived; conservation money=${conserve.money_conserved} goods=${conserve.goods_conserved} tax=${conserve.tax_conserved} deterministic=${conserve.deterministic}.`)

phase('Synthesize')
const synthesis = await agent(
  `You are the lead auditor synthesizing the Round 9 re-audit verdict for the Epocha economy base layer.

Round 8 findings not closed (only non-RESOLVED/non-DOCUMENTED shown):
${JSON.stringify(unresolved, null, 2)}

New findings that SURVIVED adversarial verification:
${JSON.stringify(confirmedNew.map((f) => ({ area: f._area, id: f.id, category: f.category, severity: f.severity, claim: f.claim, location: f.location })), null, 2)}

Conservation/reproducibility verdict: money=${conserve.money_conserved}, goods=${conserve.goods_conserved}, tax=${conserve.tax_conserved}, deterministic=${conserve.deterministic}. Reasoning: ${conserve.reasoning}

Convergence criterion: all Round 8 findings RESOLVED or honestly DOCUMENTED; no surviving new INCORRECT/UNJUSTIFIED finding; money=YES or BOUNDED_INJECTION_ONLY; goods=YES; tax=YES; deterministic=YES. Surviving new INCONSISTENT/MISSING must be listed: documentation-grade ones (stale anchors, wording) are called out for a same-branch doc pass and do NOT block convergence provided none misstates model behavior in a way that would mislead the whitepaper Methods chapter (section 4.8). Give per-module verdicts (production, monetary, market, distribution, credit-banking, whitepaper, conservation), the overall verdict, and an honest summary of what, if anything, still blocks the section-4.8 promotion.`,
  { label: 'synthesize', phase: 'Synthesize', schema: SYNTHESIS_SCHEMA, effort: 'high' }
)

return { unresolved, confirmedNew, conserve, synthesis }
