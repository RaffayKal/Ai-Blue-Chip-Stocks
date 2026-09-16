/**
 * Cloudflare Workflow: read-only, notify-only crypto quote check.
 *
 * Same job as workers/scheduled_entrypoint.py's scheduled() handler, but
 * expressed as a durable multi-step Workflow instead of a single cron
 * function -- each step gets its own retry/state checkpointing.
 *
 * This never places an order and never reaches Robinhood or the local
 * capital_engine gate (those only run on the operator's machine).
 *
 * Bindings required in wrangler.toml:
 *   [vars]
 *   SYMBOL = "BTC/USD"
 *   SPREAD_BPS_THRESHOLD = "50"
 *
 * Secrets required (`wrangler secret put <NAME>`):
 *   ALPACA_API_KEY_ID
 *   ALPACA_API_SECRET_KEY
 *   NOTIFY_WEBHOOK_URL
 *
 * Trigger this Workflow from a Worker's scheduled() handler bound via
 * [triggers] crons in wrangler.toml, calling env.VIABILITY_WORKFLOW.create().
 */
import { WorkflowEntrypoint, WorkflowStep, WorkflowEvent } from "cloudflare:workers";

interface Env {
	ALPACA_API_KEY_ID: string;
	ALPACA_API_SECRET_KEY: string;
	NOTIFY_WEBHOOK_URL?: string;
	SYMBOL?: string;
	SPREAD_BPS_THRESHOLD?: string;
}

type Params = Record<string, never>;

interface Quote {
	bid: number;
	ask: number;
	mid: number;
	spreadBps: number;
}

export class ViabilityWorkflow extends WorkflowEntrypoint<Env, Params> {
	async run(event: WorkflowEvent<Params>, step: WorkflowStep) {
		const symbol = this.env.SYMBOL ?? "BTC/USD";
		const thresholdBps = Number(this.env.SPREAD_BPS_THRESHOLD ?? "50");
		const triggeredBy = event.schedule
			? `cron="${event.schedule.cron}" scheduledTime=${new Date(event.schedule.scheduledTime).toISOString()}`
			: `manual instanceId=${event.instanceId}`;
		console.log(`VIABILITY_WORKFLOW_START ${triggeredBy}`);

		const quote = await step.do("fetch-alpaca-quote", async (): Promise<Quote | null> => {
			const url = `https://data.alpaca.markets/v1beta3/crypto/us/latest/quotes?symbols=${encodeURIComponent(symbol)}`;
			const response = await fetch(url, {
				headers: {
					"APCA-API-KEY-ID": this.env.ALPACA_API_KEY_ID,
					"APCA-API-SECRET-KEY": this.env.ALPACA_API_SECRET_KEY,
				},
			});
			if (!response.ok) {
				throw new Error(`ALPACA_QUOTE_ERROR status=${response.status}`);
			}
			const payload: any = await response.json();
			const raw = payload?.quotes?.[symbol];
			const bid = raw?.bp;
			const ask = raw?.ap;
			if (!bid || !ask || bid <= 0 || ask <= 0) {
				return null;
			}
			const mid = (bid + ask) / 2;
			const spreadBps = ((ask - bid) / mid) * 10000;
			return { bid, ask, mid, spreadBps };
		});

		if (!quote) {
			return { state: "NO_QUOTE_RETURNED", instanceId: event.instanceId };
		}

		const viable = await step.do("evaluate-spread", async () => {
			return quote.spreadBps <= thresholdBps;
		});

		if (!viable) {
			return { state: "SPREAD_TOO_WIDE_NO_NOTIFY", quote, instanceId: event.instanceId };
		}

		if (!this.env.NOTIFY_WEBHOOK_URL) {
			return { state: "VIABLE_BUT_NO_WEBHOOK_CONFIGURED", quote, instanceId: event.instanceId };
		}

		await step.do("notify-webhook", async () => {
			const message =
				`[Alpaca workflow check] ${symbol} bid=${quote.bid} ask=${quote.ask} ` +
				`spread_bps=${quote.spreadBps.toFixed(1)} -- data signal only, not a trade. ` +
				`Review manually before any action. (instanceId=${event.instanceId})`;
			await fetch(this.env.NOTIFY_WEBHOOK_URL as string, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ text: message }),
			});
		});

		return { state: "NOTIFIED", quote, instanceId: event.instanceId };
	}
}
