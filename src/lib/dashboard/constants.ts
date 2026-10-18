import type {
	IncidentKind,
	IncidentReport,
	Role,
	SystemSpec,
	ViewId,
	WorkloadProfile,
} from "./types";

/** Human-readable labels for each incident kind. */
export const INCIDENT_KINDS: Readonly<Record<IncidentKind, string>> = {
	spike: "Traffic spike",
	leak: "Memory leak",
	batch: "Batch job overlap",
};

/** The selectable roles, in display order. */
export const ROLES: readonly Role[] = ["QA engineer", "Infra engineer", "Eng manager"];

/** The dashboard views, in navigation order. */
export const VIEWS: ReadonlyArray<{ id: ViewId; label: string }> = [
	{ id: "report", label: "Report" },
	{ id: "verdict", label: "Verdict" },
	{ id: "overview", label: "Overview" },
];

export const DEFAULT_ROLE: Role = "QA engineer";

export const DEFAULT_SPEC: SystemSpec = {
	cpuVcpu: 4,
	ramGb: 8,
	networkGbps: 1,
};

export const DEFAULT_PROFILE: WorkloadProfile = {
	cpuMsPerRequest: 1.5,
	responseKb: 60,
	ramGbPerKiloReqS: 1.2,
	idleRamGb: 2,
};

export const DEFAULT_DRAFT: IncidentReport = {
	description:
		"Checkout API returned 503s for about 4 minutes after the promo email went out. App-tier CPU stayed pinned.",
	kind: "spike",
	peakLoadReqS: 2400,
	durationMin: 4,
};

/** Key under which `PersistedState` is stored in localStorage. */
export const STORAGE_KEY = "serveragent.v1";

/** Maximum number of incidents retained in history. */
export const HISTORY_LIMIT = 50;

/** A seed for the "load examples" action. */
export interface SampleIncidentSeed {
	title: string;
	reportedBy: Role;
	kind: IncidentKind;
	peakLoadReqS: number;
	durationMin: number;
	daysAgo: number;
}

export const SAMPLE_INCIDENT_SEEDS: readonly SampleIncidentSeed[] = [
	{
		title: "Checkout 503s after promo email",
		reportedBy: "QA engineer",
		kind: "spike",
		peakLoadReqS: 2400,
		durationMin: 4,
		daysAgo: 3,
	},
	{
		title: "Nightly report job slows the API",
		reportedBy: "Infra engineer",
		kind: "batch",
		peakLoadReqS: 1800,
		durationMin: 30,
		daysAgo: 5,
	},
	{
		title: "Login latency after deploy",
		reportedBy: "QA engineer",
		kind: "spike",
		peakLoadReqS: 900,
		durationMin: 10,
		daysAgo: 8,
	},
	{
		title: "Worker memory climbs overnight",
		reportedBy: "Infra engineer",
		kind: "leak",
		peakLoadReqS: 600,
		durationMin: 480,
		daysAgo: 10,
	},
];
