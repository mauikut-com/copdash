import { Format } from "../format";
import { INCIDENT_KINDS } from "../constants";
import { View } from "./View";

/** The "Report an incident" view: incident details plus the current spec/profile. */
export class ReportView extends View {
	render(): string {
		const { draft, spec, profile } = this.app.state;

		const kindOptions = Object.entries(INCIDENT_KINDS)
			.map(
				([value, label]) =>
					`<option value="${value}"${value === draft.kind ? " selected" : ""}>${label}</option>`,
			)
			.join("");

		return `<div class="row">
<section class="card a">
<h1>Report an incident</h1>
<p class="mu">Describe what happened. ServerAgent checks whether it would happen again on the current system spec.</p>
<div><label for="description">What happened</label><textarea id="description">${Format.escape(draft.description)}</textarea></div>
<div class="g3"><div><label for="kind">Incident type</label><select id="kind">${kindOptions}</select></div>${this.numberField("load", "Peak load (req/s)", draft.peakLoadReqS)}${this.numberField("duration", "Duration (min)", draft.durationMin)}</div>
<p id="err" class="err" role="alert"></p>
<div class="btns"><button class="pri" id="run">Run verdict</button></div>
</section>
<aside class="card b">
<h2>Current spec</h2>
<div class="g2">${this.numberField("cpu", "CPU (vCPU)", spec.cpuVcpu)}${this.numberField("ram", "RAM (GB)", spec.ramGb)}${this.numberField("net", "Network (Gbps)", spec.networkGbps)}</div>
<h2>Workload profile</h2>
<div class="g2">${this.numberField("cpuMs", "CPU ms per request", profile.cpuMsPerRequest)}${this.numberField("kb", "Response KB", profile.responseKb)}${this.numberField("ramK", "GB RAM per 1k req/s", profile.ramGbPerKiloReqS)}${this.numberField("base", "Idle RAM (GB)", profile.idleRamGb)}</div>
<p class="mu sm">Model: demand = load × per-request cost. Batch overlap adds 1.5 vCPU and 2 GB. A memory leak adds 0.15 GB per minute.</p>
</aside>
</div>`;
	}

	mount(): void {
		this.app.bind("#run", () => this.app.runReport());
	}
}
