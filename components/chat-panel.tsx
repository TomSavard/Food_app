"use client";

import { useEffect, useRef, useState } from "react";
import { MessageCircle, X, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";

export function ChatPanel() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, streaming]);

  async function send() {
    const text = input.trim();
    if (!text || streaming !== null) return;
    setInput("");
    setError(null);
    const next: ChatMessage[] = [...messages, { role: "user", text }];
    setMessages(next);
    setStreaming("");

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: next }),
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let assembled = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let idx: number;
        while ((idx = buf.indexOf("\n\n")) !== -1) {
          const event = buf.slice(0, idx).trim();
          buf = buf.slice(idx + 2);
          if (!event.startsWith("data: ")) continue;
          const payload = event.slice(6);
          if (payload === "[DONE]") continue;
          try {
            const obj = JSON.parse(payload);
            if (obj.text) {
              assembled += obj.text;
              setStreaming(assembled);
            } else if (obj.error) {
              throw new Error(obj.error);
            }
          } catch (e) {
            if (e instanceof SyntaxError) continue;
            throw e;
          }
        }
      }
      setMessages([...next, { role: "model", text: assembled }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setStreaming(null);
      inputRef.current?.focus();
    }
  }

  return (
    <>
      <Button
        size="icon"
        className="fixed bottom-6 right-6 z-50 h-14 w-14 rounded-full shadow-lg"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Fermer l'assistant" : "Ouvrir l'assistant"}
      >
        {open ? <X className="h-5 w-5" /> : <MessageCircle className="h-5 w-5" />}
      </Button>

      {open && (
        <div className="fixed bottom-24 right-6 z-50 flex h-[520px] w-[360px] max-w-[calc(100vw-2rem)] flex-col rounded-xl border bg-background shadow-2xl sm:right-6">
          <div className="flex items-center justify-between border-b px-4 py-3">
            <h3 className="text-base font-semibold">Assistant</h3>
            <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground" aria-label="Fermer">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div ref={scrollRef} className="flex-1 space-y-2 overflow-y-auto p-3 text-sm">
            {messages.length === 0 && !streaming && (
              <p className="text-muted-foreground">Demande-moi ce que tu veux sur tes recettes.</p>
            )}
            {messages.map((m, i) => (
              <Bubble key={i} role={m.role} text={m.text} />
            ))}
            {streaming !== null && <Bubble role="model" text={streaming || "…"} />}
            {error && <Bubble role="error" text={`Erreur: ${error}`} />}
          </div>
          <div className="flex gap-2 border-t p-3">
            <Input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              placeholder="Écris ton message…"
              disabled={streaming !== null}
            />
            <Button size="icon" onClick={send} disabled={streaming !== null || !input.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </>
  );
}

function Bubble({ role, text }: { role: "user" | "model" | "error"; text: string }) {
  return (
    <div
      className={cn(
        "max-w-[85%] whitespace-pre-wrap break-words rounded-xl px-3 py-2 text-sm",
        role === "user" && "ml-auto bg-primary text-primary-foreground",
        role === "model" && "bg-secondary text-secondary-foreground",
        role === "error" && "border border-destructive/50 bg-destructive/10 text-destructive"
      )}
    >
      {text}
    </div>
  );
}
