# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Documentation Resources for MCP

==============================

This module provides access to ViolentUTF documentation through the MCP protocol
with full-text search, natural language querying, and intelligent response formatting.
"""

import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.mcp.resources.base import AdvancedResource, BaseResourceProvider, ResourceMetadata, advanced_resource_registry

logger = logging.getLogger(__name__)


class DocumentMetadata:
    """Enhanced metadata for documentation files"""

    def __init__(self, file_path: Path) -> None:
        """Initialize DocumentMetadata with file path."""
        self.file_path = file_path
        self.title = ""
        self.category = ""
        self.tags: List[str] = []
        self.author = ""
        self.word_count = 0
        self.line_count = 0
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.checksum = ""
        self.size = 0
        self.extract_metadata()

    def extract_metadata(self) -> None:
        """Extract metadata from the documentation file"""
        try:
            if not self.file_path.exists():
                logger.warning("Documentation file not found: %s", self.file_path)
                return

            # Get file stats
            stat = self.file_path.stat()
            self.size = stat.st_size
            self.created_at = datetime.fromtimestamp(stat.st_ctime, timezone.utc)
            self.updated_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc)

            # Read file content
            content = self.file_path.read_text(encoding="utf-8", errors="ignore")
            self.line_count = len(content.splitlines())
            self.word_count = len(content.split())

            # Calculate checksum
            self.checksum = hashlib.md5(content.encode("utf-8")).hexdigest()

            # Extract title from first heading or filename
            lines = content.splitlines()
            for line in lines:
                line = line.strip()
                if line.startswith("# "):
                    self.title = line[2:].strip()
                    break

            if not self.title:
                self.title = self.file_path.stem.replace("_", " ").replace("-", " ").title()

            # Determine category from path
            path_parts = self.file_path.parts
            if "docs" in path_parts:
                docs_index = path_parts.index("docs")
                if docs_index + 1 < len(path_parts):
                    self.category = path_parts[docs_index + 1]
                else:
                    self.category = "root"
            else:
                self.category = "other"

            # Extract tags from content (looking for common patterns)
            self.tags = self._extract_tags(content)

            # Try to extract author from git blame or file content
            self.author = self._extract_author(content)

        except Exception as e:
            logger.error("Error extracting metadata from %s: %s", self.file_path, e)

    def _extract_tags(self, content: str) -> List[str]:
        """Extract tags from document content"""
        tags = set()

        # Common ViolentUTF terms that should be tags
        common_terms = [
            "api",
            "apisix",
            "authentication",
            "docker",
            "keycloak",
            "mcp",
            "pyrit",
            "garak",
            "setup",
            "configuration",
            "troubleshooting",
            "testing",
            "security",
            "oauth",
            "jwt",
            "streamlit",
            "fastapi",
        ]

        content_lower = content.lower()
        for term in common_terms:
            if term in content_lower:
                tags.add(term)

        # Extract hashtags if present
        hashtag_pattern = r"#(\w+)"
        hashtags = re.findall(hashtag_pattern, content)
        tags.update(tag.lower() for tag in hashtags)

        # Extract from headers (common patterns)
        header_pattern = r"^##?\s+(.+)$"
        headers = re.findall(header_pattern, content, re.MULTILINE)
        for header in headers[:5]:  # Only first 5 headers
            # Extract meaningful words from headers
            words = re.findall(r"\b\w{4,}\b", header.lower())
            tags.update(word for word in words if word not in ["this", "that", "with", "from"])

        return list(tags)[:10]  # Limit to 10 most relevant tags

    def _extract_author(self, content: str) -> str:
        """Try to extract author information"""
        # Look for author patterns in content
        author_patterns = [r"Author:\s*(.+?)(?:\n|$)", r"By:\s*(.+?)(?:\n|$)", r"Created by:\s*(.+?)(?:\n|$)"]

        for pattern in author_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "ViolentUTF Team"

    def to_resource_metadata(self) -> ResourceMetadata:
        """Convert to MCP ResourceMetadata"""
        return ResourceMetadata(
            created_at=self.created_at,
            updated_at=self.updated_at,
            version="1.0",
            author=self.author,
            tags=self.tags,
            size=self.size,
            checksum=self.checksum,
        )


class DocumentIndex:
    """In-memory index for fast document searching"""

    def __init__(self) -> None:
        """Initialize DocumentIndex."""
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.word_index: Dict[str, Set[str]] = {}
        self.category_index: Dict[str, Set[str]] = {}
        self.tag_index: Dict[str, Set[str]] = {}
        self.title_index: Dict[str, str] = {}

    def add_document(self, doc_id: str, metadata: DocumentMetadata, content: str) -> None:
        """Add a document to the index"""
        try:
            # Store document
            self.documents[doc_id] = {
                "metadata": metadata,
                "content": content,
                "content_lower": content.lower(),
                "indexed_at": datetime.now(timezone.utc),
            }

            # Update category index
            if metadata.category not in self.category_index:
                self.category_index[metadata.category] = set()
            self.category_index[metadata.category].add(doc_id)

            # Update tag index
            for tag in metadata.tags:
                if tag not in self.tag_index:
                    self.tag_index[tag] = set()
                self.tag_index[tag].add(doc_id)

            # Update title index
            self.title_index[doc_id] = metadata.title

            # Update word index for full-text search
            words = self._extract_searchable_words(content)
            for word in words:
                if word not in self.word_index:
                    self.word_index[word] = set()
                self.word_index[word].add(doc_id)

            logger.debug("Indexed document: %s (%s unique words)", doc_id, len(words))

        except Exception as e:
            logger.error("Error indexing document %s: %s", doc_id, e)

    def _extract_searchable_words(self, content: str) -> Set[str]:
        """Extract words for search indexing"""
        # Convert to lowercase and extract words
        words = re.findall(r"\b\w{2,}\b", content.lower())

        # Filter out common stop words
        stop_words = {
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "up",
            "about",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "among",
            "this",
            "that",
            "these",
            "those",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "should",
            "could",
            "can",
            "may",
            "might",
            "must",
            "shall",
        }

        return {word for word in words if word not in stop_words and len(word) >= 2}

    def search(
        self, query: str, category: Optional[str] = None, tags: Optional[List[str]] = None, limit: int = 10
    ) -> List[Tuple[str, float]]:
        """Search documents and return ranked results"""
        if not query.strip():
            return []

        query_words = self._extract_searchable_words(query)
        if not query_words:
            return []

        # Find candidate documents
        candidates = set()
        for word in query_words:
            if word in self.word_index:
                candidates.update(self.word_index[word])

        # Apply category filter
        if category and category in self.category_index:
            candidates = candidates.intersection(self.category_index[category])

        # Apply tag filters
        if tags:
            for tag in tags:
                if tag in self.tag_index:
                    candidates = candidates.intersection(self.tag_index[tag])

        # Score and rank results
        scored_results = []
        for doc_id in candidates:
            score = self._calculate_relevance_score(doc_id, query_words)
            scored_results.append((doc_id, score))

        # Sort by score (descending) and limit results
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return scored_results[:limit]

    def _calculate_relevance_score(self, doc_id: str, query_words: Set[str]) -> float:
        """Calculate relevance score for a document"""
        if doc_id not in self.documents:
            return 0.0

        doc = self.documents[doc_id]
        content_lower = doc["content_lower"]
        title = self.title_index.get(doc_id, "").lower()

        score = 0.0

        # Title matches are heavily weighted
        title_matches = sum(1 for word in query_words if word in title)
        score += title_matches * 5.0

        # Content matches
        content_matches = sum(1 for word in query_words if word in content_lower)
        score += content_matches

        # Boost score for exact phrase matches
        query_phrase = " ".join(query_words)
        if query_phrase in content_lower:
            score += 3.0

        # Boost score for documents with more matching words
        matching_words = len([word for word in query_words if word in content_lower])
        score += (matching_words / len(query_words)) * 2.0

        return score

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        return self.documents.get(doc_id)

    def get_categories(self) -> List[str]:
        """Get all available categories"""
        return list(self.category_index.keys())

    def get_tags(self) -> List[str]:
        """Get all available tags"""
        return list(self.tag_index.keys())

    def get_document_count(self) -> int:
        """Get total number of indexed documents"""
        return len(self.documents)


class DocumentationResourceProvider(BaseResourceProvider):
    """Provides searchable access to ViolentUTF documentation"""

    def __init__(self) -> None:
        """Initialize AdvancedDocumentationProvider."""
        super().__init__(
            uri_pattern="violentutf://docs/{category}/{document_id}", provider_name="DocumentationProvider"
        )

        # Find documentation root directory
        self.docs_root = self._find_docs_root()
        self.index = DocumentIndex()
        self._indexed = False

        logger.info("DocumentationResourceProvider initialized with docs root: %s", self.docs_root)

    def _find_docs_root(self) -> Path:
        """Find the ViolentUTF docs directory"""
        # Try different possible locations
        possible_paths = [
            Path("/app/docs"),  # Docker container (primary)
            Path(__file__).parents[3] / "docs",  # From fastapi_app root (parents[3] = /app)
            Path(os.getenv("VIOLENTUTF_DOCS_PATH", "/tmp")),  # Environment variable
        ]

        for path in possible_paths:
            if path.exists() and path.is_dir():
                logger.info("Found docs directory: %s", path)
                return path

        # Fallback: create empty directory
        fallback = Path("/tmp/violentutf_docs")
        fallback.mkdir(exist_ok=True)
        logger.warning("No docs directory found, using fallback: %s", fallback)
        return fallback

    async def initialize(self) -> None:
        """Initialize the documentation index"""
        if self._indexed:
            return

        logger.info("Building documentation index...")
        start_time = datetime.now()

        try:
            # Find all markdown files
            md_files = list(self.docs_root.rglob("*.md"))
            logger.info("Found %s documentation files", len(md_files))

            indexed_count = 0
            for md_file in md_files:
                try:
                    # Extract metadata
                    metadata = DocumentMetadata(md_file)

                    # Read content
                    content = md_file.read_text(encoding="utf-8", errors="ignore")

                    # Generate document ID
                    relative_path = md_file.relative_to(self.docs_root)
                    doc_id = str(relative_path).replace("/", "_").replace(".md", "")

                    # Add to index
                    self.index.add_document(doc_id, metadata, content)
                    indexed_count += 1

                except Exception as e:
                    logger.error("Error processing %s: %s", md_file, e)

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info("Documentation index built: %s documents in %.2fs", indexed_count, elapsed)
            self._indexed = True

        except Exception as e:
            logger.error("Error building documentation index: %s", e)
            raise

    async def list_resources(self, params: Dict[str, Any] = None) -> List[AdvancedResource]:
        """List all available documentation resources"""
        if not self._indexed:
            await self.initialize()

        resources = []

        # Add search resource
        resources.append(
            AdvancedResource(
                uri="violentutf://docs/search/query",
                name="Documentation Search",
                description="Search ViolentUTF documentation with natural language queries",
                mimeType="application/json",
                content={"type": "search_endpoint", "description": "Query documentation with natural language"},
            )
        )

        # Add category overview resources
        categories = self.index.get_categories()
        for category in categories:
            resources.append(
                AdvancedResource(
                    uri=f"violentutf://docs/{category}/overview",
                    name=f"{category.title()} Documentation",
                    description=f"Overview of {category} documentation",
                    mimeType="application/json",
                    content={"type": "category_overview", "category": category},
                )
            )

        # Add individual document resources (limited to prevent overflow)
        doc_count = 0
        for doc_id in self.index.documents.keys():
            if doc_count >= 50:  # Limit to prevent large response
                break

            doc = self.index.get_document(doc_id)
            if doc:
                metadata = doc["metadata"]
                resources.append(
                    AdvancedResource(
                        uri=f"violentutf://docs/{metadata.category}/{doc_id}",
                        name=metadata.title,
                        description=f"Documentation: {metadata.title}",
                        mimeType="text/markdown",
                        content={"type": "document_reference", "doc_id": doc_id},
                        metadata=metadata.to_resource_metadata(),
                    )
                )
                doc_count += 1

        logger.debug("Listed %s documentation resources", len(resources))
        return resources

    async def get_resource(self, uri: str, params: Dict[str, Any]) -> Optional[AdvancedResource]:
        """Get specific documentation resource"""
        if not self._indexed:
            await self.initialize()

        uri_params = self.extract_params(uri)
        category = uri_params.get("category")
        document_id = uri_params.get("document_id")

        if not category or not document_id:
            logger.warning("Invalid documentation URI: %s", uri)
            return None

        try:
            # Handle search queries
            if category == "search" and document_id == "query":
                return await self._handle_search_query(uri, params)

            # Handle category overviews
            if document_id == "overview":
                return await self._handle_category_overview(category, params)

            # Handle specific document requests
            return await self._handle_document_request(category, document_id, params)

        except Exception as e:
            logger.error("Error getting documentation resource %s: %s", uri, e)
            return None

    async def _handle_search_query(self, uri: str, params: Dict[str, Any]) -> Optional[AdvancedResource]:
        """Handle documentation search queries"""
        query = params.get("query", "").strip()
        category_filter = params.get("category")
        tag_filters = params.get("tags", [])
        limit = min(params.get("limit", 5), 20)  # Limit to reasonable number

        if not query:
            return AdvancedResource(
                uri=uri,
                name="Search Help",
                description="Documentation search help and examples",
                content={
                    "error": "no_query",
                    "message": "Please provide a search query",
                    "examples": [
                        "How to setup ViolentUTF",
                        "API authentication",
                        "Troubleshooting Docker issues",
                        "MCP configuration",
                    ],
                    "categories": self.index.get_categories(),
                    "total_documents": self.index.get_document_count(),
                },
            )

        # Perform search
        results = self.index.search(query, category_filter, tag_filters, limit)

        if not results:
            return AdvancedResource(
                uri=uri,
                name="No Results",
                description=f"No documentation found for '{query}'",
                content={
                    "query": query,
                    "results": [],
                    "suggestions": self._get_search_suggestions(query),
                    "total_documents": self.index.get_document_count(),
                },
            )

        # Format search results
        formatted_results = []
        for doc_id, score in results:
            doc = self.index.get_document(doc_id)
            if doc:
                metadata = doc["metadata"]
                # Extract relevant snippet
                snippet = self._extract_snippet(doc["content"], query)

                formatted_results.append(
                    {
                        "id": doc_id,
                        "title": metadata.title,
                        "category": metadata.category,
                        "score": round(score, 2),
                        "snippet": snippet,
                        "tags": metadata.tags[:5],
                        "word_count": metadata.word_count,
                        "uri": f"violentutf://docs/{metadata.category}/{doc_id}",
                    }
                )

        return AdvancedResource(
            uri=uri,
            name=f"Search Results: {query}",
            description=f"Found {len(formatted_results)} documents matching '{query}'",
            content={
                "query": query,
                "results": formatted_results,
                "total_found": len(formatted_results),
                "search_time": datetime.now().isoformat(),
            },
        )

    def _extract_snippet(self, content: str, query: str, max_length: int = 200) -> str:
        """Extract a relevant snippet from document content"""
        query_words = query.lower().split()

        # Find the best position to extract snippet
        best_pos = 0
        best_score = 0

        # Search for positions with highest query word density
        words = content.split()
        for i in range(0, len(words) - 10, 5):  # Check every 5 words
            window = " ".join(words[i : i + 30]).lower()  # 30-word window
            score = sum(1 for qword in query_words if qword in window)
            if score > best_score:
                best_score = score
                best_pos = i

        # Extract snippet around best position
        start_word = max(0, best_pos - 10)
        end_word = min(len(words), best_pos + 20)
        snippet_words = words[start_word:end_word]
        snippet = " ".join(snippet_words)

        # Truncate if too long
        if len(snippet) > max_length:
            snippet = snippet[: max_length - 3] + "..."

        return snippet

    def _get_search_suggestions(self, query: str) -> List[str]:
        """Get search suggestions for failed queries"""
        suggestions = []

        # Common documentation topics
        common_topics = [
            "setup",
            "installation",
            "configuration",
            "troubleshooting",
            "API",
            "authentication",
            "Docker",
            "Keycloak",
            "MCP",
        ]

        # Find similar topics based on edit distance (simple approach)
        query_lower = query.lower()
        for topic in common_topics:
            if any(word in topic.lower() for word in query_lower.split()):
                suggestions.append(f"Try searching for '{topic}'")

        # Add category-based suggestions
        categories = self.index.get_categories()
        for category in categories[:3]:  # Limit to 3
            suggestions.append(f"Browse {category} documentation")

        return suggestions[:5]  # Limit to 5 suggestions

    async def _handle_category_overview(self, category: str, params: Dict[str, Any]) -> Optional[AdvancedResource]:
        """Handle category overview requests"""
        if category not in self.index.category_index:
            return None

        doc_ids = self.index.category_index[category]
        documents = []

        for doc_id in list(doc_ids)[:20]:  # Limit to 20 documents
            doc = self.index.get_document(doc_id)
            if doc:
                metadata = doc["metadata"]
                documents.append(
                    {
                        "id": doc_id,
                        "title": metadata.title,
                        "tags": metadata.tags[:3],
                        "word_count": metadata.word_count,
                        "updated_at": metadata.updated_at.isoformat(),
                        "uri": f"violentutf://docs/{category}/{doc_id}",
                    }
                )

        return AdvancedResource(
            uri=f"violentutf://docs/{category}/overview",
            name=f"{category.title()} Documentation Overview",
            description=f"Overview of all {category} documentation",
            content={"category": category, "document_count": len(doc_ids), "documents": documents},
        )

    async def _handle_document_request(
        self, category: str, document_id: str, params: Dict[str, Any]
    ) -> Optional[AdvancedResource]:
        """Handle specific document requests"""
        doc = self.index.get_document(document_id)
        if not doc:
            return None

        metadata = doc["metadata"]
        content = doc["content"]

        # Check if summary is requested
        if params.get("summary", False):
            content = self._create_document_summary(content)

        return AdvancedResource(
            uri=f"violentutf://docs/{category}/{document_id}",
            name=metadata.title,
            description=f"Documentation: {metadata.title}",
            mimeType="text/markdown",
            content=content,
            metadata=metadata.to_resource_metadata(),
        )

    def _create_document_summary(self, content: str, max_sentences: int = 5) -> str:
        """Create a summary of the document"""
        # Simple extractive summarization
        sentences = re.split(r"[.!?]+", content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        if len(sentences) <= max_sentences:
            return content

        # Score sentences based on position and keyword frequency
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            score = 0

            # Position bonus (first and last sentences)
            if i == 0:
                score += 3
            elif i < 3:
                score += 2
            elif i >= len(sentences) - 2:
                score += 1

            # Keyword bonus
            keywords = ["setup", "install", "configure", "important", "note", "warning"]
            for keyword in keywords:
                if keyword.lower() in sentence.lower():
                    score += 1

            scored_sentences.append((sentence, score))

        # Select top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [s[0] for s in scored_sentences[:max_sentences]]

        # Preserve original order
        summary_sentences = []
        for sentence in sentences:
            if sentence in top_sentences:
                summary_sentences.append(sentence)

        return ". ".join(summary_sentences) + "."


# Register the documentation resource provider
try:
    # Only skip registration during testing
    if not os.getenv("SKIP_RESOURCE_REGISTRATION"):
        documentation_provider = DocumentationResourceProvider()
        advanced_resource_registry.register(documentation_provider)
        logger.info("Documentation resource provider registered successfully")
    else:
        logger.info("Documentation resource provider registration skipped (testing mode)")
except Exception as e:
    logger.warning("Failed to register documentation resource provider: %s", e)
    # Don't fail startup if documentation provider fails
