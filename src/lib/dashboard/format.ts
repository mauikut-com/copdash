/**
 * Formatting helpers shared across views.
 *
 * These are stateless, so they are exposed as static methods rather than
 * instance methods; there is no state to encapsulate.
 */
export class Format {
	private static readonly HTML_ESCAPES: Readonly<Record<string, string>> = {
		"&": "&amp;",
		"<": "&lt;",
		">": "&gt;",
		'"': "&quot;",
	};

	/** Escape a value for safe interpolation into HTML text or attributes. */
	static escape(value: unknown): string {
		return String(value).replace(/[&<>"]/g, (char) => Format.HTML_ESCAPES[char]);
	}

	/**
	 * Format a number to a fixed number of decimal places, trimming trailing
	 * zeros and a trailing decimal point (matching the reference output).
	 */
	static fixed(value: number, digits = 1): string {
		return String(Number(value.toFixed(digits)));
	}

	/** Round a ratio to a whole-number percentage. */
	static percent(ratio: number): number {
		return Math.round(ratio * 100);
	}

	/** Render an epoch timestamp as a short human date (e.g. "Oct 18"). */
	static date(epochMs: number): string {
		return new Date(epochMs).toLocaleDateString(undefined, {
			month: "short",
			day: "numeric",
		});
	}
}
