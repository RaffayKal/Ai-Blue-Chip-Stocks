import { DurableObject } from "cloudflare:workers";

type QuoteSnapshot = {
	asset_class: "crypto" | "equity";
	symbol: string;
	bid: number;
	ask: number;
	last: number;
	quote_timestamp: string;
	source: "robinhood";
	execution_authority: "robinhood";
};

const MAX_AGE_SECONDS = 7;

function json(body: unknown, status = 200): Response {
	return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

function authorized(request: Request, env: Env & { RUNPOD_RELAY_TOKEN?: string }): boolean {
	const token = env.RUNPOD_RELAY_TOKEN;
	return Boolean(token && request.headers.get("authorization") === `Bearer ${token}`);
}

function parseSnapshot(value: unknown): QuoteSnapshot | null {
	if (!value || typeof value !== "object") return null;
	const item = value as Record<string, unknown>;
	const numbers = [item.bid, item.ask, item.last];
	if ((item.asset_class !== "crypto" && item.asset_class !== "equity") ||
		item.source !== "robinhood" || item.execution_authority !== "robinhood" ||
		typeof item.symbol !== "string" || !item.symbol ||
		numbers.some((value) => typeof value !== "number" || !Number.isFinite(value) || value <= 0) ||
		typeof item.quote_timestamp !== "string" || !Number.isFinite(Date.parse(item.quote_timestamp))) return null;
	return item as QuoteSnapshot;
}

export class MyDurableObject extends DurableObject<Env> {
	async putSnapshot(snapshot: QuoteSnapshot): Promise<void> { await this.ctx.storage.put("latest", snapshot); }
	async getSnapshot(): Promise<QuoteSnapshot | null> { return (await this.ctx.storage.get<QuoteSnapshot>("latest")) ?? null; }
}

export default {
	async fetch(request, env): Promise<Response> {
		const runtimeEnv = env as Env & { RUNPOD_RELAY_TOKEN?: string };
		const path = new URL(request.url).pathname;
		if (path === "/health" && request.method === "GET") return json({ ok: true, service: "robinhood-relay", authority: "robinhood" });
		if (!authorized(request, runtimeEnv)) return json({ ok: false, error: "unauthorized" }, 401);
		const stub = env.MY_DURABLE_OBJECT.getByName("robinhood");
		if (path === "/v1/robinhood/snapshot" && request.method === "PUT") {
			let snapshot: QuoteSnapshot | null = null;
			try { snapshot = parseSnapshot(await request.json()); } catch { snapshot = null; }
			if (!snapshot) return json({ ok: false, error: "invalid_robinhood_snapshot" }, 400);
			await stub.putSnapshot(snapshot);
			return json({ ok: true, stored: true, symbol: snapshot.symbol });
		}
		if (path === "/v1/robinhood/snapshot" && request.method === "GET") {
			const snapshot = await stub.getSnapshot();
			if (!snapshot) return json({ ok: false, status: "NO_ACTION", reason: "no_snapshot" }, 503);
			const ageSeconds = (Date.now() - Date.parse(snapshot.quote_timestamp)) / 1000;
			if (!Number.isFinite(ageSeconds) || ageSeconds < 0 || ageSeconds > MAX_AGE_SECONDS) return json({ ok: false, status: "NO_ACTION", reason: "stale_snapshot", age_seconds: ageSeconds }, 503);
			return json({ ok: true, status: "FRESH", age_seconds: ageSeconds, snapshot });
		}
		return json({ ok: false, error: "not_found" }, 404);
	},
} satisfies ExportedHandler<Env>;
