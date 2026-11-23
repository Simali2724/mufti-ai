from app.core.config import settings

# llama.cpp compiles a JSON Schema into a GBNF grammar and expands every length and count
# bound into explicit repetition, so `maxLength: 700` becomes hundreds of grammar
# alternatives that are re-evaluated for each sampled token. Measured on this machine with
# qwen3:1.7b and an identical prompt: the full schema produced 634 output tokens in 394s
# (1.6 tok/s), the same schema without these bounds produced the same 634 tokens and the same
# 10 resolvable claims in 215s (3.0 tok/s). Dropping the schema entirely was faster still but
# yielded 0 resolvable claims, so the structure matters and only the bounds are expensive.
# The bounds are therefore enforced in code after parsing instead: see
# answer_agent.attach_support and verifier_agent.model_pass.
GRAMMAR_BOUNDS = ('maxLength', 'minLength', 'maxItems', 'minItems', 'minimum', 'maximum')


def relax_for_grammar(schema):
    """The same schema with the bounds that make a local GBNF grammar expensive removed."""
    if isinstance(schema, dict):
        return {key: relax_for_grammar(value) for key, value in schema.items()
                if key not in GRAMMAR_BOUNDS}
    if isinstance(schema, list):
        return [relax_for_grammar(value) for value in schema]
    return schema


def obj(properties, required=None):
    return {'type': 'object', 'properties': properties, 'required': list(required or properties),
            'additionalProperties': False}


STRING = {'type': 'string', 'maxLength': 400}
LONG_STRING = {'type': 'string', 'maxLength': 700}

CLAIM = obj({
    'text': LONG_STRING,
    'source_id': {'type': 'integer', 'minimum': 1, 'maximum': 10},
    'span_ids': {'type': 'array', 'items': {'type': 'integer', 'minimum': 1, 'maximum': 24}, 'minItems': 1,
                 'maxItems': 4},
})

SECTION = obj({
    'heading': {'type': 'string', 'maxLength': 90},
    'claims': {'type': 'array', 'minItems': 1, 'maxItems': 4, 'items': CLAIM},
})

SCHEMAS = {
    'language': obj({'standalone': STRING, 'urdu': STRING, 'english': STRING}),
    'router': obj({'intent': {'type': 'string',
                              'enum': ['seerah', 'fiqh_masala', 'hadith', 'history', 'quran_tafsir', 'general',
                                       'unsafe', 'out_of_scope']},
                   'topics': {'type': 'array', 'items': {'type': 'string', 'maxLength': 60}, 'maxItems': 4}}),
    'answer': obj({
        'coverage': {'type': 'string', 'enum': ['full', 'partial', 'none']},
        'sections': {'type': 'array', 'maxItems': settings.answer_max_sections, 'items': SECTION},
        'missing_aspects': {'type': 'array', 'maxItems': 5, 'items': {'type': 'string', 'maxLength': 140}},
    }),
    'verifier': obj({
        'claims': {'type': 'array', 'maxItems': settings.answer_max_claims, 'items': obj({
            'claim_id': {'type': 'integer', 'minimum': 1, 'maximum': settings.answer_max_claims},
            'supported': {'type': 'boolean'},
            'attribution_correct': {'type': 'boolean'},
            'answers_question': {'type': 'boolean'},
            # Kept short on purpose: a full batch of verbose feedback used to overrun the
            # local output budget, truncating the JSON and losing the later verdicts.
            'feedback': {'type': 'string', 'maxLength': 160},
        })},
        'language_correct': {'type': 'boolean'},
    }),
    'repair': obj({
        'claims': {'type': 'array', 'maxItems': settings.repair_max_claims, 'items': obj({
            'claim_id': {'type': 'integer', 'minimum': 1},
            'text': LONG_STRING,
        })},
    }),
    'subtopics': obj({'queries': {'type': 'array', 'maxItems': 4, 'items': {'type': 'string', 'maxLength': 120}}}),
}

# Faithfulness audit of a streamed explanation (app/agents/explain_agent.py). Only the
# problem sentences are returned, so a clean answer costs a handful of output tokens.
SCHEMAS['audit'] = obj({
    'problems': {'type': 'array', 'maxItems': 40, 'items': obj({
        'id': {'type': 'integer', 'minimum': 1},
        'issue': {'type': 'string', 'enum': ['unsupported', 'misattributed', 'overstated', 'contradicted']},
        'fix': {'type': 'string', 'maxLength': 700},
    })},
    # 2026-11-18: citations the auditor proposes for factual sentences that had none.
    # No length/count bounds here: Gemini rejected the bounded version with HTTP 400 "schema produces
    # a constraint that has too many states" (measured 2026-11-18). Bounds are enforced in code
    # (explain_agent.citations_for_uncited: existing source numbers only, at most 4).
    'add_citations': {'type': 'array', 'items': obj({
        'id': {'type': 'integer'},
        'cites': {'type': 'array', 'items': {'type': 'integer'}},
    })},
})
# The strong first-pass audit returns exactly the same structure.
SCHEMAS['audit_strong'] = SCHEMAS['audit']

# Quiz from an answer (app/agents/quiz_agent.py, loop 3, 2026-11-17). Bounds re-checked in code.
SCHEMAS['quiz'] = obj({
    'questions': {'type': 'array', 'maxItems': 6, 'items': obj({
        'question': {'type': 'string', 'maxLength': 300},
        'options': {'type': 'array', 'minItems': 3, 'maxItems': 4, 'items': {'type': 'string', 'maxLength': 200}},
        'correct': {'type': 'integer', 'minimum': 0, 'maximum': 3},
        'statement': {'type': 'integer', 'minimum': 1},
        'explanation': {'type': 'string', 'maxLength': 400},
    })},
})
