"""
Transcript chunking utilities for large documents
"""

import re
from datetime import datetime
from typing import Any, Dict, List


class TranscriptChunker:
    """Handles intelligent chunking of large transcripts"""

    def __init__(self, max_chunk_size: int = 4000, overlap_size: int = 200):
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size

    def chunk_by_speakers(self, transcript: str) -> List[Dict[str, Any]]:
        """Chunk transcript by speaker changes, keeping context"""
        chunks = []
        lines = transcript.split("\n")

        current_chunk = []
        current_size = 0
        chunk_id = 1

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this is a speaker line (contains timestamp or speaker name)
            is_speaker_change = self._is_speaker_line(line)
            line_size = len(line)

            # If adding this line would exceed chunk size and we have content
            if (
                current_size + line_size > self.max_chunk_size
                and current_chunk
                and is_speaker_change
            ):

                # Create chunk
                chunk_text = "\n".join(current_chunk)
                chunks.append(
                    {
                        "id": chunk_id,
                        "text": chunk_text,
                        "start_line": current_chunk[0] if current_chunk else "",
                        "size": current_size,
                        "speaker_count": self._count_speakers(chunk_text),
                    }
                )

                # Start new chunk with overlap
                overlap_lines = self._get_overlap_lines(current_chunk)
                current_chunk = overlap_lines + [line]
                current_size = sum(len(l) for l in current_chunk)
                chunk_id += 1
            else:
                current_chunk.append(line)
                current_size += line_size

        # Add remaining content as final chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {
                    "id": chunk_id,
                    "text": chunk_text,
                    "start_line": current_chunk[0] if current_chunk else "",
                    "size": current_size,
                    "speaker_count": self._count_speakers(chunk_text),
                }
            )

        return chunks

    def chunk_by_time_segments(
        self, transcript: str, segment_minutes: int = 15
    ) -> List[Dict[str, Any]]:
        """Chunk transcript by time segments"""
        chunks = []
        lines = transcript.split("\n")

        current_chunk = []
        current_start_time = None
        chunk_id = 1

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Extract timestamp if present
            timestamp = self._extract_timestamp(line)

            if timestamp:
                if current_start_time is None:
                    current_start_time = timestamp

                # Check if we've exceeded the time segment
                if (
                    self._time_diff_minutes(current_start_time, timestamp)
                    >= segment_minutes
                ):
                    if current_chunk:
                        chunk_text = "\n".join(current_chunk)
                        chunks.append(
                            {
                                "id": chunk_id,
                                "text": chunk_text,
                                "start_time": current_start_time,
                                "end_time": timestamp,
                                "duration_minutes": segment_minutes,
                            }
                        )

                        # Start new chunk
                        current_chunk = [line]
                        current_start_time = timestamp
                        chunk_id += 1
                        continue

            current_chunk.append(line)

        # Add remaining content
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {
                    "id": chunk_id,
                    "text": chunk_text,
                    "start_time": current_start_time,
                    "end_time": timestamp if "timestamp" in locals() else None,
                    "duration_minutes": segment_minutes,
                }
            )

        return chunks

    def should_chunk(self, transcript: str) -> bool:
        """Determine if transcript should be chunked"""
        # Chunk if transcript is large or has many speakers
        transcript_size = len(transcript)
        speaker_count = self._count_speakers(transcript)
        line_count = len(transcript.split("\n"))

        return (
            transcript_size > self.max_chunk_size * 2  # Large transcript
            or speaker_count > 10  # Many speakers
            or line_count > 200  # Long transcript
        )

    def _is_speaker_line(self, line: str) -> bool:
        """Check if line indicates a speaker change"""
        # Look for timestamp patterns like [00:01:15] or speaker patterns like "Name:"
        timestamp_pattern = r"\[\d{2}:\d{2}:\d{2}\]"
        speaker_pattern = r"^[A-Za-z\s]+\s*[\(\[].+?[\)\]]?\s*:"

        return (
            bool(re.search(timestamp_pattern, line))
            or bool(re.match(speaker_pattern, line))
            or line.endswith(":")
        )

    def _get_overlap_lines(self, lines: List[str]) -> List[str]:
        """Get overlap lines for context preservation"""
        if not lines:
            return []

        # Take last few lines that fit within overlap size
        overlap_lines = []
        size = 0

        for line in reversed(lines):
            if size + len(line) <= self.overlap_size:
                overlap_lines.insert(0, line)
                size += len(line)
            else:
                break

        return overlap_lines

    def _count_speakers(self, text: str) -> int:
        """Count unique speakers in text"""
        speakers = set()
        lines = text.split("\n")

        for line in lines:
            if self._is_speaker_line(line):
                # Extract speaker name
                if ":" in line:
                    speaker = line.split(":")[0].strip()
                    # Clean up speaker name (remove timestamps, roles)
                    speaker = re.sub(r"\[.*?\]", "", speaker)
                    speaker = re.sub(r"\(.*?\)", "", speaker)
                    speaker = speaker.strip()
                    if speaker:
                        speakers.add(speaker)

        return len(speakers)

    def _extract_timestamp(self, line: str) -> str:
        """Extract timestamp from line"""
        timestamp_pattern = r"\[(\d{2}:\d{2}:\d{2})\]"
        match = re.search(timestamp_pattern, line)
        return match.group(1) if match else None

    def _time_diff_minutes(self, start_time: str, end_time: str) -> int:
        """Calculate time difference in minutes"""
        if not start_time or not end_time:
            return 0

        try:
            start = datetime.strptime(start_time, "%H:%M:%S")
            end = datetime.strptime(end_time, "%H:%M:%S")
            diff = (end - start).total_seconds() / 60
            return max(0, int(diff))
        except ValueError:
            return 0
