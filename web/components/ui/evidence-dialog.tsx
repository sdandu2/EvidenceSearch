"use client";
import * as Dialog from "@radix-ui/react-dialog";
import { ArrowUpRight, Copy, X } from "lucide-react";
import type { Paper } from "@/lib/types";

export function EvidenceDialog({ paper, close }: {paper: Paper | null; close: () => void}) {
  return <Dialog.Root open={Boolean(paper)} onOpenChange={(open) => { if (!open) close(); }}>
    <Dialog.Portal>
      <Dialog.Overlay className="modal-backdrop" />
      <Dialog.Content className="document-modal" aria-describedby="evidence-desc">
        <div className="dialog-top"><span className="eyebrow">ORIGINAL CORPUS ABSTRACT · {paper?.document_id}</span><Dialog.Close className="icon-button" aria-label="Close abstract"><X size={20}/></Dialog.Close></div>
        <Dialog.Title className="modal-title">{paper?.title}</Dialog.Title>
        <Dialog.Description id="evidence-desc" className="dialog-subtitle">Text from the SciFact corpus. Ranking is not verification of this claim.</Dialog.Description>
        <div className="modal-text">{paper?.abstract}</div>
        <div className="dialog-bottom"><span className="caption">SciFact source record · {paper?.document_id}</span><button className="small-button" onClick={() => { if (paper) navigator.clipboard?.writeText(`${paper.title}\n\n${paper.abstract}`); }}><Copy size={15}/> Copy text</button></div>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}
