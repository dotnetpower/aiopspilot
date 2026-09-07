import { getLocale } from "../i18n";

const COPY = {
  en: {
    label: "Conversation model",
    hint: "Choose the model tier for new questions in this conversation.",
    auto: "Auto",
    t1: "T1 - Fast",
    t2Unavailable: "T2 - Unavailable",
    confirmT2: "T2 responses can take longer and cost more. Use T2 for new questions in this conversation?",
    appliesNext: "The conversation model will apply to the next question.",
  },
  ko: {
    label: "대화 모델",
    hint: "이 대화의 새 질문에 사용할 모델 등급을 선택합니다.",
    auto: "자동",
    t1: "T1 - 빠른 응답",
    t2Unavailable: "T2 - 사용 불가",
    confirmT2: "T2 응답은 더 오래 걸리고 비용이 증가할 수 있습니다. 이 대화의 새 질문에 T2를 사용하시겠습니까?",
    appliesNext: "선택한 대화 모델은 다음 질문부터 적용됩니다.",
  },
} as const;

export type ConversationModelCopyKey = keyof typeof COPY.en;

export function conversationModelText(key: ConversationModelCopyKey): string {
  return COPY[getLocale()][key];
}

export function conversationT2Label(model: string): string {
  return `T2 - ${model}`;
}
