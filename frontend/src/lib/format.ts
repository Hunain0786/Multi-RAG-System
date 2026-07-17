import type { MetricFormat } from "@/lib/types";

const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const usdDetailed = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

const integer = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const decimal = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatCell(value: unknown, format: MetricFormat): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") {
    switch (format) {
      case "currency_usd":
        return Math.abs(value) >= 1000 ? usd.format(value) : usdDetailed.format(value);
      case "percentage":
        // Backend already sends "X.YZ" style numbers in %; keep 2dp.
        return `${decimal.format(value)}%`;
      case "integer":
        return integer.format(value);
      case "number":
        return decimal.format(value);
      case "days":
        return `${integer.format(value)} d`;
      case "string":
        return String(value);
    }
  }
  return String(value);
}

const dateFmt = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
});
const dateTimeFmt = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return dateFmt.format(d);
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return dateTimeFmt.format(d);
}

export function formatDurationMs(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}
