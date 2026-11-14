"use client";

/** Original atmospheric science illustrations. Decorative—not benchmark observations. */
export function ScienceScene({variant = "hero"}: {variant?: "hero" | "method" | "performance"}) {
  return <div className={`science-scene science-scene-${variant}`} aria-hidden="true">
    <div className="science-art-frame"><img src={variant === "performance" ? "/visuals/wavefield.svg" : variant === "method" ? "/visuals/microstructure.svg" : "/visuals/evidence-field.svg"} alt="" /></div>
    <div className="science-ambient-ring science-ambient-ring-a" />
    <div className="science-ambient-ring science-ambient-ring-b" />
    <span className="science-ping science-ping-1" /><span className="science-ping science-ping-2" /><span className="science-ping science-ping-3" />
    <div className="science-art-caption">RESEARCH // SIGNALS // EVIDENCE</div>
  </div>;
}

export function ScienceTriad() {
  return <div className="science-triad" aria-label="Science-inspired visual studies">
    {[
      {src:"/visuals/microstructure.svg",title:"Observe",kind:"MICROSTRUCTURE"},
      {src:"/visuals/wavefield.svg",title:"Measure",kind:"SIGNAL DYNAMICS"},
      {src:"/visuals/lattice.svg",title:"Connect",kind:"EVIDENCE NETWORKS"},
    ].map((item,index) => <div className="science-study" key={item.kind}>
      <img src={item.src} alt="" loading="lazy" />
      <span className="science-study-shade" />
      <span className="science-study-counter">0{index+1} / SCIENCE STUDY</span>
      <span className="science-study-title">{item.title}<small>{item.kind}</small></span>
    </div>)}
    <p className="science-illustration-note">Original illustrative visuals, not scientific measurements or search results.</p>
  </div>;
}
