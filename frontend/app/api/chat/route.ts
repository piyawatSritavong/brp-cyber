import { NextRequest, NextResponse } from "next/server";
import { SYSTEM_PROMPT } from "@/lib/systemContext";

const OLLAMA_URL = process.env.OLLAMA_URL ?? "http://localhost:11434";
const OLLAMA_MODEL = process.env.OLLAMA_MODEL ?? "llama3.2";

type HistoryMessage = { role: "user" | "agent"; text: string };

export async function POST(req: NextRequest) {
  const body = await req.json() as { message: string; history?: HistoryMessage[] };
  const { message, history = [] } = body;

  const messages = [
    { role: "system", content: SYSTEM_PROMPT },
    // Last 10 turns for context
    ...history.slice(-10).map((m) => ({
      role: m.role === "agent" ? "assistant" : "user",
      content: m.text,
    })),
    { role: "user", content: message },
  ];

  let ollamaRes: Response;
  try {
    ollamaRes = await fetch(`${OLLAMA_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: OLLAMA_MODEL, messages, stream: true }),
    });
  } catch {
    return NextResponse.json(
      { error: "Ollama ไม่พร้อมใช้งาน ตรวจสอบว่ารัน `ollama serve` แล้ว" },
      { status: 503 }
    );
  }

  if (!ollamaRes.ok || !ollamaRes.body) {
    const text = await ollamaRes.text().catch(() => "");
    return NextResponse.json(
      { error: `Ollama error ${ollamaRes.status}: ${text}` },
      { status: ollamaRes.status }
    );
  }

  // Stream Ollama response to client, extracting message.content from each JSON line
  const decoder = new TextDecoder();
  const encoder = new TextEncoder();
  const source = ollamaRes.body;

  const readable = new ReadableStream({
    async start(controller) {
      const reader = source.getReader();
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          for (const line of chunk.split("\n")) {
            const trimmed = line.trim();
            if (!trimmed) continue;
            try {
              const json = JSON.parse(trimmed) as {
                message?: { content?: string };
                done?: boolean;
              };
              if (json.message?.content) {
                controller.enqueue(encoder.encode(json.message.content));
              }
            } catch {
              // skip malformed lines
            }
          }
        }
      } catch (err) {
        controller.error(err);
      } finally {
        controller.close();
      }
    },
  });

  return new Response(readable, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
