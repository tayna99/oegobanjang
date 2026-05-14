export type OperatorRole = "viewer" | "manager" | "admin" | "system";

export type OperatorContext = {
  companyId: string;
  userId: string;
  role: OperatorRole;
};

const STORAGE_KEY = "workbridge.operatorContext";

export const defaultOperatorContext: OperatorContext = {
  companyId: "company_001",
  userId: "manager_001",
  role: "manager",
};

function isOperatorRole(value: unknown): value is OperatorRole {
  return value === "viewer" || value === "manager" || value === "admin" || value === "system";
}

export function getOperatorContext(): OperatorContext {
  if (typeof window === "undefined") {
    return defaultOperatorContext;
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return defaultOperatorContext;
    }
    const parsed = JSON.parse(raw) as Partial<OperatorContext>;
    return {
      companyId: parsed.companyId || defaultOperatorContext.companyId,
      userId: parsed.userId || defaultOperatorContext.userId,
      role: isOperatorRole(parsed.role) ? parsed.role : defaultOperatorContext.role,
    };
  } catch {
    return defaultOperatorContext;
  }
}

export function setOperatorContext(context: OperatorContext) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(context));
  window.dispatchEvent(new Event("workbridge-operator-context-change"));
}

export function getOperatorHeaders(overrides: Partial<OperatorContext> = {}): Record<string, string> {
  const context = { ...getOperatorContext(), ...overrides };
  return {
    "X-Company-Id": context.companyId,
    "X-User-Id": context.userId,
    "X-User-Role": context.role,
  };
}
