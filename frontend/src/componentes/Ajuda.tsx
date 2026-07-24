// Pequenos componentes de UI reutilizáveis: tooltip de ajuda e rótulo de campo.

import type { ReactNode } from "react";

export function Tooltip({ texto }: { texto: string }) {
  return (
    <span className="tooltip" role="img" aria-label="Ajuda">
      ?<span className="tooltip-balao">{texto}</span>
    </span>
  );
}

export function Campo({
  rotulo,
  ajuda,
  dica,
  children,
}: {
  rotulo: string;
  ajuda?: string; // texto auxiliar sempre visível, abaixo do campo
  dica?: string; // texto do tooltip (?), ao lado do rótulo
  children: ReactNode;
}) {
  return (
    <div className="campo">
      <label className="campo-rotulo">
        {rotulo}
        {dica && <Tooltip texto={dica} />}
      </label>
      {children}
      {ajuda && <div className="campo-ajuda">{ajuda}</div>}
    </div>
  );
}
