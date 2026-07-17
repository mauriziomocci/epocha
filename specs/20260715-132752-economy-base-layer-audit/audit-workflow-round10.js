export const meta = {
  name: 'economy-base-layer-audit-round10',
  description: 'Round 10 re-audit: verify the two Round 9 survivors closed (R9-NEW-1 collateral-selection id tiebreak, R9-NEW-2/R9-DOC-1 whitepaper 4.2.2 maturity __lte doc-sync), re-verify the section-4.8 promotion is Methods-grade and single-frame, full conservation/determinism sweep, deliver the convergence verdict.',
  phases: [
    { title: 'Reaudit', detail: 'verify the two Round 9 survivors + hunt new issues' },
    { title: 'Conserve', detail: 'end-to-end conservation + determinism completeness sweep' },
    { title: 'Verify', detail: 'adversarially confirm any new finding' },
    { title: 'Synthesize', detail: 'convergence verdict' },
  ],
}

const REPO = '/Users/mauriziomocci/Documents/workspace/Opensource/epocha'

const AREAS = [
  {
    key: 'collateral-tiebreak',
    path: 'epocha/apps/economy/credit.py',
    r9: 'R9-NEW-1 (INCONSISTENT/medium): find_best_unpledged_property -- the authoritative borrow-path collateral selector (consumed at simulation/engine.py:193 -> issue_loan) -- sorted .order_by("-value") with no id tiebreak, while its context twin (context.py, pinned to ("-value","id") in commit 98da17e) and every sibling selection gate (sell_property simulation/engine.py, the listing match property_market.py) are id-pinned. On an exact value tie Postgres returned tied rows in unspecified physical order, so the pledged collateral (and the default-seizure path it drives) was not reproducible across identically-seeded runs, and could disagree with the property the LLM context advertised as best.',
    fix: 'Commit 137c277: find_best_unpledged_property now sorts .order_by("-value","id") (credit.py:916 region), matching the context twin and every sibling gate. Determinism-pin regression test test_find_unpledged_property_deterministic_on_value_tie asserts the lowest id wins a value tie.',
    angle: 'Verify the fix, then sweep the WHOLE economy package for any REMAINING property/agent/loan selector that ends in .first()/[0]/.last() or feeds order-sensitive persisted state without a total-order tiebreak (order_by on a non-unique key with no id). Report every unpinned order-sensitive selector as a finding with file:line. Also confirm the id tiebreak did not change the normal (distinct-value) selection.',
  },
  {
    key: 'whitepaper',
    path: 'docs/whitepaper/epocha-whitepaper.md',
    r9: 'R9-NEW-2 / R9-DOC-1 (INCONSISTENT/medium): the section-4.2 Algorithm paragraph (being promoted 8.2->4.2 Methods in this branch) still described service_loans as excluding, and process_maturity as matching, loans whose "due_at_tick equals the current tick", contradicting commit 35d642b (R8-NEW-5) which moved both to due_at_tick__lte=tick; a reader reimplementing from the paper would use == and reopen the overdue-loan stranding the fix closed.',
    fix: 'Working tree (to be committed with the section-4.8 promotion): the 4.2.2 Algorithm "Second" (service_loans) and "Third" (process_maturity) sentences now describe the due_at_tick <= tick catch-up sweep in both languages (EN line ~949, IT line ~985).',
    angle: 'Verify the two 4.2.2 sentences now match the code (service_loans excludes due_at_tick__lte=tick at credit.py:399-407; process_maturity matches due_at_tick__lte=tick at credit.py:479-487) in BOTH epocha-whitepaper.md and epocha-whitepaper.it.md, and that EN and IT stay semantically identical. Then RE-VERIFY the whole section-4.8 promotion chapter as a Methods-grade chapter: the CES three branches, Walrasian tatonnement with the Scarf 1960 caveat, the Ricardo 1817 rent+wages+profit partition (0.6/0.15/0.25), the Fisher 1911 MV=PQ diagnostic, the parameter-table values vs the code constants, and the Simplifications disclosures (Carli bias, wage cap, mood step, ownerless->treasury, deposits outside M, wash-trade exclusion, primary-currency demand, essential-first settlement) must each match code and cite a real source; the banking-interest sink correction (R8-NEW-3) must be consistent between 4.2.2 and section 5; the section-4.2 code anchors must be single-frame. KNOWN NON-FINDINGS: the "round 6 / sei round" wording in the 4.8 Status header and Background line is a placeholder updated to the real round at the convergence declaration; the 4.8 Status pin commit SHA is set at merge. Do not file either as a finding.',
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
  return `You are a HOSTILE adversarial scientific reviewer running the ROUND 10 re-audit for the Epocha economy base layer. Round 9 found the issue below; it was then fixed in this branch. Your job: (1) verify the Round 9 finding is genuinely closed in the CURRENT code/working tree (RESOLVED for behavioral fixes, DOCUMENTED for honest disclosures), and (2) hunt for NEW defects the latest fix introduced. Keep proportion: this layer has been through nine audit rounds -- do not re-litigate previously adjudicated design decisions (approach-A factor partition wage 0.6/rent 0.15/profit 0.25, deposits outside M, Carli index disclosure, essential-first settlement, primary-currency demand sizing, treasury-outside-M boundary, inside-money credit flows, Fisher income-velocity diagnostic, default_settled terminal state, lien pair ["active","defaulted"], maturity __lte catch-up, banking-interest M-contracting sink); hunt only for genuine defects introduced by the LATEST commit (137c277) or missed by all prior rounds.

Repository: ${REPO}
Primary file: ${a.path} (read every other file you need: engine.py, credit.py, banking.py, monetary.py, property_market.py, context.py, distribution.py, market.py, production.py, models.py, tests/, docs/whitepaper/)

Round 9 finding for this area:
${a.r9}

Claimed fix:
${a.fix}

Adversarial angle:
${a.angle}

${a.doc ? 'This is a DOCUMENTATION area: verify the whitepaper text against the ACTUAL code (function behavior, constant values, cited sources). A scientific misstatement that would mislead the Methods chapter is a real finding; a stale file:line anchor is a low-severity finding; do NOT file the known round-count placeholder or the merge-time pin SHA as findings.' : ''}

Every new finding needs file:line and concrete evidence. Return the structured result.`
}

function conservePrompt() {
  return `You are an adversarial conservation-and-reproducibility auditor for the Epocha economy base layer (${REPO}/epocha/apps/economy/), Round 10 -- the convergence check after nine rounds of fixes plus commit 137c277 (collateral-selection id tiebreak). Your PRIMARY focus this round: DETERMINISM COMPLETENESS. Sweep EVERY iteration order and EVERY selection (.first()/.last()/[0]/.order_by(...).) feeding order-sensitive persisted OR prompt-affecting state across the whole tick and the whole package (engine zone loop, goods, currencies, agents, properties, trades, payees, tax set, credit loan querysets, maturity catch-up set, cascade BFS order, banking aggregations, broadcast RNG, expectations merge, property market buyers/listings, context debt block, all_agents/step-8 sums, initialization). For each, confirm it is pinned with a total-order tiebreak or is provably order-insensitive. Report ANY remaining unpinned order-sensitive selector with file:line.

Also re-confirm the standing invariants by reading the ACTUAL code:
1. MONEY: net cash injected by rent/wages/profit equals zone output value V (or less only via the documented wage-cap clip); taxation, property sales (ownerless-to-treasury, expropriation) are pure transfers; credit flows are two-legged or documented inside-money; defaults processed exactly once; the maturity __lte catch-up charges exactly one final period per loan-tick.
2. GOODS: trades, settlement scaling, collateral seizure, expropriation move goods/property conservatively, exactly once.
3. Fisher diagnostic: MV (income velocity * M) vs PQ (sum of per-zone V_z) independently measured and equal under conservation.

Report money_conserved, goods_conserved, tax_conserved, deterministic, remaining findings with file:line, and your reasoning.`
}

function verifyPrompt(f) {
  return `Adversarial verifier for the Round 10 economy audit. Refute this NEW finding (default survives=false when uncertain). Read the actual code at ${REPO}/${f.location} before deciding. This layer has been through nine audit rounds: previously adjudicated design decisions (approach-A partition, deposits outside M, Carli disclosure, essential-first settlement, primary-currency sizing, treasury outside M, inside-money credit flows, Fisher income-velocity diagnostic, default_settled terminal state, lien pair, maturity __lte catch-up, banking-interest sink) are settled -- a finding that re-litigates one does not survive. The section-4.8 round-count placeholder and the merge-time pin SHA are not findings. Materiality bar: a finding must either break an invariant (conservation, determinism, exactly-once), misstate model behavior in code comments/whitepaper in a way that would mislead the Methods chapter, or leave a formula/constant unsourced and untagged.

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

log(`Round 10: ${unresolved.length} Round-9 findings not closed; ${confirmedNew.length}/${newFindings.length} new findings survived; conservation money=${conserve.money_conserved} goods=${conserve.goods_conserved} tax=${conserve.tax_conserved} deterministic=${conserve.deterministic}.`)

phase('Synthesize')
const synthesis = await agent(
  `You are the lead auditor synthesizing the Round 10 re-audit verdict for the Epocha economy base layer.

Round 9 findings not closed (only non-RESOLVED/non-DOCUMENTED shown):
${JSON.stringify(unresolved, null, 2)}

New findings that SURVIVED adversarial verification:
${JSON.stringify(confirmedNew.map((f) => ({ area: f._area, id: f.id, category: f.category, severity: f.severity, claim: f.claim, location: f.location })), null, 2)}

Conservation/reproducibility verdict: money=${conserve.money_conserved}, goods=${conserve.goods_conserved}, tax=${conserve.tax_conserved}, deterministic=${conserve.deterministic}. Reasoning: ${conserve.reasoning}

Convergence criterion: all Round 9 findings RESOLVED or honestly DOCUMENTED; no surviving new INCORRECT/UNJUSTIFIED finding; money=YES or BOUNDED_INJECTION_ONLY; goods=YES; tax=YES; deterministic=YES. Surviving new INCONSISTENT/MISSING must be listed: documentation-grade ones (stale anchors, wording) are called out for a same-branch doc pass and do NOT block convergence provided none misstates model behavior in a way that would mislead the whitepaper Methods chapter (section 4.8), and no surviving finding breaks the determinism invariant. Give per-module verdicts (production, monetary, market, distribution, credit-banking, whitepaper, conservation), the overall verdict, and an honest summary of what, if anything, still blocks the section-4.8 promotion.`,
  { label: 'synthesize', phase: 'Synthesize', schema: SYNTHESIS_SCHEMA, effort: 'high' }
)

return { unresolved, confirmedNew, conserve, synthesis }
