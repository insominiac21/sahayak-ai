"""
Semantic chunker for government scheme documents.
Splits documents by semantic boundaries (headers, sections) instead of fixed sizes.
"""

import re
from typing import List, Tuple


class SemanticChunker:
    """
    Split documents into semantic chunks (200-300 tokens each).
    Uses markdown headers and natural section boundaries.
    """

    def __init__(self, target_chunk_tokens: int = 250, max_chunk_tokens: int = 300):
        """
        Initialize chunker.
        
        Args:
            target_chunk_tokens: Target chunk size in tokens (approximate)
            max_chunk_tokens: Maximum chunk size in tokens
        """
        self.target_chunk_tokens = target_chunk_tokens
        self.max_chunk_tokens = max_chunk_tokens

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Rough estimate of token count (1 token ≈ 4 characters for English).
        
        Args:
            text: Text to estimate
        
        Returns:
            Approximate token count
        """
        return len(text) // 4

    def split_by_headers(self, text: str) -> List[Tuple[str, str]]:
        """
        Split text by markdown headers (# ## ###).
        
        Args:
            text: Document text
        
        Returns:
            List of (header_text, content) tuples
        """
        # Split on markdown headers
        pattern = r"^(#{1,3})\s+(.+?)$"
        lines = text.split("\n")
        
        sections = []
        current_header = "Overview"
        current_content = []
        
        for line in lines:
            match = re.match(pattern, line)
            if match:
                # Save previous section
                if current_content:
                    content = "\n".join(current_content).strip()
                    if content:
                        sections.append((current_header, content))
                
                # Start new section
                current_header = match.group(2).strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_content:
            content = "\n".join(current_content).strip()
            if content:
                sections.append((current_header, content))
        
        return sections

    def split_section_into_chunks(self, header: str, content: str) -> List[Tuple[str, str]]:
        """
        Split a section's content into chunks if it's larger than max_tokens.
        
        Args:
            header: Section header
            content: Section content
        
        Returns:
            List of (full_header, chunk_content) tuples
        """
        # If content is small enough, return as one chunk
        token_count = self.estimate_tokens(content)
        
        if token_count <= self.max_chunk_tokens:
            return [(header, content)]
        
        # Otherwise, split by paragraphs
        paragraphs = content.split("\n\n")
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = self.estimate_tokens(para)
            
            # If adding this paragraph exceeds max, save current chunk
            if current_tokens + para_tokens > self.max_chunk_tokens and current_chunk:
                chunk_content = "\n\n".join(current_chunk).strip()
                chunks.append((header, chunk_content))
                current_chunk = [para]
                current_tokens = para_tokens
            else:
                current_chunk.append(para)
                current_tokens += para_tokens
        
        # Save last chunk
        if current_chunk:
            chunk_content = "\n\n".join(current_chunk).strip()
            chunks.append((header, chunk_content))
        
        return chunks

    def chunk(self, text: str) -> List[str]:
        """
        Chunk a document into semantic pieces.
        
        Args:
            text: Full document text
        
        Returns:
            List of chunk texts (headers included for context)
        """
        # Split by headers first
        sections = self.split_by_headers(text)
        
        chunks = []
        for header, content in sections:
            # Further split each section if needed
            section_chunks = self.split_section_into_chunks(header, content)
            
            for chunk_header, chunk_content in section_chunks:
                # Include header in chunk for context
                full_chunk = f"## {chunk_header}\n\n{chunk_content}"
                chunks.append(full_chunk)
        
        return chunks

    def chunk_with_metadata(self, text: str, source: str = "") -> List[Tuple[str, str]]:
        """
        Chunk document and return with source metadata.
        
        Args:
            text: Document text
            source: Source document name
        
        Returns:
            List of (chunk_text, source) tuples
        """
        chunks = self.chunk(text)
        return [(chunk, source) for chunk in chunks]
