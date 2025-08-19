#!/usr/bin/env python3
"""Fix remaining issues in generator_config.py"""

import re

file_path = "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf/generators/generator_config.py"

with open(file_path, "r") as f:
    content = f.read()

# Remove duplicate lines that were introduced
content = re.sub(
    r"    global _generators_cache  # noqa: F824\n    global _generators_cache  # noqa: F824\n",
    "    global _generators_cache  # noqa: F824\n",
    content,
)
content = re.sub(r"    data_to_save = \{\}\n    data_to_save = \{\}\n", "    data_to_save = {}\n", content)
content = re.sub(
    r"    if not _generators_cache:\n    if not _generators_cache:\n", "    if not _generators_cache:\n", content
)
content = re.sub(
    r"    if generator_name not in _generators_cache:\n    if generator_name not in _generators_cache:\n",
    "    if generator_name not in _generators_cache:\n",
    content,
)
content = re.sub(
    r"    gen = _generators_cache\.get\(generator_name\)\n    gen = _generators_cache\.get\(generator_name\)\n",
    "    gen = _generators_cache.get(generator_name)\n",
    content,
)
content = re.sub(
    r"    Returns a list of available Generator type names in the defined order\.\n    Returns a list of available Generator type names in the defined order\.\n",
    "    Returns a list of available Generator type names in the defined order.\n",
    content,
)
content = re.sub(r"    try:\n    try:\n", "    try:\n", content)
content = re.sub(r"        if not name:\n        if not name:\n", "        if not name:\n", content)
content = re.sub(
    r"        return self\.instance\n        return self\.instance\n", "        return self.instance\n", content
)
content = re.sub(
    r'        logger\.debug\(f"Validating parameters for \'\{self\.name\}\'\.\.\."\)\n        logger\.debug\(f"Validating parameters for \'\{self\.name\}\'\.\.\."\)\n',
    "        logger.debug(f\"Validating parameters for '{self.name}'...\")\n",
    content,
)
content = re.sub(
    r'        logger\.info\(f"Attempting to instantiate target for \'\{self\.name\}\' \(Type: \{self\.generator_type\}\)"\)\n        logger\.info\(f"Attempting to instantiate target for \'\{self\.name\}\' \(Type: \{self\.generator_type\}\)"\)\n',
    "        logger.info(f\"Attempting to instantiate target for '{self.name}' (Type: {self.generator_type})\")\n",
    content,
)
content = re.sub(
    r'    logger\.debug\(f"Instance save method called for \'\{self\.name\}\'[^"]*"\)\n    logger\.debug\(f"Instance save method called for \'\{self\.name\}\'[^"]*"\)\n',
    "        logger.debug(f\"Instance save method called for '{self.name}'. Triggering global save.\")\n",
    content,
)
content = re.sub(
    r'    logger\.info\(f"Updating parameters for generator \'\{self\.name\}\'\.\.\."\)\n    logger\.info\(f"Updating parameters for generator \'\{self\.name\}\'\.\.\."\)\n',
    "        logger.info(f\"Updating parameters for generator '{self.name}'...\")\n",
    content,
)
content = re.sub(
    r"    if generator_name not in _generators_cache:\n    if generator_name not in _generators_cache:\n",
    "    if generator_name not in _generators_cache:\n",
    content,
)
content = re.sub(
    r"    if not response_request[^:]+:\n    if not response_request[^:]+:\n",
    "    if not response_request or not response_request.request_pieces or len(response_request.request_pieces) <= 1:\n",
    content,
)
content = re.sub(r"    if success:\n    if success:\n", "    if success:\n", content)

# Fix multiple statements on single lines
content = re.sub(
    r'        return False, "Test failed\. Invalid or empty response structure received from target\."     assistant_response_piece = response_request\.request_pieces\[-1\]',
    '        return False, "Test failed. Invalid or empty response structure received from target."\n    assistant_response_piece = response_request.request_pieces[-1]',
    content,
)
content = re.sub(
    r'    if assistant_response_piece\.role != "assistant": return False,[^\n]+',
    '    if assistant_response_piece.role != "assistant":\n        return False, f"Test failed. Expected assistant role in response, got \'{assistant_response_piece.role}\'."',
    content,
)
content = re.sub(
    r'    if assistant_response_piece\.response_error == "none" and assistant_response_piece\.converted_value: message = [^\n]+ return True, message',
    """    if assistant_response_piece.response_error == "none" and assistant_response_piece.converted_value:
        message = f"Test successful. Received response snippet: {assistant_response_piece.converted_value[:100]}..."
        logger.debug(f"Full test response for '{generator_name}': {assistant_response_piece.converted_value}")
        return True, message""",
    content,
)
content = re.sub(
    r'    elif assistant_response_piece\.response_error and assistant_response_piece\.response_error != "none": return False,[^\n]+ elif not assistant_response_piece\.converted_value:',
    """    elif assistant_response_piece.response_error and assistant_response_piece.response_error != "none":
        return False, f"Test failed. API returned error: {assistant_response_piece.response_error}. Details: {assistant_response_piece.original_value}"
    elif not assistant_response_piece.converted_value:""",
    content,
)
content = re.sub(
    r'        return False, "Test failed\. Received an empty or invalid response content from assistant \(error=\'none\'\)\." else:',
    """        return False, "Test failed. Received an empty or invalid response content from assistant (error='none')."
    else:""",
    content,
)
content = re.sub(
    r'        return False, "Test failed\. Unknown response state\." \n',
    '        return False, "Test failed. Unknown response state."\n\n',
    content,
)
content = re.sub(
    r'        logger\.info\(f"Test result for \'\{generator_name\}\': PASSED\. Message: \{message\}"\) else:',
    """        logger.info(f"Test result for '{generator_name}': PASSED. Message: {message}")
    else:""",
    content,
)

# Fix if generator_type == "HTTP REST" line
content = re.sub(
    r'    if generator_type == "HTTP REST" and "HTTP REST" not in GENERATOR_PARAMS and "HTTPTarget" in GENERATOR_PARAMS:\n    if generator_type == "HTTP REST"[^\n]+\n',
    '    if generator_type == "HTTP REST" and "HTTP REST" not in GENERATOR_PARAMS and "HTTPTarget" in GENERATOR_PARAMS:\n',
    content,
)

with open(file_path, "w") as f:
    f.write(content)

print(f"Fixed issues in {file_path}")
