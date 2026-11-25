// Mock card checkout helpers. There is NO real payment gateway in this project:
// nothing here talks to a bank, and the full card number / CVV never leave the browser.
// Only the last 4 digits and a generated reference are sent to the API.

export const TEST_CARD = "4242 4242 4242 4242";   // always approved
export const DECLINE_CARD = "4000 0000 0000 0002"; // always declined

export const digits = (v) => String(v || "").replace(/\D/g, "");

export function brand(number) {
  const d = digits(number);
  if (/^4/.test(d)) return "Visa";
  if (/^(5[1-5]|2[2-7])/.test(d)) return "Mastercard";
  if (/^(5078|6304|6759|676[1-3])/.test(d)) return "Maestro";
  if (/^(34|37)/.test(d)) return "Amex";
  return "";
}

export function formatNumber(v) {
  const d = digits(v).slice(0, 19);
  return (d.match(/.{1,4}/g) || []).join(" ");
}

export function formatExpiry(v) {
  const d = digits(v).slice(0, 4);
  if (d.length < 3) return d.length === 2 && String(v).endsWith("/") ? d + "/" : d;
  return d.slice(0, 2) + "/" + d.slice(2);
}

export function luhn(number) {
  const d = digits(number);
  if (d.length < 13) return false;
  let sum = 0;
  for (let i = 0; i < d.length; i++) {
    let n = Number(d[d.length - 1 - i]);
    if (i % 2 === 1) { n *= 2; if (n > 9) n -= 9; }
    sum += n;
  }
  return sum % 10 === 0;
}

/** Returns an error message, or "" when the details look valid. */
export function validateCard({ number, name, expiry, cvv }) {
  if (!luhn(number)) return "That card number doesn't look right. Check it and try again.";
  if (name.trim().length < 2) return "Enter the name on the card.";
  const m = /^(\d{2})\/(\d{2})$/.exec(expiry);
  if (!m || Number(m[1]) < 1 || Number(m[1]) > 12) return "Enter the expiry date as MM/YY.";
  const now = new Date();
  const endOfMonth = new Date(2000 + Number(m[2]), Number(m[1]), 0, 23, 59, 59);
  if (endOfMonth < now) return "This card has expired.";
  const need = brand(number) === "Amex" ? 4 : 3;
  if (digits(cvv).length !== need) return `Enter the ${need}-digit security code.`;
  return "";
}

/** Pretend to ask a bank. Resolves after a short delay, or rejects with a decline reason. */
export function mockAuthorize(number) {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      if (digits(number) === digits(DECLINE_CARD)) reject(new Error("Your card was declined by the bank. Try another card."));
      else resolve();
    }, 1800);
  });
}

/** Stand-in for a gateway's transaction ID: MOCK-<last4>-<random>. Never contains the full number. */
export function makeReference(number) {
  const rand = (crypto.randomUUID?.() || String(Math.random()).slice(2)).replace(/-/g, "").slice(0, 10).toUpperCase();
  return `MOCK-${digits(number).slice(-4)}-${rand}`;
}
