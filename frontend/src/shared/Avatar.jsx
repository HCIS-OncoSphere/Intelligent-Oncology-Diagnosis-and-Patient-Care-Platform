// A person's picture: their uploaded photo, or their initials on a colored circle when there is none.
// The color comes from `seed` (use the user id) so the same person always gets the same color.
export function initials(name) {
  return String(name || "?").trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
}

export function Avatar({ src, name, size = 40, seed = 0, className = "" }) {
  const style = { width: size, height: size, fontSize: Math.round(size * 0.36) };
  return src
    ? <img className={`uavatar ${className}`} src={src} alt="" style={style} />
    : <span className={`uavatar uavatar-initials c${Math.abs(seed) % 5} ${className}`} style={style} aria-hidden="true">{initials(name)}</span>;
}
