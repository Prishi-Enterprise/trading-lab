import Link from "next/link";
import { Brand } from "@/components/brand";

export function LabHeader({
  active,
  displayName,
}: {
  active: "stocks" | "commodities";
  displayName: string;
}) {
  return (
    <header className="topbar">
      <Brand inverse />
      <nav className="lab-nav" aria-label="Trading Lab sections">
        <Link className={active === "stocks" ? "active" : ""} href="/stocks">Stocks</Link>
        <Link className={active === "commodities" ? "active" : ""} href="/commodities">Commodities</Link>
      </nav>
      <div className="topbar-meta">
        <span className="mode-pill"><i /> RESEARCH ONLY</span>
        <span className="user-name">{displayName}</span>
        <form action="/auth/signout" method="post"><button className="signout-button">Sign out</button></form>
      </div>
    </header>
  );
}
