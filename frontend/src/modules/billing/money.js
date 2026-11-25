// Money as the clinic shows it. One place to change the currency.
export const CURRENCY = "EGP";
export const money = (v) => `${CURRENCY} ${Number(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
/** Whole pounds when there are no piastres, for prices on cards: EGP 4,200 */
export const price = (v) => `${CURRENCY} ${Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
export const METHODS = { cash: "Cash", card: "Card", insurance: "Insurance" };
