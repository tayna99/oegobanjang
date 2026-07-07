import { Send, Sparkles } from "lucide-react";
import { useState } from "react";

export function ChatPromptBox({
  compact,
  placeholder,
  prompts,
}: {
  compact?: boolean;
  placeholder: string;
  prompts: string[];
}) {
  const [answer, setAnswer] = useState<string | null>(null);

  function answerFor(prompt: string) {
    if (prompt.includes("우선")) {
      return "체류만료 D-30이고 표준근로계약서 사본과 여권 사본이 빠져 있어 먼저 확인해야 합니다.";
    }
    if (prompt.includes("정중")) {
      return "정중한 요청 문구로 바꿨습니다. 승인 전에는 실제 발송되지 않습니다.";
    }
    if (prompt.includes("응답")) {
      return "2일 동안 응답이 없으면 리마인드 메시지를 제안합니다.";
    }
    return "요청 내용을 반영해 데모 답변을 준비했습니다.";
  }

  return (
    <section className={compact ? "mobile-demo-chat compact" : "mobile-demo-chat"}>
      {!compact ? <h3>AI에게 요청하기</h3> : null}
      <button className="mobile-demo-chat-input" onClick={() => setAnswer(answerFor(placeholder))} type="button">
        <Sparkles aria-hidden="true" />
        <span>{placeholder}</span>
        <Send aria-hidden="true" />
      </button>
      <div className="mobile-demo-chip-row">
        {prompts.map((prompt) => (
          <button key={prompt} onClick={() => setAnswer(answerFor(prompt))} type="button">
            {prompt}
          </button>
        ))}
      </div>
      {answer ? <p className="mobile-demo-chat-answer">{answer}</p> : null}
    </section>
  );
}
