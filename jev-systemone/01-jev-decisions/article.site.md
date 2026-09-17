---
title: A model that answers in probabilities
date: 2026-09-17
summary: TypeSafe's Jev returns typed, calibrated judgments instead of generating text. We ran its separately audited v2 runtime on AdventureBench: incredibly accurate, fast, and revealing on terse commands.
author: Adrian Tame
author_url: https://github.com/AdrianTJ
publisher: Plicara Labs
slug: jev-decisions
---
<style>
.pl-fig { margin: 2.4rem 0; }
.pl-fig svg { width: 100%; height: auto; display: block; overflow: visible; }
.pl-fig .figlabel { font-family: var(--pl-font-mono, monospace); font-size: 0.68rem;
  letter-spacing: .12em; text-transform: uppercase; color: var(--pl-text-muted, #666);
  display: block; margin-bottom: .9rem; }
.pl-fig .grid { stroke: var(--pl-rule, #ccc); stroke-width: 1; }
.pl-fig .axis { stroke: var(--pl-text, #111); stroke-width: 1; }
.pl-fig .tick { fill: var(--pl-text-muted, #666); font: 0.72rem var(--pl-font-mono, monospace); }
.pl-fig .axistitle { fill: var(--pl-text, #111); font: 700 0.71rem var(--pl-font-mono, monospace); letter-spacing: .06em; }
.pl-fig .front { fill: none; stroke: var(--pl-series-1, #31606D); stroke-width: 3; stroke-dasharray: 7 5; }
.pl-fig .dot { stroke-width: 2; }
.pl-fig .dot-f { fill: var(--pl-series-1, #31606D); }
.pl-fig .dot-d { fill: var(--pl-series-1, #31606D); opacity: .3; }
.pl-fig .lbl { fill: var(--pl-text, #111); font: 600 0.75rem Georgia, serif; }
.pl-fig .leader { stroke: var(--pl-text-muted, #666); stroke-width: 1; }
.pl-fig .axistitle { fill: var(--pl-text, #111); font: 700 0.71rem var(--pl-font-mono, monospace); letter-spacing: .06em; }
.pl-fig .jlab { fill: var(--pl-orange, #EE8B33); font: 0.78rem var(--pl-font-mono, monospace); }
.pl-fig .ci { stroke: var(--pl-text-muted, #666); stroke-width: 1.5; }
</style>

Everything awkward about putting LLMs inside programs lives in the gap of their natural output: language. Traditional software is not designed to take natural language as input, and that is why LLMs as part of pipelines can break things. Examples include but are not limited to coaxing text into JSON, parsing it back, and generating valid URLs. TypeSafe's [Jev](https://typesafe.ai) is new and pretty exciting, and kind of breaks this calculus. It never generates text at all. You send it application state and typed questions, and it returns choices, scores and probabilities your code can branch on directly.

One of the use cases they included in their demo of the model was it playing Doom at a ridiculous speed, and I run a benchmark that could really benefit from something like that. So we ran Jev on [AdventureBench](https://plicara.ai/benchmarks/adventurebench/), our test of grounded instruction-following for text-based adventure games: map a player's free-form command onto a small action vocabulary against a described scene, or refuse honestly when nothing fits.

## results: incredibly accurate

There is one methodological point to get out of the way. Our benchmark's comparison contract requires all models in one release to share the same prompt. Jev cannot take our chat prompt since it has no chat interface. Scoring it through the chat harness would mean testing a text wrapper, not the model, and that would not be a fair comparison, since we could tune the wrapper a bunch. So we did the closest thing we could instead: we maintained the frozen dataset and deterministic scorer but built a separate audited runtime that speaks Jev's native interface (two parallel Choice questions per case, plus a confidence gate that flips uncertain answers to refusal). The numbers below sit *next to* the chat results, not merged with them. Full evidence and the replay code are in the [public repository](https://github.com/plicara/benchmarks/tree/main/adventurebench/releases/20260917-plicara-jev-v2).

<figure class="pl-fig"><span class="figlabel">score versus cost</span><svg class="pl-chart" viewBox="0 0 840 410" role="img" aria-label="Score versus cost"><title>Score versus cost</title><desc>Chat-model cost frontier with the Jev point marked separately</desc><clipPath id="fig-cost"><rect x="86" y="36" width="704" height="296" /></clipPath><line class="grid" x1="86" y1="332.00" x2="790" y2="332.00" />
<line class="grid" x1="86" y1="258.00" x2="790" y2="258.00" />
<line class="grid" x1="86" y1="184.00" x2="790" y2="184.00" />
<line class="grid" x1="86" y1="110.00" x2="790" y2="110.00" />
<line class="grid" x1="86" y1="36.00" x2="790" y2="36.00" />
<text class="tick" x="74" y="336.00" text-anchor="end">61.2%</text>
<text class="tick" x="74" y="262.00" text-anchor="end">70.0%</text>
<text class="tick" x="74" y="188.00" text-anchor="end">78.8%</text>
<text class="tick" x="74" y="114.00" text-anchor="end">87.6%</text>
<text class="tick" x="74" y="40.00" text-anchor="end">96.4%</text>
<text class="tick" x="132.97" y="355" text-anchor="middle">$0.01</text>
<text class="tick" x="316.59" y="355" text-anchor="middle">$0.02</text>
<text class="tick" x="559.32" y="355" text-anchor="middle">$0.05</text>
<text class="tick" x="742.93" y="355" text-anchor="middle">$0.10</text>
<line class="axis" x1="86" y1="332" x2="790" y2="332" /><line class="axis" x1="86" y1="36" x2="86" y2="332" /><text class="axistitle" x="438.00" y="406" text-anchor="middle">FULL-RUN COST (USD, LOG SCALE)</text><text class="axistitle" x="19" y="184.00" text-anchor="middle" transform="rotate(-90 19 184.00)">ADVENTURE BENCH SCORE</text><path class="front" d="M 86.00 229.74 L 222.27 137.84 L 340.15 136.69 L 518.64 119.46 L 790.00 84.99" /><line class="leader" x1="86.00" y1="229.74" x2="92.00" y2="217.74" /><line class="leader" x1="222.27" y1="137.84" x2="228.27" y2="125.84" /><line class="leader" x1="340.15" y1="136.69" x2="346.15" y2="124.69" /><line class="leader" x1="518.64" y1="119.46" x2="524.64" y2="107.46" /><line class="leader" x1="790.00" y1="84.99" x2="796.00" y2="72.99" /><g clip-path="url(#fig-cost)"><g><title>ibm-granite/granite-4.0-h-micro: 73.4% at $0.008 </title><circle class="dot dot-f" cx="86.00" cy="229.74" r="6.5" /></g><line class="ci" x1="86.00" y1="184.84" x2="86.00" y2="278.18" /><line class="ci" x1="81.00" y1="184.84" x2="91.00" y2="184.84" /><line class="ci" x1="81.00" y1="278.18" x2="91.00" y2="278.18" /><g><title>mistralai/ministral-3b-2512: 84.3% at $0.014 </title><circle class="dot dot-f" cx="222.27" cy="137.84" r="6.5" /></g><line class="ci" x1="222.27" y1="102.43" x2="222.27" y2="175.59" /><line class="ci" x1="217.27" y1="102.43" x2="227.27" y2="102.43" /><line class="ci" x1="217.27" y1="175.59" x2="227.27" y2="175.59" /><g><title>mistralai/ministral-8b-2512: 84.4% at $0.022 </title><circle class="dot dot-f" cx="340.15" cy="136.69" r="6.5" /></g><line class="ci" x1="340.15" y1="99.91" x2="340.15" y2="175.59" /><line class="ci" x1="335.15" y1="99.91" x2="345.15" y2="99.91" /><line class="ci" x1="335.15" y1="175.59" x2="345.15" y2="175.59" /><g><title>mistralai/ministral-14b-2512: 86.5% at $0.043 </title><circle class="dot dot-f" cx="518.64" cy="119.46" r="6.5" /></g><line class="ci" x1="518.64" y1="84.77" x2="518.64" y2="156.25" /><line class="ci" x1="513.64" y1="84.77" x2="523.64" y2="84.77" /><line class="ci" x1="513.64" y1="156.25" x2="523.64" y2="156.25" /><g><title>z-ai/glm-5.2: 90.6% at $0.119 </title><circle class="dot dot-f" cx="790.00" cy="84.99" r="6.5" /></g><line class="ci" x1="790.00" y1="57.02" x2="790.00" y2="115.05" /><line class="ci" x1="785.00" y1="57.02" x2="795.00" y2="57.02" /><line class="ci" x1="785.00" y1="115.05" x2="795.00" y2="115.05" /><g><title>qwen/qwen3.5-9b: 82.7% at $0.039 </title><circle class="dot dot-d" cx="495.06" cy="151.62" r="6.5" /></g><g><title>ibm-granite/granite-4.1-8b: 75.8% at $0.020 </title><circle class="dot dot-d" cx="310.25" cy="209.06" r="6.5" /></g><g><title>google/gemma-3-4b-it: 72.5% at $0.020 </title><circle class="dot dot-d" cx="309.96" cy="236.63" r="6.5" /></g><g><title>ibm-granite/granite-4.2-8b: 79.5% at $0.023 </title><circle class="dot dot-d" cx="358.82" cy="178.04" r="6.5" /></g><g><title>meta-llama/llama-3.2-3b-instruct: 68.9% at $0.023 </title><circle class="dot dot-d" cx="349.71" cy="267.65" r="6.5" /></g><g><title>nvidia/nemotron-3.5-lightning: 84.4% at $0.033 </title><circle class="dot dot-d" cx="449.99" cy="136.69" r="6.5" /></g><g><title>meta-llama/llama-3.1-8b-instruct: 73.6% at $0.020 </title><circle class="dot dot-d" cx="314.51" cy="227.44" r="6.5" /></g><line class="ci" x1="405.95" y1="44.41" x2="405.95" y2="99.07" /><line class="ci" x1="400.95" y1="44.41" x2="410.95" y2="44.41" /><line class="ci" x1="400.95" y1="99.07" x2="410.95" y2="99.07" /><g><title>Jev (jev-1.13.0): 92.3% at $0.028; separate interface, not comparable</title><rect x="398.95" y="63.06" width="14" height="14" fill="var(--pl-orange, #EE8B33)" /><line class="leader" x1="405.95" y1="70.06" x2="419.95" y2="74.06" /></g><text class="jlab" x="419.95" y="74.06" text-anchor="start">Jev (separate interface)</text></g><text class="lbl" x="96.00" y="212.74" text-anchor="start">Granite Micro</text><text class="lbl" x="232.27" y="120.84" text-anchor="start">Ministral 3B</text><text class="lbl" x="350.15" y="119.69" text-anchor="start">Ministral 8B</text><text class="lbl" x="528.64" y="102.46" text-anchor="start">Ministral 14B</text><text class="lbl" x="800.00" y="67.99" text-anchor="start">GLM 5.2</text></svg></figure>

## breaking the benchmark on speed as well

Jev's median per-case time is 303 ms. At 300 milliseconds, model judgment fits inside interactive loops: game turns, form validation, live moderation, anything where a human is waiting. At three seconds it introduces enough latency that the friction is felt quite significantly. This is client-measured round-trip time from one collection window, not a hardware benchmark, and the separate interface means it does not enter the chat-model frontier.

<figure class="pl-fig"><span class="figlabel">score versus latency</span><svg class="pl-chart" viewBox="0 0 840 410" role="img" aria-label="Score versus latency"><title>Score versus latency</title><desc>Chat-model latency frontier with the Jev point marked separately</desc><clipPath id="fig-lat"><rect x="86" y="36" width="704" height="296" /></clipPath><line class="grid" x1="86" y1="332.00" x2="790" y2="332.00" />
<line class="grid" x1="86" y1="258.00" x2="790" y2="258.00" />
<line class="grid" x1="86" y1="184.00" x2="790" y2="184.00" />
<line class="grid" x1="86" y1="110.00" x2="790" y2="110.00" />
<line class="grid" x1="86" y1="36.00" x2="790" y2="36.00" />
<text class="tick" x="74" y="336.00" text-anchor="end">61.2%</text>
<text class="tick" x="74" y="262.00" text-anchor="end">70.0%</text>
<text class="tick" x="74" y="188.00" text-anchor="end">78.8%</text>
<text class="tick" x="74" y="114.00" text-anchor="end">87.6%</text>
<text class="tick" x="74" y="40.00" text-anchor="end">96.4%</text>
<text class="tick" x="44.58" y="355" text-anchor="middle">0 ms</text>
<text class="tick" x="204.10" y="355" text-anchor="middle">500 ms</text>
<text class="tick" x="363.63" y="355" text-anchor="middle">1.0 s</text>
<text class="tick" x="523.15" y="355" text-anchor="middle">1.5 s</text>
<text class="tick" x="682.68" y="355" text-anchor="middle">2.0 s</text>
<line class="axis" x1="86" y1="332" x2="790" y2="332" /><line class="axis" x1="86" y1="36" x2="86" y2="332" /><text class="axistitle" x="438.00" y="406" text-anchor="middle">MEDIAN PER-CASE LATENCY</text><text class="axistitle" x="19" y="184.00" text-anchor="middle" transform="rotate(-90 19 184.00)">ADVENTURE BENCH SCORE</text><path class="front" d="M 134.55 227.44 L 178.55 178.04 L 181.32 136.69 L 295.83 119.46 L 343.05 84.99" /><line class="leader" x1="134.55" y1="227.44" x2="128.55" y2="241.44" /><line class="leader" x1="178.55" y1="178.04" x2="184.55" y2="166.04" /><line class="leader" x1="181.32" y1="136.69" x2="187.32" y2="124.69" /><line class="leader" x1="295.83" y1="119.46" x2="289.83" y2="133.46" /><line class="leader" x1="343.05" y1="84.99" x2="349.05" y2="72.99" /><g clip-path="url(#fig-lat)"><g><title>meta-llama/llama-3.1-8b-instruct: 73.6% at 282 ms </title><circle class="dot dot-f" cx="134.55" cy="227.44" r="6.5" /></g><line class="ci" x1="134.55" y1="182.32" x2="134.55" y2="274.82" /><line class="ci" x1="129.55" y1="182.32" x2="139.55" y2="182.32" /><line class="ci" x1="129.55" y1="274.82" x2="139.55" y2="274.82" /><g><title>ibm-granite/granite-4.2-8b: 79.5% at 420 ms </title><circle class="dot dot-f" cx="178.55" cy="178.04" r="6.5" /></g><line class="ci" x1="178.55" y1="136.91" x2="178.55" y2="222.68" /><line class="ci" x1="173.55" y1="136.91" x2="183.55" y2="136.91" /><line class="ci" x1="173.55" y1="222.68" x2="183.55" y2="222.68" /><g><title>nvidia/nemotron-3.5-lightning: 84.4% at 429 ms </title><circle class="dot dot-f" cx="181.32" cy="136.69" r="6.5" /></g><line class="ci" x1="181.32" y1="99.91" x2="181.32" y2="177.27" /><line class="ci" x1="176.32" y1="99.91" x2="186.32" y2="99.91" /><line class="ci" x1="176.32" y1="177.27" x2="186.32" y2="177.27" /><g><title>mistralai/ministral-14b-2512: 86.5% at 788 ms </title><circle class="dot dot-f" cx="295.83" cy="119.46" r="6.5" /></g><line class="ci" x1="295.83" y1="84.77" x2="295.83" y2="156.25" /><line class="ci" x1="290.83" y1="84.77" x2="300.83" y2="84.77" /><line class="ci" x1="290.83" y1="156.25" x2="300.83" y2="156.25" /><g><title>z-ai/glm-5.2: 90.6% at 936 ms </title><circle class="dot dot-f" cx="343.05" cy="84.99" r="6.5" /></g><line class="ci" x1="343.05" y1="57.02" x2="343.05" y2="115.05" /><line class="ci" x1="338.05" y1="57.02" x2="348.05" y2="57.02" /><line class="ci" x1="338.05" y1="115.05" x2="348.05" y2="115.05" /><g><title>qwen/qwen3.5-9b: 82.7% at 2184 ms </title><circle class="dot dot-d" cx="741.45" cy="151.62" r="6.5" /></g><g><title>mistralai/ministral-3b-2512: 84.3% at 645 ms </title><circle class="dot dot-d" cx="250.27" cy="137.84" r="6.5" /></g><g><title>ibm-granite/granite-4.0-h-micro: 73.4% at 1322 ms </title><circle class="dot dot-d" cx="466.27" cy="229.74" r="6.5" /></g><g><title>ibm-granite/granite-4.1-8b: 75.8% at 523 ms </title><circle class="dot dot-d" cx="211.35" cy="209.06" r="6.5" /></g><g><title>mistralai/ministral-8b-2512: 84.4% at 700 ms </title><circle class="dot dot-d" cx="267.82" cy="136.69" r="6.5" /></g><g><title>google/gemma-3-4b-it: 72.5% at 828 ms </title><circle class="dot dot-d" cx="308.63" cy="236.63" r="6.5" /></g><g><title>meta-llama/llama-3.2-3b-instruct: 68.9% at 624 ms </title><circle class="dot dot-d" cx="243.67" cy="267.65" r="6.5" /></g><line class="ci" x1="141.32" y1="44.41" x2="141.32" y2="99.07" /><line class="ci" x1="136.32" y1="44.41" x2="146.32" y2="44.41" /><line class="ci" x1="136.32" y1="99.07" x2="146.32" y2="99.07" /><g><title>Jev (jev-1.13.0): 92.3% at 303 ms; separate interface, not comparable</title><rect x="134.32" y="63.06" width="14" height="14" fill="var(--pl-orange, #EE8B33)" /><line class="leader" x1="141.32" y1="70.06" x2="155.32" y2="74.06" /></g><text class="jlab" x="155.32" y="74.06" text-anchor="start">Jev (separate interface)</text></g><text class="lbl" x="124.55" y="251.44" text-anchor="end">Llama 3.1 8B</text><text class="lbl" x="188.55" y="161.04" text-anchor="start">Granite 4.2</text><text class="lbl" x="191.32" y="119.69" text-anchor="start">Nemotron</text><text class="lbl" x="285.83" y="143.46" text-anchor="end">Ministral 14B</text><text class="lbl" x="353.05" y="67.99" text-anchor="start">GLM 5.2</text></svg></figure>

## a second pass after tuning on synthetic data

Jev scores 0.923 (95% interval 0.889 to 0.954) across 732 scored cases at a recorded cost of $0.028. A second, pinned `jev-1.13.0` run scores 0.925 (677/732). At this benchmark's scale, where a full run costs pennies, small chat models are brutally efficient and Jev's per-token price advantage mostly washes out against its longer structured requests.

Every Jev answer carries a confidence estimate, and our runtime refuses to act below a threshold. This second pass is a new prompt specification, selected on synthetic data and frozen before the evaluation release: missing targets become unclear, mapping tags use a 0.75 gate, calibration tags use a 0.9 gate, and relative directions without orientation are refused. The historic v1 evidence still replays under its pinned v1 mapping; this is not a rewrite of the published result.

Importantly for the purposes of this benchmark, the release was not used to tune those rules. The failure mode is still instructive: 47 of 56 misses in the alias run are overcautious refusals rather than confident mistakes. A model whose characteristic failure is saying "I don't know" is better than one that is overconfident in its answers.

## where it genuinely wins, and where it loses

The per-pattern table is the most Jev-shaped result in this piece:

| Pattern | Passed | Total |
| --- | --- | --- |
| Out-of-vocabulary verbs | 126 | 126 |
| Absent objects | 30 | 30 |
| Exact verbs | 36 | 36 |
| Typos | 35 | 36 |
| Abbreviations | 9 | 30 |
| Missing prepositions | 21 | 27 |

Refusal calibration is essentially perfect: unknown verbs, missing objects and nonsense all get refused at 100 percent, with zero type errors by construction. The weakness is terse commands. Single letters and dropped prepositions carry so little evidence that confidence sags below the gate, and good mappings get refused along with the bad ones. That is the price of the confidence tuned dial, and it suggests the next improvement is not a better model but state design: give the judgment more context and the same confidence goes further. When Jev does refuse, it is usually right (precision 0.862), and it catches nearly all genuine refusals (recall 0.980).

## how this could be wrong

1. This is one model snapshot (pinned jev-1.13.0, also tested under its floating alias with 721 of 732 per-case agreement); vendors like TypeSafe can change backends and prices move.
2. Latency is client-measured round-trip time from one collection window, not a hardware benchmark.
3. The comparison set is twelve chat models on one 244-case benchmark. It says nothing about reasoning tasks, open-ended generation, or anything where strings are the actual product (this is the point though).

## reproduce it!

The release pins every number above to raw evidence: [the Jev v2 release record](https://github.com/plicara/benchmarks/tree/main/adventurebench/releases/20260917-plicara-jev-v2). Recheck it offline with `adventure-bench-rescore --run-id 20260917-jev-v2-full --check`. The runtime, frozen prompt specifications, and replay code live in the [public benchmark repo](https://github.com/plicara/benchmarks/tree/main/adventurebench), and TypeSafe documents the model at [typesafe.ai](https://typesafe.ai) with live docs at [docs.typesafe.ai](https://docs.typesafe.ai).

## provenance

| Article output | Source | Verified |
| --- | --- | --- |
| V2 score, interval, cost, and alias latency | `results/jev_decisions/figures.json`, generated from the audited v2 alias release and raw evidence | Yes |
| Pinned confirmation score and agreement | `results/jev_decisions/figures.json`, generated from the audited v2 pinned release and raw evidence | Yes |
| Per-tag counts and refusal metrics | `results/jev_decisions/figures.json`, generated from replay-derived v2 results | Yes |
| Cost and latency charts | Inline SVG generated by `scripts/jev_decisions/build_article.py` from `results/jev_decisions/figures.json` | Yes |
