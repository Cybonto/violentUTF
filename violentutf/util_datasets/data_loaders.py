# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

# datasets/data_loaders.py

"""
Module: Data Loaders.

Contains functions for loading datasets from various sources.

Key Functions:
- get_pyrit_datasets(): Retrieves a list of PyRIT native datasets.
- get_garak_probes(): Retrieves a list of Garak's probes.
- load_dataset(dataset_name, config): Loads a dataset based on the name and configuration.
- parse_local_dataset_file(uploaded_file): Parses an uploaded local dataset file.
- fetch_online_dataset(url): Downloads and parses a dataset from an online source.
- map_dataset_fields(dataframe, mappings): Maps dataset fields to SeedPrompt attributes.
- create_seed_prompt_dataset(prompts): Creates a SeedPromptDataset from a list of SeedPrompts.

Dependencies:
- pyrit.datasets
- pyrit.models (SeedPrompt, SeedPromptDataset)
- pandas
- PyYAML
- requests
- utils.error_handling
- utils.logging
"""

import asyncio
import json
import logging
import os
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
import requests
import yaml
from pyrit.datasets import (  # Add other datasets as needed
    fetch_adv_bench_dataset,
    fetch_aya_redteaming_dataset,
    fetch_decoding_trust_stereotypes_dataset,
    fetch_forbidden_questions_dataset,
    fetch_harmbench_dataset,
    fetch_many_shot_jailbreaking_dataset,
    fetch_pku_safe_rlhf_dataset,
    fetch_seclists_bias_testing_dataset,
    fetch_wmdp_dataset,
    fetch_xstest_dataset,
)
from pyrit.models import SeedPrompt, SeedPromptDataset
from utils.error_handling import DatasetLoadingError, DatasetParsingError
from utils.logging import get_logger

logger = get_logger(__name__)

# Mapping of dataset names to their corresponding fetch functions
PYRIT_DATASETS = {
    "decoding_trust_stereotypes": fetch_decoding_trust_stereotypes_dataset,
    "harmbench": fetch_harmbench_dataset,
    # 'many_shot_jailbreaking': fetch_many_shot_jailbreaking_dataset,
    "adv_bench": fetch_adv_bench_dataset,
    "aya_redteaming": fetch_aya_redteaming_dataset,
    "seclists_bias_testing": fetch_seclists_bias_testing_dataset,
    "xstest": fetch_xstest_dataset,
    # 'pku_safe_rlhf': fetch_pku_safe_rlhf_dataset,
    # 'wmdp': fetch_wmdp_dataset,
    "forbidden_questions": fetch_forbidden_questions_dataset,
    # Add other datasets as needed
}


def get_pyrit_datasets() -> List[str]:
    """
    Retrieves a list of natively supported datasets for PyRIT.

    Parameters:
        None

    Returns:
        datasets_list (list): A list of dataset names supported by PyRIT.

    Raises:
        None

    Upstream functions:
        - display_native_datasets() in 'pages/3_ConfigureDatasets.py'

    Downstream functions:
        None

    Dependencies:
        - PYRIT_DATASETS (dict)
    """
    datasets_list = list(PYRIT_DATASETS.keys())
    logger.debug(f"Retrieved PyRIT datasets: {datasets_list}")
    return datasets_list


def get_garak_probes() -> List[str]:
    """
    Retrieves a list of natively supported probes for Garak.

    Parameters:
        None

    Returns:
        probes_list (list): A list of probe names or identifiers supported by Garak.

    Raises:
        NotImplementedError: If Garak integration is not yet implemented.

    Upstream functions:
        - display_native_datasets() in 'pages/3_ConfigureDatasets.py'

    Downstream functions:
        None

    Dependencies:
        - garak (when implemented)
    """
    logger.warning("get_garak_probes() is not yet implemented.")
    raise NotImplementedError("get_garak_probes() is not implemented yet.")


def load_dataset(dataset_name: str, config: Dict[str, Any]) -> Optional[SeedPromptDataset]:
    """
    Loads a dataset by name and returns a SeedPromptDataset object.

    Parameters:
        dataset_name (str): The name or identifier of the dataset to load.
        config (dict): Configuration parameters for dataset loading.

    Returns:
        dataset (SeedPromptDataset): The loaded dataset object, or None if loading fails.

    Raises:
        DatasetLoadingError: If loading the dataset fails.

    Upstream functions:
        - load_dataset() in 'pages/3_ConfigureDatasets.py'

    Downstream functions:
        None

    Dependencies:
        - PYRIT_DATASETS
        - utils.error_handling
    """
    try:
        if dataset_name in PYRIT_DATASETS:
            fetch_function = PYRIT_DATASETS[dataset_name]
            # Remove None values from config
            config = {k: v for k, v in config.items() if v is not None}
            logger.info(f"Loading dataset '{dataset_name}' with config: {config}")
            dataset = fetch_function(**config)
            if dataset:
                logger.info(f"Dataset '{dataset_name}' loaded successfully.")
                return dataset
            else:
                logger.error(f"Dataset '{dataset_name}' returned None.")
                raise DatasetLoadingError(f"Dataset '{dataset_name}' returned None.")
        else:
            logger.error(f"Dataset '{dataset_name}' not found in available datasets.")
            raise DatasetLoadingError(f"Dataset '{dataset_name}' is not supported.")
    except Exception as e:
        logger.exception(f"Error loading dataset '{dataset_name}': {e}")
        raise DatasetLoadingError(f"Error loading dataset '{dataset_name}': {e}") from e


def parse_local_dataset_file(uploaded_file) -> pd.DataFrame:
    """
    Parses an uploaded local dataset file in various formats.

    Parameters:
        uploaded_file (UploadedFile): The uploaded file object from Streamlit.

    Returns:
        dataframe (pandas.DataFrame): Parsed data as a DataFrame.

    Raises:
        DatasetParsingError: If the file format is unsupported or the content is invalid.

    Upstream functions:
        - flow_upload_local_dataset() in 'pages/3_ConfigureDatasets.py'

    Downstream functions:
        - map_dataset_fields()

    Dependencies:
        - pandas
        - utils.error_handling
    """
    try:
        file_extension = Path(uploaded_file.name).suffix.lower()
        content = uploaded_file.read()
        logger.info(f"Parsing uploaded file '{uploaded_file.name}' with extension '{file_extension}'")
        if file_extension in [".csv", ".tsv"]:
            delimiter = "," if file_extension == ".csv" else "\t"
            dataframe = pd.read_csv(StringIO(content.decode("utf-8")), delimiter=delimiter)
        elif file_extension in [".json", ".jsonl"]:
            lines = content.decode("utf-8").splitlines()
            if len(lines) == 1:
                json_data = json.loads(lines[0])
            else:
                json_data = [json.loads(line) for line in lines]
            dataframe = pd.json_normalize(json_data)
        elif file_extension in [".yaml", ".yml"]:
            yaml_data = yaml.safe_load(content.decode("utf-8"))
            dataframe = pd.json_normalize(yaml_data)
        elif file_extension in [".txt"]:
            text = content.decode("utf-8")
            lines = text.strip().split("\n")
            dataframe = pd.DataFrame(lines, columns=["text"])
        else:
            logger.error(f"Unsupported file type: '{file_extension}'")
            raise DatasetParsingError(f"Unsupported file type: '{file_extension}'")
        logger.info(f"Uploaded file '{uploaded_file.name}' parsed successfully.")
        return dataframe
    except Exception as e:
        logger.exception(f"Error parsing uploaded file '{uploaded_file.name}': {e}")
        raise DatasetParsingError(f"Error parsing uploaded file '{uploaded_file.name}': {e}") from e


def fetch_online_dataset(url: str) -> pd.DataFrame:
    """
    Downloads and parses a dataset from a given URL.

    Parameters:
        url (str): The URL of the dataset file.

    Returns:
        dataframe (pandas.DataFrame): Parsed data as a DataFrame.

    Raises:
        DatasetParsingError: If the URL is invalid or the content is invalid.
        HTTPError: If the download fails.

    Upstream functions:
        - flow_fetch_online_dataset() in 'pages/3_ConfigureDatasets.py'

    Downstream functions:
        - map_dataset_fields()

    Dependencies:
        - requests
        - pandas
        - utils.error_handling
    """
    try:
        logger.info(f"Fetching dataset from URL: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        # Determine the file extension based on the URL
        parsed_url = requests.utils.urlparse(url)
        file_extension = Path(parsed_url.path).suffix.lower()
        content = response.content
        if file_extension not in [".csv", ".tsv", ".json", ".jsonl", ".yaml", ".yml", ".txt"]:
            logger.warning("Could not determine file type from URL. Assuming CSV format.")
            file_extension = ".csv"  # Default to CSV
        uploaded_file = type(
            "UploadedFile", (object,), {"name": f"downloaded{file_extension}", "read": lambda: content}
        )
        dataframe = parse_local_dataset_file(uploaded_file)
        logger.info(f"Dataset fetched and parsed successfully from URL: {url}")
        return dataframe
    except requests.HTTPError as e:
        logger.exception(f"HTTP error fetching dataset from URL '{url}': {e}")
        raise DatasetParsingError(f"HTTP error fetching dataset from URL '{url}': {e}") from e
    except Exception as e:
        logger.exception(f"Error fetching dataset from URL '{url}': {e}")
        raise DatasetParsingError(f"Error fetching dataset from URL '{url}': {e}") from e


def map_dataset_fields(dataframe: pd.DataFrame, mappings: Dict[str, str]) -> List[SeedPrompt]:
    """
    Maps fields from the dataframe to the required SeedPrompt attributes.

    Parameters:
        dataframe (pandas.DataFrame): The DataFrame containing dataset data.
        mappings (dict): A dictionary mapping DataFrame columns to SeedPrompt attributes.

    Returns:
        seed_prompts (list): A list of SeedPrompt objects.

    Raises:
        DatasetParsingError: If required fields are missing or mapping is invalid.

    Upstream functions:
        - flow_upload_local_dataset()
        - flow_fetch_online_dataset()

    Downstream functions:
        - create_seed_prompt_dataset()

    Dependencies:
        - pyrit.models.SeedPrompt
        - utils.error_handling
    """
    try:
        required_attributes = ["value"]
        seed_prompts = []
        for index, row in dataframe.iterrows():
            seed_prompt_data = {}
            for dataframe_column, prompt_attr in mappings.items():
                if dataframe_column not in dataframe.columns:
                    logger.error(f"Column '{dataframe_column}' not found in DataFrame")
                    raise DatasetParsingError(f"Column '{dataframe_column}' not found in dataset.")
                seed_prompt_data[prompt_attr] = row[dataframe_column]
            # Ensure required attributes are present
            if not all(attr in seed_prompt_data for attr in required_attributes):
                missing_attrs = [attr for attr in required_attributes if attr not in seed_prompt_data]
                logger.error(f"Missing required attributes: {missing_attrs} in row {index}")
                raise DatasetParsingError(f"Missing required attributes: {missing_attrs}")
            # Create SeedPrompt object
            seed_prompt = SeedPrompt(**seed_prompt_data)
            seed_prompts.append(seed_prompt)
        logger.info(f"Mapped dataset fields successfully. Total prompts: {len(seed_prompts)}")
        return seed_prompts
    except Exception as e:
        logger.exception(f"Error mapping dataset fields: {e}")
        raise DatasetParsingError(f"Error mapping dataset fields: {e}") from e


def create_seed_prompt_dataset(seed_prompts: List[SeedPrompt]) -> SeedPromptDataset:
    """
    Creates a SeedPromptDataset from a list of SeedPrompts.

    Parameters:
        seed_prompts (list): A list of SeedPrompt objects.

    Returns:
        dataset (SeedPromptDataset): The created SeedPromptDataset object.

    Raises:
        ValueError: If seed_prompts list is empty.

    Upstream functions:
        - map_dataset_fields()

    Downstream functions:
        - Used in dataset configuration steps.

    Dependencies:
        - pyrit.models.SeedPromptDataset
    """
    if not seed_prompts:
        logger.error("Seed prompts list is empty. Cannot create dataset.")
        raise ValueError("Cannot create SeedPromptDataset with an empty seed prompts list.")
    dataset = SeedPromptDataset(prompts=seed_prompts)
    logger.info(f"Created SeedPromptDataset with {len(seed_prompts)} prompts.")
    return dataset
