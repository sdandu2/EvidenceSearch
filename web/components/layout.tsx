"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, ArrowUpRight, Atom, FlaskConical, Search } from "lucide-react";
import { motion } from "motion/react";
import type { ReactNode } from "react";

const navigation = [
  { href: "/classic", label: "Discover", icon: Search },
  { href: "/performance", label: "Performance", icon: Activity },
  { href: "/methodology", label: "Methodology", icon: FlaskConical },
];

export function Shell({ children }: { children: ReactNode }) {
  const current = usePathname();
  if (current === "/" || current === "/observatory") return <>{children}</>;
  return <div className="site-shell">
    <a className="skip" href="#main">Skip to content</a>
    <aside className="rail" aria-label="Main navigation">
      <Link className="brand" href="/"><span className="brand-symbol"><Atom size={25} strokeWidth={1.4}/></span><span><strong>Evidence<span>Search</span></strong><small>SCIENTIFIC RETRIEVAL</small></span></Link>
      <div className="rail-group"><span className="rail-caption">WORKSPACE</span>
        <nav className="rail-nav">{navigation.map(item => {
          const Icon = item.icon; const active = current === item.href;
          return <Link href={item.href} key={item.href} className={`rail-link ${active ? "current" : ""}`} aria-current={active ? "page" : undefined}><Icon size={18}/><span>{item.label}</span>{active && <motion.span layoutId="rail-dot" className="nav-dot"/>}</Link>;
        })}</nav>
      </div>
      <div className="rail-footer"><div className="rail-version">V4.1 · RESEARCH WORKSPACE</div></div>
    </aside>
    <div className="main-shell"><header className="topbar"><span className="breadcrumbs">WORKSPACE <span>/</span> {navigation.find(n=>n.href===current)?.label || "Discover"}</span><div className="topbar-right"><span className="environment-label"><span className="pulse-dot"/> SciFact · 5,183 abstracts</span><a href="https://github.com/beir-cellar/beir" target="_blank" rel="noreferrer" className="icon-button" aria-label="About SciFact benchmark"><ArrowUpRight size={18}/></a></div></header>
      <main id="main" className="app-main">{children}</main>
      <footer className="footer"><span>EvidenceSearch · scientific relevance, not truth classification</span><span>Built around traceable research</span></footer>
    </div>
  </div>;
}
