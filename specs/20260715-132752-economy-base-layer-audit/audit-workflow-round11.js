export const meta = {
  name: 'economy-base-layer-audit-round11',
  description: 'Round 11 re-audit: verify the two Round 10 determinism pins closed (R10-DET-1 context property enumeration, R10-DET-2 expropriation loop order), run an EXHAUSTIVE determinism-completeness sweep to confirm zero remaining unpinned order-sensitive selectors, final Methods-grade verification of the section-4.8 promotion, deliver the convergence verdict.',
  phases: [
    { title: 'Reaudit', detail: 'verify the two Round 10 pins + final whitepaper check' },
    { title: 'Conserve', detail: 'exhaustive conservation + determinism-completeness sweep' },
    { title: 'Verify', detail: 'adversarially confirm any new finding' },
    { title: 'Synthesize', detail: 'convergence verdict' },
  ],
}

const REPO = '/Users/mauriziomocci/Documents/workspace/Opensource/epocha'

const AREAS = [
  {
    key: 'determinism-pins',
    path: 'epocha/apps/economy/context.py',
    r10: 'R10-DET-1 (INCONSISTENT/medium): build_economic_context read the agent owned-property list with values_list and no order_by and joined it into the LLM prompt while the sibling holdings/market-price enumerations are sorted. R10-DET-2 (INCONSISTENT/low): process_expropriation iterated the target-properties and affected-agents querysets unordered, allocating seizure side effects and Memory rows in unspecified order.',
    fix: 'Commit 43f6bca: context.py adds .order_by("id") before .values_list("property_type") (regression test test_property_enumeration_is_id_ordered); property_market.py id-orders both target_properties and affected_agents in process_expropriation.',
    angle: 'Verify BOTH pins in the current code. Then confirm the fixes introduced no regression to the enumeration content or the expropriation transfer result. No new hunt needed here beyond confirming the two pins; the exhaustive sweep is the conservation auditor job.',
  },
  {
    key: 'whitepaper',
    path: 'docs/whitepaper/epocha-whitepaper.md',
    r10: 'The whitepaper was CONVERGED at Round 10 (no surviving finding misstates model behavior). It carries: the section-4.8 Methods promotion (EN ~line 1882, IT ~1949), section 8.2 removed and the residual section-8 count reconciled to Knowledge Graph only, the section-4.2 code anchors refreshed to a single working-tree frame, the R8-NEW-3 banking-interest M-contracting-sink correction, and the R9 section-4.2.2 maturity due_at_tick<=tick doc-sync.',
    fix: 'This is the final Methods-grade pass before the promotion commit. Re-verify against the ACTUAL code: the section-4.8 CES three branches, Walrasian tatonnement + Scarf 1960 caveat, Ricardo 1817 rent+wages+profit partition (0.6/0.15/0.25), Fisher 1911 MV=PQ diagnostic, the parameter-table values vs code constants, the Simplifications disclosures; the section-4.2.2 service_loans/process_maturity due_at_tick<=tick wording vs credit.py; the banking-interest sink consistency between 4.2.2 and section 5; EN/IT symmetry.',
    angle: 'Report any scientific misstatement (INCORRECT), any parameter/source mismatch (UNJUSTIFIED/INCONSISTENT), any stale anchor (low), any EN/IT divergence. KNOWN NON-FINDINGS: the "round 6 / sei round" placeholder wording in the 4.8 Status header and Background line (updated to the real round at the convergence declaration) and the 4.8 Status pin commit SHA (set at merge) -- do NOT file either.',
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
  return `You are a HOSTILE adversarial scientific reviewer running the ROUND 11 re-audit for the Epocha economy base layer. Round 10 found the issue(s) below; they were then fixed in this branch (commit 43f6bca). Verify each is genuinely closed in the CURRENT code/working tree, and hunt only for genuine NEW defects introduced by the latest commit. Keep proportion: this layer has been through ten audit rounds -- do not re-litigate previously adjudicated design decisions (approach-A factor partition, deposits outside M, Carli disclosure, essential-first settlement, primary-currency demand sizing, treasury-outside-M boundary, inside-money credit flows, Fisher income-velocity diagnostic, default_settled terminal state, lien pair, maturity __lte catch-up, banking-interest M-contracting sink, id tiebreaks).

Repository: ${REPO}
Primary file: ${a.path} (read every other file you need)

Round 10 finding(s):
${a.r10}

Claimed fix:
${a.fix}

Adversarial angle:
${a.angle}

${a.doc ? 'This is a DOCUMENTATION area: verify the whitepaper text against the ACTUAL code. Do NOT file the known round-count placeholder or the merge-time pin SHA as findings.' : ''}

Every new finding needs file:line and concrete evidence. Return the structured result.`
}

function conservePrompt() {
  return `You are an adversarial conservation-and-reproducibility auditor for the Epocha economy base layer (${REPO}/epocha/apps/economy/), Round 11 -- the CONVERGENCE check after ten rounds. Commit 43f6bca pinned the last two order-sensitive selectors the Round 10 sweep found (context property enumeration, expropriation loops).

Your PRIMARY job: an EXHAUSTIVE determinism-completeness sweep. Enumerate EVERY iteration order and EVERY selection (.first()/.last()/[0], .order_by(...), values_list joined into a prompt, dict/set iteration feeding a float sum or a prompt, Memory/row create loops) across the ENTIRE economy package AND its consumers in simulation/engine.py (context.py, engine.py, credit.py, banking.py, monetary.py, market.py, distribution.py, production.py, property_market.py, expectations.py, initialization.py, political_feedback.py). For EACH one, state whether it is pinned with a total-order tiebreak or provably order-insensitive. Your goal is to either (a) confirm ZERO remaining unpinned order-sensitive selectors, or (b) report each remaining one with file:line and concrete evidence of how it feeds order-sensitive persisted or prompt state.

Also re-confirm the standing invariants by reading the ACTUAL code: MONEY (bounded-injection factor income; taxation/property-sale/expropriation pure transfers; credit two-legged or documented inside-money; defaults once; maturity __lte one final period); GOODS (trades/settlement/seizure/expropriation conservative, exactly once); Fisher MV vs PQ independently measured and equal.

Report money_conserved, goods_conserved, tax_conserved, deterministic (YES only if you found ZERO remaining unpinned order-sensitive selectors), remaining findings with file:line, and your reasoning listing the selectors you checked.`
}

function verifyPrompt(f) {
  return `Adversarial verifier for the Round 11 economy audit. Refute this NEW finding (default survives=false when uncertain). Read the actual code at ${REPO}/${f.location} before deciding. This layer has been through ten audit rounds: previously adjudicated design decisions are settled -- a finding that re-litigates one does not survive. The section-4.8 round-count placeholder and the merge-time pin SHA are not findings. A determinism finding survives ONLY if the unpinned order actually feeds order-sensitive PERSISTED or PROMPT state (a create-order nit that no consumer reads order-dependently is not material). Materiality bar: break an invariant (conservation, determinism, exactly-once), misstate model behavior in a way that would mislead the Methods chapter, or leave a formula/constant unsourced.

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

log(`Round 11: ${unresolved.length} Round-10 findings not closed; ${confirmedNew.length}/${newFindings.length} new findings survived; conservation money=${conserve.money_conserved} goods=${conserve.goods_conserved} tax=${conserve.tax_conserved} deterministic=${conserve.deterministic}.`)

phase('Synthesize')
const synthesis = await agent(
  `You are the lead auditor synthesizing the Round 11 re-audit verdict for the Epocha economy base layer.

Round 10 findings not closed (only non-RESOLVED/non-DOCUMENTED shown):
${JSON.stringify(unresolved, null, 2)}

New findings that SURVIVED adversarial verification:
${JSON.stringify(confirmedNew.map((f) => ({ area: f._area, id: f.id, category: f.category, severity: f.severity, claim: f.claim, location: f.location })), null, 2)}

Conservation/reproducibility verdict: money=${conserve.money_conserved}, goods=${conserve.goods_conserved}, tax=${conserve.tax_conserved}, deterministic=${conserve.deterministic}. Reasoning: ${conserve.reasoning}

Convergence criterion: all Round 10 findings RESOLVED or honestly DOCUMENTED; no surviving new INCORRECT/UNJUSTIFIED finding; money=YES or BOUNDED_INJECTION_ONLY; goods=YES; tax=YES; deterministic=YES (zero remaining unpinned order-sensitive selectors). Surviving new INCONSISTENT/MISSING must be listed and, if documentation-grade and not misleading model behavior, called out for a same-branch doc pass without blocking. Give per-module verdicts (production, monetary, market, distribution, credit-banking, whitepaper, conservation), the overall verdict, and an honest summary of whether the section-4.8 promotion can now proceed.`,
  { label: 'synthesize', phase: 'Synthesize', schema: SYNTHESIS_SCHEMA, effort: 'high' }
)

return { unresolved, confirmedNew, conserve, synthesis }
