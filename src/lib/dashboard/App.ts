import { Format } from "./format";
import { Store } from "./Store";
import { VerdictEngine } from "./VerdictEngine";
import {
	DEFAULT_DRAFT,
	DEFAULT_PROFILE,
	DEFAULT_ROLE,
	DEFAULT_SPEC,
	HISTORY_LIMIT,
	INCIDENT_KINDS,
	ROLES,
	SAMPLE_INCIDENT_SEEDS,
	VIEWS,
} from "./constants";
import type {
	AppState,
	Incident,
	IncidentKind,
	IncidentReport,
	PersistedState,
	Role,
	SystemSpec,
	ValidationResult,
	ViewId,
	WorkloadProfile,
} from "./types";
import { OverviewView } from "./views/OverviewView";
import { ReportView } from "./views/ReportView";
import { VerdictView } from "./views/VerdictView";
import type { View } from "./views/View";

const DAY_MS = 86_400_000;

/**
 * Orchestrates the dashboard: owns the application state, drives rendering,
 * and handles all user interactions. Constructed in the browser and started
 * via {@link App.init}.
 */
export class App {
	readonly engine = new VerdictEngine();

	private readonly doc: Document;
	private readonly store: Store;
	private readonly views: Record<ViewId, View>;
	#state: AppState;

	constructor(doc: Document = document) {
		this.doc = doc;
		this.store = new Store(App.resolveStorage(doc));
		this.views = {
			report: new ReportView(this),
			verdict: new VerdictView(this),
			overview: new OverviewView(this),
		};
		this.#state = this.restore(this.store.load());
	}

	/** The current application state. Views read it but mutate via App methods. */
	get state(): AppState {
		return this.#state;
	}

	private static resolveStorage(doc: Document): Storage | null {
		try {
			return doc.defaultView?.localStorage ?? null;
		} catch {
			return null;
		}
	}

	/** Wire up the static shell and render the initial view. */
	init(): void {
		const roleSelect = this.query<HTMLSelectElement>("#role");
		if (roleSelect) {
			roleSelect.value = this.#state.role;
			roleSelect.addEventListener("change", (event) => {
				const value = (event.target as HTMLSelectElement).value;
				this.#state.role = this.isRole(value) ? value : DEFAULT_ROLE;
				this.persist();
			});
		}

		this.doc.addEventListener("click", (event) => this.handleClick(event));
		this.render();
	}

	private restore(persisted: PersistedState | null): AppState {
		if (!persisted) {
			return {
				view: "report",
				role: DEFAULT_ROLE,
				spec: { ...DEFAULT_SPEC },
				profile: { ...DEFAULT_PROFILE },
				draft: { ...DEFAULT_DRAFT },
				history: [],
				current: null,
			};
		}
		return {
			view: "report",
			role: persisted.role ?? DEFAULT_ROLE,
			spec: { ...DEFAULT_SPEC, ...persisted.spec },
			profile: { ...DEFAULT_PROFILE, ...persisted.profile },
			draft: { ...DEFAULT_DRAFT, ...persisted.draft },
			history: persisted.history ?? [],
			current: persisted.current ?? null,
		};
	}

	private handleClick(event: MouseEvent): void {
		if (!(event.target instanceof Element)) return;
		const button = event.target.closest<HTMLElement>("[data-go],[data-open]");
		if (!button) return;

		const openId = button.dataset.open;
		if (openId !== undefined) {
			const match = this.#state.history.find((incident) => String(incident.id) === openId);
			if (match) this.#state.current = match;
			this.go("verdict");
			return;
		}

		const destination = button.dataset.go;
		if (destination === "report" || destination === "verdict" || destination === "overview") {
			this.go(destination);
		}
	}

	go(view: ViewId): void {
		this.#state.view = view;
		this.render();
	}

	render(): void {
		for (const { id } of VIEWS) {
			const button = this.query<HTMLButtonElement>(`nav button[data-go="${id}"]`);
			button?.setAttribute("aria-current", this.#state.view === id ? "page" : "false");
		}

		const main = this.query<HTMLElement>("#m");
		if (!main) return;

		const view = this.views[this.#state.view];
		main.innerHTML = view.render();
		view.mount();
		this.doc.defaultView?.scrollTo(0, 0);
	}

	/** Query the document for a single element. */
	query<T extends Element>(selector: string): T | null {
		return this.doc.querySelector<T>(selector);
	}

	/** Attach a click handler to the first element matching `selector`, if any. */
	bind(selector: string, handler: () => void): void {
		const element = this.query<HTMLElement>(selector);
		element?.addEventListener("click", handler);
	}

	private persist(): void {
		this.store.save({
			role: this.#state.role,
			spec: this.#state.spec,
			profile: this.#state.profile,
			draft: this.#state.draft,
			history: this.#state.history,
			current: this.#state.current,
		});
	}

	/** Read and validate the report form, then record a new incident. */
	runReport(): void {
		const result = this.collectAndValidate();
		if (!result.ok) {
			const error = this.query<HTMLElement>("#err");
			if (error) error.textContent = result.message;
			return;
		}

		const { report, spec, profile } = result;
		this.#state.spec = spec;
		this.#state.profile = profile;
		this.#state.draft = report;

		const now = Date.now();
		const verdict = this.engine.simulate({ ...report, spec, profile });
		const incident: Incident = {
			id: now,
			title: App.deriveTitle(report.description),
			report,
			reportedBy: this.#state.role,
			spec,
			profile,
			recordedAt: now,
			occurs: verdict.occurs,
			limitingResource: verdict.occurs ? verdict.limiting.kind : null,
		};

		this.#state.history.unshift(incident);
		this.#state.history = this.#state.history.slice(0, HISTORY_LIMIT);
		this.#state.current = incident;
		this.persist();
		this.go("verdict");
	}

	private collectAndValidate(): ValidationResult {
		const parseNumber = (id: string): number => {
			const element = this.query<HTMLInputElement>(`#${id}`);
			return element ? Number.parseFloat(element.value) : Number.NaN;
		};

		const description = this.query<HTMLTextAreaElement>("#description")?.value.trim() ?? "";
		const kindRaw = this.query<HTMLSelectElement>("#kind")?.value ?? "spike";
		const kind: IncidentKind = kindRaw in INCIDENT_KINDS ? (kindRaw as IncidentKind) : "spike";

		const report: IncidentReport = {
			description,
			kind,
			peakLoadReqS: parseNumber("load"),
			durationMin: parseNumber("duration"),
		};

		const spec: SystemSpec = {
			cpuVcpu: parseNumber("cpu"),
			ramGb: parseNumber("ram"),
			networkGbps: parseNumber("net"),
		};

		const profile: WorkloadProfile = {
			cpuMsPerRequest: parseNumber("cpuMs"),
			responseKb: parseNumber("kb"),
			ramGbPerKiloReqS: parseNumber("ramK"),
			idleRamGb: parseNumber("base"),
		};

		if (!description) {
			return { ok: false, message: "Describe the incident first." };
		}

		const mustBePositive = [
			report.peakLoadReqS,
			report.durationMin,
			spec.cpuVcpu,
			spec.ramGb,
			spec.networkGbps,
			profile.cpuMsPerRequest,
			profile.responseKb,
		];
		if (mustBePositive.some((value) => !(value > 0))) {
			return { ok: false, message: "Load, duration, spec and per-request costs must be above zero." };
		}

		if (!(profile.ramGbPerKiloReqS >= 0 && profile.idleRamGb >= 0)) {
			return { ok: false, message: "RAM figures cannot be negative." };
		}

		return { ok: true, report, spec, profile };
	}

	async copySummary(): Promise<void> {
		const { current } = this.#state;
		const status = this.query<HTMLElement>("#cm");
		if (!current || !status) return;

		const verdict = this.engine.simulateIncident(current);
		const summary =
			`${current.title}: ${verdict.occurs ? "will occur" : "will not occur"} on ${current.spec.cpuVcpu} vCPU / ${current.spec.ramGb} GB / ${current.spec.networkGbps} Gbps. ` +
			verdict.demands.map((demand) => `${demand.kind} ${Format.percent(demand.ratio)}%`).join(", ") +
			".";

		let copied = false;
		try {
			await navigator.clipboard.writeText(summary);
			copied = true;
		} catch {
			copied = false;
		}

		status.textContent = copied ? "Copied." : `Copy is blocked here: ${summary}`;
	}

	loadSamples(): void {
		const now = Date.now();
		this.#state.history = SAMPLE_INCIDENT_SEEDS.map((seed, index) => {
			const report: IncidentReport = {
				description: seed.title,
				kind: seed.kind,
				peakLoadReqS: seed.peakLoadReqS,
				durationMin: seed.durationMin,
			};
			const spec: SystemSpec = { ...this.#state.spec };
			const profile: WorkloadProfile = { ...this.#state.profile };
			const verdict = this.engine.simulate({ ...report, spec, profile });

			const incident: Incident = {
				id: now + index,
				title: seed.title,
				report,
				reportedBy: seed.reportedBy,
				spec,
				profile,
				recordedAt: now - seed.daysAgo * DAY_MS,
				occurs: verdict.occurs,
				limitingResource: verdict.occurs ? verdict.limiting.kind : null,
			};
			return incident;
		});

		this.#state.current = this.#state.history[0] ?? null;
		this.persist();
		this.render();
	}

	clearHistory(): void {
		const button = this.query<HTMLButtonElement>("#clr");
		if (!button) return;

		if (button.dataset.ok !== "1") {
			button.dataset.ok = "1";
			button.textContent = "Click again to clear all";
			return;
		}

		this.#state.history = [];
		this.#state.current = null;
		this.persist();
		this.render();
	}

	private isRole(value: string): value is Role {
		return ROLES.some((role) => role === value);
	}

	private static deriveTitle(description: string): string {
		return description.split(/[.\n]/)[0].slice(0, 70);
	}
}
