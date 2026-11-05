"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { API_URL } from "@/lib/api";

type Citation = {
  page: number;
  excerpt: string;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
};

type DocumentChatProps = {
  documentId: string;
  documentName: string;
  isPreparingDocument: boolean;
  isGenerating: boolean;
  onPrepareDocument: () => Promise<string>;
  onCitationClick: (page: number) => void;
};

export default function DocumentChat({
  documentId,
  documentName,
  isPreparingDocument,
  isGenerating,
  onPrepareDocument,
  onCitationClick,
}: DocumentChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [error, setError] = useState("");
  const [isSending, setIsSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isSending]);

  async function sendQuestion(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const text = question.trim();
    if (!text || isSending || isGenerating) return;

    setIsSending(true);
    setError("");

    try {
      const activeDocumentId = documentId || await onPrepareDocument();
      const history = messages.slice(-8).map(({ role, content }) => ({
        role,
        content,
      }));
      const userMessage: Message = { role: "user", content: text };
      setMessages((previous) => [...previous, userMessage]);
      setQuestion("");

      const response = await fetch(
        `${API_URL}/chat/${activeDocumentId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: text, history }),
        }
      );
      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : `Chat request failed (${response.status}).`
        );
      }

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: result.answer,
          citations: result.citations,
        },
      ]);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Could not get an answer from the document."
      );
    } finally {
      setIsSending(false);
    }
  }

  function handleQuestionKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendQuestion();
    }
  }

  const busy = isSending || isPreparingDocument || isGenerating;

  return (
    <section className="studio-card mt-6 rounded-3xl border border-white/10 bg-[#11111b]/90 p-5 md:p-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold">Chat with your document</h3>
          <p className="mt-1 text-sm text-gray-400">
            Ask questions and get answers grounded in the uploaded file.
          </p>
        </div>
        {documentId && (
          <span className="max-w-full truncate rounded-full border border-[#dedfd6] bg-[#f5f5ef] px-3 py-1 text-xs text-[#53665c]">
            {documentName || "Document ready"}
          </span>
        )}
      </div>

      {!documentId && (
        <div className="mt-6 rounded-2xl border border-dashed border-white/10 p-8 text-center">
          <p className="text-sm text-gray-300">
            {documentName
              ? "Send a question to upload this document and start chatting."
              : "Select a PDF or PPTX above to start a document chat."}
          </p>
          {!documentName && (
            <p className="mt-2 text-xs text-gray-500">
              Answers are generated from retrieved passages; citations link to
              their source pages.
            </p>
          )}
        </div>
      )}

      {documentId && (
        <div
          ref={scrollRef}
          className="mt-6 max-h-[440px] min-h-32 space-y-4 overflow-y-auto rounded-2xl border border-[#dedfd6] bg-[#f8f8f3] p-4"
          aria-live="polite"
        >
          {messages.length === 0 && (
            <p className="py-8 text-center text-sm text-gray-500">
              Ask about the document&apos;s key ideas, details, or conclusions.
            </p>
          )}
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`max-w-[90%] rounded-2xl px-4 py-3 text-sm leading-6 ${
                message.role === "user"
                  ? "ml-auto bg-[#e6eee8] text-[#26332e]"
                  : "mr-auto border border-[#e4e4dc] bg-white text-gray-200"
              }`}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>
              {!!message.citations?.length && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {message.citations.map((citation) => (
                    <button
                      key={citation.page}
                      type="button"
                      title={citation.excerpt}
                      onClick={() => onCitationClick(citation.page)}
                      className="rounded-full border border-[#d6e1d8] bg-[#eff4ef] px-3 py-1 text-xs text-[#31574b] hover:bg-[#e2ece4]"
                    >
                      Page {citation.page}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
          {isSending && (
            <p className="text-sm text-gray-500">Searching the document…</p>
          )}
        </div>
      )}

      <form onSubmit={sendQuestion} className="mt-4">
        <label htmlFor="document-question" className="sr-only">
          Ask a question about the document
        </label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <textarea
            id="document-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={handleQuestionKeyDown}
            maxLength={1500}
            rows={2}
            placeholder="Ask a question about this document…"
            disabled={!documentName || busy}
            className="min-h-12 flex-1 resize-y rounded-xl border border-[#dedfd6] bg-white px-4 py-3 text-sm text-[#202a26] outline-none placeholder:text-gray-500 focus:border-[#709080] disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!documentName || !question.trim() || busy}
            className="rounded-xl bg-[#294d42] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[#25473c] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? "Working…" : "Ask"}
          </button>
        </div>
        <p className="mt-2 text-xs text-gray-500">
          Search embeddings run locally. Relevant excerpts and your question
          are sent to Groq to generate the answer.
        </p>
        {error && (
          <p className="mt-3 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </p>
        )}
      </form>
    </section>
  );
}
