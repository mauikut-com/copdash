/// <reference types="astro/client" />

import type { Runtime } from "@astrojs/cloudflare";

/**
 * Cloudflare bindings exposed on `Astro.locals.runtime.env`.
 *
 * `copdash_db` is typed as `unknown` until the backend is implemented; the D1
 * binding itself is already declared in `wrangler.json`. The generated
 * `worker-configuration.d.ts` is intentionally excluded from `tsconfig.json`
 * because its workerd runtime types (e.g. a global `Element` for HTMLRewriter)
 * conflict with the DOM lib used by client-side code.
 */
interface Env {
	copdash_db: unknown;
}

declare namespace App {
	interface Locals extends Runtime<Env> {}
}
