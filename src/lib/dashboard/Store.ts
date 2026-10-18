import { STORAGE_KEY } from "./constants";
import type { PersistedState } from "./types";

/**
 * Persists application state to `localStorage` (or any `Storage`-like object).
 * All operations are best-effort: read/write failures (quota exceeded, privacy
 * mode, unavailable storage) degrade gracefully to an in-memory session.
 */
export class Store {
	constructor(
		private readonly storage: Storage | null,
		private readonly key: string = STORAGE_KEY,
	) {}

	/** Load the persisted state, or `null` when absent or unreadable. */
	load(): PersistedState | null {
		if (!this.storage) return null;
		try {
			const raw = this.storage.getItem(this.key);
			return raw === null ? null : (JSON.parse(raw) as PersistedState);
		} catch {
			return null;
		}
	}

	save(state: PersistedState): void {
		if (!this.storage) return;
		try {
			this.storage.setItem(this.key, JSON.stringify(state));
		} catch {
			// Persistence is best-effort; ignore failures.
		}
	}
}
