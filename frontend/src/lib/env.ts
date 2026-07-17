import "server-only";

function required(name: string, value: string | undefined): string {
  if (!value || value.trim() === "") {
    throw new Error(
      `Missing required environment variable: ${name}. ` +
        `Add it to frontend/.env.local (see .env.local.example).`,
    );
  }
  return value;
}

export const env = {
  BACKEND_URL: required("BACKEND_URL", process.env.BACKEND_URL),
} as const;
