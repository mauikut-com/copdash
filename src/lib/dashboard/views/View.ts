import type { App } from "../App";

/**
 * Base class for a dashboard view. A view renders its own markup and, once
 * that markup is in the DOM, binds its own event handlers.
 */
export abstract class View {
	constructor(protected readonly app: App) {}

	/** Return the view's HTML. */
	abstract render(): string;

	/** Bind event handlers after `render`'s output has been inserted. */
	mount(): void {}

	/** Render a labelled numeric input field. */
	protected numberField(id: string, label: string, value: number): string {
		return `<div><label for="${id}">${label}</label><input id="${id}" type="number" step="any" min="0" inputmode="decimal" value="${value}"></div>`;
	}
}
