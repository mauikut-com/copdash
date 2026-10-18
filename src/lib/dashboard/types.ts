// Domain model for the ServerAgent dashboard.

/** The category of incident being reported. */
export type IncidentKind = "spike" | "leak" | "batch";

/** The persona reporting an incident; only used to label a report. */
export type Role = "QA engineer" | "Infra engineer" | "Eng manager";

/** The three dashboard views. */
export type ViewId = "report" | "verdict" | "overview";

/** The hardware the application runs on. */
export interface SystemSpec {
	cpuVcpu: number;
	ramGb: number;
	networkGbps: number;
}

/**
 * The per-request cost model used to project demand from load.
 * Demand = load × per-request cost (plus incident-kind adjustments).
 */
export interface WorkloadProfile {
	/** CPU time per request, in milliseconds. */
	cpuMsPerRequest: number;
	/** Response size per request, in kilobytes. */
	responseKb: number;
	/** GB of RAM consumed per 1000 req/s of sustained load. */
	ramGbPerKiloReqS: number;
	/** Baseline (idle) RAM footprint, in GB. */
	idleRamGb: number;
}

export type ResourceKind = "CPU" | "RAM" | "Network";
export type ResourceUnit = "vCPU" | "GB" | "Gbps";

/** A single resource's projected demand against its capacity. */
export interface ResourceDemand {
	kind: ResourceKind;
	demand: number;
	capacity: number;
	unit: ResourceUnit;
	/** demand / capacity; a value above 1 means over capacity. */
	ratio: number;
}

/** The full output of the verdict engine for a single incident. */
export interface Verdict {
	demands: ResourceDemand[];
	/** The resource with the highest ratio (the tightest constraint). */
	limiting: ResourceDemand;
	/** Resources whose demand exceeds capacity. */
	overCapacity: ResourceDemand[];
	/** True when at least one resource is over capacity. */
	occurs: boolean;
	/** Human-readable derivation of the verdict, in order. */
	steps: string[];
}

/** The facts of an incident as entered by the user. */
export interface IncidentReport {
	description: string;
	kind: IncidentKind;
	/** Peak load observed, in requests per second. */
	peakLoadReqS: number;
	/** How long the incident lasted, in minutes. */
	durationMin: number;
}

/** Everything the verdict engine needs to evaluate an incident. */
export interface IncidentInput extends IncidentReport {
	spec: SystemSpec;
	profile: WorkloadProfile;
}

/**
 * A recorded incident. The `spec` and `profile` are snapshots taken at
 * report time so a historical verdict is reproducible.
 */
export interface Incident {
	id: number;
	title: string;
	report: IncidentReport;
	reportedBy: Role;
	spec: SystemSpec;
	profile: WorkloadProfile;
	/** Epoch milliseconds when the incident was recorded. */
	recordedAt: number;
	/** Cached verdict summary; the full `Verdict` is recomputed on demand. */
	occurs: boolean;
	limitingResource: ResourceKind | null;
}

/** State that survives a page reload. */
export interface PersistedState {
	role: Role;
	spec: SystemSpec;
	profile: WorkloadProfile;
	draft: IncidentReport;
	history: Incident[];
	current: Incident | null;
}

/** The full in-memory application state (persisted fields plus the active view). */
export interface AppState extends PersistedState {
	view: ViewId;
}

/** Result of validating the report form. */
export type ValidationResult =
	| {
			ok: true;
			report: IncidentReport;
			spec: SystemSpec;
			profile: WorkloadProfile;
	  }
	| { ok: false; message: string };
