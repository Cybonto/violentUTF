#!/usr/bin/env python3
"""Fix syntax errors in scorer_integration_service.py"""

import re

# Read the file
file_path = (
    "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app/app/services/scorer_integration_service.py"
)
with open(file_path, "r") as f:
    content = f.read()

# Fix patterns where }, } appears at end of line
content = re.sub(r'", }\s+}(\s+else:)', r'",\n            }\n        }\1', content)
content = re.sub(r'", }\s+}(\s+except)', r'",\n            }\n    }\1', content)
content = re.sub(r'", }(\s+#)', r'",\n            }\n        #', content)
content = re.sub(r'", }$', r'",\n        }', content, flags=re.MULTILINE)

# Fix malformed docstrings and multi-statement lines
# Lines 260-262
old_260 = r"def _execute_self_ask_likert_scorer\(parameters: Dict, text: str, scorer_config: Dict\) -> Dict\[str, Any\]:\s*\\\"\\\"\\\"Execute SelfAskLikertScorer with question-based evaluation.\\\"\\\"\\\" question = parameters\.get\(\\\"likert_scale_question\\\", \\\"How helpful is this response\?\\\"\) scale_min = parameters\.get\(\\\"scale_min\\\", 1\) scale_max = parameters\.get\(\\\"scale_max\\\", 5\) text_lower = text\.lower\(\)\s+# Use dispatch pattern for different question types\s*if \\\"helpful\\\" in question\.lower\(\): score_value, rationale = _evaluate_helpfulness_question\(text_lower, scale_min, scale_max, question\) elif \\\"quality\\\" in question\.lower\(\): score_value, rationale = _evaluate_quality_question\(text_lower, scale_min, scale_max, question\)"

new_260 = '''def _execute_self_ask_likert_scorer(parameters: Dict, text: str, scorer_config: Dict) -> Dict[str, Any]:
    """Execute SelfAskLikertScorer with question-based evaluation."""
    question = parameters.get("likert_scale_question", "How helpful is this response?")
    scale_min = parameters.get("scale_min", 1)
    scale_max = parameters.get("scale_max", 5)
    text_lower = text.lower()

    # Use dispatch pattern for different question types
    if "helpful" in question.lower():
        score_value, rationale = _evaluate_helpfulness_question(text_lower, scale_min, scale_max, question)
    elif "quality" in question.lower():
        score_value, rationale = _evaluate_quality_question(text_lower, scale_min, scale_max, question)'''

content = re.sub(old_260, new_260, content)

# Fix lines 269-270
old_269 = r"return {\s*\\\"score_value\\\": round\(normalized_score, 3\), \\\"score_value_description\\\": f\\\"Likert scale evaluation \({scale_min}-{scale_max}\) normalized to 0-1 for: {question}\\\", \\\"score_type\\\": \\\"float_scale\\\", \\\"score_category\\\": \\\"self_ask_evaluation\\\", \\\"score_rationale\\\": f\\\"{rationale} \(Original: {score_value}, Normalized: {normalized_score:\.3f}\)\\\", \\\"score_metadata\\\": f\'{{\\\"question\\\": \\\"{question}\\\", \\\"scale_min\\\": {scale_min}, \\\"scale_max\\\": {scale_max}, \\\"original_score\\\": {score_value}, \\\"scorer_name\\\": \\\"{scorer_config\.get\(\\\"name\\\", \\\"Unknown\\\"\)}\\\", \\\"scorer_type\\\": \\\"SelfAskLikertScorer\\\"}}\', }"

new_269 = """return {
        "score_value": round(normalized_score, 3),
        "score_value_description": f"Likert scale evaluation ({scale_min}-{scale_max}) normalized to 0-1 for: {question}",
        "score_type": "float_scale",
        "score_category": "self_ask_evaluation",
        "score_rationale": f"{rationale} (Original: {score_value}, Normalized: {normalized_score:.3f})",
        "score_metadata": f'{{"question": "{question}", "scale_min": {scale_min}, "scale_max": {scale_max}, "original_score": {score_value}, "scorer_name": "{scorer_config.get("name", "Unknown")}", "scorer_type": "SelfAskLikertScorer"}}',
    }"""

content = re.sub(old_269, new_269, content, flags=re.DOTALL)

# Fix lines 271-272
old_271 = r"def _execute_generic_likert_scorer\(text: str, scorer_config: Dict\) -> Dict\[str, Any\]:\s*\\\"\\\"\\\"Execute generic Likert scorer based on text length.\\\"\\\"\\\" text_length = len\(text\)\s+# Return normalized 0-1 score for PyRIT compatibility"

new_271 = '''
def _execute_generic_likert_scorer(text: str, scorer_config: Dict) -> Dict[str, Any]:
    """Execute generic Likert scorer based on text length."""
    text_length = len(text)

    # Return normalized 0-1 score for PyRIT compatibility'''

content = re.sub(old_271, new_271, content)

# Fix lines 285
old_285 = r"return {\s*\\\"score_value\\\": score_value, \\\"score_value_description\\\": \\\"Likert scale score \(0-1\) based on response length\\\", \\\"score_type\\\": \\\"float_scale\\\", \\\"score_category\\\": scorer_config\.get\(\\\"category\\\", \\\"general\\\"\), \\\"score_rationale\\\": f\\\"Score based on text length: {text_length} characters \(normalized to 0-1 scale\)\\\", \\\"score_metadata\\\": f\'{{\\\"text_length\\\": {text_length}, \\\"scale\\\": \\\"0-1\\\", \\\"scorer_name\\\": \\\"{scorer_config\.get\(\\\"name\\\", \\\"Unknown\\\"\)}\\\"}}\'*, }"

new_285 = """return {
        "score_value": score_value,
        "score_value_description": "Likert scale score (0-1) based on response length",
        "score_type": "float_scale",
        "score_category": scorer_config.get("category", "general"),
        "score_rationale": f"Score based on text length: {text_length} characters (normalized to 0-1 scale)",
        "score_metadata": f'{{"text_length": {text_length}, "scale": "0-1", "scorer_name": "{scorer_config.get("name", "Unknown")}"}}',
    }"""

content = re.sub(old_285, new_285, content, flags=re.DOTALL)

# Fix other helper functions
# Lines 286-287
old_286 = r"def _evaluate_helpfulness_question\(text_lower: str, scale_min: int, scale_max: int, question: str\) -> tuple:\s*\\\"\\\"\\\"Evaluate helpfulness indicators in text.\\\"\\\"\\\" helpful_indicators = \[\\\"helpful\\\", \\\"useful\\\", \\\"informative\\\", \\\"clear\\\", \\\"explain\\\", \\\"answer\\\", \\\"solution\\\", \\\"understand\\\"\] unhelpful_indicators = \[\\\"unclear\\\", \\\"confusing\\\", \\\"wrong\\\", \\\"incorrect\\\", \\\"unhelpful\\\", \\\"useless\\\"\]\s+helpful_count = sum\(1 for indicator in helpful_indicators if indicator in text_lower\) unhelpful_count = sum\(1 for indicator in unhelpful_indicators if indicator in text_lower\)"

new_286 = '''
def _evaluate_helpfulness_question(text_lower: str, scale_min: int, scale_max: int, question: str) -> tuple:
    """Evaluate helpfulness indicators in text."""
    helpful_indicators = ["helpful", "useful", "informative", "clear", "explain", "answer", "solution", "understand"]
    unhelpful_indicators = ["unclear", "confusing", "wrong", "incorrect", "unhelpful", "useless"]

    helpful_count = sum(1 for indicator in helpful_indicators if indicator in text_lower)
    unhelpful_count = sum(1 for indicator in unhelpful_indicators if indicator in text_lower)'''

content = re.sub(old_286, new_286, content)

# Line 296
old_296 = r"rationale = f\\\"Helpfulness score: {helpful_count} positive vs {unhelpful_count} negative indicators for question: {question}\\\" return score_value, rationale"
new_296 = """rationale = f"Helpfulness score: {helpful_count} positive vs {unhelpful_count} negative indicators for question: {question}"
    return score_value, rationale"""
content = re.sub(old_296, new_296, content)

# Lines 297-298
old_297 = r"def _evaluate_quality_question\(text_lower: str, scale_min: int, scale_max: int, question: str\) -> tuple:\s*\\\"\\\"\\\"Evaluate quality indicators in text.\\\"\\\"\\\" quality_indicators = \[\\\"excellent\\\", \\\"good\\\", \\\"well\\\", \\\"thorough\\\", \\\"detailed\\\", \\\"accurate\\\"\] poor_indicators = \[\\\"poor\\\", \\\"bad\\\", \\\"terrible\\\", \\\"incomplete\\\", \\\"wrong\\\", \\\"inaccurate\\\"\]\s+quality_count = sum\(1 for indicator in quality_indicators if indicator in text_lower\) poor_count = sum\(1 for indicator in poor_indicators if indicator in text_lower\)"

new_297 = '''
def _evaluate_quality_question(text_lower: str, scale_min: int, scale_max: int, question: str) -> tuple:
    """Evaluate quality indicators in text."""
    quality_indicators = ["excellent", "good", "well", "thorough", "detailed", "accurate"]
    poor_indicators = ["poor", "bad", "terrible", "incomplete", "wrong", "inaccurate"]

    quality_count = sum(1 for indicator in quality_indicators if indicator in text_lower)
    poor_count = sum(1 for indicator in poor_indicators if indicator in text_lower)'''

content = re.sub(old_297, new_297, content)

# Line 307
old_307 = r"rationale = f\\\"Quality score: {quality_count} positive vs {poor_count} negative indicators for question: {question}\\\" return score_value, rationale"
new_307 = """rationale = f"Quality score: {quality_count} positive vs {poor_count} negative indicators for question: {question}"
    return score_value, rationale"""
content = re.sub(old_307, new_307, content)

# Lines 308-309
old_308 = r"def _evaluate_generic_question\(text: str, scale_min: int, scale_max: int, question: str\) -> tuple:\s*\\\"\\\"\\\"Evaluate generic question based on text length.\\\"\\\"\\\" text_length = len\(text\) word_count = len\(text\.split\(\)\)"

new_308 = '''
def _evaluate_generic_question(text: str, scale_min: int, scale_max: int, question: str) -> tuple:
    """Evaluate generic question based on text length."""
    text_length = len(text)
    word_count = len(text.split())'''

content = re.sub(old_308, new_308, content)

# Line 322
old_322 = r"rationale = f\\\"Length-based score: {text_length} characters, {word_count} words \(scale: {scale_min}-{scale_max}\) for question: {question}\\\" return score_value, rationale"
new_322 = """rationale = f"Length-based score: {text_length} characters, {word_count} words (scale: {scale_min}-{scale_max}) for question: {question}"
    return score_value, rationale"""
content = re.sub(old_322, new_322, content)

# Lines 323-324
old_323 = r"def _create_likert_error_response\(e: Exception, scorer_config: Dict\) -> Dict\[str, Any\]:\s*\\\"\\\"\\\"Create error response for Likert scorer.\\\"\\\"\\\" return { \\\"score_value\\\": 0\.5, \\\"score_value_description\\\": \\\"Error occurred during scoring\\\", \\\"score_type\\\": \\\"float_scale\\\", \\\"score_category\\\": \\\"error\\\", \\\"score_rationale\\\": f\\\"Scoring failed: {str\(e\)}\\\", \\\"score_metadata\\\": f\'{{\\\"error\\\": \\\"{str\(e\)}\\\", \\\"scorer_name\\\": \\\"{scorer_config\.get\(\\\"name\\\", \\\"Unknown\\\"\)}\\\"}}\'*, }"

new_323 = '''
def _create_likert_error_response(e: Exception, scorer_config: Dict) -> Dict[str, Any]:
    """Create error response for Likert scorer."""
    return {
        "score_value": 0.5,
        "score_value_description": "Error occurred during scoring",
        "score_type": "float_scale",
        "score_category": "error",
        "score_rationale": f"Scoring failed: {str(e)}",
        "score_metadata": f'{{"error": "{str(e)}", "scorer_name": "{scorer_config.get("name", "Unknown")}"}}',
    }'''

content = re.sub(old_323, new_323, content, flags=re.DOTALL)

# Write back the fixed content
with open(file_path, "w") as f:
    f.write(content)

print("Fixed syntax errors in scorer_integration_service.py")
