// The card part of the patient's "Pay your bill" popup. Looks like a real checkout,
// but it is a simulation (see cardMock.js): no bank is contacted and nothing sensitive is stored.
import { Icon } from "../../shared/Icon.jsx";
import { brand, formatExpiry, formatNumber, TEST_CARD } from "./cardMock.js";

export function CardCheckout({ card, setCard, disabled }) {
  const set = (k) => (e) => setCard({ ...card, [k]: e.target.value });
  const b = brand(card.number);
  const shown = (formatNumber(card.number) + " " + "•••• •••• •••• ••••".slice(formatNumber(card.number).length)).trim();
  const amex = b === "Amex";
  return (
    <>
      <div className="card-preview" aria-hidden="true">
        <div className="card-top"><Icon name="creditCard" /><span>{b || "Card"}</span></div>
        <div className="card-num">{shown}</div>
        <div className="card-bottom">
          <span>{card.name.trim() || "NAME ON CARD"}</span>
          <span>{card.expiry || "MM/YY"}</span>
        </div>
      </div>
      <label>Card number
        <input inputMode="numeric" autoComplete="cc-number" placeholder="1234 1234 1234 1234" disabled={disabled}
               value={card.number} onChange={(e) => setCard({ ...card, number: formatNumber(e.target.value) })} required />
      </label>
      <label>Name on card
        <input autoComplete="cc-name" placeholder="As printed on the card" maxLength={40} disabled={disabled}
               value={card.name} onChange={set("name")} required />
      </label>
      <div className="card-row">
        <label>Expiry
          <input inputMode="numeric" autoComplete="cc-exp" placeholder="MM/YY" maxLength={5} disabled={disabled}
                 value={card.expiry} onChange={(e) => setCard({ ...card, expiry: formatExpiry(e.target.value) })} required />
        </label>
        <label>Security code
          <input inputMode="numeric" type="password" autoComplete="cc-csc" placeholder={amex ? "4 digits" : "3 digits"} maxLength={4} disabled={disabled}
                 value={card.cvv} onChange={(e) => setCard({ ...card, cvv: e.target.value.replace(/\D/g, "") })} required />
        </label>
      </div>
      <p className="hint pay-note"><Icon name="lock" /> Demo checkout: no real payment is made. Use test card <button type="button" className="link-btn" disabled={disabled}
        onClick={() => setCard({ number: TEST_CARD, name: card.name || "TEST PATIENT", expiry: "12/30", cvv: "123" })}>{TEST_CARD}</button>.</p>
    </>
  );
}
