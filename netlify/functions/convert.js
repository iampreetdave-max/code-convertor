// Netlify serverless conversion endpoint.
//
// Lets the app run as a PURE STATIC deploy (no FastAPI backend to host).
// The Groq key lives in Netlify env vars (Site settings -> Environment
// variables -> GROQ_API_KEY) and is NEVER shipped in the published HTML.
//
// Returns exactly the same JSON shape as the FastAPI /convert endpoint, so the
// frontend works against either one unchanged.

const LANG = {
  python: "Python", javascript: "JavaScript", typescript: "TypeScript",
  java: "Java", html: "HTML", cpp: "C++", csharp: "C#", go: "Go",
  rust: "Rust", ruby: "Ruby", php: "PHP",
};

const SOURCES = ["python", "javascript", "typescript", "java", "html", "cpp", "csharp", "go", "rust", "ruby", "php"];
const TARGETS = ["python", "javascript", "typescript", "java", "cpp", "csharp", "go", "rust", "ruby", "php"];

function systemPrompt(source, target) {
  const s = LANG[source] || source;
  const t = LANG[target] || target;
  return `You are an expert polyglot code translator converting ${s} to clean, idiomatic, CORRECT ${t}.

Translate SEMANTICS faithfully - produce code a professional ${t} developer would actually write, not a token-by-token swap.

## RULES
- Map data structures, standard-library calls and idioms to their natural ${t} equivalents.
- Preserve behavior exactly. Keep names/structure recognizable.
- If the input is a standalone script, emit a runnable ${t} program (entry point / main / imports / class wrapper as ${t} requires).
- Where a construct has no faithful equivalent, translate the closest form and mark it with a "TODO: verify" comment instead of silently guessing.
- Do not invent APIs. Prefer the ${t} standard library.

## FIDELITY (CRITICAL)
Translate the ENTIRE input - convert EVERY function, class, statement and
declaration, one for one, in the same order. Do NOT summarize, merge,
deduplicate, refactor, generalize or omit anything, even if the input is long or
repetitive. Never replace repeated code with a single generalized version.

## OUTPUT FORMAT
Return ONLY the converted code inside a single \`\`\`${target} code fence. No prose
before or after. On the LAST line inside the fence add exactly:
// Conversion confidence: HIGH|MEDIUM|LOW - <short reason if not HIGH>`;
}

function extractCode(raw) {
  if (!raw) return "";
  let s = raw.trim();
  const m = s.match(/```[a-zA-Z]*\s*\n([\s\S]*?)```/);
  if (m) return m[1].trim();
  // One-sided / unclosed fence (model omitted the closer): strip what's there.
  s = s.replace(/^```[a-zA-Z]*\s*\n?/, "").replace(/\n?```\s*$/, "");
  return s.trim();
}

function stripMarker(code) {
  return code
    .split("\n")
    .filter((l) => !l.toLowerCase().includes("conversion confidence:"))
    .join("\n")
    .replace(/\s+$/, "");
}

function confidenceOf(raw) {
  const tail = raw.split("\n").slice(-6).join("\n").toLowerCase();
  if (tail.includes("conversion confidence:")) {
    if (tail.includes("high")) return 0.95;
    if (tail.includes("medium")) return 0.75;
    if (tail.includes("low")) return 0.5;
  }
  return 0.8;
}

function json(statusCode, body) {
  return {
    statusCode,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

function shape(code, source, target, confidence, warnings) {
  return {
    converted_code: code,
    source_language: source,
    target_language: target,
    conversion_confidence: confidence,
    warnings: warnings || [],
    unsupported_constructs: [],
    unsupported_lines_count: 0,
    conversion_level: 3,
    metadata: { method: "llm", provider: "groq", runtime: "netlify-function" },
  };
}

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") return json(405, { detail: "Method not allowed" });

  const key = process.env.GROQ_API_KEY;
  if (!key) {
    return json(500, {
      detail: "GROQ_API_KEY is not set. Add it in Netlify: Site settings -> Environment variables.",
    });
  }

  let body;
  try {
    body = JSON.parse(event.body || "{}");
  } catch (_) {
    return json(400, { detail: "Invalid JSON body" });
  }

  const code = (body.code || "").trim();
  const source = (body.source_language || "").toLowerCase();
  const target = (body.target_language || "").toLowerCase();

  if (!code) return json(400, { detail: "Code cannot be empty" });
  if (!source || !target) return json(400, { detail: "Source and target languages are required" });
  if (source === target) {
    return json(200, shape(code, source, target, 1.0, ["Source and target languages are the same"]));
  }
  if (!SOURCES.includes(source) || !TARGETS.includes(target)) {
    return json(400, {
      detail: `Conversion from ${source} to ${target} is not supported. Sources: ${SOURCES.join(", ")}. Targets: ${TARGETS.join(", ")}.`,
    });
  }

  try {
    const res = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${key}` },
      body: JSON.stringify({
        model: process.env.GROQ_MODEL || "llama-3.3-70b-versatile",
        temperature: 0.1,
        max_tokens: 8000,
        messages: [
          { role: "system", content: systemPrompt(source, target) },
          { role: "user", content: `Convert this ${source} to ${target}:\n\n${code}` },
        ],
      }),
    });

    if (!res.ok) {
      const text = await res.text();
      return json(502, { detail: `Groq API error (${res.status}): ${text.slice(0, 200)}` });
    }

    const data = await res.json();
    const raw = (data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content) || "";
    const converted = stripMarker(extractCode(raw));
    if (!converted.trim()) return json(502, { detail: "Model returned an empty conversion." });

    return json(200, shape(converted, source, target, confidenceOf(raw), []));
  } catch (e) {
    return json(500, { detail: `Conversion failed: ${e.message}` });
  }
};
