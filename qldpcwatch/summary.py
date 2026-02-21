from __future__ import annotations

from qldpcwatch.models import PaperExtraction

UNKNOWN = "Unknown / not specified"


def _fmt(value: str | None) -> str:
    if value is None or not str(value).strip():
        return UNKNOWN
    return str(value)


def render_summary_markdown(extraction: PaperExtraction) -> str:
    lines: list[str] = []
    lines.append(f"# {extraction.title}")
    lines.append("")
    lines.append(f"- arXiv: `{extraction.arxiv_id}{extraction.arxiv_version}`")
    lines.append(
        f"- Categories: {', '.join(extraction.categories) if extraction.categories else UNKNOWN}"
    )
    lines.append(
        f"- Relevance: **{extraction.relevance.label}** "
        f"(confidence {extraction.relevance.confidence:.2f})"
    )
    lines.append("")

    lines.append("## Decoder approach")
    lines.append(f"- Name: {_fmt(extraction.decoder.name)}")
    lines.append(f"- Family: {_fmt(extraction.decoder.decoder_family)}")
    lines.append(f"- Description: {_fmt(extraction.decoder.high_level_description)}")
    if extraction.decoder.key_ideas:
        lines.append("- Key ideas:")
        lines.extend(f"  - {idea}" for idea in extraction.decoder.key_ideas)
    else:
        lines.append(f"- Key ideas: {UNKNOWN}")
    lines.append("")

    lines.append("## Performance claims")
    if extraction.performance_claims.headline_claims:
        lines.extend(f"- {claim}" for claim in extraction.performance_claims.headline_claims)
    else:
        lines.append(f"- {UNKNOWN}")

    if extraction.performance_claims.thresholds:
        lines.append("")
        lines.append("### Thresholds")
        for thr in extraction.performance_claims.thresholds:
            val = str(thr.threshold_value) if thr.threshold_value is not None else "null"
            units = thr.threshold_units if thr.threshold_units else ""
            lines.append(
                f"- [{thr.level}] noise={thr.noise_model}; threshold={val} {units}".rstrip()
            )
            if thr.code_families:
                lines.append(f"  - code families: {', '.join(thr.code_families)}")
            if thr.comparisons:
                lines.append(f"  - comparisons: {', '.join(thr.comparisons)}")
            if thr.evidence:
                ev = thr.evidence[0]
                lines.append(
                    "  - evidence: "
                    f"page={ev.page}, section={_fmt(ev.section)}, quote={_fmt(ev.quote)}"
                )
    else:
        lines.append("")
        lines.append("### Thresholds")
        lines.append(f"- {UNKNOWN}")

    lines.append("")
    lines.append("## Simulations")
    if extraction.simulations:
        for sim in extraction.simulations:
            lines.append(
                f"- level={sim.simulation_level}; noise={sim.noise_model}; "
                f"codes={', '.join(sim.codes_tested) if sim.codes_tested else UNKNOWN}; "
                f"results={'; '.join(sim.main_results) if sim.main_results else UNKNOWN}"
            )
    else:
        lines.append(f"- {UNKNOWN}")

    lines.append("")
    lines.append("## Missing fields")
    if extraction.missing_fields:
        lines.extend(f"- {f}" for f in extraction.missing_fields)
    else:
        lines.append("- None")

    lines.append("")
    lines.append("## Links")
    lines.append(f"- Abstract: {extraction.links.abs_url}")
    lines.append(f"- PDF: {extraction.links.pdf_url}")
    lines.append(f"- DOI: {_fmt(extraction.links.doi)}")

    return "\n".join(lines) + "\n"
