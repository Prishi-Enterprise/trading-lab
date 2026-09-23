import Link from "next/link";

export function Brand({ inverse = false }: { inverse?: boolean }) {
  return (
    <Link className={`brand ${inverse ? "brand-inverse" : ""}`} href="/" aria-label="Prishi Trading Lab home">
      <span className="brand-mark" aria-hidden="true">p</span>
      <span>
        <strong>prishi<span>.</span></strong>
        <small>TRADING LAB</small>
      </span>
    </Link>
  );
}
