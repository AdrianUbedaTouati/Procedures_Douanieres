# -*- coding: utf-8 -*-
"""Prompts module - System prompts for the agent."""

from .prompts import (
    SYSTEM_PROMPT,
    ROUTING_SYSTEM_PROMPT,
    GRADING_SYSTEM_PROMPT,
    QUERY_REWRITE_SYSTEM_PROMPT,
    NO_CONTEXT_MESSAGE,
    INSUFFICIENT_CONTEXT_MESSAGE,
    CLARIFICATION_NEEDED_MESSAGE,
    create_answer_prompt,
    create_grading_prompt,
    create_query_rewrite_prompt,
    create_routing_prompt,
)

__all__ = [
    'SYSTEM_PROMPT',
    'ROUTING_SYSTEM_PROMPT',
    'GRADING_SYSTEM_PROMPT',
    'QUERY_REWRITE_SYSTEM_PROMPT',
    'NO_CONTEXT_MESSAGE',
    'INSUFFICIENT_CONTEXT_MESSAGE',
    'CLARIFICATION_NEEDED_MESSAGE',
    'create_answer_prompt',
    'create_grading_prompt',
    'create_query_rewrite_prompt',
    'create_routing_prompt',
]
