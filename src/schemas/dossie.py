"""Contrato de saida do agente: o dossie entregue a pessoa desenvolvedora."""

from datetime import datetime, timezone
from typing import List

from pydantic import BaseModel, Field

from src.schemas.issue import Issue
from src.schemas.plano import Plano
from src.schemas.revisao import DecisaoHumana
from src.schemas.triagem import Triagem


class Dossie(BaseModel):
    """O que foi decidido, por quem, com base em que."""

    issue: Issue
    triagem: Triagem
    plano: Plano
    decisao: DecisaoHumana
    fontes: List[str] = Field(
        default_factory=list,
        description="IDs realmente recuperados e citados, ex.: politica-de-engenharia#2",
    )
    alertas: List[str] = Field(
        default_factory=list,
        description="O que o guardrail de saida apontou e a pessoa revisora viu antes de decidir",
    )
    revisoes: int = 0
    gerado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    @classmethod
    def montar(
        cls,
        *,
        issue: Issue,
        triagem: Triagem,
        plano: Plano,
        decisao: DecisaoHumana,
        contexto: List[dict],
        alertas: List[str],
        revisoes: int,
    ) -> "Dossie":
        """Monta o dossie mantendo so as fontes que foram de fato recuperadas.

        A intersecao com o contexto derruba id inventado pelo modelo: o dossie nao
        carrega citacao que nao existe. O que foi derrubado ja esta em `alertas`,
        entao a invencao fica registrada em vez de sumir sem deixar rastro.
        """
        recuperados = {t["id"] for t in contexto}
        citados = set(triagem.fontes) | set(plano.fontes)
        return cls(
            issue=issue,
            triagem=triagem,
            plano=plano,
            decisao=decisao,
            fontes=sorted(citados & recuperados),
            alertas=alertas,
            revisoes=revisoes,
        )

    def markdown(self) -> str:
        """Renderiza o dossie para leitura humana."""
        linhas = [
            f"# Dossie {self.issue.id} - {self.issue.titulo}",
            "",
            f"**Projeto:** {self.issue.projeto}  ",
            f"**Autor da issue:** {self.issue.autor}  ",
            f"**Revisado por:** {self.decisao.revisor} ({self.decisao.acao})  ",
            f"**Gerado em:** {self.gerado_em}  ",
            f"**Rodadas de revisao:** {self.revisoes}",
            "",
            "## Triagem",
            "",
            f"- **Tipo:** {self.triagem.tipo}",
            f"- **Severidade:** {self.triagem.severidade}",
            f"- **Prioridade:** {self.triagem.prioridade}",
            f"- **Esforco:** {self.triagem.esforco}",
            f"- **Componentes:** {', '.join(self.triagem.componentes) or '-'}",
            "",
            self.triagem.justificativa,
            "",
            "## Plano",
            "",
            self.plano.resumo,
            "",
        ]
        for passo in sorted(self.plano.passos, key=lambda p: p.ordem):
            cobre = f" _({', '.join(passo.criterios_atendidos)})_" if passo.criterios_atendidos else ""
            linhas += [f"{passo.ordem}. **{passo.titulo}**{cobre}", f"   {passo.detalhe}"]

        linhas += ["", "## Testes a escrever", ""]
        linhas += [f"- {t}" for t in self.plano.testes]

        if self.plano.riscos:
            linhas += ["", "## Riscos", ""]
            linhas += [f"- {r}" for r in self.plano.riscos]

        linhas += ["", "## Fontes", ""]
        linhas += [f"- `{f}`" for f in self.fontes] or ["- _nenhuma: a triagem e o plano nao consultaram a base_"]

        if self.alertas:
            linhas += ["", "## Alertas da verificacao automatica", ""]
            linhas += [f"- {a}" for a in self.alertas]

        return "\n".join(linhas)
