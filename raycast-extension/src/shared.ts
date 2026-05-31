import { execSync } from "child_process";

const OHHOME = `${process.env.HOME}/.ohright`;
const PYTHON = "/usr/bin/python3";

export interface OhRightResult {
  title: string;
  subtitle: string;
  type: string;
  attention: number;
  match?: number;
  revisits?: number;
  last_seen?: string;
  dwell_hours?: number;
  url?: string;
  status?: string;
}

export interface OhRightStats {
  graph: {
    total_nodes: number;
    active: number;
    dormant: number;
    abandoned: number;
  };
  events: {
    raw: number;
    semantic: number;
  };
  types: Record<string, number>;
}

/**
 * Run a query command and return parsed results.
 */
export function runQuery(command: string, arg?: string): OhRightResult[] | OhRightStats {
  const cmd = arg
    ? `cd ${OHHOME} && ${PYTHON} query.py ${command} "${arg.replace(/"/g, '\\"')}"`
    : `cd ${OHHOME} && ${PYTHON} query.py ${command}`;

  try {
    const output = execSync(cmd, {
      timeout: 10000,
      maxBuffer: 1024 * 1024,
      encoding: "utf-8",
    });

    // Filter out warnings (urllib3 etc.)
    const jsonStart = output.indexOf("[");
    const jsonStart2 = output.indexOf("{");
    let cleanOutput = output;

    if (jsonStart >= 0 && (jsonStart < jsonStart2 || jsonStart2 < 0)) {
      cleanOutput = output.slice(jsonStart);
    } else if (jsonStart2 >= 0) {
      cleanOutput = output.slice(jsonStart2);
    }

    return JSON.parse(cleanOutput);
  } catch (error) {
    console.error("Query error:", error);
    return [];
  }
}

/**
 * Run ask.py for natural language queries.
 */
export function runAsk(query: string): { results: OhRightResult[]; message: string } {
  const cmd = `cd ${OHHOME} && ${PYTHON} ask.py "${query.replace(/"/g, '\\"')}"`;

  try {
    const output = execSync(cmd, {
      timeout: 15000,
      maxBuffer: 1024 * 1024,
      encoding: "utf-8",
    });

    return parseAskOutput(output);
  } catch (error) {
    console.error("Ask error:", error);
    return { results: [], message: "OhRight couldn't process your query. Is screenpipe running?" };
  }
}

/**
 * Parse the text output from ask.py back into structured data.
 * ask.py outputs formatted text but we also run query.py directly for structure.
 */
function parseAskOutput(output: string): { results: OhRightResult[]; message: string } {
  // For now, we'll run query.py alongside for structured data.
  // The formatted output from ask.py is used as fallback.
  const lines = output.split("\n");
  const message = lines[0] || "";
  return { results: [], message };
}

/**
 * Check if OhRight is installed and configured.
 */
export function checkSetup(): { installed: boolean; hasKeys: boolean; screenpipeRunning: boolean } {
  try {
    execSync(`test -f ${OHHOME}/query.py`, { timeout: 2000 });
    const hasOpenAI = execSync(`test -f ${OHHOME}/.openai_key && echo yes || echo no`, {
      encoding: "utf-8",
      timeout: 2000,
    }).trim();
    const hasSP = execSync(`test -f ${OHHOME}/.sp_key && echo yes || echo no`, {
      encoding: "utf-8",
      timeout: 2000,
    }).trim();

    let screenpipeRunning = false;
    try {
      execSync("curl -s -o /dev/null -w '%{http_code}' http://localhost:3030/health", {
        timeout: 3000,
      });
      screenpipeRunning = true;
    } catch {
      // screenpipe not running
    }

    return {
      installed: true,
      hasKeys: hasOpenAI === "yes" && hasSP === "yes",
      screenpipeRunning,
    };
  } catch {
    return { installed: false, hasKeys: false, screenpipeRunning: false };
  }
}

/**
 * Get attention bar for visual display.
 */
export function attentionBar(score: number): string {
  const filled = Math.round(score * 8);
  return "█".repeat(filled) + "░".repeat(8 - filled);
}

/**
 * Get emoji for node type.
 */
export function typeEmoji(type: string): string {
  const map: Record<string, string> = {
    product: "🛒",
    interest: "🔥",
    project: "📁",
    workflow: "⚙️",
    habit: "🔄",
    job: "💼",
    travel: "✈️",
    media: "🎵",
    social: "💬",
  };
  return map[type] || "📌";
}
