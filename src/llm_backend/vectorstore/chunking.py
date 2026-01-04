from typing import List
from llm_backend.utils.logger import logger


class RecursiveTokenChunker:
    """
    Splits text recursively based on a list of separators, trying to keep chunks
    within a target size.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def split_text(self, text: str) -> List[str]:
        final_chunks = []
        if not text:
            return final_chunks

        # 1. Start with the whole text as one chunk
        good_splits = self._split_recursively(text, self.separators)

        # 2. Merge small splits back together up to chunk_size
        current_chunk = ""
        for split in good_splits:
            if len(current_chunk) + len(split) <= self.chunk_size:
                current_chunk += split
            else:
                if current_chunk:
                    final_chunks.append(current_chunk)

                # Start new chunk with overlap if possible (simplified here: just start new)
                # Ideally we want overlap. For now, simple accumulation.
                if len(split) > self.chunk_size:
                    # If single split is huge, force break it?
                    # The recursive splitter should have handled it mostly,
                    # but if it failed (no separators), we take it as is.
                    final_chunks.append(split)
                    current_chunk = ""
                else:
                    current_chunk = split

        if current_chunk:
            final_chunks.append(current_chunk)

        return final_chunks

    def _split_recursively(self, text: str, separators: List[str]) -> List[str]:
        """
        Recursively split text by the first separator that produces valid splits.
        """
        if not separators:
            return [text]  # No more separators, return as is (even if large)

        separator = separators[0]
        new_separators = separators[1:]

        if separator == "":
            # Character split
            return [c for c in text]

        splits = text.split(separator)

        # If splitting didn't help (still just one chunk) and it's too big, try next separator
        if len(splits) == 1 and len(text) > self.chunk_size:
            return self._split_recursively(text, new_separators)

        # Re-add separator to keep it? LangChain usually drops or keeps.
        # Let's drop for simplicity or append.
        # Ideally, we want to construct meaningful blocks.
        # Let's try to refine:

        final_splits = []
        for s in splits:
            if not s.strip():
                continue

            # Restore separator if needed. (e.g. prepending or appending)
            # SImplified: separator is lost in split.
            # Let's add separator back to end of s, except last.
            s_with_sep = s + separator

            if len(s_with_sep) <= self.chunk_size:
                final_splits.append(s_with_sep)
            else:
                # Recurse on this big chunk
                final_splits.extend(self._split_recursively(s_with_sep, new_separators))

        return final_splits


# Robust Implementation Logic (Inspired by standard libraries)
class SimpleRecursiveChunker:
    def __init__(self, chunk_size=1000, chunk_overlap=100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", " ", ""]

    def split_text(self, text: str) -> List[str]:
        return self._split(text, self.separators)

    def _split(self, text: str, separators: List[str]) -> List[str]:
        separator = separators[-1]

        # Find the best separator
        for sep in separators:
            if sep == "":
                separator = ""
                break
            if sep in text:
                separator = sep
                break

        # Split
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)  # Char split

        # Merge
        good_splits = []
        for s in splits:
            if len(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if len(good_splits) > 0:
                    # Flush accumulated? No, this is recursive descent.
                    # We need to recurse on 's' if possible
                    if separators.index(separator) + 1 < len(separators):
                        sub_splits = self._split(
                            s, separators[separators.index(separator) + 1 :]
                        )
                        good_splits.extend(sub_splits)
                    else:
                        good_splits.append(s)  # Can't split further

        # Now merge 'good_splits' into chunks of size 'chunk_size' with overlap
        return self._merge_splits(good_splits, separator)

    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        docs = []
        current_doc = []
        total = 0
        for d in splits:
            _len = len(d)
            if total + _len + (len(separator) if current_doc else 0) > self.chunk_size:
                if total > self.chunk_size:
                    logger.warning(
                        f"Created chunk of size {total}, which is longer than {self.chunk_size}"
                    )

                if current_doc:
                    docs.append(separator.join(current_doc))

                    # Handle Overlap (Basic)
                    # Keep last few items that fit in overlap
                    while total > self.chunk_overlap:
                        total -= len(current_doc[0]) + len(separator)
                        current_doc.pop(0)

            current_doc.append(d)
            total += _len + (len(separator) if len(current_doc) > 1 else 0)

        if current_doc:
            docs.append(separator.join(current_doc))

        return docs
