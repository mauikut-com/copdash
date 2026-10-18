import { Format } from "../format";
import { View } from "./View";

/** The "Overview" view: summary tiles plus the incident history table. */
export class OverviewView extends View {
	render(): string {
		const { history } = this.app.state;
		const willOccur = history.filter((incident) => incident.occurs).length;

		const tiles = [
			this.tile("Will occur", String(willOccur), "wt"),
			this.tile("Will not occur", String(history.length - willOccur), "ot"),
			this.tile("Incidents reviewed", String(history.length), ""),
		].join("");

		const heading = `<h1>Incident overview</h1><div class="tiles">${tiles}</div>`;

		if (history.length === 0) {
			return `${heading}<div class="card"><p class="mu">No incidents yet. Report one, or load four examples to see the overview.</p><div class="btns"><button class="sec" data-go="report">Report an incident</button><button class="pri" id="smp">Load examples</button></div></div>`;
		}

		const head = ["Incident", "Reported by", "Verdict", "Limiting resource", "Date"]
			.map((label) => `<th scope="col">${label}</th>`)
			.join("");

		const body = history
			.map(
				(incident) => `<tr>
<td><button class="lk" data-open="${incident.id}">${Format.escape(incident.title)}</button></td>
<td>${Format.escape(incident.reportedBy)}</td>
<td><span class="pill ${incident.occurs ? "w" : "o"}">${incident.occurs ? "Will occur" : "Will not occur"}</span></td>
<td>${incident.limitingResource ?? "None"}</td>
<td class="mono">${Format.date(incident.recordedAt)}</td>
</tr>`,
			)
			.join("");

		return `${heading}<div class="card tw"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>
<div class="btns"><button class="sec" id="clr">Clear history</button></div>`;
	}

	mount(): void {
		this.app.bind("#smp", () => this.app.loadSamples());
		this.app.bind("#clr", () => this.app.clearHistory());
	}

	private tile(label: string, value: string, className: string): string {
		return `<div class="card tile"><div class="mu sm">${label}</div><div class="mono big ${className}">${value}</div></div>`;
	}
}
