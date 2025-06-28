"""
Unit tests for data loaders (violentutf.util_datasets.data_loaders)

This module tests various dataset loading utilities including:
- Dataset loading
- Data parsing
- Error handling
- Data validation
"""

import json
import logging
import os
# Mock the error handling module before importing data_loaders
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pandas as pd
import pytest
import yaml


# Create mock error classes
class DatasetLoadingError(Exception):
    pass


class DatasetParsingError(Exception):
    pass


# Mock the error_handling module
mock_error_module = MagicMock()
mock_error_module.DatasetLoadingError = DatasetLoadingError
mock_error_module.DatasetParsingError = DatasetParsingError
sys.modules["utils.error_handling"] = mock_error_module

# Mock the logging module
mock_logging_module = MagicMock()
mock_logging_module.get_logger = MagicMock(return_value=logging.getLogger("test"))
sys.modules["utils.logging"] = mock_logging_module

from util_datasets.data_loaders import (create_seed_prompt_dataset,
                                        fetch_online_dataset, get_garak_probes,
                                        get_pyrit_datasets, load_dataset,
                                        map_dataset_fields,
                                        parse_local_dataset_file)


class TestDataLoaders:
    """Test data loading functionality"""

    def test_get_pyrit_datasets(self):
        """Test retrieving PyRIT dataset names"""
        datasets = get_pyrit_datasets()
        assert isinstance(datasets, list)
        assert len(datasets) > 0

    def test_get_garak_probes(self):
        """Test retrieving Garak probe names"""
        probes = get_garak_probes()
        assert isinstance(probes, list)
        assert len(probes) > 0

    @patch("util_datasets.data_loaders.pd.read_csv")
    def test_parse_local_dataset_file_csv(self, mock_read_csv):
        """Test parsing CSV files"""
        mock_df = pd.DataFrame({"prompt": ["test1", "test2"]})
        mock_read_csv.return_value = mock_df

        mock_file = Mock()
        mock_file.name = "test.csv"

        result = parse_local_dataset_file(mock_file)
        assert isinstance(result, pd.DataFrame)

    @patch("util_datasets.data_loaders.requests.get")
    def test_fetch_online_dataset(self, mock_get):
        """Test fetching online datasets"""
        mock_response = Mock()
        mock_response.text = "prompt\ntest1\ntest2"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = fetch_online_dataset("http://example.com/dataset.csv")
        assert isinstance(result, pd.DataFrame)

    def test_map_dataset_fields(self):
        """Test mapping dataset fields to SeedPrompt objects"""
        df = pd.DataFrame(
            {"text": ["prompt1", "prompt2"], "category": ["test", "test"]}
        )

        mappings = {"prompt_column": "text", "metadata_columns": ["category"]}

        result = map_dataset_fields(df, mappings)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_create_seed_prompt_dataset(self):
        """Test creating SeedPromptDataset from prompts"""
        from pyrit.models import SeedPrompt

        prompts = [
            Mock(spec=SeedPrompt, value="test1"),
            Mock(spec=SeedPrompt, value="test2"),
        ]

        result = create_seed_prompt_dataset(prompts)
        assert result is not None


class TestDatasetValidation:
    """Test dataset validation functionality"""

    def test_load_dataset_with_config(self):
        """Test loading dataset with configuration"""
        config = {"dataset_type": "local", "file_path": "test.csv"}

        with patch("util_datasets.data_loaders.parse_local_dataset_file") as mock_parse:
            mock_parse.return_value = pd.DataFrame({"prompt": ["test"]})

            result = load_dataset("test_dataset", config)
            assert result is not None

    def test_load_dataset_invalid_config(self):
        """Test loading dataset with invalid configuration"""
        config = {}

        result = load_dataset("test_dataset", config)
        assert result is None


class TestErrorHandling:
    """Test error handling in data loaders"""

    def test_parse_local_dataset_file_unsupported_format(self):
        """Test parsing unsupported file formats"""
        mock_file = Mock()
        mock_file.name = "test.unknown"

        with pytest.raises(ValueError):
            parse_local_dataset_file(mock_file)

    @patch("util_datasets.data_loaders.requests.get")
    def test_fetch_online_dataset_network_error(self, mock_get):
        """Test handling network errors when fetching datasets"""
        mock_get.side_effect = Exception("Network error")

        with pytest.raises(Exception):
            fetch_online_dataset("http://example.com/dataset.csv")
