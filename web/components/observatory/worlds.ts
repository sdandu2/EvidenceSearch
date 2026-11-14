export type WorldKey = "neural" | "climate" | "quantum" | "genetics" | "immune";
export interface World {
  key:WorldKey; name:string; label:string; title:string; description:string;
  query:string; accent:string; coverage:"benchmark-adjacent"|"exploratory";
}
export const WORLDS:World[]=[
  {key:"neural",name:"Neuroscience",label:"THE LIVING NETWORK",title:"Inside the mind.",description:"Signals, circuitry and the mechanisms shaping the nervous system.",query:"Brain circuits are shaped by synaptic plasticity and neuronal activity.",accent:"#A5A2FF",coverage:"exploratory"},
  {key:"climate",name:"Climate",label:"THE DYNAMIC PLANET",title:"A changing planet.",description:"Atmospheric systems, warming signals and planetary feedback.",query:"Rising carbon dioxide concentrations contribute to global warming.",accent:"#73E1D0",coverage:"exploratory"},
  {key:"quantum",name:"Quantum",label:"THE PROBABILITY FIELD",title:"Beyond certainty.",description:"Quantum behavior, noise and physical information.",query:"Environmental noise contributes to decoherence in superconducting qubits.",accent:"#A2D3FF",coverage:"exploratory"},
  {key:"genetics",name:"Genetics",label:"THE CODE OF LIFE",title:"Patterns in the code.",description:"Genetic regulation, conservation and molecular processes.",query:"Sequence conservation in gene regulatory regions between species is a poor predictor of conserved functionality.",accent:"#F4B9CD",coverage:"benchmark-adjacent"},
  {key:"immune",name:"Immunology",label:"THE DEFENSE SYSTEM",title:"The science of response.",description:"Cells, signaling and the dynamic immune system.",query:"TCR/CD3 microdomains are required to induce the immunologic synapse to activate T cells.",accent:"#F5C68B",coverage:"benchmark-adjacent"},
];
