const PASSPORT_PATTERN = /\b[A-Z]{1,2}[0-9]{6,9}\b/g;
const ALIEN_REGISTRATION_PATTERN = /\b[0-9]{6}-[0-9]{7}\b/g;
const PHONE_PATTERN = /\b010-[0-9]{3,4}-[0-9]{4}\b/g;

function maskMiddle(value: string, visibleStart = 2, visibleEnd = 2): string {
  if (value.length <= visibleStart + visibleEnd) {
    return "*".repeat(value.length);
  }

  return `${value.slice(0, visibleStart)}${"*".repeat(
    value.length - visibleStart - visibleEnd,
  )}${value.slice(-visibleEnd)}`;
}

export function maskSensitiveText(value: string): string {
  return value
    .replace(PASSPORT_PATTERN, (match) => maskMiddle(match, 2, 2))
    .replace(ALIEN_REGISTRATION_PATTERN, (match) => maskMiddle(match, 2, 2))
    .replace(PHONE_PATTERN, (match) => maskMiddle(match, 3, 2));
}

export function maskPassport(value: string): string {
  return maskMiddle(value, 2, 2);
}

export function maskPhone(value: string): string {
  return maskMiddle(value, 3, 2);
}
