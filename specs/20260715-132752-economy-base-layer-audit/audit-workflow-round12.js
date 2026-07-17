export const meta = {
  name: 'economy-base-layer-audit-round12',
  description: 'Round 12 re-audit: verify the R11-DET-1 sell_property expectation pin closed and that it was the last unpinned selector; verify the completed whole-document whitepaper economy-anchor refresh (single frame at a50358c) + the §5->§4.8 cross-reference fix + R11-NEW-1..4 resolutions; final conservation/determinism sweep; deliver the convergence verdict.',
  phases: [
    { title: 'Reaudit', detail: 'verify R11-DET-1 + the whitepaper doc pass' },
    { title: 'Conserve', detail: 'final conservation + determinism-completeness sweep' },
    { title: 'Verify', detail: 'adversarially confirm any new finding' },
    { title: 'Synthesize', detail: 'convergence verdict' },
  ],
}

const REPO = '/Users/mauriziomocci/Documents/workspace/Opensource/epocha'

const AREAS = [
  {
    key: 'determinism-final',
    path: 'epocha/apps/simulation/engine.py',
    r11: 'R11-DET-1 (INCONSISTENT/medium): the sell_property action handler read the asking-price trend multiplier from AgentExpectation.objects.filter(agent=agent).first() with no order_by; an agent holds one expectation per good, so the unordered .first() picked a DB-heap-order row, and its trend set the persisted PropertyListing.asking_price that drives the order-sensitive property settlement -- non-reproducible across identically-seeded runs. This was the LAST unpinned order-sensitive selector the exhaustive Round 11 sweep found.',
    fix: 'Commit a50358c: the selection is now AgentExpectation.objects.filter(agent=agent).order_by("good_code").first() (simulation/engine.py ~line 280). RED-first test test_sell_property_asking_price_deterministic_on_expectation creates a rising "wheat" expectation before a falling "barley" one so the pre-fix insertion-order pick (1.1) and the post-fix good_code-order pick (0.9) diverge, asserting asking == fundamental * 0.9.',
    angle: 'Verify the pin. Then confirm this was truly the last one: independently re-check that NO other .first()/.last()/[0]/order_by-on-non-unique-key selector across the economy package and simulation/engine.py feeds order-sensitive persisted or prompt state without a total-order tiebreak. If you find any, report it; otherwise state explicitly that the determinism sweep is clean.',
  },
  {
    key: 'whitepaper',
    path: 'docs/whitepaper/epocha-whitepaper.md',
    r11: 'Round 11 raised four documentation findings, all INCONSISTENT/low: R11-NEW-1 (§4.2.2 process_default_cascade anchor stale at credit.py:921-1076), R11-NEW-2 (Table 6.1 + Appendix A.9 property-market anchors stale at property_market.py:222 / :114-121), R11-NEW-3 (Appendix A.8 anchors stale: rollover credit.py:504, CASCADE credit.py:50, _CONCERN banking.py:319), R11-NEW-4 (§4.2.2 banking-interest disclosure cross-referenced "§5", which does not document it; the disclosure lives in §4.8).',
    fix: 'A whole-document economy-anchor refresh was applied to BOTH whitepaper files against the frozen code frame (last code commit a50358c): every economy-module file:line anchor (§4.2, Table 6.1, Appendix A.8/A.9, and the drifted context.py/credit.py/simulation-engine.py/economy-models.py anchors) now matches the current working-tree line ranges, EN and IT anchor-identical; and the §4.2.2 cross-reference now reads "see §4.8" (EN) / "cfr. §4.8" (IT). NOTE: the section-4.1/4.6/5.4 (demography/movement/persistence) anchors are pinned to their OWN frozen Status commits, NOT to HEAD, so they are intentionally NOT refreshed by this economy branch.',
    angle: 'Spot-verify a sample of the refreshed economy anchors against the ACTUAL code at HEAD (process_default_cascade credit.py:930-1085; property_market listing expiration :235 and Gordon guard band :121-128; the three _CONCERN constants banking.py:325/329/334; CASCADE_LOSS_THRESHOLD credit.py:54; rollover credit.py:636; run_economy simulation/engine.py:380-398 dispatch :394; AgentExpectation economy/models.py:527-585). Confirm the §5->§4.8 fix and that §5 indeed does not document the M-contraction while §4.8 does. Re-confirm the §4.8 Methods chapter is unchanged and correct. Report ONLY genuine remaining scientific misstatements or economy-anchor mismatches. KNOWN NON-FINDINGS: the "round 6 / sei round" placeholder wording (updated to the real round at the convergence declaration), the merge-time §4.8 pin SHA, and the non-economy (§4.1/§4.6/§5.4) anchors pinned to other commits -- do NOT file any of these.',
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
  return `You are a HOSTILE adversarial scientific reviewer running the ROUND 12 re-audit for the Epocha economy base layer -- the CONVERGENCE round after eleven rounds. Round 11 found the issue(s) below; they were then fixed. Verify each is genuinely closed in the CURRENT code/working tree, and hunt only for genuine NEW defects introduced by the latest changes. Keep proportion: do not re-litigate settled design decisions (approach-A partition, deposits outside M, Carli disclosure, essential-first settlement, primary-currency sizing, treasury outside M, inside-money credit flows, Fisher income-velocity diagnostic, default_settled terminal state, lien pair, maturity __lte catch-up, banking-interest M-contracting sink, id tiebreaks).

Repository: ${REPO}
Primary file: ${a.path} (read every other file you need)

Round 11 finding(s):
${a.r11}

Claimed fix:
${a.fix}

Adversarial angle:
${a.angle}

${a.doc ? 'This is a DOCUMENTATION area: verify the whitepaper text against the ACTUAL code at HEAD. Do NOT file the known round-count placeholder, the merge-time pin SHA, or the non-economy anchors pinned to other frozen commits.' : ''}

Every new finding needs file:line and concrete evidence. Return the structured result.`
}

function conservePrompt() {
  return `You are an adversarial conservation-and-reproducibility auditor for the Epocha economy base layer (${REPO}/epocha/apps/economy/), Round 12 -- the FINAL convergence check. Commit a50358c pinned the last order-sensitive selector the Round 11 sweep found (sell_property expectation selection). Confirm the layer now reproduces bit-identical state under identical seeds.

Read the ACTUAL current code end-to-end and:
1. Re-confirm the conservation invariants: MONEY bounded-injection-only (factor income = zone V minus documented wage-cap clip; taxation/property-sale/ownerless/expropriation pure transfers; credit two-legged or documented inside-money; defaults exactly once; maturity __lte one final period); GOODS conservative exactly once; TAX two-legged; Fisher MV vs PQ independently measured and equal.
2. Re-run the determinism-completeness sweep: is EVERY iteration order and selection that feeds order-sensitive persisted or prompt state now pinned with a total-order tiebreak or provably order-insensitive (including the sell_property expectation pick at simulation/engine.py, the context property enumeration, the collateral selection, the expropriation loops)? Set deterministic=YES only if you find ZERO remaining unpinned order-sensitive selector.

Report money_conserved, goods_conserved, tax_conserved, deterministic, remaining findings with file:line, and your reasoning.`
}

function verifyPrompt(f) {
  return `Adversarial verifier for the Round 12 economy audit. Refute this NEW finding (default survives=false when uncertain). Read the actual code at ${REPO}/${f.location} before deciding. Settled design decisions do not survive re-litigation. The section-4.8 round-count placeholder, the merge-time pin SHA, and non-economy anchors pinned to other frozen commits are NOT findings. A determinism finding survives ONLY if the unpinned order actually feeds order-sensitive PERSISTED or PROMPT state. Materiality bar: break an invariant (conservation, determinism, exactly-once), misstate model behavior in a way that would mislead the Methods chapter, or leave a formula/constant unsourced.

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

log(`Round 12: ${unresolved.length} Round-11 findings not closed; ${confirmedNew.length}/${newFindings.length} new findings survived; conservation money=${conserve.money_conserved} goods=${conserve.goods_conserved} tax=${conserve.tax_conserved} deterministic=${conserve.deterministic}.`)

phase('Synthesize')
const synthesis = await agent(
  `You are the lead auditor synthesizing the Round 12 re-audit verdict for the Epocha economy base layer -- the convergence declaration.

Round 11 findings not closed (only non-RESOLVED/non-DOCUMENTED shown):
${JSON.stringify(unresolved, null, 2)}

New findings that SURVIVED adversarial verification:
${JSON.stringify(confirmedNew.map((f) => ({ area: f._area, id: f.id, category: f.category, severity: f.severity, claim: f.claim, location: f.location })), null, 2)}

Conservation/reproducibility verdict: money=${conserve.money_conserved}, goods=${conserve.goods_conserved}, tax=${conserve.tax_conserved}, deterministic=${conserve.deterministic}. Reasoning: ${conserve.reasoning}

Convergence criterion: all Round 11 findings RESOLVED or honestly DOCUMENTED; no surviving new INCORRECT/UNJUSTIFIED finding; money=YES or BOUNDED_INJECTION_ONLY; goods=YES; tax=YES; deterministic=YES (zero remaining unpinned order-sensitive selectors). Any surviving new INCONSISTENT/MISSING must be listed and, if documentation-grade and not misleading model behavior, called out for a doc pass without blocking. Give per-module verdicts (production, monetary, market, distribution, credit-banking, whitepaper, conservation), the overall verdict, and an honest summary of whether the section-4.8 promotion can now proceed. No "close enough" -- either CONVERGED or NOT CONVERGED with the precise blocker.`,
  { label: 'synthesize', phase: 'Synthesize', schema: SYNTHESIS_SCHEMA, effort: 'high' }
)

return { unresolved, confirmedNew, conserve, synthesis }
