import { Format } from "../format";
import { View } from "./View";
import type { ResourceDemand } from "../types";

/** The "Verdict" view: shows the outcome for the current incident. */
export class VerdictView extends View {
	render(): string {
		const { current } = this.app.state;
		if (!current) {
			return `<section class="card"><h1>No verdict yet</h1><p class="mu">Report an incident to get one.</p><div class="btns"><button class="pri" data-go="report">Report an incident</button></div></section>`;
		}

		const verdict = this.app.engine.simulateIncident(current);
		const icon = verdict.occurs
			? '<path d="M12 3 2 21h20L12 3z"/><path d="M12 10v5M12 18v.01"/>'
			: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>';

		const detail = verdict.occurs
			? `${verdict.limiting.kind} is the limiting resource.`
			: `Nothing exceeds capacity; ${verdict.limiting.kind} is tightest.`;

		const banner = `<div class="ban ${verdict.occurs ? "w" : "o"}"><svg aria-hidden="true" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${icon}</svg>
<div><div class="bt">This incident will${verdict.occurs ? "" : " not"} occur on the current spec</div><div>${Format.escape(current.title)}. ${detail}</div></div></div>`;

		const bars = verdict.demands.map((demand) => this.bar(demand)).join("");
		const steps = verdict.steps.map((step) => `<li>${Format.escape(step)}</li>`).join("");

		return `${banner}
<div class="row"><section class="card a"><h2>Simulated peak vs. spec</h2>${bars}
<div class="btns"><button class="sec" data-go="report">Edit spec and re-run</button><button class="pri" id="cp">Copy summary</button><span id="cm" class="mu sm" role="status"></span></div></section>
<aside class="card b"><h2>How the verdict was reached</h2><ol>${steps}</ol></aside></div>`;
	}

	mount(): void {
		this.app.bind("#cp", () => void this.app.copySummary());
	}

	private bar(resource: ResourceDemand): string {
		const percent = Format.percent(resource.ratio);
		const status =
			resource.ratio > 1 ? "over capacity" : resource.ratio >= 0.85 ? "near limit" : "within capacity";
		return `<div class="bar"><div class="bh"><b>${resource.kind}</b><span class="mono">${Format.fixed(resource.demand, 2)} of ${Format.fixed(resource.capacity, 2)} ${resource.unit} · ${percent}% · ${status}</span></div><div class="tr"><i class="${resource.ratio > 1 ? "ov" : ""}" style="width:${Math.min(percent, 100)}%"></i></div></div>`;
	}
}
