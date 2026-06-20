"""Prompt contract text for Stage 3.0 typed-AST operator search.

This module is data-only. It defines the boundary text that a future Stage 3
LLM caller must use, but it does not call an LLM or depend on any LLM SDK.
"""

from __future__ import annotations

from dataclasses import dataclass


PROMPT_CONTRACT_SCHEMA_VERSION = "loco.operator_prompt_contract.v1"


@dataclass(frozen=True)
class OperatorPromptContract:
    schema_version: str
    system_rules: tuple[str, ...]
    output_rules: tuple[str, ...]
    forbidden_rules: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "system_rules": list(self.system_rules),
            "output_rules": list(self.output_rules),
            "forbidden_rules": list(self.forbidden_rules),
        }


def build_operator_prompt_contract() -> OperatorPromptContract:
    """Return the frozen Stage 3.0 prompt boundary contract."""

    system_rules = (
        "You may propose only a typed coordination operator AST.",
        "The AST may act only on shared variables in overlapping LSGO.",
        "The AST must coordinate conflicting proposals for shared variables.",
        "You must do not generate optimizer logic or optimizer implementations.",
        "You must do not generate scheduler logic.",
        "You must do not generate controller logic.",
        "You must do not select optimizer or modify BaseOpt.",
        "The protocol allows no test feedback access during search.",
        "The protocol allows no benchmark-specific metadata access.",
        "The protocol allows no arbitrary executable code.",
    )
    output_rules = (
        "Return a JSON object with schema_version loco.llm_candidate.v1.",
        "The JSON object must wrap a loco.dsl.v1 typed coordination operator AST.",
        "The declared_scope target must be shared_variables_only.",
        "All negative boundary flags must be true.",
    )
    forbidden_rules = (
        "no optimizer generation",
        "no scheduler/controller generation",
        "no optimizer selection",
        "no BaseOpt modification",
        "no benchmark objective rewrite",
        "no test feedback",
        "no benchmark-specific metadata",
        "no arbitrary executable code",
    )
    return OperatorPromptContract(
        schema_version=PROMPT_CONTRACT_SCHEMA_VERSION,
        system_rules=system_rules,
        output_rules=output_rules,
        forbidden_rules=forbidden_rules,
    )
