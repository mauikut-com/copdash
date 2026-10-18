import { Format } from "./format";
import { INCIDENT_KINDS } from "./constants";
import type {
	Incident,
	IncidentInput,
	ResourceDemand,
	Verdict,
} from "./types";

/** Fixed demand contributed by a batch-job overlap, per resource. */
const BATCH_CPU_ADDED = 1.5;
const BATCH_RAM_ADDED = 2;

/** GB of RAM added per minute by a memory leak. */
const LEAK_GB_PER_MINUTE = 0.15;

/**
 * Produces a verdict for an incident.
 *
 * This mirrors the reference simulation and is a placeholder for the real
 * ServerAgent backend; when that API exists, `simulate` should be replaced
 * with a call to it while keeping the `Verdict` shape unchanged.
 */
export class VerdictEngine {
	simulate(input: IncidentInput): Verdict {
		const { spec, profile } = input;
		const { kind, peakLoadReqS: load, durationMin: duration } = input;

		let cpu = (load * profile.cpuMsPerRequest) / 1000;
		let ram = profile.idleRamGb + (load / 1000) * profile.ramGbPerKiloReqS;
		const network = (load * profile.responseKb * 8) / 1e6;

		const steps: string[] = [
			`Read the report: ${INCIDENT_KINDS[kind].toLowerCase()}, ${load.toLocaleString()} req/s for ${duration} min.`,
			`Loaded the spec: ${spec.cpuVcpu} vCPU, ${spec.ramGb} GB RAM, ${spec.networkGbps} Gbps.`,
			`Base demand: ${Format.fixed(cpu, 2)} vCPU, ${Format.fixed(ram, 2)} GB, ${Format.fixed(network, 2)} Gbps, from ${profile.cpuMsPerRequest} ms CPU and ${profile.responseKb} KB per request.`,
		];

		if (kind === "batch") {
			cpu += BATCH_CPU_ADDED;
			ram += BATCH_RAM_ADDED;
			steps.push("Batch overlap adds 1.5 vCPU and 2 GB.");
		}

		if (kind === "leak") {
			const leakGb = LEAK_GB_PER_MINUTE * duration;
			ram += leakGb;
			steps.push(`The leak adds ${Format.fixed(leakGb, 2)} GB over ${duration} min.`);
		}

		const seeds: ReadonlyArray<Omit<ResourceDemand, "ratio">> = [
			{ kind: "CPU", demand: cpu, capacity: spec.cpuVcpu, unit: "vCPU" },
			{ kind: "RAM", demand: ram, capacity: spec.ramGb, unit: "GB" },
			{ kind: "Network", demand: network, capacity: spec.networkGbps, unit: "Gbps" },
		];

		const demands: ResourceDemand[] = seeds.map((seed) => ({
			...seed,
			ratio: seed.demand / seed.capacity,
		}));

		const limiting = [...demands].sort((a, b) => b.ratio - a.ratio)[0];
		const overCapacity = demands.filter((demand) => demand.ratio > 1);

		steps.push(
			overCapacity.length > 0
				? `Compared demand to capacity: ${overCapacity.map((d) => d.kind).join(" and ")} exceed${overCapacity.length > 1 ? "" : "s"} it.`
				: `Compared demand to capacity: nothing exceeds it. ${limiting.kind} is tightest at ${Format.percent(limiting.ratio)}%.`,
		);

		return {
			demands,
			limiting,
			overCapacity,
			occurs: overCapacity.length > 0,
			steps,
		};
	}

	/** Recompute the verdict for a recorded incident. */
	simulateIncident(incident: Incident): Verdict {
		return this.simulate({
			...incident.report,
			spec: incident.spec,
			profile: incident.profile,
		});
	}
}
