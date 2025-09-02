# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# converters/converter_config.py

"""Module: Converter Configuration

Contains functions for loading available converter classes,
retrieving converter categories, parameters, and instantiating converters.

Key Functions:
- list_available_converters(): Returns a list of available converter names.
- get_converter_params(converter_name): Returns the parameters required by a converter.
- instantiate_converter(converter_name, parameters): Instantiates a converter with given parameters.


Dependencies:
- pyrit.prompt_converter
- logging
- inspect
- utils.error_handling
- utils.logging
"""
import collections.abc  # To check for Callable
import inspect
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Type,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from pyrit.models import SeedPrompt  # If needed
from pyrit.prompt_converter import PromptConverter
from pyrit.prompt_target import PromptChatTarget  # Needed for some converters
from utils.error_handling import ConverterLoadingError
from utils.logging import get_logger

logger = get_logger(__name__)


# Build AVAILABLE_CONVERTERS directly


def _get_available_converters() -> Dict[str, Type[Any]]:
    """Build AVAILABLE_CONVERTERS dict from imported converter classes.

    Returns:
        Dict[str, Type[PromptConverter]]: Available converters mapping converter names to classes.

    Raises:
        ConverterLoadingError: If unable to load converters.
    """
    try:

        # Get all converter classes from globals()
        converter_classes = {
            name: cls
            for name, cls in globals().items()
            if inspect.isclass(cls) and issubclass(cls, PromptConverter) and cls is not PromptConverter
        }

        logger.info("Loaded %s converters.", len(converter_classes))
        return converter_classes
    except Exception as e:
        logger.error("Error loading available converters: %s", e)
        raise ConverterLoadingError(f"Error loading converters: {e}") from e


# AVAILABLE_CONVERTERS is built at module load time
AVAILABLE_CONVERTERS = _get_available_converters()


def list_available_converters() -> List[str]:
    """Return a list of available converter names.

    Returns:
        converters_list (list): A list of converter class names.
    """
    converters_list = list(AVAILABLE_CONVERTERS.keys())

    logger.debug("Available converters: %s", converters_list)
    return converters_list


def get_converter_params(converter_name: str) -> List[Dict[str, object]]:
    """Return detailed parameters required by the specified converter, including type information.

    Parameters:
        converter_name (str): Name of the converter class.

    Returns:
        params_list (list): A list of parameter definitions, each as a dict with keys like
                            'name', 'type', 'raw_type', 'required', 'default', 'description',
                            'literal_choices'.

    Raises:
        ConverterLoadingError: If converter is not found or parameters cannot be retrieved.
    """
    try:

        converter_class = AVAILABLE_CONVERTERS.get(converter_name)
        if not converter_class:
            logger.error(f"Converter '{converter_name}' not found.")
            raise ConverterLoadingError(f"Converter '{converter_name}' not found.")

        init_method = converter_class.__init__
        init_signature = inspect.signature(init_method)
        # Use get_type_hints for more reliable type info, including forward references
        try:
            # Use include_extras=True if available and needed for Annotated types, requires Python 3.9+
            # type_hints = get_type_hints(init_method, include_extras=True)
            type_hints = get_type_hints(init_method)
        except (AttributeError, TypeError, NameError, ValueError) as e:
            logger.warning(
                "Could not get type hints for %s.__init__: %s. Falling back.",
                converter_name,
                e,
            )
            type_hints = {}

        params_list = []
        for param_name, param in init_signature.parameters.items():
            # Skip 'self' and variable args/kwargs
            if param_name == "self" or param.kind in [
                param.VAR_POSITIONAL,
                param.VAR_KEYWORD,
            ]:
                continue

            # Get type hint, default to Any if not found
            raw_annotation = type_hints.get(param_name, Any)
            origin_type = get_origin(raw_annotation)
            type_args = get_args(raw_annotation)

            # --- Determine Primary Type and Literal Choices ---
            primary_type = raw_annotation
            literal_choices = None
            type_str = str(raw_annotation).replace("typing.", "")  # Default string representation

            if origin_type is Literal:  # Handle Literal
                literal_choices = list(type_args)
                # Infer primary type from the first literal choice if possible
                if literal_choices:
                    primary_type = type(literal_choices[0])
                    type_str = f"Literal[{', '.join(map(repr, literal_choices))}]"
                else:
                    primary_type = Any  # Empty Literal?
                    type_str = "Literal[]"

            elif origin_type is Union:  # Handle Union and Optional (Optional[X] is Union[X, NoneType])
                non_none_types = [t for t in type_args if t is not type(None)]
                if len(non_none_types) == 1:
                    primary_type = non_none_types[0]
                    # Check if the inner type is Literal
                    inner_origin = get_origin(primary_type)
                    inner_args = get_args(primary_type)
                    if inner_origin is Literal:
                        literal_choices = list(inner_args)
                        if literal_choices:
                            # Type string for Optional[Literal[...]]
                            type_str = f"Optional[Literal[{', '.join(map(repr, literal_choices))}]]"
                            # Update primary_type based on literal values
                            primary_type = type(literal_choices[0])
                        else:
                            type_str = "Optional[Literal[]]"
                            primary_type = Any
                    else:
                        # Regular Optional[Type]
                        type_str = f"Optional[{str(primary_type).replace('typing.', '')}]"

                else:
                    # Handle complex Unions if necessary, for now just represent as string
                    primary_type = Union  # Represent the Union itself
                    type_str = str(raw_annotation).replace("typing.", "")

            elif origin_type is list or origin_type is collections.abc.Sequence:
                primary_type = list
                if type_args:
                    type_str = f"list[{str(type_args[0]).replace('typing.', '')}]"
                else:
                    type_str = "list"
            elif origin_type is tuple or origin_type is collections.abc.Sequence:  # Handle Tuple
                primary_type = tuple
                if type_args:
                    # Handle Tuple[int, int, int] vs Tuple[str, ...]
                    if len(type_args) > 1 and type_args[1] == Ellipsis:
                        type_str = f"tuple[{str(type_args[0]).replace('typing.', '')}, ...]"
                    else:
                        type_str = f"tuple[{', '.join(str(t).replace('typing.', '') for t in type_args)}]"
                else:
                    type_str = "tuple"
            elif origin_type is dict:
                primary_type = dict
                if type_args and len(type_args) == 2:
                    type_str = (
                        f"dict[{str(type_args[0]).replace('typing.', '')}, {str(type_args[1]).replace('typing.', '')}]"
                    )
                else:
                    type_str = "dict"

            # --- Determine if parameter should be skipped in simple UI ---
            # Skip complex types that need special handling outside the generic UI loop
            skip_in_ui = False
            if (
                primary_type is PromptChatTarget
                or primary_type is SeedPrompt
                or isinstance(primary_type, type)
                and issubclass(primary_type, PromptConverter)
                or primary_type is list
                and type_args
                and issubclass(type_args[0], PromptConverter)
                or primary_type is collections.abc.Callable
            ):  # Check if it's Callable
                skip_in_ui = True

            # --- Get Default Value ---
            default_value = None if param.default == param.empty else param.default

            # --- Special handling for specific parameters ---
            description = param_name.replace("_", " ").capitalize()  # Default description

            # Special handling for append_description parameter
            if param_name == "append_description":
                # Override default to True for better UX
                default_value = True
                # Provide detailed description with context
                description = "Append description (adds cipher explanation and instructions for AI responses)"

            # Special handling for RepeatTokenConverter parameters
            elif param_name == "token_to_repeat":
                # Provide default value to prevent None error
                if default_value is None:
                    default_value = "REPEAT"
                description = "Token to repeat (text to duplicate in prompt)"
            elif param_name == "times_to_repeat":
                # Provide default value to prevent None error
                if default_value is None:
                    default_value = 2
                description = "Times to repeat (number of repetitions)"

            # Special handling for encrypt_type parameter (CodeChameleonConverter)
            elif param_name == "encrypt_type":
                description = "Encryption type (choose: custom, reverse, binary_tree, odd_even, length)"

            param_info = {
                "name": param_name,
                "type_str": type_str,  # String representation for display
                "raw_type": raw_annotation,  # The actual annotation
                "primary_type": primary_type,  # Simplified primary type (int, str, list, tuple, Literal, etc.)
                "literal_choices": literal_choices,  # List of choices if Literal
                "required": param.default == param.empty,
                "default": default_value,
                "skip_in_ui": skip_in_ui,  # Flag to skip in generic UI generation
                "description": description,
            }
            params_list.append(param_info)

        logger.debug(f"Parameters for converter '{converter_name}': {params_list}")
        return params_list

    except Exception as e:
        logger.error(
            f"Error retrieving parameters for converter '{converter_name}': {e}",
            exc_info=True,
        )
        raise ConverterLoadingError(f"Error retrieving parameters for converter '{converter_name}': {e}") from e


def instantiate_converter(converter_name: str, parameters: Dict[str, object]) -> PromptConverter:
    """Instantiate a converter with the specified parameters.

    Assumes parameters are already correctly typed and complex objects are included.
    Handles zero-argument constructors robustly.

    Parameters:
        converter_name (str): Name of the converter class.
        parameters (dict): Dictionary of parameter values (should include basic types
                           correctly converted AND any required complex objects like
                           PromptChatTarget or SeedPrompt, injected by the caller).

    Returns:
        converter_instance (PromptConverter): An instance of the converter.

    Raises:
        ConverterLoadingError: If instantiation fails.
    """
    try:
        converter_class = AVAILABLE_CONVERTERS.get(converter_name)
        if not converter_class:
            logger.error(f"Converter '{converter_name}' not found.")
            raise ConverterLoadingError(f"Converter '{converter_name}' not found.")

        # Get the expected __init__ parameters' signature
        try:
            converter_init_params = inspect.signature(converter_class.__init__).parameters
        except ValueError as e:
            logger.error("Could not get signature for %s.__init__: %s", converter_name, e)
            raise ConverterLoadingError(f"Could not determine signature for {converter_name}") from e
        except TypeError as e:
            # Handle potential issues with C-implemented __init__ or other edge cases
            logger.error(
                "TypeError getting signature for %s.__init__: %s. Assuming no named params.",
                converter_name,
                e,
            )
            converter_init_params = {}  # type: ignore # Fallback: assume no named parameters inspectable

        # --- Updated Filtering ---
        # Determine the names of *NAMED* parameters, explicitly excluding self, *args, **kwargs
        # by checking both name and parameter kind.
        init_param_names = []
        for pname, p in converter_init_params.items():
            if pname == "self":
                continue
            if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD or p.kind == inspect.Parameter.KEYWORD_ONLY:
                init_param_names.append(pname)
            # else: parameter is VAR_POSITIONAL (*args), VAR_KEYWORD (**kwargs),
            # or POSITIONAL_ONLY (less common here) - ignore these

        logger.debug(
            "Found named __init__ param names for %s: %s",
            converter_name,
            init_param_names,
        )

        # --- Handle Converters with No Named Arguments ---
        # This block now correctly triggers if __init__ only has self, *args, **kwargs, or is empty.
        if not init_param_names:
            if parameters:
                logger.warning(
                    f"Converter '{converter_name}' takes no named arguments, but received parameters: {parameters}. "
                    "These parameters will be ignored during instantiation."
                )
            # Instantiate with no arguments. This works even if the actual __init__ takes *args/**kwargs.
            converter_instance = converter_class()
            logger.info(f"Converter '{converter_name}' instantiated (takes no named arguments).")
        else:
            # --- Logic for Converters WITH Named Arguments ---

            # Filter the provided parameters to only include the identified named parameters.
            filtered_params = {k: v for k, v in parameters.items() if k in init_param_names}

            # Check if all *required* named parameters (those without defaults) are present.
            required_param_names = {
                p.name
                for p in converter_init_params.values()
                # Check only parameters that are in our named list and are required
                if p.name in init_param_names and p.default == inspect.Parameter.empty
            }

            missing_required = required_param_names - set(filtered_params.keys())

            # (Keep the logic for checking if missing parameters allow None)
            truly_missing = set()
            try:
                # Use global_ns/local_ns if needed for resolving forward references in type hints
                init_type_hints = get_type_hints(converter_class.__init__)
            except (AttributeError, TypeError, NameError, ValueError) as e:
                logger.warning(
                    f"Could not reliably get type hints for {converter_name}.__init__ during missing param check: {e}"
                )
                init_type_hints = {}  # Fallback

            for missing_name in missing_required:
                param_type_hint = init_type_hints.get(missing_name, Any)
                origin = get_origin(param_type_hint)
                args = get_args(param_type_hint)
                # Check if the type hint is Optional[T] or Union[T, None]
                allows_none = origin is Union and type(None) in args
                if not allows_none:
                    truly_missing.add(missing_name)

            if truly_missing:
                logger.error(
                    f"Missing required non-nullable named parameters for {converter_name}: {truly_missing}. "
                    f"Provided params: {filtered_params}"
                )
                raise ConverterLoadingError(f"Missing required parameters for {converter_name}: {truly_missing}")

            # Instantiate with the filtered named parameters
            logger.debug(
                "Attempting to instantiate %s with filtered named params: %s",
                converter_name,
                filtered_params,
            )
            converter_instance = converter_class(**filtered_params)
            logger.info(f"Converter '{converter_name}' instantiated with parameters: {filtered_params}")

        return converter_instance

    except TypeError as te:
        # Catch TypeErrors which often happen with wrong argument types/counts during **filtered_params call
        logger.error(
            f"TypeError during instantiation of '{converter_name}' with params {parameters}: {te}",
            exc_info=True,
        )
        raise ConverterLoadingError(
            f"TypeError instantiating converter '{converter_name}': {te}. Check parameter types/counts."
        ) from te
    except Exception as e:
        logger.error(
            f"Unexpected error instantiating converter '{converter_name}' with params {parameters}: {e}",
            exc_info=True,
        )
        raise ConverterLoadingError(f"Error instantiating converter '{converter_name}': {e}") from e


def get_converter_categories() -> Dict[str, List[str]]:
    """Return a dictionary of converter categories mapped to converter names.

    Returns:
        categories_dict (dict): A dictionary where keys are category names and values are lists of converter names.
    """
    # Categories mapping

    categories = {
        "Encoding": [
            "Base64Converter",
            "ROT13Converter",
            "AtbashConverter",
            "CaesarConverter",
        ],
        "Transformation": [
            "AsciiArtConverter",
            "FlipConverter",
            "LeetspeakConverter",
            "StringJoinConverter",
            "RandomCapitalLettersConverter",
            "RepeatTokenConverter",
            "SuffixAppendConverter",
        ],
        "Multimedia": [
            "AddImageTextConverter",
            "AddTextImageConverter",
            "AudioFrequencyConverter",
            "QRCodeConverter",
        ],
        "Language": ["TranslationConverter", "ToneConverter", "TenseConverter"],
        "Obfuscation": [
            "UnicodeConfusableConverter",
            "UnicodeSubstitutionConverter",
            "MorseConverter",
            "EmojiConverter",
            "UrlConverter",
            "CodeChameleonConverter",
            "CharacterSpaceConverter",
        ],
        "LLM-Based": [
            "LLMGenericTextConverter",
            "MaliciousQuestionGeneratorConverter",
            "MathPromptConverter",
            "PersuasionConverter",
            "NoiseConverter",
            "VariationConverter",
            "FuzzerCrossOverConverter",
            "FuzzerExpandConverter",
            "FuzzerRephraseConverter",
            "FuzzerShortenConverter",
            "FuzzerSimilarConverter",
        ],
        "Human Interaction": ["HumanInTheLoopConverter"],
        "Azure Services": [
            "AzureSpeechAudioToTextConverter",
            "AzureSpeechTextToAudioConverter",
        ],
        # Add more categories and mappings as needed
    }
    logger.debug("Converter categories: %s", categories)
    return categories
